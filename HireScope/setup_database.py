import sqlite3
import os

def setup_database():
   
    db_path = 'hirescope.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            skills TEXT,
            experience TEXT,
            job_role TEXT NOT NULL,
            resume_text TEXT NOT NULL,
            match_percentage INTEGER NOT NULL,
            filename TEXT NOT NULL,
            is_shortlisted BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT (datetime('now', '+5 hours', '+30 minutes'))

        )
    ''')
   
    uploads_dir = 'uploads'
    if not os.path.exists(uploads_dir):
        os.makedirs(uploads_dir)
        
    conn.commit()
    conn.close()
   
if __name__ == '__main__':
    setup_database()
