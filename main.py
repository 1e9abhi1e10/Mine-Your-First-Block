import json
import os
import hashlib
import time

# Constants
MEMPOOL_DIR = 'mempool'
OUTPUT_FILE = 'output.txt'
DIFFICULTY_TARGET = '0000ffff00000000000000000000000000000000000000000000000000000000'
MAX_NONCE = 2**32  # Maximum nonce value before wrapping around

def read_transaction_file(filename):
    with open(os.path.join(MEMPOOL_DIR, filename), 'r') as file:
        return json.load(file)

def is_valid_transaction(transaction):
    # Basic validation checks
    required_fields = ['vin', 'vout']
    for field in required_fields:
        if field not in transaction:
            return False

    if not transaction['vin'] or not transaction['vout']:
        return False

    input_value = sum([vin['prevout']['value'] for vin in transaction['vin']])
    output_value = sum([vout['value'] for vout in transaction['vout']])
    if input_value < output_value:
        return False

    return True

def calculate_transaction_fee(transaction):
    input_value = sum([vin['prevout']['value'] for vin in transaction['vin']])
    output_value = sum([vout['value'] for vout in transaction['vout']])
    return input_value - output_value

def create_coinbase_transaction(block_transactions):
    return {
        "txid": "coinbase",
        "value": 50  # Fixed block reward for example purposes
    }

def mine_block(transactions, previous_block_hash):
    # Implementing the proof-of-work algorithm
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

    valid_transactions = [tx for tx in transactions if is_valid_transaction(tx)]
    print(f"Validated {len(valid_transactions)} transactions.")

    valid_transactions.sort(key=calculate_transaction_fee, reverse=True)
    print("Sorted transactions by fee in descending order.")

    coinbase_tx = create_coinbase_transaction(valid_transactions)
    print("Created coinbase transaction.")

    previous_block_hash = '0000000000000000000000000000000000000000000000000000000000000000'
    block_hash, block_transactions = mine_block([coinbase_tx] + valid_transactions, previous_block_hash)

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
