# 🚀 Quick Start Guide - Hati Multi-Agent System

Selamat datang di **Hati**! Panduan ini akan membantu Anda menjalankan sistem multi-agen berkecepatan tinggi untuk manajemen suasana hati.

## 📋 Prerequisites

- **Python 3.9+** 
- **PHP 7.4+** (untuk frontend)
- **API Keys** dari:
  - [Groq Cloud](https://console.groq.com/) - **WAJIB**
  - [Spotify](https://developer.spotify.com/) - Opsional
  - [Google Maps](https://console.cloud.google.com/) - Opsional  
  - [Giphy](https://developers.giphy.com/) - Opsional
  - [TMDb](https://www.themoviedb.org/settings/api) - Opsional

## ⚡ Installation & Setup

### 1. Clone & Setup Environment
```bash
# Clone project
git clone <your-repo>
cd hati

# Setup Python virtual environment (recommended)
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt
```

### 2. Configure API Keys
```bash
# Copy environment template
cp config/.env.example config/.env

# Edit config/.env dan masukkan API keys Anda
# Minimal: GROQ_API_KEY harus diisi
```

### 3. Quick Check
```bash
python run.py --mode check
```

## 🏃‍♂️ Running the Application

### Option 1: Auto Runner (Recommended)
```bash
# Terminal 1 - Backend
python run.py --mode backend

# Terminal 2 - Frontend  
python run.py --mode frontend
```

### Option 2: Manual
```bash
# Backend
cd backend
uvicorn main:app --reload

# Frontend (new terminal)
cd frontend
php -S localhost:8080
```

## 🌐 Access Points

- **Frontend**: http://localhost:8080
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 🧪 Testing

```bash
# Run tests
pytest tests/

# Test specific agent
python -m pytest tests/test_agents.py::TestReflectionAgent -v

# Test API endpoint
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Aku sedang sedih hari ini", "user_id": "test"}'
```

## 🔧 Development Mode

### Backend dengan auto-reload:
```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Debug mode:
- Enable debug mode di frontend settings
- Check console untuk performance metrics
- Monitor logs di terminal backend

## 📱 Usage Examples

### Chat Commands:
- **"Aku sedang sedih"** → Reflection Agent
- **"Rekomendasikan musik yang menenangkan"** → Music Agent  
- **"Aku butuh hiburan"** → Entertainment Agent
- **"Tempat untuk relaksasi di Jakarta"** → Relaxation Agent

### API Testing:
```bash
# Health check
curl http://localhost:8000/health

# Chat message
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello Hati!", "user_id": "test123"}'

# Get agents info
curl http://localhost:8000/agents
```

## ⚠️ Troubleshooting

### Backend tidak start:
1. Check Python version: `python --version`
2. Install dependencies: `pip install -r backend/requirements.txt`
3. Check API keys di `config/.env`
4. Verify port 8000 tidak dipakai

### Frontend tidak load:
1. Check PHP installed: `php --version`
2. Verify backend running di port 8000
3. Check browser console untuk errors
4. Try different port: `php -S localhost:8081`

### API Keys Issues:
- **Groq**: Pastikan API key valid dan ada quota
- **Spotify**: Perlu Client ID dan Client Secret
- **Google Maps**: Enable Places API dan Geocoding API
- **External APIs**: Check rate limits

### Common Errors:
```bash
# ImportError: No module named 'fastapi'
pip install fastapi uvicorn

# Connection refused to localhost:8000  
python run.py --mode backend

# CORS error
Check FRONTEND_URL di config/.env

# Groq API error
Verify GROQ_API_KEY di config/.env
```

## 🚀 Production Deployment

### Backend (Recommended):
```bash
# Using gunicorn
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app

# Using Docker
# TODO: Add Dockerfile
```

### Frontend:
- Deploy ke Apache/Nginx dengan PHP support
- Update backend URL di settings
- Setup HTTPS untuk production

## 📊 Performance Tips

1. **Groq API**: Pilih model yang sesuai (llama3-8b untuk speed, llama3-70b untuk quality)
2. **Caching**: Implement Redis untuk response caching
3. **Rate Limiting**: Monitor API quotas
4. **Monitoring**: Add application monitoring

## 📞 Support

- **Issues**: Create GitHub issue
- **Documentation**: Check `/docs` endpoint
- **API Reference**: http://localhost:8000/docs

---

> **Happy Coding!** 🤖❤️ Hati siap membantu mengelola suasana hati dengan respons yang instant!
