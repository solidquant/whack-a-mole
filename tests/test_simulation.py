import json
import eth_abi
import datetime
from web3 import Web3
from unittest import TestCase
from eth_account.account import Account

from simulation import UniswapV2Simulator, UniswapV3Simulator

POOL_V2_ABI = json.load(open('../abi/UniswapV2Pool.json', 'r'))
POOL_V3_ABI = json.load(open('../abi/UniswapV3Pool.json', 'r'))

ROUTER2_ABI = json.load(open('../abi/UniswapV2Router2.json', 'r'))
QUOTER2_ABI = json.load(open('../abi/UniswapV3Quoter2.json', 'r'))

SWAP_ROUTER2_ABI = json.load(open('../abi/UniswapV3SwapRouter2.json', 'r'))

WETH_ABI = json.load(open('../abi/WETH.json', 'r'))
ERC20_ABI = json.load(open('../abi/ERC20.json', 'r'))


class SimulationTests(TestCase):
    """
    Simulation tests are dependent on mainnet hardforks
    Make sure to have a local mainnet hardfork running before testing

    For people using Foundry, running Anvil Ethereum mainnet hardfork is easy:

    anvil --fork-url <RPC_URL>
    """

    HARDFORK_RPC_URL = 'http://localhost:8545'

    # Private key is from Anvil
    TEST_PRIVATE_KEY = '0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80'

    WETH = '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'
    USDT = '0xdAC17F958D2ee523a2206206994597C13D831ec7'
    DAI = '0x6B175474E89094C44Da98b954EedeAC495271d0F'

    WETH_DECIMALS = 18
    USDT_DECIMALS = 6
    DAI_DECIMALS = 18

    POOL_V3_FEE = 500

    # WETH-USDT Uniswap V2 pool
    POOL_V2 = '0x0d4a11d5EEaaC28EC3F61d100daF4d40471f1852'
    ROUTER2 = '0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'

    # WETH-USDT Uniswap V3 pool
    # POOL_V3 = '0x11b815efB8f581194ae79006d24E0d814B7697F6'
    POOL_V3 = '0xC2e9F25Be6257c210d7Adf0D4Cd6E3E881ba25f8'
    QUOTER2 = '0x61fFE014bA17989E743c5F6cB21bF9697530B21e'
    SWAP_ROUTER = '0xE592427A0AEce92De3Edee1F18E0157C05861564'

    # WhackAMoleBotV1
    BOT = '0x46d4674578a2daBbD0CEAB0500c6c7867999db34'

    def setUp(self):
        self.signer = Account.from_key(self.TEST_PRIVATE_KEY)

        self.web3 = Web3(Web3.HTTPProvider(self.HARDFORK_RPC_URL))

        self.weth = self.web3.eth.contract(address=self.WETH, abi=WETH_ABI)
        self.usdt = self.web3.eth.contract(address=self.USDT, abi=ERC20_ABI)

        # V2 contracts
        self.pool_v2 = self.web3.eth.contract(address=self.POOL_V2, abi=POOL_V2_ABI)
        self.router2 = self.web3.eth.contract(address=self.ROUTER2, abi=ROUTER2_ABI)

        # V3 contracts
        self.pool_v3 = self.web3.eth.contract(address=self.POOL_V3, abi=POOL_V3_ABI)
        self.quoter2 = self.web3.eth.contract(address=self.QUOTER2, abi=QUOTER2_ABI)
        self.swap_router = self.web3.eth.contract(address=self.SWAP_ROUTER, abi=SWAP_ROUTER2_ABI)

        self.sim_v2 = UniswapV2Simulator()
        self.sim_v3 = UniswapV3Simulator()

    # def test_sim_v2_get_amount_out(self):
    #     token_in = self.WETH
    #     token0 = self.pool_v2.functions.token0().call()
    #     token0_in = token_in == token0
    #
    #     reserve0, reserve1, _ = self.pool_v2.functions.getReserves().call()
    #
    #     if token0_in:
    #         reserve_in, reserve_out = reserve0, reserve1
    #     else:
    #         reserve_in, reserve_out = reserve1, reserve0
    #
    #     amount_in = self.web3.toWei(1, 'ether')
    #
    #     # First check that the simulation results equal that of Router2
    #     router_amount_out = self.router2.functions.getAmountOut(
    #         amount_in, reserve_in, reserve_out
    #     ).call()
    #
    #     sim_amount_out = self.sim_v2.get_amount_out(
    #         amount_in, reserve_in, reserve_out
    #     )
    #
    #     self.assertEqual(router_amount_out, sim_amount_out)
    #
    #     # Next, check that swapping 1 WETH does in fact result in amount_out USDT
    #     nonce = self.web3.eth.get_transaction_count(self.signer.address)
    #     approve_transaction = self.weth.functions.approve(self.ROUTER2, amount_in).build_transaction({
    #         'from': self.signer.address,
    #         'chainId': 1,
    #         'nonce': nonce,
    #         'gas': 200000,
    #         'maxFeePerGas': self.web3.toWei(100, 'gwei'),
    #         'maxPriorityFeePerGas': self.web3.toWei(50, 'gwei'),
    #     })
    #     signed = self.signer.sign_transaction(approve_transaction)
    #     tx_hash = self.web3.eth.send_raw_transaction(signed.rawTransaction)
    #     _ = self.web3.eth.get_transaction(tx_hash)
    #
    #     allowance_amount = self.weth.functions.allowance(self.signer.address, self.ROUTER2).call()
    #     self.assertEqual(amount_in, allowance_amount)  # approve was successful
    #
    #     usdt_balance_before = self.usdt.functions.balanceOf(self.signer.address).call()
    #
    #     path = [self.WETH, self.USDT]
    #     nonce = self.web3.eth.get_transaction_count(self.signer.address)
    #     # I'm not including slippage tolerance here, so this transaction
    #     # will most likely fail in real life scenarios unless your transaction is at the top of the block
    #     swap_transaction = self.router2.functions.swapExactTokensForTokens(
    #         amount_in,
    #         sim_amount_out,
    #         path,
    #         self.signer.address,
    #         int(datetime.datetime.now().timestamp()) + 60000  # 1 minute
    #     ).build_transaction({
    #         'from': self.signer.address,
    #         'chainId': 1,
    #         'nonce': nonce,
    #         'gas': 200000,
    #         'maxFeePerGas': self.web3.toWei(100, 'gwei'),
    #         'maxPriorityFeePerGas': self.web3.toWei(50, 'gwei'),
    #     })
    #     signed = self.signer.sign_transaction(swap_transaction)
    #     tx_hash = self.web3.eth.send_raw_transaction(signed.rawTransaction)
    #     _ = self.web3.eth.get_transaction(tx_hash)
    #
    #     usdt_balance_after = self.usdt.functions.balanceOf(self.signer.address).call()
    #
    #     self.assertEqual(usdt_balance_before + sim_amount_out, usdt_balance_after)

    def test_sim_v3_get_amount_out(self):
        """
        Currently only implements single tick swap
        """
        import math

        # # Wrap ETH to WETH
        # nonce = self.web3.eth.get_transaction_count(self.signer.address)
        # transaction = {
        #     'from': self.signer.address,
        #     'to': self.WETH,
        #     'value': self.web3.to_wei(100, 'ether'),
        #     'chainId': 1,
        #     'nonce': nonce,
        #     'gas': 200000,
        #     'maxFeePerGas': self.web3.to_wei(100, 'gwei'),  # set at randomly high gas price
        #     'maxPriorityFeePerGas': self.web3.to_wei(50, 'gwei'),  # set at random
        # }
        # signed = self.signer.sign_transaction(transaction)
        # tx_hash = self.web3.eth.send_raw_transaction(signed.rawTransaction)
        # _ = self.web3.eth.get_transaction(tx_hash)
        #
        # weth_balance = self.weth.functions.balanceOf(self.signer.address).call()
        # print('WETH: ', weth_balance)

        # Approve WETH
        nonce = self.web3.eth.get_transaction_count(self.signer.address)
        approve_transaction = self.weth.functions.approve(
            self.pool_v3.address, 100 * 10 ** 18
        ).build_transaction({
            'from': self.signer.address,
            'chainId': 1,
            'nonce': nonce,
            'gas': 200000,
            'maxFeePerGas': self.web3.to_wei(100, 'gwei'),
            'maxPriorityFeePerGas': self.web3.to_wei(50, 'gwei'),
        })
        signed = self.signer.sign_transaction(approve_transaction)
        tx_hash = self.web3.eth.send_raw_transaction(signed.rawTransaction)
        _ = self.web3.eth.get_transaction(tx_hash)

        allowance = self.weth.functions.allowance(self.signer.address, self.SWAP_ROUTER).call()
        print('WETH allowance: ', allowance)


        token_in = self.WETH
        token0 = self.pool_v3.functions.token0().call()
        token0_in = token_in == token0

        slot0 = self.pool_v3.functions.slot0().call()
        tick_spacing = self.pool_v3.functions.tickSpacing().call()
        liquidity = self.pool_v3.functions.liquidity().call()

        sqrt_price, current_tick, *_ = slot0

        upper_tick_idx = tick_spacing * (current_tick // tick_spacing + 1)
        lower_tick_idx = tick_spacing * (current_tick // tick_spacing)

        print(upper_tick_idx, current_tick, lower_tick_idx)

        print(slot0)
        print(tick_spacing)
        print(liquidity)

        price_range = self.sim_v3.tick_to_price_range(current_tick, tick_spacing, self.DAI_DECIMALS, self.WETH_DECIMALS, token0_in)
        print('Price range: ', price_range)

        curr_price = self.sim_v3.sqrtx96_to_price(sqrt_price, self.DAI_DECIMALS, self.WETH_DECIMALS, token0_in)
        print('Curr price: ', curr_price)

        sqrt_price_tick = self.sim_v3.sqrtx96_to_tick(sqrt_price)
        print(sqrt_price_tick)

        p = self.sim_v3.tick_to_price(sqrt_price_tick, self.DAI_DECIMALS, self.WETH_DECIMALS)
        print(p)

        target_price = self.sim_v3.tick_to_price(lower_tick_idx, self.DAI_DECIMALS, self.WETH_DECIMALS)
        print('target price: ', 1 / target_price)
        price_diff = (1 / target_price) - curr_price
        price_diff_liq = price_diff * liquidity
        print(price_diff_liq / 10 ** self.DAI_DECIMALS)



        nonce = self.web3.eth.get_transaction_count(self.signer.address)
        params = (
            self.WETH,
            self.DAI,
            3000,
            self.signer.address,
            99999999999999999,
            1 * 10 ** self.WETH_DECIMALS,
            0,
            0,
        )
        swap_transaction = self.pool_v3.functions.swap(
            self.signer.address,
            False,
            1 * 10 ** 18,
            4400000000,
            ''
        ).build_transaction({
            'from': self.signer.address,
            'chainId': 1,
            'nonce': nonce,
            'gas': 1200000,
            'maxFeePerGas': self.web3.to_wei(100, 'gwei'),
            'maxPriorityFeePerGas': self.web3.to_wei(50, 'gwei'),
        })
        print(swap_transaction)
        signed = self.signer.sign_transaction(swap_transaction)
        tx_hash = self.web3.eth.send_raw_transaction(signed.rawTransaction)
        tx = self.web3.eth.get_transaction(tx_hash)

        replay_tx = {
            'to': tx['to'],
            'from': tx['from'],
            'value': tx['value'],
            'data': tx['input'],
        }

        self.web3.eth.call(replay_tx, tx.blockNumber - 1)

        print('swapped')

        slot0 = self.pool_v3.functions.slot0().call()
        liquidity = self.pool_v3.functions.liquidity().call()

        print('slot0: ', slot0)
        print('liquidity: ', liquidity)



        # upper_price = 1.0001 ** (upper_tick_idx / 2)
        # print(upper_tick_idx, upper_price)
        # print(sqrt_price * 2 ** (-96))
        # max_amount_in = (upper_price - (sqrt_price * 2 ** (-96))) * liquidity
        # print(max_amount_in)
        # max_amount_in = max_amount_in / 10 ** self.WETH_DECIMALS
        # print('max_amount_in: ', max_amount_in)
        #
        # q96 = 2 ** 96
        # eth = 10 ** self.WETH_DECIMALS
        # amount_in = int(max_amount_in * eth)
        # price_diff = int((amount_in * q96) // liquidity)
        # print('amount_in: ', amount_in)
        # print('price_diff: ', price_diff)
        #
        # sqrt_price_next = sqrt_price + price_diff
        # print(sqrt_price, price_diff, sqrt_price_next)
        # price_next = self.sim_v3.sqrtx96_to_price(sqrt_price_next, self.WETH_DECIMALS, self.USDT_DECIMALS, token0_in)
        #
        # print('price next: ', sqrt_price_next)
        # print('new price: ', price_next)
        #
        # usdt_balance_before = self.usdt.functions.balanceOf(self.signer.address).call()



        #     path = [self.WETH, self.USDT]
        #     nonce = self.web3.eth.get_transaction_count(self.signer.address)
        #     # I'm not including slippage tolerance here, so this transaction
        #     # will most likely fail in real life scenarios unless your transaction is at the top of the block
        #     swap_transaction = self.router2.functions.swapExactTokensForTokens(
        #         amount_in,
        #         sim_amount_out,
        #         path,
        #         self.signer.address,
        #         int(datetime.datetime.now().timestamp()) + 60000  # 1 minute
        #     ).build_transaction({
        #         'from': self.signer.address,
        #         'chainId': 1,
        #         'nonce': nonce,
        #         'gas': 200000,
        #         'maxFeePerGas': self.web3.toWei(100, 'gwei'),
        #         'maxPriorityFeePerGas': self.web3.toWei(50, 'gwei'),
        #     })
        #     signed = self.signer.sign_transaction(swap_transaction)
        #     tx_hash = self.web3.eth.send_raw_transaction(signed.rawTransaction)
        #     _ = self.web3.eth.get_transaction(tx_hash)

    # def test_sim_v2_get_max_amount_in(self):
    #     token_in = self.WETH
    #     token0 = self.pool_v2.functions.token0().call()
    #     token0_in = token_in == token0
    #
    #     reserve0, reserve1, _ = self.pool_v2.functions.getReserves().call()
    #
    #     self.sim_v2.get_max_amount_in(reserve0,
    #                                   reserve1,
    #                                   self.WETH_DECIMALS,
    #                                   self.USDT_DECIMALS,
    #                                   3000,
    #                                   token0_in,
    #                                   100,
    #                                   0.1,
    #                                   0.0,
    #                                   0.0001)
