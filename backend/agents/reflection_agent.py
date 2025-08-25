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
    
    async def process(self, user_message: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process reflection conversation request
        
        Returns:
            {
                "reflection": {
                    "insights": [...],
                    "questions": [...],
                    "suggestions": [...]
                },
                "conversation_type": "deep/casual/guided",
                "emotional_context": "detected emotions",
                "follow_up_prompts": [...]
            }
        """
        try:
            mood = parameters.get("mood", "contemplative")
            conversation_type = parameters.get("type", "deep")
            topic = parameters.get("topic", "general")
            
            self.log_activity(f"Starting reflection conversation: {conversation_type}, mood: {mood}")
            
            # Generate reflection insights
            insights = await self._generate_insights(user_message, mood, topic)
            
            # Generate thoughtful questions
            questions = await self._generate_reflection_questions(user_message, mood)
            
            # Provide suggestions for further reflection
            suggestions = await self._generate_suggestions(mood, topic)
            
            # Create follow-up prompts
            follow_ups = await self._generate_follow_up_prompts(user_message, mood)
            
            return {
                "reflection": {
                    "insights": insights,
                    "questions": questions,
                    "suggestions": suggestions
                },
                "conversation_type": conversation_type,
                "emotional_context": mood,
                "follow_up_prompts": follow_ups,
                "session_context": {
                    "topic": topic,
                    "mood": mood,
                    "message_length": len(user_message),
                    "reflection_depth": conversation_type
                }
            }
            
        except Exception as e:
            self.log_activity(f"Error processing reflection request: {e}", "ERROR")
            return self._fallback_response(user_message)
    
    async def _generate_insights(self, user_message: str, mood: str, topic: str) -> List[str]:
        """Generate thoughtful insights based on user's message"""
        system_prompt = f"""
        Kamu adalah seorang counselor yang bijaksana dan empatik. Berikan insights yang mendalam dan bermakna berdasarkan pesan pengguna.
        
        Mood yang terdeteksi: {mood}
        Topik: {topic}
        
        Tugas kamu:
        1. Identifikasi tema-tema emosional dalam pesan
        2. Berikan perspektif yang membangun dan mendukung
        3. Bantu pengguna melihat situasi dari sudut pandang yang berbeda
        4. Berikan validasi emosional yang tepat
        
        Berikan 2-3 insights dalam format JSON array dengan struktur:
        ["insight 1", "insight 2", "insight 3"]
        
        Gaya bicara: Hangat, mendukung, tidak menggurui, menggunakan bahasa Indonesia yang natural.
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Pesan dari pengguna: {user_message}"}
        ]
        
        try:
            response = await groq_client.chat_completion(
                messages=messages,
                temperature=0.7,
                max_tokens=300,
                response_format={"type": "json_object"}
            )
            
            import json
            insights_data = json.loads(response)
            return insights_data.get("insights", [
                "Setiap perasaan yang kamu rasakan itu valid dan penting",
                "Kadang kita perlu mengambil jarak sejenak untuk melihat situasi dengan lebih jelas",
                "Kamu sudah menunjukkan keberanian dengan merefleksikan perasaanmu"
            ])
            
        except Exception as e:
            self.log_activity(f"Error generating insights: {e}", "ERROR")
            return [
                "Terima kasih sudah mau berbagi perasaanmu - itu langkah yang berani",
                "Setiap pengalaman mengajarkan kita sesuatu tentang diri kita sendiri",
                "Kamu tidak sendirian dalam menghadapi perasaan ini"
            ]
    
    async def _generate_reflection_questions(self, user_message: str, mood: str) -> List[str]:
        """Generate thoughtful questions to encourage deeper reflection"""
        questions_by_mood = {
            "sad": [
                "Apa yang paling kamu butuhkan saat ini untuk merasa lebih baik?",
                "Kalau kamu bicara dengan sahabat yang mengalami hal yang sama, apa yang akan kamu katakan?",
                "Adakah hal kecil yang masih bisa kamu syukuri hari ini?"
            ],
            "anxious": [
                "Dari semua kekhawatiran ini, mana yang benar-benar bisa kamu kontrol?",
                "Kalau skenario terburuk benar-benar terjadi, apa yang akan kamu lakukan?",
                "Apa yang akan kamu katakan pada dirimu sendiri 5 tahun yang lalu tentang situasi ini?"
            ],
            "angry": [
                "Apa yang sebenarnya tersembunyi di balik rasa marah ini?",
                "Bagaimana cara mengekspresikan perasaan ini dengan lebih konstruktif?",
                "Apa yang kamu harapkan dari situasi atau orang yang membuatmu marah?"
            ],
            "confused": [
                "Kalau kamu harus menjelaskan situasi ini ke anak kecil, bagaimana kamu akan menyederhanakannya?",
                "Apa nilai-nilai yang paling penting bagimu dalam mengambil keputusan ini?",
                "Bagaimana perasaanmu tentang setiap pilihan yang tersedia?"
            ],
            "grateful": [
                "Siapa atau apa yang paling berperan dalam membuat kamu merasa bersyukur?",
                "Bagaimana cara kamu bisa berbagi kebersyukuran ini dengan orang lain?",
                "Apa yang bisa kamu lakukan untuk mempertahankan perasaan positif ini?"
            ],
            "lonely": [
                "Kapan terakhir kali kamu merasa benar-benar terhubung dengan seseorang?",
                "Apa yang membuat seseorang menjadi 'rumah' bagi perasaanmu?",
                "Bagaimana cara kamu bisa lebih terbuka untuk menerima dukungan dari orang lain?"
            ],
            "default": [
                "Apa yang paling ingin kamu ubah dari situasi saat ini?",
                "Bagaimana perasaanmu tentang dirimu sendiri dalam menghadapi ini?",
                "Apa yang kamu pelajari tentang dirimu dari pengalaman ini?"
            ]
        }
        
        return questions_by_mood.get(mood.lower(), questions_by_mood["default"])
    
    async def _generate_suggestions(self, mood: str, topic: str) -> List[Dict[str, str]]:
        """Generate actionable suggestions for self-reflection"""
        suggestions = {
            "journaling": {
                "title": "Menulis Jurnal Perasaan",
                "description": "Tulis 3 hal yang kamu rasakan hari ini dan mengapa",
                "time_needed": "10-15 menit",
                "benefits": "Membantu mengorganisir pikiran dan perasaan"
            },
            "meditation": {
                "title": "Meditasi Mindfulness",
                "description": "Duduk tenang dan amati perasaanmu tanpa menilai",
                "time_needed": "5-10 menit",
                "benefits": "Meningkatkan kesadaran diri dan ketenangan"
            },
            "letter_writing": {
                "title": "Menulis Surat untuk Diri Sendiri",
                "description": "Tulis surat untuk dirimu sendiri dari perspektif sahabat terbaik",
                "time_needed": "15-20 menit",
                "benefits": "Mengembangkan self-compassion dan perspektif baru"
            },
            "gratitude": {
                "title": "Praktik Syukur",
                "description": "Tuliskan 5 hal yang kamu syukuri hari ini, sekecil apapun",
                "time_needed": "5 menit",
                "benefits": "Menggeser fokus ke hal-hal positif"
            },
            "body_scan": {
                "title": "Body Scan Meditation",
                "description": "Perhatikan sensasi di setiap bagian tubuh dari kepala ke kaki",
                "time_needed": "10-15 menit",
                "benefits": "Menghubungkan pikiran dan tubuh"
            }
        }
        
        # Select appropriate suggestions based on mood
        mood_suggestions = {
            "sad": ["journaling", "gratitude", "letter_writing"],
            "anxious": ["meditation", "body_scan", "journaling"],
            "angry": ["body_scan", "letter_writing", "meditation"],
            "confused": ["journaling", "meditation", "letter_writing"],
            "grateful": ["gratitude", "journaling", "letter_writing"],
            "lonely": ["letter_writing", "gratitude", "journaling"]
        }
        
        selected_keys = mood_suggestions.get(mood.lower(), ["journaling", "meditation", "gratitude"])
        return [suggestions[key] for key in selected_keys[:3]]
    
    async def _generate_follow_up_prompts(self, user_message: str, mood: str) -> List[str]:
        """Generate prompts to continue the conversation"""
        prompts = [
            "Ceritakan lebih lanjut tentang perasaan ini...",
            "Apa yang paling sulit dari situasi ini?",
            "Bagaimana kamu biasanya menghadapi perasaan seperti ini?",
            "Adakah seseorang yang bisa kamu ajak bicara tentang hal ini?",
            "Apa yang kamu harapkan setelah berbagi perasaan ini?"
        ]
        
        mood_specific_prompts = {
            "sad": [
                "Apa yang biasanya membuatmu merasa lebih baik?",
                "Kapan terakhir kali kamu merasa bahagia? Apa yang membuatmu merasa seperti itu?"
            ],
            "anxious": [
                "Apa skenario terbaik yang mungkin terjadi?",
                "Bagaimana cara kamu menenangkan diri saat cemas menyerang?"
            ],
            "angry": [
                "Apa yang kamu inginkan dari orang atau situasi yang membuatmu marah?",
                "Bagaimana cara kamu mengekspresikan marah dengan sehat?"
            ]
        }
        
        specific_prompts = mood_specific_prompts.get(mood.lower(), [])
        return (specific_prompts + prompts)[:3]
    
    def _fallback_response(self, user_message: str) -> Dict[str, Any]:
        """Fallback response when reflection generation fails"""
        return {
            "reflection": {
                "insights": [
                    "Terima kasih sudah mau berbagi perasaanmu dengan aku",
                    "Setiap perasaan yang kamu rasakan itu valid dan penting",
                    "Kamu tidak sendirian dalam perjalanan ini"
                ],
                "questions": [
                    "Apa yang paling kamu butuhkan saat ini?",
                    "Bagaimana perasaanmu setelah berbagi hal ini?",
                    "Apa satu hal kecil yang bisa kamu lakukan untuk dirimu sendiri hari ini?"
                ],
                "suggestions": [
                    {
                        "title": "Bernapas Dengan Sadar",
                        "description": "Ambil napas dalam-dalam dan rasakan sensasinya",
                        "time_needed": "2 menit",
                        "benefits": "Grounding dan menenangkan"
                    }
                ]
            },
            "conversation_type": "supportive",
            "emotional_context": "general",
            "follow_up_prompts": [
                "Ceritakan lebih lanjut jika kamu mau..."
            ],
            "error": "Reflection generation fallback"
        }
