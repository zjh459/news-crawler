"""
Fox News爬虫
"""

from bs4 import BeautifulSoup
from urllib.parse import urljoin
from news_crawler.scrapers.base_scraper import BaseNewsScraper
from news_crawler.config import NEWS_SITES
from crawl4ai import AsyncWebCrawler

class FoxNewsScraper(BaseNewsScraper):
    """Fox News爬虫类"""
    
    def __init__(self, save_to_db=True):
        """
        初始化Fox News爬虫
        
        Args:
            save_to_db (bool): 是否保存到数据库
        """
        super().__init__(NEWS_SITES["foxnews"], save_to_db)
    
    async def scrape_list_page(self):
        """
        重写爬取列表页方法，优先获取头条新闻
        
        Returns:
            list: 文章信息列表
        """
        articles = []
        
        async with AsyncWebCrawler(browser_config=self.browser_config) as crawler:
            # 爬取首页
            result = await crawler.arun(
                url="https://www.foxnews.com",
                run_config=self.run_config
            )
            
            soup = BeautifulSoup(result.html, 'html.parser')
            
            # 首先尝试获取主要头条新闻
            main_headline = soup.select_one('h1.headline a, h1.title a')
            if main_headline:
                title = main_headline.get_text(strip=True)
                link = main_headline.get('href')
                
                # 处理相对URL
                if link and not link.startswith(('http://', 'https://')):
                    link = urljoin("https://www.foxnews.com", link)
                
                # 提取摘要
                summary = ""
                summary_element = main_headline.find_parent('article').select_one('.dek, .description, .content p')
                if summary_element:
                    summary = summary_element.get_text(strip=True)
                
                if title and link:
                    articles.append({
                        'title': title,
                        'url': link,
                        'summary': summary,
                        'source': 'Fox News',
                        'category': 'main_headline',
                        'is_headline': True
                    })
            
            # 获取其他重要新闻
            article_elements = soup.select('article.story, .content article.article')
            
            for article in article_elements:
                try:
                    # 跳过已经添加的主要头条
                    title_element = article.select_one('h2 a, h3 a, .title a, .info a')
                    if not title_element:
                        continue
                    
                    title = title_element.get_text(strip=True)
                    link = title_element.get('href')
                    
                    # 处理相对URL
                    if link and not link.startswith(('http://', 'https://')):
                        link = urljoin("https://www.foxnews.com", link)
                    
                    # 提取摘要
                    summary = ""
                    summary_element = article.select_one('.dek, .description, .content p')
                    if summary_element:
                        summary = summary_element.get_text(strip=True)
                    
                    # 检查是否已经添加过这篇文章
                    if title and link and link not in [a['url'] for a in articles]:
                        articles.append({
                            'title': title,
                            'url': link,
                            'summary': summary,
                            'source': 'Fox News',
                            'category': 'headline',
                            'is_headline': False
                        })
                        
                        # 如果已经获取足够的文章，就停止
                        if len(articles) >= 10:
                            break
                            
                except Exception as e:
                    print(f"提取文章信息失败: {e}")
            
            # 如果没有找到足够的文章，尝试其他选择器
            if len(articles) < 10:
                print("使用备用选择器")
                # 尝试其他可能的文章容器
                article_elements = soup.select('.main-content article, .collection article')
                
                for article in article_elements:
                    try:
                        # 提取标题和链接
                        title_element = article.select_one('a[data-type="title"], .headline a, .title a')
                        if not title_element:
                            continue
                            
                        title = title_element.get_text(strip=True)
                        link = title_element.get('href')
                        
                        # 处理相对URL
                        if link and not link.startswith(('http://', 'https://')):
                            link = urljoin("https://www.foxnews.com", link)
                        
                        # 提取摘要
                        summary = ""
                        summary_element = article.select_one('[data-type="dek"], .description, .content p')
                        if summary_element:
                            summary = summary_element.get_text(strip=True)
                        
                        # 检查是否已经添加过这篇文章
                        if title and link and link not in [a['url'] for a in articles]:
                            articles.append({
                                'title': title,
                                'url': link,
                                'summary': summary,
                                'source': 'Fox News',
                                'category': 'headline',
                                'is_headline': False
                            })
                            
                            # 如果已经获取足够的文章，就停止
                            if len(articles) >= 10:
                                break
                                
                    except Exception as e:
                        print(f"提取文章信息失败（备用选择器）: {e}")
            
        return articles[:10]  # 确保最多返回10篇文章
    
    async def scrape_article_content(self, article_info):
        """
        重写爬取文章内容方法，提取纯文本内容
        
        Args:
            article_info (dict): 文章信息
            
        Returns:
            dict: 更新后的文章信息
        """
        try:
            async with AsyncWebCrawler(browser_config=self.browser_config) as crawler:
                result = await crawler.arun(
                    url=article_info["url"],
                    run_config=self.run_config
                )
                
                soup = BeautifulSoup(result.html, 'html.parser')
                
                # 移除不需要的元素
                for element in soup.select('script, style, iframe, .ad-container, .video-container, .social-share'):
                    element.decompose()
                
                # 提取文章主体
                article_body = soup.select_one('.article-body')
                if article_body:
                    # 只保留段落文本
                    paragraphs = []
                    
                    # 添加标题作为第一行
                    title = article_info.get('title', '')
                    if title:
                        paragraphs.append(f"# {title}")  # 使用 Markdown 格式标记标题
                        paragraphs.append("")  # 添加一个空行分隔标题和正文
                    
                    for p in article_body.select('p'):
                        # 跳过广告和社交媒体相关段落
                        if any(keyword in p.get_text().lower() for keyword in ['advertisement', 'click here', 'follow us']):
                            continue
                        text = p.get_text(strip=True)
                        if text:
                            paragraphs.append(text)
                    
                    # 合并段落
                    content = '\n\n'.join(paragraphs)
                    
                    # 更新文章信息
                    article_info["content"] = content
                    article_info["metadata"] = {
                        "word_count": len(content.split()),
                        "is_headline": article_info.get("is_headline", False)
                    }
                
                return article_info
        except Exception as e:
            print(f"爬取文章内容失败: {e}")
            return article_info 