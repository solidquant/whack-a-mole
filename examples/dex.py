from data.dex import DEX

from configs import RPC_ENDPOINTS, TOKENS, POOLS


# Initializing DEX
dex = DEX(rpc_endpoints=RPC_ENDPOINTS,
          tokens=TOKENS,
          pools=POOLS,
          trading_symbols=['ETH/USDT'],
          max_swap_number=2)

print('Chain ID: ', dex.chain_to_id)
print('Exchange ID: ', dex.exchange_to_id)
print('Token ID: ', dex.token_to_id)

# Retrieving storage data using get_index and storage_array
idx_1 = dex.get_index(chain='ethereum',
                      exchange='uniswap',
                      token0='ETH',
                      token1='USDT',
                      version=3)

idx_2 = dex.get_index(chain='ethereum',
                      exchange='uniswap',
                      token0='USDT',
                      token1='ETH',
                      version=3)

idx_1_values = dex.storage_array[idx_1]
idx_2_values = dex.storage_array[idx_2]

print(idx_1, idx_1_values)
print(idx_2, idx_2_values)