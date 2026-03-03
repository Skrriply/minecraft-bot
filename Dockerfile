FROM python:3.14-slim

# Python environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System dependencies
# https://camoufox.com/python/installation/#debian-based-distros
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ca-certificates \
    libgtk-3-0 \
    libx11-xcb1 \
    libasound2 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# User configuration & permissions
RUN adduser --disabled-password --home /home/container container

COPY --chown=container:container ./entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER container
WORKDIR /home/container
ENV USER=container HOME=/home/container

# Pterodactyl environment overrides
ENV USER=container \
    HOME=/home/container \
    TMPDIR=/home/container/tmp \
    UV_CACHE_DIR=/home/container/.cache/uv \
    XDG_CACHE_HOME=/home/container/.cache

CMD ["/bin/bash", "/entrypoint.sh"]
