"""
爬虫运行器，用于管理多个爬虫的运行
"""

import asyncio
import os
import json
import pandas as pd
from datetime import datetime
from news_crawler.scrapers.foxnews_scraper import FoxNewsScraper
from news_crawler.config import CRAWLER_CONFIG

class CrawlerRunner:
    """爬虫运行器，用于管理多个爬虫的运行"""
    
    def __init__(self, save_to_db=True, save_to_file=True):
        """
        初始化爬虫运行器
        
        Args:
            save_to_db (bool): 是否保存到数据库
            save_to_file (bool): 是否保存到文件
        """
        self.save_to_db = save_to_db
        self.save_to_file = save_to_file
        self.scrapers = {
            "foxnews": FoxNewsScraper(save_to_db)
        }
    
    async def run_scraper(self, scraper_name, max_articles=10):
        """
        运行指定的爬虫
        
        Args:
            scraper_name (str): 爬虫名称
            max_articles (int): 最大爬取文章数
            
        Returns:
            list: 爬取的文章列表
        """
        if scraper_name not in self.scrapers:
            print(f"爬虫 {scraper_name} 不存在")
            return []
        
        scraper = self.scrapers[scraper_name]
        articles = await scraper.run(max_articles)
        
        # 保存到文件
        if self.save_to_file:
            self._save_to_file(scraper_name, articles)
        
        return articles
    
    async def run_all(self, max_articles_per_site=10):
        """
        运行所有爬虫
        
        Args:
            max_articles_per_site (int): 每个网站最大爬取文章数
            
        Returns:
            dict: 各爬虫爬取的文章列表
        """
        tasks = {
            name: self.run_scraper(name, max_articles_per_site)
            for name in self.scrapers
        }
        
        results = {}
        for name, task in tasks.items():
            results[name] = await task
        
        return results
    
    def _save_to_file(self, scraper_name, articles):
        """
        保存文章到文件
        
        Args:
            scraper_name (str): 爬虫名称
            articles (list): 文章列表
        """
        if not articles:
            return
        
        # 确保目录存在
        save_dir = os.path.join(CRAWLER_CONFIG["save_path"], scraper_name)
        os.makedirs(save_dir, exist_ok=True)
        
        # 生成时间戳
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存为JSON文件
        json_path = os.path.join(save_dir, f"{scraper_name}_{timestamp}.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
            
        # 保存为Excel文件
        excel_path = os.path.join(save_dir, f"{scraper_name}_{timestamp}.xlsx")
        
        # 将文章列表转换为DataFrame
        df = pd.DataFrame(articles)
        
        # 重新排列列的顺序，确保重要信息在前面
        columns = ['title', 'url', 'publish_time', 'content', 'source', 'category', 'author', 'site']
        existing_columns = [col for col in columns if col in df.columns]
        other_columns = [col for col in df.columns if col not in columns]
        final_columns = existing_columns + other_columns
        
        # 重新排序列并保存为Excel
        df = df[final_columns]
        df.to_excel(excel_path, index=False, engine='openpyxl')
        
        return json_path, excel_path
    
    def close(self):
        """关闭爬虫，释放资源"""
        pass 
    
    async def scrape_single_url(self, url):
        """
        抓取单个 URL 的文章内容
        
        Args:
            url (str): 文章 URL
            
        Returns:
            list: 包含单篇文章的列表
        """
        try:
            # 创建一个临时的 FoxNews 爬虫实例
            scraper = FoxNewsScraper(self.save_to_db)
            
            # 构造基本文章信息
            article_info = {
                'url': url,
                'title': '',  # 将在抓取内容时更新
                'source': 'Fox News',
                'crawled_at': datetime.now().isoformat()
            }
            
            # 抓取文章内容
            article = await scraper.scrape_article_content(article_info)
            
            # 如果抓取成功，返回包含这篇文章的列表
            if article and article.get('content'):
                return [article]
            else:
                print(f"抓取文章失败: {url}")
                return []
                
        except Exception as e:
            print(f"抓取文章失败: {e}")
            return [] 