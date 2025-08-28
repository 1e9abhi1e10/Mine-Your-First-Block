
# Summer of Bitcoin 2024: Mine your first block

## Overview
In this challenge, you are tasked with the simulation of mining process of a block, which includes validating and including transactions from a given set of transactions.
The repository contains a folder `mempool` which contains JSON files. 
These files represent individual transactions, some of which may be invalid. Your goal is to successfully mine a block by including only the valid transactions, following the specific requirements outlined below.

## Objective
Your primary objective is to write a script that processes a series of transactions, validates them, and then mines them into a block. The output of your script should be a file named `output.txt` that follows a specific format.

## Requirements
### Input
- You are provided with a folder named `mempool` containing several JSON files. Each file represents a transaction that includes all necessary information for validation.
- Among these transactions, some are invalid. Your script should be able to discern valid transactions from invalid ones.

### Output
Your script must generate an output file named `output.txt` with the following structure:
- First line: The block header.
- Second line: The serialized coinbase transaction.
- Following lines: The transaction IDs (txids) of the transactions mined in the block, in order. The first txid should be that of the coinbase transaction

### Difficulty Target
The difficulty target is `0000ffff00000000000000000000000000000000000000000000000000000000`. This is the value that the block hash must be less than for the block to be successfully mined.

## Execution
- Create a file named `run.sh` that contains the command to execute your script. This file should ideally contain a single command like `python main.py` or `node index.js`.
- Your script should autonomously perform all tasks when `run.sh` is executed, without requiring any manual intervention.

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

A GitHub Actions workflow builds the Docker image and runs the project on each push to `main`. It also uploads `output.txt` as a build artifact.

## Results

Add your latest run metrics here after a successful run:

- Total fees (sats): <fill>
- Block weight: <fill>
- Runtime: <fill>

To run a tiny sanity test locally:

```
python3 tests_smoke.py
```

