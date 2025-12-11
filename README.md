# Telegram Music Bot

This is a simple Telegram bot that can search for and download music using Jamendo, Deezer (via Deemix),
and a YouTube fallback (yt-dlp).

## Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/telegram-music-bot.git
   cd telegram-music-bot
   ```

2. **Install the dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the bot:**

   - Set your environment variables first (or create a .env file and load it via your shell or a manager like `direnv`):

   ```bash
   export TELEGRAM_BOT_TOKEN="<your_telegram_token>"
   export JAMENDO_CLIENT_ID="<your_jamendo_client_id>"
   export JAMENDO_TOKEN="<your_jamendo_token>"
   # Optional: DEEMIX_ARL for a logged Deezer account if you use Deemix for higher bitrate downloads
   export DEEMIX_ARL="<your_deemix_arl_cookie>"
   ```

   - Install dependencies in a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

   - Ensure `ffmpeg` is installed on your system for `yt-dlp` audio post-processing:
   ```bash
   # Debian/Ubuntu
   sudo apt update && sudo apt install -y ffmpeg
   # Fedora
   sudo dnf install -y ffmpeg
   ```

   - Run the bot:
   ```bash
   python bot.py
   ```

## Usage

- Start a conversation with the bot on Telegram.
- Send the `/start` command to see the welcome message.
- Send any song name to the bot, and it will search for the song, download it, and send it to you as an audio file.

## Note

This bot uses Jamendo (for legal downloadable tracks), Deemix/Deezer (for tracks available via Deemix), and falls back to `yt-dlp`/YouTube for tracks not available via the other sources.

Notes:
- Provide a `DEEMIX_ARL` cookie to get better results with Deemix; otherwise, the bot will work for previews or tracks Deemix can access without a logged-in session.
- If you exposed your `TELEGRAM_BOT_TOKEN` in a commit, rotate it immediately — the token in this repository may have been committed earlier. Consider removing secrets and using environment variables.
- Add large media files to `.gitignore` (already included in this repo) to keep the repository clean.

If you want me to create a Pull Request for the changes made in the `feat/jamendo-yt-fallback` branch, I can push any additional changes and open the PR for you.
# telegram-music-bot
