import os
import json
import hashlib
import coincurve

def validate_signature(signature, message, publicKey):
    """
    Validates a signature against a given message and public key.
    """
    b_sig = bytes.fromhex(signature)
    b_msg = bytes.fromhex(message)
    b_pub = bytes.fromhex(publicKey)
    return coincurve.verify_signature(b_sig, b_msg, b_pub)

def to_compact_size(value):
    """
    Converts an integer to its compact size representation.
    """
    if value < 0xFD:
        return value.to_bytes(1, byteorder="little").hex()
    elif value <= 0xFFFF:
        return (0xFD).to_bytes(1, byteorder="little").hex() + value.to_bytes(2, byteorder="little").hex()
    elif value <= 0xFFFFFFFF:
        return (0xFE).to_bytes(1, byteorder="little").hex() + value.to_bytes(4, byteorder="little").hex()
    else:
        return (0xFF).to_bytes(1, byteorder="little").hex() + value.to_bytes(8, byteorder="little").hex()

def little_endian(num, size):
    """
    Converts an integer to little-endian byte representation.
    """
    return num.to_bytes(size, byteorder="little").hex()

def to_hash160(hex_input):
    sha = hashlib.sha256(bytes.fromhex(hex_input)).hexdigest()
    hash_160 = hashlib.new("ripemd160")
    hash_160.update(bytes.fromhex(sha))

    return hash_160.hexdigest()
def p2pkh_segwit_txn_data(txn_id):
    """
    Constructs preimage data for a SegWit transaction.
    """
    file_path = os.path.join("mempool", f"{txn_id}.json")
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            data = json.load(f)
            ver = little_endian(data['version'], 4)

            # Concatenating (txid + vout) for all inputs
            serialized_txid_vout = ''.join([bytes.fromhex(iN['txid'])[::-1].hex() + little_endian(iN['vout'], 4) for iN in data['vin']])
            hash256_in = hashlib.sha256(hashlib.sha256(bytes.fromhex(serialized_txid_vout)).digest()).digest().hex()

            # Concatenating sequences for all inputs
            serialized_sequence = ''.join([little_endian(iN['sequence'], 4) for iN in data['vin']])
            hash256_seq = hashlib.sha256(hashlib.sha256(bytes.fromhex(serialized_sequence)).digest()).digest().hex()

            # Extracting required input data
            required_input = data['vin'][0]
            ser_tx_vout_sp = bytes.fromhex(required_input['txid'])[::-1].hex() + little_endian(required_input['vout'], 4)
            pkh = required_input['prevout']['scriptpubkey'][6:-4]
            scriptcode = f"1976a914{pkh}88ac"
            in_amt = little_endian(required_input['prevout']['value'], 8)
            sequence_txn = little_endian(required_input['sequence'], 4)

            # Concatenating outputs
            serialized_output = ''.join([little_endian(out['value'], 8) + to_compact_size(len(out['scriptpubkey'])//2) + out['scriptpubkey'] for out in data['vout']])
            hash256_out = hashlib.sha256(hashlib.sha256(bytes.fromhex(serialized_output)).digest()).digest().hex()

            locktime = little_endian(data['locktime'], 4)

            preimage = ver + hash256_in + hash256_seq + ser_tx_vout_sp + scriptcode + in_amt + sequence_txn + hash256_out + locktime
    return preimage

def p2pkh_legacy_txn_data(txn_id):
    """
    Constructs preimage data for legacy (non-SegWit) transaction.
    """
    txn_hash = ""
    file_path = os.path.join("mempool", f"{txn_id}.json")
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            data = json.load(f)
            txn_hash += f"{little_endian(data['version'], 4)}"
            txn_hash += f"{str(to_compact_size(len(data['vin'])))}"
            for iN in data["vin"]:
                txn_hash += f"{bytes.fromhex(iN['txid'])[::-1].hex()}"
                txn_hash += f"{little_endian(iN['vout'], 4)}"
                txn_hash += f"{to_compact_size(len(iN['prevout']['scriptpubkey'])//2)}"
                txn_hash += f"{iN['prevout']['scriptpubkey']}"
                txn_hash += f"{little_endian(iN['sequence'], 4)}"
            txn_hash += f"{str(to_compact_size(len(data['vout'])))}"
            for out in data["vout"]:
                txn_hash += f"{little_endian(out['value'], 8)}"
                txn_hash += f"{to_compact_size(len(out['scriptpubkey'])//2)}"
                txn_hash += f"{out['scriptpubkey']}"
                script_len = len(out['scriptpubkey']) // 2
                if script_len == 25:  # P2PKH script length
                    address_type = 'P2PKH'
                elif script_len == 67:  # P2PK script length
                    address_type = 'P2PK'
                else:
                    address_type = 'UNKNOWN'
                txn_hash += f"{to_compact_size(script_len)}"
                txn_hash += f"{out['scriptpubkey']}"
            txn_hash += f"{little_endian(data['locktime'], 4)}"
    return txn_hash


def validate_p2pkh_txn(signature, public_key, scriptpubkey_asm, txn_data):
    """
    Validates Pay-to-Public-Key-Hash transaction.
    """
    stack = [signature, public_key]

    for instruction in scriptpubkey_asm:
        if instruction == "OP_DUP":
            stack.append(stack[-1])

        elif instruction == "OP_HASH160":
            sha = hashlib.sha256(bytes.fromhex(stack[-1])).hexdigest()
            hash_160 = hashlib.new("ripemd160", bytes.fromhex(sha)).hexdigest()
            stack.pop(-1)
            stack.append(hash_160)

        elif instruction == "OP_EQUALVERIFY":
            if stack[-1] != stack[-2]:
                return False
            stack.pop()
            stack.pop()

        elif instruction == "OP_CHECKSIG":
            if signature[-2:] == "01":  # SIGHASH_ALL ONLY
                der_signature = signature[:-2]
                message = txn_data + "01000000"
                message_hash = hashlib.sha256(bytes.fromhex(message)).digest().hex()
                return validate_signature(der_signature, message_hash, public_key)

        elif instruction == "OP_PUSHBYTES_20":
            stack.append(scriptpubkey_asm[scriptpubkey_asm.index("OP_PUSHBYTES_20") + 1])

    return True

def p2psh_legacy_txn_data(txn_id):
    txn_hash = ""
    file_path = os.path.join("mempool", f"{txn_id}.json")
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
            txn_hash += f"{little_endian(data['version'], 4)}"
            txn_hash += f"{str(to_compact_size(len(data['vin'])))}"
            for iN in data["vin"]:
                txn_hash += f"{bytes.fromhex(iN['txid'])[::-1].hex()}"
                txn_hash += f"{little_endian(iN['vout'], 4)}"
                txn_hash += f"{to_compact_size(len(iN['prevout']['scriptpubkey'])//2)}"
                txn_hash += f"{iN['prevout']['scriptpubkey']}"
                txn_hash += f"{little_endian(iN['sequence'], 4)}"
            txn_hash += f"{str(to_compact_size(len(data['vout'])))}"
            for out in data["vout"]:
                txn_hash += f"{little_endian(out['value'], 8)}"
                txn_hash += f"{to_compact_size(len(out['scriptpubkey'])//2)}"
                txn_hash += f"{out['scriptpubkey']}"
            txn_hash += f"{little_endian(data['locktime'], 4)}"
    except FileNotFoundError:
        print(f"File {file_path} not found.")
    return txn_hash

def validate_p2sh_txn_basic(inner_redeemscript_asm, scriptpubkey_asm):
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
            ripemd160_hash = to_hash160(stack[-1])
            stack.pop(-1)
            stack.append(ripemd160_hash)
        if i == "OP_PUSHBYTES_20":
            stack.append(scriptpubkey[scriptpubkey.index("OP_PUSHBYTES_20") + 1])
        if i == "OP_EQUAL":
            return stack[-1] == stack[-2]


def validate_p2sh_txn_adv(inner_redeemscript_asm, scriptpubkey_asm, scriptsig_asm, txn_data):
    inner_redeemscript = inner_redeemscript_asm.split(" ")
    scriptpubkey = scriptpubkey_asm.split(" ")
    scriptsig = scriptsig_asm.split(" ")
    redeem_stack = []
    signatures = []
    for item in scriptsig:
        if "OP_PUSHBYTES_" in item:
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
    return True  # Modify this according to your validation logic



def p2pwkh_segwit_txn_data(txn_id):
    """
    Constructs a preimage for a SegWit transaction.
    """
    file_path = os.path.join("mempool", f"{txn_id}.json")
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
                ver = f"{little_endian(data['version'], 4)}"
                serialized_txid_vout = ""
                for iN in data["vin"]:
                    serialized_txid_vout += f"{bytes.fromhex(iN['txid'])[::-1].hex()}"
                    serialized_txid_vout += f"{little_endian(iN['vout'], 4)}"
                hash256_in = hashlib.sha256(hashlib.sha256(bytes.fromhex(serialized_txid_vout)).digest()).digest().hex()
                serialized_sequense = ""
                for iN in data["vin"]:
                    serialized_sequense += f"{little_endian(iN['sequence'], 4)}"
                hash256_seq = hashlib.sha256(hashlib.sha256(bytes.fromhex(serialized_sequense)).digest()).digest().hex()

                ser_tx_vout_sp = f"{bytes.fromhex(data['vin'][0]['txid'])[::-1].hex()}{little_endian(data['vin'][0]['vout'], 4)}"
                pkh = f"{data['vin'][0]['prevout']['scriptpubkey'][4:]}"
                scriptcode = f"1976a914{pkh}88ac"
                in_amt = f"{little_endian(data['vin'][0]['prevout']['value'], 8)}"
                sequence_txn = f"{little_endian(data['vin'][0]['sequence'], 4)}"
                serialized_output = ""
                for out in data["vout"]:
                    serialized_output += f"{little_endian(out['value'], 8)}"
                    serialized_output += f"{to_compact_size(len(out['scriptpubkey'])//2)}"
                    serialized_output += f"{out['scriptpubkey']}"
                hash256_out = hashlib.sha256(hashlib.sha256(bytes.fromhex(serialized_output)).digest()).digest().hex()

                locktime = f"{little_endian(data['locktime'], 4)}"

                preimage = (
                    ver + hash256_in + hash256_seq + ser_tx_vout_sp + scriptcode +
                    in_amt + sequence_txn + hash256_out + locktime
                )
                return preimage
        except Exception as e:
            print(f"Error reading JSON file: {e}")
    return ""

def validate_p2wpkh_txn(witness, wit_scriptpubkey_asm, txn_data):
    """
    Validates a Pay-to-Witness-Public-Key-Hash (P2WPKH) transaction.
    """
    wit_sig, wit_pubkey = witness[0], witness[1]
    pkh = wit_scriptpubkey_asm.split(" ")[-1]
    scriptpubkey_asm = [
        "OP_DUP", "OP_HASH160", "OP_PUSHBYTES_20", pkh, "OP_EQUALVERIFY", "OP_CHECKSIG"
    ]
    return validate_signature(wit_sig, txn_data, wit_pubkey) and \
           validate_p2pkh_txn(wit_sig, wit_pubkey, scriptpubkey_asm, txn_data)