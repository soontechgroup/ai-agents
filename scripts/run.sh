#!/bin/bash

# FastAPI AI Agents 项目控制脚本
# 适用于生产环境和开发环境

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

log_info "项目目录: $PROJECT_DIR"

# 切换到项目目录
cd "$PROJECT_DIR"

# 配置变量
DEFAULT_HOST="0.0.0.0"
DEFAULT_PORT="8000"
PID_FILE="pids/app.pid"
LOG_FILE="logs/app.log"
VENV_DIR=".venv"

# 检查Python环境
check_python() {
    log_info "检查Python环境..."
    
    # 检查Python是否安装
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 未安装，请先安装Python3"
        exit 1
    fi
    
    # 检查Python版本
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    log_success "Python版本: $PYTHON_VERSION"
    
    # 检查Python版本是否满足要求（至少3.8）
    if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
        log_error "Python版本需要3.8或更高版本"
        exit 1
    fi
}

# 设置虚拟环境
setup_venv() {
    log_info "设置虚拟环境..."
    
    if [ ! -d "$VENV_DIR" ]; then
        log_info "创建虚拟环境..."
        python3 -m venv "$VENV_DIR"
        log_success "虚拟环境创建完成"
    else
        log_info "虚拟环境已存在"
    fi
    
    # 激活虚拟环境
    log_info "激活虚拟环境..."
    source "$VENV_DIR/bin/activate"
    
    # 显示Python路径
    log_success "虚拟环境已激活: $(which python)"
}

# 安装依赖
install_dependencies() {
    log_info "安装项目依赖..."
    
    if [ ! -f "requirements.txt" ]; then
        log_error "requirements.txt 文件不存在"
        exit 1
    fi
    
    # 升级pip
    python -m pip install --upgrade pip
    
    # 安装依赖
    pip install -r requirements.txt
    log_success "依赖安装完成"
}

# 检查环境变量配置
check_env() {
    log_info "检查环境配置..."
    
    # 设置默认环境变量
    export HOST="${HOST:-$DEFAULT_HOST}"
    export PORT="${PORT:-$DEFAULT_PORT}"
    export RELOAD="${RELOAD:-false}"
    export ENVIRONMENT="${ENVIRONMENT:-dev}"  # 默认开发环境
    
    log_success "环境配置完成 - Host: $HOST, Port: $PORT, Environment: $ENVIRONMENT"
    
    # 根据环境变量加载对应的配置文件
    case "$ENVIRONMENT" in
        "dev"|"development")
            ENV_FILE=".env.dev"
            ;;
        "test")
            ENV_FILE=".env.test"
            ;;
        "staging")
            ENV_FILE=".env.staging"
            ;;
        "prod"|"production")
            ENV_FILE=".env.prod"
            ;;
        *)
            ENV_FILE=".env"
            ;;
    esac
    
    if [ -f "$ENV_FILE" ]; then
        log_info "加载环境配置文件: $ENV_FILE"
        set -a  # 自动导出变量
        source "$ENV_FILE"
        set +a
        log_success "环境变量已加载"
    else
        log_warning "环境配置文件不存在: $ENV_FILE，使用默认配置"
        # 尝试加载默认的 .env 文件
        if [ -f ".env" ]; then
            log_info "加载默认配置文件: .env"
            set -a
            source .env
            set +a
        fi
    fi
}

# 创建必要目录
setup_directories() {
    log_info "设置必要目录..."
    
    # 创建pids目录
    if [ ! -d "pids" ]; then
        mkdir -p pids
        log_success "PID目录创建完成"
    fi
    
    # 创建logs目录
    if [ ! -d "logs" ]; then
        mkdir -p logs
        log_success "日志目录创建完成"
    fi
}

# 启动应用
start_app() {
    log_info "启动FastAPI应用..."
    
    # 检查是否已经在运行
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            log_warning "服务已在运行 (PID: $PID)"
            log_info "API文档地址: http://$HOST:$PORT/docs"
            return 0
        else
            log_info "清理过期的PID文件"
            rm -f "$PID_FILE"
        fi
    fi
    
    # 检查端口占用
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        log_warning "端口 $PORT 被占用，尝试终止占用进程..."
        lsof -ti:$PORT | xargs kill -9 2>/dev/null || true
        sleep 2
    fi
    
    log_success "正在启动服务，端口: $PORT"
    log_info "API文档地址: http://$HOST:$PORT/docs"
    log_info "主页地址: http://$HOST:$PORT/"
    
    # 激活虚拟环境并后台启动应用
    source "$VENV_DIR/bin/activate"
    nohup uvicorn app.main:app --host "$HOST" --port "$PORT" --reload="$RELOAD" --log-level info > "$LOG_FILE" 2>&1 &
    APP_PID=$!
    
    # 保存PID
    echo $APP_PID > "$PID_FILE"
    
    # 等待服务启动
    sleep 3
    
    # 检查服务是否启动成功
    if ps -p $APP_PID > /dev/null 2>&1; then
        log_success "服务启动成功 (PID: $APP_PID)"
        log_info "日志文件: $LOG_FILE"
        
        # 尝试检查HTTP服务是否可用
        sleep 2
        if curl -s http://$HOST:$PORT/ > /dev/null 2>&1; then
            log_success "HTTP服务检查通过"
        else
            log_warning "HTTP服务可能需要更多时间启动"
        fi
    else
        log_error "服务启动失败"
        rm -f "$PID_FILE"
        if [ -f "$LOG_FILE" ]; then
            log_error "错误日志:"
            tail -n 10 "$LOG_FILE"
        fi
        exit 1
    fi
}

# 停止应用
stop_app() {
    log_info "停止FastAPI应用..."
    
    if [ ! -f "$PID_FILE" ]; then
        log_warning "PID文件不存在，服务可能未运行"
        
        # 尝试通过端口查找并终止进程
        if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
            log_info "发现端口占用，尝试终止进程..."
            lsof -ti:$PORT | xargs kill -TERM 2>/dev/null || true
            sleep 2
            # 如果还在运行，强制终止
            if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
                lsof -ti:$PORT | xargs kill -9 2>/dev/null || true
            fi
            log_success "端口进程已终止"
        fi
        return 0
    fi
    
    PID=$(cat "$PID_FILE")
    
    if ! ps -p $PID > /dev/null 2>&1; then
        log_warning "进程不存在，清理PID文件"
        rm -f "$PID_FILE"
        return 0
    fi
    
    log_info "停止进程 (PID: $PID)..."
    kill -TERM $PID
    
    # 等待进程优雅退出
    for i in {1..10}; do
        if ! ps -p $PID > /dev/null 2>&1; then
            break
        fi
        sleep 1
    done
    
    # 如果进程仍在运行，强制终止
    if ps -p $PID > /dev/null 2>&1; then
        log_warning "强制终止进程..."
        kill -KILL $PID
        sleep 1
    fi
    
    rm -f "$PID_FILE"
    log_success "服务已停止"
}

# 检查服务状态
check_status() {
    log_info "检查服务状态..."
    
    if [ ! -f "$PID_FILE" ]; then
        log_error "PID文件不存在，服务未运行"
        return 1
    fi
    
    PID=$(cat "$PID_FILE")
    
    if ps -p $PID > /dev/null 2>&1; then
        log_success "服务正在运行 (PID: $PID)"
        
        # 检查端口监听
        if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
            log_success "端口 $PORT 正在监听"
        else
            log_warning "端口 $PORT 未在监听"
        fi
        
        # 显示进程信息
        echo "进程信息:"
        ps -p $PID -o pid,ppid,cmd --no-headers 2>/dev/null || ps -p $PID
        
        # 显示服务地址
        log_info "服务地址:"
        echo "  主页: http://$HOST:$PORT/"
        echo "  API文档: http://$HOST:$PORT/docs"
        
        return 0
    else
        log_error "服务未运行"
        rm -f "$PID_FILE"
        return 1
    fi
}

# 重启服务
restart_app() {
    log_info "重启服务..."
    stop_app
    sleep 2
    
    # 重新设置环境并启动
    check_env
    start_app
}

# 显示日志
show_logs() {
    log_info "显示服务日志..."
    
    if [ -f "$LOG_FILE" ]; then
        echo "=== 应用日志 (最后50行) ==="
        tail -n 50 "$LOG_FILE"
    else
        log_warning "日志文件不存在: $LOG_FILE"
    fi
}

# 实时查看日志
tail_logs() {
    log_info "实时查看服务日志 (按Ctrl+C退出)..."
    
    if [ -f "$LOG_FILE" ]; then
        tail -f "$LOG_FILE"
    else
        log_warning "日志文件不存在: $LOG_FILE"
    fi
}

# 启动服务（完整流程）
start_service() {
    log_info "开始启动 FastAPI AI Agents 服务..."
    echo "=================================="
    
    check_python
    setup_venv
    install_dependencies
    check_env
    setup_directories
    
    echo "=================================="
    log_success "环境准备完成，正在启动服务..."
    
    start_app
}

# 开发模式启动
dev_start() {
    log_info "开发模式启动..."
    export RELOAD="true"
    export HOST="${HOST:-127.0.0.1}"
    export PORT="${PORT:-8000}"
    
    check_python
    setup_venv
    check_env
    setup_directories
    
    # 激活虚拟环境并直接运行（前台模式）
    source "$VENV_DIR/bin/activate"
    log_success "开发模式启动，热重载已开启"
    log_info "API文档地址: http://$HOST:$PORT/docs"
    uvicorn app.main:app --host "$HOST" --port "$PORT" --reload --log-level info
}

# 清理函数
cleanup() {
    log_info "清理临时文件..."
    
    # 清理PID文件
    if [ -f "$PID_FILE" ]; then
        rm -f "$PID_FILE"
        log_success "PID文件已清理"
    fi
    
    # 可选：清理日志文件
    if [ "$1" = "all" ]; then
        if [ -f "$LOG_FILE" ]; then
            rm -f "$LOG_FILE"
            log_success "日志文件已清理"
        fi
    fi
}

# 显示帮助信息
show_help() {
    echo "FastAPI AI Agents 项目控制脚本"
    echo ""
    echo "用法: $0 [命令] [选项]"
    echo ""
    echo "命令:"
    echo "  start     - 启动服务 (生产模式)"
    echo "  stop      - 停止服务"
    echo "  restart   - 重启服务"
    echo "  status    - 检查服务状态"
    echo "  logs      - 显示日志 (最后50行)"
    echo "  tail      - 实时查看日志"
    echo "  dev       - 开发模式启动 (热重载)"
    echo "  cleanup   - 清理PID文件"
    echo "  help      - 显示帮助信息"
    echo ""
    echo "环境变量:"
    echo "  HOST        - 服务监听地址 (默认: $DEFAULT_HOST)"
    echo "  PORT        - 服务监听端口 (默认: $DEFAULT_PORT)"
    echo "  RELOAD      - 是否启用热重载 (默认: false)"
    echo "  ENVIRONMENT - 运行环境 (默认: dev)"
    echo "                可选值: dev, development, test, staging, prod, production"
    echo ""
    echo "示例:"
    echo "  $0 start                           # 启动服务 (默认dev环境)"
    echo "  $0 dev                             # 开发模式启动"
    echo "  PORT=9000 $0 start                 # 指定端口启动"
    echo "  HOST=127.0.0.1 $0 start            # 指定监听地址启动"
    echo "  ENVIRONMENT=prod $0 start          # 生产环境启动"
    echo "  ENVIRONMENT=staging $0 start       # 预发环境启动"
}

# 主函数
main() {
    case "${1:-help}" in
        start)
            start_service
            ;;
        stop)
            stop_app
            ;;
        restart)
            restart_app
            ;;
        status)
            check_status
            ;;
        logs)
            show_logs
            ;;
        tail)
            tail_logs
            ;;
        dev)
            dev_start
            ;;
        cleanup)
            cleanup "${2:-}"
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "未知命令: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# 信号处理
cleanup_on_exit() {
    log_info "正在清理..."
    exit 0
}

trap cleanup_on_exit SIGINT SIGTERM

# 执行主函数
main "$@" 