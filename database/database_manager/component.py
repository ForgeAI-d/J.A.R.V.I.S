from core.base_manager import BaseManager
import sqlite3
from pathlib import Path
class DatabaseManager(BaseManager):
    COMPONENT_ID = "database.database_manager"
    NAME = "DatabaseManager"
    VERSION = "1.0.0-alpha"
    PRIORITY = 100
    AUTO_START = True

    DATABASE_NAME = "jarvis.db"
    def __init__(self):
        BaseManager.__init__(self)
        self.database_path = (
            Path(__file__).parent /
            self.DATABASE_NAME
        )
        self.connection = sqlite3.connect(
            self.database_path,
            check_same_thread=False
        )
        self.connection.row_factory = sqlite3.Row
        self.cursor = self.connection.cursor()
        self.cursor.execute(
            "PRAGMA foreign_keys = ON"
        )
        self.initialize_database()
    def initialize_database(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                display_name TEXT,
                role TEXT NOT NULL,
                relationship TEXT NOT NULL,
                status TEXT NOT NULL,
                voice_profile_id TEXT,
                profile_metadata TEXT,
                created_at TEXT NOT NULL,
                last_seen TEXT
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS voice_profiles (
                voice_profile_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                profile_name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_trained TEXT,
                confidence REAL DEFAULT 0,
                FOREIGN KEY(user_id)
                    REFERENCES users(user_id)
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS face_profiles (
                face_profile_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                profile_name TEXT NOT NULL,
                encoding_path TEXT,
                created_at TEXT NOT NULL,
                last_seen TEXT,
                confidence REAL DEFAULT 0,
                FOREIGN KEY(user_id)
                    REFERENCES users(user_id)
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                device_id TEXT PRIMARY KEY,
                owner_id TEXT,
                name TEXT NOT NULL,
                device_type TEXT NOT NULL,
                platform TEXT,
                trusted INTEGER NOT NULL,
                status TEXT NOT NULL,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                device_fingerprint TEXT,
                agent_version TEXT,
                local_ip TEXT,
                public_ip TEXT,
                lost_mode INTEGER NOT NULL DEFAULT 0,
                quarantine_mode INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(owner_id)
                    REFERENCES users(user_id)
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS permissions (
                permission_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                permission_name TEXT NOT NULL,
                allowed INTEGER NOT NULL,
                critical INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id)
                    REFERENCES users(user_id)
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS permission_logs (
                log_id TEXT PRIMARY KEY,
                user_id TEXT,
                device_id TEXT,
                permission_name TEXT NOT NULL,
                result TEXT NOT NULL,
                reason TEXT,
                source TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY(user_id)
                    REFERENCES users(user_id),
                FOREIGN KEY(device_id)
                    REFERENCES devices(device_id)
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL,
                priority INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                completed_at TEXT
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                source TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_entries (
                memory_id TEXT PRIMARY KEY,
                user_id TEXT,
                category TEXT NOT NULL,
                content TEXT NOT NULL,
                importance INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id)
                    REFERENCES users(user_id)
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                notification_id TEXT PRIMARY KEY,
                user_id TEXT,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                read INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(user_id)
                    REFERENCES users(user_id)
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS backups (
                backup_id TEXT PRIMARY KEY,
                backup_name TEXT NOT NULL,
                backup_path TEXT NOT NULL,
                created_at TEXT NOT NULL,
                checksum TEXT
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS smart_home_devices (
                device_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                room TEXT,
                status TEXT,
                last_update TEXT
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS locations (
                location_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                radius REAL NOT NULL,
                FOREIGN KEY(user_id)
                    REFERENCES users(user_id)
            )
        """)
        self.connection.commit()
    def execute(
        self,
        query,
        parameters=()
    ):
        try:
            self.cursor.execute(
                query,
                parameters
            )
            self.connection.commit()
            return True
        except sqlite3.Error as error:
            print(
                f"Database Error: {error}"
            )
            return False
    def fetchone(
        self,
        query,
        parameters=()
    ):
        try:
            self.cursor.execute(
                query,
                parameters
            )
            return self.cursor.fetchone()
        except sqlite3.Error as error:
            print(
                f"Database Error: {error}"
            )
            return None
    def fetchall(
        self,
        query,
        parameters=()
    ):
        try:
            self.cursor.execute(
                query,
                parameters
            )
            return self.cursor.fetchall()
        except sqlite3.Error as error:
            print(
                f"Database Error: {error}"
            )
            return []
    def health_check(self):
        try:
            self.cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = self.cursor.fetchall()
            return {
                "database": str(
                    self.database_path
                ),
                "status": "ONLINE",
                "table_count": len(
                    tables
                )
            }
        except Exception as error:
            return {
                "status": "ERROR",
                "error": str(error)
            }
    def close(self):
        self.connection.close()
if __name__ == "__main__":
    db = DatabaseManager()
    print(
        "=== DATABASE HEALTH ==="
    )
    print(
        db.health_check()
    )
    db.close()
