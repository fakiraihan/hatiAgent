import sys
import os
import subprocess
import importlib.util

def check_package_installed(package_name):
    """Check if a package is installed by trying to import it"""
    try:
        if package_name == "python-dotenv":
            import dotenv
            return True
        elif package_name == "fastapi":
            import fastapi
            return True
        elif package_name == "uvicorn":
            import uvicorn
            return True
        elif package_name == "requests":
            import requests
            return True
        elif package_name == "groq":
            import groq
            return True
        elif package_name == "pydantic-settings":
            import pydantic_settings
            return True
        elif package_name == "pytest":
            import pytest
            return True
        else:
            # Generic check using importlib
            spec = importlib.util.find_spec(package_name)
            return spec is not None
    except ImportError:
        return False

def check_system():
    """Perform comprehensive system checks"""
    print("🤖 Hati Multi-Agent System")
    print("=" * 40)
    
    # Check Python version
    python_version = sys.version
    print(f"✅ Python version: {python_version}")
    
    if sys.version_info < (3, 9):
        print("❌ Python 3.9+ required")
        return False
    
    print("\n🔍 Running system checks...")
    
    # Check required packages
    required_packages = [
        "fastapi",
        "uvicorn", 
        "requests",
        "python-dotenv",
        "groq",
        "pydantic-settings"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        if check_package_installed(package):
            print(f"✅ {package}")
        else:
            print(f"❌ {package}")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n❌ Missing packages: {', '.join(missing_packages)}")
        print("Run: pip install -r backend/requirements.txt")
        return False
    
    # Check environment file
    env_file = "config/.env"
    if os.path.exists(env_file):
        print("✅ Environment file exists")
        
        # Check for Groq API key
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
            
            groq_key = os.getenv('GROQ_API_KEY')
            if groq_key and groq_key.startswith('gsk_'):
                print("✅ Groq API key configured")
            else:
                print("⚠️  Groq API key not configured (required for full functionality)")
        except Exception as e:
            print(f"⚠️  Could not check environment variables: {e}")
    else:
        print("⚠️  Environment file not found. Copy config/.env.example to config/.env")
    
    # Check directory structure
    required_dirs = [
        "backend",
        "frontend", 
        "config",
        "tests"
    ]
    
    for directory in required_dirs:
        if os.path.exists(directory):
            print(f"✅ {directory}/ directory")
        else:
            print(f"❌ {directory}/ directory missing")
            return False
    
    print("\n✅ All system checks passed! Ready to run Hati.")
    print("\nNext steps:")
    print("1. Configure API keys in config/.env")
    print("2. Start backend: python run.py --mode backend")
    print("3. Start frontend: python run.py --mode frontend")
    print("4. Access: http://localhost:8080")
    
    return True

def start_backend():
    """Start the FastAPI backend"""
    print("🚀 Starting Hati Backend...")
    print("Backend will be available at: http://localhost:8000")
    print("API Documentation at: http://localhost:8000/docs")
    print("Press Ctrl+C to stop")
    
    try:
        subprocess.run([sys.executable, "-m", "uvicorn", "backend.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"])
    except KeyboardInterrupt:
        print("\n👋 Backend stopped")

def start_frontend():
    """Start the PHP frontend"""
    print("🌐 Starting Hati Frontend...")
    print("Frontend will be available at: http://localhost:8080")
    print("Press Ctrl+C to stop")
    
    os.chdir("frontend")
    try:
        subprocess.run(["php", "-S", "localhost:8080"])
    except KeyboardInterrupt:
        print("\n👋 Frontend stopped")
    except FileNotFoundError:
        print("❌ PHP not found. Please install PHP to run the frontend.")
        print("Alternative: Use any web server to serve the frontend/ directory")

def show_help():
    """Show help information"""
    print("🤖 Hati Multi-Agent System Runner")
    print("=" * 40)
    print("\nUsage: python run.py --mode <mode>")
    print("\nModes:")
    print("  check    - Run system checks")
    print("  backend  - Start FastAPI backend server")
    print("  frontend - Start PHP frontend server")
    print("  help     - Show this help message")
    print("\nExamples:")
    print("  python run.py --mode check")
    print("  python run.py --mode backend")
    print("  python run.py --mode frontend")

def main():
    if len(sys.argv) != 3 or sys.argv[1] != "--mode":
        show_help()
        return
    
    mode = sys.argv[2]
    
    if mode == "check":
        success = check_system()
        sys.exit(0 if success else 1)
    elif mode == "backend":
        start_backend()
    elif mode == "frontend":
        start_frontend()
    elif mode == "help":
        show_help()
    else:
        print(f"❌ Unknown mode: {mode}")
        show_help()
        sys.exit(1)

if __name__ == "__main__":
    main()