"""
SQLite Database Manager for Hati Multi-Agent Platform
Handles user conversations, caching, and agent memory
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path: str = None):
        """Initialize database manager"""
        if db_path is None:
            # Default to data directory in project root
            project_root = Path(__file__).parent.parent.parent
            db_path = project_root / "data" / "hati.db"
        else:
            db_path = Path(db_path)
        
        self.db_path = str(db_path)
        self.ensure_directory()
        self.init_database()
    
    def ensure_directory(self):
        """Ensure the database directory exists"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        try:
            yield conn
        finally:
            conn.close()
    
    def init_database(self):
        """Initialize database tables"""
        with self.get_connection() as conn:
            conn.executescript("""
            -- User profiles and preferences
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE NOT NULL,
                name TEXT,
                preferred_mood TEXT,
                music_preferences TEXT, -- JSON
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Conversation history
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                user_message TEXT NOT NULL,
                bot_response TEXT NOT NULL,
                mood_detected TEXT,
                agent_used TEXT,
                agent_data TEXT, -- JSON response from specialist agents
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES users (session_id)
            );
            
            -- API response cache
            CREATE TABLE IF NOT EXISTS api_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cache_key TEXT UNIQUE NOT NULL,
                response_data TEXT NOT NULL, -- JSON
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Agent memory for learning user preferences
            CREATE TABLE IF NOT EXISTS agent_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                agent_type TEXT NOT NULL,
                memory_key TEXT NOT NULL,
                memory_value TEXT NOT NULL, -- JSON
                importance_score INTEGER DEFAULT 1, -- 1-10 scale
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(session_id, agent_type, memory_key)
            );
            
            -- Mood patterns and analytics
            CREATE TABLE IF NOT EXISTS mood_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                mood TEXT NOT NULL,
                triggers TEXT, -- JSON array of detected triggers
                successful_interventions TEXT, -- JSON array of what worked
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Create indexes for performance
            CREATE INDEX IF NOT EXISTS idx_conversations_session 
                ON conversations(session_id, timestamp);
            CREATE INDEX IF NOT EXISTS idx_cache_key 
                ON api_cache(cache_key, expires_at);
            CREATE INDEX IF NOT EXISTS idx_agent_memory_session 
                ON agent_memory(session_id, agent_type);
            CREATE INDEX IF NOT EXISTS idx_mood_patterns_session 
                ON mood_patterns(session_id, timestamp);
            """)
            conn.commit()
            logger.info("Database initialized successfully")

    # User Management
    def create_or_update_user(self, session_id: str, name: str = None, 
                             preferences: Dict = None) -> Dict:
        """Create or update user profile"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if user exists
            cursor.execute("SELECT * FROM users WHERE session_id = ?", (session_id,))
            user = cursor.fetchone()
            
            if user:
                # Update existing user
                updates = ["last_active = CURRENT_TIMESTAMP"]
                params = []
                
                if name:
                    updates.append("name = ?")
                    params.append(name)
                
                if preferences:
                    updates.append("music_preferences = ?")
                    params.append(json.dumps(preferences))
                
                params.append(session_id)
                
                cursor.execute(f"""
                    UPDATE users SET {', '.join(updates)}
                    WHERE session_id = ?
                """, params)
            else:
                # Create new user
                cursor.execute("""
                    INSERT INTO users (session_id, name, music_preferences)
                    VALUES (?, ?, ?)
                """, (session_id, name, json.dumps(preferences or {})))
            
            conn.commit()
            
            # Return updated user data
            cursor.execute("SELECT * FROM users WHERE session_id = ?", (session_id,))
            return dict(cursor.fetchone())

    def get_user(self, session_id: str) -> Optional[Dict]:
        """Get user profile"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE session_id = ?", (session_id,))
            user = cursor.fetchone()
            return dict(user) if user else None

    # Conversation History
    def save_conversation(self, session_id: str, user_message: str, 
                         bot_response: str, mood_detected: str = None,
                         agent_used: str = None, agent_data: Dict = None):
        """Save conversation to history"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO conversations 
                (session_id, user_message, bot_response, mood_detected, 
                 agent_used, agent_data)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (session_id, user_message, bot_response, mood_detected,
                  agent_used, json.dumps(agent_data or {})))
            conn.commit()

    def get_conversation_history(self, session_id: str, limit: int = 10) -> List[Dict]:
        """Get recent conversation history"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM conversations 
                WHERE session_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (session_id, limit))
            return [dict(row) for row in cursor.fetchall()]

    # API Caching
    def get_cached_response(self, cache_key: str) -> Optional[Dict]:
        """Get cached API response if not expired"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT response_data FROM api_cache 
                WHERE cache_key = ? AND expires_at > CURRENT_TIMESTAMP
            """, (cache_key,))
            result = cursor.fetchone()
            return json.loads(result[0]) if result else None

    def cache_response(self, cache_key: str, data: Dict, ttl_hours: int = 24):
        """Cache API response with TTL"""
        expires_at = datetime.now() + timedelta(hours=ttl_hours)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO api_cache 
                (cache_key, response_data, expires_at)
                VALUES (?, ?, ?)
            """, (cache_key, json.dumps(data), expires_at))
            conn.commit()

    def cleanup_expired_cache(self):
        """Remove expired cache entries"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM api_cache 
                WHERE expires_at < CURRENT_TIMESTAMP
            """)
            deleted = cursor.rowcount
            conn.commit()
            logger.info(f"Cleaned up {deleted} expired cache entries")

    # Agent Memory
    def save_agent_memory(self, session_id: str, agent_type: str, 
                         memory_key: str, memory_value: Any, 
                         importance_score: int = 5):
        """Save agent memory for user personalization"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO agent_memory 
                (session_id, agent_type, memory_key, memory_value, 
                 importance_score, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (session_id, agent_type, memory_key, 
                  json.dumps(memory_value), importance_score))
            conn.commit()

    def get_agent_memory(self, session_id: str, agent_type: str) -> Dict:
        """Get all memories for specific agent and user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT memory_key, memory_value, importance_score 
                FROM agent_memory 
                WHERE session_id = ? AND agent_type = ?
                ORDER BY importance_score DESC, updated_at DESC
            """, (session_id, agent_type))
            
            memories = {}
            for row in cursor.fetchall():
                memories[row[0]] = {
                    'value': json.loads(row[1]),
                    'importance': row[2]
                }
            return memories

    # Mood Analytics
    def save_mood_pattern(self, session_id: str, mood: str, 
                         triggers: List[str] = None, 
                         successful_interventions: List[str] = None):
        """Save mood pattern for analytics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO mood_patterns 
                (session_id, mood, triggers, successful_interventions)
                VALUES (?, ?, ?, ?)
            """, (session_id, mood, json.dumps(triggers or []),
                  json.dumps(successful_interventions or [])))
            conn.commit()

    def get_mood_analytics(self, session_id: str, days: int = 30) -> Dict:
        """Get mood analytics for user"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Mood frequency
            cursor.execute("""
                SELECT mood, COUNT(*) as count 
                FROM mood_patterns 
                WHERE session_id = ? AND timestamp > ?
                GROUP BY mood
                ORDER BY count DESC
            """, (session_id, cutoff_date))
            mood_frequency = dict(cursor.fetchall())
            
            # Common triggers
            cursor.execute("""
                SELECT triggers FROM mood_patterns 
                WHERE session_id = ? AND timestamp > ?
            """, (session_id, cutoff_date))
            
            all_triggers = []
            for row in cursor.fetchall():
                triggers = json.loads(row[0])
                all_triggers.extend(triggers)
            
            # Count trigger frequency
            trigger_count = {}
            for trigger in all_triggers:
                trigger_count[trigger] = trigger_count.get(trigger, 0) + 1
            
            return {
                'mood_frequency': mood_frequency,
                'common_triggers': dict(sorted(trigger_count.items(), 
                                             key=lambda x: x[1], reverse=True)[:10]),
                'total_entries': sum(mood_frequency.values()),
                'period_days': days
            }

# Global database instance
db_manager = None

def get_db() -> DatabaseManager:
    """Get database manager singleton"""
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager()
    return db_manager

def init_database():
    """Initialize database on startup"""
    global db_manager
    db_manager = DatabaseManager()
    return db_manager
