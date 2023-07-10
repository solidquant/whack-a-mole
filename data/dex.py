import numpy as np
from web3 import Web3
from typing import Any, Dict, List
from multicall import Call, Multicall

# Dimension of DEX.storage_array
CHAIN = 0
EXCHANGE = 1
TOKEN_IN = 2
TOKEN_OUT = 3
VERSION = 4
STORAGE = 5

V2 = 0
V3 = 1

DECIMALS0 = 0
DECIMALS1 = 1
RESERVE0 = 2
RESERVE1 = 3
SQRT_PRICE = 4
FEE = 5
TOKEN_IN_IS_TOKEN0 = 6


class DexBase:

    def __init__(self,
                 rpc_endpoints: Dict[str, str],
                 tokens: Dict[str, Dict[str, List[str or int]]],
                 pools: List[Dict[str, Any]],
                 trading_symbols: List[str],
                 max_swap_number: int = 3):
        """
        :param rpc_endpoints:
        ex) {'ethereum': '<RPC URL>'}

        :param tokens:
        ex) {'ethereum': {'ETH': ['<token address>', 18]}}

        :param pools:
        ex) [{'chain': 'ethereum',
              'exchange': 'uniswap',
              'version': 3,
              'name': 'ETH/USDT',
              'address': '<pool address>',
              'fee': 500,  # 0.05%
              'token0': 'ETH',
              'token1': 'USDT'}]

        :param trading_symbols:
        ex) ['BTC/USDT']

        :param max_swap_number: the maximum number of swaps in a trade
        ex) 1, 2, 3, ...
        """
        self.rpc_endpoints = rpc_endpoints
        self.tokens = tokens
        self.pools = pools
        self.trading_symbols = trading_symbols
        self.max_swap_number = max_swap_number

        self.web3 = {k: Web3(Web3.HTTPProvider(v)) for k, v in rpc_endpoints.items()}

        # extract keys from tokens, pools
        self.chains_list = sorted(list(tokens.keys()))
        self.exchanges_list = sorted(set([p['exchange'] for p in pools]))

        tokens_list = []
        for exchange, tokens_dict in tokens.items():
            tokens_list.extend(list(tokens_dict.keys()))
        self.tokens_list = sorted(list(set(tokens_list)))

        # map chains, exchanges, tokens to int id value
        # this is used to map chains/exchanges/tokens to numpy array index values
        self.chain_to_id = {k: i for i, k in enumerate(self.chains_list)}
        self.exchange_to_id = {k: i for i, k in enumerate(self.exchanges_list)}
        self.token_to_id = {k: i for i, k in enumerate(self.tokens_list)}

        """
        storage_array
        : 6-dimensional array that stores storage values from pool contracts
        """
        self.storage_array = np.zeros((
            len(self.chains_list),      # chains
            len(self.exchanges_list),   # exchanges
            len(tokens_list),           # token in
            len(tokens_list),           # token out
            2,                          # uniswap variant version: 2, 3
            7                           # decimals0, decimals1, reserve0, reserve1, sqrtPriceX96, fee, token0_is_input
        ))

        """
        storage_index
        : Keeps the 5-dimensional index of storage_array by chains
        : Used to generate swap paths
        : Filled in _load_pool_data()
        
        ex) {'ethereum': [(0, 0, 1, 2, 0), ...]
        """
        self.storage_index = {c: [] for c in self.chains_list}

        """
        swap_paths
        : contains information about swap paths, tokens involved, price, fee
        : Filled in _generate_swap_paths()

        ex) {'ETH/USDT': {'path': np.ndarray,
                          'tokens': np.ndarray,
                          'price': np.ndarray
                          'fee': np.ndarray}, ...}
        """
        self.swap_paths = {s: None for s in self.trading_symbols}

        self._load_pool_data()
        self._generate_swap_paths()

    def _load_pool_data(self):
        """
        Loads all storage values from multiple pool contracts using Multicall
        this enables users to bulk query data on the blockchain
        """
        calls_by_chain = {c: [] for c in self.chains_list}

        for pool_idx, pool in enumerate(self.pools):
            if pool['version'] == 2:
                """
                Reference: https://github.com/Uniswap/v2-core/blob/master/contracts/UniswapV2Pair.sol
                Return values: reserve0, reserve1, blockTimestampLast
                """
                signature = 'getReserves()((uint112,uint112,uint32))'
            else:
                """
                Reference: https://github.com/Uniswap/v3-core/blob/main/contracts/UniswapV3Pool.sol
                Return values: sqrtPriceX96, tick, observationIndex, observationCardinality,
                               observationCardinalityNext, feeProtocol, unlocked
                """
                signature = 'slot0()((uint160,int24,uint16,uint16,uint16,uint8,bool))'

            call = Call(
                pool['address'],
                signature,
                [(str(pool_idx), lambda x: x)]
            )
            calls_by_chain[pool['chain']].append(call)

        # Send multicall queries
        multicall_results = {}
        for exchange, calls in calls_by_chain.items():
            multicall = Multicall(calls, _w3=self.web3[exchange])
            multicall_results = {
                **multicall_results,
                **multicall()
            }

        # Fill in storage_index, storage_array
        for pool_idx, storage_data in multicall_results.items():
            pool: Dict[str, Any] = self.pools[int(pool_idx)]

            chain_idx = self.chain_to_id[pool['chain']]
            exchange_idx = self.exchange_to_id[pool['exchange']]
            token0_idx = self.token_to_id[pool['token0']]
            token1_idx = self.token_to_id[pool['token1']]
            version_idx = V2 if pool['version'] == 2 else V3

            # We create two indexes to indicate:
            # - token0 -> token1,
            # - token1 -> token0
            idx_1 = (chain_idx, exchange_idx, token0_idx, token1_idx, version_idx)
            idx_2 = (chain_idx, exchange_idx, token1_idx, token0_idx, version_idx)

            self.storage_index[pool['chain']].append(idx_1)
            self.storage_index[pool['chain']].append(idx_2)

            decimals0 = self.tokens[pool['chain']][pool['token0']][1]
            decimals1 = self.tokens[pool['chain']][pool['token1']][1]
            fee = pool['fee'] / 10000.0 / 100.0

            data = [0] * 6

            if version_idx == V2:
                reserve0 = storage_data[0]
                reserve1 = storage_data[1]
                data = [decimals0, decimals1, reserve0, reserve1, 0, fee]

            elif version_idx == V3:
                sqrt_price = storage_data[0]
                data = [decimals0, decimals1, 0, 0, sqrt_price, fee]

            self.storage_array[idx_1] = data + [1]  # token_in is token0
            self.storage_array[idx_2] = data + [0]  # token_in is not token0

    def _generate_swap_paths(self):
        """
        Generates all the swap paths up to max_swap_number swaps
        This internal function has to be called after DEX.storage_index has been filled
        """
        token_in_out = {
            symbol: [self.token_to_id[token] for token in reversed(symbol.split('/'))]
            for symbol in self.trading_symbols
        }

        chain_swap_paths = {}

        for chain, index in self.storage_index.items():
            index_arr = np.array(index)

            symbol_swap_paths = {}

            """
            Loop through each symbol from trading_symbols
            and generate viable swap paths that can occur within a blockchain.
            This means that there will be multiple viable swap paths for each chain.
            """
            for symbol, in_out in token_in_out.items():
                pool_samples = self.__sample_pools(index_arr, in_out)
                paths = self.__generate_paths(pool_samples)

                paths_arr = np.array(paths)
                if paths_arr.shape[0] != 0:
                    symbol_swap_paths[symbol] = paths_arr
                else:
                    symbol_swap_paths[symbol] = paths_arr.reshape((0, 3, 5)).astype(np.int64)

            chain_swap_paths[chain] = symbol_swap_paths

        # concatenate the paths generated for each chain
        for symbol in self.trading_symbols:
            symbol_paths_list = [chain_swap_paths[chain][symbol] for chain in self.chains_list]
            symbol_paths_array = np.concatenate(symbol_paths_list)

            _tokens_involved = symbol_paths_array[:, :, [TOKEN_IN, TOKEN_OUT]].reshape(-1, 2)
            tokens_involved = np.unique(_tokens_involved[~np.all(_tokens_involved == 0, axis=1)])

            price_arr = np.zeros(symbol_paths_array.shape[0])
            fee_arr = np.zeros(symbol_paths_array.shape[0])

            self.swap_paths[symbol] = {
                'path': symbol_paths_array,
                'tokens': tokens_involved,
                'price': price_arr,
                'fee': fee_arr,
            }

    def __sample_pools(self, index_arr: np.ndarray, in_out: List[int]) -> Dict[int, List[List[List[int]]]]:
        # Step #1
        # Sampling pools that can be used in n-hop swaps with token_in, token_out constraints
        # Sampling before finding swap paths can reduce the time it takes to build viable swap paths
        swap_nums = range(1, self.max_swap_number + 1)
        pool_samples = {n: [] for n in swap_nums}

        for n in swap_nums:
            token_in, token_out = in_out

            no_path = False

            # setup an empty list of pool samples that could be used in each nth step of the swap path
            filtered_pools = [[]] * self.max_swap_number

            for i in range(n):
                if i == 0:
                    # token_in is int here
                    condition_1 = index_arr[:, TOKEN_IN] == token_in
                else:
                    # token_in in List[int] here
                    condition_1 = np.isin(index_arr[:, TOKEN_IN], token_in)

                if i == n - 1:
                    condition_2 = index_arr[:, TOKEN_OUT] == token_out
                else:
                    condition_2 = index_arr[:, TOKEN_OUT] != token_out

                condition = condition_1 & condition_2
                filtered = index_arr[condition]
                if filtered.shape[0] > 0:
                    filtered_pools[i] = filtered.tolist()
                else:
                    no_path = True
                    break

                # set the next token_in to be current token_outs
                token_in = list(filtered[:, TOKEN_OUT])

            if not no_path:
                pool_samples[n] = filtered_pools

        return pool_samples

    def __generate_paths(self, pool_samples: Dict[int, List[List[List[int]]]]) -> List[List[List[int]]]:
        """
        :param pool_samples: returned value of DEX._sample_pools
        """

        def __sample_paths_list(_n_total_hops: int,
                                _nth_hop: int,
                                _prev_pool: None or List[int],
                                _sampled: List[List[int]],
                                _pool_samples: Dict[int, List[List[List[int]]]],
                                _paths: List[List[List[int]]]):
            """
            Uses recursive looping to fill in paths_list

            :param _n_total_hops: the number of hops you are trying to sample. ex) 1, 2, 3, ...
            :param _nth_hop: out of the _n_total_hops which _nth_hop are you on
            :param _prev_pool: the previous pool index. ex) (0, 0, 1, 2, 0)
            :param _sampled: the sampled pools we should append to _paths
            :param _pool_samples: pool_samples we made from the above sampling process
            :param _paths: the list that collects all viable combination of pools
            """

            for _p in _pool_samples[_n_total_hops][_nth_hop]:
                _sampled[_nth_hop] = _p
                if _prev_pool is None or _prev_pool[TOKEN_OUT] == _p[TOKEN_IN]:
                    if _nth_hop == _n_total_hops - 1:
                        if _prev_pool:
                            """
                            Exclude swaps that buy from the previous step, and sells on this one
                            ex) ETH -> USDT -> ETH
                            (ETH/USDT, USDT/ETH pools on the same exchange, version are considered equal)

                            This isn't necessarily true in Uniswap V3 variants, because different fee levels can exist.
                            However, we exclude that scenario for simplicity.
                            """
                            same_exchange = _prev_pool[EXCHANGE] == _p[EXCHANGE]
                            same_version = _prev_pool[VERSION] == _p[VERSION]
                            same_pool = _prev_pool[TOKEN_IN] == _p[TOKEN_OUT] and _prev_pool[TOKEN_OUT] == _p[
                                TOKEN_IN]
                            if not (same_exchange and same_version and same_pool):
                                _paths.append(_sampled.copy())
                        else:
                            _paths.append(_sampled.copy())
                    else:
                        __sample_paths_list(_n_total_hops,
                                            _nth_hop + 1,
                                            _p,
                                            _sampled,
                                            _pool_samples,
                                            _paths)

        # Step #2
        # Generate swap paths by applying conditional checks to see if token_in, token_out is in sync
        paths = []
        empty_pool = [0, 0, 0, 0, 0]

        for i in range(1, self.max_swap_number + 1):
            if len(pool_samples[i]) > 0:
                sampled = [empty_pool] * self.max_swap_number
                prev_pool = None
                __sample_paths_list(_n_total_hops=i,
                                    _nth_hop=0,
                                    _prev_pool=prev_pool,
                                    _sampled=sampled,
                                    _pool_samples=pool_samples,
                                    _paths=paths)

        return paths


class NoSymbolError(Exception):

    def __init__(self, msg: str):
        self.msg = msg

    def __str__(self):
        return self.msg


class DEX(DexBase):

    def __init__(self,
                 rpc_endpoints: Dict[str, str],
                 tokens: Dict[str, Dict[str, List[str or int]]],
                 pools: List[Dict[str, Any]],
                 trading_symbols: List[str],
                 max_swap_number: int = 3):

        super().__init__(rpc_endpoints,
                         tokens,
                         pools,
                         trading_symbols,
                         max_swap_number)

        for symbol in self.trading_symbols:
            self.update_price_for_symbol(symbol)

    def get_index(self,
                  chain: str,
                  exchange: str,
                  token0: str,
                  token1: str,
                  version: int) -> tuple:

        c = self.chain_to_id[chain]
        e = self.exchange_to_id[exchange]
        t0 = self.token_to_id[token0]
        t1 = self.token_to_id[token1]
        v = V2 if version == 2 else V3
        return c, e, t0, t1, v

    def get_price(self,
                  c: int,
                  e: int,
                  t0: int,
                  t1: int,
                  v: int) -> tuple:

        idx = (c, e, t0, t1, v)
        dec0, dec1, res0, res1, sqrt, fee, tok0 = self.storage_array[idx]

        if v == V2:
            price = reserves_to_price(res0, res1, dec0, dec1, tok0)
        else:
            price = sqrt_to_price(sqrt, dec0, dec1, tok0)

        return price, fee

    def get_symbols_to_update(self, token0: str, token1: str) -> List[str]:
        """
        Returns the symbols that need to be updated after
        token0, token1 storage information have been updated

        This is used in DexStream to figure out which symbols to update the price for
        after receiving Sync, Swap events from Uniswap V2, V3 variant exchanges
        """
        token0_id = self.token_to_id[token0]
        token1_id = self.token_to_id[token1]

        symbols_to_update = []

        for symbol in self.trading_symbols:
            tokens_involved = self.swap_paths[symbol]['tokens']
            if token0_id in tokens_involved or token1_id in tokens_involved:
                symbols_to_update.append(symbol)

        return symbols_to_update

    def update_price_for_symbol(self, symbol: str):
        if symbol not in self.trading_symbols:
            raise NoSymbolError(f'{symbol} not in {self.trading_symbols}')

        paths_arr = self.swap_paths[symbol]['path']
        price_arr = self.swap_paths[symbol]['price']
        fee_arr = self.swap_paths[symbol]['fee']

        for i in np.arange(paths_arr.shape[0]):
            path = paths_arr[i]
            price = 1
            fee = 1
            for p_step in np.arange(path.shape[0]):
                idx = path[p_step]
                if np.sum(idx) == 0:
                    break
                _p, _f = self.get_price(*idx)
                """
                Take the inverse of price.
                This is needed because if you are trying to BUY ETH with USDT,
                then token_in will be USDT, and token_out will be ETH.
                Thus, the quote amount of ETH you get for providing 1 USDT is currently: 0.0005387 ETH.
                However, we want the price to be ETH/USDT = 1856.32 USDT.
                To get this value, we take the inverse of price.
                1 / 0.0005387 = 1856.32
                """
                price = price * (1 / _p)
                fee = fee * (1 - _f)

            price_arr[i] = price
            fee_arr[i] = 1 - fee

    def update_reserves(self,
                        chain: str,
                        exchange: str,
                        token0: str,
                        token1: str,
                        reserve0: float,
                        reserve1: float):

        idx_1 = self.get_index(chain, exchange, token0, token1, 2)
        idx_2 = (idx_1[0], idx_1[1], idx_1[3], idx_1[2], idx_1[4])

        storage_1 = self.storage_array[idx_1]
        storage_1[RESERVE0] = reserve0
        storage_1[RESERVE1] = reserve1

        storage_2 = self.storage_array[idx_2]
        storage_2[RESERVE0] = reserve0
        storage_2[RESERVE1] = reserve1

        self.storage_array[idx_1] = storage_1
        self.storage_array[idx_2] = storage_2

    def update_sqrt_price(self,
                          chain: str,
                          exchange: str,
                          token0: str,
                          token1: str,
                          sqrt_price: float):

        idx_1 = self.get_index(chain, exchange, token0, token1, 2)
        idx_2 = (idx_1[0], idx_1[1], idx_1[3], idx_1[2], idx_1[4])

        storage_1 = self.storage_array[idx_1]
        storage_1[SQRT_PRICE] = sqrt_price

        storage_2 = self.storage_array[idx_2]
        storage_2[SQRT_PRICE] = sqrt_price

        self.storage_array[idx_1] = storage_1
        self.storage_array[idx_2] = storage_2

    def debug_message(self,
                      chain: str,
                      exchange: str,
                      token0: str,
                      token1: str,
                      version: int):

        idx = self.get_index(chain, exchange, token0, token1, version)
        price, _ = self.get_price(*idx)
        print(f'[{chain}] {exchange} V{version}: {token0} -> {token1} @{price} / {token1} -> {token0} @{1 / price}')


# Uniswap math utility functions

def sqrt_to_price(sqrt: float,
                  decimals0: float,
                  decimals1: float,
                  token_in_is_token0: int) -> float:
    """
    Uniswap V3 variant calculation of price
    """
    numerator = sqrt ** 2
    denominator = 2 ** 192
    ratio = numerator / denominator
    shift_decimals = 10 ** (decimals0 - decimals1)
    ratio *= shift_decimals
    return ratio if token_in_is_token0 == 1 else 1 / ratio


def reserves_to_price(reserve0: float,
                      reserve1: float,
                      decimals0: float,
                      decimals1: float,
                      token_in_is_token0: int) -> float:
    """
    Uniswap V2 variant calculation of price
    """
    ratio = reserve1 / reserve0 * 10 ** (decimals0 - decimals1)
    return ratio if token_in_is_token0 == 1 else 1 / ratio


if __name__ == '__main__':
    from configs import RPC_ENDPOINTS, TOKENS, POOLS, TRADING_SYMBOLS

    dex = DEX(RPC_ENDPOINTS,
              TOKENS,
              POOLS,
              TRADING_SYMBOLS)
