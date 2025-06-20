import sqlite3
import threading

class MessageDB:
    def __init__(self, db_file="data.db"):
        self.conn = sqlite3.connect(db_file, check_same_thread=False)
        self.lock = threading.Lock()
        self.create_table()

    def create_table(self):
        with self.lock:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    user_id INTEGER,
                    role TEXT,
                    content TEXT
                )
            """)
            self.conn.commit()

    def insert_message(self, user_id, role, content):
        with self.lock:
            self.conn.execute(
                "INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)",
                (user_id, role, content)
            )
            self.conn.commit()

    def get_messages_by_user(self_id):
        with self.lock:
            cursor = self.conn.execute(
                "SELECT role, content FROM messages WHERE user_id = ?",
                (self_id,)
            )
            return [{"role": row[0], "content": row[1]} for row in cursor.fetchall()]
