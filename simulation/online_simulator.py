import os
import json
from web3 import Web3
from pathlib import Path
from typing import Any, Dict, List

PROTOCOL_TO_ID = {
    'uniswap_v2': 0,
    'sushiswap_v2': 0,
    'uniswap_v3': 1,
    'sushiswap_v3': 1,
}

DIR = os.path.dirname(os.path.abspath(__file__))
ABI_FILE_PATH = Path(DIR) / 'SimulatorV1.json'
SIMULATOR_ABI = json.load(open(ABI_FILE_PATH, 'r'))['abi']


class OnlineSimulator:
    """
    This class will be used temporarily before an offline simulator is built.

    Using an online simulator is easy, but comes with a cost of latency.
    """

    def __init__(self,
                 rpc_endpoints: Dict[str, str],
                 tokens: Dict[str, Dict[str, List[str or int]]],
                 pools: List[Dict[str, Any]],
                 contracts: Dict[str, str],
                 handlers: Dict[str, Dict[str, str]]):
        """
        :param rpc_endpoints: refer to data.dex.DEX
        :param tokens: refer to data.dex.DEX
        :param pools: refer to dadta.dex.DEX

        :param contracts: the dict of address of SimulatorV1 contract deployed
        ex) {'ethereum': '<ADDRESS>', 'polygon': '<ADDRESS>', ... }

        :param handlers: dict of handler addresses for uniswap_v2, sushiswap_v2, uniswap_v3, sushiswap_v3, etc...
        For simulations an Uniswap V2 variant uses Factory, and an Uniswap V3 variant uses QuoterV2 to simulate swaps.
        ex) {'ethereum': {'uniswap_v2': '<FACTORY_ADDRESS>', ... }, ... }
        """
        self.rpc_endpoints = rpc_endpoints
        self.tokens = tokens
        self.pools = pools
        self.contracts = contracts
        self.handlers = handlers

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

        self.web3 = {k: Web3(Web3.HTTPProvider(v)) for k, v in rpc_endpoints.items()}

        self.sim = {
            chain: self.web3[chain].eth.contract(address=self.contracts[chain], abi=SIMULATOR_ABI)
            for chain in self.chains_list
        }

    def make_params(self,
                    amount_in: float,
                    buy_path: List[List[int]],
                    sell_path: List[List[int]],
                    buy_pools: List[int],
                    sell_pools: List[int]) -> List[Dict[str, Any]]:

        params = []
        params.extend(self._make_buy_params(amount_in, buy_path, buy_pools))
        params.extend(self._make_sell_params(sell_path, sell_pools))
        return params

    def _make_buy_params(self,
                         amount_in: float,
                         path: List[List[int]],
                         pools: List[int]):

        params_list = []

        for i in range(len(path)):
            _path = path[i]
            if not sum(_path):
                continue

            _pool_idx = pools[i]

            pool = self.pools[_pool_idx]
            chain = pool['chain']
            exchange = pool['exchange']
            version = pool['version']
            exchange_key = f'{exchange}_v{version}'

            token_in = self.tokens_list[_path[2]]
            token_out = self.tokens_list[_path[3]]

            amount_in_scaled = amount_in if i == 0 else 0

            params = {
                'protocol': PROTOCOL_TO_ID[exchange_key],
                'handler': self.handlers[chain][exchange_key],
                'tokenIn': self.tokens[chain][token_in][0],
                'tokenOut': self.tokens[chain][token_out][0],
                'fee': pool['fee'],
                'amount': int(amount_in_scaled),
            }
            params_list.append(params)

        return params_list

    def _make_sell_params(self, path: List[List[int]], pools: List[int]):
        params_list = []

        for i in range(len(path)):
            _path = path[i]
            if not sum(_path):
                continue

            _pool_idx = pools[i]

            pool = self.pools[_pool_idx]
            chain = pool['chain']
            exchange = pool['exchange']
            version = pool['version']
            exchange_key = f'{exchange}_v{version}'

            # not the index difference with buy_params
            token_in = self.tokens_list[_path[3]]
            token_out = self.tokens_list[_path[2]]

            params = {
                'protocol': PROTOCOL_TO_ID[exchange_key],
                'handler': self.handlers[chain][exchange_key],
                'tokenIn': self.tokens[chain][token_in][0],
                'tokenOut': self.tokens[chain][token_out][0],
                'fee': pool['fee'],
                'amount': 0,  # no need to set amount
            }
            params_list.append(params)

        return list(reversed(params_list))

    def simulate(self, chain: str, params: List[Dict[str, Any]]) -> int:
        return self.sim[chain].functions.simulateSwapIn(params).call()


if __name__ == '__main__':
    import os
    from dotenv import load_dotenv

    from configs import RPC_ENDPOINTS
    from addresses.ethereum import TOKENS, POOLS, SIMULATION_HANDLERS

    load_dotenv(override=True)

    ETHEREUM_SIMULATOR_ADDRESS = os.getenv('ETHEREUM_SIMULATOR_ADDRESS')

    chain = 'ethereum'

    rpc_endpoints = {chain: RPC_ENDPOINTS[chain]}
    tokens = {chain: TOKENS}
    pools = [pool for pool in POOLS if pool['chain'] == chain]
    contracts = {chain: ETHEREUM_SIMULATOR_ADDRESS}
    handlers = {chain: SIMULATION_HANDLERS}

    sim = OnlineSimulator(rpc_endpoints, tokens, pools, contracts, handlers)

    """
    ETH/USDT
    - Buy: USDT -> ETH
    - Sell: ETH -> USDT

    Buy, sell should work like CEXs
    """
    for i in range(100, 1000, 100):
        amount_in = i * 10 ** 6
        print('==========')
        print('Amount in: ', amount_in)

        buy_path = [[0, 1, 5, 2, 1], [0, 0, 0, 0, 0]]
        sell_path = [[0, 0, 5, 2, 1], [0, 0, 0, 0, 0]]

        buy_pools = [0]
        sell_pools = [9]

        params = sim.make_params(amount_in, buy_path, sell_path, buy_pools, sell_pools)

        for param in params:
            print(param)
        """
        SUS3ETHUSDT/UNI3ETHUSDT
        
        - Buy: UNI3ETHUSDT
        - Sell: SUS3ETHUSDT
        
        Output:
        
        {'protocol': 1, 'handler': '0x61fFE014bA17989E743c5F6cB21bF9697530B21e', 'tokenIn': '0xdAC17F958D2ee523a2206206994597C13D831ec7', 'tokenOut': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2', 'fee': 500, 'amount': 100000000}
        {'protocol': 1, 'handler': '0x64e8802FE490fa7cc61d3463958199161Bb608A7', 'tokenIn': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2', 'tokenOut': '0xdAC17F958D2ee523a2206206994597C13D831ec7', 'fee': 500, 'amount': 0}
        """

        simulated_amount_out = sim.simulate(chain, params)
        print(f'Simulated amount out: {simulated_amount_out / 10 ** 6} USDT')

        simulated_profit_in_usdt = (simulated_amount_out - amount_in) / 10 ** 6
        print(f'Simulated profit: {simulated_profit_in_usdt} USDT')
