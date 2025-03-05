# News Crawler

一个强大的新闻爬虫系统，支持多个新闻源的实时新闻抓取。

## 功能特点

- 支持多个新闻源（Fox News等）
- 实时抓取最新新闻
- 自动提取新闻标题、摘要和正文
- Web界面支持任务管理和查看
- 异步爬虫设计，高效且稳定

## 安装要求

- Python 3.11+
- 虚拟环境 (推荐)

## 快速开始

1. 克隆仓库：
```bash
git clone https://github.com/zjh459/news-crawler.git
cd news-crawler
```

2. 创建并激活虚拟环境：
```bash
python -m venv news_crawler_env
source news_crawler_env/bin/activate  # Linux/Mac
# 或
news_crawler_env\Scripts\activate  # Windows
```

3. 安装依赖：
```bash
pip install -r requirements.txt
```

4. 配置环境：
```bash
# 复制示例配置文件
cp .env.example .env
cp news_crawler/config/deepseek_config.example.py news_crawler/config/deepseek_config.py

# 编辑配置文件，设置必要的参数
# - 在 .env 文件中设置环境变量
# - 在 deepseek_config.py 中设置 API 密钥
```

5. 启动应用：
```bash
./entrypoint.sh
```

## 配置

### 环境变量
复制 `.env.example` 到 `.env` 并设置以下变量：
- `OPENROUTER_API_KEY`: OpenRouter API 密钥
- `DEBUG`: 调试模式 (True/False)
- `PORT`: 服务端口
- `HOST`: 服务地址
- `DB_PATH`: 数据库路径

### DeepSeek 配置
复制 `news_crawler/config/deepseek_config.example.py` 到 `deepseek_config.py` 并设置：
- API 密钥
- 模型参数
- 其他配置选项

## 使用说明

1. 访问 `http://localhost:8080` 打开Web界面
2. 点击"开始抓取"按钮启动爬虫
3. 在任务列表中查看抓取进度和结果

## 数据存储

爬取的数据存储在以下位置：
- JSON文件: `news_crawler/data/*.json`
- 数据库文件: `news_crawler/data/news.db`

## 贡献

欢迎提交 Pull Request 或创建 Issue。

## 许可证

MIT License 