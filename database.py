import os
import sqlite3
import datetime
import logging
from typing import List, Dict, Any, Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HavenDatabase")

SQLITE_DB_FILE = "companion_memory.db"

class HavenDatabase:
    def __init__(self, mongodb_uri: Optional[str] = None):
        """
        Initialize Haven's Hybrid Persistent Memory.
        Primary: MongoDB Atlas (if mongodb_uri provided and reachable)
        Fallback: Local SQLite database (companion_memory.db)
        """
        self.mongodb_uri = mongodb_uri or os.getenv("MONGODB_URI")
        self.mongo_client = None
        self.mongo_db = None
        self.collection = None
        self.is_mongo_active = False

        self._init_sqlite()
        if self.mongodb_uri:
            self._try_connect_mongodb()

    def _init_sqlite(self):
        """Initialize local SQLite database table if it doesn't exist."""
        try:
            with sqlite3.connect(SQLITE_DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        speaker TEXT NOT NULL,
                        text TEXT NOT NULL,
                        emotion_tag TEXT DEFAULT 'neutral'
                    )
                """)
                conn.commit()
            logger.info("SQLite database initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize SQLite database: {e}")

    def _try_connect_mongodb(self) -> bool:
        """Attempt to connect to MongoDB Atlas with a 2-second timeout."""
        if not self.mongodb_uri:
            self.is_mongo_active = False
            return False
        
        try:
            from pymongo import MongoClient
            # 2 second timeout for fast fallback if unreachable
            client = MongoClient(self.mongodb_uri, serverSelectionTimeoutMS=2000)
            # Check connection using admin ping command
            client.admin.command('ping')
            
            self.mongo_client = client
            self.mongo_db = client["haven_db"]
            self.collection = self.mongo_db["memory"]
            self.is_mongo_active = True
            logger.info("Successfully connected to MongoDB Atlas.")
            return True
        except Exception as e:
            logger.warning(f"MongoDB Atlas connection failed: {e}. Falling back to SQLite.")
            self.mongo_client = None
            self.mongo_db = None
            self.collection = None
            self.is_mongo_active = False
            return False

    def get_storage_mode(self) -> Dict[str, str]:
        """Return the current active storage mode and details."""
        if self.is_mongo_active:
            return {
                "mode": "MongoDB Atlas",
                "status": "Connected (Cloud Persistent)",
                "icon": "☁️"
            }
        else:
            return {
                "mode": "SQLite (Local)",
                "status": "Active (Local Offline)",
                "icon": "💾"
            }

    def save_message(self, speaker: str, text: str, emotion_tag: str = "neutral") -> bool:
        """
        Save a message to the active database (MongoDB Atlas or SQLite).
        """
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        # Primary: Mongo Atlas if active
        if self.is_mongo_active and self.collection is not None:
            try:
                doc = {
                    "timestamp": timestamp,
                    "speaker": speaker,
                    "text": text,
                    "emotion_tag": emotion_tag
                }
                self.collection.insert_one(doc)
                logger.info(f"Message saved to MongoDB Atlas ({speaker}).")
                # Also mirror to SQLite for local sync backup
                self._save_sqlite(timestamp, speaker, text, emotion_tag)
                return True
            except Exception as e:
                logger.error(f"Error saving to MongoDB Atlas: {e}. Falling back to SQLite.")
                self.is_mongo_active = False

        # Fallback: SQLite
        return self._save_sqlite(timestamp, speaker, text, emotion_tag)

    def _save_sqlite(self, timestamp: str, speaker: str, text: str, emotion_tag: str) -> bool:
        try:
            with sqlite3.connect(SQLITE_DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO messages (timestamp, speaker, text, emotion_tag) VALUES (?, ?, ?, ?)",
                    (timestamp, speaker, text, emotion_tag)
                )
                conn.commit()
            logger.info(f"Message saved to SQLite ({speaker}).")
            return True
        except Exception as e:
            logger.error(f"Error saving to SQLite: {e}")
            return False

    def get_recent_context(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch the most recent N messages for conversational context.
        Returns chronologically sorted list of dicts:
        [{'speaker': 'User'|'Haven', 'text': '...', 'timestamp': '...', 'emotion_tag': '...'}]
        """
        if self.is_mongo_active and self.collection is not None:
            try:
                cursor = self.collection.find().sort("timestamp", -1).limit(limit)
                docs = list(cursor)
                docs.reverse()  # Oldest to newest
                return [
                    {
                        "speaker": d.get("speaker"),
                        "text": d.get("text"),
                        "timestamp": d.get("timestamp"),
                        "emotion_tag": d.get("emotion_tag", "neutral")
                    }
                    for d in docs
                ]
            except Exception as e:
                logger.error(f"Error fetching from MongoDB Atlas: {e}. Falling back to SQLite.")
                self.is_mongo_active = False

        # Fallback SQLite
        try:
            with sqlite3.connect(SQLITE_DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT speaker, text, timestamp, emotion_tag FROM messages ORDER BY id DESC LIMIT ?",
                    (limit,)
                )
                rows = cursor.fetchall()
                rows.reverse()  # Oldest to newest
                return [
                    {
                        "speaker": row[0],
                        "text": row[1],
                        "timestamp": row[2],
                        "emotion_tag": row[3]
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Error fetching recent context from SQLite: {e}")
            return []

    def get_all_history(self) -> List[Dict[str, Any]]:
        """
        Fetch all history records for the history drawer.
        """
        if self.is_mongo_active and self.collection is not None:
            try:
                cursor = self.collection.find().sort("timestamp", 1)
                return [
                    {
                        "speaker": d.get("speaker"),
                        "text": d.get("text"),
                        "timestamp": d.get("timestamp"),
                        "emotion_tag": d.get("emotion_tag", "neutral")
                    }
                    for d in cursor
                ]
            except Exception as e:
                logger.error(f"Error fetching history from MongoDB Atlas: {e}")

        # Fallback SQLite
        try:
            with sqlite3.connect(SQLITE_DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT speaker, text, timestamp, emotion_tag FROM messages ORDER BY id ASC")
                rows = cursor.fetchall()
                return [
                    {
                        "speaker": row[0],
                        "text": row[1],
                        "timestamp": row[2],
                        "emotion_tag": row[3]
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Error fetching history from SQLite: {e}")
            return []

    def clear_memory(self) -> bool:
        """
        Cleanly wipe memory from active store and local backup.
        """
        success = True
        # Clear Mongo
        if self.is_mongo_active and self.collection is not None:
            try:
                self.collection.delete_many({})
                logger.info("MongoDB memory wiped.")
            except Exception as e:
                logger.error(f"Failed to wipe MongoDB memory: {e}")
                success = False

        # Clear SQLite
        try:
            with sqlite3.connect(SQLITE_DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM messages")
                conn.commit()
            logger.info("SQLite memory wiped.")
        except Exception as e:
            logger.error(f"Failed to wipe SQLite memory: {e}")
            success = False

        return success
