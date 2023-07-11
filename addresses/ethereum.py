EXCHANGE = 'ethereum'

TOKENS = {
    'ETH': ['0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2', 18],
    'USDT': ['0xdAC17F958D2ee523a2206206994597C13D831ec7', 6],
    'USDC': ['0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48', 6],
    'BTC': ['0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599', 8],
}

columns = ['chain', 'exchange', 'version', 'name', 'address', 'fee', 'token0', 'token1']

POOLS = [
    ['uniswap', 3, 'ETH/USDT', '0x11b815efB8f581194ae79006d24E0d814B7697F6', 500, 'ETH', 'USDT'],
    ['uniswap', 3, 'USDC/USDT', '0x3416cF6C708Da44DB2624D63ea0AAef7113527C6', 100, 'USDC', 'USDT'],
    ['uniswap', 3, 'BTC/ETH', '0x4585FE77225b41b697C938B018E2Ac67Ac5a20c0', 500, 'BTC', 'ETH'],
    ['uniswap', 2, 'ETH/USDT', '0x0d4a11d5EEaaC28EC3F61d100daF4d40471f1852', 3000, 'ETH', 'USDT'],
    ['uniswap', 2, 'USDC/ETH', '0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc', 3000, 'USDC', 'ETH'],
    ['sushiswap', 3, 'ETH/USDT', '0x72c2178E082feDB13246877B5aA42ebcE1b72218', 500, 'ETH', 'USDT'],
]

POOLS = [dict(zip(columns, [EXCHANGE] + pool)) for pool in POOLS]
