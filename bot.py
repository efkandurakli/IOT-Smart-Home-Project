import cv2
import numpy as np
import asyncio
import logging
import requests
from telegram import ForceReply, Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from dotenv import load_dotenv
import os
from face_rec import *
from io import BytesIO

load_dotenv()
server_url = "http://10.51.9.13:5000"
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
    """Send unexpected event notifications to the specific user."""
    job = context.job  # The job contains metadata about the scheduled task
    chat_id = job.chat_id  # Retrieve the user's chat ID from the job metadata

    try:
        response = requests.get(f"{server_url}/current_frame", timeout=5)
        response.raise_for_status()

        print("Response content-type:", response.headers.get("Content-Type"))

        image_bytes = np.frombuffer(response.content, dtype=np.uint8)
        print("Image bytes:", image_bytes)
        opencv_image = cv2.imdecode(image_bytes, cv2.IMREAD_COLOR)
        print("OpenCV image:", opencv_image)


        face_image, num_knowns, num_unknowns = find_number_of_known_and_unknown_faces(opencv_image, known_face_encodings)
        print("Num of knowns: ", num_knowns)
        print("Num of unknowns: ", num_unknowns)

        if num_unknowns > 0:
            _, buffer = cv2.imencode('.jpg', face_image)
            image_bytes = BytesIO(buffer.tobytes())
            image_bytes.name = "image.jpg"  # Optional: Telegram likes named files

            await context.bot.send_photo(
                chat_id=chat_id,
                photo=image_bytes,
                caption=f"{num_unknowns} unknowns detected in your house!"
            )
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching current frame: {e}")

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching current frame: {e}")


def remove_job_if_exists(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Remove job with given name. Returns whether job was removed."""
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
        print(f"Removed job {job.name}")
    return True
        
    
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /start command and adds user to the active list."""
    user_id = update.effective_user.id
    active_users.add(user_id)
    #job_removed = remove_job_if_exists(str(user_id), context)

    await update.message.reply_text("""You will receive a notification whenever something unexpected happens in the house!
To start unknown people detector: /startDetectingFaces
To stop unknown people detector: /stopDetectingFaces
To start getting sensor info: /startGettingSensorInfo
To stop getting sensor info: /stopGettingSensorInfo""")

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

async def startDetectingFaces(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    #job_removed = remove_job_if_exists(str(chat_id), context)
    context.job_queue.run_repeating(send_unexpected_event_notification, interval=2, chat_id=update.message.chat_id, name=f"face_info_{chat_id}")
    print("Job", context.job_queue.get_jobs_by_name(f"face_info_{chat_id}"))
    message = "Started detecting faces!" 
    #if not job_removed else "Restarted detecting faces!"
    await update.message.reply_text(message)

async def stopDetectingFaces(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print("Stopping to detect faces")
    remove_job_if_exists(f"face_info_{update.message.chat_id}", context)
    await update.message.reply_text("Stopped detecting faces")

async def startGettingSensorInfo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    context.job_queue.run_repeating(get_sensor_info, interval=2, chat_id=update.message.chat_id, name=f"sensor_info_{chat_id}")
    print("Job", context.job_queue.get_jobs_by_name(f"sensor_info_{chat_id}"))
    message = "Started getting sensor info!" 
    await update.message.reply_text(message)

async def stopGettingSensorInfo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print("Stopping to get sensor info")
    remove_job_if_exists(f"sensor_info_{update.message.chat_id}", context)
    await update.message.reply_text("Stopped getting sensor info")

async def get_sensor_info(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send unexpected event notifications to the specific user."""
    job = context.job  # The job contains metadata about the scheduled task
    chat_id = job.chat_id  # Retrieve the user's chat ID from the job metadata
    try:
        response = requests.get(f" {server_url}/get_sensor_info", stream=True)
        response.raise_for_status()
        response = response.json()
        warning_message = ""
        if response["CO"] == int(1):
            warning_message += "CO level is high. "
        if response["Flamable"] == int(1):
            warning_message += "Flamable gas detected. "
        if response["Flame"] == int(1):
            warning_message += "Fire detected."
        if warning_message != "":
            await context.bot.send_message(chat_id=chat_id, text=warning_message)
    except:
        print("Failed to get sensor info")


def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(bot_token).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("get_current_frame", get_current_frame_command))
    application.add_handler(CommandHandler("startDetectingFaces", startDetectingFaces))
    application.add_handler(CommandHandler("stopDetectingFaces", stopDetectingFaces))
    application.add_handler(CommandHandler("startGettingSensorInfo", startGettingSensorInfo))
    application.add_handler(CommandHandler("stopGettingSensorInfo", stopGettingSensorInfo))


    # on non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()