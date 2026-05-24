import mysql.connector

# 1. Create database
conn = mysql.connector.connect(host='localhost', user='root', password='123456')
cur = conn.cursor()
cur.execute('CREATE DATABASE IF NOT EXISTS ai_accounts CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci')
print('Database ai_accounts created')
conn.close()

# 2. Create users table
conn = mysql.connector.connect(host='localhost', user='root', password='123456', database='ai_accounts')
cur = conn.cursor()
cur.execute('''CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    email VARCHAR(100) DEFAULT NULL,
    role ENUM('teacher','student','admin','guest') DEFAULT 'student',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')
conn.commit()
print('Table users created')

# 3. Migrate users from old DB
try:
    conn_old = mysql.connector.connect(host='localhost', user='root', password='123456', database='ai_teaching_assistant')
    cur_old = conn_old.cursor(dictionary=True)
    cur_old.execute('SELECT * FROM users')
    users = cur_old.fetchall()
    for u in users:
        cur.execute(
            'INSERT IGNORE INTO users (id, username, password, email, role, created_at, updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s)',
            (u['id'], u['username'], u['password'], u.get('email'), u.get('role', 'student'), u['created_at'], u['updated_at'])
        )
    conn.commit()
    print(f'Migrated {len(users)} users')
    conn_old.close()
except Exception as e:
    print(f'Migration note: {e}')

# 4. Verify
cur.execute('SELECT id, username, role FROM users')
rows = cur.fetchall()
print(f'Users in ai_accounts: {rows}')
conn.close()
