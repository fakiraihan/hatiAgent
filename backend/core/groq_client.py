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
        Analisis pesan user dan tentukan agen yang tepat dengan SANGAT KETAT:

        Pilihan agen:
        - "music": HANYA jika user EKSPLISIT minta musik/lagu ("cariin musik", "minta lagu", "play musik")
        - "entertainment": HANYA jika user EKSPLISIT minta hiburan konten ("kasih jokes", "cariin meme", "recommend film", "mau nonton movie", "show me funny gifs")
        - "relaxation": HANYA jika user EKSPLISIT minta tempat/lokasi ("mau jalan-jalan", "rekomendasi tempat", "cari lokasi", "tempat wisata di...")
        - "reflection": DEFAULT untuk semua percakapan, curhat, tanya-tanya, diskusi topik apapun

        SUPER PENTING - JANGAN SALAH DELEGASI:
        ❌ "selingkuh", "balas dendam", "hubungan" = INI BUKAN entertainment, ini reflection!
        ❌ "mantap", "bisaaa", "gimana kalau" = INI BUKAN entertainment, ini reflection!
        ❌ Ngobrol biasa, sharing cerita, tanya pendapat = reflection
        ❌ Diskusi topik emosional/personal = reflection

        ✅ Entertainment HANYA jika ada kata kunci EKSPLISIT:
        - "kasih aku jokes", "mau ketawa", "cariin meme lucu"
        - "recommend film", "mau nonton", "suggest movie"
        - "show me gifs", "animated funny"

        ✅ Music HANYA jika ada kata kunci EKSPLISIT:
        - "cariin musik", "minta lagu", "play song", "music recommendation"

        ✅ Relaxation HANYA jika ada kata kunci EKSPLISIT:
        - "tempat jalan-jalan", "mau ke mana", "lokasi wisata", "recommend place"

        PENTING untuk entertainment agent (jika benar-benar dipanggil):
        - Jika user minta "jokes", "lucu", "meme", "humor", set type="jokes"
        - Jika user minta "film", "movie", "bioskop", set type="movies"  
        - Jika user minta "gif", "animated", set type="gifs"
        - Jika tidak spesifik, set type="mixed"

        PENTING untuk relaxation agent (jika benar-benar dipanggil):
        - Jika ada nama kota/daerah (Jakarta, Bandung, Surabaya, Yogyakarta, Bali), gunakan itu sebagai location
        - Jika tidak ada nama kota spesifik, gunakan "Jakarta" sebagai default location

        DALAM KERAGUAN, SELALU PILIH "reflection"!

        Response JSON:
        {
            "agent": "nama_agen",
            "mood": "mood_user",
            "parameters": {
                "location": "nama_kota_atau_Jakarta_jika_tidak_ada",
                "place_type": "outdoor/indoor/mixed", 
                "type": "jokes/movies/gifs/mixed",
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

        ATURAN BERDASARKAN AGENT TYPE:

        REFLECTION AGENT:
        - HANYA gunakan data main_response dari reflection agent
        - JANGAN tambahkan rekomendasi musik/hiburan/tempat
        - Fokus pada percakapan empati yang natural
        - Response sebagai teman yang mendengarkan

        MUSIC AGENT:
        - Boleh menyebutkan ada rekomendasi musik
        - Cukup bilang "Aku punya rekomendasi musik yang tepat untuk mood kamu!"
        - JANGAN sebutkan detail lagu - biarkan frontend tampilkan sebagai cards

        ENTERTAINMENT AGENT:
        - Boleh menyebutkan ada rekomendasi hiburan
        - Cukup bilang "Aku punya rekomendasi hiburan yang cocok!"
        - JANGAN sebutkan detail konten - biarkan frontend tampilkan sebagai cards

        RELAXATION AGENT:
        - Boleh menyebutkan ada rekomendasi tempat
        - Cukup bilang "Aku punya rekomendasi tempat bagus!"
        - JANGAN sebutkan detail tempat - biarkan frontend tampilkan sebagai cards

        Buatlah respons yang:
        - Hangat dan mendukung sesuai mood user
        - Singkat dan natural (maksimal 2-3 kalimat)
        - Pakai bahasa Indonesia yang natural
        - Fokus pada empati dan dukungan

        PENTING: Untuk reflection agent, JANGAN tambahkan rekomendasi apa pun yang tidak ada dalam data specialist!
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
