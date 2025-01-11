import sqlite3

connection = sqlite3.connect('data.db')

cursor = connection.cursor()

cursor.execute('PRAGMA foreign_keys = ON;')

cursor.execute('CREATE TABLE IF NOT EXISTS Bot (BotID TEXT PRIMARY KEY, FaceDetection INTEGER, SensorInfo INTEGER, BotIP TEXT)')
cursor.execute('''CREATE TABLE IF NOT EXISTS Chat (ChatID TEXT PRIMARY KEY, FaceDetection INTEGER, 
               SensorInfo INTEGER, BotID TEXT, FOREIGN KEY (BotID) REFERENCES Bot(BotID))''')

connection.commit()

cursor.execute('SELECT * FROM Bot')
rows = cursor.fetchall()
for row in rows:
    print(row)

cursor.execute('SELECT * FROM Chat')
rows = cursor.fetchall()
for row in rows:
    print(row)
connection.close()

