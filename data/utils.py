import asyncio
import websockets
from typing import Callable


async def reconnecting_websocket_loop(stream_fn: Callable, tag: str):
    while True:
        try:
            await stream_fn()

        except (websockets.ConnectionClosedError, websockets.ConnectionClosedOK) as e:
            print(f'{tag} websocket connection closed: {e}')
            print('Reconnecting...')
            await asyncio.sleep(2)

        except Exception as e:
            print(f'An error has occurred with {tag} websocket: {e}')
            break
