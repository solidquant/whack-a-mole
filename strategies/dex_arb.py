import asyncio
import numpy as np
import aioprocessing
from multiprocessing import Process
from typing import Any, Dict, Optional, List

from configs import *
from external import InfluxDB
from data import DexBase, DEX, DexStream


def calculate_spreads(data: Dict[str, List[Any]]):
    keys = list(data.keys())
    spreads = {}

    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            path1 = keys[i]
            path2 = keys[j]
            key1 = '/'.join([path1, path2])
            key2 = '/'.join([path2, path1])
            if key1 not in spreads and key2 not in spreads:
                price1, fee1 = data[path1]
                price2, fee2 = data[path2]
                fee = 1 - ((1 - fee1) * (1 - fee2))
                spread1 = ((price1 * (1 - fee) / price2) - 1) * 100
                spread2 = ((price2 * (1 - fee) / price1) - 1) * 100
                spreads[key1] = spread1
                spreads[key2] = spread2

    return spreads


def message_formatter(symbol: str, message: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(
        zip(
            message['tag'],
            [
                [message['price'][i], message['fee'][i]]
                for i in range(len(message['tag']))
            ]
        )
    )
    spreads = calculate_spreads(data)

    tag_path = {
        message['tag'][i]: {
            'path': message['path'][i].tolist(),
            'pool_index': message['pool_indexes'][i],
        }
        for i in range(len(message['tag']))
    }

    return {
        'symbol': symbol,
        'path': tag_path,
        'spreads': spreads,
    }


def dex_stream_process(publisher: aioprocessing.AioQueue,
                       chain: Optional[str] = None,
                       trading_symbols: List[str] = TRADING_SYMBOLS,
                       max_swaps: int = 3):
    if not chain:
        dex = DEX(RPC_ENDPOINTS,
                  TOKENS,
                  POOLS,
                  trading_symbols,
                  max_swaps)
    else:
        dex = DEX({chain: RPC_ENDPOINTS[chain]},
                  {chain: TOKENS[chain]},
                  [pool for pool in POOLS if pool['chain'] == chain],
                  trading_symbols,
                  max_swaps)

    dex_stream = DexStream(dex, WS_ENDPOINTS, publisher, message_formatter)
    dex_stream.start_streams()


def path_debug_message(dex: DexBase, path: List[List[int]]) -> str:
    full_path_string = ''
    for p in path:
        if np.sum(p) != 0:
            chain = dex.chains_list[p[0]].capitalize()
            exchange = dex.exchanges_list[p[1]].capitalize()
            token_in = dex.tokens_list[p[2]]
            token_out = dex.tokens_list[p[3]]
            version = 2 if p[4] == 0 else 3
            path_string = f'{chain} {exchange} V{version}: {token_in} -> {token_out}'
            full_path_string = f'{full_path_string}{path_string}\n'
    return full_path_string.rstrip()


async def data_collector(subscriber: aioprocessing.AioQueue,
                         chain: Optional[str] = None,
                         trading_symbols: List[str] = TRADING_SYMBOLS,
                         max_swaps: int = 3):

    influxdb = InfluxDB()

    if not chain:
        dex = DexBase(RPC_ENDPOINTS,
                      TOKENS,
                      POOLS,
                      trading_symbols,
                      max_swaps)
    else:
        dex = DexBase({chain: RPC_ENDPOINTS[chain]},
                      {chain: TOKENS[chain]},
                      [pool for pool in POOLS if pool['chain'] == chain],
                      trading_symbols,
                      max_swaps)

    while True:
        try:
            data = await subscriber.coro_get()
            # await influxdb.send('ETHUSDT_2HOP', data['spreads'])

            max_key = max(data['spreads'], key=data['spreads'].get)
            sell_path = data['path'][max_key.split('/')[0]]
            buy_path = data['path'][max_key.split('/')[1]]

            print(f'{max_key}: {data["spreads"][max_key]}')
            print('BUY')
            print(path_debug_message(dex, buy_path['path']))
            print('SELL')
            print(path_debug_message(dex, sell_path['path']))
            print('\n')
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
