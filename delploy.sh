#!/bin/bash
# 部署脚本 - 在本地执行，将代码同步到远程服务器并重启服务

set -e  # 遇到错误立即退出

# ---------- 配置变量（请根据实际情况修改）----------
REMOTE_USER="root"
REMOTE_HOST="139.224.43.78"
REMOTE_DIR="/home/admin/python_project"        # 远程项目根目录
REMOTE_VENV_DIR="$REMOTE_DIR/venv"       # 远程虚拟环境路径
SERVICE_NAME="myapp"                      # systemd 服务名
# -------------------------------------------------

# 检查必要工具
command -v pipreqs >/dev/null 2>&1 || { echo "需要 pipreqs，请安装: pip install pipreqs"; exit 1; }
command -v rsync >/dev/null 2>&1 || { echo "需要 rsync，请安装"; exit 1; }

echo "1. 生成依赖文件 requirements.txt (基于当前代码)"
# pipreqs ./ --force

echo "2. 同步代码到远程服务器 (排除不需要的文件)"
rsync -avz --delete \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    --exclude='.env' \
    --exclude='*.sqlite3' \
    --exclude='*.sqlite3-shm' \
    --exclude='*.sqlite3-wal' \
    --exclude='*.log' \
    --exclude='.vscode' \
    --exclude='dist' \
    --exclude='build' \
    --exclude='.gitignore' \
    ./ "$REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/"

echo "3. 远程更新虚拟环境和重启服务"
#ssh "$REMOTE_USER@$REMOTE_HOST" bash -s << EOF
#    set -e
#    cd "$REMOTE_DIR"
#    echo "   - 检查/创建虚拟环境"
#    if [ ! -d "venv" ]; then
#        python3 -m venv venv
#    fi
#    source venv/bin/activate
#    echo "   - 安装/更新依赖"
#    pip install -r requirements.txt
#    echo "   - 重启服务 (需sudo权限)"
#    # 如果 sudo 需要密码，请提前配置 NOPASSWD 或使用其他方式
#    sudo systemctl restart "$SERVICE_NAME"
#    echo "   - 服务状态"
#    sudo systemctl status "$SERVICE_NAME" --no-pager
#EOF

echo "✅ 部署完成"