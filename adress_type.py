import hashlib
import json
import os


def to_hash160(hex_input):
    """
    Compute the RIPEMD-160 hash of the SHA-256 hash of the input hex string.

    :param hex_input: A hexadecimal string to be hashed.
    :return: A hexadecimal string representing the RIPEMD-160 hash of the input.
    """
    sha = hashlib.sha256(bytes.fromhex(hex_input)).hexdigest()
    hash_160 = hashlib.new("ripemd160")
    hash_160.update(bytes.fromhex(sha))
    return hash_160.hexdigest()


def to_compact_size(value):
    """
    Encode an integer value into Bitcoin's variable-length integer format.

    :param value: The integer value to encode.
    :return: A hexadecimal string representing the encoded integer.
    """
    if value < 0xFD:
        return value.to_bytes(1, byteorder="little").hex()
    elif value <= 0xFFFF:
        return (0xFD).to_bytes(1, byteorder="little").hex() + value.to_bytes(2, byteorder="little").hex()
    elif value <= 0xFFFFFFFF:
        return (0xFE).to_bytes(1, byteorder="little").hex() + value.to_bytes(4, byteorder="little").hex()
    else:
        return (0xFF).to_bytes(1, byteorder="little").hex() + value.to_bytes(8, byteorder="little").hex()


def to_little_endian(num, size):
    """
    Convert an integer to a little-endian hexadecimal string of a given size.

    :param num: The integer value to convert.
    :param size: The size (in bytes) of the resulting hexadecimal string.
    :return: A hexadecimal string representing the little-endian byte representation of the integer.
    """
    return num.to_bytes(size, byteorder="little").hex()


def generate_transaction_hash(txn_id):
    """
    Generate a hash for a transaction given its ID by reading the corresponding JSON file.

    This function constructs the transaction hash by concatenating various parts of the transaction data,
    such as version, number of inputs and outputs, and other relevant information.

    :param txn_id: The transaction ID for which to generate the hash.
    :return: A string representing the transaction hash.
    """
    transaction_hash = ""
    file_path = os.path.join("mempool", f"{txn_id}.json")
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            data = json.load(f)
            # Version
            transaction_hash += f"{to_little_endian(data['version'], 4)}"
            # Number of inputs
            transaction_hash += f"{str(to_compact_size(len(data['vin'])))}"
            for input_transaction in data["vin"]:
                # Input transaction ID
                transaction_hash += f"{bytes.fromhex(input_transaction['txid'])[::-1].hex()}"
                # Output index
                transaction_hash += f"{to_little_endian(input_transaction['vout'], 4)}"
                # ScriptPubKey length
                transaction_hash += f"{to_compact_size(len(input_transaction['prevout']['scriptpubkey'])//2)}"
                # ScriptPubKey
                transaction_hash += f"{input_transaction['prevout']['scriptpubkey']}"
                # Sequence
                transaction_hash += f"{to_little_endian(input_transaction['sequence'], 4)}"
            # Number of outputs
            transaction_hash += f"{str(to_compact_size(len(data['vout'])))}"
            for output_transaction in data["vout"]:
                # Output value
                transaction_hash += f"{to_little_endian(output_transaction['value'], 8)}"
                # ScriptPubKey length
                transaction_hash += f"{to_compact_size(len(output_transaction['scriptpubkey'])//2)}"
                # ScriptPubKey
                transaction_hash += f"{output_transaction['scriptpubkey']}"
            # Locktime
            transaction_hash += f"{to_little_endian(data['locktime'], 4)}"
    return transaction_hash


def validate_p2sh_txn_basic(inner_redeemscript_asm, scriptpubkey_asm):
    """
    Perform a basic validation of a Pay-to-Script-Hash (P2SH) transaction.

    This function checks if the provided redeem script and scriptPubKey lead to the same hash.

    :param inner_redeemscript_asm: The assembly string of the inner redeem script.
    :param scriptpubkey_asm: The assembly string of the scriptPubKey.
    :return: True if the validation passes, False otherwise.
    """
    inner_script = inner_redeemscript_asm.split(" ")
    scriptpubkey = scriptpubkey_asm.split(" ")

    stack = []
    redeem_script = ""

    for i in inner_script:
        if i == "OP_0":
            redeem_script += "00"
        if i == "OP_PUSHNUM_2":
            redeem_script += "02"
        if i == "OP_PUSHBYTES_20":
            redeem_script += "14"
            redeem_script += inner_script[inner_script.index("OP_PUSHBYTES_20") + 1]
        if i == "OP_PUSHBYTES_33":
            redeem_script += "21"
            redeem_script += inner_script[inner_script.index("OP_PUSHBYTES_33") + 1]

    stack.append(redeem_script)

    for i in scriptpubkey:
        if i == "OP_HASH160":
            # Compute RIPEMD-160 hash
            ripemd160_hash = to_hash160(stack[-1])
            stack.pop(-1)
            stack.append(ripemd160_hash)

        if i == "OP_PUSHBYTES_20":
            stack.append(scriptpubkey[scriptpubkey.index("OP_PUSHBYTES_20") + 1])

        if i == "OP_EQUAL":
            return stack[-1] == stack[-2]


def validate_p2sh_txn_adv(inner_redeemscript_asm, scriptpubkey_asm, scriptsig_asm, txn_data):
    """
    Placeholder for advanced P2SH transaction validation logic.

    This function should include more advanced validation such as signature verification.

    :param inner_redeemscript_asm: The assembly string of the inner redeem script.
    :param scriptpubkey_asm: The assembly string of the scriptPubKey.
    :param scriptsig_asm: The assembly string of the scriptSig.
    :param txn_data: The transaction data.
    :return: True if the validation passes, False otherwise.
    """
    inner_redeemscript = inner_redeemscript_asm.split(" ")
    scriptpubkey = scriptpubkey_asm.split(" ")
    scriptsig = scriptsig_asm.split(" ")

    redeem_stack = []
    signatures = []

    for item in scriptsig:
        if "OP_PUSHBYTES_" in item:
            # Extract signatures
            signatures.append(scriptsig[scriptsig.index(item) + 1])
            scriptsig[scriptsig.index(item)] = "DONE"

    for item in inner_redeemscript:
        if "OP_PUSHNUM_" in item:
            num = item[len("OP_PUSHNUM_") :]
            redeem_stack.append(int(num))

        if "OP_PUSHBYTES_" in item:
            redeem_stack.append(inner_redeemscript[inner_redeemscript.index(item) + 1])
            inner_redeemscript[inner_redeemscript.index(item)] = "DONE"

        if "OP_CHECKMULTISIG" in item:
            msg = txn_data + "01000000"
            msg_hash = hashlib.sha256(bytes.fromhex(msg)).digest().hexdigest()

    return True  # Placeholder for actual validation logic


def validate_advanced_p2sh_transaction():
    """
    Entry point for validating an advanced P2SH transaction.

    Currently, this function prints the validation result of a hardcoded transaction.

    :return: None
    """
    # ADVANCED Txn
    filename = "0dd03993f8318d968b7b6fdf843682e9fd89258c186187688511243345c2009f"
    file_path = os.path.join("mempool", f"{filename}.json")
    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            txn_data = json.load(file)

    redeemscript_asm = txn_data["vin"][0]["inner_redeemscript_asm"]
    scriptpubkey_asm = txn_data["vin"][0]["prevout"]["scriptpubkey_asm"]
    scriptsig_asm = txn_data["vin"][0]["scriptsig_asm"]
    txn_data = generate_transaction_hash(filename)
    print(f"txn_data: {txn_data}\n")
    print(
        f"p2sh(adv)::> {validate_p2sh_txn_adv(redeemscript_asm, scriptpubkey_asm, scriptsig_asm, txn_data)}"
    )
