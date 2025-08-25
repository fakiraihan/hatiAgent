"""
Core Groq LLM Client for Hati Project
Provides high-speed inference using Groq Cloud API
"""

import asyncio
from typing import Dict, List, Optional, Any
from groq import Groq
import sys
import os

# Add project root to path for config imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from config.settings import settings
import json
import logging

logger = logging.getLogger(__name__)

class GroqClient:
    """High-speed LLM client using Groq Cloud API"""
    
    def __init__(self):
        self.client = Groq(api_key=settings.groq_api_key)
        self.model = settings.groq_model
    
    async def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        max_tokens: int = 1000,
        temperature: float = 0.7,
        response_format: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Send chat completion request to Groq
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            response_format: Optional JSON response format
            
        Returns:
            Generated response content
        """
        try:
            completion_kwargs = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            
            if response_format:
                completion_kwargs["response_format"] = response_format
            
            # Use asyncio to run sync Groq client in async context
            loop = asyncio.get_event_loop()
            completion = await loop.run_in_executor(
                None, 
                lambda: self.client.chat.completions.create(**completion_kwargs)
            )
            
            return completion.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error in Groq completion: {e}")
            raise
    
    async def analyze_and_delegate(self, user_message: str) -> Dict[str, Any]:
        """
        First LLM call: Analyze user message and decide which specialist agent to call
        
        Args:
            user_message: User's input message
            
        Returns:
            Dictionary with agent decision and reasoning
        """
        system_prompt = """
        Analisis pesan user dan tentukan agen yang tepat:

        Pilihan agen:
        - "music": untuk rekomendasi musik/lagu berdasarkan mood
        - "entertainment": untuk hiburan/meme/film/jokes/konten lucu  
        - "relaxation": untuk relaksasi/tempat tenang/tempat jalan-jalan/lokasi rekreasi/maps/tempat wisata
        - "reflection": untuk curhat/refleksi/dukungan emosional

        Contoh keyword yang mengarah ke relaxation:
        - "tempat jalan jalan", "rekomendasi tempat", "mau ke mana", "tempat wisata"
        - "tempat tenang", "tempat santai", "lokasi relaksasi", "tempat bagus"
        - "stress butuh jalan", "pengen keluar", "mau refreshing"

        PENTING untuk relaxation agent:
        - Jika ada nama kota/daerah (Jakarta, Bandung, Surabaya, Yogyakarta, Bali), gunakan itu sebagai location
        - Jika tidak ada nama kota spesifik, gunakan "Jakarta" sebagai default location
        - Jangan gunakan kata "outdoor", "indoor", "cafe", "mall" sebagai location

        Response JSON:
        {
            "agent": "nama_agen",
            "mood": "mood_user",
            "parameters": {
                "location": "nama_kota_atau_Jakarta_jika_tidak_ada",
                "place_type": "outdoor/indoor/mixed", 
                "intensity": "low/medium/high"
            },
            "reasoning": "alasan_singkat"
        }
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        response = await self.chat_completion(
            messages=messages,
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse delegation response: {response}")
            # Fallback to reflection agent if parsing fails
            return {
                "agent": "reflection",
                "mood": "confused",
                "parameters": {},
                "reasoning": "Fallback to reflection due to parsing error"
            }
    
    async def personalize_response(
        self, 
        user_message: str, 
        specialist_data: Dict[str, Any],
        agent_type: str
    ) -> str:
        """
        Second LLM call: Convert specialist data into personalized conversation
        
        Args:
            user_message: Original user message
            specialist_data: JSON data from specialist agent
            agent_type: Type of specialist agent that provided the data
            
        Returns:
            Personalized conversational response
        """
        system_prompt = f"""
        Kamu adalah asisten Hati yang ramah dan empatik. 

        User berkata: "{user_message}"
        Agent yang digunakan: {agent_type}
        Data yang kamu dapat: {json.dumps(specialist_data, indent=2)}

        Buatlah respons yang:
        - Hangat dan mendukung sesuai mood user
        - Jika ada musik dari music agent, JANGAN sebutkan detail lagu atau link - biarkan frontend yang tampilkan sebagai music cards
        - Jika ada tempat dari relaxation agent, JANGAN sebutkan detail tempat - biarkan frontend yang tampilkan sebagai place cards
        - Jika ada movies/GIFs dari entertainment agent, JANGAN sebutkan detail konten - biarkan frontend yang tampilkan sebagai content cards
        - Singkat dan natural (maksimal 2-3 kalimat)
        - Pakai bahasa Indonesia yang natural
        - Fokus pada empati dan dukungan, bukan detail konten

        Khusus untuk rekomendasi musik:
        - Cukup bilang "Aku punya rekomendasi musik yang tepat untuk mood kamu!"
        - Jangan sebutkan judul lagu atau artis - akan ditampilkan sebagai cards
        - Berikan motivasi singkat kenapa musik bagus untuk mood mereka

        Khusus untuk rekomendasi tempat:
        - Cukup bilang "Aku punya rekomendasi tempat bagus di [kota]!" 
        - Jangan sebutkan nama tempat spesifik - akan ditampilkan sebagai cards
        - Berikan motivasi singkat kenapa jalan-jalan bagus untuk mood mereka

        Khusus untuk hiburan (movies/GIFs):
        - Cukup bilang "Aku punya rekomendasi film/hiburan yang cocok untuk mood kamu!"
        - Jangan sebutkan judul film atau detail - akan ditampilkan sebagai cards
        - Berikan motivasi singkat kenapa hiburan bagus untuk mood mereka

        Contoh musik: "Aku punya rekomendasi musik yang sempurna untuk menghibur hatimu! Musik memang punya kekuatan luar biasa untuk memperbaiki mood."
        Contoh tempat: "Aku punya rekomendasi tempat bagus di Bandung! Jalan-jalan bisa bantu menghilangkan stres dan bikin pikiran lebih fresh."
        Contoh hiburan: "Aku punya rekomendasi film yang pas banget untuk mood kamu! Menonton sesuatu yang bagus bisa jadi pelarian yang menyenangkan."
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Personalisasikan data ini untuk respons ke pengguna: {json.dumps(specialist_data)}"}
        ]
        
        response = await self.chat_completion(
            messages=messages,
            temperature=0.8,
            max_tokens=500
        )
        
        return response

# Global Groq client instance
groq_client = GroqClient()
