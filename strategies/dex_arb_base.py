import asyncio
import aioprocessing
from multiprocessing import Process
from typing import Any, Dict, Optional, List

from configs import *
from data import DEX, DexStream
from external import InfluxDB, Telegram


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
                       trading_symbols: List[str] = TRADING_SYMBOLS,
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
            pool_indexes_2 = pool_indexes[i + 1:]
            for j in range(len(pool_indexes_2)):
                p_2 = pool_indexes_2[j]
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


async def data_collector(subscriber: aioprocessing.AioQueue,
                         chain: Optional[str] = None,
                         trading_symbols: List[str] = TRADING_SYMBOLS,
                         max_swaps: int = 3):

    """
    Use env variables from .env
    """
    influxdb = InfluxDB()
    telegram = Telegram()

    compare_paths = {}
    gas_info = {}
    pending = None

    """
    The cost of WhachAMoleBotV1 n-hop swaps
    """
    contract_gas_costs = {
        2: 187000,
        3: 221000,

    }

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
            elif data_type == 'event':
                # data sent from: data.dex_streams.DexStream.stream_uniswap_v2_events/stream_uniswap_v3_events
                print(data)

            # await influxdb.send('ETHUSDT_2HOP', data['spreads'])
            print(compare_paths)
        except Exception as e:
            print(e)
            await influxdb.close()


async def main():
    chain = 'ethereum'
    max_swaps = 2
    trading_symbols = ['ETH/USDT']

    queue = aioprocessing.AioQueue()

    p1 = Process(target=dex_stream_process, args=(queue, chain, trading_symbols, max_swaps,))
    p1.start()

    await data_collector(queue, chain, trading_symbols, max_swaps)


if __name__ == '__main__':
    asyncio.run(main())
