import json
import os
import threading
import time
import face_recognition
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler
import config
import hardware
import face_recognition_utils
import logging
from telegram.error import TelegramError, NetworkError, TimedOut

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

bot = None
updater = None
database = None
face_path_cache = {}  # Temporary storage for face paths
face_cache_lock = threading.Lock()  # Lock for thread-safe access to face_path_cache

FACE_CACHE_CLEANUP_TIME = 3600  # 1-hour cleanup timer for cached face paths
RETRY_ATTEMPTS = 3  # Retry attempts for Telegram alerts
RETRY_DELAY = 2  # Seconds to wait between retries

def initialize_bot(face_db):
    """Initialize the Telegram bot."""
    global bot, updater, database
    database = face_db

    try:
        bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
        updater = Updater(token=config.TELEGRAM_BOT_TOKEN, use_context=True)
        dispatcher = updater.dispatcher

        dispatcher.add_handler(CommandHandler('start', start_command))
        dispatcher.add_handler(CallbackQueryHandler(button_callback))

        # Test connection before starting thread
        bot.get_me()
        
        # Start polling in a daemon thread without idle()
        threading.Thread(target=run_bot, daemon=True).start()
        logging.info("Telegram bot initialized")
        return True
    except Exception as e:
        logging.error(f"Failed to initialize Telegram bot: {e}")
        return False

def run_bot():
    """Run the Telegram bot with increased timeout and error handling."""
    global updater
    try:
        # Start polling but don't use idle() in a non-main thread
        updater.start_polling(timeout=120, drop_pending_updates=True)
        logging.info("Telegram bot started polling")
        
        # Instead of idle(), use a simple loop to keep the thread alive
        while True:
            time.sleep(1)
            
    except NetworkError as e:
        logging.error(f"Network error in bot polling: {e}")
        time.sleep(10)  # Wait before potential reconnect
        run_bot()  # Recursive retry with backoff handled by Updater
    except Exception as e:
        logging.error(f"Critical error in bot polling: {e}")
        time.sleep(60)  # Wait before retry
        run_bot()  # Try to restart the polling

def shutdown_bot():
    """Shutdown the Telegram bot gracefully."""
    try:
        if updater:
            updater.stop()
            logging.info("Telegram bot stopped")
    except Exception as e:
        logging.error(f"Error stopping bot: {e}")

def start_command(update, context):
    """Handle the /start command."""
    try:
        update.message.reply_text("Welcome to Door Security Bot! I will notify you when someone is at the door.")
    except Exception as e:
        logging.error(f"Error in start_command: {e}")

def button_callback(update, context):
    """Handle button interactions safely."""
    try:
        query = update.callback_query
        query.answer()  # Acknowledge the button press to client

        if not query.message:
            logging.error("ERROR in button_callback: No message object in callback query")
            return

        data = json.loads(query.data)
        action = data.get("action")
        face_id = data.get("id")
        
        with face_cache_lock:
            face_path = face_path_cache.get(face_id)

        if not face_path:
            safe_edit_caption(query, "Error: Face data expired or not found.")
            return

        if action == "allow_always":
            process_allow_always(query, face_path)
        elif action == "allow_once":
            process_allow_once(query)
        elif action == "deny":
            safe_edit_caption(query, "Access denied.")

        with face_cache_lock:
            face_path_cache.pop(face_id, None)

    except json.JSONDecodeError:
        safe_edit_caption(query, "Error: Invalid button data format.")
    except Exception as e:
        logging.error(f"ERROR in button_callback: {e}")
        safe_edit_caption(query, "An error occurred. Please try again.")

def safe_edit_caption(query, text):
    """Safely edit a message caption, handling potential errors."""
    if not query or not query.message:
        logging.error("Cannot edit message: Invalid query or missing message")
        return
        
    try:
        # Edit the caption instead of trying to edit message text for photo messages
        query.edit_message_caption(
            caption=text
        )
    except TelegramError as e:
        logging.warning(f"Failed to edit message caption: {e}")
        try:
            # As fallback, send a new message
            bot.send_message(
                chat_id=query.message.chat_id,
                text=f"Update: {text}"
            )
        except Exception as e2:
            logging.error(f"Failed to send fallback message: {e2}")

def process_allow_always(query, face_path):
    """Process allowing a face permanently."""
    try:
        if not os.path.exists(face_path):
            safe_edit_caption(query, "ERROR: Face image does not exist.")
            return

        image = face_recognition.load_image_file(face_path)
        face_locations = face_recognition.face_locations(image)

        if not face_locations:
            safe_edit_caption(query, "Could not detect face in image.")
            return
            
        face_encoding = face_recognition.face_encodings(image, [face_locations[0]])[0]
        name = f"Person_{int(time.time())}"
        
        # Save face to database and image file
        success = face_recognition_utils.add_face_to_database(database, face_encoding, name)
        if not success:
            safe_edit_caption(query, "Failed to add person to database.")
            return
            
        face_recognition_utils.save_known_person_image(image, name)
        
        # Unlock door after successful database operations
        door_unlocked = hardware.unlock_door(config.UNLOCK_DURATION)
        
        message = f"Person added to database as {name}."
        if door_unlocked:
            message += " Door unlocked."
        else:
            message += " Door unlock failed."
            
        safe_edit_caption(query, message)

    except Exception as e:
        logging.error(f"Error in process_allow_always: {e}")
        safe_edit_caption(query, "Failed to add person to database.")

def process_allow_once(query):
    """Process allowing temporary access."""
    try:
        success = hardware.unlock_door(config.UNLOCK_DURATION)
        message = "Door unlocked for one-time access." if success else "Failed to unlock door."
        safe_edit_caption(query, message)
    except Exception as e:
        logging.error(f"Error in process_allow_once: {e}")
        safe_edit_caption(query, "Failed to process one-time access.")

def send_unknown_face_alert(face_path):
    """Send an alert about an unknown face."""
    if not bot:
        logging.error("Telegram bot not initialized")
        return False
        
    if not os.path.exists(face_path):
        logging.error(f"ERROR: Face image {face_path} does not exist.")
        return False

    face_id = str(int(time.time()))
    with face_cache_lock:
        face_path_cache[face_id] = face_path

    keyboard = [
        [
            InlineKeyboardButton("Allow Always", callback_data=json.dumps({"action": "allow_always", "id": face_id})),
            InlineKeyboardButton("Allow Once", callback_data=json.dumps({"action": "allow_once", "id": face_id}))
        ],
        [
            InlineKeyboardButton("Deny", callback_data=json.dumps({"action": "deny", "id": face_id}))
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    success = False
    for attempt in range(RETRY_ATTEMPTS):
        try:
            # Check if file is valid before trying to send
            if not os.path.getsize(face_path) > 0:
                logging.error(f"Face image file is empty: {face_path}")
                return False
                
            with open(face_path, 'rb') as photo:
                bot.send_photo(
                    chat_id=config.ADMIN_CHAT_ID,
                    photo=photo,
                    caption="Unknown person at the door. What would you like to do?",
                    reply_markup=reply_markup
                )
            logging.info("Sent unknown face alert to Telegram")
            success = True
            break  # Exit loop on success
        except TimedOut:
            logging.warning(f"Telegram request timed out (Attempt {attempt+1}/{RETRY_ATTEMPTS})")
            time.sleep(RETRY_DELAY * (attempt + 1))  # Exponential backoff
        except Exception as e:
            logging.error(f"ERROR sending alert (Attempt {attempt+1}/{RETRY_ATTEMPTS}): {e}")
            time.sleep(RETRY_DELAY)

    # Start cleanup thread only if we successfully sent the alert
    if success:
        threading.Thread(target=delayed_face_cache_cleanup, args=(face_id,), daemon=True).start()
    else:
        # Clean up immediately if all attempts failed
        with face_cache_lock:
            face_path_cache.pop(face_id, None)
            
        # Try sending a text-only notification as fallback
        try:
            bot.send_message(
                chat_id=config.ADMIN_CHAT_ID,
                text="⚠️ Unknown person detected at the door but couldn't send photo. Please check security cameras."
            )
        except Exception as e:
            logging.error(f"Failed to send fallback text notification: {e}")
            
    return success

def delayed_face_cache_cleanup(face_id):
    """Cleanup cached face paths after a delay."""
    time.sleep(FACE_CACHE_CLEANUP_TIME)
    with face_cache_lock:
        if face_id in face_path_cache:
            path = face_path_cache.pop(face_id)
            logging.info(f"Face cache cleanup completed for {face_id}")
            
            # Optionally, clean up temporary image files
            try:
                if os.path.exists(path) and "temp" in path.lower():
                    os.remove(path)
                    logging.info(f"Removed temporary face image: {path}")
            except Exception as e:
                logging.warning(f"Failed to remove temporary face image: {e}")
