import os
from dotenv import load_dotenv

from addresses import (
    ETHEREUM_TOKENS,
    POLYGON_TOKENS,
    ARBITRUM_TOKENS,

    ETHEREUM_POOLS,
    POLYGON_POOLS,
    ARBITRUM_POOLS,
)

load_dotenv(override=True)

RPC_ENDPOINTS = {
    'ethereum': os.getenv('ETHEREUM_HTTP_RPC_URL'),
    'polygon': os.getenv('POLYGON_HTTP_RPC_URL'),
    'arbitrum': os.getenv('ARBITRUM_HTTP_RPC_URL'),
}

WS_ENDPOINTS = {
    'ethereum': os.getenv('ETHEREUM_WS_RPC_URL'),
    'polygon': os.getenv('POLYGON_WS_RPC_URL'),
    'arbitrum': os.getenv('ARBITRUM_WS_RPC_URL'),
}

TRADING_SYMBOLS = [
    'BTC/USDT',
    # 'ETH/USDT',
    # 'USDC/USDT',
    # 'MATIC/USDT',
]

TOKENS = {
    'ethereum': ETHEREUM_TOKENS,
    'polygon': POLYGON_TOKENS,
    'arbitrum': ARBITRUM_TOKENS,
}

POOLS = ETHEREUM_POOLS + POLYGON_POOLS + ARBITRUM_POOLS

CEX_LIST = ['binance', 'okx', 'bybit']
