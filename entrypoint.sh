#!/bin/bash

cd /home/container || exit 1

# 1. Environment initialization
echo "[Setup] Initializing environment..."
mkdir -p "${TMPDIR}"

# 2. Code update via Git
if [ -d ".git" ]; then
    echo "[Git] Pulling updates from the repository..."
    git pull || echo "[Git] Warning: Failed to update the repository. Continuing startup..."
fi

# 3. Dependency installation
echo "[uv] Synchronizing dependencies and fetching Camoufox..."
uv sync --no-dev
uv run camoufox fetch

# 4. Pterodactyl command processing
echo "[Run] Formatting startup command..."
# Replace {{VAR}} syntax with standard bash $VAR syntax
MODIFIED_STARTUP=$(eval echo $(echo ${STARTUP} | sed -e 's/{{/${/g' -e 's/}}/}/g'))

# Output the final command for debugging purposes
echo ":/home/container$ ${MODIFIED_STARTUP}"

# 5. Server startup
eval exec ${MODIFIED_STARTUP}
