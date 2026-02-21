# IPTV Telegram Bot

A Telegram bot that searches for movies and series using the IPTV backend API and returns watch URLs. Users choose Movie or Series, search by name, then (for series) pick season and episode.

## Local setup

1. Copy `.env.example` to `.env` and set your Telegram bot token:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token
   IPTV_BASE_URL=https://iptv-be-production.up.railway.app
   ```
2. Install and run:
   ```bash
   pip install -r requirements.txt
   python main.py
   ```

## Deploy to Railway

1. **Create a new project** on [Railway](https://railway.app) and connect your repo (or deploy from GitHub).

2. **Add a service** from this repository. Railway will detect Python and use `requirements.txt` and the `Procfile`.

3. **Set environment variables** in the service → Variables:
   - `TELEGRAM_BOT_TOKEN` (required) — from [@BotFather](https://t.me/BotFather)
   - `IPTV_BASE_URL` (optional) — defaults to `https://iptv-be-production.up.railway.app`

4. **Start command** — The `Procfile` runs `python main.py` as a worker. If Railway does not pick it up, set the start command manually in the service settings to:
   ```bash
   python main.py
   ```

5. Deploy. The bot runs as a long-running worker (no web port needed).

**Important:** Only one instance of the bot can run per token. If you see `Conflict: terminated by other getUpdates request`, another process is already polling (e.g. the same bot running locally or in another Railway service). Stop all other instances and run the bot in a single place only.

 ## Requirements

- Python 3.12+
- `TELEGRAM_BOT_TOKEN` in the environment


 