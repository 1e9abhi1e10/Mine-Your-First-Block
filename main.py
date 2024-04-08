import os
import sys
import json
import hashlib
import time

sys.path.append('/home/ubuntu/.local/lib/python3.10/site-packages')
import base58
import bech32
from ecdsa import VerifyingKey, BadSignatureError, SECP256k1

# Constants
MEMPOOL_DIR = 'mempool'
OUTPUT_FILE = 'output.txt'
DIFFICULTY_TARGET = '0000ffff00000000000000000000000000000000000000000000000000000000'
MAX_NONCE = 2**32  # Maximum nonce value before wrapping around
DUST_THRESHOLD = 546  # Satoshis, smallest output value that is considered non-dust
BLOCK_SIZE_LIMIT = 1000000  # Define the block size limit constant (1MB)

def read_transaction_file(filename):
    with open(os.path.join(MEMPOOL_DIR, filename), 'r') as file:
        return json.load(file)

def convert_asm_to_scriptPubKey(asm):
    ops = asm.split(' ')
    if len(ops) == 5 and ops[0] == 'OP_DUP' and ops[1] == 'OP_HASH160' and ops[3] == 'OP_EQUALVERIFY' and ops[4] == 'OP_CHECKSIG':
        pubkey_hash = ops[2]
        scriptPubKey = f'76a9{pubkey_hash}88ac'
        return scriptPubKey
    else:
        return 'UNKNOWN_SCRIPT_TYPE'

def validate_script_and_address(transaction):
    asm = transaction.get('asm', '')
    address = transaction.get('address', '')

    scriptPubKey = convert_asm_to_scriptPubKey(asm)

    try:
        if base58.b58decode_check(address):
            return True
    except ValueError:
        pass

    try:
        if bech32.bech32_decode(address):
            return True
    except ValueError:
        pass

    return False
def detect_dust_and_double_spending(transactions):
    spent_inputs = set()
    valid_transactions = []

    for tx in transactions:
        if tx['value'] < DUST_THRESHOLD:
            continue

        is_double_spent = False
        for vin in tx['vin']:
            input_key = (vin['txid'], vin['vout'])
            if input_key in spent_inputs:
                is_double_spent = True
                break
            spent_inputs.add(input_key)

        if not is_double_spent:
            valid_transactions.append(tx)

    return valid_transactions

def validate_redeem_script(transaction):
    for vin in transaction['vin']:
        if 'scriptSig' in vin and 'redeemScript' in vin['scriptSig']:
            redeem_script = vin['scriptSig']['redeemScript']
            redeem_script_bytes = bytes.fromhex(redeem_script)
            sha256_hash = hashlib.sha256(redeem_script_bytes).digest()
            redeem_script_hash160 = hashlib.new('ripemd160', sha256_hash).hexdigest()
            corresponding_output = transaction['vout'][vin['vout']]
            scriptPubKey = corresponding_output['scriptPubKey']
            if redeem_script_hash160 not in scriptPubKey:
                return False
    return True

def extract_and_verify_signatures(transaction):
    for vin in transaction['vin']:
        if 'scriptSig' in vin:
            scriptSig = vin['scriptSig']
            signature = scriptSig.get('signature', '')
            pubkey = scriptSig.get('pubkey', '')
            if signature and pubkey:
                try:
                    vk = VerifyingKey.from_string(bytes.fromhex(pubkey), curve=SECP256k1)
                    if not vk.verify(bytes.fromhex(signature), transaction['txid'].encode()):
                        return False
                except BadSignatureError:
                    return False
        if 'witness' in vin:
            witness = vin['witness']
            if len(witness) == 2:
                signature, pubkey = witness
                try:
                    vk = VerifyingKey.from_string(bytes.fromhex(pubkey), curve=SECP256k1)
                    if not vk.verify(bytes.fromhex(signature), transaction['txid'].encode()):
                        return False
                except BadSignatureError:
                    return False
    return True

def optimize_transaction_selection(transactions, block_size_limit):
    for tx in transactions:
        tx_size = len(json.dumps(tx))
        tx['fee_rate'] = tx['fee'] / tx_size

    sorted_transactions = sorted(transactions, key=lambda tx: tx['fee_rate'], reverse=True)

    selected_transactions = []
    current_block_size = 0
    for tx in sorted_transactions:
        tx_size = len(json.dumps(tx))
        if current_block_size + tx_size <= block_size_limit:
            selected_transactions.append(tx)
            current_block_size += tx_size
        else:
            break

    return selected_transactions
def is_valid_transaction(transaction):
    if not validate_script_and_address(transaction):
        return False
    if not validate_redeem_script(transaction):
        return False
    if not extract_and_verify_signatures(transaction):
        return False
    return True

def calculate_transaction_fee(transaction):
    input_value = sum([vin['prevout']['value'] for vin in transaction['vin']])
    output_value = sum([vout['value'] for vout in transaction['vout']])
    return input_value - output_value

def create_coinbase_transaction(block_transactions):
    return {
        "txid": "coinbase",
        "value": 50
    }

def mine_block(transactions, previous_block_hash):
    nonce = 0
    while nonce < MAX_NONCE:
        block_header = str(previous_block_hash) + str(time.time()) + str(nonce)
        block_hash = hashlib.sha256(block_header.encode()).hexdigest()
        if block_hash < DIFFICULTY_TARGET:
            return block_hash, transactions
        nonce += 1
    return None, transactions

def main():
    print("Starting mining simulation...")
    transaction_files = os.listdir(MEMPOOL_DIR)
    transactions = [read_transaction_file(f) for f in transaction_files if f.endswith('.json')]

    print(f"Read {len(transactions)} transactions from the mempool.")

    non_dust_transactions = detect_dust_and_double_spending(transactions)
    print(f"Filtered out dust transactions. {len(non_dust_transactions)} transactions remaining.")

    valid_transactions = [tx for tx in non_dust_transactions if is_valid_transaction(tx)]
    print(f"Validated {len(valid_transactions)} transactions.")

    optimized_transactions = optimize_transaction_selection(valid_transactions, BLOCK_SIZE_LIMIT)
    print("Optimized transaction selection to maximize fees.")

    coinbase_tx = create_coinbase_transaction(optimized_transactions)
    print("Created coinbase transaction.")

    previous_block_hash = '0000000000000000000000000000000000000000000000000000000000000000'
    block_hash, block_transactions = mine_block([coinbase_tx] + optimized_transactions, previous_block_hash)

    if block_hash is not None:
        print(f"Successfully mined a block with hash: {block_hash}")
        with open(OUTPUT_FILE, 'w') as file:
            file.write(block_hash + '\n')
            file.write(json.dumps(coinbase_tx) + '\n')
            for tx in block_transactions:
                if 'txid' in tx and tx['txid'] != "coinbase":
                    file.write(tx['txid'] + '\n')
    else:
        print("Failed to mine a block within the nonce range.")

if __name__ == '__main__':
    main()
