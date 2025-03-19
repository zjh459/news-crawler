"""
华尔街日报爬虫
"""
import logging
import asyncio
import json
import re
import aiohttp
import feedparser
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from datetime import datetime, timedelta
from news_crawler.scrapers.base_scraper import BaseScraper
from news_crawler.config.config import NEWS_SITES, CRAWLER_CONFIG
import pytz
from email.utils import parsedate_to_datetime

logger = logging.getLogger(__name__)

class WSJScraper(BaseScraper):
    """华尔街日报爬虫类"""
    
    def __init__(self):
        """初始化爬虫"""
        super().__init__(NEWS_SITES["wsj"])
        self.site_name = NEWS_SITES["wsj"]["name"]
        # WSJ RSS 源，按重要性排序
        self.rss_feeds = [
            # 头条新闻和重要新闻
            "https://feeds.content.dowjones.io/public/rss/RSSWorldNews",  # 国际新闻
            "https://feeds.content.dowjones.io/public/rss/WSJcomUSBusiness",  # 美国商业新闻
            "https://feeds.content.dowjones.io/public/rss/RSSMarketsMain",  # 市场新闻
            "https://feeds.content.dowjones.io/public/rss/RSSWSJD",  # 科技新闻
            "https://feeds.content.dowjones.io/public/rss/RSSOpinion",  # 观点
            # 可以添加更多 RSS 源
        ]
    
    async def scrape(self):
        """重写爬虫方法，从 RSS 源获取最新文章"""
        articles = []
        
        # 从所有 RSS 源获取文章
        rss_articles = await self.scrape_from_rss()
        if rss_articles:
            articles.extend(rss_articles)
            logger.info(f"从 RSS 源获取到 {len(rss_articles)} 篇文章")
        
        # 根据发布时间和重要性对文章进行排序
        sorted_articles = self.sort_articles_by_time_and_importance(articles)
        
        # 限制文章数量并去重
        unique_articles = []
        urls = set()
        for article in sorted_articles:
            if article["url"] not in urls and len(unique_articles) < self.max_news:
                urls.add(article["url"])
                unique_articles.append(article)
        
        # 获取文章内容
        tasks = []
        for article in unique_articles:
            if article.get("url") and not article.get("content"):
                tasks.append(self.fetch_article_content(article))
        
        if tasks:
            await asyncio.gather(*tasks)
        
        # 保存文章到JSON文件
        self.save_to_json(unique_articles)
        
        return unique_articles
    
    def sort_articles_by_time_and_importance(self, articles):
        """根据发布时间和重要性对文章进行排序"""
        try:
            # 获取当前时间
            now = datetime.now(pytz.UTC)
            
            # 为每篇文章计算分数
            for article in articles:
                score = 0
                
                # 根据发布时间计算分数
                try:
                    if article.get("publish_time"):
                        # 解析发布时间
                        pub_time = None
                        try:
                            # 尝试解析 RSS 格式的时间
                            pub_time = parsedate_to_datetime(article["publish_time"])
                        except:
                            try:
                                # 尝试解析其他格式的时间
                                pub_time = datetime.strptime(article["publish_time"], "%Y-%m-%d %H:%M:%S")
                                pub_time = pytz.UTC.localize(pub_time)
                            except:
                                pass
                        
                        if pub_time:
                            # 计算文章的新鲜度分数（24小时内的文章得分最高）
                            time_diff = now - pub_time
                            if time_diff <= timedelta(hours=24):
                                score += 100
                            elif time_diff <= timedelta(days=2):
                                score += 80
                            elif time_diff <= timedelta(days=7):
                                score += 60
                            else:
                                score += 40
                except Exception as e:
                    logger.error(f"计算时间分数时出错: {str(e)}")
                    score += 50  # 如果无法解析时间，给予中等分数
                
                # 根据文章特征增加分数
                title = article.get("title", "").lower()
                
                # 重要性标记词
                importance_keywords = [
                    'breaking', 'exclusive', 'urgent', 'alert',
                    'just in', 'update', 'developing',
                    'market', 'economy', 'fed', 'inflation',
                    'crisis', 'war', 'conflict',
                    'earnings', 'stock', 'trade'
                ]
                
                # 检查标题中的重要性关键词
                for keyword in importance_keywords:
                    if keyword in title:
                        score += 20
                        break
                
                # 保存分数
                article["importance_score"] = score
            
            # 根据分数排序
            sorted_articles = sorted(articles, key=lambda x: x.get("importance_score", 0), reverse=True)
            
            # 移除临时的分数字段
            for article in sorted_articles:
                article.pop("importance_score", None)
            
            return sorted_articles
            
        except Exception as e:
            logger.error(f"排序文章时出错: {str(e)}")
            return articles
    
    async def scrape_from_rss(self):
        """从RSS源获取文章的改进版本"""
        articles = []
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for feed_url in self.rss_feeds:
                try:
                    logger.info(f"从RSS源获取文章: {feed_url}")
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                        "Accept": "application/rss+xml,application/xml;q=0.9,*/*;q=0.8",
                    }
                    
                    async with session.get(feed_url, headers=headers) as response:
                        if response.status == 200:
                            feed_content = await response.text()
                            
                            # 验证RSS内容
                            if not feed_content or len(feed_content) < 100:
                                logger.warning(f"RSS源返回内容过短: {feed_url}")
                                continue
                                
                            if not ('<rss' in feed_content or '<feed' in feed_content):
                                logger.warning(f"返回内容不是有效的RSS格式: {feed_url}")
                                continue
                            
                            feed = feedparser.parse(feed_content)
                            
                            if not feed.entries:
                                logger.warning(f"RSS源没有任何条目: {feed_url}")
                                continue
                            
                            for entry in feed.entries:
                                try:
                                    # 验证必要字段
                                    if not hasattr(entry, 'title') or not hasattr(entry, 'link'):
                                        continue
                                    
                                    url = entry.link
                                    if not self.is_valid_article_url(url):
                                        continue
                                    
                                    title = entry.title.strip()
                                    if not title:
                                        continue
                                    
                                    summary = ""
                                    if hasattr(entry, 'summary'):
                                        summary = entry.summary
                                    elif hasattr(entry, 'description'):
                                        summary = entry.description
                                    
                                    # 处理发布时间
                                    publish_time = ""
                                    for time_field in ['published', 'pubDate', 'updated', 'created']:
                                        if hasattr(entry, time_field):
                                            publish_time = getattr(entry, time_field)
                                            break
                                    
                                    article = {
                                        "title": title,
                                        "url": url,
                                        "summary": summary,
                                        "publish_time": publish_time,
                                        "source": self.site_name,
                                        "site": "wsj",
                                        "is_top_news": False,
                                        "importance": 5,
                                        "crawl_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        "content": ""
                                    }
                                    
                                    articles.append(article)
                                    logger.info(f"从RSS源提取文章: {title[:50]}...")
                                except Exception as e:
                                    logger.error(f"处理RSS条目时出错: {str(e)}")
                        else:
                            logger.warning(f"获取RSS源失败，状态码: {response.status}, URL: {feed_url}")
                except asyncio.TimeoutError:
                    logger.error(f"获取RSS源超时: {feed_url}")
                except Exception as e:
                    logger.error(f"获取RSS源出错: {feed_url}, 错误: {str(e)}")
        
        return articles
    
    async def fetch_article_content(self, article):
        """获取文章内容，不使用随机延迟"""
        try:
            html = await self.fetch_page(article["url"])
            if not html:
                return
            
            soup = BeautifulSoup(html, "html.parser")
            
            # 提取文章内容
            content_selectors = [
                self.site_config["content_selector"],
                "article p",
                "[class*='article-body'] p",
                "[class*='body'] p",
                ".WSJTheme--richTextBody p",
                ".article-content p",
                ".article-wrap p"
            ]
            
            content = ""
            for selector in content_selectors:
                content_elements = soup.select(selector)
                if content_elements:
                    logger.info(f"使用选择器 {selector} 找到 {len(content_elements)} 段内容")
                    content = "\n".join([p.get_text().strip() for p in content_elements])
                    break
            
            article["content"] = content
            
        except Exception as e:
            logger.error(f"获取文章内容时出错: {str(e)}")
            article["content"] = ""
    
    async def fetch_page(self, url):
        """获取页面内容，不使用随机延迟"""
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.text()
                    else:
                        logger.warning(f"获取页面失败，状态码: {response.status}, URL: {url}")
                        return ""
                        
        except Exception as e:
            logger.error(f"获取页面内容时出错: {str(e)}")
            return ""
    
    def parse_article_list(self, html, is_top_news=False):
        """解析文章列表，重写BaseScraper的方法"""
        soup = BeautifulSoup(html, 'html.parser')
        articles = []
        
        # 打印页面标题，确认页面内容正确
        page_title = soup.title.text if soup.title else "无标题"
        logger.info(f"页面标题: {page_title}")
        
        # 保存HTML内容用于调试
        debug_file = f"wsj_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(debug_file, "w", encoding="utf-8") as f:
            f.write(html)
        logger.info(f"已保存HTML内容到 {debug_file} 用于调试")
        
        # 尝试从 JSON 数据中提取文章
        json_data = self.extract_json_data(html)
        if json_data:
            logger.info("从 JSON 数据中提取文章")
            json_articles = self.parse_json_articles(json_data)
            if json_articles:
                logger.info(f"从 JSON 数据中提取到 {len(json_articles)} 篇文章")
                articles.extend(json_articles)
        
        # 如果从 JSON 中没有提取到文章，尝试从 HTML 中提取
        if not articles:
            # 尝试多种选择器以提高抓取成功率
            if is_top_news:
                selectors = [
                    self.site_config["top_news_selector"],
                    "div[class*='top-stories']",
                    "section[class*='top-stories']",
                    "div[class*='lead-']",
                    "div[class*='hero-']",
                    "div[class*='main-content']",
                    "[data-module-zone='top_news']",
                    "[data-module-zone='headline']"
                ]
            else:
                selectors = [
                    self.site_config["article_selector"],
                    "article",
                    "div[class*='article']",
                    "div[class*='story']",
                    ".WSJTheme--story",
                    ".style--story",
                    ".WSJBaseCard",
                    "[data-type='article']",
                    "div.wsj-card",
                    "div.WSJCard",
                    "div.WSJTheme--card",
                    "div[class*='card']",
                    "div.headline-item",
                    "li.headline-item"
                ]
            
            article_elements = []
            for selector in selectors:
                elements = soup.select(selector)
                if elements:
                    logger.info(f"使用选择器 '{selector}' 找到 {len(elements)} 个文章元素")
                    article_elements.extend(elements)
                    # 打印找到的元素的类名，帮助调试
                    for elem in elements[:3]:  # 只打印前3个元素
                        logger.info(f"找到文章元素，类名: {elem.get('class', [])}，标签: {elem.name}")
                else:
                    logger.debug(f"选择器 '{selector}' 未找到任何元素")
            
            # 如果仍然没有找到文章，尝试查找所有链接
            if not article_elements:
                logger.warning("所有选择器都未找到文章元素，尝试查找所有链接")
                links = soup.select("a[href*='/articles/'], a[href*='/news/']")
                for link in links:
                    # 创建一个简单的文章对象
                    url = link.get("href", "")
                    if url and ('/articles/' in url or '/news/' in url):
                        # 处理相对URL
                        if not url.startswith(("http://", "https://")):
                            url = urljoin(self.site_config["url"], url)
                        
                        title = link.get_text().strip()
                        if title and url and len(title) > 5:  # 确保标题不是太短
                            article = {
                                "title": title,
                                "url": url,
                                "summary": "",
                                "publish_time": "",
                                "source": self.site_name,
                                "site": "wsj",
                                "is_top_news": is_top_news,
                                "importance": 10 if is_top_news else 5,
                                "crawl_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "content": ""
                            }
                            articles.append(article)
                            logger.info(f"从链接提取文章: {title[:50]}...")
            else:
                # 处理找到的文章元素
                for element in article_elements:
                    article = self.extract_article_info(element, is_top_news)
                    if article:
                        articles.append(article)
                        logger.info(f"成功提取文章: {article['title'][:50]}...")
                    else:
                        logger.warning(f"无法从元素提取文章信息，类名: {element.get('class', [])}")
        
        # 去重
        unique_articles = []
        urls = set()
        for article in articles:
            if article["url"] not in urls:
                urls.add(article["url"])
                unique_articles.append(article)
        
        logger.info(f"总共找到 {len(unique_articles)} 篇不重复文章")
        return unique_articles[:self.max_news]
    
    def extract_json_data(self, html):
        """从页面中提取嵌入的JSON数据"""
        try:
            # 查找包含文章数据的script标签
            soup = BeautifulSoup(html, 'html.parser')
            json_scripts = soup.find_all('script', type='application/json')
            
            for script in json_scripts:
                try:
                    data = json.loads(script.string)
                    # 检查是否包含文章数据
                    if isinstance(data, dict) and ('articles' in data or 'items' in data or 'headlines' in data):
                        return data
                except:
                    continue
            
            # 尝试查找其他可能包含数据的script标签
            scripts = soup.find_all('script')
            for script in scripts:
                if not script.string:
                    continue
                try:
                    # 查找类似 window.__INITIAL_STATE__ = {...} 的模式
                    match = re.search(r'window\.__[A-Z_]+__\s*=\s*({.*?});', script.string, re.DOTALL)
                    if match:
                        data = json.loads(match.group(1))
                        if isinstance(data, dict) and ('articles' in data or 'items' in data or 'headlines' in data):
                            return data
                except:
                    continue
                    
            return None
        except Exception as e:
            logger.error(f"提取JSON数据时出错: {str(e)}")
            return None

    def parse_json_articles(self, data):
        """解析从JSON数据中提取的文章"""
        articles = []
        try:
            # 处理不同的数据结构
            items = []
            if 'articles' in data:
                items = data['articles']
            elif 'items' in data:
                items = data['items']
            elif 'headlines' in data:
                items = data['headlines']
            
            for item in items:
                try:
                    # 提取文章URL
                    url = item.get('url') or item.get('link') or item.get('articleUrl')
                    if not url:
                        continue
                        
                    # 确保URL是完整的
                    if not url.startswith('http'):
                        url = urljoin('https://www.wsj.com', url)
                    
                    # 检查是否是有效的WSJ文章URL
                    if not self.is_valid_article_url(url):
                        continue
                    
                    # 提取文章标题
                    title = item.get('headline') or item.get('title') or item.get('name')
                    if not title:
                        continue
                    
                    # 提取摘要
                    summary = item.get('summary') or item.get('description') or item.get('snippet') or ""
                    
                    # 提取发布时间
                    publish_time = item.get('publishedAt') or item.get('datePublished') or item.get('timestamp') or ""
                    if isinstance(publish_time, (int, float)):
                        publish_time = datetime.fromtimestamp(publish_time).strftime("%Y-%m-%d %H:%M:%S")
                    
                    article = {
                        "title": title,
                        "url": url,
                        "summary": summary,
                        "publish_time": publish_time,
                        "source": self.site_name,
                        "site": "wsj",
                        "is_top_news": False,
                        "importance": 5,
                        "crawl_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "content": ""
                    }
                    
                    articles.append(article)
                    logger.info(f"从JSON数据中提取文章: {title[:50]}...")
                except Exception as e:
                    logger.error(f"解析单个JSON文章时出错: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"解析JSON文章数据时出错: {str(e)}")
        
        return articles

    def is_valid_article_url(self, url):
        """检查URL是否是有效的WSJ文章链接"""
        try:
            parsed = urlparse(url)
            # 检查域名
            if not parsed.netloc.endswith('wsj.com'):
                return False
            
            # 检查路径
            path = parsed.path.lower()
            # 排除无效路径
            invalid_paths = ['/video/', '/podcasts/', '/photos/', '/graphics/', '/amp/', '/print/']
            if any(p in path for p in invalid_paths):
                return False
                
            # 检查是否包含文章标识符
            valid_patterns = ['/articles/', '/news/', '/markets/', '/business/', '/tech/', '/world/']
            return any(p in path for p in valid_patterns)
            
        except:
            return False
    
    def extract_article_info(self, element, is_top_news=False):
        """从文章元素中提取信息"""
        try:
            # 提取标题
            title_selectors = [
                self.site_config["title_selector"],
                "h1, h2, h3, h4",
                "[class*='headline']",
                "[class*='title']",
                ".WSJTheme--headlineText",
                ".style--headlineText",
                "a[href*='/articles/']",  # 有时链接本身就包含标题
                "a[href*='/news/']"
            ]
            
            title = None
            title_element = None
            for selector in title_selectors:
                title_element = element.select_one(selector)
                if title_element:
                    title = title_element.get_text().strip()
                    if title:
                        break
            
            if not title:
                # 尝试直接从元素获取文本
                title = element.get_text().strip()
                if len(title) > 100:  # 如果文本太长，可能不是标题
                    title = None
            
            if not title:
                return None
                
            # 提取链接
            link_selectors = [
                self.site_config["link_selector"],
                "a[href*='/articles/']",
                "a[href*='/news/']",
                "a[href*='/markets/']",
                "a[href*='/business/']",
                "a[href*='/features/']",
                "a[href]:not([href^='#'])"  # 最后的备用选择器
            ]
            
            url = None
            # 如果标题元素是链接或包含链接
            if title_element:
                if title_element.name == "a" and title_element.has_attr("href"):
                    url = title_element["href"]
                else:
                    link_in_title = title_element.select_one("a")
                    if link_in_title and link_in_title.has_attr("href"):
                        url = link_in_title["href"]
            
            # 如果从标题元素中没有找到链接，尝试其他选择器
            if not url:
                for selector in link_selectors:
                    link_element = element.select_one(selector)
                    if link_element and link_element.has_attr("href"):
                        url = link_element["href"]
                        break
            
            # 处理相对URL
            if url and not url.startswith(("http://", "https://")):
                url = urljoin(self.site_config["url"], url)
            
            if not url:
                return None
            
            # 提取摘要
            summary_selectors = [
                self.site_config["summary_selector"],
                "[class*='summary']",
                "[class*='dek']",
                "[class*='description']",
                "p.WSJTheme--description",
                ".style--description",
                "p:not([class])"  # 最后的备用选择器
            ]
            
            summary = ""
            for selector in summary_selectors:
                summary_element = element.select_one(selector)
                if summary_element:
                    summary = summary_element.get_text().strip()
                    if summary:
                        break
            
            # 提取时间
            time_selectors = [
                self.site_config["time_selector"],
                "time",
                "[datetime]",
                "[class*='timestamp']",
                "[class*='date']",
                ".WSJTheme--timestamp",
                ".style--timestamp"
            ]
            
            publish_time = ""
            for selector in time_selectors:
                time_element = element.select_one(selector)
                if time_element:
                    if time_element.has_attr("datetime"):
                        publish_time = time_element["datetime"]
                    else:
                        publish_time = time_element.get_text().strip()
                    if publish_time:
                        break
            
            # 创建文章对象
            article = {
                "title": title,
                "url": url,
                "summary": summary,
                "publish_time": publish_time,
                "source": self.site_name,
                "site": "wsj",
                "is_top_news": is_top_news,
                "importance": 10 if is_top_news else 5,
                "crawl_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "content": ""
            }
            
            return article
        except Exception as e:
            logger.error(f"提取文章信息时出错: {str(e)}")
            return None 