import json
from web3 import Web3
from unittest import TestCase
from eth_account.account import Account

POOL_V2_ABI = json.load(open('../abi/UniswapV2Pool.json', 'r'))
POOL_V3_ABI = json.load(open('../abi/UniswapV3Pool.json', 'r'))

ROUTER2_ABI = json.load(open('../abi/UniswapV2Router2.json', 'r'))
QUOTER2_ABI = json.load(open('../abi/UniswapV3Quoter2.json', 'r'))

SWAP_ROUTER2_ABI = json.load(open('../abi/UniswapV3SwapRouter2.json', 'r'))

WETH_ABI = json.load(open('../abi/WETH.json', 'r'))
ERC20_ABI = json.load(open('../abi/ERC20.json', 'r'))

BOT_ABI = json.load(open('../contracts/out/WhackAMoleBotV1.sol/WhackAMoleBotV1.json', 'r'))['abi']
SIMULATOR_ABI = json.load(open('../contracts/out/SimulatorV1.sol/SimulatorV1.json', 'r'))['abi']


class WhackAMoleBotV1Tests(TestCase):
    """
    WhackAMoleBotV1 tests are dependent on WhackAMoleBotV1 contract
    Make sure to deploy the contract to mainnet hardfork before testing

    forge create --rpc-url <RPC_URL> --private-key <PRIVATE_KEY> src/WhackAMoleBotV1.sol:WhackAMoleBotV1
    """

    HARDFORK_RPC_URL = 'http://localhost:8545'
    FLASHBOTS_URL = 'https://relay.flashbots.net'

    # Private key is from Anvil
    TEST_PRIVATE_KEY = '0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80'

    WETH = '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'
    USDT = '0xdAC17F958D2ee523a2206206994597C13D831ec7'

    WETH_DECIMALS = 18
    USDT_DECIMALS = 6

    POOL_V3_FEE = 500

    # WETH-USDT Uniswap V2 pool
    POOL_V2 = '0x0d4a11d5EEaaC28EC3F61d100daF4d40471f1852'
    ROUTER2 = '0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'

    # WETH-USDT Uniswap V3 pool
    POOL_V3 = '0x11b815efB8f581194ae79006d24E0d814B7697F6'
    QUOTER2 = '0x61fFE014bA17989E743c5F6cB21bF9697530B21e'
    SWAP_ROUTER = '0xE592427A0AEce92De3Edee1F18E0157C05861564'

    # WhackAMoleBotV1
    BOT = '0x9155497EAE31D432C0b13dBCc0615a37f55a2c87'
    SIMULATOR = '0xfB12F7170FF298CDed84C793dAb9aBBEcc01E798'

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

        # WhackAMoleBotV1
        self.bot = self.web3.eth.contract(address=self.BOT, abi=BOT_ABI)
        self.sim = self.web3.eth.contract(address=self.SIMULATOR, abi=SIMULATOR_ABI)

        # Wrap ETH to WETH
        # Transfer ETH to WETH contract
        nonce = self.web3.eth.get_transaction_count(self.signer.address)
        transaction = {
            'from': self.signer.address,
            'to': self.WETH,
            'value': self.web3.to_wei(10, 'ether'),
            'chainId': 1,
            'nonce': nonce,
            'gas': 200000,
            'maxFeePerGas': self.web3.to_wei(100, 'gwei'),  # set at randomly high gas price
            'maxPriorityFeePerGas': self.web3.to_wei(50, 'gwei'),  # set at random
        }
        signed = self.signer.sign_transaction(transaction)
        tx_hash = self.web3.eth.send_raw_transaction(signed.rawTransaction)
        _ = self.web3.eth.get_transaction(tx_hash)

        # transfer WETH to bot contract
        nonce = self.web3.eth.get_transaction_count(self.signer.address)
        transfer_transaction = self.weth.functions.transfer(
            self.BOT, self.web3.to_wei(3, 'ether')
        ).build_transaction({
            'from': self.signer.address,
            'chainId': 1,
            'nonce': nonce,
            'gas': 200000,
            'maxFeePerGas': self.web3.to_wei(100, 'gwei'),
            'maxPriorityFeePerGas': self.web3.to_wei(50, 'gwei'),
        })
        signed = self.signer.sign_transaction(transfer_transaction)
        tx_hash = self.web3.eth.send_raw_transaction(signed.rawTransaction)
        _ = self.web3.eth.get_transaction(tx_hash)

        bot_weth_balance = self.weth.functions.balanceOf(self.BOT).call()
        print('Bot WETH balance: ', bot_weth_balance)
        self.assertTrue(bot_weth_balance >= self.web3.to_wei(3, 'ether'))

        # approve usage of WETH, USDT to Uniswap V2, V3 routers
        tokens = [self.WETH, self.USDT]
        protocols = [self.ROUTER2, self.SWAP_ROUTER]

        nonce = self.web3.eth.get_transaction_count(self.signer.address)
        transfer_transaction = self.bot.functions.approveHandlers(
            tokens, protocols
        ).build_transaction({
            'from': self.signer.address,
            'chainId': 1,
            'nonce': nonce,
            'gas': 200000,
            'maxFeePerGas': self.web3.to_wei(100, 'gwei'),
            'maxPriorityFeePerGas': self.web3.to_wei(50, 'gwei'),
        })
        signed = self.signer.sign_transaction(transfer_transaction)
        tx_hash = self.web3.eth.send_raw_transaction(signed.rawTransaction)
        _ = self.web3.eth.get_transaction(tx_hash)

        max_int = 2 ** 256 - 1

        for protocol in protocols:
            weth_allowance = self.weth.functions.allowance(self.BOT, protocol).call()
            self.assertEqual(weth_allowance, max_int)

            usdt_allowance = self.usdt.functions.allowance(self.BOT, protocol).call()
            self.assertEqual(usdt_allowance, max_int)

    def test_recover_tokens(self):
        # test recoverTokens
        bot_weth_balance_before = self.weth.functions.balanceOf(self.BOT).call()
        signer_weth_balance_before = self.weth.functions.balanceOf(self.signer.address).call()

        tokens = [self.WETH]
        nonce = self.web3.eth.get_transaction_count(self.signer.address)
        transfer_transaction = self.bot.functions.recoverTokens(
            tokens
        ).build_transaction({
            'from': self.signer.address,
            'chainId': 1,
            'nonce': nonce,
            'gas': 300000,
            'maxFeePerGas': self.web3.to_wei(100, 'gwei'),
            'maxPriorityFeePerGas': self.web3.to_wei(50, 'gwei'),
        })
        signed = self.signer.sign_transaction(transfer_transaction)
        tx_hash = self.web3.eth.send_raw_transaction(signed.rawTransaction)
        _ = self.web3.eth.get_transaction(tx_hash)

        bot_weth_balance_after = self.weth.functions.balanceOf(self.BOT).call()
        signer_weth_balance_after = self.weth.functions.balanceOf(self.signer.address).call()

        # print(bot_weth_balance_before, bot_weth_balance_after)
        # print(signer_weth_balance_before, signer_weth_balance_after)
        self.assertEqual(bot_weth_balance_before, signer_weth_balance_after)

    def test_v2_swap(self):
        factory = self.pool_v2.functions.factory().call()
        params = {
            'protocol': 0,
            'handler': factory,
            'tokenIn': self.WETH,
            'tokenOut': self.USDT,
            'fee': 3000,
            'amount': self.web3.to_wei(1, 'ether'),
        }
        simulated_amount_out = self.sim.functions.simulateSwapIn([params]).call()

        usdt_balance_before = self.usdt.functions.balanceOf(self.BOT).call()

        swap_params = {
            **params,
            'handler': self.ROUTER2,
        }
        nonce = self.web3.eth.get_transaction_count(self.signer.address)
        transfer_transaction = self.bot.functions.whack(
            [swap_params], 0
        ).build_transaction({
            'from': self.signer.address,
            'chainId': 1,
            'nonce': nonce,
            'gas': 300000,
            'maxFeePerGas': self.web3.to_wei(100, 'gwei'),
            'maxPriorityFeePerGas': self.web3.to_wei(50, 'gwei'),
        })
        signed = self.signer.sign_transaction(transfer_transaction)
        tx_hash = self.web3.eth.send_raw_transaction(signed.rawTransaction)
        _ = self.web3.eth.get_transaction(tx_hash)

        usdt_balance_after = self.usdt.functions.balanceOf(self.BOT).call()

        self.assertEqual(simulated_amount_out, usdt_balance_after - usdt_balance_before)

    def test_v3_swap(self):
        params = {
            'protocol': 1,
            'handler': self.QUOTER2,
            'tokenIn': self.WETH,
            'tokenOut': self.USDT,
            'fee': self.POOL_V3_FEE,
            'amount': self.web3.to_wei(1, 'ether'),
        }
        simulated_amount_out = self.sim.functions.simulateSwapIn([params]).call()

        usdt_balance_before = self.usdt.functions.balanceOf(self.BOT).call()

        swap_params = {
            **params,
            'handler': self.SWAP_ROUTER,
        }
        nonce = self.web3.eth.get_transaction_count(self.signer.address)
        transfer_transaction = self.bot.functions.whack(
            [swap_params], 0
        ).build_transaction({
            'from': self.signer.address,
            'chainId': 1,
            'nonce': nonce,
            'gas': 300000,
            'maxFeePerGas': self.web3.to_wei(100, 'gwei'),
            'maxPriorityFeePerGas': self.web3.to_wei(50, 'gwei'),
        })
        signed = self.signer.sign_transaction(transfer_transaction)
        tx_hash = self.web3.eth.send_raw_transaction(signed.rawTransaction)
        _ = self.web3.eth.get_transaction(tx_hash)

        usdt_balance_after = self.usdt.functions.balanceOf(self.BOT).call()

        self.assertEqual(simulated_amount_out, usdt_balance_after - usdt_balance_before)

    def test_2_hop_swaps(self):
        factory = self.pool_v2.functions.factory().call()
        params_1 = {
            'protocol': 0,
            'handler': factory,
            'tokenIn': self.WETH,
            'tokenOut': self.USDT,
            'fee': 3000,
            'amount': self.web3.to_wei(1, 'ether'),
        }
        params_2 = {
            'protocol': 1,
            'handler': self.QUOTER2,
            'tokenIn': self.USDT,
            'tokenOut': self.WETH,
            'fee': self.POOL_V3_FEE,
            'amount': 0,
        }
        simulated_amount_out = self.sim.functions.simulateSwapIn(
            [params_1, params_2]
        ).call()

        weth_balance_before = self.weth.functions.balanceOf(self.BOT).call()

        swap_params_1 = {
            **params_1,
            'handler': self.ROUTER2,
        }
        swap_params_2 = {
            **params_2,
            'handler': self.SWAP_ROUTER,
        }
        nonce = self.web3.eth.get_transaction_count(self.signer.address)
        transfer_transaction = self.bot.functions.whack(
            [swap_params_1, swap_params_2], 0
        ).build_transaction({
            'from': self.signer.address,
            'chainId': 1,
            'nonce': nonce,
            'gas': 300000,
            'maxFeePerGas': self.web3.to_wei(100, 'gwei'),
            'maxPriorityFeePerGas': self.web3.to_wei(50, 'gwei'),
        })
        signed = self.signer.sign_transaction(transfer_transaction)
        tx_hash = self.web3.eth.send_raw_transaction(signed.rawTransaction)
        _ = self.web3.eth.get_transaction(tx_hash)

        weth_balance_after = self.weth.functions.balanceOf(self.BOT).call()

        weth_amount_out = weth_balance_after - (weth_balance_before - self.web3.to_wei(1, 'ether'))
        self.assertEqual(simulated_amount_out, weth_amount_out)

    def test_n_hop_swap_gas(self):
        """
        V2 1-hop: 116040
           2-hop: 145834
           3-hop: 182965
           4-hop: 208761

        V3 1-hop: 117267
           2-hop: 161362
           3-hop: 207317
           4-hop: 242614

        V2 1-hop / V3 1-hop: 186354
        V2 2-hop / V3 1-hop: 220666
        V2 1-hop / V3 2-hop: 235437
        V2 2-hop / V3 2-hop: 262089

        For simplicity:
        Base cost: 100000
        V2 1-hop costs: 40000
        V3 1-hop costs: 50000
        """
        params_1 = {
            'protocol': 0,
            'handler': self.ROUTER2,
            'tokenIn': self.WETH,
            'tokenOut': self.USDT,
            'fee': 3000,
            'amount': self.web3.to_wei(0.1, 'ether'),
        }
        params_2 = {
            'protocol': 1,
            'handler': self.SWAP_ROUTER,
            'tokenIn': self.USDT,
            'tokenOut': self.WETH,
            'fee': 500,
            'amount': 0,
        }
        params_3 = {
            'protocol': 1,
            'handler': self.SWAP_ROUTER,
            'tokenIn': self.WETH,
            'tokenOut': self.USDT,
            'fee': 500,
            'amount': 0,
        }
        params_4 = {
            'protocol': 0,
            'handler': self.ROUTER2,
            'tokenIn': self.USDT,
            'tokenOut': self.WETH,
            'fee': 3000,
            'amount': 0,
        }

        nonce = self.web3.eth.get_transaction_count(self.signer.address)
        transfer_transaction = self.bot.functions.whack(
            [params_1, params_4, params_1, params_4], 0
        ).build_transaction({
            'from': self.signer.address,
            'chainId': 1,
            'nonce': nonce,
            'gas': 300000,
            'maxFeePerGas': self.web3.to_wei(100, 'gwei'),
            'maxPriorityFeePerGas': self.web3.to_wei(50, 'gwei'),
        })
        signed = self.signer.sign_transaction(transfer_transaction)
        tx_hash = self.web3.eth.send_raw_transaction(signed.rawTransaction)
        tx = self.web3.eth.get_transaction(tx_hash)
        print(tx)

    def test_price_impact_simulation(self):
        uniswap_quoter2 = '0x61fFE014bA17989E743c5F6cB21bF9697530B21e'
        sushiswap_quoter2 = '0x64e8802FE490fa7cc61d3463958199161Bb608A7'

        # Scenario 1: WETH -> USDT -> WETH
        amount_in = 1 * 10 ** self.WETH_DECIMALS

        params_1 = {
            'protocol': 1,
            'handler': uniswap_quoter2,
            'tokenIn': self.WETH,
            'tokenOut': self.USDT,
            'fee': 500,
            'amount': amount_in,
        }
        params_2 = {
            'protocol': 1,
            'handler': sushiswap_quoter2,
            'tokenIn': self.USDT,
            'tokenOut': self.WETH,
            'fee': 500,
            'amount': 0,
        }
        simulated_amount_out = self.sim.functions.simulateSwapIn(
            [params_1, params_2]
        ).call()

        # Scenario 2: USDT -> WETH -> USDT
        amount_in = 1 * 10 ** self.USDT_DECIMALS
