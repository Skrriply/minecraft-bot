# ⛏️ Minecraft Discord Bot

A Discord bot built with [Python](https://www.python.org/) and [disnake](https://disnake.dev/) for my friends and me. It helps protect your self-hosted Minecraft server from data corruption during sudden power outages and provides several other useful features.

## ✨ Features

- ⚡ **Automated power management.** Continually scrapes and monitors DTEK power outage schedules in the background.
- 🛑 **Graceful shutdown.** Safely stops the Minecraft server and initiates a shutdown command to the Proxmox host 10 minutes before the outage.
- 🎮 **Pterodactyl integration.** Start, stop, restart, kill, and send remote console commands to your Minecraft server directly from Discord.
- 📊 **Server status.** Real-time CPU, RAM, disk usage, server state, and upcoming DTEK power schedules.

## ⚙️ Prerequisites

1. Proxmox VE host with API access enabled.
   - Ensure your server's motherboard BIOS has **"Restore on AC Power Loss"** (or similar) set to **"Power On"** so the host boots automatically when power restores.
   - It is recommended to create a dedicated, unprivileged user for the bot, granting it only the permission to shut down the server (`Sys.PowerMgmt`).
2. Pterodactyl Panel with a generated Client API key.
3. Discord bot application with the necessary intents.

## 🚀 Installation & Setup

### 1. Manual

#### 1. Clone the repository.

```bash
git clone https://github.com/Skrriply/minecraft-bot.git
cd minecraft-bot
```

#### 2. Install dependencies.

It's recommended to use [uv](https://docs.astral.sh/uv/).

```bash
python -m pip install uv
python -m uv sync --no-dev
python -m uv run camoufox fetch
```

#### 3. Configure environment variables.

Create a copy of the `.env.example` file in the root directory and rename it to `.env`, then fill in the required variables.

#### 4. Run the bot.

```bash
python -m uv run ./src/bot/main.py
```

---

### 2. Using [Pterodactyl](https://pterodactyl.io/)

1. Create a new Nest in your Pterodactyl Panel settings.
2. Download the [egg-minecraft-bot.json](https://github.com/Skrriply/minecraft-bot/blob/main/egg-minecraft-bot.json) file.
3. Import the downloaded file into Pterodactyl and assign it to the Nest you just created.
4. Create a new server using this Egg.
5. After the server installing create a copy of the `.env.example` file in the root directory, rename it to `.env`, then fill in the required variables.
6. Start the server.

## 📜 Discord Slash Commands

| Command       | Description                                                       | Permissions              |
| ------------- | ----------------------------------------------------------------- | ------------------------ |
| /start        | 🚀 Sends a start signal to the Minecraft server.                  | Everyone (with cooldown) |
| /status       | 📊 Displays current Minecraft server resources and DTEK schedule. | Everyone                 |
| /power        | 🔌 Sends a power action (start, stop, restart, kill).             | Bot owner only           |
| /cmd          | 🛠️ Sends a command directly to the Minecraft console.             | Bot owner only           |

## ⚖️ License

Distributed under the [GPL-3.0 License](https://github.com/Skrriply/minecraft-bot/blob/main/LICENSE).
