import sqlite3

def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0,
            language TEXT DEFAULT 'uz'
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            file_id TEXT,
            status TEXT DEFAULT 'pending',
            category TEXT,
            dars_turi TEXT,
            topic TEXT,
            language TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Eski bazalarda ba'zi ustunlar bo'lmasligi mumkin — mavjud bo'lmasa qo'shamiz
    for ddl in [
        'ALTER TABLE users ADD COLUMN language TEXT DEFAULT "uz"',
        'ALTER TABLE payments ADD COLUMN category TEXT',
        'ALTER TABLE payments ADD COLUMN dars_turi TEXT',
        'ALTER TABLE payments ADD COLUMN topic TEXT',
        'ALTER TABLE payments ADD COLUMN language TEXT',
    ]:
        try:
            cursor.execute(ddl)
            conn.commit()
        except sqlite3.OperationalError:
            pass  # Ustun allaqachon mavjud
    conn.commit()
    conn.close()

def get_balance(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return result[0]
    else:
        # Agar foydalanuvchi bazada bo'lmasa, uni qo'shish
        add_user(user_id)
        return 0

def add_user(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, ?)', (user_id, 0))
    conn.commit()
    conn.close()

def update_balance(user_id, amount):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
    conn.commit()
    conn.close()

# ---------- TIL (LANGUAGE) FUNKSIYALARI ----------

def get_language(user_id):
    """Foydalanuvchining tanlagan tilini qaytaradi (standart: 'uz')."""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT language FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    if result and result[0]:
        return result[0]
    else:
        add_user(user_id)
        return 'uz'

def set_language(user_id, lang_code):
    """Foydalanuvchining tilini saqlaydi."""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    add_user(user_id)
    cursor.execute('UPDATE users SET language = ? WHERE user_id = ?', (lang_code, user_id))
    conn.commit()
    conn.close()

# ---------- TO'LOV / BUYURTMA (PAYMENT) FUNKSIYALARI ----------

def create_payment(user_id, amount, file_id, category=None, dars_turi=None, topic=None, language=None):
    """Yangi to'lov/buyurtma so'rovi yaratadi va uning ID sini qaytaradi."""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute(
        '''INSERT INTO payments
           (user_id, amount, file_id, status, category, dars_turi, topic, language)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        (user_id, amount, file_id, 'pending', category, dars_turi, topic, language)
    )
    conn.commit()
    payment_id = cursor.lastrowid
    conn.close()
    return payment_id

def get_payment(payment_id):
    """Bitta to'lov/buyurtma so'rovini qaytaradi:
    (id, user_id, amount, file_id, status, category, dars_turi, topic, language)."""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute(
        '''SELECT id, user_id, amount, file_id, status, category, dars_turi, topic, language
           FROM payments WHERE id = ?''',
        (payment_id,)
    )
    result = cursor.fetchone()
    conn.close()
    return result

def set_payment_status(payment_id, status):
    """To'lov holatini yangilaydi: 'approved' yoki 'rejected'."""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE payments SET status = ? WHERE id = ?', (status, payment_id))
    conn.commit()
    conn.close()
