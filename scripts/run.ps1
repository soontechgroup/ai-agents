# FastAPI AI Agents Project Control Script
# For Windows Development Environment

# Color definitions for output
$Colors = @{
    Info    = 'Cyan'
    Success = 'Green'
    Warning = 'Yellow'
    Error   = 'Red'
}

# Configuration variables
$ScriptPath = $PSCommandPath
$ScriptDir = Split-Path -Parent $ScriptPath
$ProjectDir = Split-Path -Parent $ScriptDir
$Config = @{
    DefaultHost = "127.0.0.1"
    DefaultPort = 8000
    PidFile = Join-Path $ProjectDir "pids/app.pid"
    LogFile = Join-Path $ProjectDir "logs/app.log"
    VenvDir = Join-Path $ProjectDir ".win-venv"
}

# Logging functions
function Write-LogMessage {
    param(
        [string]$Message,
        [string]$Type = "Info"
    )
    Write-Host "[$($Type.ToUpper())] $Message" -ForegroundColor $Colors[$Type]
}

# Function to check Python environment
function Test-PythonEnvironment {
    Write-LogMessage "Checking Python environment..."
    try {
        $pythonVersion = (python --version 2>&1).ToString()
        if (-not $pythonVersion) {
            Write-LogMessage "Python is not installed. Please install Python first." -Type "Error"
            return $false
        }
        Write-LogMessage "Python version: $pythonVersion" -Type "Success"
        return $true
    }
    catch {
        Write-LogMessage "Python is not installed or not in PATH. Please install Python first." -Type "Error"
        return $false
    }
}

# Function to setup virtual environment
function Initialize-VirtualEnvironment {
    Write-LogMessage "Setting up virtual environment..."
    
    if (-not (Test-Path $Config.VenvDir)) {
        Write-LogMessage "Creating virtual environment..."
        python -m venv $Config.VenvDir
        if (-not $?) {
            Write-LogMessage "Failed to create virtual environment." -Type "Error"
            return $false
        }
        Write-LogMessage "Virtual environment created" -Type "Success"
    }
    else {
        Write-LogMessage "Virtual environment already exists"
    }

    & "$($Config.VenvDir)\Scripts\Activate.ps1"
    if (-not $?) {
        Write-LogMessage "Failed to activate virtual environment." -Type "Error"
        return $false
    }
    Write-LogMessage "Virtual environment activated: $env:VIRTUAL_ENV" -Type "Success"
    return $true
}

# Function to install dependencies
function Install-Dependencies {
    Write-LogMessage "Installing project dependencies..."
    
    $requirementsFile = Join-Path $ProjectDir "requirements.txt"
    if (-not (Test-Path $requirementsFile)) {
        Write-LogMessage "requirements.txt file not found" -Type "Error"
        return $false
    }

    python -m pip install --upgrade pip
    if (-not $?) {
        Write-LogMessage "Failed to upgrade pip." -Type "Error"
        return $false
    }

    pip install -r $requirementsFile
    if (-not $?) {
        Write-LogMessage "Failed to install dependencies." -Type "Error"
        return $false
    }

    Write-LogMessage "Dependencies installed" -Type "Success"
    return $true
}

# Function to check environment configuration
function Set-EnvironmentConfig {
    Write-LogMessage "Checking environment configuration..."
    
    $script:ListenHost = if ($env:HOST) { $env:HOST } else { $Config.DefaultHost }
    $script:Port = if ($env:PORT) { $env:PORT } else { $Config.DefaultPort }
    $script:Reload = if ($env:RELOAD) { $env:RELOAD } else { "false" }

    Write-LogMessage "Environment configured - Host: $script:ListenHost, Port: $script:Port" -Type "Success"

    $envFile = Join-Path $ProjectDir ".env"
    if (Test-Path $envFile) {
        Write-LogMessage "Loading .env file..."
        Get-Content $envFile | ForEach-Object {
            if ($_ -match '^([^=]+)=(.*)$') {
                $key = $matches[1].Trim()
                $value = $matches[2].Trim()
                Set-Item "env:$key" $value
            }
        }
        Write-LogMessage "Environment variables loaded" -Type "Success"
    }
    return $true
}

# Function to setup directories
function Initialize-Directories {
    Write-LogMessage "Setting up directories..."
    
    $dirs = @(
        (Join-Path $ProjectDir "pids"),
        (Join-Path $ProjectDir "logs")
    )

    foreach ($dir in $dirs) {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir | Out-Null
        }
    }

    Write-LogMessage "Directories created" -Type "Success"
    return $true
}

# Function to check if process is running
function Test-ProcessRunning {
    param([int]$ProcessId)
    
    try {
        $process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
        return $null -ne $process
    }
    catch {
        return $false
    }
}

# Function to check if port is in use
function Test-PortInUse {
    param([int]$Port)
    
    $inUse = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    return $null -ne $inUse
}

# Function to start application
function Start-FastAPIApp {
    param([switch]$DevMode)

    Write-LogMessage "Starting FastAPI application..."

    # Check if process is already running
    if (Test-Path $Config.PidFile) {
        $storedPid = Get-Content $Config.PidFile
        if (Test-ProcessRunning $storedPid) {
            Write-LogMessage "Service is already running (PID: $storedPid)" -Type "Warning"
            Write-LogMessage "API documentation: http://$($script:ListenHost):$($script:Port)/docs"
            return $true
        }
        else {
            Write-LogMessage "Cleaning up stale PID file"
            Remove-Item $Config.PidFile -Force
        }
    }

    # Check if port is in use
    if (Test-PortInUse $script:Port) {
        Write-LogMessage "Port $script:Port is in use, attempting to free it..." -Type "Warning"
        Stop-Process -Id (Get-NetTCPConnection -LocalPort $script:Port).OwningProcess -Force
        Start-Sleep -Seconds 2
    }

    Write-LogMessage "Starting service on port: $script:Port" -Type "Success"
    Write-LogMessage "API documentation: http://$($script:ListenHost):$($script:Port)/docs"
    Write-LogMessage "Homepage: http://$($script:ListenHost):$($script:Port)/"

    if ($DevMode) {
        # Start directly (not in background) for dev mode
        & uvicorn app.main:app --host $script:ListenHost --port $script:Port --reload --log-level info
    }
    else {
        # Start in background for production mode
        $job = Start-Job -ScriptBlock {
            param($venvDir, $listenHost, $port, $reload)
            & "$venvDir\Scripts\uvicorn.exe" app.main:app --host $listenHost --port $port --reload=$reload --log-level info
        } -ArgumentList $Config.VenvDir, $script:ListenHost, $script:Port, $script:Reload

        $processId = $job.Id
        $processId | Set-Content $Config.PidFile

        Write-LogMessage "Service started successfully (PID: $processId)" -Type "Success"
        Write-LogMessage "Log file: $($Config.LogFile)" -Type "Info"
    }

    return $true
}

# Function to stop application
function Stop-FastAPIApp {
    Write-LogMessage "Stopping FastAPI application..."

    if (-not (Test-Path $Config.PidFile)) {
        Write-LogMessage "PID file not found, service might not be running" -Type "Warning"
        return $true
    }

    $storedPid = Get-Content $Config.PidFile
    if (-not (Test-ProcessRunning $storedPid)) {
        Write-LogMessage "Process not found, cleaning up PID file" -Type "Warning"
        Remove-Item $Config.PidFile -Force
        return $true
    }

    Write-LogMessage "Stopping process (PID: $storedPid)..."
    Stop-Process -Id $storedPid -Force
    Remove-Item $Config.PidFile -Force
    Write-LogMessage "Service stopped" -Type "Success"
    return $true
}

# Function to show status
function Get-ServiceStatus {
    Write-LogMessage "Checking service status..."

    if (-not (Test-Path $Config.PidFile)) {
        Write-LogMessage "PID file not found, service is not running" -Type "Error"
        return $false
    }

    $storedPid = Get-Content $Config.PidFile
    if (Test-ProcessRunning $storedPid) {
        Write-LogMessage "Service is running (PID: $storedPid)" -Type "Success"
        
        if (Test-PortInUse $script:Port) {
            Write-LogMessage "Port $script:Port is listening" -Type "Success"
        }
        else {
            Write-LogMessage "Port $script:Port is not listening" -Type "Warning"
        }

        Write-Host "`nProcess information:"
        Get-Process -Id $storedPid | Format-List Id, ProcessName, Path, StartTime

        Write-LogMessage "Service URLs:"
        Write-Host "  Homepage: http://$($script:ListenHost):$($script:Port)/"
        Write-Host "  API docs: http://$($script:ListenHost):$($script:Port)/docs"
        return $true
    }
    else {
        Write-LogMessage "Service is not running" -Type "Error"
        Remove-Item $Config.PidFile -Force
        return $false
    }
}

# Function to show logs
function Show-ServiceLogs {
    param([switch]$Tail)

    Write-LogMessage "Showing service logs..."
    
    if (-not (Test-Path $Config.LogFile)) {
        Write-LogMessage "Log file does not exist: $($Config.LogFile)" -Type "Warning"
        return
    }

    Write-Host "`n=== Application logs (last 50 lines) ===`n"
    if ($Tail) {
        Get-Content $Config.LogFile -Tail 50 -Wait
    }
    else {
        Get-Content $Config.LogFile -Tail 50
    }
}

# Function to cleanup
function Remove-ServiceFiles {
    param([switch]$All)

    Write-LogMessage "Cleaning up temporary files..."
    
    if (Test-Path $Config.PidFile) {
        Remove-Item $Config.PidFile -Force
        Write-LogMessage "PID file cleaned up" -Type "Success"
    }

    if ($All -and (Test-Path $Config.LogFile)) {
        Remove-Item $Config.LogFile -Force
        Write-LogMessage "Log file cleaned up" -Type "Success"
    }
}

# Function to show help
function Show-Help {
    Write-Host "FastAPI AI Agents Project Control Script`n"
    Write-Host "Usage: $($MyInvocation.MyCommand.Name) [command] [options]`n"
    Write-Host "Commands:"
    Write-Host "  start     - Start service (production mode)"
    Write-Host "  stop      - Stop service"
    Write-Host "  restart   - Restart service"
    Write-Host "  status    - Check service status"
    Write-Host "  logs      - Show logs (last 50 lines)"
    Write-Host "  tail      - Tail logs in real-time"
    Write-Host "  dev       - Start development mode (hot reload)"
    Write-Host "  cleanup   - Clean up PID files"
    Write-Host "  help      - Show this help message`n"
    Write-Host "Environment variables:"
    Write-Host "  HOST      - Service listen address (default: $($Config.DefaultHost))"
    Write-Host "  PORT      - Service listen port (default: $($Config.DefaultPort))"
    Write-Host "  RELOAD    - Enable hot reload (default: false)`n"
    Write-Host "Examples:"
    Write-Host "  .\$($MyInvocation.MyCommand.Name) start              # Start service"
    Write-Host "  .\$($MyInvocation.MyCommand.Name) dev                # Start development mode"
    Write-Host "  `$env:PORT=9000; .\$($MyInvocation.MyCommand.Name) start    # Start on specific port"
    Write-Host "  `$env:HOST='0.0.0.0'; .\$($MyInvocation.MyCommand.Name) start  # Start on specific host"
}

# Main execution
function Start-Main {
    param(
        [Parameter(Position=0)]
        [string]$Command = "help",
        
        [Parameter(ValueFromRemainingArguments=$true)]
        [string[]]$Arguments
    )

    # Change to project directory
    Set-Location $ProjectDir

    switch ($Command.ToLower()) {
        "start" {
            if (-not (Test-PythonEnvironment)) { return }
            if (-not (Initialize-VirtualEnvironment)) { return }
            if (-not (Install-Dependencies)) { return }
            if (-not (Set-EnvironmentConfig)) { return }
            if (-not (Initialize-Directories)) { return }
            Start-FastAPIApp
        }
        "stop" { 
            Stop-FastAPIApp 
        }
        "restart" {
            Stop-FastAPIApp
            Start-Sleep -Seconds 2
            if (-not (Set-EnvironmentConfig)) { return }
            Start-FastAPIApp
        }
        "status" { 
            if (-not (Set-EnvironmentConfig)) { return }
            Get-ServiceStatus 
        }
        "logs" { 
            Show-ServiceLogs 
        }
        "tail" { 
            Show-ServiceLogs -Tail 
        }
        "dev" {
            if (-not (Test-PythonEnvironment)) { return }
            if (-not (Initialize-VirtualEnvironment)) { return }
            if (-not (Install-Dependencies)) { return }
            $env:RELOAD = "true"
            $env:HOST = "127.0.0.1"
            $env:PORT = "8000"
            if (-not (Set-EnvironmentConfig)) { return }
            if (-not (Initialize-Directories)) { return }
            Start-FastAPIApp -DevMode
        }
        "cleanup" {
            $all = $Arguments -contains "all"
            Remove-ServiceFiles -All:$all
        }
        "help" { 
            Show-Help 
        }
        default {
            Write-LogMessage "Unknown command: $Command" -Type "Error"
            Write-Host ""
            Show-Help
        }
    }
}

# Start execution
Start-Main @args 