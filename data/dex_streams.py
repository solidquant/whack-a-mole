import os
import json
import time
import eth_abi
import asyncio
import aiohttp
import requests
import datetime
import eth_utils
import websockets
import aioprocessing
from web3 import Web3
from functools import partial
from dotenv import load_dotenv
from typing import Any, Callable, Dict, Optional

from data.dex import DEX
from data.utils import reconnecting_websocket_loop, calculate_next_block_base_fee

load_dotenv(override=True)

BLOCKNATIVE_API_KEY = os.getenv('BLOCKNATIVE_API_KEY')


def default_message_format(symbol: str, message: Dict[str, Any]) -> Dict[str, Any]:
    """

    :param symbol: BTC/USDT, ETH/USDT, ...
    :param message: value of DEX.swap_paths[symbol]
    ex) {'path': np.ndarray,
         'pool_indexes': List[List[int]],
         'tag': List[str],
         'tokens': np.ndarray,
         'price': np.ndarray,
         'fee': np.ndarray}
    :return:
    """
    return {
        'source': 'dex',
        'path': message['path'].tolist(),
        'pool_indexes': message['pool_indexes'],
        'symbol': symbol,
        'tag': message['tag'],
        'price': message['price'].tolist(),
        'fee': message['fee'].tolist(),
    }


class DexStream:

    def __init__(self,
                 dex: DEX,
                 ws_endpoints: Dict[str, str],
                 publisher: Optional[aioprocessing.AioQueue] = None,
                 message_formatter: Callable = default_message_format,
                 debug: bool = False):
        """
        :param dex: DEX instance

        :param ws_endpoints:
        ex) {'ethereum': '<WS URL>'}

        :param publisher: an instance of aioprocessing.AioQueue, used to send processed
                          market data to strategy

        :param message_formatter: is used to format message sent through the publisher
                                  this data will be accessed from the main process
        """
        self.dex = dex
        self.ws_endpoints = ws_endpoints
        self.publisher = publisher
        self.message_formatter = message_formatter
        self.debug = debug

    def publish(self, data: Any):
        if self.publisher:
            self.publisher.put(data)

    def start_streams(self):
        streams = []

        for chain in self.dex.chains_list:
            v2_stream = reconnecting_websocket_loop(
                partial(self.stream_uniswap_v2_events, chain),
                tag=f'{chain.upper()}_V2'
            )
            v3_stream = reconnecting_websocket_loop(
                partial(self.stream_uniswap_v3_events, chain),
                tag=f'{chain.upper()}_V3'
            )
            streams.extend([asyncio.ensure_future(f) for f in [v2_stream, v3_stream]])

        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.wait(streams))

    async def stream_uniswap_v2_events(self, chain: str):
        filtered_pools = [
            pool for pool in self.dex.pools
            if pool['chain'] == chain and pool['version'] == 2
        ]
        pools = {pool['address'].lower(): pool for pool in filtered_pools}

        sync_event_selector = self.dex.web3[chain].keccak(
            text='Sync(uint112,uint112)'
        ).hex()

        async with websockets.connect(self.ws_endpoints[chain]) as ws:
            subscription = {
                'json': '2.0',
                'id': 1,
                'method': 'eth_subscribe',
                'params': [
                    'logs',
                    {'topics': [sync_event_selector]}
                ]
            }

            await ws.send(json.dumps(subscription))
            _ = await ws.recv()

            while True:
                msg = await asyncio.wait_for(ws.recv(), timeout=60 * 10)
                event = json.loads(msg)['params']['result']
                address = event['address'].lower()

                if address in pools:
                    s = time.time()
                    pool = pools[address]
                    data = eth_abi.decode_abi(
                        ['uint112', 'uint112'],
                        eth_utils.decode_hex(event['data'])
                    )

                    chain = pool['chain']
                    exchange = pool['exchange']
                    token0 = pool['token0']
                    token1 = pool['token1']

                    self.dex.update_reserves(chain, exchange, token0, token1, data[0], data[1])

                    symbols = self.dex.get_symbols_to_update(token0, token1)
                    for symbol in symbols:
                        self.dex.update_price_for_symbol(chain, symbol)
                        self.publish(self.message_formatter(symbol, self.dex.swap_paths[symbol]))
                    e = time.time()

                    if self.debug:
                        dbg_msg = self.dex.debug_message(chain, exchange, token0, token1, 2)
                        print(f'{datetime.datetime.now()} {dbg_msg} -> Update took: {e - s} seconds')

    async def stream_uniswap_v3_events(self, chain: str):
        filtered_pools = [
            pool for pool in self.dex.pools
            if pool['chain'] == chain and pool['version'] == 3
        ]
        pools = {pool['address'].lower(): pool for pool in filtered_pools}

        swap_event_selector = self.dex.web3[chain].keccak(
            text='Swap(address,address,int256,int256,uint160,uint128,int24)'
        ).hex()

        async with websockets.connect(self.ws_endpoints[chain]) as ws:
            subscription = {
                'json': '2.0',
                'id': 1,
                'method': 'eth_subscribe',
                'params': [
                    'logs',
                    {'topics': [swap_event_selector]}
                ]
            }

            await ws.send(json.dumps(subscription))
            _ = await ws.recv()

            while True:
                msg = await asyncio.wait_for(ws.recv(), timeout=60 * 10)
                event = json.loads(msg)['params']['result']
                address = event['address'].lower()

                if address in pools:
                    # we don't need the sender, recipient data in topics
                    s = time.time()
                    pool = pools[address]
                    data = eth_abi.decode_abi(
                        ['int256', 'int256', 'uint160', 'uint128', 'int24'],
                        eth_utils.decode_hex(event['data'])
                    )

                    chain = pool['chain']
                    exchange = pool['exchange']
                    token0 = pool['token0']
                    token1 = pool['token1']

                    self.dex.update_sqrt_price(chain, exchange, token0, token1, data[2])

                    symbols = self.dex.get_symbols_to_update(token0, token1)
                    for symbol in symbols:
                        self.dex.update_price_for_symbol(chain, symbol)
                        self.publish(self.message_formatter(symbol, self.dex.swap_paths[symbol]))
                    e = time.time()

                    if self.debug:
                        dbg_msg = self.dex.debug_message(chain, exchange, token0, token1, 3)
                        print(f'{datetime.datetime.now()} {dbg_msg} -> Update took: {e - s} seconds')

    async def stream_new_blocks(self, chain: str):
        """
        Retrieves new blocks and calculates base fees accordingly
        Base fees are calculated adhering to the EIP-1559 implementation and
        max_price, max_priority_fee_per_gas, max_fee_per_gas are retrieved using Blocknative's gas estimator endpoint

        - Ethereum: https://api.blocknative.com/gasprices/blockprices?chainId=1
        - Polygon: https://api.blocknative.com/gasprices/blockprices?chainId=137
        """
        w3 = Web3(Web3.AsyncHTTPProvider(self.dex.rpc_endpoints[chain]))

        async with websockets.connect(self.ws_endpoints[chain]) as ws:
            subscription = {
                'json': '2.0',
                'id': 1,
                'method': 'eth_subscribe',
                'params': ['newHeads']
            }

            await ws.send(json.dumps(subscription))
            _ = await ws.recv()

            while True:
                msg = await asyncio.wait_for(ws.recv(), timeout=60 * 10)
                block = json.loads(msg)['params']['result']
                base_fee = calculate_next_block_base_fee(block)
                print(base_fee / 10 ** 9)

                """
                For Ethereum and Polygon, use gas price estimation tools provided by Blocknative
                """
                if chain in ['ethereum', 'polygon'] and BLOCKNATIVE_API_KEY:
                    chain_id = 1 if 'ethereum' else 137
                    headers = {'Authorization': BLOCKNATIVE_API_KEY}
                    async with aiohttp.ClientSession(headers=headers) as session:
                        async with session.get(f'https://api.blocknative.com/gasprices/blockprices?chainId={chain_id}') as r:
                            res = await r.json()
                            estimated_price = res['blockPrices'][0]['estimatedPrices'][0]

                            max_price = res['maxPrice']
                            max_priority_fee_per_gas = estimated_price['maxPriorityFeePerGas']
                            max_fee_per_gas = estimated_price['maxFeePerGas']


if __name__ == '__main__':
    from configs import (
        RPC_ENDPOINTS,
        WS_ENDPOINTS,
        TOKENS,
        POOLS,
        TRADING_SYMBOLS,
    )

    dex = DEX(RPC_ENDPOINTS,
              TOKENS,
              POOLS,
              TRADING_SYMBOLS)

    queue = aioprocessing.AioQueue()

    dex_stream = DexStream(dex, WS_ENDPOINTS, queue, default_message_format, False)
    # dex_stream.start_streams()

    asyncio.run(dex_stream.stream_new_blocks('ethereum'))
