"""
Entertainment Agent - Specialist for entertainment content using Giphy and TMDb APIs
"""

import httpx
from typing import Dict, Any, List
import sys
import os

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from backend.core.base_agent import BaseAgent
from config.settings import settings

class EntertainmentAgent(BaseAgent):
    """Agent for entertainment content recommendations"""
    
    def __init__(self):
        super().__init__("entertainment")
        self.giphy_api_key = settings.giphy_api_key
        self.tmdb_api_key = settings.tmdb_api_key
        self.giphy_base_url = "https://api.giphy.com/v1/gifs"
        self.tmdb_base_url = "https://api.themoviedb.org/3"
    
    async def process(self, user_message: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process entertainment recommendation request
        
        Returns:
            {
                "content": {
                    "gifs": [...],
                    "movies": [...],
                    "jokes": [...]
                },
                "mood_analysis": "detected mood",
                "content_type": "mixed/gifs/movies",
                "total_items": int
            }
        """
        try:
            mood = parameters.get("mood", "neutral")
            content_type = parameters.get("type", "mixed")
            intensity = parameters.get("intensity", "medium")
            
            self.log_activity(f"Finding entertainment for mood: {mood}, type: {content_type}")
            
            content = {}
            total_items = 0
            
            # Get GIFs based on mood
            if content_type in ["mixed", "gifs"]:
                gifs = await self._get_mood_gifs(mood, intensity)
                content["gifs"] = gifs
                total_items += len(gifs)
            
            # Get movie/TV recommendations
            if content_type in ["mixed", "movies"]:
                movies = await self._get_mood_movies(mood, intensity)
                content["movies"] = movies
                total_items += len(movies)
            
            # Generate mood-appropriate jokes/quotes
            if content_type in ["mixed", "jokes"]:
                jokes = await self._get_mood_jokes(mood)
                content["jokes"] = jokes
                total_items += len(jokes)
            
            return_data = {
                "content": content,
                "mood_analysis": mood,
                "content_type": content_type,
                "total_items": total_items,
                "search_parameters": {
                    "mood": mood,
                    "type": content_type,
                    "intensity": intensity
                }
            }
            
            self.log_activity(f"Returning entertainment data: {len(content.get('movies', []))} movies, {len(content.get('gifs', []))} gifs")
            return return_data
            
        except Exception as e:
            self.log_activity(f"Error processing entertainment request: {e}", "ERROR")
            return self._fallback_response(user_message)
    
    async def _get_mood_gifs(self, mood: str, intensity: str, limit: int = 5) -> List[Dict]:
        """Get GIFs based on mood from Giphy API with randomization"""
        try:
            # Map mood to search terms
            mood_terms = self._mood_to_gif_terms(mood, intensity)
            
            # Add randomness to search term selection
            import random
            search_term = random.choice(mood_terms) if mood_terms else "happy"
            
            # Add random offset to get different results each time
            # Giphy search returns up to 50 results per page, we'll randomize offset
            random_offset = random.randint(0, 45)  # Keep within reasonable range
            
            self.log_activity(f"Searching GIFs for mood '{mood}' with term '{search_term}' and offset {random_offset}")
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.giphy_base_url}/search",
                    params={
                        "api_key": self.giphy_api_key,
                        "q": search_term,
                        "limit": limit * 2,  # Get more results to pick randomly from
                        "offset": random_offset,
                        "rating": "g",  # Family-friendly content
                        "lang": "en"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    all_gifs = data.get("data", [])
                    
                    self.log_activity(f"Giphy returned {len(all_gifs)} GIFs for term '{search_term}'")
                    
                    # Randomly shuffle and select from results
                    if all_gifs:
                        random.shuffle(all_gifs)
                        selected_gifs = all_gifs[:limit]
                    else:
                        selected_gifs = []
                    
                    gifs = []
                    for gif in selected_gifs:
                        gif_data = {
                            "title": gif.get("title", "Fun GIF"),
                            "url": gif["images"]["original"]["url"],
                            "preview_url": gif["images"]["fixed_height_small"]["url"],
                            "source": "giphy",
                            "rating": gif.get("rating", "g"),
                            "search_term": search_term,
                            "mood": mood
                        }
                        gifs.append(gif_data)
                        self.log_activity(f"Added GIF: {gif.get('title', 'Untitled')} for mood '{mood}'")
                    
                    return gifs
                else:
                    self.log_activity(f"Giphy API error: {response.status_code} - {response.text}", "ERROR")
                    return []
                    
        except Exception as e:
            self.log_activity(f"Error fetching GIFs: {e}", "ERROR")
            # Return empty list instead of failing completely
            return []
    
    async def _get_mood_movies(self, mood: str, intensity: str, limit: int = 3) -> List[Dict]:
        """Get movie recommendations based on mood from TMDb API"""
        try:
            # Map mood to genre IDs (TMDb genre IDs)
            genre_id = self._mood_to_movie_genre(mood)
            
            # Add variety by using different sorting methods based on mood
            sort_options = [
                "popularity.desc",
                "vote_average.desc", 
                "release_date.desc",
                "revenue.desc"
            ]
            
            # Use mood to determine sorting preference
            if mood in ["excited", "energetic"]:
                sort_by = "popularity.desc"
            elif mood in ["thoughtful", "sad"]:
                sort_by = "vote_average.desc"
            elif mood in ["happy", "relaxed"]:
                sort_by = "release_date.desc"
            else:
                import random
                sort_by = random.choice(sort_options)
            
            # Random page to get different results
            import random
            page = random.randint(1, 3)  # Get from first 3 pages for variety
            
            self.log_activity(f"Searching movies for mood '{mood}' with genre {genre_id}, sort: {sort_by}, page: {page}")
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.tmdb_base_url}/discover/movie",
                    params={
                        "api_key": self.tmdb_api_key,
                        "with_genres": genre_id,
                        "sort_by": sort_by,
                        "vote_average.gte": 6.0,  # Good ratings only
                        "page": page,
                        "language": "en-US",
                        "vote_count.gte": 100  # Ensure movies have enough votes
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    movies = []
                    
                    self.log_activity(f"TMDb returned {len(data.get('results', []))} movies for genre {genre_id}")
                    
                    for movie in data.get("results", [])[:limit]:
                        movie_data = {
                            "title": movie.get("title"),
                            "overview": movie.get("overview")[:150] + "...",
                            "rating": movie.get("vote_average"),
                            "release_date": movie.get("release_date"),
                            "poster_url": f"https://image.tmdb.org/t/p/w500{movie.get('poster_path')}" if movie.get('poster_path') else None,
                            "genre_id": genre_id,
                            "mood": mood,
                            "source": "tmdb"
                        }
                        movies.append(movie_data)
                        self.log_activity(f"Added movie: {movie.get('title')} (rating: {movie.get('vote_average')})")
                    
                    return movies
                else:
                    self.log_activity(f"TMDb API error: {response.status_code} - {response.text}", "ERROR")
                    return []
                    
        except Exception as e:
            self.log_activity(f"Error fetching movies: {e}", "ERROR")
            return []
    
    async def _get_mood_jokes(self, mood: str) -> List[Dict]:
        """Generate mood-appropriate jokes or inspirational quotes"""
        mood_jokes = {
            "sad": [
                "Kenapa ikan nggak pernah sedih? Soalnya dia selalu swimming in the good vibes! 🐠",
                "Hari yang buruk bukan berarti hidup yang buruk. Besok adalah halaman baru! 📖"
            ],
            "happy": [
                "Kenapa senyum itu gratis? Karena kebahagiaan nggak boleh dikenakan pajak! 😄",
                "Hari ini adalah hari yang sempurna untuk bahagia! ✨"
            ],
            "angry": [
                "Marah itu kayak memegang bara api untuk dilempar ke orang lain - yang kepanasan duluan kita sendiri 🔥",
                "Take a deep breath... Sekarang hitung sampai 10... Masih marah? Hitung lagi! 😅"
            ],
            "stressed": [
                "Kenapa komputer nggak pernah stress? Soalnya dia bisa di-restart! Kita juga bisa kok 💻",
                "Stress itu kayak rocking chair - banyak gerakan tapi nggak kemana-mana 🪑"
            ],
            "default": [
                "Hidup itu seperti kopi - bisa pahit, tapi bisa juga dibuat manis sesuai selera! ☕",
                "Senyum adalah makeup terbaik yang bisa kamu pakai hari ini! 😊"
            ]
        }
        
        jokes = mood_jokes.get(mood.lower(), mood_jokes["default"])
        return [{"text": joke, "type": "joke"} for joke in jokes]
    
    def _mood_to_gif_terms(self, mood: str, intensity: str) -> List[str]:
        """Map mood to GIF search terms with variety"""
        mood_terms = {
            "happy": ["happy", "celebration", "joy", "dance", "smile", "cheerful", "excited", "yay"],
            "sad": ["comfort", "hug", "cute animals", "support", "cheer up", "better days", "hope", "love"],
            "angry": ["calm down", "chill", "relax", "meditation", "breathe", "peace", "zen", "cool down"],
            "excited": ["excited", "party", "celebration", "wow", "amazing", "awesome", "yes", "victory"],
            "tired": ["coffee", "sleep", "rest", "cozy", "nap", "energy", "tired", "yawn"],
            "stressed": ["relax", "meditation", "calm", "peace", "stress relief", "breathe", "zen", "chill"],
            "lonely": ["friendship", "love", "support", "care", "together", "friends", "hug", "connection"],
            "confused": ["thinking", "question", "hmm", "wonder", "confused", "what", "mind blown", "puzzled"],
            "grateful": ["thank you", "grateful", "appreciation", "love", "blessed", "thankful", "heart", "gratitude"],
            "motivated": ["motivation", "success", "goal", "achievement", "you can do it", "strong", "power", "determination"],
            "bored": ["fun", "entertainment", "interesting", "surprise", "random", "cool", "weird", "funny"],
            "anxious": ["calm", "relax", "peace", "breathe", "anxiety relief", "comfort", "safe", "okay"],
            "romantic": ["love", "romance", "heart", "cute couple", "sweet", "kiss", "adorable", "valentine"],
            "nostalgic": ["memories", "nostalgia", "old times", "vintage", "classic", "throwback", "remember", "past"],
            "energetic": ["energy", "active", "sports", "workout", "dynamic", "power", "strong", "go"],
            "thoughtful": ["thinking", "deep", "philosophical", "wisdom", "contemplation", "reflection", "mind", "idea"],
            "playful": ["play", "fun", "silly", "games", "laugh", "humor", "joke", "entertaining"],
            "neutral": ["good vibes", "positive", "nice", "pleasant", "okay", "fine", "alright", "normal"]
        }
        
        # Get terms for the mood, fallback to neutral if mood not found
        terms = mood_terms.get(mood.lower(), mood_terms["neutral"])
        
        # Add intensity-based modifications
        if intensity == "high":
            # For high intensity, prefer more energetic terms
            energetic_terms = ["very " + term for term in terms[:3]]
            terms = energetic_terms + terms
        elif intensity == "low":
            # For low intensity, prefer calmer terms
            calm_terms = ["gentle " + term for term in terms[:3]]
            terms = calm_terms + terms
        
        self.log_activity(f"Available GIF terms for mood '{mood}' (intensity: {intensity}): {terms}")
        return terms
    
    def _mood_to_movie_genre(self, mood: str) -> str:
        """Map mood to TMDb genre ID with some variety"""
        # TMDb Genre IDs - now with multiple options per mood
        mood_genres = {
            "happy": ["35", "16", "10751"],     # Comedy, Animation, Family
            "sad": ["18", "10749"],             # Drama, Romance
            "excited": ["28", "12", "878"],     # Action, Adventure, Sci-Fi
            "romantic": ["10749", "35"],        # Romance, Comedy
            "scared": ["27", "53"],             # Horror, Thriller
            "adventurous": ["12", "28", "14"],  # Adventure, Action, Fantasy
            "thoughtful": ["18", "99", "36"],   # Drama, Documentary, History
            "nostalgic": ["36", "10402", "18"], # History, Music, Drama
            "energetic": ["28", "80", "9648"],  # Action, Crime, Mystery
            "relaxed": ["35", "10770"],         # Comedy, TV Movie
            "bored": ["28", "12", "878"],       # Action, Adventure, Sci-Fi
            "anxious": ["35", "16"],            # Comedy, Animation
            "angry": ["28", "80"],              # Action, Crime
            "neutral": ["35", "18", "28"]       # Comedy, Drama, Action
        }
        
        # Get genres for the mood, fallback to happy if mood not found
        genres = mood_genres.get(mood.lower(), mood_genres["happy"])
        
        # Add some randomness to avoid same results
        import random
        selected_genre = random.choice(genres)
        
        self.log_activity(f"Selected genre {selected_genre} for mood '{mood}' from options {genres}")
        return selected_genre
    
    def _fallback_response(self, user_message: str) -> Dict[str, Any]:
        """Fallback response when APIs are not available"""
        return {
            "content": {
                "jokes": [
                    {
                        "text": "Maaf, koneksi hiburan sedang gangguan, tapi senyuman kamu tetap gratis! 😊",
                        "type": "fallback"
                    }
                ]
            },
            "mood_analysis": "general",
            "content_type": "fallback",
            "total_items": 1,
            "error": "Entertainment APIs not available"
        }
