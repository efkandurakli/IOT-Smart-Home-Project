import sqlite3

connection = sqlite3.connect('data.db')

cursor = connection.cursor()

cursor.execute("SELECT * FROM Chat;")
rows = cursor.fetchall()
for row in rows:
    print(row)

cursor.execute("SELECT * FROM Bot;")
rows = cursor.fetchall()
for row in rows:
    print(row)