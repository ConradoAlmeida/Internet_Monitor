import sqlite3

conn = sqlite3.connect('/home/rubens/Internet_Monitor/internet.db')
cursor = conn.cursor()

cursor.execute('SELECT COUNT(*) FROM metrics')
print('Total de registros:', cursor.fetchone()[0])

cursor.execute('SELECT * FROM metrics ORDER BY timestamp DESC LIMIT 5')
print('\nÚltimos 5 registros:')
for row in cursor.fetchall():
    print(row)

cursor.execute("PRAGMA table_info(metrics)")
print('\nColunas da tabela:')
for col in cursor.fetchall():
    print(col)

conn.close()
