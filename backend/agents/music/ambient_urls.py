# Ambient Music URLs for Fallback
# These are free streaming URLs that can be used when Spotify API is not available

AMBIENT_MUSIC_URLS = {
    "rain": {
        "url": "https://www.youtube.com/watch?v=yIQd2Ya0Ziw",
        "stream_url": "https://archive.org/download/RainSounds-8Hours/Rain%20Sounds%20-%208%20Hours.mp3",
        "title": "Rain Sounds - 8 Hours",
        "duration": "8:00:00",
        "description": "Relaxing rain sounds for sleep and relaxation"
    },
    "ocean": {
        "url": "https://www.youtube.com/watch?v=F77zTAtTciU",
        "stream_url": "https://archive.org/download/OceanWaves-1Hour/Ocean%20Waves%20-%201%20Hour.mp3",
        "title": "Ocean Waves - 1 Hour", 
        "duration": "1:00:00",
        "description": "Peaceful ocean waves for meditation"
    },
    "forest": {
        "url": "https://www.youtube.com/watch?v=xNN7iTA57jM",
        "stream_url": "https://archive.org/download/ForestSounds-NatureSounds/Forest%20Sounds%20-%20Nature%20Sounds.mp3",
        "title": "Forest Sounds - Nature Ambience",
        "duration": "2:00:00", 
        "description": "Forest birds and nature sounds"
    },
    "cafe": {
        "url": "https://www.youtube.com/watch?v=DeumyOzKqgI", 
        "stream_url": "https://archive.org/download/CafeAmbience-CoffeeShop/Cafe%20Ambience%20-%20Coffee%20Shop.mp3",
        "title": "Cafe Ambience - Coffee Shop",
        "duration": "1:30:00",
        "description": "Coffee shop ambience with gentle chatter"
    },
    "city": {
        "url": "https://www.youtube.com/watch?v=1KaOrSuWZeM",
        "stream_url": "https://archive.org/download/CityAmbience-Night/City%20Ambience%20-%20Night.mp3", 
        "title": "City Ambience - Night Sounds",
        "duration": "2:00:00",
        "description": "Peaceful city sounds at night"
    }
}

# Note: These URLs are from Internet Archive which allows free streaming
# YouTube URLs are provided as reference, but actual streaming should use archive.org links
# Users can also use local files by placing them in backend/agents/music/ directory
