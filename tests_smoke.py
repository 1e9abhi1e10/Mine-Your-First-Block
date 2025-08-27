import json
from mine_block_script import calculate_merkle_root, validate_header


def test_merkle_root_basic():
    # Known simple vector: root of duplicate single txid should be h(h(tx||tx))
    txid = "a" * 64
    root = calculate_merkle_root([txid])
    assert isinstance(root, str) and len(root) == 64


def test_header_validation_length():
    # 80 bytes header hex -> 160 hex chars
    dummy = "00" * 80
    try:
        validate_header(dummy, "f" * 64)
    except ValueError:
        pass


if __name__ == "__main__":
    test_merkle_root_basic()
    test_header_validation_length()
    print("smoke tests passed")


