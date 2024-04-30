import json

# Constants
JSON_FILE = 'cache.json'

def main():
    """Main function that processes the JSON data."""
    try:
        with open(JSON_FILE, 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        print(f"The file {JSON_FILE} was not found.")
        return
    except json.JSONDecodeError:
        print(f"Error decoding JSON from the file {JSON_FILE}.")
        return

    for transaction in data:
        transaction_inputs = transaction.get('vin')
        if len(transaction_inputs) == 1:
            prevout = transaction_inputs[0].get('prevout')
            if prevout and prevout.get('scriptpubkey_type') == 'p2pkh':
                print(prevout.get('scriptpubkey_asm'))
                print(prevout.get('scriptpubkey_type'))

if __name__ == "__main__":
    main()
