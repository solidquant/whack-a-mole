import asyncio
import aioprocessing
from multiprocessing import Process

from configs import *
from external import InfluxDB
from data import DEX, DexStream


def dex_stream_process(publisher: aioprocessing.AioQueue):
    dex = DEX(RPC_ENDPOINTS,
              TOKENS,
              POOLS,
              TRADING_SYMBOLS)

    dex_stream = DexStream(dex, WS_ENDPOINTS, publisher)
    dex_stream.start_streams()


async def data_collector(subscriber: aioprocessing.AioQueue):
    influxdb = InfluxDB()

    while True:
        try:
            data = await subscriber.coro_get()

            price = dict(zip(data['tag'], data['price']))
            fee = dict(zip(data['tag'], data['fee']))

            await influxdb.send('monitoring_price', price)
            await influxdb.send('monitoring_fee', fee)
        except Exception as e:
            print(e)
            await influxdb.close()


if __name__ == '__main__':
    queue = aioprocessing.AioQueue()

    p1 = Process(target=dex_stream_process, args=(queue,))
    p1.start()

    asyncio.run(data_collector(queue))
