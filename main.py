import asyncio
import aioprocessing
from typing import Optional
from multiprocessing import Process

from configs import *
from data import DEX, DexStream


def dex_stream_process(publisher: aioprocessing.AioQueue, chain: Optional[str] = None):
    if not chain:
        dex = DEX(RPC_ENDPOINTS,
                  TOKENS,
                  POOLS,
                  TRADING_SYMBOLS,
                  2)
    else:
        dex = DEX({chain: RPC_ENDPOINTS[chain]},
                  {chain: TOKENS[chain]},
                  [pool for pool in POOLS if pool['chain'] == chain],
                  TRADING_SYMBOLS,
                  2)

    dex_stream = DexStream(dex, WS_ENDPOINTS, publisher)
    dex_stream.start_streams()


async def data_collector(subscriber: aioprocessing.AioQueue):
    while True:
        data = await subscriber.coro_get()

        for i in range(len(data['tag'])):
            print(data['tag'][i])
            print('- Path: ', data['path'][i])
            print('- Price: ', data['price'][i])
            print('\n')


if __name__ == '__main__':
    queue = aioprocessing.AioQueue()
    chain = 'ethereum'

    p1 = Process(target=dex_stream_process, args=(queue, chain,))
    p1.start()

    asyncio.run(data_collector(queue))
