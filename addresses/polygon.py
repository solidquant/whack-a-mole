EXCHANGE = 'polygon'

TOKENS = {
    'ETH': ['0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619', 18],
    'USDT': ['0xc2132D05D31c914a87C6611C10748AEb04B58e8F', 6],
    'USDC': ['0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174', 6],
    'BTC': ['0x1BFD67037B42Cf73acF2047067bd4F2C47D9BfD6', 8],
    'MATIC': ['0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270', 18],
}

columns = ['chain', 'exchange', 'version', 'name', 'address', 'fee', 'token0', 'token1']

POOLS = [
    ['uniswap', 3, 'USDC/ETH', '0x45dDa9cb7c25131DF268515131f647d726f50608', 500, 'USDC', 'ETH'],
    ['uniswap', 3, 'BTC/ETH', '0x50eaEDB835021E4A108B7290636d62E9765cc6d7', 500, 'BTC', 'ETH'],
    ['uniswap', 3, 'USDC/USDT', '0xDaC8A8E6DBf8c690ec6815e0fF03491B2770255D', 100, 'USDC', 'USDT'],
    ['uniswap', 3, 'MATIC/USDC', '0xA374094527e1673A86dE625aa59517c5dE346d32', 500, 'MATIC', 'USDC'],
]

POOLS = [dict(zip(columns, [EXCHANGE] + pool)) for pool in POOLS]
