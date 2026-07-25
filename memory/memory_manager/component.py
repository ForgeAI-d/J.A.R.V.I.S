from core.base_manager import BaseManager
import uuid
from datetime import datetime, timezone
class MemoryManager(BaseManager):
    COMPONENT_ID = "memory.memory_manager"
    NAME = "MemoryManager"
    VERSION = "1.0.0-alpha"
    PRIORITY = 100
    AUTO_START = True

    def __init__(self, database_manager):
        BaseManager.__init__(self)
        self.db = database_manager
    def create_memory(
        self,
        user_id,
        category,
        content,
        importance=1
    ):
        memory_id = str(uuid.uuid4())
        self.db.cursor.execute(
            """
            INSERT INTO memory_entries (
                memory_id,
                user_id,
                category,
                content,
                importance,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                memory_id,
                user_id,
                category,
                content,
                importance,
                datetime.now(timezone.utc).isoformat()
            )
        )
        self.db.connection.commit()
        return memory_id
    def get_memory(self, memory_id):
        self.db.cursor.execute(
            """
            SELECT *
            FROM memory_entries
            WHERE memory_id = ?
            """,
            (memory_id,)
        )
        result = self.db.cursor.fetchone()
        if result:
            return dict(result)
        return None
    def get_user_memories(self, user_id):
        self.db.cursor.execute(
            """
            SELECT *
            FROM memory_entries
            WHERE user_id = ?
            ORDER BY importance DESC
            """,
            (user_id,)
        )
        return [
            dict(row)
            for row in self.db.cursor.fetchall()
        ]
    def get_memories_by_category(
        self,
        user_id,
        category
    ):
        self.db.cursor.execute(
            """
            SELECT *
            FROM memory_entries
            WHERE user_id = ?
            AND category = ?
            ORDER BY importance DESC
            """,
            (
                user_id,
                category
            )
        )
        return [
            dict(row)
            for row in self.db.cursor.fetchall()
        ]
    def update_memory(
        self,
        memory_id,
        new_content
    ):
        self.db.cursor.execute(
            """
            UPDATE memory_entries
            SET content = ?
            WHERE memory_id = ?
            """,
            (
                new_content,
                memory_id
            )
        )
        self.db.connection.commit()
    def delete_memory(self, memory_id):
        self.db.cursor.execute(
            """
            DELETE FROM memory_entries
            WHERE memory_id = ?
            """,
            (memory_id,)
        )
        self.db.connection.commit()
    def search_memories(
        self,
        user_id,
        keyword
    ):
        self.db.cursor.execute(
            """
            SELECT *
            FROM memory_entries
            WHERE user_id = ?
            AND content LIKE ?
            """,
            (
                user_id,
                f"%{keyword}%"
            )
        )
        return [
            dict(row)
            for row in self.db.cursor.fetchall()
        ]
    def get_important_memories(
        self,
        user_id,
        minimum_importance=5
    ):
        self.db.cursor.execute(
            """
            SELECT *
            FROM memory_entries
            WHERE user_id = ?
            AND importance >= ?
            ORDER BY importance DESC
            """,
            (
                user_id,
                minimum_importance
            )
        )
        return [
            dict(row)
            for row in self.db.cursor.fetchall()
        ]
