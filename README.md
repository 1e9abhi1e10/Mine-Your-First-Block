
# Mine Your First Block

## Overview
This project simulates constructing and mining a Bitcoin-like block from a mempool of JSON transactions, producing an `output.txt` in the expected format. It includes basic preprocessing, Merkle root and witness commitment calculation, and a simple PoW loop under a fixed difficulty target.

## Objective
Process transactions from `mempool/`, assemble a valid block template, and mine a header meeting the target. The script writes an `output.txt` that downstream graders/tools can verify.

## Features
- Reads transactions from `mempool/` (or `valid_txn_cache.json` if present)
- Preprocesses transactions (preserves given `txid` and computes `wtxid`)
- Builds witness commitment and Merkle root
- Mines a header under a fixed target
- Outputs `output.txt` with header, coinbase, and txids

## Output format
`output.txt` contains:
- First line: Block header (hex)
- Second line: Serialized coinbase transaction (hex)
- Following lines: Transaction IDs (txids), starting with the coinbase txid

### Difficulty Target
The difficulty target is `0000ffff00000000000000000000000000000000000000000000000000000000`. This is the value that the block hash must be less than for the block to be successfully mined.

## Execution
`run.sh` runs the end-to-end pipeline without manual input.

### Run locally

- Python 3.11+ required
- Execute:

```
./run.sh
```

### Run with Docker

```
docker build -t myfirstblock:latest .
docker run --rm -v $(pwd):/app myfirstblock:latest
```

The resulting `output.txt` will be written to the mounted project directory.

### Continuous Integration
GitHub Actions workflow `CI` builds the Docker image and runs the project on each push to `main`. It uploads `output.txt` as a build artifact.

Note: The former classroom autograding workflow is disabled in this repository.

## Results

Add your latest run metrics here after a successful run (example values shown below are placeholders):

- Total fees (sats): <fill>
- Block weight: <fill>
- Runtime: <fill>

## Project structure

- `main.py`: Entry point; loads transactions and orchestrates mining
- `mine_block_script.py`: Core logic (preprocessing, merkle, witness, header, PoW)
- `_utils/hash_utils.py`: Hash utilities (double SHA256)
- `_utils/transaction_utils.py`: Serialization helpers
- `mempool/`: JSON transaction files
- `run.sh`: One-shot execution script
- `Dockerfile`: Container image for reproducible runs
- `.github/workflows/ci.yml`: CI build-and-run pipeline
