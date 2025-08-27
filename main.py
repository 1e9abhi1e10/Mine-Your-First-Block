import json
import os
from mine_block_script import preprocess_transaction, mine_block_with_transactions, calculate_block_weight_and_fee

# Constants
MEMPOOL_DIR = "mempool"
OUTPUT_FILE = "output.txt"
DIFFICULTY_TARGET = "0000ffff00000000000000000000000000000000000000000000000000000000"
BLOCK_VERSION = 4  # Update to the correct block version
# Define the witness reserved value
WITNESS_RESERVED_VALUE = '0000000000000000000000000000000000000000000000000000000000000000'
WTXID_COINBASE = bytes(32).hex()


def main():
    # Read transaction files
    transactions = []

    # Prefer cache when available, otherwise read from mempool directory
    cache_path = "valid_txn_cache.json"
    if os.path.exists(cache_path):
        with open(cache_path, "r") as file:
            unverified_txns = json.load(file)
        source_iter = unverified_txns
    else:
        filenames = [f for f in os.listdir(MEMPOOL_DIR) if f.endswith('.json')]
        filenames.sort()
        source_iter = []
        for name in filenames:
            path = os.path.join(MEMPOOL_DIR, name)
            try:
                with open(path, "r") as f:
                    source_iter.append(json.load(f))
            except Exception:
                continue

    for tx in source_iter[:2150]:
        verified_tx = preprocess_transaction(tx)
        transactions.append(verified_tx)

    print(f"Total transactions: {len(transactions)}")

    if not any(transactions):
        raise ValueError("No valid transactions to include in the block")

    # Mine the block
    block_header, txids, nonce, coinbase_tx_hex, coinbase_txid = mine_block_with_transactions(transactions)

    # Corrected writing to output file
    with open(OUTPUT_FILE, "w") as file:
        file.write(f"{block_header}\n{coinbase_tx_hex}\n{coinbase_txid}\n")
        file.writelines(f"{txid}\n" for txid in txids)

    # Print the total weight and fee of the transactions in the block
    total_weight, total_fee = calculate_block_weight_and_fee(transactions)
    print(f"Total weight: {total_weight}")
    print(f"Total fee: {total_fee}")

if __name__ == "__main__":
    main()
