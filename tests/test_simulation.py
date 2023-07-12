import json
import datetime
from web3 import Web3
from unittest import TestCase
from eth_account.account import Account

from simulation import UniswapV2Simulator

POOL_V2_ABI = json.load(open('../abi/UniswapV2Pool.json', 'r'))
POOL_V3_ABI = json.load(open('../abi/UniswapV3Pool.json', 'r'))

ROUTER2_ABI = json.load(open('../abi/UniswapV2Router2.json', 'r'))

WETH_ABI = json.load(open('../abi/WETH.json', 'r'))
ERC20_ABI = json.load(open('../abi/ERC20.json', 'r'))


class SimulationTests(TestCase):
    """
    Simulation tests are dependent on mainnet hardforks
    Make sure to have a local mainnet hardfork running before running

    For people using Foundry, running Anvil Ethereum mainnet hardfork is easy:

    anvil --fork-url <RPC_URL>
    """

    HARDFORK_RPC_URL = 'http://localhost:8545'

    # Private key is from Anvil
    TEST_PRIVATE_KEY = '0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80'

    # WETH-USDT Uniswap V2 pool
    POOL_V2 = '0x0d4a11d5EEaaC28EC3F61d100daF4d40471f1852'
    ROUTER2 = '0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'
    WETH = '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'
    USDT = '0xdAC17F958D2ee523a2206206994597C13D831ec7'

    def setUp(self):
        self.signer = Account.from_key(self.TEST_PRIVATE_KEY)

        self.web3 = Web3(Web3.HTTPProvider(self.HARDFORK_RPC_URL))

        self.pool_v2 = self.web3.eth.contract(address=self.POOL_V2, abi=POOL_V2_ABI)
        self.router2 = self.web3.eth.contract(address=self.ROUTER2, abi=ROUTER2_ABI)
        self.weth = self.web3.eth.contract(address=self.WETH, abi=WETH_ABI)
        self.usdt = self.web3.eth.contract(address=self.USDT, abi=ERC20_ABI)

        self.sim_v2 = UniswapV2Simulator()

        # Wrap 1 ETH to 1 WETH
        # Transfer 1 ETH to WETH contract
        nonce = self.web3.eth.get_transaction_count(self.signer.address)
        transaction = {
            'from': self.signer.address,
            'to': self.WETH,
            'value': self.web3.toWei(1, 'ether'),
            'chainId': 1,
            'nonce': nonce,
            'gas': 200000,
            'maxFeePerGas': self.web3.toWei(100, 'gwei'),
            'maxPriorityFeePerGas': self.web3.toWei(50, 'gwei'),
        }
        signed = self.signer.sign_transaction(transaction)
        tx_hash = self.web3.eth.send_raw_transaction(signed.rawTransaction)
        _ = self.web3.eth.get_transaction(tx_hash)

    def test_sim_v2_get_amount_out(self):
        token_in = self.WETH
        token0 = self.pool_v2.functions.token0().call()
        token_in_is_token0 = token_in == token0

        reserve0, reserve1, _ = self.pool_v2.functions.getReserves().call()

        if token_in_is_token0:
            reserve_in, reserve_out = reserve0, reserve1
        else:
            reserve_in, reserve_out = reserve1, reserve0

        amount_in = self.web3.toWei(1, 'ether')

        # First check that the simulation results equal that of Router2
        router_amount_out = self.router2.functions.getAmountOut(
            amount_in, reserve_in, reserve_out
        ).call()

        sim_amount_out = self.sim_v2.get_amount_out(
            amount_in, reserve_in, reserve_out
        )

        self.assertEqual(router_amount_out, sim_amount_out)

        # Next, check that swapping 1 WETH does in fact result in amount_out USDT
        nonce = self.web3.eth.get_transaction_count(self.signer.address)
        approve_transaction = self.weth.functions.approve(self.ROUTER2, amount_in).build_transaction({
            'from': self.signer.address,
            'chainId': 1,
            'nonce': nonce,
            'gas': 200000,
            'maxFeePerGas': self.web3.toWei(100, 'gwei'),
            'maxPriorityFeePerGas': self.web3.toWei(50, 'gwei'),
        })
        signed = self.signer.sign_transaction(approve_transaction)
        tx_hash = self.web3.eth.send_raw_transaction(signed.rawTransaction)
        _ = self.web3.eth.get_transaction(tx_hash)

        allowance_amount = self.weth.functions.allowance(self.signer.address, self.ROUTER2).call()
        self.assertEqual(amount_in, allowance_amount)  # approve was successful

        usdt_balance_before = self.usdt.functions.balanceOf(self.signer.address).call()

        path = [self.WETH, self.USDT]
        nonce = self.web3.eth.get_transaction_count(self.signer.address)
        swap_transaction = self.router2.functions.swapExactTokensForTokens(
            amount_in,
            sim_amount_out,
            path,
            self.signer.address,
            int(datetime.datetime.now().timestamp()) + 60000  # 1 minute
        ).build_transaction({
            'from': self.signer.address,
            'chainId': 1,
            'nonce': nonce,
            'gas': 200000,
            'maxFeePerGas': self.web3.toWei(100, 'gwei'),
            'maxPriorityFeePerGas': self.web3.toWei(50, 'gwei'),
        })
        signed = self.signer.sign_transaction(swap_transaction)
        tx_hash = self.web3.eth.send_raw_transaction(signed.rawTransaction)
        _ = self.web3.eth.get_transaction(tx_hash)

        usdt_balance_after = self.usdt.functions.balanceOf(self.signer.address).call()

        self.assertEqual(usdt_balance_before + sim_amount_out, usdt_balance_after)
