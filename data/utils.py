import random
import asyncio
import websockets
from typing import Any, Callable, Dict


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


def calculate_next_block_base_fee(block: Dict[str, Any]):
    base_fee = int(block['baseFeePerGas'], base=16)
    gas_used = int(block['gasUsed'], base=16)
    gas_limit = int(block['gasLimit'], base=16)

    target_gas_used = gas_limit / 2
    target_gas_used = 1 if target_gas_used == 0 else target_gas_used

    if gas_used > target_gas_used:
        new_base_fee = base_fee + ((base_fee * (gas_used - target_gas_used)) / target_gas_used) / 8
    else:
        new_base_fee = base_fee - ((base_fee * (target_gas_used - gas_used)) / target_gas_used) / 8

    return int(new_base_fee + random.randint(0, 9))
