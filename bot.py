import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
from deemix import generateDownloadObject
from deezer import Deezer
from deemix.settings import load as load_settings

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = "7722903971:AAGLv2brYFSggIc4DscNHJTxL9AsmBNHkko"
DEEZER_API_URL = "https://api.deezer.com/search"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    await update.message.reply_text("Hi! I'm a music bot. Send me a song name and I'll find it for you.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text("Send me a song name and I will search for it on Deezer.")

async def search_music(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Search for music on Deezer and download it."""
    search_query = update.message.text
    if not search_query:
        await update.message.reply_text("Please send me a song name to search.")
        return

    await update.message.reply_text("Searching for your song, please wait...")

    try:
        response = requests.get(DEEZER_API_URL, params={"q": search_query})
        response.raise_for_status()
        data = response.json()

        if data["data"]:
            track = data["data"][0]
            link = track["link"]

            # Set up deemix
            config_folder = os.path.expanduser("~/.config/deemix")
            if not os.path.exists(config_folder):
                os.makedirs(config_folder)
            
            settings = load_settings(config_folder)
            settings["downloadLocation"] = "."

            deezer = Deezer()

            # You might need to log in for better quality, but this works for previews
            # To log in, you would need an ARL cookie.
            # deezer.login_via_arl("your_arl_cookie_here")

            # `maxBitrate` is stored as a string in deemix settings; convert to int
            try:
                bitrate = int(settings.get('maxBitrate', 3))
            except Exception:
                bitrate = 3

            download_object = generateDownloadObject(deezer, link, bitrate)
            # Use the Downloader to perform the actual download
            from deemix.downloader import Downloader
            downloader = Downloader(deezer, download_object, settings)
            downloader.start()
            
            # Find the downloaded file
            files = os.listdir(".")
            for file in files:
                if file.endswith(".mp3"):
                    audio_file = file
                    break
            else:
                await update.message.reply_text("Sorry, I couldn't download the song.")
                return

            await update.message.reply_audio(audio=open(audio_file, "rb"))
            os.remove(audio_file)

        else:
            await update.message.reply_text("Sorry, I couldn't find that song. Please try another one.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching data from Deezer API: {e}")
        await update.message.reply_text("Sorry, I'm having trouble connecting to the music service. Please try again later.")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        await update.message.reply_text("An unexpected error occurred. Please try again later.")

def main() -> None:
    """Start the bot."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Explicitly initialize the application to ensure the underlying ExtBot is
    # initialized before background tasks start. This works around an init/race
    # issue observed on some Python 3.14 + PTB versions.
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if not getattr(application, "_initialized", False):
        loop.run_until_complete(application.initialize())

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_music))

    application.run_polling()

if __name__ == "__main__":
    main()
