#!/bin/bash

cd /home/container || exit 1

# 1. Environment initialization
echo "[Setup] Initializing environment..."
mkdir -p "${TMPDIR}"

# 2. Code update via Git
if [ -d ".git" ]; then
    echo "[Setup] Pulling updates from the Git repository..."
    git pull || echo "[Warning] Failed to update the repository. Continuing startup..."
fi

# 3. Dependency installation
echo "[Setup] Synchronizing dependencies and fetching Camoufox..."
uv sync --no-dev
uv run camoufox fetch

# 4. Configuration check
if [ ! -f ".env" ]; then
    echo "[Warning] A .env file was not found in the root directory!"
fi

# 5. Pterodactyl command processing
echo "[Run] Formatting startup command..."
MODIFIED_STARTUP=$(eval echo $(echo ${STARTUP} | sed -e 's/{{/${/g' -e 's/}}/}/g'))

# Output the final command for debugging purposes
echo ":/home/container$ ${MODIFIED_STARTUP}"

# 6. Server startup
eval exec ${MODIFIED_STARTUP}
