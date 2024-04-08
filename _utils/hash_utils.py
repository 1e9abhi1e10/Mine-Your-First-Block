import hashlib

def hash256(hex_string):
    binary = bytes.fromhex(hex_string)
    hash1 = hashlib.sha256(binary).digest()
    hash2 = hashlib.sha256(hash1).digest()
    result = hash2.hex()
    return result
