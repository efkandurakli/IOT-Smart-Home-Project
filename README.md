# IOT-Smart-Home-Project

This system consists of two main components:

1. **Local Server** (`local_server.py`)
   - Runs on a device (e.g., Raspberry Pi) that has a camera attached.
   - Also uses sensors (CO, flame, flammable, etc.) if available.
   - Provides camera frames and sensor data through simple HTTP endpoints.

2. **Telegram Bot** (`bot.py`)
   - Requires a **Telegram bot token** from [BotFather](https://t.me/botfather).
   - Interacts with users via commands (e.g., `/start`, `/connect_to_bot`), schedules tasks (face detection, sensor monitoring), and sends notifications.

---

## Setup & Usage

1. **Local Server**
   - On the device with a camera and sensors, run:
     ```bash
     python local_server.py
     ```
   - By default, it starts on port `5000`, providing endpoints like `/current_frame`, `/get_sensor_info`, and `/set_alarm`.

2. **Database Configuration**
   - Insert at least one record in the **SQLite** database specifying:
     - **BotID**: A unique identifier (e.g. `my_pi`).
     - **BotIP**: The local server’s IP address (e.g. `192.168.1.10:5000`).
   - Use the sample script `insert_bot_id.py` to create/update this record (adjust ID and IP accordingly).

3. **Telegram Bot**
   - Set the **Telegram bot token** in your environment or directly in `bot.py`.
   - Run:
     ```bash
     python bot.py
     ```

4. **Connecting via Telegram**
   - In the Telegram app, open your bot chat and send:
     1. `/start` to initialize the bot.
     2. `/connect_to_bot [YOUR_BOT_ID]` to link your device (using the same BotID you inserted).
   - After connecting, you can use commands like `/start_detecting_faces`, `/start_getting_sensor_info`, etc.

---