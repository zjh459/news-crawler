"""
纽约时报专用爬虫类
"""
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper, PLAYWRIGHT_AVAILABLE
from ..config.config import NEWS_SITES
import re
import asyncio
from datetime import datetime

class NYTimesScraper(BaseScraper):
    def __init__(self):
        # 设置需要JavaScript渲染
        site_config = NEWS_SITES["nytimes"].copy()
        site_config["requires_js"] = True
        super().__init__(site_config)
    
    async def scrape(self):
        """执行爬虫任务"""
        try:
            # 初始化爬虫
            await self.initialize()
            
            print(f"开始爬取 {self.site_config['name']}...")
            
            # 获取页面内容，增加等待时间确保JavaScript完全加载
            html = await self.fetch_page(self.site_config["url"], wait_time=10)
            if not html:
                print(f"Failed to fetch content from {self.site_config['name']}")
                return []
            
            print(f"成功获取 {self.site_config['name']} 页面内容，长度: {len(html)} 字符")
            
            # 保存HTML内容用于调试
            debug_file = f"nytimes_debug.html"
            with open(debug_file, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"已保存HTML内容到 {debug_file} 用于调试")
            
            # 使用BeautifulSoup解析HTML
            soup = BeautifulSoup(html, 'lxml')
            articles = []
            
            # 打印页面标题，确认页面内容正确
            page_title = soup.title.text if soup.title else "无标题"
            print(f"页面标题: {page_title}")
            
            # 首先尝试获取头条新闻区域
            top_news_selectors = [
                "div.css-1cp3ece",  # 主要头条区域
                "div.css-1l4w6pd",  # 次要头条区域
                "section.top-news",  # 顶部新闻区域
                "div.css-1ez5fsm",  # 大型头条区域
                "div.css-1qiat1j"   # 特色新闻区域
            ]
            
            top_news_elements = []
            for selector in top_news_selectors:
                elements = soup.select(selector)
                if elements:
                    print(f"在头条区域 '{selector}' 找到 {len(elements)} 个元素")
                    top_news_elements.extend(elements)
            
            # 从头条区域提取文章
            top_news = []
            for element in top_news_elements:
                article_elements = element.find_all(["article", "div", "section"], class_=lambda x: x and any(c in str(x) for c in ["story", "article", "css-"]))
                for article_element in article_elements:
                    try:
                        # 查找标题和链接
                        title_elem = article_element.find(["h1", "h2", "h3", "h4", "a"], class_=lambda x: x and any(c in str(x) for c in ["headline", "title", "css-"]))
                        link_elem = article_element.find("a", href=lambda x: x and (x.startswith("/") or "nytimes.com" in x))
                        
                        if not title_elem:
                            continue
                        
                        # 如果找到标题但没有找到链接，尝试使用标题元素本身作为链接
                        if not link_elem and title_elem.name == "a":
                            link_elem = title_elem
                        
                        # 如果仍然没有找到链接，跳过这个元素
                        if not link_elem:
                            continue
                        
                        # 提取标题和URL
                        title = title_elem.get_text(strip=True)
                        url = link_elem.get("href", "")
                        
                        # 分离标题和阅读时间
                        title_parts = title.split("min read")
                        if len(title_parts) > 1:
                            title = title_parts[0].strip()
                            if title.endswith("5") or title.endswith("4") or title.endswith("3") or title.endswith("2"):
                                title = title[:-1].strip()
                        
                        # 处理相对URL
                        if url and not url.startswith("http"):
                            if url.startswith("#") or url == "/":
                                continue
                            url = f"https://www.nytimes.com{url}"
                        
                        # 查找摘要
                        summary = ""
                        summary_elem = article_element.find("p", class_=lambda x: x and any(c in str(x) for c in ["summary", "description", "css-"]))
                        if summary_elem:
                            summary = summary_elem.get_text(strip=True)
                            # 如果摘要包含在标题中，从标题中移除
                            if summary in title:
                                title = title.replace(summary, "").strip()
                        
                        # 查找发布时间
                        time = ""
                        time_elem = article_element.find("time") or article_element.find(class_=lambda x: x and "time" in str(x).lower())
                        if time_elem:
                            time = time_elem.get_text(strip=True)
                            # 尝试标准化时间格式
                            try:
                                # 处理多种时间格式
                                time_formats = [
                                    "%B %d, %Y, %I:%M %p ET",
                                    "%B %d, %Y, %I:%M %p ET%Mm ago",
                                    "%B %d, %Y"
                                ]
                                for time_format in time_formats:
                                    try:
                                        parsed_time = datetime.strptime(time.split("m ago")[0], time_format)
                                        time = parsed_time.strftime("%Y-%m-%d %H:%M:%S")
                                        break
                                    except ValueError:
                                        continue
                            except:
                                # 如果解析失败，至少保留原始格式
                                pass
                        
                        # 提取文章内容预览
                        content_preview = ""
                        # 尝试从摘要中获取内容预览
                        if summary:
                            content_preview = summary
                        # 如果没有摘要，使用默认文本
                        else:
                            content_preview = "文章预览暂无，请点击原文阅读。"
                        
                        # 获取当前时间作为抓取时间
                        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        # 只添加有效的文章
                        if title and url and self.is_valid_article_url(url):
                            article = {
                                "title": title,
                                "url": url,
                                "summary": summary,
                                "publish_time": time,
                                "content": "",  # 先设置为空，稍后填充实际内容
                                "is_top_news": True,  # 这是头条新闻
                                "element_html": str(article_element),
                                "source": "The New York Times",  # 添加来源
                                "crawl_time": current_time  # 添加抓取时间
                            }
                            
                            # 检查是否已存在相同URL的文章
                            if not any(a["url"] == url for a in top_news):
                                top_news.append(article)
                                print(f"找到头条文章: {title}")
                    except Exception as e:
                        print(f"解析头条文章时出错: {str(e)}")
            
            # 使用更新的选择器查找普通文章
            regular_selectors = [
                "div.css-1l10c03",  # 常规文章网格
                "article[data-testid='block-grid-item']",
                "div[data-testid='block-grid-item']",
                "section[data-testid='block-grid-item']",
                "div.story-wrapper",
                "div[data-block-tracking-id]",
                "div.css-xj7rnz",
                "section.story-wrapper",
                "div.css-1njmbkd",
                "li.css-1qtaxzf",
                "div.css-9mylee"
            ]
            
            regular_news = []
            for selector in regular_selectors:
                elements = soup.select(selector)
                print(f"使用选择器 '{selector}' 找到 {len(elements)} 个元素")
                
                for element in elements:
                    try:
                        # 查找标题和链接
                        title_elem = element.find(["h2", "h3", "h4", "a", "p"], class_=lambda x: x and any(c in str(x) for c in ["headline", "title", "css-", "indicate-hover"]))
                        link_elem = element.find("a", href=lambda x: x and (x.startswith("/") or "nytimes.com" in x))
                        
                        if not title_elem:
                            continue
                        
                        # 如果找到标题但没有找到链接，尝试使用标题元素本身作为链接
                        if not link_elem and title_elem.name == "a":
                            link_elem = title_elem
                        
                        # 如果仍然没有找到链接，尝试在父元素中查找
                        if not link_elem:
                            parent = element.parent
                            if parent:
                                link_elem = parent.find("a")
                        
                        # 如果仍然没有找到链接，跳过这个元素
                        if not link_elem:
                            continue
                        
                        # 提取标题和URL
                        title = title_elem.get_text(strip=True)
                        url = link_elem.get("href", "")
                        
                        # 分离标题和阅读时间
                        title_parts = title.split("min read")
                        if len(title_parts) > 1:
                            title = title_parts[0].strip()
                            if title.endswith("5") or title.endswith("4") or title.endswith("3") or title.endswith("2"):
                                title = title[:-1].strip()
                        
                        # 处理相对URL
                        if url and not url.startswith("http"):
                            if url.startswith("#") or url == "/":
                                continue
                            url = f"https://www.nytimes.com{url}"
                        
                        # 查找摘要
                        summary = ""
                        summary_elem = element.find("p", class_=lambda x: x and any(c in str(x) for c in ["summary", "description", "css-", "summary-class"]))
                        if summary_elem:
                            summary = summary_elem.get_text(strip=True)
                            # 如果摘要包含在标题中，从标题中移除
                            if summary in title:
                                title = title.replace(summary, "").strip()
                        
                        # 查找发布时间
                        time = ""
                        time_elem = element.find("time") or element.find(class_=lambda x: x and "time" in str(x).lower())
                        if time_elem:
                            time = time_elem.get_text(strip=True)
                            # 尝试标准化时间格式
                            try:
                                # 处理多种时间格式
                                time_formats = [
                                    "%B %d, %Y, %I:%M %p ET",
                                    "%B %d, %Y, %I:%M %p ET%Mm ago",
                                    "%B %d, %Y"
                                ]
                                for time_format in time_formats:
                                    try:
                                        parsed_time = datetime.strptime(time.split("m ago")[0], time_format)
                                        time = parsed_time.strftime("%Y-%m-%d %H:%M:%S")
                                        break
                                    except ValueError:
                                        continue
                            except:
                                # 如果解析失败，至少保留原始格式
                                pass
                        
                        # 提取文章内容预览
                        content_preview = ""
                        # 尝试从摘要中获取内容预览
                        if summary:
                            content_preview = summary
                        # 如果没有摘要，使用默认文本
                        else:
                            content_preview = "文章预览暂无，请点击原文阅读。"
                        
                        # 获取当前时间作为抓取时间
                        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        # 只添加有效的文章
                        if title and url and self.is_valid_article_url(url):
                            article = {
                                "title": title,
                                "url": url,
                                "summary": summary,
                                "publish_time": time,
                                "content": "",  # 先设置为空，稍后填充实际内容
                                "is_top_news": False,  # 这是普通新闻
                                "element_html": str(element),
                                "source": "The New York Times",  # 添加来源
                                "crawl_time": current_time  # 添加抓取时间
                            }
                            
                            # 检查是否已存在相同URL的文章（包括头条新闻）
                            if not any(a["url"] == url for a in top_news) and not any(a["url"] == url for a in regular_news):
                                regular_news.append(article)
                                print(f"找到普通文章: {title}")
                    except Exception as e:
                        print(f"解析普通文章时出错: {str(e)}")
            
            # 合并头条新闻和普通新闻
            articles = top_news
            
            # 如果头条新闻数量不足，补充普通新闻
            if len(articles) < self.max_news:
                remaining_slots = self.max_news - len(articles)
                articles.extend(regular_news[:remaining_slots])
            
            # 按照重要性排序
            for i, article in enumerate(articles):
                # 设置一个重要性分数：头条新闻从100开始，普通新闻从50开始，然后按照顺序递减
                importance = 100 - i if article.get("is_top_news", False) else 50 - i
                article["importance"] = importance
            
            # 按重要性排序
            articles.sort(key=lambda x: x.get("importance", 0), reverse=True)
            
            # 限制总数量
            articles = articles[:self.max_news]
            
            print(f"共找到 {len(articles)} 篇文章")
            
            # 获取每篇文章的内容
            print("开始获取文章内容...")
            for article in articles:
                try:
                    if not article.get("content"):
                        print(f"获取文章内容: {article['title']}")
                        content = await self.fetch_article_content(article["url"])
                        if content:
                            article["content"] = content
                        else:
                            article["content"] = "无法获取文章内容，可能需要订阅或登录才能访问。"
                except Exception as e:
                    print(f"获取文章内容失败: {str(e)}")
                    article["content"] = "获取内容时出错，请点击原文阅读。"
            
            # 如果找到了文章，保存并返回
            if articles:
                # 保存数据到JSON文件
                self.save_to_json(articles)
                return articles
            
            print(f"未找到任何文章，请检查选择器是否正确")
            return []
            
        except Exception as e:
            print(f"爬取 {self.site_config['name']} 失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    def is_valid_article_url(self, url: str) -> bool:
        """检查URL是否是有效的文章URL"""
        if not url:
            return False
            
        # 忽略主页和锚点链接
        if url in ["https://www.nytimes.com", "https://www.nytimes.com/", "https://www.nytimes.com#site-content"]:
            return False
        
        # 忽略非文章页面
        invalid_patterns = [
            "/search", "/video/", "/interactive/", "/slideshow/", 
            "/subscription", "/account", "/login", "/register",
            "/newsletters", "/games/", "/crosswords/", "/podcasts/",
            "/section/", "/live/", "/tips", "/privacy", "/terms",
            "/trending", "/sitemap", "/help", "/store", "/admin"
        ]
        
        for pattern in invalid_patterns:
            if pattern in url:
                return False
        
        # 检查是否包含日期格式，这通常表示是文章
        date_pattern = r'/\d{4}/\d{2}/\d{2}/'
        date_match = re.search(date_pattern, url)
        
        if date_match:
            # 检查是否是未来日期（测试数据）
            date_str = date_match.group(0).strip('/')
            try:
                article_date = datetime.strptime(date_str, '%Y/%m/%d')
                current_date = datetime.now()
                
                # 如果是未来日期，标记为测试URL但仍然返回True以便我们可以处理它
                if article_date > current_date:
                    print(f"警告: 检测到未来日期的文章URL: {url}")
            except Exception as e:
                print(f"解析日期时出错: {str(e)}")
            
            return True
        
        # 其他可能的文章URL格式
        valid_patterns = [
            "/article/", "/opinion/", "/politics/", "/business/",
            "/technology/", "/science/", "/health/", "/sports/",
            "/arts/", "/books/", "/food/", "/travel/"
        ]
        
        for pattern in valid_patterns:
            if pattern in url:
                return True
        
        return False
    
    async def fetch_page(self, url: str, wait_time: int = 5) -> str:
        """重写fetch_page方法，增加更多的等待时间和页面交互"""
        if not PLAYWRIGHT_AVAILABLE:
            return await self.fetch_page_with_requests(url)
            
        try:
            from playwright.async_api import async_playwright
            
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch()
            page = await browser.new_page()
            
            # 设置更真实的User-Agent
            await page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            })
            
            # 访问页面
            await page.goto(url, wait_until="networkidle", timeout=30000)
            
            # 等待主要内容加载
            await asyncio.sleep(wait_time)
            
            # 模拟滚动以触发懒加载
            for _ in range(3):
                await page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(1)
            
            # 获取页面内容
            content = await page.content()
            
            await browser.close()
            await playwright.stop()
            
            return content
                
        except Exception as e:
            print(f"使用Playwright获取页面失败: {str(e)}，尝试使用requests备选方案")
            return await self.fetch_page_with_requests(url)
    
    async def fetch_page_with_requests(self, url: str) -> str:
        """使用requests库作为备选方案获取页面内容"""
        import aiohttp
        import random
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0"
        }
        
        # 添加一些随机延迟
        await asyncio.sleep(random.uniform(1, 3))
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=30) as response:
                    if response.status == 200:
                        return await response.text()
                    else:
                        print(f"请求失败，状态码: {response.status}")
                        return ""
        except Exception as e:
            print(f"使用requests获取页面失败: {str(e)}")
            return ""
    
    def parse_article_list(self, html: str, is_top_news: bool = False):
        """重写文章列表解析方法，处理NYTimes特有的HTML结构"""
        soup = BeautifulSoup(html, 'lxml')
        articles = []
        
        # 使用头条新闻选择器或普通文章选择器
        selector = self.site_config["top_news_selector"] if is_top_news else self.site_config["article_selector"]
        article_elements = soup.select(selector)
        
        # 如果没有找到文章，尝试使用更通用的选择器
        if not article_elements:
            print(f"未找到文章，尝试使用通用选择器")
            article_elements = soup.select("article")
        
        # 限制新闻数量
        article_elements = article_elements[:self.max_news]
        
        for article in article_elements:
            try:
                title_elem = article.select_one(self.site_config["title_selector"])
                link_elem = article.select_one(self.site_config["link_selector"])
                summary_elem = article.select_one(self.site_config["summary_selector"])
                time_elem = article.select_one(self.site_config["time_selector"])
                
                if title_elem and link_elem:
                    url = link_elem.get("href", "")
                    # 处理相对URL
                    if url and not url.startswith("http"):
                        url = f"https://www.nytimes.com{url}"
                    
                    articles.append({
                        "title": title_elem.get_text(strip=True),
                        "url": url,
                        "summary": summary_elem.get_text(strip=True) if summary_elem else "",
                        "publish_time": time_elem.get_text(strip=True) if time_elem else "",
                        "content": "",
                        "is_top_news": is_top_news
                    })
            except Exception as e:
                print(f"Error parsing NYTimes article: {str(e)}")
        
        return articles
    
    async def fetch_article_content(self, url: str) -> str:
        """获取文章正文内容"""
        # 检查URL是否有效
        if not self.is_valid_article_url(url):
            print(f"跳过无效的文章URL: {url}")
            return ""
        
        print(f"获取文章内容: {url}")
        
        # 检查是否是未来日期的URL（测试数据）
        date_pattern = r'/(\d{4})/(\d{2})/(\d{2})/'
        date_match = re.search(date_pattern, url)
        if date_match:
            year, month, day = date_match.groups()
            try:
                article_date = datetime(int(year), int(month), int(day))
                current_date = datetime.now()
                
                # 如果是未来日期，返回提示信息
                if article_date > current_date:
                    print(f"检测到未来日期的文章URL: {url}，使用预览内容")
                    return "无法获取文章内容，可能是测试数据或未发布的文章。"
            except Exception as e:
                print(f"解析日期时出错: {str(e)}")
        
        # 正常获取文章内容
        html = await self.fetch_page(url)
        if not html:
            print(f"无法获取文章页面: {url}")
            return "无法获取文章内容，请稍后再试。"
        
        soup = BeautifulSoup(html, 'lxml')
        
        # 尝试多种可能的选择器
        content_selectors = [
            self.site_config["content_selector"],
            "section[name='articleBody'] p",
            "div.StoryBodyCompanionColumn p",
            ".meteredContent p",
            "article p",
            ".article-content p",
            "div.article__body p",
            "div[data-testid='article-body'] p",
            "div.article-body p",
            "main p"
        ]
        
        content = ""
        for selector in content_selectors:
            content_elements = soup.select(selector)
            if content_elements:
                print(f"使用选择器 {selector} 找到 {len(content_elements)} 段内容")
                # 过滤掉标题和摘要，只保留正文内容
                filtered_elements = [p for p in content_elements if not any(
                    existing in p.get_text(strip=True) 
                    for existing in [self.site_config.get("title", ""), self.site_config.get("summary", "")]
                )]
                content = "\n".join([p.get_text(strip=True) for p in filtered_elements])
                break
        
        # 如果无法获取正文内容，尝试构建一个更丰富的预览
        if not content:
            print(f"无法获取正文内容，尝试构建预览: {url}")
            preview_content = []
            
            # 1. 尝试获取文章摘要
            summary_elements = soup.select("p.summary, .article-summary, .css-w6ymp8, .css-1l5zmz6, .css-16nhkrn, meta[name='description']")
            if summary_elements:
                for elem in summary_elements:
                    if elem.name == "meta":
                        summary = elem.get("content", "")
                    else:
                        summary = elem.get_text(strip=True)
                    if summary and len(summary) > 20:  # 确保摘要有足够长度
                        preview_content.append(summary)
            
            # 2. 尝试获取图片描述
            image_captions = soup.select("figcaption, .caption, .css-1l5zmz6, .css-16nhkrn")
            for caption in image_captions:
                caption_text = caption.get_text(strip=True)
                if caption_text and len(caption_text) > 15 and caption_text not in preview_content:
                    preview_content.append(f"图片描述: {caption_text}")
            
            # 3. 尝试获取引用或突出显示的文本
            quotes = soup.select("blockquote, .pullquote, .css-1l5zmz6, .css-16nhkrn")
            for quote in quotes:
                quote_text = quote.get_text(strip=True)
                if quote_text and len(quote_text) > 20 and quote_text not in preview_content:
                    preview_content.append(f"引用: {quote_text}")
            
            # 4. 尝试获取任何段落文本
            paragraphs = soup.find_all("p")
            filtered_paragraphs = [p for p in paragraphs if p.get_text(strip=True) and len(p.get_text(strip=True)) > 30]
            if filtered_paragraphs:
                for p in filtered_paragraphs[:3]:  # 只取前3段
                    p_text = p.get_text(strip=True)
                    if p_text not in preview_content:
                        preview_content.append(p_text)
            
            if preview_content:
                return "\n\n".join(preview_content)
            else:
                # 如果仍然没有内容，返回一个提示信息
                return "无法提取文章内容，可能需要订阅或登录才能访问。纽约时报的大多数文章需要订阅才能阅读完整内容。"
            
        return content