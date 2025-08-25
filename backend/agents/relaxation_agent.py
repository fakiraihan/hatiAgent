"""
Relaxation Agent - Specialist for relaxation and calming activities using Google Maps API
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

class RelaxationAgent(BaseAgent):
    """Agent for relaxation and calming activity recommendations"""
    
    def __init__(self):
        super().__init__("relaxation")
        self.google_maps_api_key = settings.google_maps_api_key
        self.foursquare_api_key = settings.foursquare_api_key
        self.goapi_key = settings.goapi_key
        self.places_base_url = "https://maps.googleapis.com/maps/api/place"
    
    async def process(self, user_message: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process relaxation recommendation request
        
        Returns:
            {
                "activities": {
                    "places": [...],
                    "indoor_activities": [...],
                    "breathing_exercises": [...]
                },
                "mood_analysis": "detected mood",
                "activity_type": "outdoor/indoor/mixed",
                "location_context": "detected location"
            }
        """
        try:
            mood = parameters.get("mood", "stressed")
            activity_type = parameters.get("type", parameters.get("place_type", "mixed"))
            location = parameters.get("location", "Jakarta")
            intensity = parameters.get("intensity", "medium")
            
            # Backup location extraction from user message if delegation missed it
            if location == "Jakarta" or not location:
                extracted_location = self._extract_location_from_message(user_message)
                if extracted_location:
                    location = extracted_location
                    
            self.log_activity(f"Finding relaxation for mood: {mood}, type: {activity_type}, location: {location}")
            
            activities = {}
            
            # Always try to find places when user asks for recommendations
            if any(keyword in user_message.lower() for keyword in ["tempat", "jalan", "wisata", "rekomendasi", "ke ", "di "]):
                places = await self._get_calming_places(location, mood)
                activities["places"] = places
                self.log_activity(f"Found {len(places)} places for location: {location}")
            
            # Generate indoor relaxation activities only if no places found or specifically requested
            if activity_type in ["mixed", "indoor"] or not activities.get("places"):
                indoor = await self._get_indoor_activities(mood, intensity)
                activities["indoor_activities"] = indoor
            
            # Provide breathing exercises and meditation only if no places found or specifically about stress relief
            if not activities.get("places") or any(word in user_message.lower() for word in ["stress", "cemas", "panik", "tegang"]):
                breathing = await self._get_breathing_exercises(mood, intensity)
                activities["breathing_exercises"] = breathing
                
                # Add relaxation tips only for stress-related queries without location requests
                if not activities.get("places"):
                    tips = await self._get_relaxation_tips(mood)
                    activities["relaxation_tips"] = tips
            
            return {
                "activities": activities,
                "mood_analysis": mood,
                "activity_type": activity_type,
                "location_context": location,
                "total_found": len(activities.get("places", [])),
                "search_parameters": {
                    "mood": mood,
                    "type": activity_type,
                    "location": location,
                    "intensity": intensity
                }
            }
            
        except Exception as e:
            self.log_activity(f"Error processing relaxation request: {e}", "ERROR")
            return self._fallback_response(user_message)
    
    async def _get_calming_places(self, location: str, mood: str, radius: int = 5000) -> List[Dict]:
        """Get nearby calming places using REAL APIs with verified data"""
        try:
            self.log_activity(f"Searching for REAL places in: {location} for mood: {mood}")
            
            places = []
            
            # Try Foursquare API first (most reliable for business data)
            foursquare_places = await self._get_places_from_foursquare(location, mood)
            if foursquare_places:
                places.extend(foursquare_places)
                self.log_activity(f"Found {len(foursquare_places)} places from Foursquare API")
            
            # Try Google Places API as backup (if API key available)
            if len(places) < 3 and self.google_maps_api_key:
                google_places = await self._get_places_from_google_maps(location, mood, radius)
                if google_places:
                    places.extend(google_places)
                    self.log_activity(f"Found {len(google_places)} places from Google Maps")
            
            # Try OpenStreetMap/Nominatim as secondary source (FREE and reliable)
            if len(places) < 3:
                osm_places = await self._get_places_from_openstreetmap(location, mood)
                if osm_places:
                    places.extend(osm_places)
                    self.log_activity(f"Found {len(osm_places)} places from OpenStreetMap")
            
            # Remove duplicates and return real data
            unique_places = self._remove_duplicate_places(places)
            
            if unique_places:
                self.log_activity(f"Returning {len(unique_places)} REAL verified places")
                return unique_places[:6]
            else:
                # Only use fallback if NO real data found
                self.log_activity("No real API data available, using curated recommendations")
                return self._get_curated_places(location, mood)
                
        except Exception as e:
            self.log_activity(f"Error fetching places: {e}")
            return self._get_curated_places(location, mood)
    
    async def _get_places_from_foursquare(self, location: str, mood: str) -> List[Dict]:
        """Get places from Foursquare API - REAL business data"""
        try:
            # Foursquare API v3 - real business data
            foursquare_api_key = "fsq3yKQkb1iHuUt9qMp8KPm8VJuQUQ3vgWWLJGPfmN1EtBo="  # Demo key
            
            # Get coordinates
            coordinates = self._get_coordinates(location)
            if not coordinates:
                return []
            
            lat, lng = coordinates.split(',')
            
            # Map mood to Foursquare categories
            categories = self._mood_to_foursquare_categories(mood)
            
            places = []
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                for category in categories[:2]:  # Try 2 categories
                    try:
                        headers = {
                            "Authorization": foursquare_api_key,
                            "Accept": "application/json"
                        }
                        
                        params = {
                            "ll": f"{lat},{lng}",
                            "radius": 8000,  # 8km radius
                            "categories": category["id"],
                            "limit": 10,
                            "sort": "POPULARITY"
                        }
                        
                        response = await client.get(
                            "https://api.foursquare.com/v3/places/search",
                            headers=headers,
                            params=params
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            
                            for place in data.get("results", [])[:5]:
                                place_info = {
                                    "name": place.get("name"),
                                    "type": category["name"],
                                    "address": self._format_foursquare_address(place.get("location", {})),
                                    "rating": place.get("rating", 0),
                                    "distance": place.get("distance", 0),
                                    "coordinates": {
                                        "lat": place.get("geocodes", {}).get("main", {}).get("latitude"),
                                        "lng": place.get("geocodes", {}).get("main", {}).get("longitude")
                                    },
                                    "source": "Foursquare API",
                                    "verified": True,
                                    "description": f"{category['name']} yang populer di {location}",
                                    "category_id": place.get("categories", [{}])[0].get("id"),
                                    "fsq_id": place.get("fsq_id")
                                }
                                places.append(place_info)
                                
                        elif response.status_code == 429:
                            self.log_activity("Foursquare API rate limit reached")
                            break
                        else:
                            self.log_activity(f"Foursquare API error: {response.status_code}")
                            
                    except Exception as e:
                        self.log_activity(f"Error with Foursquare category {category['name']}: {e}")
                        continue
            
            return places
            
        except Exception as e:
            self.log_activity(f"Foursquare API completely failed: {e}")
            return []
    
    def _mood_to_foursquare_categories(self, mood: str) -> List[Dict]:
        """Map mood to real Foursquare category IDs"""
        
        # Real Foursquare category IDs
        categories = {
            "stressed": [
                {"id": "16032", "name": "Taman"},  # Parks
                {"id": "13065", "name": "Kafe"},   # Cafe
                {"id": "12040", "name": "Spa"}     # Spa
            ],
            "sedih": [
                {"id": "13065", "name": "Kafe"},   # Cafe
                {"id": "12053", "name": "Museum"}, # Museum
                {"id": "13383", "name": "Toko Buku"} # Bookstore
            ],
            "bored": [
                {"id": "10030", "name": "Pusat Perbelanjaan"}, # Shopping
                {"id": "10032", "name": "Tempat Hiburan"},     # Entertainment
                {"id": "13065", "name": "Kafe"}                # Cafe
            ],
            "lelah": [
                {"id": "16032", "name": "Taman"},  # Parks
                {"id": "12040", "name": "Spa"},    # Spa
                {"id": "13065", "name": "Kafe"}    # Cafe
            ]
        }
        
        return categories.get(mood.lower(), categories["stressed"])
    
    def _format_foursquare_address(self, location_data: Dict) -> str:
        """Format Foursquare address data"""
        address_parts = []
        
        if location_data.get("address"):
            address_parts.append(location_data["address"])
        if location_data.get("locality"):
            address_parts.append(location_data["locality"])
        if location_data.get("region"):
            address_parts.append(location_data["region"])
        
        return ", ".join(address_parts) if address_parts else "Alamat tersedia di aplikasi"
    
    async def _get_places_from_openstreetmap(self, location: str, mood: str) -> List[Dict]:
        """Get places from OpenStreetMap/Nominatim - FREE and reliable"""
        try:
            self.log_activity(f"Searching OpenStreetMap for places in: {location}")
            
            # Map mood to OpenStreetMap amenity types
            amenity_types = self._mood_to_osm_amenities(mood)
            places = []
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                for amenity in amenity_types[:3]:  # Try 3 amenity types
                    try:
                        # Nominatim search with specific amenity type
                        params = {
                            "q": f"{amenity['query']} {location}",
                            "format": "json",
                            "limit": 10,
                            "countrycodes": "id",  # Indonesia only
                            "addressdetails": 1,
                            "extratags": 1,
                            "namedetails": 1
                        }
                        
                        headers = {
                            "User-Agent": "HatiApp/1.0 (relaxation-assistant)"
                        }
                        
                        response = await client.get(
                            "https://nominatim.openstreetmap.org/search",
                            headers=headers,
                            params=params
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            
                            for place in data[:5]:  # Take first 5 results
                                # Extract useful information
                                name = place.get("display_name", "").split(",")[0]
                                if not name or len(name) < 3:
                                    continue
                                    
                                place_info = {
                                    "name": name,
                                    "type": amenity["name"],
                                    "address": place.get("display_name", ""),
                                    "coordinates": {
                                        "lat": float(place.get("lat", 0)),
                                        "lng": float(place.get("lon", 0))
                                    },
                                    "source": "OpenStreetMap",
                                    "verified": True,
                                    "description": f"{amenity['name']} di {location}",
                                    "osm_id": place.get("osm_id"),
                                    "osm_type": place.get("osm_type"),
                                    "class": place.get("class"),
                                    "type_detail": place.get("type")
                                }
                                places.append(place_info)
                                
                        else:
                            self.log_activity(f"OpenStreetMap search failed: {response.status_code}")
                            
                    except Exception as e:
                        self.log_activity(f"Error searching OpenStreetMap for {amenity}: {e}")
                        continue
                        
            self.log_activity(f"OpenStreetMap search completed, found {len(places)} places")
            return places
            
        except Exception as e:
            self.log_activity(f"OpenStreetMap error: {e}")
            return []
    
    def _mood_to_osm_amenities(self, mood: str) -> List[Dict]:
        """Map mood to OpenStreetMap amenity types"""
        mood_mapping = {
            "stressed": [
                {"query": "spa", "name": "Spa"},
                {"query": "park", "name": "Taman"},
                {"query": "cafe", "name": "Cafe"},
                {"query": "place_of_worship", "name": "Tempat Ibadah"}
            ],
            "sad": [
                {"query": "park", "name": "Taman"},
                {"query": "museum", "name": "Museum"},
                {"query": "library", "name": "Perpustakaan"},
                {"query": "cafe", "name": "Cafe"}
            ],
            "anxious": [
                {"query": "park", "name": "Taman"},
                {"query": "place_of_worship", "name": "Tempat Ibadah"},
                {"query": "hospital", "name": "Rumah Sakit"},
                {"query": "pharmacy", "name": "Apotek"}
            ],
            "tired": [
                {"query": "spa", "name": "Spa"},
                {"query": "hotel", "name": "Hotel"},
                {"query": "cafe", "name": "Cafe"},
                {"query": "park", "name": "Taman"}
            ],
            "angry": [
                {"query": "park", "name": "Taman"},
                {"query": "sports_centre", "name": "Pusat Olahraga"},
                {"query": "gym", "name": "Gym"},
                {"query": "swimming_pool", "name": "Kolam Renang"}
            ],
            "lonely": [
                {"query": "cafe", "name": "Cafe"},
                {"query": "restaurant", "name": "Restoran"},
                {"query": "mall", "name": "Mall"},
                {"query": "community_centre", "name": "Pusat Komunitas"}
            ],
            "excited": [
                {"query": "tourist_attraction", "name": "Wisata"},
                {"query": "amusement_park", "name": "Taman Hiburan"},
                {"query": "shopping_mall", "name": "Mall"},
                {"query": "restaurant", "name": "Restoran"}
            ],
            "happy": [
                {"query": "tourist_attraction", "name": "Wisata"},
                {"query": "park", "name": "Taman"},
                {"query": "restaurant", "name": "Restoran"},
                {"query": "entertainment", "name": "Hiburan"}
            ],
            "calm": [
                {"query": "park", "name": "Taman"},
                {"query": "beach", "name": "Pantai"},
                {"query": "lake", "name": "Danau"},
                {"query": "mountain", "name": "Gunung"}
            ]
        }
        
        default_amenities = [
            {"query": "park", "name": "Taman"},
            {"query": "tourist_attraction", "name": "Wisata"},
            {"query": "cafe", "name": "Cafe"}
        ]
        
        return mood_mapping.get(mood.lower(), default_amenities)
    
    async def _get_places_from_here(self, location: str, mood: str) -> List[Dict]:
        """Deprecated - replaced with GOAPI"""
        return []
    
    def _get_curated_places(self, location: str, mood: str) -> List[Dict]:
        """Curated real places database - manually verified locations"""
        
        # Real, manually curated places for major Indonesian cities
        real_places = {
            "bandung": [
                {
                    "name": "Taman Hutan Raya Ir. H. Djuanda",
                    "type": "Taman",
                    "address": "Jl. Ir. H. Djuanda No.99, Ciburial, Cimenyan, Bandung",
                    "description": "Taman hutan seluas 590 hektar dengan udara sejuk dan pemandangan indah",
                    "coordinates": {"lat": -6.8746, "lng": 107.6434},
                    "source": "Curated Database",
                    "verified": True,
                    "rating": 4.5
                },
                {
                    "name": "Kawah Putih",
                    "type": "Wisata Alam",
                    "address": "Jl. Raya Soreang - Ciwidey, Ciwidey, Bandung Selatan",
                    "description": "Danau kawah dengan air berwarna putih kehijauan yang memukau",
                    "coordinates": {"lat": -7.1662, "lng": 107.4026},
                    "source": "Curated Database",
                    "verified": True,
                    "rating": 4.6
                },
                {
                    "name": "Floating Market Lembang",
                    "type": "Wisata Kuliner",
                    "address": "Jl. Grand Hotel No.33E, Lembang, Bandung Barat",
                    "description": "Pasar terapung dengan berbagai kuliner khas Bandung",
                    "coordinates": {"lat": -6.8115, "lng": 107.6179},
                    "source": "Curated Database",
                    "verified": True,
                    "rating": 4.3
                }
            ],
            "jakarta": [
                {
                    "name": "Taman Menteng",
                    "type": "Taman",
                    "address": "Jl. HOS Cokroaminoto, Menteng, Jakarta Pusat",
                    "description": "Taman kota di tengah Jakarta dengan fasilitas lengkap",
                    "coordinates": {"lat": -6.1944, "lng": 106.8314},
                    "source": "Curated Database",
                    "verified": True,
                    "rating": 4.2
                },
                {
                    "name": "Monumen Nasional (Monas)",
                    "type": "Monumen",
                    "address": "Jl. Silang Monas, Gambir, Jakarta Pusat",
                    "description": "Monumen nasional dengan taman luas di sekelilingnya",
                    "coordinates": {"lat": -6.1754, "lng": 106.8272},
                    "source": "Curated Database",
                    "verified": True,
                    "rating": 4.4
                },
                {
                    "name": "Kota Tua Jakarta",
                    "type": "Wisata Sejarah",
                    "address": "Jl. Taman Fatahillah, Pinangsia, Tamansari, Jakarta Barat",
                    "description": "Area bersejarah dengan museum dan kafe-kafe unik",
                    "coordinates": {"lat": -6.1352, "lng": 106.8133},
                    "source": "Curated Database",
                    "verified": True,
                    "rating": 4.3
                }
            ],
            "yogyakarta": [
                {
                    "name": "Candi Prambanan",
                    "type": "Candi",
                    "address": "Jl. Raya Solo - Yogyakarta No.16, Prambanan, Sleman",
                    "description": "Kompleks candi Hindu terbesar di Indonesia",
                    "coordinates": {"lat": -7.7520, "lng": 110.4915},
                    "source": "Curated Database",
                    "verified": True,
                    "rating": 4.7
                },
                {
                    "name": "Malioboro Street",
                    "type": "Jalan Wisata",
                    "address": "Jl. Malioboro, Yogyakarta",
                    "description": "Jalan legendaris dengan berbagai toko, kuliner, dan seni jalanan",
                    "coordinates": {"lat": -7.7925, "lng": 110.3656},
                    "source": "Curated Database",
                    "verified": True,
                    "rating": 4.5
                },
                {
                    "name": "Taman Sari",
                    "type": "Wisata Sejarah",
                    "address": "Jl. Taman, Kraton, Yogyakarta",
                    "description": "Situs bekas taman kerajaan dengan arsitektur yang indah",
                    "coordinates": {"lat": -7.8056, "lng": 110.3603},
                    "source": "Curated Database",
                    "verified": True,
                    "rating": 4.4
                }
            ]
        }
        
        location_lower = location.lower()
        for city, places in real_places.items():
            if city in location_lower:
                return places
        
        # Default to Jakarta places if location not found
        return real_places.get("jakarta", [])
    
    async def _get_places_from_osm(self, location: str, mood: str) -> List[Dict]:
        """Get places using OpenStreetMap Overpass API (completely FREE!)"""
        try:
            # Get coordinates for the location
            coordinates = self._get_coordinates(location)
            if not coordinates:
                return []
            
            # Map mood to OpenStreetMap place types
            place_types = self._mood_to_osm_types(mood)
            
            places = []
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                for place_type in place_types[:3]:  # Limit to 3 types
                    # Overpass API query for places
                    overpass_query = f"""
                    [out:json][timeout:15];
                    (
                      node["{place_type['key']}"="{place_type['value']}"](around:8000,{coordinates});
                      way["{place_type['key']}"="{place_type['value']}"](around:8000,{coordinates});
                    );
                    out center meta;
                    """
                    
                    try:
                        response = await client.post(
                            "https://overpass-api.de/api/interpreter",
                            data=overpass_query,
                            headers={"Content-Type": "text/plain"}
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            osm_places = self._process_osm_data(data, place_type['name'])
                            places.extend(osm_places)
                            
                        if len(places) >= 5:  # Stop when we have enough places
                            break
                            
                    except Exception as e:
                        self.log_activity(f"Error querying Overpass API for {place_type['name']}: {e}")
                        continue
            
            # Remove duplicates and limit results
            unique_places = self._remove_duplicate_places(places)
            return unique_places[:6]  # Return top 6 places
            
        except Exception as e:
            self.log_activity(f"Error with OpenStreetMap: {e}")
            return []
    
    def _get_coordinates(self, location: str) -> str:
        """Get coordinates for major Indonesian cities (no API required!)"""
        # Comprehensive coordinates mapping for Indonesia
        city_coords = {
            # Jakarta & surrounding
            "jakarta": "-6.2088,106.8456",
            "bekasi": "-6.2383,106.9756", 
            "tangerang": "-6.1783,106.6319",
            "depok": "-6.4025,106.7942",
            "bogor": "-6.5971,106.8060",
            
            # West Java
            "bandung": "-6.9175,107.6191",
            "cirebon": "-6.7063,108.5570",
            "sukabumi": "-6.9218,106.9270",
            "tasikmalaya": "-7.3506,108.2181",
            
            # Central Java
            "semarang": "-6.9667,110.4167",
            "yogyakarta": "-7.7956,110.3695",
            "yogya": "-7.7956,110.3695",
            "jogja": "-7.7956,110.3695",
            "solo": "-7.5663,110.8405",
            "surakarta": "-7.5663,110.8405",
            
            # East Java
            "surabaya": "-7.2575,112.7521",
            "malang": "-7.9666,112.6326",
            "kediri": "-7.8167,112.0167",
            "madiun": "-7.6298,111.5239",
            
            # North Sumatra
            "medan": "3.5952,98.6722",
            "pematangsiantar": "2.9595,99.0687",
            
            # South Sumatra
            "palembang": "-2.9761,104.7754",
            
            # Riau
            "pekanbaru": "0.5071,101.4478",
            
            # Lampung
            "bandar lampung": "-5.3971,105.2946",
            "lampung": "-5.3971,105.2946",
            
            # Bali
            "denpasar": "-8.6705,115.2126",
            "bali": "-8.6705,115.2126",
            "ubud": "-8.5069,115.2624",
            "sanur": "-8.6872,115.2620",
            "kuta": "-8.7183,115.1686",
            
            # Other major cities
            "makassar": "-5.1477,119.4327",
            "manado": "1.4748,124.8421",
            "balikpapan": "-1.2379,116.8529",
            "pontianak": "-0.0263,109.3425"
        }
        
        location_lower = location.lower().strip()
        
        # Direct match
        if location_lower in city_coords:
            return city_coords[location_lower]
        
        # Partial match (e.g., "ke bandung" -> "bandung")
        for city, coords in city_coords.items():
            if city in location_lower or location_lower in city:
                return coords
        
        # Default to Jakarta if location not found
        self.log_activity(f"Location '{location}' not found in database, defaulting to Jakarta")
        return city_coords["jakarta"]
    
    def _mood_to_osm_types(self, mood: str) -> List[Dict]:
        """Map mood to OpenStreetMap place types for Indonesian context"""
        
        # Common place types for relaxation and recreation
        base_types = [
            {"key": "leisure", "value": "park", "name": "Taman"},
            {"key": "amenity", "value": "cafe", "name": "Kafe"}, 
            {"key": "tourism", "value": "attraction", "name": "Tempat Wisata"},
            {"key": "leisure", "value": "garden", "name": "Kebun"},
            {"key": "amenity", "value": "library", "name": "Perpustakaan"},
            {"key": "leisure", "value": "fitness_centre", "name": "Pusat Kebugaran"},
            {"key": "shop", "value": "mall", "name": "Mall"},
            {"key": "tourism", "value": "museum", "name": "Museum"},
            {"key": "amenity", "value": "restaurant", "name": "Restoran"},
            {"key": "natural", "value": "beach", "name": "Pantai"}
        ]
        
        mood_mapping = {
            "stressed": [
                {"key": "leisure", "value": "park", "name": "Taman"},
                {"key": "tourism", "value": "attraction", "name": "Tempat Wisata"},
                {"key": "amenity", "value": "cafe", "name": "Kafe"}
            ],
            "sedih": [
                {"key": "amenity", "value": "cafe", "name": "Kafe"},
                {"key": "amenity", "value": "library", "name": "Perpustakaan"},
                {"key": "tourism", "value": "museum", "name": "Museum"}
            ],
            "bosan": [
                {"key": "tourism", "value": "attraction", "name": "Tempat Wisata"},
                {"key": "shop", "value": "mall", "name": "Mall"},
                {"key": "amenity", "value": "restaurant", "name": "Restoran"}
            ],
            "lelah": [
                {"key": "leisure", "value": "park", "name": "Taman"},
                {"key": "amenity", "value": "cafe", "name": "Kafe"},
                {"key": "leisure", "value": "garden", "name": "Kebun"}
            ]
        }
        
        return mood_mapping.get(mood.lower(), base_types[:3])
    
    def _process_osm_data(self, data: Dict, place_type_name: str) -> List[Dict]:
        """Process OpenStreetMap data into our standardized format"""
        places = []
        
        for element in data.get("elements", []):
            tags = element.get("tags", {})
            name = tags.get("name")
            
            if not name:
                continue
                
            # Get coordinates (handle both nodes and ways)
            if element.get("lat") and element.get("lon"):
                lat, lon = element["lat"], element["lon"]
            elif element.get("center"):
                lat, lon = element["center"]["lat"], element["center"]["lon"]
            else:
                continue
            
            # Build address from available tags
            address_parts = []
            if tags.get("addr:street"):
                address_parts.append(tags["addr:street"])
            if tags.get("addr:city"):
                address_parts.append(tags["addr:city"])
            
            address = ", ".join(address_parts) if address_parts else "Alamat tidak tersedia"
            
            place_info = {
                "name": name,
                "type": place_type_name,
                "address": address,
                "description": tags.get("description", f"Tempat {place_type_name.lower()} yang bagus untuk relaksasi"),
                "coordinates": {
                    "lat": lat,
                    "lon": lon
                },
                "source": "OpenStreetMap",
                "additional_info": {
                    "opening_hours": tags.get("opening_hours"),
                    "phone": tags.get("phone"),
                    "website": tags.get("website"),
                    "amenity": tags.get("amenity"),
                    "leisure": tags.get("leisure"),
                    "tourism": tags.get("tourism")
                }
            }
            
            places.append(place_info)
        
        return places
    
    def _remove_duplicate_places(self, places: List[Dict]) -> List[Dict]:
        """Remove duplicate places based on name similarity"""
        unique_places = []
        seen_names = set()
        
        for place in places:
            name_lower = place["name"].lower().strip()
            if name_lower not in seen_names:
                seen_names.add(name_lower)
                unique_places.append(place)
        
        return unique_places
    
    def _get_general_places(self, location: str, mood: str) -> List[Dict]:
        """Fallback recommendations when APIs fail"""
        return [
            {
                "name": f"Taman Kota {location}",
                "type": "Taman",
                "address": f"Area pusat kota {location}",
                "description": "Taman kota yang nyaman untuk bersantai dan menghilangkan stres",
                "source": "General Recommendation"
            },
            {
                "name": f"Mall/Plaza di {location}",
                "type": "Pusat Perbelanjaan", 
                "address": f"Area komersial {location}",
                "description": "Pusat perbelanjaan dengan AC dan berbagai fasilitas hiburan",
                "source": "General Recommendation"
            },
            {
                "name": f"Kafe di {location}",
                "type": "Kafe",
                "address": f"Area pusat {location}",
                "description": "Kafe nyaman untuk duduk santai sambil menikmati minuman",
                "source": "General Recommendation"
            }
        ]
    
    async def _get_places_from_google_maps(self, location: str, mood: str, radius: int) -> List[Dict]:
        """Get places from Google Places API - verified business data"""
        try:
            if not self.google_maps_api_key or self.google_maps_api_key == "your_google_maps_api_key_here":
                return []
            
            self.log_activity(f"Using Google Places API for {location}")
            
            # Get coordinates for location
            coordinates = self._get_coordinates(location)
            if not coordinates:
                return []
            
            lat, lng = coordinates.split(',')
            
            # Map mood to Google Places types
            place_types = self._mood_to_google_types(mood)
            
            places = []
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                for place_type in place_types[:2]:  # Limit API calls
                    try:
                        # Google Places Nearby Search
                        params = {
                            "location": f"{lat},{lng}",
                            "radius": radius,
                            "type": place_type["type"],
                            "key": self.google_maps_api_key,
                            "language": "id"  # Indonesian language
                        }
                        
                        response = await client.get(
                            f"{self.places_base_url}/nearbysearch/json",
                            params=params
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            
                            if data.get("status") == "OK":
                                for place in data.get("results", [])[:4]:
                                    place_info = {
                                        "name": place.get("name"),
                                        "type": place_type["name"],
                                        "address": place.get("vicinity", "Alamat tidak tersedia"),
                                        "rating": place.get("rating", 0),
                                        "price_level": place.get("price_level", 0),
                                        "coordinates": {
                                            "lat": place["geometry"]["location"]["lat"],
                                            "lng": place["geometry"]["location"]["lng"]
                                        },
                                        "place_id": place.get("place_id"),
                                        "photos": place.get("photos", []),
                                        "opening_hours": place.get("opening_hours", {}),
                                        "source": "Google Places API",
                                        "verified": True,
                                        "description": f"{place_type['name']} yang verified oleh Google"
                                    }
                                    places.append(place_info)
                            else:
                                self.log_activity(f"Google Places API error: {data.get('status')}")
                                
                        elif response.status_code == 403:
                            self.log_activity("Google Places API: Invalid API key or quota exceeded")
                            break
                        else:
                            self.log_activity(f"Google Places API HTTP error: {response.status_code}")
                            
                    except Exception as e:
                        self.log_activity(f"Error with Google Places type {place_type['name']}: {e}")
                        continue
            
            return places
            
        except Exception as e:
            self.log_activity(f"Google Places API completely failed: {e}")
            return []
    
    def _mood_to_google_types(self, mood: str) -> List[Dict]:
        """Map mood to Google Places API types"""
        
        google_types = {
            "stressed": [
                {"type": "park", "name": "Taman"},
                {"type": "spa", "name": "Spa"},
                {"type": "cafe", "name": "Kafe"}
            ],
            "sedih": [
                {"type": "cafe", "name": "Kafe"},
                {"type": "museum", "name": "Museum"},
                {"type": "book_store", "name": "Toko Buku"}
            ],
            "bored": [
                {"type": "shopping_mall", "name": "Mall"},
                {"type": "tourist_attraction", "name": "Tempat Wisata"},
                {"type": "amusement_park", "name": "Tempat Hiburan"}
            ],
            "lelah": [
                {"type": "park", "name": "Taman"},
                {"type": "spa", "name": "Spa"},
                {"type": "cafe", "name": "Kafe"}
            ]
        }
        
        return google_types.get(mood.lower(), google_types["stressed"])
    
    async def _get_places_from_osm(self, location: str, mood: str) -> List[Dict]:
        """Fallback: Get places using OpenStreetMap Overpass API (FREE)"""
        try:
            self.log_activity(f"Using OpenStreetMap fallback for location: {location}")
            
            # Simple coordinate mapping for major Indonesian cities
            city_coords = {
                "jakarta": "-6.2088,106.8456",
                "bandung": "-6.9175,107.6191", 
                "surabaya": "-7.2575,112.7521",
                "yogyakarta": "-7.7956,110.3695",
                "medan": "3.5952,98.6722",
                "semarang": "-6.9667,110.4167",
                "palembang": "-2.9761,104.7754",
                "makassar": "-5.1477,119.4327",
                "bali": "-8.4095,115.1889",
                "denpasar": "-8.4095,115.1889"
            }
            
            # Find coordinates for the location
            location_lower = location.lower()
            coordinates = None
            for city, coords in city_coords.items():
                if city in location_lower:
                    coordinates = coords
                    break
            
            if not coordinates:
                coordinates = city_coords["jakarta"]  # Default to Jakarta
            
            # Map mood to place types for OpenStreetMap
            place_types = {
                "stressed": ["park", "garden", "library"],
                "anxious": ["park", "cafe", "bookstore"],
                "sad": ["cafe", "museum", "art_gallery"],
                "tired": ["spa", "park", "cafe"],
                "overwhelmed": ["park", "library", "quiet"]
            }
            
            mood_types = place_types.get(mood.lower(), ["park", "cafe"])
            
            places = []
            
            async with httpx.AsyncClient() as client:
                for place_type in mood_types[:2]:  # Limit to 2 types
                    # Overpass query for different amenities
                    overpass_query = f"""
                    [out:json][timeout:25];
                    (
                      node["amenity"="{place_type}"](around:5000,{coordinates});
                      node["leisure"="{place_type}"](around:5000,{coordinates});
                      node["tourism"="{place_type}"](around:5000,{coordinates});
                    );
                    out body;
                    """
                    
                    try:
                        response = await client.post(
                            "https://overpass-api.de/api/interpreter",
                            data=overpass_query,
                            timeout=10.0
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            
                            for element in data.get("elements", [])[:3]:
                                tags = element.get("tags", {})
                                name = tags.get("name", "Unknown Place")
                                
                                if name and name != "Unknown Place":
                                    places.append({
                                        "name": name,
                                        "type": place_type,
                                        "rating": None,  # OSM doesn't have ratings
                                        "address": self._build_address_osm(tags),
                                        "open_now": None,
                                        "place_id": f"osm_{element.get('id')}",
                                        "location": {
                                            "lat": element.get("lat"),
                                            "lng": element.get("lon")
                                        },
                                        "source": "OpenStreetMap"
                                    })
                    except Exception as e:
                        self.log_activity(f"Error with OSM query for {place_type}: {e}", "ERROR")
                        continue
            
            self.log_activity(f"Found {len(places)} places from OpenStreetMap")
            return places[:5]
            
        except Exception as e:
            self.log_activity(f"Error with OpenStreetMap fallback: {e}", "ERROR")
            return []

    def _build_address_osm(self, tags: Dict) -> str:
        """Build address from OSM tags"""
        address_parts = []
        if tags.get("addr:street"):
            address_parts.append(tags["addr:street"])
        if tags.get("addr:city"):
            address_parts.append(tags["addr:city"])
        elif tags.get("addr:town"):
            address_parts.append(tags["addr:town"])
        
        return ", ".join(address_parts) if address_parts else "Alamat tidak tersedia"
    
    async def _get_indoor_activities(self, mood: str, intensity: str) -> List[Dict]:
        """Generate indoor relaxation activities based on mood"""
        activities_by_mood = {
            "stressed": [
                {"activity": "Meditation 10 menit", "duration": "10 min", "difficulty": "easy"},
                {"activity": "Menggambar atau mewarnai", "duration": "30 min", "difficulty": "easy"},
                {"activity": "Membaca buku favorit", "duration": "flexible", "difficulty": "easy"},
                {"activity": "Aromaterapi dengan lilin wangi", "duration": "20 min", "difficulty": "easy"}
            ],
            "anxious": [
                {"activity": "Journaling - tulis perasaan", "duration": "15 min", "difficulty": "medium"},
                {"activity": "Yoga ringan", "duration": "20 min", "difficulty": "medium"},
                {"activity": "Mendengarkan podcast menenangkan", "duration": "30 min", "difficulty": "easy"},
                {"activity": "Merajut atau kerajinan tangan", "duration": "45 min", "difficulty": "medium"}
            ],
            "sad": [
                {"activity": "Mandi air hangat", "duration": "20 min", "difficulty": "easy"},
                {"activity": "Menonton film komedi ringan", "duration": "90 min", "difficulty": "easy"},
                {"activity": "Memasak makanan favorit", "duration": "60 min", "difficulty": "medium"},
                {"activity": "Video call dengan teman dekat", "duration": "30 min", "difficulty": "easy"}
            ],
            "overwhelmed": [
                {"activity": "Bersih-bersih ruangan", "duration": "30 min", "difficulty": "medium"},
                {"activity": "Membuat to-do list yang realistis", "duration": "10 min", "difficulty": "easy"},
                {"activity": "Progressive muscle relaxation", "duration": "15 min", "difficulty": "medium"},
                {"activity": "Membuat teh herbal", "duration": "10 min", "difficulty": "easy"}
            ],
            "tired": [
                {"activity": "Power nap 20 menit", "duration": "20 min", "difficulty": "easy"},
                {"activity": "Stretching ringan", "duration": "10 min", "difficulty": "easy"},
                {"activity": "Minum air putih yang cukup", "duration": "5 min", "difficulty": "easy"},
                {"activity": "Matikan gadget 30 menit", "duration": "30 min", "difficulty": "medium"}
            ]
        }
        
        mood_activities = activities_by_mood.get(mood.lower(), activities_by_mood["stressed"])
        
        # Adjust based on intensity
        if intensity == "low":
            return [act for act in mood_activities if act["difficulty"] == "easy"][:3]
        elif intensity == "high":
            return mood_activities
        else:
            return mood_activities[:3]
    
    async def _get_breathing_exercises(self, mood: str, intensity: str) -> List[Dict]:
        """Provide breathing exercises based on mood"""
        exercises = {
            "4-7-8 Technique": {
                "description": "Tarik napas 4 hitungan, tahan 7 hitungan, keluarkan 8 hitungan",
                "duration": "3-5 menit",
                "good_for": ["stress", "anxiety", "sleep"],
                "steps": [
                    "Duduk dengan nyaman, punggung tegak",
                    "Buang semua udara dari paru-paru",
                    "Tarik napas melalui hidung sambil hitung 4",
                    "Tahan napas sambil hitung 7",
                    "Buang napas melalui mulut sambil hitung 8",
                    "Ulangi 3-4 kali"
                ]
            },
            "Box Breathing": {
                "description": "Bernapas dalam pola kotak: 4-4-4-4",
                "duration": "5-10 menit",
                "good_for": ["focus", "calm", "anxiety"],
                "steps": [
                    "Tarik napas 4 hitungan",
                    "Tahan napas 4 hitungan",
                    "Buang napas 4 hitungan",
                    "Tahan kosong 4 hitungan",
                    "Ulangi 5-10 kali"
                ]
            },
            "Simple Deep Breathing": {
                "description": "Bernapas dalam sederhana untuk relaksasi cepat",
                "duration": "2-3 menit",
                "good_for": ["quick relief", "anywhere"],
                "steps": [
                    "Letakkan satu tangan di dada, satu di perut",
                    "Tarik napas dalam melalui hidung",
                    "Pastikan perut mengembang lebih dari dada",
                    "Buang napas perlahan melalui mulut",
                    "Ulangi 5-10 kali"
                ]
            }
        }
        
        # Return appropriate exercises based on intensity
        if intensity == "low":
            return [exercises["Simple Deep Breathing"]]
        elif intensity == "high":
            return list(exercises.values())
        else:
            return [exercises["4-7-8 Technique"], exercises["Simple Deep Breathing"]]
    
    async def _get_relaxation_tips(self, mood: str) -> List[str]:
        """Get relaxation tips based on mood"""
        tips_by_mood = {
            "stressed": [
                "Ingat: yang penting adalah bernapas dan mengambil satu langkah kecil setiap saat",
                "Cobalah teknik 5-4-3-2-1: 5 hal yang kamu lihat, 4 yang kamu dengar, 3 yang kamu sentuh, 2 yang kamu cium, 1 yang kamu rasakan",
                "Stress adalah sinyal tubuh bahwa kamu perlu istirahat - dengarkan tubuhmu"
            ],
            "anxious": [
                "Kecemasan adalah pikiran tentang masa depan - fokuslah pada saat ini",
                "Tidak apa-apa tidak sempurna - kamu sudah melakukan yang terbaik",
                "Cemas itu normal, tapi jangan biarkan dia yang mengontrol hidupmu"
            ],
            "sad": [
                "Sedih itu bagian dari hidup - izinkan dirimu merasakannya",
                "Besok adalah kesempatan baru untuk memulai lagi",
                "Kamu tidak sendirian - ada orang yang peduli padamu"
            ],
            "default": [
                "Relaksasi adalah investasi terbaik untuk kesehatan mentalmu",
                "Luangkan waktu untuk dirimu sendiri - kamu layak mendapatkannya",
                "Pikiran yang tenang menghasilkan keputusan yang lebih baik"
            ]
        }
        
        return tips_by_mood.get(mood.lower(), tips_by_mood["default"])
    
    def _mood_to_place_types(self, mood: str) -> List[str]:
        """Map mood to Google Places API place types"""
        mood_places = {
            "stressed": ["park", "spa", "library", "museum"],
            "anxious": ["park", "church", "library", "cafe"],
            "sad": ["park", "cafe", "bookstore", "art_gallery"],
            "overwhelmed": ["park", "beach", "hiking_area", "spa"],
            "tired": ["cafe", "park", "spa", "library"]
        }
        return mood_places.get(mood.lower(), ["park", "cafe"])
    
    def _extract_location_from_message(self, user_message: str) -> str:
        """Extract location from user message as backup"""
        message_lower = user_message.lower()
        
        # Known Indonesian cities and locations
        locations = [
            "jakarta", "bandung", "surabaya", "yogyakarta", "yogya", "jogja", 
            "semarang", "medan", "palembang", "makassar", "denpasar", "bali",
            "solo", "surakarta", "malang", "bogor", "depok", "tangerang", 
            "bekasi", "cirebon", "pontianak", "balikpapan", "manado",
            "pekanbaru", "bandar lampung", "lampung", "tasikmalaya",
            "sukabumi", "kediri", "madiun", "pematangsiantar", "ubud",
            "sanur", "kuta"
        ]
        
        # Look for city names in the message
        for location in locations:
            # Check for exact matches or common patterns
            patterns = [
                f" {location} ",  # " bandung "
                f" ke {location}",  # " ke bandung"
                f" di {location}",  # " di bandung"
                f"{location} ",  # "bandung " (at start)
                f" {location}",  # " bandung" (at end)
            ]
            
            for pattern in patterns:
                if pattern in f" {message_lower} ":
                    return location.title()  # Return with proper capitalization
        
        return None
    
    def _fallback_response(self, user_message: str) -> Dict[str, Any]:
        """Fallback response when APIs are not available"""
        return {
            "activities": {
                "indoor_activities": [
                    {
                        "activity": "Bernapas dalam-dalam 10 kali",
                        "duration": "2 min",
                        "difficulty": "easy"
                    }
                ],
                "breathing_exercises": [
                    {
                        "description": "Tarik napas dalam, tahan 3 detik, buang perlahan",
                        "duration": "5 menit",
                        "steps": ["Duduk nyaman", "Tarik napas dalam", "Tahan 3 detik", "Buang perlahan"]
                    }
                ],
                "relaxation_tips": [
                    "Kadang yang kamu butuhkan hanya bernapas dan mengingat bahwa kamu kuat"
                ]
            },
            "mood_analysis": "general",
            "activity_type": "fallback",
            "error": "Google Maps API not available"
        }
