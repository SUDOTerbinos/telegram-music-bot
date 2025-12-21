import logging
import os
from telegram import Update, BotCommand, MenuButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
from deezer import Deezer
from deemix import generateDownloadObject
from deemix.settings import load as load_settings
import tempfile
import shutil
from urllib.parse import quote_plus
import yt_dlp

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = "7722903971:AAGLv2brYFSggIc4DscNHJTxL9AsmBNHkko"
DEEZER_API_URL = "https://api.deezer.com/search"
JAMENDO_CLIENT_ID = os.getenv('JAMENDO_CLIENT_ID') or "9TnoWt3SEKlKfDnUQtSuk7iMB__T9aLENCQ_4GvZqo2nB9VFT9FWTpPL_ofesbIx"
JAMENDO_TOKEN = os.getenv('JAMENDO_TOKEN') or "tHB8YRRan4fIflv0raWKWdyhfzpyhguZzDUj6Dor2yXJ9klr2Pj41cX5kujZ7l9g"
JAMENDO_API = "https://api.jamendo.com/v3.0/tracks"


def jamendo_search_and_download(query: str):
    """Search Jamendo for `query`, download the first result audio and return local file path or (None, error)."""
    try:
        params = {
            'client_id': JAMENDO_CLIENT_ID,
            'format': 'json',
            'limit': 1,
            'search': query,
            'include': 'musicinfo',
        }
        headers = {}
        if JAMENDO_TOKEN:
            headers['Authorization'] = f'Bearer {JAMENDO_TOKEN}'

        resp = requests.get(JAMENDO_API, params=params, headers=headers, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        tracks = data.get('results') or data.get('tracks') or []
        if not tracks:
            return None, "no_results"
        track = tracks[0]

        audio_url = track.get('audiodownload') or track.get('audio') or track.get('download')
        if not audio_url:
            for key, val in track.items():
                if isinstance(val, str) and val.startswith('http') and (val.endswith('.mp3') or 'audio' in key.lower()):
                    audio_url = val
                    break

        if not audio_url:
            return None, "no_download_url"

        tmpdir = tempfile.mkdtemp(prefix='jamendo_')
        try:
            ext = os.path.splitext(audio_url.split('?')[0])[1] or '.mp3'
            safe_title = quote_plus(f"{track.get('artist_name','artist')}-{track.get('name','track')}")
            out_path = os.path.join(tmpdir, f"{safe_title}{ext}")
            with requests.get(audio_url, stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(out_path, 'wb') as f:
                    shutil.copyfileobj(r.raw, f)
            return out_path, None
        except Exception as e:
            try:
                shutil.rmtree(tmpdir)
            except Exception:
                pass
            logger.exception("Error downloading Jamendo audio: %s", e)
            return None, str(e)
    except requests.exceptions.RequestException as e:
        logger.exception("Jamendo API request failed: %s", e)
        return None, 'api_error'
    except Exception as e:
        logger.exception("Unexpected error in Jamendo search: %s", e)
        return None, 'unexpected'


def download_from_youtube(query: str):
    """Search YouTube for `query` and download best audio as MP3 to a temp directory.

    Returns (path, None) on success or (None, error_string) on failure.

    Note: This requires `ffmpeg` to be installed on the host for audio post-processing.
    """
    tmpdir = tempfile.mkdtemp(prefix='yt_')
    try:
        search_query = f"{query} official audio"

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(tmpdir, '%(id)s.%(ext)s'),
            'noplaylist': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
            'writethumbnail': False,
            'writeinfojson': False,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch1:{search_query}", download=True)
            entries = info.get('entries') if isinstance(info, dict) else None
            if entries:
                first = entries[0]
        for fname in os.listdir(tmpdir):
            if fname.lower().endswith('.mp3'):
                return os.path.join(tmpdir, fname), None
        for fname in os.listdir(tmpdir):
            if any(fname.lower().endswith(ext) for ext in ('.m4a', '.opus', '.webm', '.wav')):
                return os.path.join(tmpdir, fname), None
        shutil.rmtree(tmpdir)
        return None, 'no_downloaded_file'
    except yt_dlp.utils.DownloadError as e:
        try:
            shutil.rmtree(tmpdir)
        except Exception:
            pass
        logger.exception('yt-dlp download error: %s', e)
        return None, 'download_error'
    except Exception as e:
        try:
            shutil.rmtree(tmpdir)
        except Exception:
            pass
        logger.exception('Unexpected error in yt-dlp flow: %s', e)
        return None, 'unexpected'

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    await update.message.reply_text("🎶 Hi! I'm a music bot. Send me a song name and I'll find it for you.")


async def yt_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Download audio from YouTube directly (usage: /yt <query>)"""
    args = context.args or []
    if not args:
        await update.message.reply_text("Usage: /yt <song name or artist - title>\nExample: /yt Shape of You - Ed Sheeran")
        return

    query = " ".join(args)
    await update.message.reply_text(f"🔍 Searching YouTube for '{query}' and downloading audio...")
    path, err = download_from_youtube(query)
    if not path:
        await update.message.reply_text("❌ Could not download from YouTube: %s" % err)
        return

    try:
        await update.message.reply_audio(audio=open(path, 'rb'))
    finally:
        try:
            shutil.rmtree(os.path.dirname(path))
        except Exception:
            logger.exception("Failed to cleanup yt-dlp temp files %s", path)


async def set_bot_metadata(application: Application) -> None:
    """Set bot commands and descriptions programmatically so users see custom text instead of default prompts."""
    try:
        commands = [
            BotCommand("start", "Start and get help"),
            BotCommand("help", "Show help and usage"),
            BotCommand("yt", "Download audio from YouTube (opt-in)")
        ]
        await application.bot.set_my_commands(commands)
        # Short description shown in the bot profile (on newer clients)
        try:
            await application.bot.set_my_short_description("Search & deliver music (Jamendo/Deezer/YouTube)")
        except Exception:
            # Older API / Bot may not support this method depending on library version
            logger.debug("set_my_short_description not available on this installation")

        try:
            await application.bot.set_my_description(
                "Send a song name to fetch audio from Jamendo, Deemix/Deezer, or YouTube (fallback)."
            )
        except Exception:
            logger.debug("set_my_description not available on this installation")
    except Exception as e:
        logger.exception("Failed to set bot metadata: %s", e)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text("❓ Need help? Send me a song name and I will search for it on Jamendo/Deezer (or use YouTube fallback). 🎧")

async def search_music(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Search for music on Deezer and download it."""
    search_query = update.message.text
    if not search_query:
        await update.message.reply_text("Please send me a song name to search.")
        return

    await update.message.reply_text("🔍 Searching for your song, please wait...")

    try:
        jam_path, jam_err = jamendo_search_and_download(search_query)
        if jam_path:
            try:
                await update.message.reply_audio(audio=open(jam_path, "rb"))
            finally:
                try:
                    shutil.rmtree(os.path.dirname(jam_path))
                except Exception:
                    logger.exception("Failed to cleanup Jamendo temp files %s", jam_path)
            return

        response = requests.get(DEEZER_API_URL, params={"q": search_query})
        response.raise_for_status()
        data = response.json()

        if data["data"]:
            track = data["data"][0]
            link = track["link"]

            config_folder = os.path.expanduser("~/.config/deemix")
            if not os.path.exists(config_folder):
                os.makedirs(config_folder)
            
            settings = load_settings(config_folder)
            settings["downloadLocation"] = "."

            deezer = Deezer()


            try:
                bitrate = int(settings.get('maxBitrate', 3))
            except Exception:
                bitrate = 3

            download_object = generateDownloadObject(deezer, link, bitrate)
            from deemix.downloader import Downloader
            downloader = Downloader(deezer, download_object, settings)
            try:
                downloader.start()
            except Exception as e:
                logger.exception("Deemix downloader raised an exception: %s", e)
                await update.message.reply_text("❌ Sorry, I couldn't download the song (internal error).")
                return

            files_info = getattr(download_object, 'files', []) or []
            if files_info:
                audio_file = None
                for info in files_info:
                    p = info.get('path') or info.get('filename') or ""
                    if p and any(p.lower().endswith(ext) for ext in ('.mp3', '.flac', '.m4a', '.opus')):
                        audio_file = p
                        break

                if not audio_file:
                    audio_file = files_info[0].get('path') or files_info[0].get('filename')

                if audio_file and os.path.isabs(audio_file) and os.path.exists(audio_file):
                    await update.message.reply_audio(audio=open(audio_file, "rb"))
                    try:
                        os.remove(audio_file)
                    except Exception:
                        logger.exception("Failed to remove downloaded file %s", audio_file)
                    return
                elif audio_file and os.path.exists(audio_file):
                    await update.message.reply_audio(audio=open(audio_file, "rb"))
                    try:
                        os.remove(audio_file)
                    except Exception:
                        logger.exception("Failed to remove downloaded file %s", audio_file)
                    return

            errors = getattr(download_object, 'errors', []) or []
            if errors:
                logger.error("Deemix reported errors: %s", errors)
                try_yt = False
                for err in errors:
                    errid = err.get('errid', '') if isinstance(err, dict) else ''
                    if errid in ('wrongLicense', 'wrongGeolocation', 'notAvailable', 'wrongBitrate', 'notEncoded'):
                        try_yt = True
                        break

                if try_yt:
                    await update.message.reply_text("Deemix couldn't download (reason: %s). Trying YouTube fallback... pls wait 😌" % errors[0].get('message', 'unknown'))
                    yt_path, yt_err = download_from_youtube(search_query)
                    if yt_path:
                        try:
                            await update.message.reply_audio(audio=open(yt_path, "rb"))
                        finally:
                            try:
                                shutil.rmtree(os.path.dirname(yt_path))
                            except Exception:
                                logger.exception("Failed to cleanup yt-dlp temp files %s", yt_path)
                        return

                await update.message.reply_text("Sorry, I couldn't download the song. Error: %s" % errors[0].get('message', 'unknown'))
                return

            files = os.listdir(".")
            for file in files:
                if file.endswith((".mp3", ".flac", ".m4a", ".opus")):
                    audio_file = file
                    break
            else:
                yt_path, yt_err = download_from_youtube(search_query)
                if yt_path:
                    try:
                        await update.message.reply_audio(audio=open(yt_path, "rb"))
                    finally:
                        try:
                            shutil.rmtree(os.path.dirname(yt_path))
                        except Exception:
                            logger.exception("Failed to cleanup yt-dlp temp files %s", yt_path)
                    return

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

    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if not getattr(application, "_initialized", False):
        loop.run_until_complete(application.initialize())

    # Set bot commands, descriptions and menu to commands so users see helpful text
    try:
        loop.run_until_complete(set_bot_metadata(application))
    except Exception:
        logger.exception("Failed to set bot metadata during startup")

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("yt", yt_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_music))

    application.run_polling()

if __name__ == "__main__":
    main()
