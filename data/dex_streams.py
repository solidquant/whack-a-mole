import json
import time
import eth_abi
import asyncio
import datetime
import eth_utils
import websockets
import aioprocessing
from functools import partial
from typing import Any, Callable, Dict, Optional

from data.dex import DEX
from data.utils import reconnecting_websocket_loop


def default_message_format(symbol: str, message: Dict[str, Any]) -> Dict[str, Any]:
    """

    :param symbol: BTC/USDT, ETH/USDT, ...
    :param message: value of DEX.swap_paths[symbol]
    ex) {'path': np.ndarray, 'tag': List[str], 'tokens': np.ndarray, 'price': np.ndarray, 'fee': np.ndarray}
    :return:
    """
    return {
        'source': 'dex',
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
    dex_stream.start_streams()
