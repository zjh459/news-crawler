"""
配置文件，包含新闻网站的URL和其他配置参数
"""

# 新闻网站配置
NEWS_SITES = {
    "nytimes": {
        "name": "The New York Times",
        "url": "https://www.nytimes.com/",
        "article_selector": "article[data-testid='block-grid-item'], div.css-1cp3ece, div.css-1l4w6pd",  # 文章列表选择器
        "title_selector": "h3, h2, .e1h9rw200, .css-1qwxefa",  # 标题选择器
        "link_selector": "a, h3 a, h2 a",                      # 链接选择器
        "summary_selector": "p, .css-1echdzn",                 # 摘要选择器
        "time_selector": "time, .css-1sbuyqj",                 # 时间选择器
        "content_selector": "section[name='articleBody'] p, div.StoryBodyCompanionColumn p, .meteredContent p",  # 正文选择器
        "top_news_selector": "section.top-news article, div.css-1cp3ece, div.css-1l4w6pd"  # 头条新闻选择器
    },
    "washingtonpost": {
        "name": "The Washington Post",
        "url": "https://www.washingtonpost.com/",
        "article_selector": "div.story-list-story, div.card, div.story, article",  # 文章列表选择器
        "title_selector": "h2, h3, .headline, .title",         # 标题选择器
        "link_selector": "h2 a, h3 a, .headline a, a",         # 链接选择器
        "summary_selector": "div.story-description, p.blurb, .description", # 摘要选择器
        "time_selector": "span.timestamp, time, .date",        # 时间选择器
        "content_selector": "article p, .article-body p, .story-body p",  # 正文选择器
        "top_news_selector": "div.top-story, .main-content article, .main-stage article",  # 头条新闻选择器
        "requires_js": True,                                   # 需要JavaScript渲染
        "use_proxy": True                                      # 使用代理
    },
    "foxnews": {
        "name": "Fox News",
        "url": "https://www.foxnews.com/",
        "article_selector": "article.article, .collection-article, .content",  # 文章列表选择器
        "title_selector": "h3.title a, h2.title, .headline",   # 标题选择器
        "link_selector": "h3.title a, h2.title a, a.title",    # 链接选择器
        "summary_selector": "div.content p, .dek, .description",  # 摘要选择器
        "time_selector": "span.time, time, .date",             # 时间选择器
        "content_selector": "div.article-body p, .article-content p",  # 正文选择器
        "top_news_selector": "main article.article, .main-content article"  # 头条新闻选择器
    },
    "cnn": {
        "name": "CNN",
        "url": "https://www.cnn.com/",
        "article_selector": ".container__item-container, .card--standard, .card",
        "title_selector": ".container__title-text, .container__headline-text, .card__headline-text",
        "link_selector": "a[href^='/']",
        "summary_selector": ".container__description-text, .card__description",
        "time_selector": "time, .timestamp, meta[property='article:published_time']",
        "content_selector": ".article__content p, .article-body p, .article__body p, .zn-body__paragraph, article p",
        "top_news_selector": ".container_lead-plus-headlines__item--lead, .container_lead-package",
        "requires_js": False,  # 禁用 Playwright
        "wait_until": "domcontentloaded",
        "timeout": 15000
    },
    'bbc': {
        'name': 'BBC News',
        'url': 'https://www.bbc.com/news',
        'article_selector': '.sc-914f79f9-2, .sc-530fb3d6-1, .sc-e5949eb5-1',  # 更新文章容器选择器
        'title_selector': '.sc-87075214-3',  # 更新标题选择器
        'link_selector': '.sc-2e6baa30-0',  # 更新链接选择器
        'summary_selector': '.sc-eb7bd5f6-0',  # 更新摘要选择器
        'time_selector': '.sc-6fba5bd4-1',  # 更新时间选择器
        'content_selector': 'article p',  # 保持不变
        'top_news_selector': '.sc-41044fee-1',  # 更新头条新闻选择器
        'requires_js': False,  # 禁用 Playwright
        'wait_until': 'domcontentloaded',
        'timeout': 30000,
        'random_delay': {
            'min': 0.5,
            'max': 1.5
        }
    },
    "wsj": {
        "name": "Wall Street Journal",
        "url": "https://www.wsj.com/",
        "article_selector": "article, div[class*='article'], div[class*='story'], .WSJTheme--story, .style--story, .WSJBaseCard, [data-type='article']",
        "title_selector": "h1, h2, h3, [class*='headline'], [class*='title'], .WSJTheme--headlineText, .style--headlineText",
        "link_selector": "a[href*='/articles/'], a[href*='/news/'], a[href*='/markets/'], a[href*='/business/'], a[href*='/features/']",
        "summary_selector": "[class*='summary'], [class*='dek'], [class*='description'], p.WSJTheme--description, .style--description",
        "time_selector": "time, [datetime], [class*='timestamp'], [class*='date'], .WSJTheme--timestamp, .style--timestamp",
        "content_selector": "article p, [class*='article-body'] p, [class*='body'] p, .WSJTheme--richTextBody p",
        "top_news_selector": "[class*='top-stories'], [class*='lead-'], [class*='hero-'], [data-type='top-story']",
        "requires_js": True,
        "wait_until": "networkidle",
        "timeout": 30000,
        "random_delay": {
            "min": 1,
            "max": 3
        }
    }
}

# 爬虫配置
CRAWLER_CONFIG = {
    "headers": {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
        "Sec-Ch-Ua": "\"Chromium\";v=\"122\", \"Not(A:Brand\";v=\"24\", \"Google Chrome\";v=\"122\"",
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": "\"Windows\"",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1"
    },
    "timeout": 15,  # 减少超时时间到15秒
    "retry_times": 3,
    "retry_interval": 1,
    "save_path": "data",
    "max_news_per_site": 10,
    "use_proxy": False,
    "random_delay": {
        "enabled": True,
        "min": 0.5,  # 减少最小延迟到0.5秒
        "max": 1.5   # 减少最大延迟到1.5秒
    },
    "playwright": {  # Playwright特定配置
        "viewport": {
            "width": 1920,
            "height": 1080
        },
        "device_scale_factor": 1,
        "timeout": 30000,  # 30秒超时
        "wait_until": "domcontentloaded",  # 等待DOM加载完成即可
        "ignore_https_errors": True
    }
} 