import sqlite3

connection = sqlite3.connect('data.db')

cursor = connection.cursor()

cursor.execute(
    'INSERT INTO Bot (BotID, FaceDetection, SensorInfo, BotIP) VALUES (?, ?, ?, ?)',
    ("pi_bot", 0, 0, "10.51.9.13:5000")
)

connection.commit()
connection.close()