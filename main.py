import asyncio
import aioprocessing
from multiprocessing import Process
from typing import Any, Dict, Optional, List

from configs import *
from external import InfluxDB
from data import DEX, DexStream


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
    return {
        'symbol': symbol,
        'spreads': spreads
    }


def dex_stream_process(publisher: aioprocessing.AioQueue, chain: Optional[str] = None):
    if not chain:
        dex = DEX(RPC_ENDPOINTS,
                  TOKENS,
                  POOLS,
                  TRADING_SYMBOLS)
    else:
        dex = DEX({chain: RPC_ENDPOINTS[chain]},
                  {chain: TOKENS[chain]},
                  [pool for pool in POOLS if pool['chain'] == chain],
                  TRADING_SYMBOLS)

    dex_stream = DexStream(dex, WS_ENDPOINTS, publisher, message_formatter)
    dex_stream.start_streams()


async def data_collector(subscriber: aioprocessing.AioQueue):
    influxdb = InfluxDB()

    while True:
        try:
            data = await subscriber.coro_get()
            await influxdb.send('ETHEREUM_ETHUSDT', data['spreads'])
        except Exception as e:
            print(e)
            await influxdb.close()


if __name__ == '__main__':
    queue = aioprocessing.AioQueue()
    chain = 'ethereum'

    p1 = Process(target=dex_stream_process, args=(queue, chain,))
    p1.start()

    asyncio.run(data_collector(queue))
