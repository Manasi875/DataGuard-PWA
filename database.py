import os
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path('/tmp/dataguard.db') if os.environ.get('VERCEL') else BASE_DIR / 'dataguard.db'


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def init_db():
    conn = get_connection()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS datasets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            original_name TEXT NOT NULL,
            stored_name TEXT NOT NULL,
            rows_count INTEGER NOT NULL DEFAULT 0,
            columns_count INTEGER NOT NULL DEFAULT 0,
            missing_count INTEGER NOT NULL DEFAULT 0,
            duplicate_count INTEGER NOT NULL DEFAULT 0,
            outlier_count INTEGER NOT NULL DEFAULT 0,
            quality_score REAL NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS columns_profile (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_id INTEGER NOT NULL,
            column_name TEXT NOT NULL,
            data_type TEXT NOT NULL,
            missing_count INTEGER NOT NULL DEFAULT 0,
            unique_count INTEGER NOT NULL DEFAULT 0,
            outlier_count INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS analysis_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            quality_score REAL NOT NULL DEFAULT 0,
            missing_count INTEGER NOT NULL DEFAULT 0,
            duplicate_count INTEGER NOT NULL DEFAULT 0,
            outlier_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT NOT NULL,
            details TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
        );
    ''')

    # Migration for older DataGuard databases.
    user_columns = [r['name'] for r in conn.execute('PRAGMA table_info(users)').fetchall()]
    if 'role' not in user_columns:
        conn.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")

    admin_username = os.environ.get('DATAGUARD_ADMIN_USERNAME', 'admin')
    admin_email = os.environ.get('DATAGUARD_ADMIN_EMAIL', 'admin@dataguard.local')
    admin_password = os.environ.get('DATAGUARD_ADMIN_PASSWORD', 'Admin@12345')

    existing_admin = conn.execute("SELECT id FROM users WHERE role='admin' LIMIT 1").fetchone()
    if not existing_admin:
        existing_user = conn.execute(
            "SELECT id FROM users WHERE lower(username)=lower(?) OR lower(email)=lower(?)",
            (admin_username, admin_email)
        ).fetchone()
        if existing_user:
            conn.execute('UPDATE users SET role="admin" WHERE id=?', (existing_user['id'],))
        else:
            from werkzeug.security import generate_password_hash
            conn.execute(
                'INSERT INTO users(username,email,password_hash,role) VALUES(?,?,?,"admin")',
                (admin_username, admin_email, generate_password_hash(admin_password))
            )

    conn.commit()
    conn.close()
