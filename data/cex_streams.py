import json
import time
import eth_abi
import asyncio
import datetime
import eth_utils
import websockets
import aioprocessing
from functools import partial
from typing import Any, Dict, Optional

from data.cex import CEX
from data.utils import reconnecting_websocket_loop


class CexStream:
    """
    WIP

    The first step to building CEX-DEX arbitrage bot is making sure DEX execution works well
    Data from CEX and DEX are updated at different time frames, as CEX data is real-time,
    whereas DEX data is updated every new block.

    Analyze how this will affect execution of CEX-DEX arbitrage
    """

    def __init__(self,
                 cex: CEX,
                 publisher: Optional[aioprocessing.AioQueue] = None,
                 debug: bool = False):

        self.cex = cex
        self.publisher = publisher
        self.debug = debug

    def publish(self, data: Any):
        if self.publisher:
            self.publisher.put(data)

    def start_stream(self):
        pass

    async def stream_binance_usdm_orderbook(self):
        async with websockets.connect('wss://fstream.binance.com/ws/') as ws:
            params = [f'{s.replace("/", "").lower()}@depth5@100ms' for s in self.cex.trading_symbols]
            subscription = {
                'method': 'SUBSCRIBE',
                'params': params,
                'id': 1,
            }
            await ws.send(json.dumps(subscription))
            _ = await ws.recv()

            while True:
                msg = await asyncio.wait_for(ws.recv(), timeout=15)
                data = json.loads(msg)
                print(data)

    async def stream_okx_usdm_orderbook(self):
        async with websockets.connect('wss://ws.okx.com:8443/ws/v5/public') as ws:
            args = [{'channel': 'books5', 'instId': f'{s.replace("/", "-")}-SWAP'} for s in self.cex.trading_symbols]
            subscription = {
                'op': 'subscribe',
                'args': args,
            }
            await ws.send(json.dumps(subscription))
            _ = await ws.recv()

            while True:
                msg = await asyncio.wait_for(ws.recv(), timeout=15)
                data = json.loads(msg)
                print(data)

    async def stream_bybit_usdm_orderbook(self):
        async with websockets.connect('wss://stream.bybit.com/v5/public/linear') as ws:
            args = [f'orderbook.50.{s.replace("/", "").upper()}' for s in self.cex.trading_symbols]
            subscription = {
                'op': 'subscribe',
                'args': args,
            }
            await ws.send(json.dumps(subscription))
            _ = await ws.recv()

            while True:
                msg = await asyncio.wait_for(ws.recv(), timeout=15)
                data = json.loads(msg)
                print(data)


if __name__ == '__main__':
    from configs import TRADING_SYMBOLS

    cex = CEX(TRADING_SYMBOLS)

    queue = aioprocessing.AioQueue()

    cex_streams = CexStream(cex, queue, False)

    asyncio.run(cex_streams.stream_okx_usdm_orderbook())
