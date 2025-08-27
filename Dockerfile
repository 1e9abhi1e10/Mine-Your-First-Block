FROM python:3.11-slim

# Install system dependencies
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only required files first to leverage Docker layer caching
COPY README.md SOLUTION.md run.sh main.py mine_block_script.py operations.py validate_txn_main.py /app/
COPY _utils /app/_utils
COPY mempool /app/mempool

# Ensure run.sh is executable
RUN chmod +x /app/run.sh

# Default command
CMD ["/app/run.sh"]


