import cv2
import numpy as np
import asyncio
import logging
import requests
from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from dotenv import load_dotenv
import os
from face_rec import *
from io import BytesIO

load_dotenv()
server_url = "http://127.0.0.1:5000"
bot_token = "7910037233:AAF84g6Ba0eUkfckY_S5FXKqQWhmQwkN7Vo"

active_users = set()

known_face_encodings = load_face_encodings("encodings.pkl")

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


async def send_unexpected_event_notification(context: ContextTypes.DEFAULT_TYPE) -> None:
    
    while True:
        try:
            response = requests.get(f"{server_url}/current_frame", timeout=2)
            response.raise_for_status()
            
            image_bytes = np.frombuffer(response.content, dtype=np.uint8)
            
            opencv_image = cv2.imdecode(image_bytes, cv2.IMREAD_COLOR)



            face_image, num_knowns, num_unknowns = find_number_of_known_and_unknown_faces(opencv_image, known_face_encodings)
            
            _, buffer = cv2.imencode('.jpg', face_image)
             
             
            image_bytes = BytesIO(buffer.tobytes())
            image_bytes.name = "image.jpg"  # Optional: Telegram likes named files
            # Send the image to all active users
            if num_unknowns > 0:
                for user_id in active_users:
                    try:
                        await context.bot.send_photo(chat_id=user_id, photo=image_bytes, caption=f"{num_unknowns} unknowns detected in your house!")
                        #logger.info(f"Sent current frame to user {user_id}")
                    except Exception as e:
                        logger.error(f"Failed to send current frame to user {user_id}: {e}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching current frame: {e}")
        
        finally:
            await asyncio.sleep(5)

  
def remove_job_if_exists(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Remove job with given name. Returns whether job was removed."""
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True
        
    
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /start command and adds user to the active list."""
    user_id = update.effective_user.id
    active_users.add(user_id)
    job_removed = remove_job_if_exists(str(user_id), context)
    await update.message.reply_text("You will receive a notification whenever something unexpected happens in the house!")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text("Help!")


async def get_current_frame_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
   

    try:
        response = requests.get(f" {server_url}/current_frame", stream=True)
        response.raise_for_status()
        await update.message.reply_photo(photo=response.raw)
    
    except requests.exceptions.RequestException as e:
        await update.message.reply_text(f"Failed to fetch the current frame: {e}")
    
    except Exception as e:
        await update.message.reply_text(f"An error occurred: {e}")
        


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the user message."""
    await update.message.reply_text(update.message.text)


def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(bot_token).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("get_current_frame", get_current_frame_command))

    # on non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Start the frame sending loop in the background
    application.job_queue.run_once(send_unexpected_event_notification, when=0)

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()