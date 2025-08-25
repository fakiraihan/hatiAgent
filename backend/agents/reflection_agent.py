"""
Reflection Agent - Specialist for introspective conversations using Groq LLM
"""

from typing import Dict, Any, List
import sys
import os

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from backend.core.base_agent import BaseAgent
from backend.core.groq_client import groq_client

class ReflectionAgent(BaseAgent):
    """Agent for deep reflection and introspective conversations"""
    
    def __init__(self):
        super().__init__("reflection")
        self.conversation_history = {}  # Store conversation context per user
        self.conversation_summaries = {}  # Store conversation summaries per user
    
    async def process(self, user_message: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process reflection conversation request with context awareness
        
        Returns:
            {
                "main_response": "conversational response",
                "conversation_type": "supportive/empathetic",
                "emotional_context": "detected emotions", 
                "session_context": {...}
            }
        """
        try:
            mood = parameters.get("mood", "contemplative")
            session_id = parameters.get("session_id", "default")
            
            self.log_activity(f"Reflection conversation: mood: {mood}, session: {session_id}")
            
            # Get conversation history for this session
            conversation_context = self.conversation_history.get(session_id, [])
            
            # Generate contextual conversational response
            main_response = await self._generate_conversational_response(
                user_message, mood, conversation_context, session_id
            )
            
            # Update conversation history
            await self._update_conversation_history(session_id, user_message, main_response)
            
            return {
                "main_response": main_response,
                "conversation_type": "supportive",
                "emotional_context": mood,
                "session_context": {
                    "mood": mood,
                    "message_length": len(user_message),
                    "conversation_turns": len(conversation_context)
                }
            }
            
        except Exception as e:
            self.log_activity(f"Error processing reflection request: {e}", "ERROR")
            return self._fallback_response(user_message)
    
    async def _generate_conversational_response(self, user_message: str, mood: str, conversation_context: List, session_id: str) -> str:
        """Generate natural conversational response with context awareness"""
        
        # Build conversation history for context
        context_text = ""
        session_summary = self.conversation_summaries.get(session_id, "")
        
        if session_summary:
            context_text += f"Previous conversation summary: {session_summary}\n\n"
        
        if conversation_context:
            context_text += "Recent conversation:\n"
            for turn in conversation_context[-5:]:  # Last 5 turns for context (increased from 3)
                context_text += f"User: {turn['user']}\nYou: {turn['assistant']}\n"
            context_text += "\nCurrent message:\n"
        
        system_prompt = f"""
        Kamu adalah teman dekat yang bisa diajak curhat. Respond dengan natural kayak ngobrol di WhatsApp.
        
        KARAKTERISTIK:
        - Ngobrol santai, pake bahasa Indonesia casual
        - Care dan supportive tapi ga formal
        - Fokus dengerin dan validasi perasaan mereka
        - Tanya follow-up yang natural buat bikin nyaman cerita
        - JANGAN langsung kasih rekomendasi musik/hiburan kecuali user eksplisit minta
        
        GAYA BICARA:
        - Kayak chat sama teman deket
        - Pake kata "iya", "emang", "banget", "sih", "dong", etc
        - Ga perlu panjang-panjang, 1-2 kalimat cukup
        - Kalau udah ada context sebelumnya, sambung dari situ
        - Tunjukkin empati yang genuine
        - FOKUS pada percakapan, bukan rekomendasi
        
        PENTING: HANYA suggest musik/hiburan kalau user bilang "minta rekomendasi" atau "cariin musik" atau hal serupa. Sebaliknya, tetap fokus jadi pendengar yang baik.
        
        SITUASI SEKARANG:
        - Mood: {mood}
        - User butuh tempat curhat dan didengar
        
        Respond natural dalam 1-2 kalimat pendek yang caring.
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{context_text}User: {user_message}"}
        ]
        
        try:
            response = await groq_client.chat_completion(
                messages=messages,
                temperature=0.8,
                max_tokens=200
            )
            
            return response.strip()
            
        except Exception as e:
            self.log_activity(f"Error generating conversational response: {e}", "ERROR")
            # Fallback responses based on mood
            fallback_responses = {
                "sad": "iya, kayaknya berat banget ya yang kamu rasain. mau cerita lebih lanjut?",
                "angry": "kesel banget ya? boleh cerita kenapa sampe segitunya?",
                "confused": "kayaknya lagi bingung banget nih. gimana ceritanya?",
                "anxious": "sepertinya lagi khawatir ya? ada apa emang?",
                "default": "kayaknya ada yang pengen diceritain nih. aku dengerin kok"
            }
            return fallback_responses.get(mood.lower(), fallback_responses["default"])
    
    async def _update_conversation_history(self, session_id: str, user_message: str, assistant_response: str):
        """Update conversation history for context with summarization"""
        if session_id not in self.conversation_history:
            self.conversation_history[session_id] = []
        
        self.conversation_history[session_id].append({
            "user": user_message,
            "assistant": assistant_response
        })
        
        # If conversation gets too long, summarize older parts
        if len(self.conversation_history[session_id]) > 20:  # Increased from 10 to 20
            await self._summarize_and_trim_conversation(session_id)
    
    async def _summarize_and_trim_conversation(self, session_id: str):
        """Summarize older conversation and keep recent parts"""
        conversation = self.conversation_history[session_id]
        
        # Take first 10 turns to summarize
        old_turns = conversation[:10]
        recent_turns = conversation[10:]
        
        # Create summary of old conversation
        old_conversation_text = ""
        for turn in old_turns:
            old_conversation_text += f"User: {turn['user']}\nAssistant: {turn['assistant']}\n"
        
        summary_prompt = f"""
        Summarize this conversation between a user and their supportive friend. 
        Focus on:
        - Main emotional themes and topics discussed
        - Key events or situations mentioned
        - User's feelings and emotional journey
        - Important context for future conversation
        
        Keep it concise but meaningful in Indonesian, casual tone.
        
        Conversation to summarize:
        {old_conversation_text}
        """
        
        try:
            summary = await groq_client.chat_completion(
                messages=[{"role": "user", "content": summary_prompt}],
                temperature=0.3,
                max_tokens=300
            )
            
            # Update or append to existing summary
            existing_summary = self.conversation_summaries.get(session_id, "")
            if existing_summary:
                self.conversation_summaries[session_id] = f"{existing_summary}\n\nLanjutan: {summary}"
            else:
                self.conversation_summaries[session_id] = summary
                
            # Keep only recent 10 turns in active memory
            self.conversation_history[session_id] = recent_turns
            
            self.log_activity(f"Conversation summarized for session {session_id}")
            
        except Exception as e:
            self.log_activity(f"Error summarizing conversation: {e}", "ERROR")
            # Fallback: just trim without summary
            self.conversation_history[session_id] = conversation[-15:]
    
    async def _generate_reflection_questions(self, user_message: str, mood: str) -> List[str]:
        """Generate casual questions to encourage sharing"""
        questions_by_mood = {
            "sad": [
                "kenapa itu sakit hatinya? boleh diceritain?",
                "ada yang bikin kecewa ya? gimana ceritanya?",
                "masih ada hal yang bikin seneng ga hari ini?"
            ],
            "anxious": [
                "lagi khawatir apa sih? sharing dong",
                "kayaknya overthinking nih, bener ga?",
                "kalau misal terjadi hal terburuk, terus gimana menurutmu?"
            ],
            "angry": [
                "kesel banget ya? kenapa emangnya?",
                "yang bikin sebel itu apa sih?",
                "pengen marah-marah atau pengen cerita dulu?"
            ],
            "confused": [
                "bingung ya? emang lagi mikirin apa?",
                "kayaknya dilema nih, gimana ceritanya?",
                "kata hati kamu gimana? ikutin aja dulu"
            ],
            "grateful": [
                "siapa yang paling berperan bikin kamu bersyukur?",
                "gimana caranya berbagi kebersyukuran ini sama orang lain?",
                "apa yang bisa kamu lakukan buat pertahanin perasaan positif ini?"
            ],
            "lonely": [
                "lagi berasa sendirian ya? gimana ceritanya?",
                "kapan terakhir kali chat sama temen? mau coba reach out ga?",
                "kadang sendirian itu berat ya, tapi kamu ga sendirian kok"
            ],
            "default": [
                "gimana perasaan kamu tentang hal ini?",
                "mau cerita lebih lanjut ga?",
                "ada yang pengen kamu sharing?"
            ]
        }
        
        return questions_by_mood.get(mood.lower(), questions_by_mood["default"])
    
    async def _generate_suggestions(self, mood: str, topic: str) -> List[Dict[str, str]]:
        """Generate casual suggestions for self-reflection"""
        suggestions = {
            "journaling": {
                "title": "Nulis di jurnal",
                "description": "Tulis aja 3 hal yang kamu rasain hari ini, bebas mau gimana",
                "time_needed": "10-15 menit",
                "benefits": "Bikin pikiran jadi lebih clear"
            },
            "meditation": {
                "title": "Duduk tenang bentar",
                "description": "Coba duduk diam dan perhatiin napas kamu aja",
                "time_needed": "5-10 menit",
                "benefits": "Bikin hati tenang dan pikiran jernih"
            },
            "letter_writing": {
                "title": "Nulis surat buat diri sendiri",
                "description": "Bayangin kamu lagi ngasih semangat ke diri sendiri",
                "time_needed": "15-20 menit",
                "benefits": "Jadi lebih sayang sama diri sendiri"
            },
            "gratitude": {
                "title": "Inget hal-hal baik",
                "description": "Tulis 5 hal yang bikin kamu seneng hari ini, sekecil apapun",
                "time_needed": "5 menit",
                "benefits": "Mood jadi lebih positif"
            },
            "body_scan": {
                "title": "Cek perasaan di badan",
                "description": "Perhatiin gimana rasanya di kepala, dada, sampe kaki",
                "time_needed": "10-15 menit",
                "benefits": "Nyambungin pikiran sama perasaan"
            },
            "music": {
                "title": "Dengerin musik",
                "description": "Pilih lagu yang sesuai sama mood kamu sekarang",
                "time_needed": "10-30 menit", 
                "benefits": "Bantu ekspresiin perasaan"
            },
            "walk": {
                "title": "Jalan-jalan bentar",
                "description": "Keluar rumah atau jalan di dalam ruangan aja",
                "time_needed": "10-20 menit",
                "benefits": "Bikin pikiran fresh"
            }
        }
        
        # Select appropriate suggestions based on mood
        mood_suggestions = {
            "sad": ["journaling", "music", "letter_writing"],
            "anxious": ["meditation", "walk", "body_scan"],
            "angry": ["walk", "body_scan", "music"],
            "confused": ["journaling", "walk", "letter_writing"],
            "grateful": ["gratitude", "journaling", "music"],
            "lonely": ["music", "letter_writing", "gratitude"]
        }
        
        selected_keys = mood_suggestions.get(mood.lower(), ["journaling", "music", "walk"])
        return [suggestions[key] for key in selected_keys[:3]]
    
    async def _generate_follow_up_prompts(self, user_message: str, mood: str) -> List[str]:
        """Generate prompts to continue the conversation"""
        prompts = [
            "cerita lebih lanjut yuk...",
            "apa yang paling berat dari situasi ini?",
            "biasanya kamu gimana sih kalau ngadepin perasaan kaya gini?",
            "ada orang yang bisa diajak ngobrol ga tentang hal ini?",
            "kamu berharap gimana setelah cerita ini?"
        ]
        
        mood_specific_prompts = {
            "sad": [
                "apa yang biasanya bikin kamu merasa lebih baik?",
                "kapan terakhir kali kamu seneng banget? karena apa?"
            ],
            "anxious": [
                "apa skenario terbaik yang mungkin terjadi?",
                "gimana cara kamu tenang-tenang kalau lagi cemas?"
            ],
            "angry": [
                "kamu maunya gimana sih sama orang atau situasi yang bikin kesel?",
                "gimana cara kamu ngungkapin marah tanpa nyakitin orang?"
            ]
        }
        
        specific_prompts = mood_specific_prompts.get(mood.lower(), [])
        return (specific_prompts + prompts)[:3]
    
    def _fallback_response(self, user_message: str) -> Dict[str, Any]:
        """Fallback response when reflection generation fails"""
        return {
            "main_response": "makasih ya udah mau cerita sama aku. kayaknya lagi ada yang bikin berat pikiran nih. aku di sini kalau mau lanjut cerita",
            "conversation_type": "supportive",
            "emotional_context": "general",
            "session_context": {
                "mood": "general",
                "message_length": len(user_message),
                "conversation_turns": 0
            },
            "error": "Reflection generation fallback"
        }
