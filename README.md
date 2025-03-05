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
git clone https://github.com/yourusername/news-crawler.git
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

4. 启动应用：
```bash
./entrypoint.sh
```

## 配置

- 配置文件位于 `news_crawler/config.py`
- 可以自定义新闻源、抓取间隔等参数

## 使用说明

1. 访问 `http://localhost:8080` 打开Web界面
2. 点击"开始抓取"按钮启动爬虫
3. 在任务列表中查看抓取进度和结果

## 贡献

欢迎提交 Pull Request 或创建 Issue。

## 许可证

MIT License 