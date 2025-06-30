# FastAPI AI Agents Control Script
# For Windows environments

# Color definitions for PowerShell
$Colors = @{
    Red = 'Red'
    Green = 'Green'
    Yellow = 'Yellow'
    Blue = 'Cyan'
}

# Logging functions
function Write-LogInfo { param($Message)
    Write-Host "[INFO] $Message" -ForegroundColor $Colors.Blue
}

function Write-LogSuccess { param($Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor $Colors.Green
}

function Write-LogWarning { param($Message)
    Write-Host "[WARNING] $Message" -ForegroundColor $Colors.Yellow
}

function Write-LogError { param($Message)
    Write-Host "[ERROR] $Message" -ForegroundColor $Colors.Red
}

# Get script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir

Write-LogInfo "Project directory: $ProjectDir"

# Change to project directory
Set-Location $ProjectDir

# Configuration variables
$DefaultHost = "0.0.0.0"
$DefaultPort = "8000"
$PidFile = "pids/app.pid"
$LogFile = "logs/app.log"
$VenvDir = ".win-venv"

# Check Python environment
function Check-Python {
    Write-LogInfo "Checking Python environment..."
    
    try {
        $pythonVersion = (python --version 2>&1).ToString()
        Write-LogSuccess "Python version: $pythonVersion"
        
        # Check Python version
        $versionCheck = python -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"
        if ($LASTEXITCODE -ne 0) {
            Write-LogError "Python version 3.8 or higher is required"
            exit 1
        }
    }
    catch {
        Write-LogError "Python is not installed or not in PATH"
        exit 1
    }
}

# Setup virtual environment
function Setup-Venv {
    Write-LogInfo "Setting up virtual environment..."
    
    if (-not (Test-Path $VenvDir)) {
        Write-LogInfo "Creating virtual environment..."
        python -m venv $VenvDir
        Write-LogSuccess "Virtual environment created"
    }
    else {
        Write-LogInfo "Virtual environment already exists"
    }
    
    # Activate virtual environment
    Write-LogInfo "Activating virtual environment..."
    & "$VenvDir\Scripts\Activate.ps1"
    
    # Display Python path
    $pythonPath = (Get-Command python).Path
    Write-LogSuccess "Virtual environment activated: $pythonPath"
}

# Install dependencies
function Install-Dependencies {
    Write-LogInfo "Installing project dependencies..."
    
    if (-not (Test-Path "requirements.txt")) {
        Write-LogError "requirements.txt file not found"
        exit 1
    }
    
    # Upgrade pip
    python -m pip install --upgrade pip
    
    # Install dependencies
    pip install -r requirements.txt
    Write-LogSuccess "Dependencies installed"
}

# Check environment configuration
function Check-Env {
    Write-LogInfo "Checking environment configuration..."
    
    # Set default environment variables if not exists
    if (-not $env:HOST) { $env:HOST = $DefaultHost }
    if (-not $env:PORT) { $env:PORT = $DefaultPort }
    if (-not $env:RELOAD) { $env:RELOAD = "true" }
    
    # Database configuration
    if (-not $env:DB_HOST) { $env:DB_HOST = "localhost" }
    if (-not $env:DB_PORT) { $env:DB_PORT = "3307" }
    if (-not $env:DB_USER) { $env:DB_USER = "root" }
    if (-not $env:DB_PASSWORD) { $env:DB_PASSWORD = "123456" }
    if (-not $env:DB_NAME) { $env:DB_NAME = "ai_agents" }
    
    # JWT configuration
    if (-not $env:JWT_SECRET_KEY) { $env:JWT_SECRET_KEY = "your-secret-key-keep-it-secret" }
    if (-not $env:JWT_ALGORITHM) { $env:JWT_ALGORITHM = "HS256" }
    if (-not $env:JWT_ACCESS_TOKEN_EXPIRE_MINUTES) { $env:JWT_ACCESS_TOKEN_EXPIRE_MINUTES = "30" }
    
    Write-LogSuccess "Environment configured - Host: $env:HOST, Port: $env:PORT"
    
    # Load .env file if it exists
    if (Test-Path ".env") {
        Write-LogInfo "Loading .env file..."
        Get-Content ".env" | ForEach-Object {
            if ($_ -match '^([^=]+)=(.*)$') {
                $key = $matches[1]
                $value = $matches[2]
                [Environment]::SetEnvironmentVariable($key, $value)
            }
        }
        Write-LogSuccess "Environment variables loaded"
    }
}

# Create necessary directories
function Setup-Directories {
    Write-LogInfo "Setting up necessary directories..."
    
    # Create pids directory
    if (-not (Test-Path "pids")) {
        New-Item -ItemType Directory -Path "pids" | Out-Null
        Write-LogSuccess "PID directory created"
    }
    
    # Create logs directory
    if (-not (Test-Path "logs")) {
        New-Item -ItemType Directory -Path "logs" | Out-Null
        Write-LogSuccess "Logs directory created"
    }
}

# Check Docker and database
function Check-DockerAndDb {
    Write-LogInfo "Checking Docker and database..."
    
    # Check if Docker is running
    try {
        docker info | Out-Null
    }
    catch {
        Write-LogError "Docker is not running. Please start Docker and try again."
        exit 1
    }
    
    # Check if database container is running
    $dbRunning = docker ps | Select-String "ai-agent-mysql"
    if (-not $dbRunning) {
        Write-LogInfo "Starting database container..."
        docker-compose up -d
        
        # Initial delay to allow container to start
        Start-Sleep -Seconds 5
        
        # Wait for database to be ready
        Write-LogInfo "Waiting for database to be ready..."
        $maxAttempts = 30
        $attempts = 0
        $dbReady = $false
        
        do {
            Write-Host "." -NoNewline
            $attempts++
            
            try {
                $dbReady = docker exec ai-agent-mysql mysqladmin -h localhost -u root -p123456 ping --silent
            }
            catch {
                Start-Sleep -Seconds 2
                continue
            }
            
            if ($attempts -ge $maxAttempts) {
                Write-LogError "Database failed to become ready after $($maxAttempts * 2) seconds"
                Write-LogError "Please check Docker logs with: docker logs ai-agent-mysql"
                exit 1
            }
        } while (-not $dbReady)
        
        Write-Host ""
        Write-LogSuccess "Database is ready!"
        
        # Additional check for database and user table
        try {
            docker exec ai-agent-mysql mysql -h localhost -u root -p123456 -e "USE ai_agents; SHOW TABLES;" | Out-Null
            Write-LogSuccess "Database schema verified"
        }
        catch {
            Write-LogError "Failed to verify database schema. Error: $_"
            exit 1
        }
    }
    else {
        Write-LogSuccess "Database container is already running"
        
        # Verify database connection even if container is running
        try {
            docker exec ai-agent-mysql mysqladmin -h localhost -u root -p123456 ping --silent | Out-Null
            Write-LogSuccess "Database connection verified"
        }
        catch {
            Write-LogError "Database container is running but not responding. Try restarting with: docker-compose restart"
            exit 1
        }
    }
}

# Check if port is in use and kill process if necessary
function Check-Port {
    param($Port)
    
    $portInUse = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    if ($portInUse) {
        Write-LogWarning "Port $Port is in use, attempting to kill the process..."
        foreach ($connection in $portInUse) {
            $process = Get-Process -Id $connection.OwningProcess -ErrorAction SilentlyContinue
            if ($process) {
                Stop-Process -Id $process.Id -Force
                Write-LogSuccess "Killed process $($process.Id)"
            }
        }
        Start-Sleep -Seconds 2
    }
}

# Check if HTTP service is available
function Test-HttpService {
    param($Host, $Port)
    
    try {
        $response = Invoke-WebRequest -Uri "http://${Host}:${Port}/" -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-LogSuccess "HTTP service check passed"
            return $true
        }
    }
    catch {
        Write-LogWarning "HTTP service might need more time to start"
        return $false
    }
}

# Start application
function Start-App {
    Write-LogInfo "Starting FastAPI application..."
    
    # Check if already running
    if (Test-Path $PidFile) {
        $existingPid = Get-Content $PidFile
        $process = Get-Process -Id $existingPid -ErrorAction SilentlyContinue
        if ($process) {
            Write-LogWarning "Service is already running (PID: $existingPid)"
            Write-LogInfo "API docs available at: http://$($env:HOST):$($env:PORT)/docs"
            return
        }
        else {
            Write-LogInfo "Cleaning up stale PID file"
            Remove-Item $PidFile -Force
        }
    }
    
    # Check and clear port if needed
    Check-Port $env:PORT
    
    Write-LogSuccess "Starting service on port: $env:PORT"
    Write-LogInfo "API docs will be available at: http://$($env:HOST):$($env:PORT)/docs"
    Write-LogInfo "Homepage will be available at: http://$($env:HOST):$($env:PORT)/"
    
    # Start uvicorn directly in the current PowerShell window
    uvicorn app.main:app --reload --host $env:HOST --port $env:PORT
}

# Main execution
function Main {
    Check-Python
    Setup-Venv
    Install-Dependencies
    Check-Env
    Setup-Directories
    Check-DockerAndDb
    Start-App
}

# Run main function
Main 