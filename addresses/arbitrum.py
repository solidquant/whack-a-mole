EXCHANGE = 'arbitrum'

TOKENS = {
    'ETH': ['0x82aF49447D8a07e3bd95BD0d56f35241523fBab1', 18],
    'USDT': ['0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9', 6],
    'USDC': ['0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8', 6],
    'BTC': ['0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f', 8],
    'ARB': ['0x912CE59144191C1204E64559FE8253a0e49E6548', 18],
}

columns = ['chain', 'exchange', 'version', 'name', 'address', 'fee', 'token0', 'token1']

POOLS = [
    ['uniswap', 3, 'ETH/USDC', '0xC31E54c7a869B9FcBEcc14363CF510d1c41fa443', 500, 'ETH', 'USDC'],
    ['uniswap', 3, 'BTC/ETH', '0x2f5e87C9312fa29aed5c179E456625D79015299c', 500, 'BTC', 'ETH'],
    ['uniswap', 3, 'ETH/USDT', '0x641C00A822e8b671738d32a431a4Fb6074E5c79d', 500, 'ETH', 'USDT'],
    ['uniswap', 3, 'USDT/USDC', '0x8c9D230D45d6CfeE39a6680Fb7CB7E8DE7Ea8E71', 100, 'USDT', 'USDC'],
]

POOLS = [dict(zip(columns, [EXCHANGE] + pool)) for pool in POOLS]
