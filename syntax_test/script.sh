#!/bin/bash

# LitheServer 部署和管理脚本
# Shell 语法高亮测试文件
# 
# 作者: xyanmi
# 日期: 2024-03-15
# 版本: 1.0

set -euo pipefail  # 启用严格模式

# 颜色定义
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly PURPLE='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly WHITE='\033[1;37m'
readonly NC='\033[0m' # No Color

# 常量定义
readonly SCRIPT_NAME="$(basename "$0")"
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_NAME="LitheServer"
readonly DEFAULT_PORT=8080
readonly CONFIG_FILE="config.yaml"
readonly LOG_FILE="LitheServer.log"
readonly PID_FILE="LitheServer.pid"

# 全局变量
VERBOSE=false
DRY_RUN=false
FORCE=false
ENVIRONMENT="development"
PORT=${DEFAULT_PORT}

# 函数：打印彩色消息
print_message() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case "$level" in
        "info")
            echo -e "${timestamp} ${CYAN}[INFO]${NC} $message"
            ;;
        "warn")
            echo -e "${timestamp} ${YELLOW}[WARN]${NC} $message" >&2
            ;;
        "error")
            echo -e "${timestamp} ${RED}[ERROR]${NC} $message" >&2
            ;;
        "success")
            echo -e "${timestamp} ${GREEN}[SUCCESS]${NC} $message"
            ;;
        "debug")
            if [[ "$VERBOSE" == true ]]; then
                echo -e "${timestamp} ${PURPLE}[DEBUG]${NC} $message"
            fi
            ;;
        *)
            echo -e "${timestamp} $message"
            ;;
    esac
}

# 函数：显示帮助信息
show_help() {
    cat << EOF
${PROJECT_NAME} 管理脚本

用法: $SCRIPT_NAME [选项] <命令> [参数]

命令:
    start           启动服务器
    stop            停止服务器
    restart         重启服务器
    status          查看服务器状态
    deploy          部署应用程序
    backup          备份数据
    restore         恢复数据
    logs            查看日志
    test            运行测试
    health          健康检查

选项:
    -h, --help      显示此帮助信息
    -v, --verbose   详细输出模式
    -n, --dry-run   仅显示将要执行的操作（不实际执行）
    -f, --force     强制执行操作
    -e, --env ENV   指定环境 (development|staging|production)
    -p, --port PORT 指定端口号 (默认: $DEFAULT_PORT)

示例:
    $SCRIPT_NAME start
    $SCRIPT_NAME start --port 8090 --env production
    $SCRIPT_NAME stop --force
    $SCRIPT_NAME deploy --env staging
    $SCRIPT_NAME logs --verbose

EOF
}

# 函数：检查依赖
check_dependencies() {
    local dependencies=("python3" "pip" "curl" "jq")
    local missing_deps=()
    
    print_message "info" "检查系统依赖..."
    
    for dep in "${dependencies[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            missing_deps+=("$dep")
        else
            print_message "debug" "✓ $dep 已安装"
        fi
    done
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        print_message "error" "缺少以下依赖: ${missing_deps[*]}"
        print_message "info" "请安装缺少的依赖后重试"
        exit 1
    fi
    
    print_message "success" "所有依赖检查通过"
}

# 函数：检查服务器状态
check_server_status() {
    local port="$1"
    
    if [[ -f "$PID_FILE" ]]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            print_message "info" "服务器正在运行 (PID: $pid, Port: $port)"
            return 0
        else
            print_message "warn" "PID 文件存在但进程不在运行，清理 PID 文件"
            rm -f "$PID_FILE"
        fi
    fi
    
    # 检查端口是否被占用
    if netstat -tuln 2>/dev/null | grep -q ":$port "; then
        print_message "warn" "端口 $port 被其他进程占用"
        return 1
    fi
    
    print_message "info" "服务器未运行"
    return 2
}

# 函数：启动服务器
start_server() {
    local port="$1"
    local env="$2"
    
    print_message "info" "启动 $PROJECT_NAME 服务器..."
    print_message "debug" "环境: $env, 端口: $port"
    
    # 检查服务器状态
    if check_server_status "$port"; then
        print_message "warn" "服务器已在运行"
        return 0
    fi
    
    # 创建必要的目录
    mkdir -p logs
    
    # 构建启动命令
    local cmd="python3 -m LitheServer --port $port --host 0.0.0.0"
    
    if [[ "$env" == "production" ]]; then
        cmd="$cmd --no-debug"
    fi
    
    if [[ "$DRY_RUN" == true ]]; then
        print_message "info" "将要执行: $cmd"
        return 0
    fi
    
    # 启动服务器
    nohup $cmd > "$LOG_FILE" 2>&1 &
    local pid=$!
    echo "$pid" > "$PID_FILE"
    
    # 等待服务器启动
    sleep 2
    
    if ps -p "$pid" > /dev/null 2>&1; then
        print_message "success" "🚀 服务器启动成功 (PID: $pid)"
        print_message "info" "🌐 访问地址: http://localhost:$port"
        print_message "info" "📝 日志文件: $LOG_FILE"
    else
        print_message "error" "服务器启动失败"
        rm -f "$PID_FILE"
        exit 1
    fi
}

# 函数：停止服务器
stop_server() {
    print_message "info" "停止 $PROJECT_NAME 服务器..."
    
    if [[ ! -f "$PID_FILE" ]]; then
        print_message "warn" "PID 文件不存在，服务器可能未运行"
        return 0
    fi
    
    local pid=$(cat "$PID_FILE")
    
    if ! ps -p "$pid" > /dev/null 2>&1; then
        print_message "warn" "进程 $pid 不存在"
        rm -f "$PID_FILE"
        return 0
    fi
    
    if [[ "$DRY_RUN" == true ]]; then
        print_message "info" "将要停止进程: $pid"
        return 0
    fi
    
    # 尝试优雅关闭
    print_message "debug" "发送 SIGTERM 信号到进程 $pid"
    kill -TERM "$pid" 2>/dev/null || true
    
    # 等待进程结束
    local count=0
    while ps -p "$pid" > /dev/null 2>&1 && [[ $count -lt 10 ]]; do
        sleep 1
        ((count++))
    done
    
    # 如果进程还在运行，强制杀死
    if ps -p "$pid" > /dev/null 2>&1; then
        if [[ "$FORCE" == true ]]; then
            print_message "warn" "强制杀死进程 $pid"
            kill -KILL "$pid" 2>/dev/null || true
        else
            print_message "error" "进程 $pid 无法正常停止，使用 --force 强制停止"
            exit 1
        fi
    fi
    
    rm -f "$PID_FILE"
    print_message "success" "👋 服务器已停止"
}

# 函数：重启服务器
restart_server() {
    local port="$1"
    local env="$2"
    
    print_message "info" "重启 $PROJECT_NAME 服务器..."
    stop_server
    sleep 1
    start_server "$port" "$env"
}

# 函数：显示服务器状态
show_status() {
    local port="$1"
    
    print_message "info" "检查 $PROJECT_NAME 状态..."
    
    local status_code
    check_server_status "$port"
    status_code=$?
    
    case $status_code in
        0)
            print_message "success" "✅ 服务器运行正常"
            ;;
        1)
            print_message "warn" "⚠️ 端口冲突"
            ;;
        2)
            print_message "error" "❌ 服务器未运行"
            ;;
    esac
    
    # 显示系统信息
    print_message "info" "系统信息:"
    echo "  操作系统: $(uname -s)"
    echo "  内核版本: $(uname -r)"
    echo "  Python 版本: $(python3 --version)"
    echo "  当前时间: $(date)"
    echo "  运行时长: $(uptime)"
}

# 函数：部署应用
deploy_app() {
    local env="$1"
    
    print_message "info" "部署 $PROJECT_NAME 到 $env 环境..."
    
    # 检查Git状态
    if [[ -d ".git" ]]; then
        local git_status=$(git status --porcelain)
        if [[ -n "$git_status" && "$FORCE" != true ]]; then
            print_message "error" "工作目录有未提交的更改，使用 --force 忽略"
            exit 1
        fi
        
        local current_branch=$(git rev-parse --abbrev-ref HEAD)
        local commit_hash=$(git rev-parse --short HEAD)
        print_message "info" "当前分支: $current_branch ($commit_hash)"
    fi
    
    # 安装依赖
    if [[ -f "requirements.txt" ]]; then
        print_message "info" "安装 Python 依赖..."
        if [[ "$DRY_RUN" != true ]]; then
            pip install -r requirements.txt
        fi
    fi
    
    # 运行测试
    if [[ "$env" != "development" ]]; then
        print_message "info" "运行测试..."
        run_tests
    fi
    
    # 备份数据
    if [[ "$env" == "production" ]]; then
        print_message "info" "备份生产数据..."
        backup_data
    fi
    
    # 重启服务器
    restart_server "$PORT" "$env"
    
    print_message "success" "🎉 部署完成!"
}

# 函数：运行测试
run_tests() {
    print_message "info" "运行测试套件..."
    
    local test_commands=(
        "python3 -m pytest tests/ -v"
        "python3 -m flake8 LitheServer/"
        "python3 -m mypy LitheServer/"
    )
    
    for cmd in "${test_commands[@]}"; do
        print_message "debug" "执行: $cmd"
        if [[ "$DRY_RUN" != true ]]; then
            if ! eval "$cmd"; then
                print_message "error" "测试失败: $cmd"
                exit 1
            fi
        fi
    done
    
    print_message "success" "✅ 所有测试通过"
}

# 函数：备份数据
backup_data() {
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local backup_dir="backups"
    local backup_file="$backup_dir/backup_$timestamp.tar.gz"
    
    print_message "info" "创建数据备份..."
    
    mkdir -p "$backup_dir"
    
    local backup_items=("data" "logs" "$CONFIG_FILE")
    local tar_cmd="tar -czf $backup_file"
    
    for item in "${backup_items[@]}"; do
        if [[ -e "$item" ]]; then
            tar_cmd="$tar_cmd $item"
        fi
    done
    
    if [[ "$DRY_RUN" != true ]]; then
        eval "$tar_cmd"
        print_message "success" "备份已创建: $backup_file"
    else
        print_message "info" "将要执行: $tar_cmd"
    fi
}

# 函数：查看日志
show_logs() {
    local lines="${1:-50}"
    
    if [[ ! -f "$LOG_FILE" ]]; then
        print_message "warn" "日志文件不存在: $LOG_FILE"
        return 1
    fi
    
    print_message "info" "显示最近 $lines 行日志:"
    echo "----------------------------------------"
    tail -n "$lines" "$LOG_FILE"
    echo "----------------------------------------"
    
    if [[ "$VERBOSE" == true ]]; then
        print_message "info" "实时跟踪日志 (Ctrl+C 退出):"
        tail -f "$LOG_FILE"
    fi
}

# 函数：健康检查
health_check() {
    local port="$1"
    local url="http://localhost:$port/health"
    
    print_message "info" "执行健康检查..."
    
    if ! command -v curl &> /dev/null; then
        print_message "error" "curl 未安装，无法执行健康检查"
        exit 1
    fi
    
    local response=$(curl -s -w "%{http_code}" -o /dev/null "$url" 2>/dev/null || echo "000")
    
    case "$response" in
        "200")
            print_message "success" "✅ 健康检查通过"
            ;;
        "000")
            print_message "error" "❌ 无法连接到服务器"
            exit 1
            ;;
        *)
            print_message "error" "❌ 健康检查失败 (HTTP $response)"
            exit 1
            ;;
    esac
}

# 函数：解析命令行参数
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -n|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -f|--force)
                FORCE=true
                shift
                ;;
            -e|--env)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -p|--port)
                PORT="$2"
                shift 2
                ;;
            start|stop|restart|status|deploy|backup|restore|logs|test|health)
                COMMAND="$1"
                shift
                ;;
            *)
                print_message "error" "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# 主函数
main() {
    local command="${COMMAND:-}"
    
    # 显示脚本信息
    if [[ "$VERBOSE" == true ]]; then
        print_message "debug" "脚本路径: $SCRIPT_DIR/$SCRIPT_NAME"
        print_message "debug" "环境: $ENVIRONMENT"
        print_message "debug" "端口: $PORT"
        print_message "debug" "详细模式: $VERBOSE"
        print_message "debug" "预览模式: $DRY_RUN"
    fi
    
    # 检查依赖
    check_dependencies
    
    # 执行命令
    case "$command" in
        "start")
            start_server "$PORT" "$ENVIRONMENT"
            ;;
        "stop")
            stop_server
            ;;
        "restart")
            restart_server "$PORT" "$ENVIRONMENT"
            ;;
        "status")
            show_status "$PORT"
            ;;
        "deploy")
            deploy_app "$ENVIRONMENT"
            ;;
        "backup")
            backup_data
            ;;
        "logs")
            show_logs
            ;;
        "test")
            run_tests
            ;;
        "health")
            health_check "$PORT"
            ;;
        "")
            print_message "error" "请指定命令"
            show_help
            exit 1
            ;;
        *)
            print_message "error" "未知命令: $command"
            show_help
            exit 1
            ;;
    esac
}

# 脚本入口点
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    parse_arguments "$@"
    main
fi 