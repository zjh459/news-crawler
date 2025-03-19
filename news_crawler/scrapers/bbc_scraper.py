from bs4 import BeautifulSoup
from urllib.parse import urljoin
from .base_scraper import BaseScraper
from ..config.config import NEWS_SITES

class BBCScraper(BaseScraper):
    def __init__(self):
        super().__init__(NEWS_SITES["bbc"])
    
    def extract_summary(self, article_element: BeautifulSoup) -> str:
        """
        从文章元素中提取摘要，使用多种策略
        """
        # 1. 尝试从class中提取摘要
        summary_selectors = [
            ["p", {"class_": lambda x: x and any(c in str(x).lower() for c in [
                "summary", "description", "article-summary", "article-description",
                "article-intro", "article-standfirst", "story-body__introduction"
            ])}],
            ["div", {"class_": lambda x: x and any(c in str(x).lower() for c in [
                "summary", "description", "article-summary", "article-description",
                "article-intro", "article-standfirst", "story-body__introduction"
            ])}]
        ]
        
        for selector in summary_selectors:
            summary_elem = article_element.find(*selector)
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
            ["div", {"class_": lambda x: x and any(c in str(x).lower() for c in [
                "story-body", "article-body", "article__body", "article-content"
            ])}]
        ]
        for selector in content_selectors:
            content_elem = article_element.find(*selector)
            if content_elem:
                text = content_elem.get_text(strip=True)
                # 提取前200个字符，在句号处截断
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
            debug_file = f"bbc_debug.html"
            with open(debug_file, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"已保存HTML内容到 {debug_file} 用于调试")
            
            # 解析页面
            soup = BeautifulSoup(html, 'lxml')
            
            # 打印页面标题，确认页面内容正确
            page_title = soup.title.text if soup.title else "无标题"
            print(f"页面标题: {page_title}")
            
            # 查找所有文章
            articles = []
            
            # 尝试多种选择器来找到文章元素
            selectors = [
                ".gs-c-promo",  # BBC文章容器
                ".nw-c-top-stories__secondary-item",  # 头条新闻
                ".nw-c-most-read__items li",  # 最多阅读
                ".sc-914f79f9-2, .sc-530fb3d6-1, .sc-e5949eb5-1",  # 新版文章容器
                "article",  # 通用文章标签
                ".media-list__item",  # 媒体列表项
                ".hard-news-unit__headline",  # 硬新闻标题
                ".faux-block-link",  # 伪块链接
                ".story-body",  # 故事正文
                ".story",  # 故事
                ".gel-layout__item"  # 布局项
            ]
            
            # 导航栏目标题列表，用于过滤
            navigation_sections = [
                "Israel-Gaza War", "War in Ukraine", "US & Canada", "UK", "Africa", "Asia", 
                "Australia", "Europe", "Latin America", "Middle East", "In Pictures", 
                "BBC InDepth", "BBC Verify", "UK Politics", "England", "N. Ireland", 
                "N. Ireland Politics", "Scotland", "Scotland Politics", "Wales", "Wales Politics",
                "Business", "Tech", "Science", "Health", "Entertainment & Arts", "World",
                "Stories", "Travel", "Weather"
            ]
            
            # 菜单项列表，用于过滤
            menu_items = [
                "Weather", "Newsletters", "Watch Live", "British Broadcasting Corporation", 
                "BBC News", "Home", "Sign in", "Sign up", "Settings", "Search BBC"
            ]
            
            for selector in selectors:
                article_elements = soup.select(selector)
                print(f"使用选择器 '{selector}' 找到 {len(article_elements)} 个元素")
                
                if article_elements:
                    for article in article_elements:
                        try:
                            # 查找标题
                            title = None
                            title_elem = None
                            
                            # 如果元素本身是标题
                            if article.name == "h2" or article.name == "h3":
                                title_elem = article
                            else:
                                # 尝试查找标题元素
                                for title_selector in [
                                    ".gs-c-promo-heading__title", 
                                    ".sc-87075214-3", 
                                    "h2", 
                                    "h3", 
                                    ".title", 
                                    ".headline",
                                    ".media__title",
                                    ".hard-news-unit__headline",
                                    ".story__headline",
                                    ".story__title"
                                ]:
                                    title_elem = article.select_one(title_selector)
                                    if title_elem:
                                        break
                            
                            # 如果找到标题元素，提取标题文本
                            if title_elem:
                                title = title_elem.get_text(strip=True)
                            elif article.name == "a" and article.get_text(strip=True):
                                # 如果元素本身是链接且有文本，使用链接文本作为标题
                                title = article.get_text(strip=True)
                            
                            # 查找链接
                            url = None
                            if article.name == "a" and article.get("href"):
                                url = article.get("href")
                            else:
                                # 尝试查找链接元素
                                for link_selector in ["a", ".gs-c-promo-heading a", "h2 a", "h3 a", ".media__link", ".faux-block-link__overlay-link"]:
                                    link_elem = article.select_one(link_selector)
                                    if link_elem and link_elem.get("href"):
                                        url = link_elem.get("href")
                                        break
                            
                            # 处理相对URL
                            if url and not url.startswith("http"):
                                url = urljoin(self.site_config["url"], url)
                            
                            # 过滤非新闻内容 - 大幅放宽条件
                            # 1. 检查是否是菜单项
                            is_menu = title in menu_items
                            
                            # 2. 检查是否有URL
                            has_url = url is not None and len(url) > 0
                            
                            # 只处理有效的新闻文章 - 大幅放宽条件
                            if title and has_url and not is_menu:
                                # 提取摘要
                                summary = self.extract_summary(article)
                                
                                # 查找时间
                                time = ""
                                time_selectors = [
                                    self.site_config["time_selector"], 
                                    ".sc-6fba5bd4-1", 
                                    "time", 
                                    ".date", 
                                    ".timestamp", 
                                    ".gs-c-timestamp",
                                    ".media__time",
                                    ".date--v2"
                                ]
                                for time_selector in time_selectors:
                                    time_elem = article.select_one(time_selector)
                                    if time_elem:
                                        time = time_elem.get_text(strip=True)
                                        break
                                
                                # 检查是否已存在相同URL的文章
                                if not any(a["url"] == url for a in articles):
                                    article_data = {
                                        "title": title,
                                        "url": url,
                                        "summary": summary,
                                        "publish_time": time,
                                        "content": summary,  # 先使用摘要作为内容
                                        "is_top_news": False
                                    }
                                    articles.append(article_data)
                                    print(f"找到文章: {title}")
                                    
                                    # 如果已经达到最大数量，停止爬取
                                    if len(articles) >= self.max_news:
                                        break
                            else:
                                if title:
                                    print(f"跳过非新闻内容: {title}")
                        except Exception as e:
                            print(f"解析文章时出错: {str(e)}")
                            continue
                
                # 如果已经找到足够的文章，停止尝试其他选择器
                if len(articles) >= self.max_news:
                    break
            
            print(f"共找到 {len(articles)} 篇文章")
            
            if not articles:
                print("未找到任何文章，请检查选择器是否正确")
                return []
            
            # 获取文章内容
            print("开始获取文章内容...")
            from datetime import datetime
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 为每篇文章添加爬取时间和来源
            for article in articles:
                article["crawl_time"] = current_time
                article["source"] = self.site_config["name"]
                
                # 获取文章详情页内容
                if article["url"]:
                    print(f"获取文章内容: {article['title']}")
                    try:
                        # 获取文章详情页
                        article_html = await self.fetch_page(article["url"])
                        if article_html:
                            # 保存文章HTML用于调试
                            article_debug_file = f"bbc_article_debug_{len(articles)}.html"
                            with open(article_debug_file, "w", encoding="utf-8") as f:
                                f.write(article_html)
                            print(f"已保存文章HTML到 {article_debug_file} 用于调试")
                            
                            # 解析文章内容
                            article_soup = BeautifulSoup(article_html, 'lxml')
                            
                            # 首先尝试提取文章摘要
                            meta_description = article_soup.find("meta", {"name": "description"})
                            if meta_description and meta_description.get("content"):
                                article["summary"] = meta_description.get("content")
                                print(f"从meta标签提取摘要: {article['summary'][:100]}...")
                            
                            # 尝试多种选择器来获取文章内容
                            content_selectors = [
                                "[data-component='text-block']",  # BBC新闻文本块
                                ".ssrcss-1q0x1qg-Paragraph",  # BBC段落类
                                ".ssrcss-1drmwog-Paragraph",  # 另一种BBC段落类
                                ".ssrcss-uf6wea-RichTextComponentWrapper",  # BBC富文本组件
                                ".article-body-component p",  # 文章正文组件
                                ".story-body__inner p",  # 旧版BBC文章
                                "article p",  # 通用文章段落
                                "main p",  # 主要内容区域段落
                                "[role='main'] p",  # 主要内容区域段落
                                ".body-content p"  # 正文内容
                            ]
                            
                            for selector in content_selectors:
                                content_elements = article_soup.select(selector)
                                if content_elements:
                                    # 过滤掉太短的段落和可能的导航元素
                                    valid_paragraphs = []
                                    for p in content_elements:
                                        text = p.get_text(strip=True)
                                        # 排除太短的段落和导航元素
                                        if len(text) > 20 and not any(nav in text.lower() for nav in [
                                            "sign in", "sign up", "newsletter", "follow us", "share this", 
                                            "related topics", "more on this story", "more stories", "read more",
                                            "watch more", "listen more", "copyright", "external sites", "advertisement"
                                        ]):
                                            valid_paragraphs.append(text)
                                    
                                    if valid_paragraphs:
                                        content = "\n\n".join(valid_paragraphs)
                                        if len(content) > 200:  # 确保内容有足够长度
                                            article["content"] = content
                                            print(f"成功获取文章内容，长度: {len(content)} 字符")
                                            break
                            
                            # 如果没有找到内容，尝试获取文章主体
                            if not article.get("content") or len(article["content"]) <= len(article["summary"]):
                                # 尝试获取整个文章主体
                                article_body_selectors = [
                                    "[data-component='text-block']",  # BBC新闻文本块
                                    "article",
                                    "main",
                                    ".story-body",
                                    ".article-body",
                                    ".ssrcss-pv1rh6-ArticleWrapper",
                                    "[role='main']"
                                ]
                                
                                for selector in article_body_selectors:
                                    body_element = article_soup.select_one(selector)
                                    if body_element:
                                        # 从主体中提取所有段落
                                        paragraphs = body_element.find_all("p")
                                        valid_paragraphs = []
                                        for p in paragraphs:
                                            text = p.get_text(strip=True)
                                            # 排除太短的段落和导航元素
                                            if len(text) > 20 and not any(nav in text.lower() for nav in [
                                                "sign in", "sign up", "newsletter", "follow us", "share this", 
                                                "related topics", "more on this story", "more stories", "read more",
                                                "watch more", "listen more", "copyright", "external sites", "advertisement"
                                            ]):
                                                valid_paragraphs.append(text)
                                        
                                        if valid_paragraphs:
                                            content = "\n\n".join(valid_paragraphs)
                                            if len(content) > 200:  # 确保内容有足够长度
                                                article["content"] = content
                                                print(f"从文章主体获取内容，长度: {len(content)} 字符")
                                                break
                            
                            # 如果仍然没有找到内容，使用摘要作为备选
                            if not article.get("content") or len(article["content"]) <= len(article["summary"]):
                                print(f"未找到文章内容，使用摘要作为备选")
                                article["content"] = article["summary"]
                    except Exception as e:
                        print(f"获取文章内容失败: {str(e)}")
                        # 如果获取失败，使用摘要作为备选
                        article["content"] = article["summary"]
            
            # 保存到JSON文件
            # 覆盖site_config中的name，确保生成正确的文件名
            original_name = self.site_config["name"]
            try:
                self.site_config["name"] = "bbc_news"  # 使用与其他代码匹配的名称
                self.save_to_json(articles)
            finally:
                # 恢复原始名称
                self.site_config["name"] = original_name
            
            return articles
            
        except Exception as e:
            print(f"爬取 {self.site_config['name']} 时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return [] 