import asyncio
import aioprocessing
from multiprocessing import Process

from data.dex import DEX
from data.dex_streams import DexStream

from configs import (
    RPC_ENDPOINTS,
    WS_ENDPOINTS,
    TOKENS,
    POOLS,
)

# Settings
chain = 'ethereum'
rpc_endpoints = {chain: RPC_ENDPOINTS[chain]}
ws_endpoints = {chain: WS_ENDPOINTS[chain]}
tokens = {chain: TOKENS[chain]}
pools = [pool for pool in POOLS if pool['chain'] == chain]
trading_symbols = ['ETH/USDT']


def dex_stream_process(publisher: aioprocessing.AioQueue):
    dex = DEX(rpc_endpoints=rpc_endpoints,
              tokens=tokens,
              pools=pools,
              trading_symbols=trading_symbols,
              max_swap_number=2)

    dex_stream = DexStream(dex=dex,
                           ws_endpoints=ws_endpoints,
                           publisher=publisher)
    dex_stream.start_streams()


async def strategy(subscriber: aioprocessing.AioQueue):
    while True:
        data = await subscriber.coro_get()
        print(data)


if __name__ == '__main__':
    # Initializing DEX
    dex = DEX(rpc_endpoints=rpc_endpoints,
              tokens=tokens,
              pools=pools,
              trading_symbols=trading_symbols,
              max_swap_number=2)

    print('Chain ID: ', dex.chain_to_id)
    print('Exchange ID: ', dex.exchange_to_id)
    print('Token ID: ', dex.token_to_id)

    # Retrieving storage data using get_index and storage_array
    idx_1 = dex.get_index(chain='ethereum',
                          exchange='uniswap',
                          token0='ETH',
                          token1='USDT',
                          version=3)

    idx_2 = dex.get_index(chain='ethereum',
                          exchange='uniswap',
                          token0='USDT',
                          token1='ETH',
                          version=3)

    idx_1_values = dex.storage_array[idx_1]
    idx_2_values = dex.storage_array[idx_2]

    print(idx_1, idx_1_values)
    print(idx_2, idx_2_values)

    # Starting DexStream
    queue = aioprocessing.AioQueue()

    # Start a process of DEX streams
    p = Process(target=dex_stream_process, args=(queue,))
    p.start()

    asyncio.run(strategy(queue))
