import hashlib

def to_compact_size(value):
    if value < 0xfd:
        return value.to_bytes(1, byteorder='little').hex()
    elif value <= 0xffff:
        return (0xfd).to_bytes(1, byteorder='little').hex() + value.to_bytes(2, byteorder='little').hex()
    elif value <= 0xffffffff:
        return (0xfe).to_bytes(1, byteorder='little').hex() + value.to_bytes(4, byteorder='little').hex()
    else:
        return (0xff).to_bytes(1, byteorder='little').hex() + value.to_bytes(8, byteorder='little').hex()

def to_little_endian(num, size):
    return num.to_bytes(size, byteorder='little').hex()

def to_reverse_bytes_string(hex_input):
    return bytes.fromhex(hex_input)[::-1].hex()

def to_hash256(hex_input):
    return hashlib.sha256(hashlib.sha256(bytes.fromhex(hex_input)).digest()).digest().hex()

def serialize_txn(txn_dict):
    transaction_hash = ""
    data = txn_dict

    # Version
    transaction_hash += to_little_endian(data['version'], 4)

    # No. of inputs:
    transaction_hash += str(to_compact_size(len(data['vin'])))

    # Inputs
    for input in data["vin"]:
        transaction_hash += to_reverse_bytes_string(input['txid'])
        transaction_hash += to_little_endian(input['vout'], 4)
        transaction_hash += to_compact_size(len(input['scriptsig']) // 2)
        transaction_hash += input['scriptsig']
        transaction_hash += to_little_endian(input['sequence'], 4)

    # No. of outputs
    transaction_hash += str(to_compact_size(len(data['vout'])))

    # Outputs
    for output in data["vout"]:
        transaction_hash += to_little_endian(output['value'], 8)
        transaction_hash += to_compact_size(len(output['scriptpubkey']) // 2)
        transaction_hash += output['scriptpubkey']

    # Locktime
    transaction_hash += to_little_endian(data['locktime'], 4)
    return transaction_hash

def wtxid_serialize(txn_data):
    transaction_hash = ""
    data = txn_data

    # Version
    transaction_hash += to_little_endian(data['version'], 4)

    # Marker+flags (if any `vin` has empty scriptsig)
    if any(input.get("scriptsig") == "" for input in data["vin"]):
        transaction_hash += "0001"

    # No. of inputs:
    transaction_hash += to_compact_size(len(data['vin']))

    # Inputs
    for input in data["vin"]:
        transaction_hash += to_reverse_bytes_string(input['txid'])
        transaction_hash += to_little_endian(input['vout'], 4)
        transaction_hash += to_compact_size(len(input['scriptsig']) // 2)
        transaction_hash += input['scriptsig']
        transaction_hash += to_little_endian(input['sequence'], 4)

    # No. of outputs
    transaction_hash += to_compact_size(len(data['vout']))

    # Outputs
    for output in data["vout"]:
        transaction_hash += to_little_endian(output['value'], 8)
        transaction_hash += to_compact_size(len(output['scriptpubkey']) // 2)
        transaction_hash += output['scriptpubkey']

    # Witness
    for input in data["vin"]:
        if "witness" in input and input["witness"]:
            transaction_hash += to_compact_size(len(input['witness']))
            for j in input["witness"]:
                transaction_hash += to_compact_size(len(j) // 2)
                transaction_hash += j

    # Locktime
    transaction_hash += to_little_endian(data['locktime'], 4)

    return transaction_hash

def serialize_coinbase_transaction(witness_commitment):
    tx_dict = {
        "version": "01000000",
        "marker": "00",
        "flag": "01",
        "inputcount": "01",
        "inputs": [
            {
                "txid": "0000000000000000000000000000000000000000000000000000000000000000",
                "vout": "ffffffff",
                "scriptsigsize": "25",
                "scriptsig": "03233708184d696e656420627920416e74506f6f6c373946205b8160a4256c0000946e0100",
                "sequence": "ffffffff",
            }
        ],
        "outputcount": "02",
        "outputs": [
            {
                "amount": "f595814a00000000",
                "scriptpubkeysize": "19",
                "scriptpubkey": "76a914edf10a7fac6b32e24daa5305c723f3de58db1bc888ac",
            },
            {
                "amount": "0000000000000000",
                "scriptpubkeysize": "26",
                "scriptpubkey": f"6a24aa21a9ed{witness_commitment}",
            },
        ],
        "witness": [
            {
                "stackitems": "01",
                "0": {
                    "size": "20",
                    "item": "0000000000000000000000000000000000000000000000000000000000000000",
                },
            }
        ],
        "locktime": "00000000",
    }
    tx_dict_modified = {
        "version": 1,
        "marker": "00",
        "flag": "01",
        "inputcount": "01",
        "vin": [
            {
                "txid": "0000000000000000000000000000000000000000000000000000000000000000",
                "vout": int("ffffffff", 16),
                "scriptsigsize": 37,
                "scriptsig": "03233708184d696e656420627920416e74506f6f6c373946205b8160a4256c0000946e0100",
                "sequence": int("ffffffff", 16),
            }
        ],
        "outputcount": "02",
        "vout": [
            {
                "value": 2753059167,
                "scriptpubkeysize": "19",
                "scriptpubkey": "76a914edf10a7fac6b32e24daa5305c723f3de58db1bc888ac",
            },
            {
                "value": 0,
                "scriptpubkeysize": "26",
                "scriptpubkey": f"6a24aa21a9ed{witness_commitment}",
            },
        ],
        "witness": [
            {
                "stackitems": "01",
                "0": {
                    "size": "20",
                    "item": "0000000000000000000000000000000000000000000000000000000000000000",
                },
            }
        ],
        "locktime": 0,
    }
    # Version
    serialized_tx = tx_dict["version"]

    # Marker and Flag
    serialized_tx += tx_dict["marker"] + tx_dict["flag"]

    # Input Count
    serialized_tx += tx_dict["inputcount"]

    # Input
    input_data = tx_dict["inputs"][0]
    serialized_tx += input_data["txid"]
    serialized_tx += input_data["vout"]
    serialized_tx += input_data["scriptsigsize"].zfill(2)
    serialized_tx += input_data["scriptsig"]
    serialized_tx += input_data["sequence"]

    # Output Count
    serialized_tx += tx_dict["outputcount"]

    # Outputs
    for output in tx_dict["outputs"]:
        serialized_tx += output["amount"].zfill(16)
        serialized_tx += output["scriptpubkeysize"].zfill(2)
        serialized_tx += output["scriptpubkey"]

    # Witness
    witness_data = tx_dict["witness"][0]
    serialized_tx += witness_data["stackitems"]
    serialized_tx += witness_data["0"]["size"].zfill(2)
    serialized_tx += witness_data["0"]["item"]

    # Locktime
    serialized_tx += tx_dict["locktime"]

    # Serialize the modified transaction dictionary
    serialized_tx_modified = serialize_txn(tx_dict_modified)

    # Compute the wtxid
    wtxid = to_reverse_bytes_string(to_hash256(serialized_tx_modified))

    return serialized_tx, wtxid
