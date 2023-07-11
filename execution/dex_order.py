import os
import secrets
from uuid import uuid4
from dotenv import load_dotenv
from flashbots import flashbot
from web3.types import TxParams
from web3 import Web3, HTTPProvider
from eth_account.account import Account
from eth_account.signers.local import LocalAccount
from web3.exceptions import TransactionNotFound

load_dotenv(override=True)

FLASHBOTS_SIGNING_KEY = os.getenv('FLASHBOTS_SIGNING_KEY')
FLASHBOTS_PRIVATE_KEY = os.getenv('FLASHBOTS_PRIVATE_KEY')

ETHEREUM_HTTP_RPC_URL = os.getenv('ETHEREUM_HTTP_RPC_URL')
GOERLI_HTTP_RPC_URL = os.getenv('GOERLI_HTTP_RPC_URL')
GOERLI_WS_RPC_URL = os.getenv('GOERLI_WS_RPC_URL')

CHAIN_ID = 5


def explore_block():
    w3 = Web3(HTTPProvider(ETHEREUM_HTTP_RPC_URL))
    block = w3.eth.get_block(17667201)

    builder = block['extraData'].decode('utf-8')

    tx_first = w3.eth.get_transaction(block['transactions'][1])
    tx_last = w3.eth.get_transaction(block['transactions'][-2])

    tx_first_gas_price = Web3.fromWei(tx_first['gasPrice'], 'gwei')
    tx_last_gas_price = Web3.fromWei(tx_last['gasPrice'], 'gwei')

    tx_first_bribe = Web3.fromWei(tx_first['maxPriorityFeePerGas'], 'gwei')
    tx_last_bribe = Web3.fromWei(tx_last['maxPriorityFeePerGas'], 'gwei')

    print(builder)

    print(f'TX 1 gas price: {tx_first_gas_price}')
    print(f'TX 1 bribe: {tx_first_bribe}')

    print(f'TX last gas price: {tx_last_gas_price}')
    print(f'TX last bribe: {tx_last_bribe}')


def main():
    sender = Account.from_key(FLASHBOTS_PRIVATE_KEY)
    signer = Account.from_key(FLASHBOTS_SIGNING_KEY)

    receiver_address = '0x837d0dF19043F97cb4fd6e80cc03B59897B0926e'

    w3 = Web3(HTTPProvider(GOERLI_HTTP_RPC_URL))
    flashbot(w3, signer, 'https://relay-goerli.flashbots.net')

    sender_balance = Web3.fromWei(w3.eth.get_balance(sender.address), 'ether')
    receiver_balance = Web3.fromWei(w3.eth.get_balance(receiver_address), 'ether')

    print(sender_balance)
    print(receiver_balance)

    nonce = w3.eth.get_transaction_count(sender.address)
    tx1 = {
        'to': receiver_address,
        'value': Web3.toWei(0.001, 'ether'),
        'gas': 21000,
        'maxFeePerGas': Web3.toWei(200, 'gwei'),
        'maxPriorityFeePerGas': Web3.toWei(50, 'gwei'),
        'nonce': nonce,
        'chainId': CHAIN_ID,
        'type': 2,
    }
    tx1_signed = sender.sign_transaction(tx1)

    tx2 = {
        'to': receiver_address,
        'value': Web3.toWei(0.001, 'ether'),
        'gas': 21000,
        'maxFeePerGas': Web3.toWei(200, 'gwei'),
        'maxPriorityFeePerGas': Web3.toWei(50, 'gwei'),
        'nonce': nonce + 1,
        'chainId': CHAIN_ID,
        'type': 2,
    }

    bundle = [
        {'signed_transaction': tx1_signed.rawTransaction},
        {'signer': sender, 'transaction': tx2},
    ]

    while True:
        block = w3.eth.block_number
        print(block)

        try:
            w3.flashbots.simulate(bundle, block)
        except Exception as e:
            print(f'Simulation error: {e}')
            return

        replacement_uuid = str(uuid4())
        send_result = w3.flashbots.send_bundle(
            bundle,
            target_block_number=block + 1,
            opts={'replacementUuid': replacement_uuid},
        )
        print('bundleHash: ', w3.toHex(send_result.bundle_hash()))

        stats_v1 = w3.flashbots.get_bundle_stats(
            w3.toHex(send_result.bundle_hash()), block
        )
        print('stats: ', stats_v1)

        stats_v2 = w3.flashbots.get_bundle_stats(
            w3.toHex(send_result.bundle_hash()), block
        )
        print('stats 2: ', stats_v2)

        send_result.wait()
        try:
            receipts = send_result.receipts()
            print(receipts)
            break
        except TransactionNotFound:
            cancel_res = w3.flashbots.cancel_bundles(replacement_uuid)
            print('cancel')
            print(cancel_res)

    sender_balance = Web3.fromWei(w3.eth.get_balance(sender.address), 'ether')
    receiver_balance = Web3.fromWei(w3.eth.get_balance(receiver_address), 'ether')

    print(sender_balance)
    print(receiver_balance)


if __name__ == '__main__':
    explore_block()
