import os
import time
import asyncio
import datetime
import aioprocessing
from functools import partial
from dotenv import load_dotenv
from multiprocessing import Process
from typing import Any, Dict, Optional, List

from configs import *
from execution import DexOrder
from data import DEX, DexStream
from simulation import OnlineSimulator
from external import InfluxDB, Telegram

load_dotenv(override=True)

FLASHBOTS_SIGNING_KEY = os.getenv('FLASHBOTS_SIGNING_KEY')
FLASHBOTS_PRIVATE_KEY = os.getenv('FLASHBOTS_PRIVATE_KEY')

ETHEREUM_BOT_ADDRESS = os.getenv('ETHEREUM_BOT_ADDRESS')
ETHEREUM_SIMULATOR_ADDRESS = os.getenv('ETHEREUM_SIMULATOR_ADDRESS')


def cycle_name(pools_1: List[int],
               pools_2: List[int],
               pools: List[Dict[str, Any]]) -> str:
    """
    Returns the name for cycle consisting of pools_1 and pools_2
    ex) UNI3ETHUSDT/UNI2ETHUSDT,
        UNI3ETHUSDT/UNI3USDCUSDT-UNI2USDCETH,
        UNI3USDCUSDT-SUS3USDCETH/SUS3USDCUSDT-SUS2USDCETH

    This is for logging/debugging purposes.
    Actual bot logic does not depend on this name.
    """

    def _pool_name(pool: Dict[str, Any]) -> str:
        exchange = pool['exchange'][:3].upper()
        version = pool['version']
        name = pool['name'].replace('/', '')
        return f'{exchange}{version}{name}'

    path_1_name = '-'.join([_pool_name(pools[i]) for i in pools_1])
    path_2_name = '-'.join([_pool_name(pools[i]) for i in pools_2])

    return f'{path_1_name}/{path_2_name}'


def dex_stream_process(publisher: aioprocessing.AioQueue,
                       chain: str,
                       trading_symbols: List[str],
                       max_swaps: int = 3):

    pools = [pool for pool in POOLS if pool['chain'] == chain]

    dex = DEX({chain: RPC_ENDPOINTS[chain]},
              {chain: TOKENS[chain]},
              pools,
              trading_symbols,
              max_swaps)

    dex_stream = DexStream(dex, WS_ENDPOINTS, publisher)

    """
    Trying to find possible cyclic arbitrage paths
    Say there are paths as such:
    - [0], [5]
    
    Path 0: Uniswap V3 ETH/USDT
    Path 5: Uniswap V2 ETH/USDT
    
    In this case, this is a possible cyclic arbitrage path:
    
    1. Uniswap V3 BUY and Uniswap V2 SELL
    BUY: Uniswap V3 USDT -> ETH
    SELL: Uniswap V2 ETH -> USDT
    
    2. Uniswap V2 BUY and Uniswap V3 SELL
    BUY: Uniswap V2 USDT -> ETH
    SELL: Uniswap V3 ETH -> USDT
    
    This type of cyclic arbitrage paths only work when two conditions are met:
    Condition #1: the first pool is different
    Condition #2: the last pool is different
    
    compare_paths is a dictionary of possible cyclic arbitrage path pairs
    """
    compare_paths = {s: {} for s in trading_symbols}

    for symbol in trading_symbols:
        pool_indexes = dex.swap_paths[symbol]['pool_indexes']
        for i in range(len(pool_indexes)):
            p_1 = pool_indexes[i]
            for j in range(i + 1, len(pool_indexes)):
                p_2 = pool_indexes[j]
                condition_1 = p_1[0] != p_2[0]
                condition_2 = p_1[-1] != p_2[-1]
                if condition_1 and condition_2:
                    name = cycle_name(p_1, p_2, pools)
                    compare_paths[symbol][name] = (i, j)

    # send compare_paths data to data_collector through publisher
    publisher.put({
        'source': 'dex',
        'type': 'setup',
        'compare_paths': compare_paths,
    })

    dex_stream.start_streams()


class Pending:

    def __init__(self):
        self.info = None

    def can_add(self):
        no_info = self.info is None
        if no_info:
            return True
        if not self.info['order_processing']:
            return True

    def get_pending(self):
        return self.info

    def add_pending(self, pending: Dict[str, Any]):
        self.info = pending

    def set_order_processing(self):
        self.info['order_processing'] = True

    def delete_pending(self):
        self.info = None


async def strategy(subscriber: aioprocessing.AioQueue,
                   chain: str,
                   max_bet_size: float,
                   target_spread: float = 0.0,
                   retry_number: int = 2,
                   debug: bool = False):

    rpc_endpoints = {chain: RPC_ENDPOINTS[chain]}
    tokens = {chain: TOKENS[chain]}
    pools = [pool for pool in POOLS if pool['chain'] == chain]
    simulator_contracts = {chain: ETHEREUM_SIMULATOR_ADDRESS}
    simulator_handlers = {chain: SIMULATION_HANDLERS[chain]}
    execution_contracts = {chain: ETHEREUM_BOT_ADDRESS}
    execution_handlers = {chain: EXECUTION_HANDLERS[chain]}

    # If .env vars relavant to InfluxDB, Telegram aren't set,
    # they'll simply stand there as placeholders, doing nothing on send calls
    influxdb = InfluxDB()
    telegram = Telegram()

    simulator = OnlineSimulator(rpc_endpoints=rpc_endpoints,
                                tokens=tokens,
                                pools=pools,
                                contracts=simulator_contracts,
                                handlers=simulator_handlers)

    execution = DexOrder(private_key=FLASHBOTS_PRIVATE_KEY,
                         signing_key=FLASHBOTS_SIGNING_KEY,
                         rpc_endpoints=rpc_endpoints,
                         tokens=tokens,
                         pools=pools,
                         contracts=execution_contracts,
                         handlers=execution_handlers)

    compare_paths = {}
    gas_info = {}

    spreads = {}
    pending = Pending()

    """
    The estimated cost of WhackAMoleBotV1 swaps
    Current gas amount is a rough estimation, for a optimized result,
    make sure to find better estimates.
    These values are overestimated for a more strict/conservative simulation result.
    """
    gas_costs = {
        0: 100000,  # base cost
        2: 40000,   # V2 1-hop cost
        3: 50000,   # V3 1-hop cost
    }

    async def _process_pending_order(pending: Pending):
        """
        1. Simulate using SimulatorV1
        2. Execute order using Flashbots
        """
        if pending.can_add():
            return

        pending_info = pending.get_pending()

        if 'block' not in gas_info or pending_info['block'] != gas_info['block']:
            return

        spread = spreads[pending_info['key']]

        if spread <= target_spread:
            pending.delete_pending()
            return

        """
        We simulate using max_fee_per_gas as the gas price
        This is to conservatively calculate the min_amount_in to be profitable
        assuming we use gas at the highest cost
        
        We also assume the quote of gas_price is at sell_price,
        which is higher than that of buy_price.
        This is another mechanism to overestimate the cost for a more realistic simulation result.
        """
        buy_price = pending_info['max_buy_sell_price'][0]
        sell_price = pending_info['max_buy_sell_price'][1]

        gas_cost = (pending_info['estimated_gas_used'] * gas_info['max_fee_per_gas']) * 10 ** (-18)  # in ETH
        gas_cost_in_usdt = gas_cost * sell_price  # the sell_price has to be price of ETH/USDT

        usdt_profit_per_unit_of_token = buy_price * (spread / 100.0)

        min_amount_in_token = gas_cost_in_usdt / usdt_profit_per_unit_of_token
        min_amount_in_usdt = min_amount_in_token * buy_price

        """
        Since we're not using flashloans yet, we can't over leverage our bets.
        The max_bet_size should be less than the amount of USDT you have in your WhackAMoleBotV1 contract.
        This would naturally mean that to cover the gas costs, we can only aim for spreads that
        are greater than other well optimized bots either 1. using flashloans, or 2. using more capital.
        """
        if min_amount_in_usdt <= max_bet_size:
            # we simulate using max_bet_size and if the result is promising we send the order to Flashbots
            usdt_decimals = simulator.tokens[chain]['USDT'][1]
            # min_amount_in = max_bet_size * 10 ** usdt_decimals
            min_amount_in = int(min_amount_in_usdt * 1.1) * 10 ** usdt_decimals
            sim_params = simulator.make_params(amount_in=min_amount_in,
                                               buy_path=pending_info['buy_path'],
                                               sell_path=pending_info['sell_path'],
                                               buy_pools=pending_info['buy_pools'],
                                               sell_pools=pending_info['sell_pools'])
            s = time.time()
            simulated_amount_out = simulator.simulate(chain, sim_params)
            e = time.time()
            simulation_took = e - s
            simulated_profit_in_usdt = (simulated_amount_out - min_amount_in) / 10 ** usdt_decimals

            final_profit = simulated_profit_in_usdt - gas_cost_in_usdt
            print(f'Simulated profit in USDT: {final_profit} (Took: {round(simulation_took, 3)} secs)')

            if final_profit > 0:
                pending.set_order_processing()

                # execute order here if program started as non-debug mode
                if not debug:
                    exe_params = execution.make_params(amount_in=min_amount_in,
                                                       buy_path=pending_info['buy_path'],
                                                       sell_path=pending_info['sell_path'],
                                                       buy_pools=pending_info['buy_pools'],
                                                       sell_pools=pending_info['sell_pools'])
                    s = time.time()
                    receipts = execution.send_order(chain=chain,
                                                    params=exe_params,
                                                    min_amount_out=int(simulated_amount_out * 0.999),  # 0.1% slippage tolerance
                                                    max_priority_fee_per_gas=gas_info['max_priority_fee_per_gas'],
                                                    max_fee_per_gas=gas_info['max_fee_per_gas'],
                                                    retry=retry_number,
                                                    block_number=gas_info['block'])
                    e = time.time()
                    execution_took = e - s
                    print(f'Execution success. Took: {round(execution_took, 3)} secs: {receipts}')

            await telegram.send(f'Block #{pending_info["block"]} {pending_info["key"]} ({round(spread, 2)}%): {final_profit} USDT')
        else:
            await telegram.send(f'Block #{pending_info["block"]} {pending_info["key"]} ({round(spread, 2)}%) min amount of USDT needed to profit: {round(min_amount_in_usdt, 3)} USDT')
        pending.delete_pending()

    # Main strategy loop
    while True:
        try:
            data = await subscriber.coro_get()
            data_type = data['type']

            if data_type == 'setup':
                # data sent from: strategies.dex_arb_base.dex_stream_process
                compare_paths = data['compare_paths']

            elif data_type == 'block':
                # data sent from: data.dex_streams.DexStream.stream_new_blocks
                gas_info = data
                print('[New block] ', gas_info)

                await _process_pending_order(pending)

            elif data_type == 'event':
                s = time.time()
                # data sent from: data.dex_streams.DexStream.stream_uniswap_v2_events/stream_uniswap_v3_events

                """
                Take 2-step operation before sending order transaction:
                
                1. Filtering: Calculate simple spread using price quotes (w/o consideration of price impact)
                              Filter out paths that had a spread over 0
                
                2. Simulating: If simple spread calculated above was above 0, it is worth simulating for price impact
                   Thus, use SimulatorV1 contract to simulate the amount_out of the potentially profitable paths
                   But to make this simpler, we simply simulate the most profitable path
                   
                This means that our simulations are done online. This will take some time, and will need to be
                ported offline to get the best performance out
                """
                max_spread = -1
                max_spread_key = ''
                max_buy_sell_price = []
                max_path_index = None

                symbol = data['symbol']
                for path_name, path_index in compare_paths[symbol].items():
                    """
                    If path_name were: UNI3ETHUSDT/UNI2ETHUSDT
                    We want to calculate the spread for both:
                    - UNI3ETHUSDT BUY -> UNI2ETHUSDT SELL
                    - UNI2ETHUSDT SELL -> UNI3ETHUSDT SELL
                    """
                    name_1, name_2 = path_name.split('/')
                    key_1 = f'{name_1}/{name_2}'
                    key_2 = f'{name_2}/{name_1}'

                    price_1 = data['price'][path_index[0]]
                    price_2 = data['price'][path_index[1]]

                    fee_1 = data['fee'][path_index[0]]
                    fee_2 = data['fee'][path_index[1]]
                    total_fee = fee_1 + fee_2

                    spread_1 = ((price_1 / price_2 - 1) - total_fee) * 100
                    spread_2 = ((price_2 / price_1 - 1) - total_fee) * 100

                    if spread_1 > max_spread:
                        max_spread_key = key_1
                        max_spread = spread_1
                        max_buy_sell_price = [price_2, price_1]
                        max_path_index = list(reversed(path_index))  # buy pool index, sell pool index

                    if spread_2 > max_spread:
                        max_spread_key = key_2
                        max_spread = spread_2
                        max_buy_sell_price = [price_1, price_2]
                        max_path_index = list(path_index)  # buy pool index, sell pool index

                    spreads[key_1] = spread_1
                    spreads[key_2] = spread_2

                await influxdb.send('DEX_ARB_BASE_ETHUSDT', spreads)
                e = time.time()
                max_msg = f'{max_spread_key}: {round(spreads[max_spread_key], 3)}%'
                print(f'[{datetime.datetime.now()}] Update took: {round(e - s, 4)} secs. {max_msg}')

                # add newly detected edge (positive spread) to pending
                # we process one edge a time to make our lives easier
                if pending.can_add() and max_spread > target_spread:
                    # before we add the new max_spread_key, first check if the spread can cover
                    # gas costs with our max_bet_size
                    buy_path = data['path'][max_path_index[0]]
                    sell_path = data['path'][max_path_index[1]]

                    """
                    Calculate the estimated_gas_used given:
                    - buy_path = [[0, 0, 5, 4, 1], [0, 0, 4, 2, 1]]
                    - sell_path = [[0, 1, 5, 2, 1], [0, 0, 0, 0, 0]]
                    """
                    estimated_gas_used = gas_costs[0]  # base cost
                    for buy_sell_path in [buy_path, sell_path]:
                        for p in buy_sell_path:
                            if sum(p) == 0:
                                continue
                            version = p[4]
                            estimated_gas_used += gas_costs[version + 2]  # V2 = 0, V3 = 1

                    """
                    The actual simulation will occur in _process_pending_order
                    This is because a newly updated block may not be avaialble yet.
                    We send a REST API call to Blocknative for gas info, so we need to wait for the response
                    to arrive before we run our simulation.
                    """
                    pending_info = {
                        'key': max_spread_key,
                        'max_buy_sell_price': max_buy_sell_price,
                        'block': data['block'],          # block at which the edge was detected
                        'cancel_at': data['block'] + 1,  # cancel after 1 block
                        'buy_path': buy_path,
                        'sell_path': sell_path,
                        'buy_pools': data['pool_indexes'][max_path_index[0]],
                        'sell_pools': data['pool_indexes'][max_path_index[1]],
                        'estimated_gas_used': estimated_gas_used,
                        'order_processing': False,
                    }
                    pending.add_pending(pending_info)
                    print(pending_info)

                await _process_pending_order(pending)

        except Exception as e:
            await influxdb.close()
            raise e


async def main():
    chain = 'ethereum'
    max_swaps = 3
    trading_symbols = ['ETH/USDT']  # other symbols won't work at the moment, because of gas cost calculations
    max_bet_size = 20000  # in USDT, because we are buying ETH with USDT
    target_spread = 0.15  # minimum target of 0.4% spread
    retry_number = 2
    debug = True  # running in debug mode won't execute orders. It'll simply send data to InfluxDB, Telegram

    queue = aioprocessing.AioQueue()

    p1 = Process(target=dex_stream_process, args=(queue, chain, trading_symbols, max_swaps,))
    p1.start()

    await strategy(queue, chain, max_bet_size, target_spread, retry_number, debug)


if __name__ == '__main__':
    asyncio.run(main())
