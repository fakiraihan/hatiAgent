# Hati: Platform Multi-Agen Berkecepatan Tinggi untuk Manajemen Suasana Hati

![Hati Logo](https://via.placeholder.com/200x100/FF6B6B/FFFFFF?text=HATI)

**Hati** adalah platform AI berkecepatan tinggi yang menggunakan arsitektur multi-agen untuk memberikan respons yang empatik dan relevan sesuai dengan suasana hati pengguna. Dibangun dengan **Groq Cloud API** sebagai mesin utama untuk mencapai latensi yang sangat rendah.

## 🚀 Fitur Utama

- **⚡ Respons Instan**: Menggunakan Groq Cloud API untuk inferensi berkecepatan tinggi
- **🤖 Arsitektur Multi-Agent**: Tim spesialis yang dikelola oleh agen manajer  
- **❤️ Manajemen Suasana Hati**: 4 agen spesialis untuk berbagai kebutuhan emosional
- **💬 Percakapan Natural**: Output yang dipersonalisasi dan empatik
- **🔗 Integrasi API**: Spotify, Google Maps, Giphy, TMDb untuk konten kaya

## 🏗️ Arsitektur Sistem

### Agen Manajer (Orkestrator & Humas)
- 🎯 **LLM Call #1**: Analisis dan delegasi tugas ke agen spesialis
- 🎭 **LLM Call #2**: Personalisasi respons untuk percakapan yang natural

### Agen Spesialis
1. **🎵 Agen Musik**: Rekomendasi musik berdasarkan mood (Spotify API)
2. **🎬 Agen Hiburan**: Konten hiburan dan tawa (Giphy/TMDb API) 
3. **🧘 Agen Relaksasi**: Lokasi menenangkan (OpenStreetMap API - GRATIS!)
4. **💭 Agen Refleksi**: Percakapan introspektif (Groq LLM)

## 🛠️ Teknologi

- **Backend**: Python 3.9+, FastAPI, Groq API
- **Frontend**: PHP, HTML5, CSS3, JavaScript
- **LLM Engine**: Groq Cloud API (Llama 3/Mixtral)
- **External APIs**: Spotify, OpenStreetMap, Giphy, TMDb
- **Database**: SQLite dengan sistem memory dan caching

## 📁 Struktur Proyek

```
hati/
├── backend/
│   ├── agents/           # Implementasi semua agen spesialis
│   │   ├── music_agent.py
│   │   ├── entertainment_agent.py
│   │   ├── relaxation_agent.py
│   │   └── reflection_agent.py
│   ├── core/            # Logika inti sistem
│   │   ├── groq_client.py    # Groq API client
│   │   └── base_agent.py     # Base classes
│   ├── main.py          # FastAPI application
│   └── requirements.txt
├── frontend/            # Interface web
│   ├── index.html       # Chat interface
│   ├── style.css        # Styling
│   ├── script.js        # Frontend logic
│   └── api.php          # PHP API bridge
├── config/              # Konfigurasi
│   ├── .env             # Environment variables
│   ├── .env.example     # Template konfigurasi
│   └── settings.py      # Settings handler
├── tests/               # Unit tests
├── run.py              # Application runner
└── QUICK_START.md      # Panduan cepat
```

## ⚡ Quick Start

### 1. Installation
```bash
# Clone repository  
git clone <repository-url>
cd hati

# Setup Python environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r backend/requirements.txt
```

### 2. Configuration
```bash
# Copy environment template
cp config/.env.example config/.env

# Edit config/.env - MINIMAL: isi GROQ_API_KEY
# Dapatkan dari: https://console.groq.com/
```

### 3. Run Application
```bash
# Quick check
python run.py --mode check

# Start backend (Terminal 1)
python run.py --mode backend

# Start frontend (Terminal 2) 
python run.py --mode frontend
```

### 4. Access
- **Frontend**: http://localhost:8080
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 🧪 Testing & Development

### API Testing
```bash
# Health check
curl http://localhost:8000/health

# Send chat message
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Aku sedang sedih hari ini", "user_id": "test"}'

# Test specific agent
curl -X POST "http://localhost:8000/test-agent/reflection" \
  -H "Content-Type: application/json" \
  -d '{"message": "Aku butuh seseorang untuk bicara"}'
```

### Run Tests
```bash
# Unit tests
pytest tests/

# Specific test
pytest tests/test_agents.py::TestReflectionAgent -v
```

## 🎯 Usage Examples

### Chat Interactions
- **"Aku sedang sedih"** → Delegasi ke Reflection Agent
- **"Rekomendasikan musik yang menenangkan"** → Music Agent + Spotify
- **"Aku butuh hiburan"** → Entertainment Agent + Giphy/TMDb  
- **"Tempat untuk relaksasi di Jakarta"** → Relaxation Agent + Google Maps

### Expected Flow
1. **User Message** → Manager Agent
2. **LLM Call #1** → Analisis & delegasi ke specialist
3. **Specialist Processing** → API calls + data processing
4. **LLM Call #2** → Personalisasi respons
5. **Natural Response** → User

## 🔧 Configuration

### Required API Keys
```env
GROQ_API_KEY=your_groq_api_key         # WAJIB - dari https://console.groq.com/
SPOTIFY_CLIENT_ID=your_spotify_id      
SPOTIFY_CLIENT_SECRET=your_spotify_secret
GIPHY_API_KEY=your_giphy_key
TMDB_API_KEY=your_tmdb_key             
```

### Performance Settings
```env
GROQ_MODEL=llama3-70b-8192             # Model LLM yang digunakan
APP_PORT=8000                          # Port backend
DEBUG=True                             # Mode development
LOG_LEVEL=INFO                         # Level logging
```

## � Troubleshooting

### Common Issues
- **Backend won't start**: Check Python version & dependencies
- **API connection failed**: Verify API keys in `.env`
- **Frontend 404**: Make sure backend is running on port 8000
- **Groq timeout**: Check API quota & network connection

### Debug Mode
Enable debug mode di frontend settings untuk melihat:
- Response times per request
- Agent delegation decisions  
- API call details
- Error stack traces

## 📄 License & Contributing

- **License**: MIT License
- **Contributing**: Pull requests welcome!
- **Issues**: Report bugs via GitHub Issues
- **Documentation**: API docs at `/docs` endpoint

## � Team & Contact

- **Project Lead**: Faki Raihan
- **Documentation**: Built-in API docs
- **Support**: Create GitHub issue

---
