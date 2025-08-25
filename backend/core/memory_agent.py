"""
Enhanced Base Agent with Memory and Learning Capabilities
Extends the original base agent with database-backed memory
"""

from ..core.base_agent import BaseAgent
from ..database.manager import get_db
from typing import Dict, List, Any, Optional
import logging
import hashlib
import json

logger = logging.getLogger(__name__)

class MemoryAgent(BaseAgent):
    """Base agent with memory and learning capabilities"""
    
    def __init__(self, agent_type: str):
        super().__init__(agent_type)
        self.agent_type = agent_type
        self.db = get_db()
    
    def remember(self, session_id: str, key: str, value: Any, importance: int = 5):
        """Store a memory for this user and agent"""
        try:
            self.db.save_agent_memory(session_id, self.agent_type, key, value, importance)
            logger.info(f"{self.agent_type} saved memory: {key} for {session_id}")
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")
    
    def recall(self, session_id: str, key: str = None) -> Dict:
        """Recall memories for this user"""
        try:
            memories = self.db.get_agent_memory(session_id, self.agent_type)
            if key:
                return memories.get(key, {})
            return memories
        except Exception as e:
            logger.error(f"Failed to recall memory: {e}")
            return {}
    
    def get_user_preferences(self, session_id: str) -> Dict:
        """Get user's accumulated preferences for this agent"""
        memories = self.recall(session_id)
        preferences = {}
        
        for key, memory in memories.items():
            if memory['importance'] >= 7:  # High importance memories
                preferences[key] = memory['value']
        
        return preferences
    
    def learn_from_success(self, session_id: str, user_request: str, 
                          successful_response: Dict, user_feedback: str = None):
        """Learn from successful interactions"""
        try:
            # Extract patterns from successful interactions
            if user_feedback and any(word in user_feedback.lower() 
                                   for word in ['love', 'perfect', 'great', 'amazing']):
                
                # High importance learning
                self.remember(session_id, f"successful_response_{hash(user_request)}", 
                            successful_response, importance=8)
                
                # Learn preferences from the response
                self._extract_preferences(session_id, user_request, successful_response)
        
        except Exception as e:
            logger.error(f"Failed to learn from success: {e}")
    
    def learn_from_failure(self, session_id: str, user_request: str, 
                          failed_response: Dict, user_feedback: str = None):
        """Learn from failed interactions"""
        try:
            if user_feedback and any(word in user_feedback.lower() 
                                   for word in ['bad', 'terrible', 'hate', 'wrong']):
                
                # Remember what NOT to do
                self.remember(session_id, f"avoid_response_{hash(user_request)}", 
                            failed_response, importance=6)
        
        except Exception as e:
            logger.error(f"Failed to learn from failure: {e}")
    
    def get_cache_key(self, request_params: Dict) -> str:
        """Generate cache key for API requests"""
        # Create deterministic hash from request parameters
        params_str = json.dumps(request_params, sort_keys=True)
        return f"{self.agent_type}_{hashlib.md5(params_str.encode()).hexdigest()}"
    
    def get_cached_response(self, cache_key: str) -> Optional[Dict]:
        """Get cached API response"""
        try:
            return self.db.get_cached_response(cache_key)
        except Exception as e:
            logger.error(f"Failed to get cached response: {e}")
            return None
    
    def cache_response(self, cache_key: str, response: Dict, ttl_hours: int = 24):
        """Cache API response"""
        try:
            self.db.cache_response(cache_key, response, ttl_hours)
        except Exception as e:
            logger.error(f"Failed to cache response: {e}")
    
    def _extract_preferences(self, session_id: str, user_request: str, response: Dict):
        """Extract and store user preferences from successful interactions"""
        # This will be overridden by specific agents to extract relevant preferences
        pass
    
    def get_personalized_context(self, session_id: str, current_mood: str) -> str:
        """Get personalized context based on user history and preferences"""
        try:
            # Get conversation history
            history = self.db.get_conversation_history(session_id, limit=5)
            
            # Get user preferences
            preferences = self.get_user_preferences(session_id)
            
            # Get mood analytics
            mood_analytics = self.db.get_mood_analytics(session_id, days=7)
            
            context_parts = []
            
            if preferences:
                context_parts.append(f"User preferences: {json.dumps(preferences)}")
            
            if history:
                recent_moods = [conv.get('mood_detected') for conv in history[:3] 
                              if conv.get('mood_detected')]
                if recent_moods:
                    context_parts.append(f"Recent moods: {', '.join(recent_moods)}")
            
            if mood_analytics.get('mood_frequency'):
                top_mood = max(mood_analytics['mood_frequency'].items(), 
                              key=lambda x: x[1])[0]
                context_parts.append(f"Most common mood: {top_mood}")
            
            return " | ".join(context_parts) if context_parts else ""
            
        except Exception as e:
            logger.error(f"Failed to get personalized context: {e}")
            return ""

def hash(text: str) -> str:
    """Simple hash function for creating memory keys"""
    return hashlib.md5(text.encode()).hexdigest()[:8]
