#!/bin/bash

echo "开始安装新闻爬虫程序..."

# 检查Python版本
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python版本: $python_version"

# 创建虚拟环境
echo "创建Python虚拟环境..."
python3 -m venv venv
source venv/bin/activate

# 安装所有Python依赖
echo "安装Python依赖..."
pip install -r requirements.txt

# 安装Playwright浏览器
echo "安装Playwright浏览器..."
playwright install chromium

# 安装系统依赖
echo "安装系统依赖..."
if [ -x "$(command -v apt-get)" ]; then
    echo "检测到apt包管理器，使用apt安装依赖..."
    sudo apt-get update
    sudo apt-get install -y \
        libglib2.0-0 \
        libnss3 \
        libnspr4 \
        libatk1.0-0 \
        libatk-bridge2.0-0 \
        libatspi2.0-0 \
        libxcomposite1 \
        libxdamage1 \
        libxfixes3 \
        libxrandr2 \
        libgbm1 \
        libxkbcommon0 \
        libasound2 \
        libssl-dev \
        zlib1g-dev \
        libbz2-dev \
        libffi-dev
elif [ -x "$(command -v playwright)" ]; then
    echo "使用playwright安装依赖..."
    sudo playwright install-deps
else
    echo "警告: 无法自动安装系统依赖，请手动安装。"
    echo "您可以运行以下命令安装依赖:"
    echo "sudo apt-get install -y libglib2.0-0 libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libatspi2.0-0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libxkbcommon0 libasound2 libssl-dev zlib1g-dev libbz2-dev libffi-dev"
fi

# 创建必要的目录
echo "创建必要的目录..."
mkdir -p news_crawler/data
mkdir -p logs

# 创建启动脚本
echo "创建启动脚本..."
cat > start.sh << 'EOF'
#!/bin/bash
source venv/bin/activate
python app.py
EOF

chmod +x start.sh

echo "安装完成！"
echo "运行 './start.sh' 启动程序" 