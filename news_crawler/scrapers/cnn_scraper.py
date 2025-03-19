from bs4 import BeautifulSoup
from urllib.parse import urljoin
from .base_scraper import BaseScraper
from ..config.config import NEWS_SITES

class CNNScraper(BaseScraper):
    def __init__(self):
        super().__init__(NEWS_SITES["cnn"])
    
    def is_valid_article_url(self, url: str) -> bool:
        """
        验证文章URL是否有效
        """
        if not url:
            return False
            
        # 确保URL是CNN的
        if not url.startswith(self.site_config["url"]):
            return False
            
        # 排除一些非文章页面
        invalid_patterns = [
            "/videos/", "/live-news/", "/gallery/",
            "/profiles/", "/weather/", "/account/",
            "/search", "/about/", "/terms/", "/privacy/"
        ]
        
        return not any(pattern in url.lower() for pattern in invalid_patterns)
    
    def extract_summary(self, article_element: BeautifulSoup) -> str:
        """
        从文章元素中提取摘要，使用多种策略
        """
        # 1. 尝试从class中提取摘要
        summary_selectors = [
            ["div", {"class_": lambda x: x and any(c in str(x).lower() for c in [
                "description", "summary", "article-description", "article-summary",
                "article-dek", "article-deck", "article-excerpt", "article-standfirst"
            ])}],
            ["p", {"class_": lambda x: x and any(c in str(x).lower() for c in [
                "description", "summary", "dek", "deck", "excerpt", "standfirst"
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
                "content", "article-content", "article-body", "story-content"
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
            debug_file = f"cnn_debug.html"
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
            article_elements = soup.select(self.site_config["article_selector"])
            print(f"找到 {len(article_elements)} 个文章元素")
            
            for article in article_elements:
                try:
                    # 调试信息
                    print(f"处理文章元素: {article.get('class', ['无类名'])}")
                    
                    # 查找标题元素 - 使用多种选择器
                    title_elem = None
                    title_selectors = [
                        "h3", ".container__title-text", ".container__headline-text", 
                        ".card__headline-text", ".headline", ".headline__text"
                    ]
                    
                    for selector in title_selectors:
                        title_elem = article.select_one(selector)
                        if title_elem:
                            print(f"找到标题元素: {selector}")
                            break
                    
                    if not title_elem:
                        print("未找到标题元素，跳过")
                        continue
                    
                    # 提取标题
                    title = title_elem.get_text(strip=True)
                    if not title:
                        print("标题为空，跳过")
                        continue
                    
                    # 查找链接元素 - 先在标题元素中查找，再在整个文章元素中查找
                    link_elem = None
                    if title_elem.name == "a":
                        link_elem = title_elem
                    elif title_elem.find("a"):
                        link_elem = title_elem.find("a")
                    else:
                        # 在整个文章元素中查找链接
                        link_elem = article.find("a")
                    
                    if not link_elem or not link_elem.get("href"):
                        print(f"未找到链接元素，跳过: {title}")
                        continue
                    
                    # 提取URL
                    url = link_elem.get("href", "")
                    
                    # 处理相对URL
                    if url and not url.startswith("http"):
                        url = urljoin(self.site_config["url"], url)
                    
                    print(f"找到文章: {title}, URL: {url}")
                    
                    # 提取摘要
                    summary = self.extract_summary(article)
                    
                    # 查找时间
                    time = ""
                    time_elem = article.select_one(self.site_config["time_selector"])
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
                            "is_top_news": False,
                            "element_html": str(article)
                        }
                        
                        # 检查是否已存在相同URL的文章
                        if not any(a["url"] == url for a in articles):
                            articles.append(article_data)
                            print(f"添加文章: {title}")
                            
                            # 如果已经达到最大数量，停止爬取
                            if len(articles) >= self.max_news:
                                break
                except Exception as e:
                    print(f"解析文章时出错: {str(e)}")
                    continue
            
            print(f"共找到 {len(articles)} 篇文章")
            
            if not articles:
                print("未找到任何文章，请检查选择器是否正确")
                return []
            
            # 获取文章内容
            print("开始获取文章内容...")
            from datetime import datetime
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 为每篇文章获取内容
            for article in articles:
                try:
                    print(f"获取文章内容: {article['url']}")
                    article_html = await self.fetch_page(article['url'])
                    if article_html:
                        article_soup = BeautifulSoup(article_html, 'lxml')
                        
                        # 提取文章内容
                        content_selectors = [
                            ".article__content",
                            ".article-body",
                            ".article__body",
                            ".body-text",
                            ".zn-body__paragraph",
                            ".article-content",
                            ".article"  # 添加更通用的选择器
                        ]
                        
                        content = []
                        for selector in content_selectors:
                            paragraphs = article_soup.select(f"{selector} p")
                            if paragraphs:
                                content = [p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)]
                                if content:  # 确保找到了内容
                                    break
                        
                        if not content:
                            # 如果没有找到内容，尝试直接查找所有段落
                            paragraphs = article_soup.select("article p, .article p, .content p")
                            content = [p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)]
                        
                        if content:
                            article['content'] = "\n\n".join(content)
                            
                            # 使用前三段作为摘要
                            summary_text = "\n".join(content[:3])
                            if len(summary_text) > 500:
                                dot_pos = summary_text[:500].rfind('.')
                                if dot_pos > 0:
                                    summary_text = summary_text[:dot_pos + 1]
                                else:
                                    summary_text = summary_text[:500] + "..."
                            article['summary'] = summary_text
                        
                        # 提取发布时间
                        time_selectors = [
                            'meta[property="article:published_time"]',
                            'meta[property="og:article:published_time"]',
                            'time[datetime]',
                            '.timestamp',
                            '.article-date',
                            '.publish-time'
                        ]
                        
                        for selector in time_selectors:
                            if selector.startswith('meta['):
                                prop = selector[selector.find('property="')+10:selector.find('"]')]
                                time_elem = article_soup.find('meta', property=prop)
                            else:
                                time_elem = article_soup.select_one(selector)
                                
                            if time_elem:
                                if time_elem.name == 'meta':
                                    article['publish_time'] = time_elem.get('content', '')
                                else:
                                    article['publish_time'] = time_elem.get('datetime', '') or time_elem.get_text(strip=True)
                                break
                        
                        # 随机延迟，避免请求过快
                        await self.random_delay()
                        
                except Exception as e:
                    print(f"获取文章内容时出错: {str(e)}")
                    import traceback
                    print(f"错误详情:\n{traceback.format_exc()}")
                    continue
                    
                # 添加爬取时间和来源
                article["crawl_time"] = current_time
                article["source"] = self.site_config["name"]
            
            # 保存数据到 JSON 文件
            if articles:
                print(f"保存 {len(articles)} 篇文章到 JSON 文件")
                self.save_to_json(articles)
            
            return articles
            
        except Exception as e:
            print(f"爬取 {self.site_config['name']} 时出错: {str(e)}")
            return [] 