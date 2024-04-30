import json
import os
import hashlib
import time
import binascii
from _utils.hash_utils import hash256
from _utils.transaction_utils import to_reverse_bytes_string, wtxid_serialize, serialize_txn, serialize_coinbase_transaction

# Constants
MEMPOOL_DIR = "mempool"
DIFFICULTY_TARGET = "0000ffff00000000000000000000000000000000000000000000000000000000"
BLOCK_VERSION = 4  # Update to the correct block version
# Define the witness reserved value
WITNESS_RESERVED_VALUE = '0000000000000000000000000000000000000000000000000000000000000000'
WTXID_COINBASE = bytes(32).hex()

def get_fee(transaction):
    """
    Calculate the fee for a transaction.

    The fee is determined by subtracting the total output value from the total input value of the transaction.

    :param transaction: A dictionary representing the transaction with 'vin' and 'vout' as keys.
    :return: The calculated fee as an integer.
    """
    input_values = [int(i["prevout"]["value"]) for i in transaction["vin"]]
    total_input_value = sum(input_values)
    output_values = [int(i["value"]) for i in transaction["vout"]]
    total_output_value = sum(output_values)
    return total_input_value - total_output_value


def preprocess_transaction(transaction):
    """
    Pre-process a transaction by calculating its txid, wtxid, and fee.

    This function takes a transaction dictionary, calculates and assigns a txid and wtxid by serializing
    the transaction and hashing it. It also calculates the fee by using the get_fee function if it's not
    already present in the transaction dictionary.

    :param transaction: A dictionary representing the transaction to be pre-processed.
    :return: The pre-processed transaction with added 'txid', 'wtxid', and 'fee' keys.
    """
    global num_p2pkh, num_p2wpkh, num_p2sh
    transaction["txid"] = to_reverse_bytes_string(hash256(serialize_txn(transaction)))
    transaction["weight"] = 1  # Assign a fixed weight of 1 for simplicity
    transaction["wtxid"] = to_reverse_bytes_string(hash256(wtxid_serialize(transaction)))
    transaction["fee"] = transaction.get(
        "fee", get_fee(transaction)
    )  # Assign a default fee if not present
    return transaction


def read_transactions_from_file(filename):
    """
    Read a JSON transaction file and return the transaction data.
    """
    with open(os.path.join(MEMPOOL_DIR, filename), "r") as file:
        transaction = json.load(file)

    preprocess_transaction(transaction)
    return transaction


def is_valid_transaction(transaction):
    """
    Validate a transaction.

    Currently, this function assumes all transactions are valid for the purpose of this challenge.
    In a real-world scenario, this function would include checks against transaction structure,
    signatures, and other rules specific to the blockchain implementation.

    :param transaction: A dictionary representing the transaction to be validated.
    :return: True if the transaction is valid, False otherwise.
    """
    # For the purpose of this challenge, we assume all transactions are valid
    return True


def validate_header(header, target_difficulty):
    """
    Validate a block header against a target difficulty.

    This function checks if the block header's hash meets the required proof-of-work target difficulty.

    :param header: The block header in hexadecimal format.
    :param target_difficulty: The target difficulty in hexadecimal format.
    :raises ValueError: If the header length is invalid or the block does not meet the target difficulty.
    """
    header_bytes = binascii.unhexlify(header)
    if len(header_bytes) != 80:
        raise ValueError("Invalid header length")

    # Calculate double SHA256 hash of the block header
    h1 = hashlib.sha256(header_bytes).digest()
    h2 = hashlib.sha256(h1).digest()

    # Reverse the hash
    reversed_hash = h2[::-1]

    # Convert hash and target difficulty to integers
    reversed_hash_int = int.from_bytes(reversed_hash, byteorder="big")
    target_int = int(target_difficulty, 16)

    # Check if the hash is less than or equal to the target difficulty
    if reversed_hash_int > target_int:
        raise ValueError("Block does not meet target difficulty")


def difficulty_target_to_bits(target):
    """
    Convert a difficulty target into 'bits', a compact representation used in block headers.

    This function calculates the exponent and coefficient for the compact representation of the target.

    :param target: The difficulty target in hexadecimal format.
    :return: The 'bits' compact representation in hexadecimal format.
    """
    # Convert target to bytes
    target_bytes = bytes.fromhex(target)

    # Find the first non-zero byte
    for i in range(len(target_bytes)):
        if target_bytes[i] != 0:
            break

    # Calculate exponent
    exponent = len(target_bytes) - i

    # Calculate coefficient
    if len(target_bytes[i:]) >= 3:
        coefficient = int.from_bytes(target_bytes[i : i + 3], byteorder="big")
    else:
        coefficient = int.from_bytes(target_bytes[i:], byteorder="big")

    # Combine exponent and coefficient into bits
    bits = (exponent << 24) | coefficient

    # Return bits as a hexadecimal string
    return hex(bits)


def mine_block_with_transactions(transactions):
    """
    Attempt to mine a block with the given transactions by finding a valid nonce.

    This function constructs a block header and iterates over nonce values to
    
    Attempt to mine a block with the given transactions by finding a valid nonce.

    This function constructs a block header and iterates over nonce values to find one that results in a block hash
    that is below the difficulty target. It also constructs the coinbase transaction and calculates the Merkle root.

    :param transactions: A list of pre-processed transaction dictionaries.
    :return: A tuple containing the block header in hexadecimal format, list of transaction IDs, nonce, coinbase transaction in hexadecimal format, and coinbase transaction ID.
    :raises ValueError: If the nonce range is invalid.
    """
    nonce = 0
    txids = [
        tx["txid"]
        for tx in transactions
    ]

    # Create a coinbase transaction with no inputs and two outputs: one for the block reward and one for the witness commitment
    witness_commitment = calculate_witness_root(transactions)
    print("witneness commitment:", witness_commitment)

    coinbase_hex, coinbase_txid = serialize_coinbase_transaction(
        witness_commitment=witness_commitment
    )

    # Calculate the Merkle root of the transactions
    merkle_root = calculate_merkle_root([coinbase_txid]+txids)

    # Construct the block header
    block_version_bytes = BLOCK_VERSION.to_bytes(4, "little")
    prev_block_hash_bytes = bytes.fromhex(
        "0000000000000000000000000000000000000000000000000000000000000000"
    )
    merkle_root_bytes = bytes.fromhex(merkle_root)
    timestamp_bytes = int(time.time()).to_bytes(4, "little")
    bits_bytes = (0x1F00FFFF).to_bytes(4, "little")
    nonce_bytes = nonce.to_bytes(4, "little")

    # Combine the header parts
    block_header = (
        block_version_bytes
        + prev_block_hash_bytes
        + merkle_root_bytes
        + timestamp_bytes
        + bits_bytes
        + nonce_bytes
    )

    # Attempt to find a nonce that results in a hash below the difficulty target
    target = int(DIFFICULTY_TARGET, 16)
    print("target:", target)
    while True:
        block_hash = hashlib.sha256(hashlib.sha256(block_header).digest()).digest()
        reversed_hash = block_hash[::-1]
        if int.from_bytes(reversed_hash, "big") <= target:
            break
        nonce += 1
        nonce_bytes = nonce.to_bytes(4, "little")
        block_header = block_header[:-4] + nonce_bytes  # Update the nonce in the header
        # Validate nonce range within the mining loop
        if nonce < 0x0 or nonce > 0xFFFFFFFF:
            raise ValueError("Invalid nonce")

    block_header_hex = block_header.hex()
    validate_header(block_header_hex, DIFFICULTY_TARGET)

    return block_header_hex, txids, nonce, coinbase_hex, coinbase_txid


def calculate_merkle_root(txids):
    """
    Generate a Merkle root from a list of transaction IDs.

    This function recursively hashes pairs of transaction IDs (or a single ID duplicated if the number of IDs is odd)
    until a single hash remains, which is the Merkle root.

    :param txids: A list of transaction IDs in hexadecimal format.
    :return: The Merkle root in hexadecimal format, or None if the list of transaction IDs is empty.
    """
    if len(txids) == 0:
        return None

    # Reverse the txids
    level = [bytes.fromhex(txid)[::-1].hex() for txid in txids]

    while len(level) > 1:
        next_level = []
        for i in range(0, len(level), 2):
            if i + 1 == len(level):
                # In case of an odd number of elements, duplicate the last one
                pair_hash = hash256(level[i] + level[i])
            else:
                pair_hash = hash256(level[i] + level[i + 1])
            next_level.append(pair_hash)
        level = next_level
    return level[0]


def calculate_block_weight_and_fee(transactions):
    """
    Calculate the total weight and fee of the transactions in a block.

    This function sums the weight and fee of each transaction to calculate the total weight and fee of the block.

    :param transactions: A list of transaction dictionaries with 'weight' and 'fee' keys.
    :return: A tuple containing the total weight and total fee of the transactions.
    :raises ValueError: If the block exceeds the maximum weight.
    """
    total_weight = 0
    total_fee = 0
    for tx in transactions:
        total_weight += tx["weight"]
        total_fee += tx["fee"]

    if total_weight > 4000000:
        raise ValueError("Block exceeds maximum weight")

    return total_weight, total_fee


def calculate_witness_root(transactions):
    """
    Calculate the witness root for a block.

    This function generates a Merkle root of the witness transaction IDs (wtxids) and combines it with a reserved value
    to calculate the witness root.

    :param transactions: A list of transaction dictionaries with 'wtxid' keys.
    :return: The witness root in hexadecimal format.
    """
    wtxids = [WTXID_COINBASE]
    for tx in transactions:
        wtxids.append(tx["wtxid"])
    witness_root = calculate_merkle_root(wtxids)

    # Combine the witness root and the witness reserved value
    combined_data = witness_root + WITNESS_RESERVED_VALUE

    # Calculate the hash
    witness_root_hash = hash256(combined_data)

    return witness_root_hash


def is_witness_commitment_valid(coinbase_tx, witness_commitment):
    """
    Verify the witness commitment in the coinbase transaction.

    This function checks if the coinbase transaction contains an output with a script that includes the witness commitment.

    :param coinbase_tx: The coinbase transaction dictionary with 'vout' key containing a list of outputs.
    :param witness_commitment: The witness commitment in hexadecimal format to verify.
    :return: True if the witness commitment is verified, False otherwise.
    """
    for output in coinbase_tx["vout"]:
        script_hex = output["scriptPubKey"]["hex"]
        if script_hex.startswith("6a24aa21a9ed") and script_hex.endswith(
            witness_commitment
        ):
            return True
    return False
