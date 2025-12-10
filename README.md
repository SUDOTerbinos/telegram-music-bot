# Telegram Music Bot

This is a simple Telegram bot that can search for and download music using the Deezer API.

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
   ```bash
   python bot.py
   ```

## Usage

- Start a conversation with the bot on Telegram.
- Send the `/start` command to see the welcome message.
- Send any song name to the bot, and it will search for the song, download it, and send it to you as an audio file.

## Note

This bot uses the `deemix` library to download music from Deezer. For better quality downloads, you may need to provide a Deezer ARL cookie. You can find instructions on how to get your ARL cookie in the `deemix` documentation.
# telegram-music-bot
