import os
import json
import asyncio
from web3 import Web3
from uuid import uuid4
from pathlib import Path
from dotenv import load_dotenv
from typing import Any, Dict, List
from eth_account.account import Account
from flashbots import flashbot, Flashbots
from web3.exceptions import TransactionNotFound
from flashbots.flashbots import FlashbotsBundleResponse

load_dotenv(override=True)

PROTOCOL_TO_ID = {
    'uniswap_v2': 0,
    'sushiswap_v2': 0,
    'uniswap_v3': 1,
    'sushiswap_v3': 1,
}

FLASHBOTS_SIGNING_KEY = os.getenv('FLASHBOTS_SIGNING_KEY')
FLASHBOTS_PRIVATE_KEY = os.getenv('FLASHBOTS_PRIVATE_KEY')

DIR = os.path.dirname(os.path.abspath(__file__))

BOT_ABI_FILE_PATH = Path(DIR) / 'WhackAMoleBotV1.json'
BOT_ABI = json.load(open(BOT_ABI_FILE_PATH, 'r'))['abi']

ERC20_ABI_FILE_PATH = Path(DIR) / 'ERC20.json'
ERC20_ABI = json.load(open(ERC20_ABI_FILE_PATH, 'r'))


class DexOrder:
    """
    TODO: Send bundles to multiple private relays to increase probability of being added
    """
    PRIVATE_RELAY = {
        'ethereum': 'https://relay.flashbots.net'
    }

    def __init__(self,
                 private_key: str = FLASHBOTS_PRIVATE_KEY,
                 signing_key: str = FLASHBOTS_SIGNING_KEY,
                 rpc_endpoints: Dict[str, str] = None,
                 tokens: Dict[str, Dict[str, List[str or int]]] = None,
                 pools: List[Dict[str, Any]] = None,
                 contracts: Dict[str, str] = None,
                 handlers: Dict[str, Dict[str, str]] = None):

        self.sender = Account.from_key(private_key)
        self.signer = Account.from_key(signing_key)  # used for Flashbots reputation

        self.rpc_endpoints = rpc_endpoints
        self.tokens = tokens
        self.pools = pools
        self.contracts = contracts
        self.handlers = handlers

        # extract keys from tokens, pools
        self.chains_list = sorted(list(tokens.keys()))
        self.exchanges_list = sorted(set([p['exchange'] for p in pools]))

        tokens_list = []
        for exchange, tokens_dict in tokens.items():
            tokens_list.extend(list(tokens_dict.keys()))
        self.tokens_list = sorted(list(set(tokens_list)))

        # map chains, exchanges, tokens to int id value
        # this is used to map chains/exchanges/tokens to numpy array index values
        self.chain_to_id = {k: i for i, k in enumerate(self.chains_list)}
        self.exchange_to_id = {k: i for i, k in enumerate(self.exchanges_list)}
        self.token_to_id = {k: i for i, k in enumerate(self.tokens_list)}

        self.web3: Dict[str, Web3] = {k: Web3(Web3.HTTPProvider(v)) for k, v in rpc_endpoints.items()}
        self.chain_id = {k: v.eth.chain_id for k, v in self.web3.items()}

        for chain, w3 in self.web3.items():
            flashbot(w3, self.signer, self.PRIVATE_RELAY[chain])

        self.bot = {
            chain: w3.eth.contract(address=contracts[chain], abi=BOT_ABI)
            for chain, w3 in self.web3.items()
        }

    async def send_bundle(self,
                          w3: Web3,
                          bundle: List[Dict[str, Any]],
                          retry: int,
                          block_number: int = None) -> list:

        flashbots: Flashbots = w3.flashbots

        left_retries = retry

        if not block_number:
            block_number = w3.eth.block_number

        receipts = []

        while left_retries > 0:
            print(f'Sending bundles at: #{block_number}')
            try:
                flashbots.simulate(bundle, block_number)
            except Exception as e:
                print('Simulation error', e)
                break

            replacement_uuid = str(uuid4())
            response: FlashbotsBundleResponse = flashbots.send_bundle(
                bundle,
                target_block_number=block_number + 1,
                opts={'replacementUuid': replacement_uuid},
            )

            while w3.eth.block_number < response.target_block_number:
                await asyncio.sleep(1)

            try:
                receipts = list(
                    map(lambda tx: w3.eth.get_transaction_receipt(tx['hash']), response.bundle)
                )
                print(f'\nBundle was mined in block {receipts[0].blockNumber}\a')
                break
            except TransactionNotFound:
                print(f'Bundle not found in block {block_number + 1}')
                flashbots.cancel_bundles(replacement_uuid)
                left_retries -= 1
                block_number += 1

        return receipts

    async def transfer_in(self,
                          chain: str,
                          token: str,
                          amount: float,
                          max_priority_fee_per_gas: float,
                          max_fee_per_gas: float,
                          retry: int,
                          block_number: int = None) -> list:

        w3 = self.web3[chain]
        token_contract = w3.eth.contract(address=token, abi=ERC20_ABI)
        nonce = w3.eth.get_transaction_count(self.sender.address)
        transaction = token_contract.functions.transfer(
            self.bot[chain].address, int(amount)
        ).build_transaction({
            'from': self.sender.address,
            'gas': 200000,
            'nonce': nonce,
            'chainId': self.chain_id[chain],
            'maxFeePerGas': int(max_fee_per_gas),
            'maxPriorityFeePerGas': int(max_priority_fee_per_gas),
        })
        signed = self.sender.sign_transaction(transaction)
        bundle = [{'signed_transaction': signed.rawTransaction}]
        return await self.send_bundle(w3, bundle, retry, block_number)

    async def transfer_out(self,
                           chain: str,
                           tokens: List[str],
                           max_priority_fee_per_gas: float,
                           max_fee_per_gas: float,
                           retry: int,
                           block_number: int = None) -> list:

        w3 = self.web3[chain]
        nonce = w3.eth.get_transaction_count(self.sender.address)
        transaction = self.bot[chain].functions.recoverTokens(
            tokens
        ).build_transaction({
            'from': self.sender.address,
            'gas': 300000,
            'nonce': nonce,
            'chainId': self.chain_id[chain],
            'maxFeePerGas': int(max_fee_per_gas),
            'maxPriorityFeePerGas': int(max_priority_fee_per_gas),
        })
        signed = self.sender.sign_transaction(transaction)
        bundle = [{'signed_transaction': signed.rawTransaction}]
        return await self.send_bundle(w3, bundle, retry, block_number)

    async def approve_handlers(self,
                               chain: str,
                               tokens: List[str],
                               handlers: List[str],
                               max_priority_fee_per_gas: float,
                               max_fee_per_gas: float,
                               retry: int,
                               block_number: int = None):
        """
        You only need to call this once with all the tokens used in your trades
        This function call will automatically set maxint as the approved amount to all the handlers
        """
        w3 = self.web3[chain]
        nonce = w3.eth.get_transaction_count(self.sender.address)
        transaction = self.bot[chain].functions.approveHandlers(
            tokens, handlers
        ).build_transaction({
            'from': self.sender.address,
            'gas': 400000,
            'nonce': nonce,
            'chainId': self.chain_id[chain],
            'maxFeePerGas': int(max_fee_per_gas),
            'maxPriorityFeePerGas': int(max_priority_fee_per_gas),
        })
        signed = self.sender.sign_transaction(transaction)
        bundle = [{'signed_transaction': signed.rawTransaction}]
        return await self.send_bundle(w3, bundle, retry, block_number)

    def make_params(self,
                    amount_in: float,
                    buy_path: List[List[int]],
                    sell_path: List[List[int]],
                    buy_pools: List[int],
                    sell_pools: List[int]) -> List[Dict[str, Any]]:

        params = []
        params.extend(self._make_buy_params(amount_in, buy_path, buy_pools))
        params.extend(self._make_sell_params(sell_path, sell_pools))
        return params

    def _make_buy_params(self,
                         amount_in: float,
                         path: List[List[int]],
                         pools: List[int]):

        params_list = []

        for i in range(len(path)):
            _path = path[i]
            if not sum(_path):
                continue

            _pool_idx = pools[i]

            pool = self.pools[_pool_idx]
            chain = pool['chain']
            exchange = pool['exchange']
            version = pool['version']
            exchange_key = f'{exchange}_v{version}'

            token_in = self.tokens_list[_path[2]]
            token_out = self.tokens_list[_path[3]]

            amount_in_scaled = amount_in if i == 0 else 0

            params = {
                'protocol': PROTOCOL_TO_ID[exchange_key],
                'handler': self.handlers[chain][exchange_key],
                'tokenIn': self.tokens[chain][token_in][0],
                'tokenOut': self.tokens[chain][token_out][0],
                'fee': pool['fee'],
                'amount': int(amount_in_scaled),
            }
            params_list.append(params)

        return params_list

    def _make_sell_params(self, path: List[List[int]], pools: List[int]):
        params_list = []

        for i in range(len(path)):
            _path = path[i]
            if not sum(_path):
                continue

            _pool_idx = pools[i]

            pool = self.pools[_pool_idx]
            chain = pool['chain']
            exchange = pool['exchange']
            version = pool['version']
            exchange_key = f'{exchange}_v{version}'

            # not the index difference with buy_params
            token_in = self.tokens_list[_path[3]]
            token_out = self.tokens_list[_path[2]]

            params = {
                'protocol': PROTOCOL_TO_ID[exchange_key],
                'handler': self.handlers[chain][exchange_key],
                'tokenIn': self.tokens[chain][token_in][0],
                'tokenOut': self.tokens[chain][token_out][0],
                'fee': pool['fee'],
                'amount': 0,  # no need to set amount
            }
            params_list.append(params)

        return list(reversed(params_list))

    async def send_order(self,
                         chain: str,
                         params: List[Dict[str, Any]],
                         min_amount_out: float,
                         max_priority_fee_per_gas: float,
                         max_fee_per_gas: float,
                         retry: int,
                         block_number: int = None):

        w3 = self.web3[chain]
        nonce = w3.eth.get_transaction_count(self.sender.address)
        transaction = self.bot[chain].functions.whack(
            params, int(min_amount_out)
        ).build_transaction({
            'from': self.sender.address,
            'gas': 400000,
            'nonce': nonce,
            'chainId': self.chain_id[chain],
            'maxFeePerGas': int(max_fee_per_gas),
            'maxPriorityFeePerGas': int(max_priority_fee_per_gas),
        })
        signed = self.sender.sign_transaction(transaction)
        bundle = [{'signed_transaction': signed.rawTransaction}]
        return await self.send_bundle(w3, bundle, retry, block_number)


if __name__ == '__main__':
    from configs import RPC_ENDPOINTS
    from addresses import ETHEREUM_EXECUTION_HANDLERS

    ETHEREUM_BOT_ADDRESS = os.getenv('ETHEREUM_BOT_ADDRESS')

    order = DexOrder(private_key=FLASHBOTS_PRIVATE_KEY,
                     signing_key=FLASHBOTS_SIGNING_KEY,
                     rpc_endpoints={'ethereum': RPC_ENDPOINTS['ethereum']},
                     contracts={'ethereum': ETHEREUM_BOT_ADDRESS},
                     handlers={'ethereum': ETHEREUM_EXECUTION_HANDLERS})

    block_number = order.web3['ethereum'].eth.block_number
    max_priority_fee_per_gas = 1 * 10 ** 9
    max_fee_per_gas = 30 * 10 ** 9

    # # example of sending USDT into bot contract
    # receipts = asyncio.run(order.transfer_in('ethereum',
    #                                          '0xdAC17F958D2ee523a2206206994597C13D831ec7',
    #                                          100 * 10 ** 6,
    #                                          max_priority_fee_per_gas,
    #                                          max_fee_per_gas,
    #                                          block_number))

    # # example of recovering USDT from bot contract
    # receipts = asyncio.run(order.transfer_out('ethereum',
    #                                           ['0xdAC17F958D2ee523a2206206994597C13D831ec7'],
    #                                           max_priority_fee_per_gas,
    #                                           max_fee_per_gas,
    #                                           3,
    #                                           block_number))

    usdt = order.web3['ethereum'].eth.contract(address='0xdAC17F958D2ee523a2206206994597C13D831ec7',
                                               abi=ERC20_ABI)
    owner_usdt_balance = usdt.functions.balanceOf(order.sender.address).call()
    bot_usdt_balance = usdt.functions.balanceOf(order.contracts['ethereum']).call()
    print(owner_usdt_balance, bot_usdt_balance)
