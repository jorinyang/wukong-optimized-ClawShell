#!/bin/bash
#==============================================================================
# ClawShell v1.0 安装脚本
# 
# 功能: 在类Unix系统上安装ClawShell
# 支持: macOS, Linux
#==============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 检查是否为root用户
check_root() {
    if [ "$EUID" -eq 0 ]; then
        log_warn "建议不要以root用户运行此脚本"
    fi
}

# 检查操作系统
check_os() {
    OS="$(uname -s)"
    case "$OS" in
        Darwin*)
            log_info "检测到 macOS"
            PKG_MANAGER="brew"
            ;;
        Linux*)
            log_info "检测到 Linux"
            if command -v apt-get &> /dev/null; then
                PKG_MANAGER="apt-get"
            elif command -v yum &> /dev/null; then
                PKG_MANAGER="yum"
            else
                log_warn "未检测到支持的包管理器"
            fi
            ;;
        *)
            log_error "不支持的操作系统: $OS"
            exit 1
            ;;
    esac
}

# 安装系统依赖
install_system_deps() {
    log_info "安装系统依赖..."
    
    case "$PKG_MANAGER" in
        brew)
            brew install curl jq git python3
            ;;
        apt-get)
            sudo apt-get update
            sudo apt-get install -y curl jq git python3 python3-pip
            ;;
        yum)
            sudo yum install -y curl jq git python3 python3-pip
            ;;
    esac
    
    log_success "系统依赖安装完成"
}

# 安装Python依赖
install_python_deps() {
    log_info "安装Python依赖..."
    
    # 检查Python版本
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    log_info "Python版本: $PYTHON_VERSION"
    
    # 创建虚拟环境（可选）
    if [ -z "$CLAWSHELL_NO_VENV" ]; then
        if command -v python3 -m venv &> /dev/null; then
            log_info "创建虚拟环境..."
            python3 -m venv venv
            source venv/bin/activate
        fi
    fi
    
    # 安装依赖
    pip3 install --upgrade pip
    pip3 install -r requirements.txt
    
    log_success "Python依赖安装完成"
}

# 安装ClawShell
install_clawshell() {
    log_info "安装ClawShell..."
    
    # 获取安装目录
    INSTALL_DIR="${CLAWSHELL_INSTALL_DIR:-$HOME/.clawshell}"
    
    # 创建安装目录
    mkdir -p "$INSTALL_DIR"
    
    # 复制文件
    log_info "复制文件到 $INSTALL_DIR..."
    rsync -av --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' . "$INSTALL_DIR/"
    
    # 创建符号链接（可选）
    if [ -z "$CLAWSHELL_NO_LINK" ]; then
        mkdir -p "$HOME/bin"
        ln -sf "$INSTALL_DIR/bin/clawshell" "$HOME/bin/clawshell"
        ln -sf "$INSTALL_DIR/bin/clawsync" "$HOME/bin/clawsync"
        
        # 确保HOME/bin在PATH中
        if ! echo "$PATH" | grep -q "$HOME/bin"; then
            log_warn "请将 $HOME/bin 添加到 PATH"
            echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc
        fi
    fi
    
    # 设置权限
    chmod +x "$INSTALL_DIR/bin/"*
    
    log_success "ClawShell安装完成"
}

# 验证安装
verify_installation() {
    log_info "验证安装..."
    
    INSTALL_DIR="${CLAWSHELL_INSTALL_DIR:-$HOME/.clawshell}"
    
    # 检查版本
    if [ -f "$INSTALL_DIR/CLAWSHELL_VERSION" ]; then
        VERSION=$(cat "$INSTALL_DIR/CLAWSHELL_VERSION")
        log_success "ClawShell版本: $VERSION"
    fi
    
    # 检查Python导入
    log_info "测试Python模块导入..."
    cd "$INSTALL_DIR"
    python3 -c "
import sys
sys.path.insert(0, '$INSTALL_DIR')
try:
    from lib.layer1 import HealthMonitor
    print('Layer1: OK')
except Exception as e:
    print(f'Layer1: FAILED - {e}')
try:
    from lib.layer2 import SelfHealing
    print('Layer2: OK')
except Exception as e:
    print(f'Layer2: FAILED - {e}')
try:
    from lib.layer3 import TaskMarket
    print('Layer3: OK')
except Exception as e:
    print(f'Layer3: FAILED - {e}')
try:
    from lib.layer4 import SwarmDiscovery
    print('Layer4: OK')
except Exception as e:
    print(f'Layer4: FAILED - {e}')
" || log_warn "部分模块导入失败"
    
    log_success "验证完成"
}

# 显示帮助信息
show_help() {
    cat << EOF
ClawShell v1.0 安装脚本

用法: $0 [选项]

选项:
    --no-venv     不创建虚拟环境
    --no-link     不创建符号链接
    --install-dir  指定安装目录
    --help        显示此帮助信息

示例:
    $0                    # 默认安装
    $0 --no-venv          # 不使用虚拟环境
    $0 --install-dir /opt  # 安装到指定目录

环境变量:
    CLAWSHELL_NO_VENV     同 --no-venv
    CLAWSHELL_NO_LINK     同 --no-link  
    CLAWSHELL_INSTALL_DIR 指定安装目录

EOF
}

# 主函数
main() {
    echo "============================================"
    echo "  ClawShell v1.0 安装脚本"
    echo "============================================"
    echo ""
    
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help)
                show_help
                exit 0
                ;;
            --no-venv)
                export CLAWSHELL_NO_VENV=1
                shift
                ;;
            --no-link)
                export CLAWSHELL_NO_LINK=1
                shift
                ;;
            --install-dir)
                export CLAWSHELL_INSTALL_DIR="$2"
                shift 2
                ;;
            *)
                log_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    check_root
    check_os
    install_system_deps
    install_python_deps
    install_clawshell
    verify_installation
    
    echo ""
    echo "============================================"
    log_success "安装完成!"
    echo "============================================"
    echo ""
    echo "下一步:"
    echo "  1. 配置环境变量（如需要）"
    echo "  2. 运行 'clawshell status' 查看状态"
    echo "  3. 阅读 README.md 了解使用方法"
    echo ""
}

# 运行主函数
main "$@"
