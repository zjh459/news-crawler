"""
Fox News专用爬虫类
"""
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper, PLAYWRIGHT_AVAILABLE
from ..config.config import NEWS_SITES
import re
from typing import List, Dict
from urllib.parse import urljoin

class FoxNewsScraper(BaseScraper):
    def __init__(self):
        super().__init__(NEWS_SITES["foxnews"])
    
    def extract_summary(self, article_element: BeautifulSoup) -> str:
        """
        从文章元素中提取摘要,使用多种策略
        """
        # 1. 尝试从class中提取摘要
        summary_selectors = [
            ["p", "div"], {"class_": lambda x: x and any(c in str(x).lower() for c in [
                "dek", "article-dek", "summary", "description", "teaser", "excerpt", "standfirst",
                "sub-headline", "article-summary", "article-description"
            ])}
        ]
        summary_elem = article_element.find(*summary_selectors)
        if summary_elem:
            return summary_elem.get_text(strip=True)
            
        # 2. 尝试从meta标签提取摘要
        meta_selectors = [
            'meta[name="description"]',
            'meta[property="og:description"]',
            'meta[name="twitter:description"]'
        ]
        for selector in meta_selectors:
            meta = article_element.find("meta", attrs={"content": True, **dict(item.split("=") for item in selector[5:-1].split(" "))})
            if meta:
                return meta["content"]
                
        # 3. 尝试使用第一段文本作为摘要
        first_p = article_element.find("p")
        if first_p:
            text = first_p.get_text(strip=True)
            # 确保文本长度合适
            if 10 <= len(text) <= 500:
                return text
                
        # 4. 尝试从文章内容中提取前几句话
        content_selectors = [
            ["div", "section"], {"class_": lambda x: x and any(c in str(x).lower() for c in [
                "content", "article-content", "article-body", "story-content"
            ])}
        ]
        content_elem = article_element.find(*content_selectors)
        if content_elem:
            text = content_elem.get_text(strip=True)
            # 提取前200个字符,在句号处截断
            if len(text) > 200:
                dot_pos = text[:200].rfind('.')
                if dot_pos > 0:
                    return text[:dot_pos + 1]
                return text[:200] + "..."
            return text
            
        return ""
    
    async def scrape(self):
        """执行爬虫任务"""
        try:
            # 初始化爬虫
            await self.initialize()
            
            print(f"开始爬取 {self.site_config['name']}...")
            
            # 获取页面内容
            html = await self.fetch_page(self.site_config["url"])
            if not html:
                print(f"Failed to fetch content from {self.site_config['name']}")
                return []
            
            print(f"成功获取 {self.site_config['name']} 页面内容，长度: {len(html)} 字符")
            
            # 保存HTML内容用于调试
            debug_file = f"foxnews_debug.html"
            with open(debug_file, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"已保存HTML内容到 {debug_file} 用于调试")
            
            # 直接使用更通用的方法解析文章
            soup = BeautifulSoup(html, 'lxml')
            
            # 打印页面标题，确认页面内容正确
            page_title = soup.title.text if soup.title else "无标题"
            print(f"页面标题: {page_title}")
            
            # 查找头条新闻区域
            print("查找头条新闻区域...")
            top_news = []
            
            # 头条新闻选择器
            top_news_selectors = [
                "main .main .primary",  # 主要头条区域
                "main .main .top-story",  # 顶部故事
                "main .main .primary-content",  # 主要内容区域
                "main .main .main-primary",  # 主要区域
                ".collection-spotlight",  # 聚焦区域
                ".collection-hero",  # 英雄区域
                ".main-content .top-story",  # 主要内容中的顶部故事
                ".main-content .primary"  # 主要内容中的主要区域
            ]
            
            for selector in top_news_selectors:
                top_elements = soup.select(selector)
                if top_elements:
                    print(f"在头条区域 '{selector}' 找到 {len(top_elements)} 个元素")
                    
                    for top_element in top_elements:
                        # 在头条区域中查找文章
                        article_elements = top_element.find_all(["article", "div", "section"], class_=lambda x: x and any(c in str(x) for c in ["article", "story", "item"]))
                        if not article_elements:
                            # 如果没有找到子元素，将整个元素视为一篇文章
                            article_elements = [top_element]
                        
                        for article in article_elements:
                            try:
                                # 查找标题
                                title_elem = article.find(["h1", "h2", "h3", "h4", "a"], class_=lambda x: x and any(c in str(x) for c in ["title", "headline", "heading"]))
                                if not title_elem:
                                    continue
                                
                                # 查找链接
                                link_elem = article.find("a", href=True)
                                if not link_elem and title_elem.name == "a" and title_elem.get("href"):
                                    link_elem = title_elem
                                
                                if not link_elem:
                                    continue
                                
                                # 提取标题和URL
                                title = title_elem.get_text(strip=True)
                                url = link_elem.get("href", "")
                                
                                # 处理相对URL
                                if url and not url.startswith("http"):
                                    url = urljoin("https://www.foxnews.com", url)
                                
                                # 提取摘要
                                summary = self.extract_summary(article)
                                
                                # 查找时间
                                time = ""
                                time_elem = article.find(["time", "span"], class_=lambda x: x and any(c in str(x) for c in ["time", "date"]))
                                if time_elem:
                                    time = time_elem.get_text(strip=True)
                                
                                # 只添加有效的文章
                                if title and url and self.is_valid_article_url(url):
                                    article_data = {
                                        "title": title,
                                        "url": url,
                                        "summary": summary,
                                        "publish_time": time,
                                        "content": summary,  # 先使用摘要作为内容
                                        "is_top_news": True,  # 这是头条新闻
                                        "element_html": str(article)
                                    }
                                    
                                    # 检查是否已存在相同URL的文章
                                    if not any(a["url"] == url for a in top_news):
                                        top_news.append(article_data)
                                        print(f"找到头条文章: {title}")
                            except Exception as e:
                                print(f"解析头条文章时出错: {str(e)}")
            
            # 查找普通新闻
            print("查找普通新闻...")
            regular_news = []
            
            # 普通新闻选择器
            regular_selectors = [
                "article.article",  # 文章
                ".collection-article",  # 集合文章
                ".article-list article",  # 文章列表中的文章
                ".content article",  # 内容区域中的文章
                ".main-content article",  # 主要内容区域中的文章
                ".sidebar article",  # 侧边栏中的文章
                ".article-list .item",  # 文章列表中的项目
                ".collection-article-list .item"  # 文章集合列表中的项目
            ]
            
            for selector in regular_selectors:
                elements = soup.select(selector)
                print(f"使用选择器 '{selector}' 找到 {len(elements)} 个元素")
                
                for article in elements:
                    try:
                        # 查找标题
                        title_elem = article.find(["h2", "h3", "h4", "a"], class_=lambda x: x and any(c in str(x) for c in ["title", "headline", "heading"]))
                        if not title_elem:
                            continue
                        
                        # 查找链接
                        link_elem = article.find("a", href=True)
                        if not link_elem and title_elem.name == "a" and title_elem.get("href"):
                            link_elem = title_elem
                        
                        if not link_elem:
                            continue
                        
                        # 提取标题和URL
                        title = title_elem.get_text(strip=True)
                        url = link_elem.get("href", "")
                        
                        # 处理相对URL
                        if url and not url.startswith("http"):
                            url = urljoin("https://www.foxnews.com", url)
                        
                        # 提取摘要
                        summary = self.extract_summary(article)
                        
                        # 查找时间
                        time = ""
                        time_elem = article.find(["time", "span"], class_=lambda x: x and any(c in str(x) for c in ["time", "date"]))
                        if time_elem:
                            time = time_elem.get_text(strip=True)
                        
                        # 只添加有效的文章
                        if title and url and self.is_valid_article_url(url):
                            article_data = {
                                "title": title,
                                "url": url,
                                "summary": summary,
                                "publish_time": time,
                                "content": summary,  # 先使用摘要作为内容
                                "is_top_news": False,  # 这是普通新闻
                                "element_html": str(article)
                            }
                            
                            # 检查是否已存在相同URL的文章（包括头条新闻）
                            if not any(a["url"] == url for a in top_news) and not any(a["url"] == url for a in regular_news):
                                regular_news.append(article_data)
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
            
            if not articles:
                print("未找到任何文章，请检查选择器是否正确")
                return []
            
            # 获取文章内容
            print("开始获取文章内容...")
            from datetime import datetime
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            for article in articles:
                try:
                    title = article.get("title", "")
                    url = article.get("url", "")
                    print(f"获取文章内容: {title}")
                    
                    # 添加来源信息
                    article["source"] = "Fox News"
                    
                    # 添加抓取时间
                    article["crawl_time"] = current_time
                    
                    # 如果没有发布时间，设置为未知
                    if not article.get("publish_time"):
                        article["publish_time"] = "未知"
                    
                    # 获取文章内容
                    content = await self.fetch_article_content(url)
                    if content:
                        article["content"] = content
                    else:
                        # 如果无法获取内容，使用摘要或默认消息
                        if article.get("summary"):
                            article["content"] = article["summary"]
                        else:
                            article["content"] = "无法获取文章内容，请访问原文阅读。"
                except Exception as e:
                    print(f"获取文章内容失败: {str(e)}")
                    # 确保文章至少有一些内容
                    if not article.get("content"):
                        article["content"] = "获取内容时出错，请访问原文阅读。"
            
            # 保存数据
            self.save_to_json(articles)
            
            return articles
        except Exception as e:
            print(f"爬取 {self.site_config['name']} 失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    def is_valid_article_url(self, url: str) -> bool:
        """检查URL是否是有效的文章URL"""
        # 忽略主页和锚点链接
        if url in ["https://www.foxnews.com", "https://www.foxnews.com/"]:
            return False
        
        # 忽略非文章页面
        invalid_patterns = [
            "/search", "/video/", "/interactive/", "/slideshow/", 
            "/subscription", "/account", "/login", "/register",
            "/newsletters", "/games/", "/crosswords/", "/podcasts/",
            "/section/", "/live/", "/tips", "/privacy", "/terms",
            "/shows/", "/category/", "/tag/", "/person/"
        ]
        
        for pattern in invalid_patterns:
            if pattern in url:
                return False
        
        # 检查是否包含日期格式，这通常表示是文章
        date_pattern = r'/\d{4}/\d{2}/\d{2}/'
        if re.search(date_pattern, url):
            return True
        
        # 其他可能的文章URL格式
        if "/article/" in url or "/opinion/" in url or "/story/" in url or "/politics/" in url or "/us/" in url:
            return True
        
        return True  # 默认认为是有效的
    
    def parse_article_list(self, html: str, is_top_news: bool = False) -> List[Dict]:
        """解析文章列表"""
        soup = BeautifulSoup(html, 'lxml')
        articles = []
        
        # 使用头条新闻选择器或普通文章选择器
        selector = self.site_config["top_news_selector"] if is_top_news else self.site_config["article_selector"]
        article_elements = soup.select(selector)
        
        # 限制新闻数量
        article_elements = article_elements[:self.max_news]
        
        for article in article_elements:
            try:
                title_elem = article.select_one(self.site_config["title_selector"])
                link_elem = article.select_one(self.site_config["link_selector"])
                
                # 尝试多个可能的摘要选择器
                summary_selectors = [
                    ".dek",  # Fox News常用的摘要类
                    ".article-dek",
                    ".article-summary",
                    ".summary",
                    ".teaser",
                    ".description",
                    "p.article-text",
                    ".article-desc",
                    "meta[name='description']",
                    "meta[property='og:description']"
                ]
                
                summary = ""
                for selector in summary_selectors:
                    summary_elem = article.select_one(selector)
                    if summary_elem:
                        if summary_elem.name == "meta":
                            summary = summary_elem.get("content", "")
                        else:
                            summary = summary_elem.get_text(strip=True)
                        if summary:
                            break
                
                # 如果没有找到摘要，尝试使用第一段文本作为摘要
                if not summary:
                    first_p = article.find("p")
                    if first_p:
                        summary = first_p.get_text(strip=True)
                
                time_elem = article.select_one(self.site_config["time_selector"])
                
                if title_elem and link_elem:
                    url = link_elem.get("href", "")
                    # 确保URL是完整的
                    if url and not url.startswith(("http://", "https://")):
                        url = urljoin(self.site_config["url"], url)
                    
                    articles.append({
                        "title": title_elem.get_text(strip=True),
                        "url": url,
                        "summary": summary,
                        "publish_time": time_elem.get_text(strip=True) if time_elem else "",
                        "content": "",
                        "is_top_news": is_top_news
                    })
            except Exception as e:
                print(f"Error parsing article: {str(e)}")
                
        return articles
    
    async def fetch_article_content(self, url: str) -> str:
        """获取文章正文内容"""
        # 检查URL是否有效
        if not self.is_valid_article_url(url):
            print(f"跳过无效的文章URL: {url}")
            return ""
        
        print(f"获取文章内容: {url}")
        html = await self.fetch_page(url)
        if not html:
            return ""
        
        soup = BeautifulSoup(html, 'lxml')
        
        # 尝试多种可能的选择器
        content_selectors = [
            self.site_config["content_selector"],
            "div.article-body p",
            "div.article-content p",
            "article p",
            ".article__body p",
            ".article-text p",
            ".story-body p",
            ".article-container p",
            ".article-body-container p",
            ".content-primary p",
            ".main-content p",
            ".article-wrap p",
            ".article-body-text p"
        ]
        
        content = ""
        for selector in content_selectors:
            content_elements = soup.select(selector)
            if content_elements:
                print(f"使用选择器 {selector} 找到 {len(content_elements)} 段内容")
                # 过滤掉可能的广告或不相关内容
                filtered_elements = [p for p in content_elements if len(p.get_text(strip=True)) > 20]
                if filtered_elements:
                    content = "\n".join([p.get_text(strip=True) for p in filtered_elements])
                    break
        
        # 如果无法获取正文内容，尝试构建一个更丰富的预览
        if not content:
            print(f"无法获取正文内容，尝试构建预览: {url}")
            preview_content = []
            
            # 1. 尝试获取文章摘要
            summary_elements = soup.select("p.summary, .article-summary, .description, meta[name='description'], .teaser-content, .article-info")
            if summary_elements:
                for elem in summary_elements:
                    if elem.name == "meta":
                        summary = elem.get("content", "")
                    else:
                        summary = elem.get_text(strip=True)
                    if summary and len(summary) > 20:  # 确保摘要有足够长度
                        preview_content.append(summary)
            
            # 2. 尝试获取图片描述
            image_captions = soup.select("figcaption, .caption, .wp-caption-text")
            for caption in image_captions:
                caption_text = caption.get_text(strip=True)
                if caption_text and len(caption_text) > 15 and caption_text not in preview_content:
                    preview_content.append(f"图片描述: {caption_text}")
            
            # 3. 尝试获取引用或突出显示的文本
            quotes = soup.select("blockquote, .pullquote, .quote")
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
            
            # 5. 尝试获取作者信息
            author_elements = soup.select(".author-names, .byline, .author, .article-byline")
            if author_elements:
                for author_elem in author_elements:
                    author_text = author_elem.get_text(strip=True)
                    if author_text and len(author_text) > 5:
                        preview_content.append(f"作者: {author_text}")
            
            if preview_content:
                return "\n\n".join(preview_content)
            else:
                # 如果仍然没有内容，返回一个提示信息
                return "无法提取文章内容，请访问原文阅读完整内容。"
            
        return content 