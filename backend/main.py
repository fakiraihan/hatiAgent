"""
FastAPI Application for Hati Multi-Agent System
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
# from fastapi.staticfiles import StaticFiles  # Not needed for streaming URLs
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging
import sys
import os
import uuid
from datetime import datetime

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from config.settings import settings
from backend.core.groq_client import groq_client
from backend.core.base_agent import ManagerAgent
from backend.agents.music_agent import MusicAgent
from backend.agents.entertainment_agent import EntertainmentAgent
from backend.agents.relaxation_agent import RelaxationAgent
from backend.agents.reflection_agent import ReflectionAgent
from backend.database.manager import init_database, get_db

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Initialize database
db = init_database()
logger.info("Database initialized successfully")

# Initialize FastAPI app
app = FastAPI(
    title="Hati - AI Mood Management",
    description="Multi-agent platform for mood management with memory and caching",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for local background music (DISABLED - using streaming URLs)
# music_directory = os.path.join(os.path.dirname(__file__), "music")
# app.mount("/music", StaticFiles(directory=music_directory), name="music")

# Initialize Manager Agent and Specialists
manager_agent = ManagerAgent(groq_client)

# Register specialist agents
manager_agent.register_specialist("music", MusicAgent())
manager_agent.register_specialist("entertainment", EntertainmentAgent())
manager_agent.register_specialist("relaxation", RelaxationAgent())
manager_agent.register_specialist("reflection", ReflectionAgent())

logger.info("Hati Multi-Agent System initialized successfully")

# Pydantic models for API
class ChatMessage(BaseModel):
    message: str
    user_id: str = "default"
    session_id: Optional[str] = None  # Will be auto-generated if not provided
    user_name: Optional[str] = None  # Optional, can be None
    preferences: Optional[Dict[str, Any]] = None  # Make it optional and handle conversion
    
    def __init__(self, **data):
        # Handle case where preferences is sent as a list instead of dict
        if 'preferences' in data and isinstance(data['preferences'], list):
            data['preferences'] = {}  # Convert empty list to empty dict
        super().__init__(**data)

class ChatResponse(BaseModel):
    response: str
    processing_time: float
    agent_used: str
    session_id: str
    metadata: Dict[str, Any] = {}
    personalized: bool = False

@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint with basic information"""
    return {
        "service": "Hati Multi-Agent Platform",
        "version": "1.0.0",
        "description": "High-speed mood management using Groq Cloud API",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test Groq connection
        test_messages = [{"role": "user", "content": "Hello"}]
        await groq_client.chat_completion(test_messages, max_tokens=10)
        groq_connected = True
    except Exception as e:
        logger.warning(f"Groq connection test failed: {e}")
        groq_connected = False
    
    return {
        "status": "healthy",
        "version": "1.0.0",
        "agents_registered": len(manager_agent.specialists),
        "groq_connected": groq_connected
    }

@app.get("/music/tracks")
async def get_background_music_tracks():
    """Get list of available streaming background music tracks"""
    try:
        # Streaming ambient music tracks (no local files needed)
        tracks = [
            {
                "id": "rain",
                "name": "Rain Ambience",
                "description": "Gentle rain sounds for relaxation",
                "url": "https://cdn.pixabay.com/download/audio/2024/10/30/audio_42e6870f29.mp3",
                "type": "ambient"
            },
            {
                "id": "forest",
                "name": "Forest Nature",
                "description": "Peaceful forest sounds and birds",
                "url": "https://cdn.freesound.org/previews/565/565564_8462944-lq.mp3",
                "type": "ambient"
            },
            {
                "id": "cafe",
                "name": "Cafe Ambience",
                "description": "Cozy coffee shop atmosphere",
                "url": "https://cdn.freesound.org/previews/567/567067_2097560-lq.mp3",
                "type": "ambient"
            },
            {
                "id": "ocean",
                "name": "Ocean Waves",
                "description": "Calming ocean wave sounds",
                "url": "https://cdn.freesound.org/previews/316/316847_5123451-lq.mp3",
                "type": "ambient"
            },
            {
                "id": "city",
                "name": "City Sounds",
                "description": "Urban environment background",
                "url": "https://cdn.freesound.org/previews/417/417443_7515445-lq.mp3",
                "type": "ambient"
            }
        ]
        
        return {
            "tracks": tracks,
            "total": len(tracks),
            "message": "Available streaming background music tracks"
        }
    except Exception as e:
        logger.error(f"Error getting music tracks: {e}")
        raise HTTPException(status_code=500, detail="Error loading music tracks")

@app.post("/chat-enhanced", response_model=Dict[str, Any])
async def chat_enhanced_endpoint(request: Request):
    """
    Enhanced chat endpoint with memory, caching and structured data
    """
    import time
    start_time = time.time()
    
    try:
        # Get raw body for debugging
        body = await request.body()
        logger.info(f"Raw request body: {body.decode()}")
        
        # Parse JSON manually to see what's coming in
        import json
        raw_data = json.loads(body.decode())
        logger.info(f"Parsed JSON data: {raw_data}")
        
        # Try to create ChatMessage
        message = ChatMessage(**raw_data)
        logger.info(f"ChatMessage created successfully: {message.model_dump()}")
        
        # Generate session ID if not provided
        if not message.session_id:
            message.session_id = str(uuid.uuid4())
            
        logger.info(f"Enhanced request from session {message.session_id}: {message.message[:50]}...")
        
        # Create or update user profile
        try:
            user_profile = db.create_or_update_user(
                session_id=message.session_id,
                name=message.user_name,
                preferences=message.preferences or {}  # Handle None case
            )
            logger.info(f"User profile created/updated: {user_profile}")
        except Exception as db_error:
            logger.error(f"Database error during user profile creation: {db_error}")
            # Continue without user profile for now
            user_profile = {}
        
        # Step 1: Analyze and delegate
        delegation_result = await manager_agent.groq_client.analyze_and_delegate(message.message)
        agent_type = delegation_result.get("agent", "reflection")
        parameters = delegation_result.get("parameters", {})
        mood = delegation_result.get("mood", "neutral")
        
        # Add session context to parameters
        parameters["mood"] = mood
        parameters["session_id"] = message.session_id
        parameters["user_profile"] = user_profile
        
        # Step 2: Get specialist data with memory
        specialist = manager_agent.specialists.get(agent_type)
        if specialist:
            specialist_data = await specialist.process(message.message, parameters)
        else:
            specialist_data = {}
        
        # Step 3: Generate conversational response with user history
        try:
            conversation_history = db.get_conversation_history(message.session_id, limit=3)
            context_messages = []
            for conv in reversed(conversation_history):  # Most recent first
                context_messages.extend([
                    {"role": "user", "content": conv["user_message"]},
                    {"role": "assistant", "content": conv["bot_response"]}
                ])
            logger.info(f"Retrieved {len(conversation_history)} conversation history items")
        except Exception as hist_error:
            logger.error(f"Error retrieving conversation history: {hist_error}")
            conversation_history = []
            context_messages = []
        
        response = await manager_agent.groq_client.personalize_response(
            user_message=message.message,
            specialist_data=specialist_data,
            agent_type=agent_type
        )
        
        processing_time = time.time() - start_time
        
        # Save conversation to database
        try:
            db.save_conversation(
                session_id=message.session_id,
                user_message=message.message,
                bot_response=response,
                mood_detected=mood,
                agent_used=agent_type,
                agent_data=specialist_data
            )
            logger.info("Conversation saved to database")
        except Exception as save_error:
            logger.error(f"Error saving conversation: {save_error}")

        # Save mood pattern for analytics  
        try:
            db.save_mood_pattern(
                session_id=message.session_id,
                mood=mood,
                triggers=[],  # Could be enhanced to detect triggers
                successful_interventions=[agent_type]
            )
            logger.info("Mood pattern saved to database")
        except Exception as mood_error:
            logger.error(f"Error saving mood pattern: {mood_error}")
        
        return {
            "response": response,
            "agent_used": agent_type,
            "mood_detected": mood,
            "specialist_data": specialist_data,
            "session_id": message.session_id,
            "personalized": bool(conversation_history),
            "processing_time": processing_time,
            "metadata": {
                "user_id": message.user_id,
                "session_id": getattr(message, 'session_id', 'default'),
                "message_length": len(message.message),
                "timestamp": time.time()
            }
        }
    except Exception as e:
        logger.error(f"Error in enhanced chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(message: ChatMessage):
    """
    Main chat endpoint with memory and session management
    """
    import time
    start_time = time.time()
    
    try:
        # Generate session ID if not provided
        if not message.session_id:
            message.session_id = str(uuid.uuid4())
        
        logger.info(f"Received message from session {message.session_id}: {message.message[:50]}...")
        
        # Create or update user profile
        db.create_or_update_user(
            session_id=message.session_id,
            name=message.user_name,
            preferences=message.preferences or {}  # Handle None case
        )
        
        # Process message through manager agent
        response = await manager_agent.process_message(message.message)
        
        processing_time = time.time() - start_time
        
        # Save conversation to database
        db.save_conversation(
            session_id=message.session_id,
            user_message=message.message,
            bot_response=response,
            mood_detected=None,  # Will be enhanced by manager agent later
            agent_used="manager"
        )
        
        logger.info(f"Response generated in {processing_time:.2f}s")
        

        return ChatResponse(
            response=response,
            processing_time=processing_time,
            agent_used="manager",
            session_id=message.session_id,
            metadata={
                "user_id": message.user_id,
                "message_length": len(message.message),
                "timestamp": time.time(),
                "database_enabled": True
            }
        )
        
    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error processing message: {str(e)}"
        )

@app.get("/analytics/{session_id}")
async def get_user_analytics(session_id: str, days: int = 30):
    """Get mood analytics for a specific user session"""
    try:
        analytics = db.get_mood_analytics(session_id, days)
        conversation_count = len(db.get_conversation_history(session_id, limit=1000))
        
        return {
            "session_id": session_id,
            "analytics_period_days": days,
            "mood_analytics": analytics,
            "total_conversations": conversation_count,
            "user_profile": db.get_user(session_id)
        }
    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/feedback/{session_id}")
async def provide_feedback(session_id: str, feedback: Dict[str, Any]):
    """Provide feedback for learning and improvement"""
    try:
        agent_type = feedback.get("agent_type")
        track_id = feedback.get("track_id")
        feedback_type = feedback.get("feedback", "neutral")
        data = feedback.get("data", {})
        
        # Get the appropriate specialist agent
        if agent_type and agent_type in manager_agent.specialists:
            specialist = manager_agent.specialists[agent_type]
            
            # If it's a music agent and has feedback learning capability
            if hasattr(specialist, 'learn_user_feedback'):
                specialist.learn_user_feedback(session_id, track_id, feedback_type, data)
            
            # General learning from success/failure
            if feedback_type in ['like', 'love', 'great']:
                if hasattr(specialist, 'learn_from_success'):
                    specialist.learn_from_success(session_id, data.get('request', ''), data, feedback_type)
            elif feedback_type in ['dislike', 'hate', 'bad']:
                if hasattr(specialist, 'learn_from_failure'):
                    specialist.learn_from_failure(session_id, data.get('request', ''), data, feedback_type)
        
        return {"status": "feedback_received", "message": "Thank you for your feedback!"}
        
    except Exception as e:
        logger.error(f"Error processing feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/cleanup")
async def cleanup_database():
    """Cleanup expired cache and old data"""
    try:
        db.cleanup_expired_cache()
        return {"status": "cleanup_completed", "message": "Database cleaned up successfully"}
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug
    )
