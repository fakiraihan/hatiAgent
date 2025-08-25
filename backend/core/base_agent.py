"""
Base Agent Class for Hati Multi-Agent System
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """Base class for all agents in the Hati system"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"agent.{name}")
    
    @abstractmethod
    async def process(self, user_message: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process user request and return structured data
        
        Args:
            user_message: Original user message
            parameters: Parameters from manager agent analysis
            
        Returns:
            Structured data in JSON format
        """
        pass
    
    async def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """
        Validate input parameters for this agent
        
        Args:
            parameters: Parameters to validate
            
        Returns:
            True if valid, False otherwise
        """
        return True
    
    def log_activity(self, message: str, level: str = "INFO"):
        """Log agent activity"""
        if level.upper() == "ERROR":
            self.logger.error(f"[{self.name}] {message}")
        elif level.upper() == "WARNING":
            self.logger.warning(f"[{self.name}] {message}")
        else:
            self.logger.info(f"[{self.name}] {message}")

class ManagerAgent:
    """
    Manager Agent - Orchestrator and PR agent for the Hati system
    Handles delegation to specialist agents and response personalization
    """
    
    def __init__(self, groq_client):
        self.groq_client = groq_client
        self.specialists = {}
        self.logger = logging.getLogger("agent.manager")
    
    def register_specialist(self, agent_type: str, agent: BaseAgent):
        """Register a specialist agent"""
        self.specialists[agent_type] = agent
        self.logger.info(f"Registered specialist agent: {agent_type}")
    
    async def process_message(self, user_message: str) -> str:
        """
        Main processing pipeline:
        1. Analyze and delegate (LLM Call #1)
        2. Call specialist agent
        3. Personalize response (LLM Call #2)
        
        Args:
            user_message: User's input message
            
        Returns:
            Final personalized response
        """
        try:
            # Step 1: Analyze and delegate
            self.logger.info(f"Processing message: {user_message[:50]}...")
            delegation_result = await self.groq_client.analyze_and_delegate(user_message)
            
            agent_type = delegation_result.get("agent", "reflection")
            parameters = delegation_result.get("parameters", {})
            mood = delegation_result.get("mood", "neutral")
            
            # Add mood to parameters so specialist agents can access it
            parameters["mood"] = mood
            
            self.logger.info(f"Delegated to agent: {agent_type} (mood: {mood})")
            
            # Step 2: Call specialist agent
            if agent_type not in self.specialists:
                self.logger.warning(f"Agent {agent_type} not found, falling back to reflection")
                agent_type = "reflection"
            
            specialist = self.specialists[agent_type]
            specialist_data = await specialist.process(user_message, parameters)
            
            # Add delegation context to specialist data
            specialist_data["delegation_context"] = {
                "detected_mood": mood,
                "reasoning": delegation_result.get("reasoning", "")
            }
            
            # Step 3: Personalize response
            final_response = await self.groq_client.personalize_response(
                user_message=user_message,
                specialist_data=specialist_data,
                agent_type=agent_type
            )
            
            self.logger.info(f"Generated final response ({len(final_response)} chars)")
            return final_response
            
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            return "Maaf, aku sedang mengalami sedikit masalah. Bisa coba lagi sebentar lagi?"
