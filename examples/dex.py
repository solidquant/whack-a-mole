import numpy as np

from data.dex import DEX
from configs import RPC_ENDPOINTS, TOKENS, POOLS


if __name__ == '__main__':
    dex = DEX(RPC_ENDPOINTS,
              TOKENS,
              POOLS,
              ['ETH/USDT', 'BTC/USDT'])

    # Retrieving the price of a specific pool
    idx = dex.get_index('ethereum', 'uniswap', 'ETH', 'USDT', 3)
    print(idx)

    price, fee = dex.get_price(*idx)
    print(price, fee)

    # Retrieving price of multiple swap paths
    btc_price = dex.swap_paths['BTC/USDT']['price']
    btc_fee = dex.swap_paths['BTC/USDT']['fee']

    print(btc_price)
    print(btc_fee)

    # Get the lowest price path: best for BUY orders
    buy_price = np.min(btc_price)

    # Get the highest price path: best for SELL orders
    sell_price = np.max(btc_price)

    # Calculate the spread between the two paths
    buy_sell_spread = (sell_price / buy_price - 1) * 100
    print(f'Buy-Sell price spread: {buy_sell_spread}%')
