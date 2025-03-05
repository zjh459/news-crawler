"""
爬虫基类，使用crawl4ai框架
"""

import asyncio
from datetime import datetime
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from news_crawler.config import CRAWLER_CONFIG

class BaseNewsScraper:
    """新闻爬虫基类"""
    
    def __init__(self, site_config, save_to_db=True):
        """
        初始化爬虫
        
        Args:
            site_config (dict): 网站配置
            save_to_db (bool): 是否保存到数据库
        """
        self.site_config = site_config
        self.save_to_db = save_to_db
        
        # 根据crawl4ai的API文档修改配置
        self.browser_config = BrowserConfig(
            user_agent=CRAWLER_CONFIG["user_agent"],
            headless=True,
            ignore_https_errors=True
        )
        
        self.run_config = CrawlerRunConfig(
            page_timeout=CRAWLER_CONFIG["timeout"] * 1000,  # 转换为毫秒
            wait_until="domcontentloaded",
            scan_full_page=True,
            verbose=True
        )
    
    async def scrape_list_page(self):
        """
        爬取列表页，获取文章链接列表
        
        Returns:
            list: 文章信息列表，包含标题、链接、摘要等
        """
        articles = []
        
        async with AsyncWebCrawler(browser_config=self.browser_config) as crawler:
            # 爬取列表页
            result = await crawler.arun(
                url=self.site_config["url"],
                run_config=self.run_config
            )
            
            # 使用BeautifulSoup解析HTML
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(result.html, 'html.parser')
            
            # 提取文章列表
            article_elements = soup.select(self.site_config["article_selector"])
            
            for element in article_elements:
                try:
                    # 提取标题和链接
                    title_element = element.select_one(self.site_config["title_selector"])
                    if not title_element:
                        continue
                    
                    title = title_element.get_text(strip=True)
                    link = title_element.get('href')
                    
                    # 处理相对URL
                    if link and not link.startswith(('http://', 'https://')):
                        from urllib.parse import urljoin
                        link = urljoin(self.site_config["url"], link)
                    
                    # 提取摘要
                    summary = ""
                    summary_element = element.select_one(self.site_config["summary_selector"])
                    if summary_element:
                        summary = summary_element.get_text(strip=True)
                    
                    # 提取发布时间
                    published_at = ""
                    time_element = element.select_one(self.site_config["time_selector"])
                    if time_element:
                        published_at = time_element.get_text(strip=True)
                    
                    # 添加到文章列表
                    if title and link:
                        articles.append({
                            'title': title,
                            'url': link,
                            'summary': summary,
                            'published_at': published_at,
                            'source': self.site_config["name"],
                            'crawled_at': datetime.now().isoformat()
                        })
                except Exception as e:
                    print(f"提取文章信息失败: {e}")
        
        return articles
    
    async def scrape_article_content(self, article_info):
        """
        爬取文章内容
        
        Args:
            article_info (dict): 文章信息，包含URL等
            
        Returns:
            dict: 更新后的文章信息，包含内容
        """
        try:
            async with AsyncWebCrawler(browser_config=self.browser_config) as crawler:
                # 爬取文章页面
                result = await crawler.arun(
                    url=article_info["url"],
                    run_config=self.run_config
                )
                
                # 提取文章内容
                article_info["content"] = result.markdown
                article_info["metadata"] = {
                    "html_title": result.url,
                    "word_count": len(result.markdown.split()),
                    "crawled_time": datetime.now().isoformat()
                }
                
                return article_info
        except Exception as e:
            print(f"爬取文章内容失败: {e}")
            return article_info
    
    async def run(self, max_articles=10):
        """
        运行爬虫
        
        Args:
            max_articles (int): 最大爬取文章数
            
        Returns:
            list: 爬取的文章列表
        """
        # 爬取列表页
        articles = await self.scrape_list_page()
        
        # 限制文章数量
        articles = articles[:max_articles]
        
        # 爬取文章内容
        tasks = [self.scrape_article_content(article) for article in articles]
        articles_with_content = await asyncio.gather(*tasks)
        
        return articles_with_content 