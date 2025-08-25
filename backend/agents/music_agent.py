"""
Music Agent - Specialist for mood-based music recommendations using Spotify API
"""

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from typing import Dict, Any, List
import sys
import os

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from backend.core.memory_agent import MemoryAgent
from backend.agents.music.ambient_urls import AMBIENT_MUSIC_URLS
from config.settings import settings

class MusicAgent(MemoryAgent):
    """Agent for music recommendations based on mood"""
    
    def __init__(self):
        super().__init__("music")
        self.setup_spotify()
    
    def setup_spotify(self):
        """Initialize Spotify client"""
        try:
            client_credentials_manager = SpotifyClientCredentials(
                client_id=settings.spotify_client_id,
                client_secret=settings.spotify_client_secret
            )
            self.spotify = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
            self.log_activity("Spotify client initialized successfully")
        except Exception as e:
            self.log_activity(f"Failed to initialize Spotify client: {e}", "ERROR")
            self.spotify = None
    
    async def process(self, user_message: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process music recommendation request with memory and caching
        Support untuk band-specific recommendations dan general mood-based
        
        Returns:
            {
                "recommendations": [...],
                "mood_analysis": "detected mood",
                "genre": "recommended genre", 
                "total_found": int,
                "personalized": bool,
                "artist_requested": str (jika ada band specific)
            }
        """
        try:
            if not self.spotify:
                return self._fallback_response(user_message)
            
            # Get session ID for personalization
            session_id = parameters.get("session_id", "default")
            
            # Check if user mentioned specific artist/band
            mentioned_artist = await self._extract_artist_from_message(user_message)
            
            if mentioned_artist:
                # Handle artist-specific recommendations
                return await self._get_artist_based_recommendations(mentioned_artist, user_message, parameters, session_id)
            else:
                # Handle general mood-based recommendations
                return await self._get_mood_based_recommendations(user_message, parameters, session_id)
                
        except Exception as e:
            self.log_activity(f"Error processing music request: {e}", "ERROR")
            return self._fallback_response(user_message)

    async def _extract_artist_from_message(self, message: str) -> str:
        """Extract artist/band name from user message using LLM"""
        try:
            system_prompt = """
            Ekstrak nama artis/band dari pesan user. Jika tidak ada nama artis yang disebutkan, return null.
            
            ATURAN:
            - Hanya ekstrak nama artis/penyanyi/band yang jelas disebutkan
            - Jangan ekstrak kata-kata seperti "lagu", "musik", "sedih", "happy", dll
            - Jika user hanya minta rekomendasi tanpa sebutkan artis, return null
            - Return nama artis persis seperti yang disebutkan user
            
            Contoh:
            - "lagu pamungkas dong" → "pamungkas"
            - "kaya lagu noah gitu" → "noah" 
            - "pengen denger taylor swift" → "taylor swift"
            - "lagu sedih dong" → null
            - "kasih rekomendasi musik" → null
            
            Response dalam format JSON:
            {"artist": "nama_artis_atau_null"}
            """
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Pesan: {message}"}
            ]
            
            # Import groq_client
            from backend.core.groq_client import groq_client
            
            response = await groq_client.chat_completion(
                messages=messages,
                temperature=0.3,
                max_tokens=100,
                response_format={"type": "json_object"}
            )
            
            import json
            result = json.loads(response)
            artist = result.get("artist")
            
            # Return None if artist is null or empty
            if artist and artist.lower() not in ["null", "none", ""]:
                self.log_activity(f"LLM extracted artist: '{artist}' from message: '{message[:50]}...'")
                return artist.strip()
            else:
                return None
                
        except Exception as e:
            self.log_activity(f"Error in LLM artist extraction: {e}", "ERROR")
            # Fallback to simple keyword matching
            return self._fallback_artist_extraction(message)
    
    def _fallback_artist_extraction(self, message: str) -> str:
        """Fallback artist extraction using simple keyword matching"""
        # Known popular artists for fallback
        known_artists = [
            "pamungkas", "noah", "sheila on 7", "tulus", "hindia", "raisa", "afgan",
            "feast", "ungu", "d'masiv", "peterpan", "nidji", "gigi", "slank",
            "coldplay", "taylor swift", "ed sheeran", "bruno mars", "maroon 5"
        ]
        
        clean_message = message.lower()
        for artist in known_artists:
            if artist in clean_message:
                return artist
        
        return None

    async def _get_artist_based_recommendations(self, artist_name: str, user_message: str, parameters: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Get recommendations based on specific artist"""
        try:
            self.log_activity(f"Searching for artist-based recommendations: {artist_name}")
            
            # Search for the artist
            results = self.spotify.search(q=f"artist:{artist_name}", type="artist", limit=1)
            
            if not results["artists"]["items"]:
                # Fallback to general search
                self.log_activity(f"Artist '{artist_name}' not found, falling back to general search")
                return await self._get_mood_based_recommendations(user_message, parameters, session_id)
            
            artist = results["artists"]["items"][0]
            artist_id = artist["id"]
            
            # Get artist's top tracks
            top_tracks = self.spotify.artist_top_tracks(artist_id, country='ID')["tracks"]
            
            # Get related artists for variety (with error handling)
            related_tracks = []
            try:
                related_artists = self.spotify.artist_related_artists(artist_id)["artists"][:3]
                
                # Get some tracks from related artists
                for related_artist in related_artists:
                    try:
                        related_top = self.spotify.artist_top_tracks(related_artist["id"], country='ID')["tracks"][:2]
                        related_tracks.extend(related_top)
                    except Exception as e:
                        self.log_activity(f"Error getting tracks for related artist {related_artist['name']}: {e}")
                        continue
                        
            except Exception as e:
                self.log_activity(f"Error getting related artists for {artist['name']}: {e}")
                # Continue without related tracks
            
            # Combine tracks (prioritize main artist)
            all_tracks = top_tracks[:8] + related_tracks[:2]
            
            recommendations = []
            for track in all_tracks:
                # Get album cover image
                album_images = track["album"].get("images", [])
                cover_url = None
                if album_images:
                    for img in album_images:
                        if img.get("height") and 200 <= img["height"] <= 400:
                            cover_url = img["url"]
                            break
                    if not cover_url:
                        cover_url = album_images[0]["url"]
                
                recommendation = {
                    "title": track["name"],
                    "artist": ", ".join([artist["name"] for artist in track["artists"]]),
                    "album": track["album"]["name"],
                    "url": track["external_urls"]["spotify"],
                    "preview_url": track.get("preview_url"),
                    "cover_url": cover_url,
                    "release_date": track["album"].get("release_date", ""),
                    "popularity": track.get("popularity", 0),
                    "duration_ms": track.get("duration_ms", 0),
                    "explicit": track.get("explicit", False)
                }
                recommendations.append(recommendation)
            
            # Get artist genres for context
            artist_genres = artist.get("genres", [])
            main_genre = artist_genres[0] if artist_genres else "pop"
            
            mood = parameters.get("mood", "happy")
            
            response = {
                "recommendations": recommendations,
                "mood_analysis": mood,
                "genre": main_genre,
                "total_found": len(recommendations),
                "personalized": True,
                "artist_requested": artist["name"],
                "artist_info": {
                    "name": artist["name"],
                    "genres": artist_genres,
                    "popularity": artist.get("popularity", 0),
                    "followers": artist.get("followers", {}).get("total", 0)
                },
                "search_parameters": {
                    "artist": artist_name,
                    "mood": mood,
                    "type": "artist_based"
                },
                "from_cache": False
            }
            
            return response
            
        except Exception as e:
            self.log_activity(f"Error in artist-based search for '{artist_name}': {e}", "ERROR")
            # Fallback to mood-based recommendations
            return await self._get_mood_based_recommendations(user_message, parameters, session_id)

    async def _get_mood_based_recommendations(self, user_message: str, parameters: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Get general mood-based recommendations (original logic)"""
        try:
            # Extract mood and genre from parameters
            mood = parameters.get("mood", "neutral")
            
            # Get user preferences from memory
            user_preferences = self.get_user_preferences(session_id)
            preferred_genre = user_preferences.get("preferred_genre", {}).get("value")
            
            # Use user's preferred genre if available, otherwise map from mood
            genre = preferred_genre or parameters.get("genre", self._mood_to_genre(mood))
            intensity = parameters.get("intensity", "medium")
            
            # Create cache key for this request
            cache_params = {
                "mood": mood,
                "genre": genre,
                "intensity": intensity,
                "session_preferences": bool(user_preferences)
            }
            cache_key = self.get_cache_key(cache_params)
            
            # Try to get cached response first
            cached_response = self.get_cached_response(cache_key)
            if cached_response:
                self.log_activity(f"Returning cached music recommendations for {mood}")
                cached_response["from_cache"] = True
                return cached_response
            
            self.log_activity(f"Searching music for mood: {mood}, genre: {genre}, preferences: {bool(user_preferences)}")
            
            # Get personalized context for better recommendations
            context = self.get_personalized_context(session_id, mood)
            
            # Search for tracks based on mood and genre
            tracks = await self._search_tracks_by_mood(mood, genre, intensity, context)
            
            recommendations = []
            for track in tracks:
                # Get album cover image (prefer medium size)
                album_images = track["album"].get("images", [])
                cover_url = None
                if album_images:
                    # Try to get medium size image, fallback to first available
                    for img in album_images:
                        if img.get("height") and 200 <= img["height"] <= 400:
                            cover_url = img["url"]
                            break
                    if not cover_url:
                        cover_url = album_images[0]["url"]
                
                recommendation = {
                    "title": track["name"],
                    "artist": ", ".join([artist["name"] for artist in track["artists"]]),
                    "album": track["album"]["name"],
                    "url": track["external_urls"]["spotify"],
                    "preview_url": track.get("preview_url"),
                    "cover_url": cover_url,
                    "release_date": track["album"].get("release_date", ""),
                    "popularity": track.get("popularity", 0),
                    "duration_ms": track.get("duration_ms", 0),
                    "explicit": track.get("explicit", False)
                }
                recommendations.append(recommendation)
            
            response = {
                "recommendations": recommendations,
                "mood_analysis": mood,
                "genre": genre,
                "total_found": len(recommendations),
                "personalized": bool(user_preferences),
                "search_parameters": {
                    "mood": mood,
                    "genre": genre,
                    "intensity": intensity
                },
                "from_cache": False
            }
            
            # Cache the response for 2 hours
            self.cache_response(cache_key, response, ttl_hours=2)
            
            return response
            
        except Exception as e:
            self.log_activity(f"Error in mood-based search: {e}", "ERROR")
            return self._fallback_response(user_message)
    
    async def _search_tracks_by_mood(self, mood: str, genre: str, intensity: str, context: str = "", limit: int = 10) -> List[Dict]:
        """Search for tracks based on mood parameters"""
        try:
            # Map Indonesian mood to English search terms
            mood_english = self._translate_mood_to_english(mood)
            
            # Create search queries based on mood and genre
            search_terms = [
                f"genre:{genre}",  # Use genre prefix for better results
                f"{genre} {intensity}",
                f"{mood_english} {genre}",
                f"{mood_english} music",
                genre
            ]
            
            all_tracks = []
            
            # Try multiple search terms to get better results
            for term in search_terms:
                try:
                    self.log_activity(f"Searching with term: '{term}'")
                    results = self.spotify.search(
                        q=term,
                        type="track",
                        limit=20
                    )
                    
                    tracks = results["tracks"]["items"]
                    
                    # Filter tracks based on popularity and avoid specific Indonesian bands
                    filtered_tracks = [
                        track for track in tracks 
                        if (track.get("popularity", 0) > 15 and  # Lower threshold for more results
                            not self._is_unwanted_artist(track))
                    ]
                    
                    all_tracks.extend(filtered_tracks)
                    
                    if len(all_tracks) >= limit * 2:  # Get more for better filtering
                        break
                        
                except Exception as search_error:
                    self.log_activity(f"Search term '{term}' failed: {search_error}", "WARNING")
                    continue
            
            # Remove duplicates based on track ID
            unique_tracks = []
            seen_ids = set()
            
            for track in all_tracks:
                if track["id"] not in seen_ids:
                    unique_tracks.append(track)
                    seen_ids.add(track["id"])
            
            # Return top results
            return unique_tracks[:limit]
            
        except Exception as e:
            self.log_activity(f"Error searching tracks: {e}", "ERROR")
            return []
    
    def _translate_mood_to_english(self, mood: str) -> str:
        """Translate Indonesian mood to English for better Spotify search"""
        mood_translation = {
            "sedih": "sad",
            "senang": "happy", 
            "bahagia": "happy",
            "gembira": "happy",
            "marah": "angry",
            "tenang": "calm",
            "rileks": "relaxed",
            "energik": "energetic",
            "romantis": "romantic",
            "nostalgia": "nostalgic",
            "fokus": "focused",
            "ceria": "cheerful",
            "melankolis": "melancholic"
        }
        return mood_translation.get(mood.lower(), mood)
    
    def _is_unwanted_artist(self, track: Dict) -> bool:
        """Filter out artists that might be incorrectly matched"""
        unwanted_artists = [
            "netral", "ntrl",  # Indonesian band that gets matched incorrectly
            "neutral",  # Avoid literal "neutral" matches
        ]
        
        for artist in track.get("artists", []):
            artist_name = artist.get("name", "").lower()
            if any(unwanted in artist_name for unwanted in unwanted_artists):
                return True
        return False
    
    def _mood_to_genre(self, mood: str) -> str:
        """Map mood to music genre"""
        mood_genre_map = {
            # Indonesian moods
            "sedih": "indie",
            "senang": "pop", 
            "bahagia": "pop",
            "gembira": "dance",
            "ceria": "pop",
            "marah": "rock",
            "tenang": "ambient",
            "rileks": "chill",
            "energik": "electronic",
            "romantis": "soul",
            "nostalgia": "classic rock",
            "fokus": "instrumental",
            "melankolis": "alternative",
            
            # English moods
            "happy": "pop",
            "sad": "indie",
            "energetic": "electronic", 
            "calm": "ambient",
            "romantic": "soul",
            "angry": "rock",
            "nostalgic": "classic rock",
            "focused": "instrumental",
            "relaxed": "chill",
            "excited": "dance",
            "cheerful": "pop",
            "melancholic": "alternative"
        }
        return mood_genre_map.get(mood.lower(), "pop")
    
    def _mood_to_audio_features(self, mood: str, intensity: str) -> Dict[str, float]:
        """Map mood and intensity to Spotify audio features"""
        base_features = {
            "happy": {"valence": 0.8, "energy": 0.7, "danceability": 0.7},
            "sad": {"valence": 0.2, "energy": 0.3, "danceability": 0.3},
            "energetic": {"valence": 0.7, "energy": 0.9, "danceability": 0.8},
            "calm": {"valence": 0.5, "energy": 0.2, "danceability": 0.3},
            "romantic": {"valence": 0.6, "energy": 0.4, "danceability": 0.5},
            "angry": {"valence": 0.3, "energy": 0.8, "danceability": 0.5},
            "nostalgic": {"valence": 0.4, "energy": 0.5, "danceability": 0.4},
            "focused": {"valence": 0.5, "energy": 0.6, "danceability": 0.2},
            "relaxed": {"valence": 0.6, "energy": 0.3, "danceability": 0.4}
        }
        
        features = base_features.get(mood.lower(), base_features["happy"])
        
        # Adjust for intensity
        if intensity == "high":
            features["energy"] = min(1.0, features["energy"] + 0.2)
            features["danceability"] = min(1.0, features["danceability"] + 0.2)
        elif intensity == "low":
            features["energy"] = max(0.0, features["energy"] - 0.2)
            features["danceability"] = max(0.0, features["danceability"] - 0.2)
        
        return features
    
    def _fallback_response(self, user_message: str) -> Dict[str, Any]:
        """Fallback response when Spotify API is not available"""
        return {
            "recommendations": [
                {
                    "title": "Relaxing Piano Music",
                    "artist": "Peaceful Piano",
                    "album": "Calm & Peaceful",
                    "url": "#",
                    "preview_url": None,
                    "cover_url": "https://via.placeholder.com/300x300/1DB954/FFFFFF?text=🎵",
                    "release_date": "2023",
                    "popularity": 75,
                    "duration_ms": 180000,
                    "explicit": False,
                    "note": "Koneksi Spotify tidak tersedia, ini adalah rekomendasi umum"
                },
                {
                    "title": "Chill Vibes",
                    "artist": "Lo-Fi Beats",
                    "album": "Study Music",
                    "url": "#",
                    "preview_url": None,
                    "cover_url": "https://via.placeholder.com/300x300/4ECDC4/FFFFFF?text=🎶",
                    "release_date": "2023",
                    "popularity": 68,
                    "duration_ms": 210000,
                    "explicit": False,
                    "note": "Koneksi Spotify tidak tersedia, ini adalah rekomendasi umum"
                }
            ],
            "mood_analysis": "general",
            "genre": "various",
            "total_found": 2,
            "error": "Spotify API not available"
        }
    
    def _extract_preferences(self, session_id: str, user_request: str, response: Dict):
        """Extract and store user music preferences from successful interactions"""
        try:
            # Extract genre preferences
            genre = response.get("genre")
            if genre:
                self.remember(session_id, "preferred_genre", genre, importance=6)
            
            # Extract artist preferences from clicked/liked songs
            recommendations = response.get("recommendations", [])
            if recommendations:
                # Store artists from recommendations as potential preferences
                artists = []
                for rec in recommendations:
                    artist = rec.get("artist", "").split(",")[0].strip()  # Get first artist
                    if artist:
                        artists.append(artist)
                
                if artists:
                    # Store as potential preferences with medium importance
                    self.remember(session_id, "liked_artists", artists, importance=5)
            
            # Learn mood-genre associations
            mood = response.get("mood_analysis")
            if mood and genre:
                existing_associations = self.recall(session_id, "mood_genre_map")
                associations = existing_associations.get("value", {}) if existing_associations else {}
                associations[mood] = genre
                self.remember(session_id, "mood_genre_map", associations, importance=7)
        
        except Exception as e:
            self.log_activity(f"Failed to extract music preferences: {e}", "ERROR")
    
    def learn_user_feedback(self, session_id: str, track_id: str, feedback: str, 
                           track_data: Dict = None):
        """Learn from user feedback on specific tracks"""
        try:
            if feedback.lower() in ['like', 'love', 'great', 'perfect']:
                # Positive feedback
                if track_data:
                    artist = track_data.get("artist", "")
                    genre = track_data.get("genre", "")
                    
                    # Increase preference for this artist
                    if artist:
                        self.remember(session_id, f"loved_artist_{artist}", 
                                    track_data, importance=8)
                    
                    # Increase preference for this genre
                    if genre:
                        self.remember(session_id, f"loved_genre_{genre}", 
                                    True, importance=7)
            
            elif feedback.lower() in ['dislike', 'hate', 'bad', 'skip']:
                # Negative feedback
                if track_data:
                    artist = track_data.get("artist", "")
                    
                    # Remember to avoid this artist
                    if artist:
                        self.remember(session_id, f"avoid_artist_{artist}", 
                                    True, importance=6)
        
        except Exception as e:
            self.log_activity(f"Failed to learn from user feedback: {e}", "ERROR")
