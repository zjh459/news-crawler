"""
网易新闻爬虫
"""

from news_crawler.scrapers.base_scraper import BaseNewsScraper
from news_crawler.config import NEWS_SITES

class NetEaseNewsScraper(BaseNewsScraper):
    """网易新闻爬虫类"""
    
    def __init__(self, save_to_db=True):
        """
        初始化网易新闻爬虫
        
        Args:
            save_to_db (bool): 是否保存到数据库
        """
        super().__init__(NEWS_SITES["163"], save_to_db)
    
    # 如果需要针对网易新闻的特殊处理，可以在这里重写基类方法 