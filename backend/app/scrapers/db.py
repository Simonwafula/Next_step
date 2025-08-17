# scrapers/db.py
import sqlite3
import logging
from pathlib import Path
from scrapers.config import DB_PATH, TABLE_NAME

logging.basicConfig(level=logging.INFO)

class Database:
    def __init__(self, db_path: str = DB_PATH, table: str = TABLE_NAME):
        self.db_path = db_path
        self.table   = table
        self.conn    = None

    def connect(self):
        # Ensure directory exists
        db_file = Path(self.db_path)
        if db_file.parent:
            db_file.parent.mkdir(parents=True, exist_ok=True)

        # Open connection and enable foreign keys
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._ensure_table()
        logging.info(f"Connected to DB at {self.db_path}, table '{self.table}' ready.")

    def close(self):
        if self.conn:
            self.conn.close()
            logging.info("Database connection closed.")

    def _ensure_table(self):
        sql = f"""
        CREATE TABLE IF NOT EXISTS {self.table} (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            full_link  TEXT    UNIQUE,
            title      TEXT,
            content    TEXT
        )
        """
        self.conn.execute(sql)
        self.conn.commit()
        logging.info(f"Ensured table `{self.table}` exists.")

    def batch_insert(self, rows):
        """
        Insert multiple rows into the jobs table.
        `rows` is an iterable of (title, full_link, content) tuples.
        Returns number of new rows inserted.
        """
        if not self.conn:
            raise RuntimeError("Database not connected. Call connect() first.")

        cursor = self.conn.cursor()
        inserted = 0
        try:
            for title, link, content in rows:
                try:
                    cursor.execute(f"""
                        INSERT OR IGNORE INTO {self.table} (title, full_link, content)
                        VALUES (?, ?, ?)
                    """, (title, link, content))
                    if cursor.rowcount:
                        inserted += 1
                except sqlite3.Error as e:
                    logging.error(f"DB error inserting '{{title}}': {e}")
            self.conn.commit()
            logging.info(f"Inserted {inserted} new rows into '{self.table}'.")
        except Exception as e:
            logging.error(f"Batch insert failed: {e}")
            self.conn.rollback()
        return inserted
