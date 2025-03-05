"""
配置文件，包含新闻网站的URL和其他配置参数
"""

# 新闻网站配置
NEWS_SITES = {
    "foxnews": {
        "name": "Fox News",
        "url": "https://www.foxnews.com/",
        "article_selector": "article.article",     # 文章列表选择器
        "title_selector": "h3.title a",            # 标题选择器
        "link_selector": "h3.title a",             # 链接选择器
        "summary_selector": "div.content p",       # 摘要选择器
        "time_selector": "span.time",              # 时间选择器
    }
}

# 爬虫配置
CRAWLER_CONFIG = {
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "timeout": 30,  # 请求超时时间（秒）
    "retry_times": 3,  # 重试次数
    "retry_interval": 5,  # 重试间隔（秒）
    "save_path": "news_crawler/data",  # 数据保存路径
}

# 数据库配置
DB_CONFIG = {
    "db_path": "news_crawler/data/news.db",  # SQLite数据库路径
} 