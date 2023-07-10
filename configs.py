import os
from dotenv import load_dotenv

load_dotenv(override=True)

RPC_ENDPOINTS = {
    'ethereum': os.getenv('ETHEREUM_HTTP_RPC_URL'),
    'polygon': os.getenv('POLYGON_HTTP_RPC_URL'),
}

WS_ENDPOINTS = {
    'ethereum': os.getenv('ETHEREUM_WS_RPC_URL'),
    'polygon': os.getenv('POLYGON_WS_RPC_URL'),
}

TRADING_SYMBOLS = [
    # 'BTC/USDT',
    'ETH/USDT',
    # 'USDC/USDT',
    # 'MATIC/USDT',
]

TOKENS = {
    'ethereum': {
        'ETH': ['0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2', 18],
        'USDT': ['0xdAC17F958D2ee523a2206206994597C13D831ec7', 6],
        # 'USDC': ['0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48', 6],
        # 'BTC': ['0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599', 8],
    },
    # 'polygon': {
    #     'ETH': ['0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619', 18],
    #     'USDT': ['0xc2132D05D31c914a87C6611C10748AEb04B58e8F', 6],
    #     'USDC': ['0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174', 6],
    #     'BTC': ['0x1BFD67037B42Cf73acF2047067bd4F2C47D9BfD6', 8],
    #     'MATIC': ['0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270', 18],
    # },
}

POOLS = [
    {
        'chain': 'ethereum',
        'exchange': 'uniswap',
        'version': 3,
        'name': 'ETH/USDT',
        'address': '0x11b815efB8f581194ae79006d24E0d814B7697F6',
        'fee': 500,
        'token0': 'ETH',
        'token1': 'USDT',
    },

    # {
    #     'chain': 'ethereum',
    #     'exchange': 'uniswap',
    #     'version': 3,
    #     'name': 'USDC/USDT',
    #     'address': '0x3416cF6C708Da44DB2624D63ea0AAef7113527C6',
    #     'fee': 100,
    #     'token0': 'USDC',
    #     'token1': 'USDT',
    # }, {
    #     'chain': 'ethereum',
    #     'exchange': 'uniswap',
    #     'version': 3,
    #     'name': 'BTC/ETH',
    #     'address': '0x4585FE77225b41b697C938B018E2Ac67Ac5a20c0',
    #     'fee': 500,
    #     'token0': 'BTC',
    #     'token1': 'ETH',
    # }, {
    #     'chain': 'ethereum',
    #     'exchange': 'uniswap',
    #     'version': 2,
    #     'name': 'ETH/USDT',
    #     'address': '0x0d4a11d5EEaaC28EC3F61d100daF4d40471f1852',
    #     'fee': 3000,
    #     'token0': 'ETH',
    #     'token1': 'USDT',
    # }, {
    #     'chain': 'ethereum',
    #     'exchange': 'uniswap',
    #     'version': 2,
    #     'name': 'USDC/ETH',
    #     'address': '0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc',
    #     'fee': 3000,
    #     'token0': 'USDC',
    #     'token1': 'ETH',
    # }, {
    #     'chain': 'ethereum',
    #     'exchange': 'sushiswap',
    #     'version': 3,
    #     'name': 'ETH/USDT',
    #     'address': '0x72c2178E082feDB13246877B5aA42ebcE1b72218',
    #     'fee': 500,
    #     'token0': 'ETH',
    #     'token1': 'USDT',
    # },

    # {
    #     'chain': 'polygon',
    #     'exchange': 'uniswap',
    #     'version': 3,
    #     'name': 'USDC/ETH',
    #     'address': '0x45dDa9cb7c25131DF268515131f647d726f50608',
    #     'fee': 500,
    #     'token0': 'USDC',
    #     'token1': 'ETH',
    # }, {
    #     'chain': 'polygon',
    #     'exchange': 'uniswap',
    #     'version': 3,
    #     'name': 'BTC/ETH',
    #     'address': '0x50eaEDB835021E4A108B7290636d62E9765cc6d7',
    #     'fee': 500,
    #     'token0': 'BTC',
    #     'token1': 'ETH',
    # }, {
    #     'chain': 'polygon',
    #     'exchange': 'uniswap',
    #     'version': 3,
    #     'name': 'USDC/USDT',
    #     'address': '0xDaC8A8E6DBf8c690ec6815e0fF03491B2770255D',
    #     'fee': 100,
    #     'token0': 'USDC',
    #     'token1': 'USDT',
    # }, {
    #     'chain': 'polygon',
    #     'exchange': 'uniswap',
    #     'version': 3,
    #     'name': 'MATIC/USDC',
    #     'address': '0xA374094527e1673A86dE625aa59517c5dE346d32',
    #     'fee': 500,
    #     'token0': 'MATIC',
    #     'token1': 'USDC',
    # },
]