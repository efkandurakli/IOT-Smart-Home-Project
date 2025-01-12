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
import sqlite3

load_dotenv()

bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
#bot_token = "7910037233:AAF84g6Ba0eUkfckY_S5FXKqQWhmQwkN7Vo"

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
    data_dict = job.data  # Retrieve the data list
    print("Data list", data_dict)
    print("Type data list", type(data_dict))
    bot_ip = data_dict["ip"]
    print("Bot ip", bot_ip)
    image_dict = {}
    known_person = False
    for i in range(5):
        try:
            response = requests.get(f"http://{bot_ip}/current_frame", timeout=5)
            response.raise_for_status()

            print("Response content-type:", response.headers.get("Content-Type"))

            image_bytes = np.frombuffer(response.content, dtype=np.uint8)
            opencv_image = cv2.imdecode(image_bytes, cv2.IMREAD_COLOR)


            face_image, num_knowns, num_unknowns = find_number_of_known_and_unknown_faces(opencv_image, known_face_encodings)
            print("Num of knowns: ", num_knowns)
            print("Num of unknowns: ", num_unknowns)
            if num_knowns > 0:
                known_person = True

            if num_unknowns > 0 and num_knowns == 0:
                data_dict["unknown_detections"] += 1
                _, buffer = cv2.imencode('.jpg', face_image)
                image_bytes = BytesIO(buffer.tobytes())
                image_bytes.name = "image.jpg"  # Optional: Telegram likes named files
                image_dict[i] = image_bytes
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching current frame: {e}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching current frame: {e}")
        await asyncio.sleep(1)
    if data_dict["unknown_detections"] >= 4 and not known_person:
        #for key, value in image_dict.items():
        await context.bot.send_photo(chat_id=chat_id, photo=image_bytes, caption="Unknown people detected in your house!")


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
    #user_id = update.effective_user.id
    chat_id = update.message.chat_id
    connection = sqlite3.connect('data.db')
    cursor = connection.cursor()
    cursor.execute('SELECT ChatID FROM Chat WHERE ChatID = ?', (str(chat_id),))
    rows = cursor.fetchone()
    if rows:
        cursor.execute('SELECT BotID FROM Chat WHERE ChatID = ?', (str(chat_id),))
        bot_id = cursor.fetchone()[0]
        connection.close()
        print("Bot id: ", bot_id)
        print(bot_id == None)
        if bot_id:
            await update.message.reply_text("You already started to communicate to your bot.")
        else:
            await update.message.reply_text("You need to match your bot. To do this, \ntype /connect_to_bot your_bot_id")

    else:
        cursor.execute('INSERT INTO Chat (ChatID, FaceDetection, SensorInfo) VALUES (?, ?, ?)', (str(chat_id), 0, 0))
        connection.commit()
        connection.close()
        await update.message.reply_text("Please give a bot id to match your bot. To do this, \ntype /connect_to_bot [your_bot_id]")
            
        
async def connect_to_bot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    arg = context.args
    if len(arg) != 1:
        await update.message.reply_text("Please give a correct number of arg.(1)")
    else:
        chat_id = update.message.chat_id
        connection = sqlite3.connect('data.db')
        cursor = connection.cursor()
        cursor.execute('SELECT ChatID FROM Chat WHERE ChatID = ?', (str(chat_id),))
        rows = cursor.fetchone()
        print("Rows: ", rows)
        print("Rows type: ", type(rows))

        if rows:
            rows = rows[0]
            new_bot_id = str(arg[0])
            is_valid = False
            cursor.execute('SELECT BotID FROM Bot WHERE BotID = ?', (new_bot_id,))
            defined_bot = cursor.fetchone()[0]
            print("Defined bot: ", defined_bot)
            print("Defined bot type", type(defined_bot))

            if defined_bot:
                is_valid = True
                cursor.execute('UPDATE Chat SET BotID = ? WHERE ChatID = ?', (new_bot_id, str(chat_id)))
                connection.commit()
                connection.close()
                await update.message.reply_text("Added to the bots chat list.\
                                                \nThere are multiple use cases for this app! You can use the following commands!\
                                                \nTo get help: /help\
                                                \nTo start unknown people detector: /start_detecting_faces\
                                                \nTo stop unknown people detector: /stop_detecting_faces\
                                                \nTo start getting sensor info: /start_getting_sensor_info\
                                                \nTo stop getting sensor info: /stop_getting_sensor_info\
                                                \nTo start getting face detection notifications: /start_face_detection_notifs\
                                                \nTo stop getting face detection notifications: /stop_face_detection_notifs\
                                                \nTo start getting sensor info notifications: /start_sensor_info_notifs\
                                                \nTo stop getting sensor info notifications: /stop_sensor_info_notifs\
                                                \nTo get the current frame of the camera: /get_current_frame\
                                                ")
            if not is_valid:
                await update.message.reply_text("Bot id is not valid.")
        else:
            await update.message.reply_text("You cannot communicate with this bot. Please write /start first.")



async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text("You can use the following commands:\
                                    \n/start: To start the bot\
                                    \n/help: To get help\
                                    \n/connect_to_bot [your_bot_id]: To match your bot\
                                    \n/start_detecting_faces: To start detecting faces\
                                    \n/stop_detecting_faces: To stop detecting faces\
                                    \n/start_getting_sensor_info: To start getting sensor info\
                                    \n/stop_getting_sensor_info: To stop getting sensor info\
                                    \n/start_face_detection_notifs: To start getting face detection notifications\
                                    \n/stop_face_detection_notifs: To stop getting face detection notifications\
                                    \n/start_sensor_info_notifs: To start getting sensor info notifications\
                                    \n/stop_sensor_info_notifs: To stop getting sensor info notifications\
                                    \n/get_current_frame: To get the current frame of the camera\
                                    ")

async def get_current_frame_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    connection = sqlite3.connect('data.db')
    cursor = connection.cursor()
    cursor.execute('SELECT BotID FROM Chat WHERE ChatID = ?', (str(chat_id),))
    bot_id = cursor.fetchone()
    if bot_id:
        try:
            cursor.execute('SELECT BotIP FROM Bot WHERE BotID = ?', (bot_id[0],))
            bot_ip = cursor.fetchone()[0]
            response = requests.get(f"http://{bot_ip}/current_frame", stream=True)
            response.raise_for_status()
            await update.message.reply_photo(photo=response.raw)
        
        except requests.exceptions.RequestException as e:
            await update.message.reply_text(f"Failed to fetch the current frame.")
            print(e)
        except Exception as e:
            await update.message.reply_text(f"An error occurred. Please try again.")
            print(e)
    else:
        await update.message.reply_text("You need to match your bot. To do this, \ntype /connect_to_bot your_bot_id")


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the user message."""
    await update.message.reply_text(update.message.text)

async def start_detecting_faces(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    connection = sqlite3.connect('data.db')
    cursor = connection.cursor()
    cursor.execute('SELECT BotID, FaceDetection FROM Chat WHERE ChatID = ?', (str(chat_id),))
    row = cursor.fetchone()
    if row:
        bot_id = row[0]
        face_detection_chat = row[1]
        cursor.execute('SELECT FaceDetection FROM Bot WHERE BotID = ?', (bot_id,))
        face_detection = cursor.fetchone()[0]
        if face_detection == 1:
            if face_detection_chat == 0:
                await update.message.reply_text("Detecting Faces is already opened. To get notifications, /start_face_detection_notifs")
            else:
                await update.message.reply_text("Detecting faces is already opened.")
        else:
            cursor.execute('UPDATE Bot SET FaceDetection = ? WHERE BotID = ?', (1, bot_id))
            cursor.execute('UPDATE Chat SET FaceDetection = ? WHERE ChatID = ?', (1, str(chat_id)))
            connection.commit()
            cursor.execute("SELECT BotIP FROM Bot WHERE BotID = ?", (bot_id,))
            bot_ip = cursor.fetchone()[0]
            context.job_queue.run_repeating(send_unexpected_event_notification, interval=10, chat_id=update.message.chat_id, data={"unknown_detections": 0, "ip": bot_ip}, name=f"face_info_{chat_id}")
            print("Job", context.job_queue.get_jobs_by_name(f"face_info_{chat_id}"))
            message = "Started detecting faces!"
            await update.message.reply_text(message)
    else:
        await update.message.reply_text("You need to match your bot. To do this, \ntype /connect_to_bot your_bot_id")
    connection.close()

async def start_face_detection_notifs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    print("Yes, we have come here!")
    connection = sqlite3.connect('data.db')
    cursor = connection.cursor()
    cursor.execute('SELECT ChatID, BotID, FaceDetection FROM Chat WHERE ChatID = ?', (str(chat_id),))
    rows = cursor.fetchone()
    print("Also here")
    print("Rows", rows)
    print("Row 2", rows[1])
    print("Row 3", rows[2])
    if rows:
        bot_id = rows[1]
        print("Bot ID:", bot_id)
        face_detection_chat = rows[2]
        print("Also came here")
        if bot_id:
            cursor.execute('SELECT FaceDetection FROM Bot WHERE BotID = ?', (bot_id,))
            face_detection = cursor.fetchone()[0]
            if face_detection == 1:
                if face_detection_chat == 0:
                    cursor.execute('SELECT BotIP FROM Bot WHERE BotID = ?', (bot_id,))
                    bot_ip = cursor.fetchone()[0]
                    context.job_queue.run_repeating(send_unexpected_event_notification, interval=10, chat_id=update.message.chat_id, data={"unknown_detections": 0, "ip": bot_ip}, name=f"face_info_{chat_id}")
                    cursor.execute('UPDATE Chat SET FaceDetection = ? WHERE ChatID = ?', (1, str(chat_id)))
                    connection.commit()
                    await update.message.reply_text("You will get face detection notifications.")
                else:
                    await update.message.reply_text("You already get face detection notifications. To stop, /stop_face_detection_notifs")
            else:
                await update.message.reply_text("You need to start face detection first by /start_detecting_faces")
        else:
            await update.message.reply_text("You need to match your bot. To do this, \ntype /connect_to_bot your_bot_id")
    else:
        await update.message.reply_text("You need to write /start first to get started with the bot.")
    connection.close()

async def stop_face_detection_notifs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    connection = sqlite3.connect('data.db')
    cursor = connection.cursor()
    cursor.execute('SELECT ChatID, BotID, FaceDetection FROM Chat WHERE ChatID = ?', (str(chat_id),))
    rows = cursor.fetchone()
    if rows:
        bot_id = rows[1]
        face_detection_chat = rows[2]
        if bot_id:
            cursor.execute('SELECT FaceDetection FROM Bot WHERE BotID = ?', (bot_id,))
            face_detection = cursor.fetchone()[0]
            if face_detection == 1:
                if face_detection_chat == 1:
                    remove_job_if_exists(f"face_info_{update.message.chat_id}", context)
                    cursor.execute('UPDATE Chat SET FaceDetection = ? WHERE ChatID = ?', (0, str(chat_id)))
                    connection.commit()
                    await update.message.reply_text("Stopped getting face detection notifications")
                else:
                    await update.message.reply_text("You already don't get notifications. To get notifications, /start_face_detection_notifs")
            else:
                await update.message.reply_text("You didn't start face detection, so you don't get any notifications. You need to start face detection first by /start_detecting_faces")
        else:
            await update.message.reply_text("You need to match your bot. To do this, \ntype /connect_to_bot your_bot_id")
    else:
        await update.message.reply_text("You need to write /start first to get started with the bot.")
    connection.close()
        

async def stop_detecting_faces(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    connection = sqlite3.connect('data.db')
    cursor = connection.cursor()
    cursor.execute('SELECT BotID FROM Chat WHERE ChatID = ?', (str(chat_id),))
    bot_id = cursor.fetchone()
    if bot_id:
        bot_id = bot_id[0]
        cursor.execute('SELECT FaceDetection FROM Bot WHERE BotID = ?', (bot_id,))
        face_detection = cursor.fetchone()[0]
        if face_detection == 1:
            print("Stopping to detect faces")
            cursor.execute("SELECT ChatID FROM Chat WHERE BotID = ?", (bot_id,))
            chats_of_this_bot = cursor.fetchall()
            for chat in chats_of_this_bot:
                print("Chat", chat[0])
                remove_job_if_exists(f"face_info_{chat[0]}", context)
            cursor.execute('UPDATE Bot SET FaceDetection = ? WHERE BotID = ?', (0, bot_id))
            cursor.execute('UPDATE Chat SET FaceDetection = ? WHERE BotID = ?', (0, bot_id))
            connection.commit()
            await update.message.reply_text("Stopped detecting faces")
        else:
            await update.message.reply_text("There is no started face detection.")
    else:
        await update.message.reply_text("You need to match your bot. To do this, \ntype /connect_to_bot your_bot_id")
    connection.close()

async def start_getting_sensor_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    connection = sqlite3.connect('data.db')
    cursor = connection.cursor()
    cursor.execute('SELECT BotID, SensorInfo FROM Chat WHERE ChatID = ?', (str(chat_id),))
    row = cursor.fetchone()
    if row:
        bot_id = row[0]
        sensor_info_chat = row[1]
        cursor.execute('SELECT SensorInfo FROM Bot WHERE BotID = ?', (bot_id,))
        sensor_info = cursor.fetchone()[0]
        if sensor_info == 1:
            if sensor_info_chat == 0:
                await update.message.reply_text("Getting Sensor Infos is already opened. To get notifications, /start_sensor_info_notifs")
            else:
                await update.message.reply_text("You already get sensor info notifications. To stop, /stop_sensor_info_notifs")
        else:
            cursor.execute('UPDATE Bot SET SensorInfo = ? WHERE BotID = ?', (1, bot_id))
            cursor.execute('UPDATE Chat SET SensorInfo = ? WHERE ChatID = ?', (1, str(chat_id)))
            connection.commit()
            cursor.execute("SELECT BotIP FROM Bot WHERE BotID = ?", (bot_id,))
            bot_ip = cursor.fetchone()[0]
            context.job_queue.run_repeating(get_sensor_info, interval=2, chat_id=update.message.chat_id, data=bot_ip, name=f"sensor_info_{chat_id}")
            print("Job", context.job_queue.get_jobs_by_name(f"sensor_info_{chat_id}"))
            message = "Started getting sensor info!"
            await update.message.reply_text(message)
    
    else:
        await update.message.reply_text("You need to match your bot. To do this, \ntype /connect_to_bot your_bot_id")
    connection.close()

async def start_sensor_info_notifs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    connection = sqlite3.connect('data.db')
    cursor = connection.cursor()
    cursor.execute('SELECT ChatID, BotID, SensorInfo FROM Chat WHERE ChatID = ?', (str(chat_id),))
    rows = cursor.fetchone()
    if rows:
        bot_id = rows[1]
        sensor_info_chat = rows[2]
        if bot_id:
            cursor.execute('SELECT SensorInfo FROM Bot WHERE BotID = ?', (bot_id,))
            sensor_info = cursor.fetchone()[0]
            if sensor_info == 1:
                if sensor_info_chat == 0:
                    cursor.execute("SELECT BotIP FROM Bot WHERE BotID = ?", (bot_id,))
                    bot_ip = cursor.fetchone()[0]
                    context.job_queue.run_repeating(get_sensor_info, interval=2, chat_id=update.message.chat_id, data=bot_ip, name=f"sensor_info_{chat_id}")
                    cursor.execute('UPDATE Chat SET SensorInfo = ? WHERE ChatID = ?', (1, str(chat_id)))
                    connection.commit()
                    await update.message.reply_text("You will get sensor info notifications.")
                else:
                    await update.message.reply_text("You already get sensor info notifications. To stop, /stop_sensor_info_notifs")
            else:
                await update.message.reply_text("You need to start getting sensor info first by /start_getting_sensor_info")
        else:
            await update.message.reply_text("You need to match your bot. To do this, \ntype /connect_to_bot your_bot_id")
    connection.close()

async def stop_sensor_info_notifs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    connection = sqlite3.connect('data.db')
    cursor = connection.cursor()
    cursor.execute('SELECT ChatID, BotID, SensorInfo FROM Chat WHERE ChatID = ?', (str(chat_id),))
    rows = cursor.fetchone()
    if rows:
        bot_id = rows[1]
        sensor_info_chat = rows[2]
        if bot_id:
            cursor.execute('SELECT SensorInfo FROM Bot WHERE BotID = ?', (bot_id,))
            sensor_info = cursor.fetchone()[0]
            if sensor_info == 1:
                if sensor_info_chat == 1:
                    remove_job_if_exists(f"sensor_info_{update.message.chat_id}", context)
                    cursor.execute('UPDATE Chat SET SensorInfo = ? WHERE ChatID = ?', (0, str(chat_id)))
                    connection.commit()
                    await update.message.reply_text("Stopped getting sensor info notifications.")
                else:
                    await update.message.reply_text("You already don't get notifications. To get notifications, /start_sensor_info_notifs")
            else:
                await update.message.reply_text("You didn't start getting sensor info, so you don't get any notifications. You need to start getting sensor info first by /start_getting_sensor_info")
        else:
            await update.message.reply_text("You need to match your bot. To do this, \ntype /connect_to_bot your_bot_id")
    connection.close()

async def stop_getting_sensor_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    connection = sqlite3.connect('data.db')
    cursor = connection.cursor()
    cursor.execute('SELECT BotID FROM Chat WHERE ChatID = ?', (str(chat_id),))
    bot_id = cursor.fetchone()
    if bot_id:
        bot_id = bot_id[0]
        cursor.execute('SELECT SensorInfo FROM Bot WHERE BotID = ?', (bot_id,))
        sensor_info = cursor.fetchone()[0]
        if sensor_info == 1:
            print("Stopping to get sensor info")
            cursor.execute("SELECT ChatID FROM Chat WHERE BotID = ?", (bot_id,))
            chats_of_this_bot = cursor.fetchall()
            for chat in chats_of_this_bot:
                print("Chat", chat[0])
                remove_job_if_exists(f"sensor_info_{chat[0]}", context)
            cursor.execute('UPDATE Bot SET SensorInfo = ? WHERE BotID = ?', (0, bot_id))
            cursor.execute('UPDATE Chat SET SensorInfo = ? WHERE BotID = ?', (0, bot_id))
            connection.commit()
            await update.message.reply_text("Stopped getting sensor info")
        else:
            await update.message.reply_text("There is no started sensor info.")
    else:
        await update.message.reply_text("You need to match your bot. To do this, \ntype /connect_to_bot your_bot_id")

async def get_sensor_info(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send unexpected event notifications to the specific user."""
    job = context.job  # The job contains metadata about the scheduled task
    chat_id = job.chat_id  # Retrieve the user's chat ID from the job metadata
    bot_ip = job.data  # Retrieve the data list
    try:
        response = requests.get(f"http://{bot_ip}/get_sensor_info", stream=True)
        response.raise_for_status()
        response = response.json()
        warning_message = ""
        if response["Flamable"] == int(1):
            warning_message += "Flammable gas detected. "
        if response["Flame"] == int(1):
            warning_message += "Fire detected."
        if warning_message != "":
            requests.get(f"http://{bot_ip}/set_alarm")
            await context.bot.send_message(chat_id=chat_id, text=warning_message)
    except:
        print("Failed to get sensor info")


def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(bot_token).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("connect_to_bot", connect_to_bot))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("get_current_frame", get_current_frame_command))
    application.add_handler(CommandHandler("start_detecting_faces", start_detecting_faces))
    application.add_handler(CommandHandler("stop_detecting_faces", stop_detecting_faces))
    application.add_handler(CommandHandler("start_getting_sensor_info", start_getting_sensor_info))
    application.add_handler(CommandHandler("stop_getting_sensor_info", stop_getting_sensor_info))
    application.add_handler(CommandHandler("start_face_detection_notifs", start_face_detection_notifs))
    application.add_handler(CommandHandler("stop_face_detection_notifs", stop_face_detection_notifs))
    application.add_handler(CommandHandler("start_sensor_info_notifs", start_sensor_info_notifs))
    application.add_handler(CommandHandler("stop_sensor_info_notifs", stop_sensor_info_notifs))


    # on non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()