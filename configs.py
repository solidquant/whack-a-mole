import os
from dotenv import load_dotenv

from addresses import (
    ETHEREUM_TOKENS,
    ETHEREUM_POOLS,
    ETHEREUM_SIMULATION_HANDLERS,
    ETHEREUM_EXECUTION_HANDLERS,
)

load_dotenv(override=True)

RPC_ENDPOINTS = {
    'ethereum': os.getenv('ETHEREUM_HTTP_RPC_URL'),
}

WS_ENDPOINTS = {
    'ethereum': os.getenv('ETHEREUM_WS_RPC_URL'),
}

TOKENS = {
    'ethereum': ETHEREUM_TOKENS,
}

POOLS = ETHEREUM_POOLS

SIMULATION_HANDLERS = {
    'ethereum': ETHEREUM_SIMULATION_HANDLERS,
}

EXECUTION_HANDLERS = {
    'ethereum': ETHEREUM_EXECUTION_HANDLERS,
}
