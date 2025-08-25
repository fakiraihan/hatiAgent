# Music Files

This directory contained local ambient music files (cafe.wav, city.wav, forest.wav, ocean.wav, rain.wav) that were used for background ambient sounds in the frontend.

## Change to Streaming URLs

To reduce repository size and make the project more GitHub-friendly, these local music files have been replaced with streaming URLs from Freesound.org.

The ambient music system now uses:
- **Free streaming URLs** from Freesound.org
- **No local file dependencies**
- **Smaller repository size**
- **Better for deployment**

## How it works now

1. **Frontend** (`frontend/script.js`): `AmbientMusic` class uses streaming URLs
2. **Backend** (`backend/main.py`): `/music/tracks` endpoint returns streaming URLs
3. **No local files needed**: Everything streams from external sources

## Benefits

- ✅ Smaller repository size (saved ~25MB)
- ✅ No copyright concerns
- ✅ Always available (no need to download files)
- ✅ Better for GitHub hosting
- ✅ Faster git clone/download

## Original Files

The original music files are backed up in `music_backup/` directory if you want to use local files instead.

To restore local file support:
1. Copy files from `music_backup/` to `backend/music/`
2. Uncomment the StaticFiles mount in `backend/main.py`
3. Update URLs in `frontend/script.js` to use `http://localhost:8000/music/`
