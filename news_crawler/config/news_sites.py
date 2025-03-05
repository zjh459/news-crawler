"""
新闻网站配置文件
包含各个新闻网站的爬取配置信息
"""

# 新闻网站配置
NEWS_SITES = {
    # 新浪新闻
    "sina": {
        "name": "新浪新闻",
        "url": "https://news.sina.com.cn/",
        "article_selector": ".news-item",  # 文章列表选择器
        "title_selector": "h2 a",  # 标题选择器
        "summary_selector": ".news-item-content",  # 摘要选择器
        "time_selector": ".time",  # 时间选择器
    },
    
    # 网易新闻
    "163": {
        "name": "网易新闻",
        "url": "https://news.163.com/",
        "article_selector": ".news_item",
        "title_selector": ".news_title a",
        "summary_selector": ".news_summary",
        "time_selector": ".time",
    },
    
    # BBC新闻
    "bbc": {
        "name": "BBC News",
        "url": "https://www.bbc.com/news",
        "article_selector": ".gs-c-promo",
        "title_selector": ".gs-c-promo-heading a",
        "summary_selector": ".gs-c-promo-summary",
        "time_selector": ".gs-o-bullet__text time",
    },
    
    # Fox News
    "foxnews": {
        "name": "Fox News",
        "url": "https://www.foxnews.com/",
        "article_selector": "article.article",
        "title_selector": ".title a",
        "summary_selector": ".content",
        "time_selector": ".time",
    }
}

# 爬虫配置
CRAWLER_CONFIG = {
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "timeout": 30,  # 超时时间(秒)
} 