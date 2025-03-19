"""
华盛顿邮报专用爬虫类
"""
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper, PLAYWRIGHT_AVAILABLE
from ..config.config import NEWS_SITES
import re

class WashingtonPostScraper(BaseScraper):
    def __init__(self):
        # 设置需要JavaScript渲染
        site_config = NEWS_SITES["washingtonpost"].copy()
        site_config["requires_js"] = True
        super().__init__(site_config)
    
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
            debug_file = f"washingtonpost_debug.html"
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
                ".main-content .top-story",  # 主要内容中的顶部故事
                ".main-content .main-stage",  # 主要内容中的主舞台
                ".homepage-hero",  # 首页英雄区域
                ".homepage-banner",  # 首页横幅
                ".top-leader-wrapper",  # 顶部领导者包装
                ".top-story",  # 顶部故事
                ".main-stage",  # 主舞台
                ".lede-package",  # 导语包
                ".chain-wrapper.top-chain"  # 顶部链条
            ]
            
            for selector in top_news_selectors:
                top_elements = soup.select(selector)
                if top_elements:
                    print(f"在头条区域 '{selector}' 找到 {len(top_elements)} 个元素")
                    
                    for top_element in top_elements:
                        # 在头条区域中查找文章
                        article_elements = top_element.find_all(["article", "div", "section"], class_=lambda x: x and any(c in str(x) for c in ["story", "article", "card"]))
                        if not article_elements:
                            # 如果没有找到子元素，将整个元素视为一篇文章
                            article_elements = [top_element]
                        
                        for article in article_elements:
                            try:
                                # 添加更多调试信息
                                print(f"处理头条元素: {article.get('class', '无类名')}")
                                
                                # 查找标题 - 尝试更多的选择器
                                title_elem = None
                                title_selectors = [
                                    ["h1", "h2", "h3", "h4", "a"], 
                                    ["h1", "h2", "h3", "h4", "a"], 
                                    ["div", "span"], 
                                    ["*"]  # 尝试任何元素
                                ]
                                title_class_patterns = [
                                    lambda x: x and any(c in str(x) for c in ["title", "headline"]),
                                    lambda x: x and any(c in str(x) for c in ["card-title", "headline-text"]),
                                    lambda x: x and any(c in str(x) for c in ["text", "label"]),
                                    lambda x: True  # 任何类
                                ]
                                
                                for tags, class_pattern in zip(title_selectors, title_class_patterns):
                                    for tag in tags:
                                        title_candidates = article.find_all(tag, class_=class_pattern)
                                        if title_candidates:
                                            # 选择文本最长的元素作为标题
                                            title_elem = max(title_candidates, key=lambda x: len(x.get_text(strip=True)))
                                            print(f"找到头条标题元素: {title_elem.name}, 类: {title_elem.get('class', '无')}")
                                            break
                                    if title_elem:
                                        break
                                
                                if not title_elem:
                                    # 如果仍然找不到标题，尝试直接获取卡片中的文本
                                    all_text = article.get_text(strip=True)
                                    if all_text and len(all_text) > 10:  # 确保文本足够长
                                        print(f"使用头条卡片文本作为标题: {all_text[:50]}...")
                                        # 创建一个虚拟元素
                                        from bs4 import Tag
                                        title_elem = Tag(name="div")
                                        title_elem.string = all_text
                                    else:
                                        print("未找到有效头条标题，跳过")
                                        continue
                                
                                # 查找链接 - 尝试更多的方法
                                link_elem = None
                                # 1. 首先检查标题元素本身是否是链接
                                if title_elem.name == "a" and title_elem.get("href"):
                                    link_elem = title_elem
                                
                                # 2. 检查标题元素的父元素是否是链接
                                if not link_elem and title_elem.parent and title_elem.parent.name == "a":
                                    link_elem = title_elem.parent
                                
                                # 3. 检查标题元素内部是否有链接
                                if not link_elem:
                                    link_elem = title_elem.find("a", href=True)
                                
                                # 4. 在整个卡片中查找链接
                                if not link_elem:
                                    all_links = article.find_all("a", href=True)
                                    if all_links:
                                        # 选择href最长的链接，通常是文章链接而不是其他功能链接
                                        link_elem = max(all_links, key=lambda x: len(x.get("href", "")))
                                
                                if not link_elem:
                                    print("未找到有效头条链接，跳过")
                                    continue
                                
                                # 提取标题和URL
                                title = title_elem.get_text(strip=True)
                                url = link_elem.get("href", "")
                                
                                # 处理相对URL
                                if url and not url.startswith("http"):
                                    url = f"https://www.washingtonpost.com{url}"
                                
                                print(f"提取到头条标题: {title}")
                                print(f"提取到头条URL: {url}")
                                
                                # 查找摘要
                                summary = ""
                                summary_elem = article.find(["p", "div", "span"], class_=lambda x: x and any(c in str(x) for c in ["description", "blurb", "summary", "teaser", "deck"]))
                                if summary_elem:
                                    summary = summary_elem.get_text(strip=True)
                                
                                # 查找时间
                                time = ""
                                time_elem = article.find(["time", "span", "div"], class_=lambda x: x and any(c in str(x) for c in ["time", "date", "timestamp", "published"]))
                                if time_elem:
                                    time = time_elem.get_text(strip=True)
                                
                                # 获取当前时间作为抓取时间
                                from datetime import datetime
                                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                
                                # 只添加有效的文章
                                if title and url and self.is_valid_article_url(url):
                                    article_data = {
                                        "title": title,
                                        "url": url,
                                        "summary": summary,
                                        "publish_time": time,
                                        "content": summary if summary else "文章预览暂无，请点击原文阅读。",
                                        "is_top_news": True,  # 这是头条新闻
                                        "element_html": str(article),
                                        "source": "The Washington Post",  # 添加来源
                                        "crawl_time": current_time  # 添加抓取时间
                                    }
                                    
                                    # 检查是否已存在相同URL的文章
                                    if not any(a["url"] == url for a in top_news):
                                        top_news.append(article_data)
                                        print(f"找到头条文章: {title}")
                            except Exception as e:
                                print(f"解析头条文章时出错: {str(e)}")
                                import traceback
                                traceback.print_exc()
            
            # 查找普通新闻
            print("查找普通新闻...")
            regular_news = []
            
            # 普通新闻选择器
            regular_selectors = [
                "div.story-list-story",  # 故事列表中的故事
                "div.card",  # 卡片
                "div.story",  # 故事
                "article",  # 文章
                ".grid-item",  # 网格项
                ".chain-wrapper .story",  # 链条中的故事
                ".story-list .story",  # 故事列表中的故事
                ".card-list .card"  # 卡片列表中的卡片
            ]
            
            for selector in regular_selectors:
                elements = soup.select(selector)
                print(f"使用选择器 '{selector}' 找到 {len(elements)} 个元素")
                
                for article in elements:
                    try:
                        # 添加更多调试信息
                        print(f"处理元素: {article.get('class', '无类名')}")
                        
                        # 查找标题 - 尝试更多的选择器
                        title_elem = None
                        title_selectors = [
                            ["h2", "h3", "h4", "a"], 
                            ["h2", "h3", "h4", "a"], 
                            ["div", "span"], 
                            ["*"]  # 尝试任何元素
                        ]
                        title_class_patterns = [
                            lambda x: x and any(c in str(x) for c in ["title", "headline"]),
                            lambda x: x and any(c in str(x) for c in ["card-title", "headline-text"]),
                            lambda x: x and any(c in str(x) for c in ["text", "label"]),
                            lambda x: True  # 任何类
                        ]
                        
                        for tags, class_pattern in zip(title_selectors, title_class_patterns):
                            for tag in tags:
                                title_candidates = article.find_all(tag, class_=class_pattern)
                                if title_candidates:
                                    # 选择文本最长的元素作为标题
                                    title_elem = max(title_candidates, key=lambda x: len(x.get_text(strip=True)))
                                    print(f"找到标题元素: {title_elem.name}, 类: {title_elem.get('class', '无')}")
                                    break
                            if title_elem:
                                break
                        
                        if not title_elem:
                            # 如果仍然找不到标题，尝试直接获取卡片中的文本
                            all_text = article.get_text(strip=True)
                            if all_text and len(all_text) > 10:  # 确保文本足够长
                                print(f"使用卡片文本作为标题: {all_text[:50]}...")
                                # 创建一个虚拟元素
                                from bs4 import Tag
                                title_elem = Tag(name="div")
                                title_elem.string = all_text
                            else:
                                print("未找到有效标题，跳过")
                                continue
                        
                        # 查找链接 - 尝试更多的方法
                        link_elem = None
                        # 1. 首先检查标题元素本身是否是链接
                        if title_elem.name == "a" and title_elem.get("href"):
                            link_elem = title_elem
                        
                        # 2. 检查标题元素的父元素是否是链接
                        if not link_elem and title_elem.parent and title_elem.parent.name == "a":
                            link_elem = title_elem.parent
                        
                        # 3. 检查标题元素内部是否有链接
                        if not link_elem:
                            link_elem = title_elem.find("a", href=True)
                        
                        # 4. 在整个卡片中查找链接
                        if not link_elem:
                            all_links = article.find_all("a", href=True)
                            if all_links:
                                # 选择href最长的链接，通常是文章链接而不是其他功能链接
                                link_elem = max(all_links, key=lambda x: len(x.get("href", "")))
                        
                        if not link_elem:
                            print("未找到有效链接，跳过")
                            continue
                        
                        # 提取标题和URL
                        title = title_elem.get_text(strip=True)
                        url = link_elem.get("href", "")
                        
                        # 处理相对URL
                        if url and not url.startswith("http"):
                            url = f"https://www.washingtonpost.com{url}"
                        
                        print(f"提取到标题: {title}")
                        print(f"提取到URL: {url}")
                        
                        # 查找摘要
                        summary = ""
                        summary_elem = article.find(["p", "div", "span"], class_=lambda x: x and any(c in str(x) for c in ["description", "blurb", "summary", "teaser", "deck"]))
                        if summary_elem:
                            summary = summary_elem.get_text(strip=True)
                        
                        # 查找时间
                        time = ""
                        time_elem = article.find(["time", "span", "div"], class_=lambda x: x and any(c in str(x) for c in ["time", "date", "timestamp", "published"]))
                        if time_elem:
                            time = time_elem.get_text(strip=True)
                        
                        # 获取当前时间作为抓取时间
                        from datetime import datetime
                        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        # 只添加有效的文章
                        if title and url and self.is_valid_article_url(url):
                            article_data = {
                                "title": title,
                                "url": url,
                                "summary": summary,
                                "publish_time": time,
                                "content": summary if summary else "文章预览暂无，请点击原文阅读。",
                                "is_top_news": False,  # 这是普通新闻
                                "element_html": str(article),
                                "source": "The Washington Post",  # 添加来源
                                "crawl_time": current_time  # 添加抓取时间
                            }
                            
                            # 检查是否已存在相同URL的文章（包括头条新闻）
                            if not any(a["url"] == url for a in top_news) and not any(a["url"] == url for a in regular_news):
                                regular_news.append(article_data)
                                print(f"找到普通文章: {title}")
                    except Exception as e:
                        print(f"解析普通文章时出错: {str(e)}")
                        import traceback
                        traceback.print_exc()
            
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
            for article in articles:
                title = article.get("title", "")
                url = article.get("url", "")
                print(f"获取文章内容: {title}")
                print(f"获取文章内容: {url}")
                
                # 获取文章内容
                content = await self.fetch_article_content(url)
                if content:
                    article["content"] = content
            
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
        if url in ["https://www.washingtonpost.com", "https://www.washingtonpost.com/"]:
            return False
        
        # 忽略非文章页面
        invalid_patterns = [
            "/search", "/video/", "/interactive/", "/slideshow/", 
            "/subscription", "/account", "/login", "/register",
            "/newsletters", "/games/", "/crosswords/", "/podcasts/",
            "/section/", "/live/", "/tips", "/privacy", "/terms"
        ]
        
        for pattern in invalid_patterns:
            if pattern in url:
                return False
        
        # 检查是否包含日期格式，这通常表示是文章
        date_pattern = r'/\d{4}/\d{2}/\d{2}/'
        if re.search(date_pattern, url):
            return True
        
        # 其他可能的文章URL格式
        if "/article/" in url or "/opinion/" in url or "/story/" in url:
            return True
        
        return True  # 默认认为是有效的
    
    def parse_article_list(self, html: str, is_top_news: bool = False):
        """重写文章列表解析方法，处理Washington Post特有的HTML结构"""
        soup = BeautifulSoup(html, 'lxml')
        articles = []
        
        # 使用头条新闻选择器或普通文章选择器
        selector = self.site_config["top_news_selector"] if is_top_news else self.site_config["article_selector"]
        article_elements = soup.select(selector)
        
        # 如果没有找到文章，尝试使用更通用的选择器
        if not article_elements:
            print(f"未找到文章，尝试使用通用选择器")
            # 尝试多种可能的选择器
            for possible_selector in [
                "div.story-headline", 
                "div.card", 
                "div.story", 
                "article"
            ]:
                article_elements = soup.select(possible_selector)
                if article_elements:
                    print(f"使用选择器 {possible_selector} 找到 {len(article_elements)} 篇文章")
                    break
        
        # 限制新闻数量
        article_elements = article_elements[:self.max_news]
        
        for article in article_elements:
            try:
                # 尝试多种可能的标题选择器
                title_elem = None
                for title_selector in ["h2", "h3", ".headline", ".title"]:
                    title_elem = article.select_one(title_selector)
                    if title_elem:
                        break
                
                # 尝试多种可能的链接选择器
                link_elem = None
                for link_selector in ["a", "h2 a", "h3 a", ".headline a"]:
                    link_elem = article.select_one(link_selector)
                    if link_elem:
                        break
                
                summary_elem = article.select_one(self.site_config["summary_selector"])
                time_elem = article.select_one(self.site_config["time_selector"])
                
                if title_elem and link_elem:
                    url = link_elem.get("href", "")
                    # 处理相对URL
                    if url and not url.startswith("http"):
                        url = f"https://www.washingtonpost.com{url}"
                    
                    articles.append({
                        "title": title_elem.get_text(strip=True),
                        "url": url,
                        "summary": summary_elem.get_text(strip=True) if summary_elem else "",
                        "publish_time": time_elem.get_text(strip=True) if time_elem else "",
                        "content": "",
                        "is_top_news": is_top_news
                    })
            except Exception as e:
                print(f"Error parsing Washington Post article: {str(e)}")
        
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
            return "无法获取文章内容，请稍后再试。"
        
        soup = BeautifulSoup(html, 'lxml')
        
        # 尝试多种可能的选择器
        content_selectors = [
            self.site_config["content_selector"],
            "article p",
            ".article-body p",
            ".story-body p",
            ".article-content p",
            "div.article__body p",
            ".story-text p",
            ".article p",
            "main p",
            ".main-content p",
            ".teaser-content p",
            ".article-wrapper p",
            "#article-body p",
            ".article-container p",
            ".grid-body p"
        ]
        
        content = ""
        for selector in content_selectors:
            content_elements = soup.select(selector)
            if content_elements:
                print(f"使用选择器 {selector} 找到 {len(content_elements)} 段内容")
                # 不再过滤内容，直接获取所有段落
                content = "\n".join([p.get_text(strip=True) for p in content_elements])
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
                return "无法提取文章内容，可能需要订阅或登录才能访问。华盛顿邮报的大多数文章需要订阅才能阅读完整内容。"
        
        return content 