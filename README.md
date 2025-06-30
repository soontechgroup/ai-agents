# AI Agents

A FastAPI and React-based web application for AI agent management.

## ⚠️ Important Notes
**This project is currently only tested and verified to work on Windows systems.**

While Linux setup files exist in the project (e.g., `scripts/run.sh`), they are **untested** and **not maintained**. We recommend using Windows for development until Linux support is properly tested and verified.

## Prerequisites
- Windows 10 or later
- Python 3.8 or later
- Node.js 16 or later
- Docker Desktop for Windows
- PowerShell

## Project Structure
```
ai-agents/
├── app/                    # FastAPI backend
├── frontend/              # React frontend
├── data/                  # Database data directory
├── init/                  # Database initialization scripts
└── scripts/               # PowerShell startup scripts
                          # (Linux scripts exist but are untested)
```

## Getting Started

1. **Clone the repository**
   ```powershell
   git clone https://github.com/soontechgroup/ai-agents.git
   cd ai-agents
   ```

2. **Set up the backend**
   ```powershell
   # Create a Windows-specific virtual environment named 'win-env'
   python -m venv win-env
   
   # Activate the Windows virtual environment
   .\win-env\Scripts\activate
   
   # Your prompt should now show (win-env) at the beginning
   # Install dependencies
   pip install -r requirements.txt
   ```

3. **Set up the frontend**
   ```powershell
   cd frontend
   npm install
   cd ..
   ```

4. **Start the database**
   ```powershell
   docker-compose up -d
   ```

5. **Start the application**
   ```powershell
   # Make sure you're in the win-env virtual environment
   # You should see (win-env) in your PowerShell prompt
   .\scripts\run_backend.ps1
   ```
   In a new PowerShell window:
   ```powershell
   cd frontend
   npm run dev
   ```

## Development
- Backend runs on: http://localhost:8000
- Frontend runs on: http://localhost:5173
- MySQL runs on: localhost:3307

## Environment
- Backend: FastAPI with Python
- Frontend: React with TypeScript
- Database: MySQL 8.0
- Container: Docker

## Important Virtual Environment Notes
- The project uses a Windows-specific virtual environment named `win-env`
- Always ensure you see `(win-env)` in your PowerShell prompt when working with the backend
- If you don't see `(win-env)`, activate it using `.\win-env\Scripts\activate`

## Linux Support Status
- Linux setup files (e.g., `scripts/run.sh`) exist in the codebase
- These files are currently **untested** and **not maintained**
- The project has not been verified to work on Linux systems
- If you need to run this on Linux, significant testing and modifications may be required
- We recommend using Windows for development until Linux support is properly implemented

