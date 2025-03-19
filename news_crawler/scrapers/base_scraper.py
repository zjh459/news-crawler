"""
基础爬虫类，提供通用的爬虫功能
"""
import os
import json
import random
import aiohttp
import asyncio
import re
from datetime import datetime
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
from ..config.config import CRAWLER_CONFIG
from ..utils.proxy_manager import ProxyManager

# 尝试导入playwright，如果不可用则忽略
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

class BaseScraper:
    def __init__(self, site_config: Dict):
        self.site_config = site_config
        self.headers = CRAWLER_CONFIG["headers"]
        self.timeout = CRAWLER_CONFIG["timeout"]
        self.retry_times = CRAWLER_CONFIG["retry_times"]
        self.retry_interval = CRAWLER_CONFIG["retry_interval"]
        self.save_path = CRAWLER_CONFIG["save_path"]
        self.max_news = CRAWLER_CONFIG["max_news_per_site"]
        self.use_proxy = CRAWLER_CONFIG["use_proxy"] and site_config.get("use_proxy", False)
        self.requires_js = site_config.get("requires_js", False)
        self.delay_config = CRAWLER_CONFIG.get("random_delay", {"enabled": False, "min": 1, "max": 3})
        self.playwright_deps_missing = False
        
        if self.use_proxy:
            self.proxy_manager = ProxyManager()
        
        # 确保保存路径存在
        os.makedirs(self.save_path, exist_ok=True)
    
    async def initialize(self):
        """初始化爬虫，包括验证代理"""
        if self.use_proxy:
            await self.proxy_manager.verify_proxies()
            if not self.proxy_manager.has_working_proxies:
                print("Warning: No working proxies found!")
    
    async def random_delay(self):
        """随机延迟，避免被反爬虫机制检测"""
        if self.delay_config.get("enabled", False):
            delay = random.uniform(self.delay_config["min"], self.delay_config["max"])
            print(f"随机延迟 {delay:.2f} 秒")
            await asyncio.sleep(delay)
    
    async def fetch_with_requests(self, url: str) -> Optional[str]:
        """使用aiohttp获取页面内容"""
        proxy = None
        if self.use_proxy and hasattr(self, 'proxy_manager') and self.proxy_manager.has_working_proxies:
            proxy = self.proxy_manager.get_random_proxy()
        
        for i in range(self.retry_times):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        url, 
                        headers=self.headers, 
                        timeout=self.timeout,
                        proxy=proxy
                    ) as response:
                        if response.status == 200:
                            return await response.text()
                        else:
                            print(f"HTTP错误: {response.status} - {url}")
            except Exception as e:
                print(f"请求失败 ({i+1}/{self.retry_times}): {str(e)} - {url}")
                if i < self.retry_times - 1:
                    await asyncio.sleep(self.retry_interval)
                    # 如果使用代理且失败，尝试更换代理
                    if self.use_proxy and hasattr(self, 'proxy_manager') and self.proxy_manager.has_working_proxies:
                        proxy = self.proxy_manager.get_random_proxy()
        
        return None
    
    async def fetch_with_playwright(self, url: str) -> Optional[str]:
        """使用Playwright获取页面内容（支持JavaScript渲染）"""
        if not PLAYWRIGHT_AVAILABLE:
            print("Playwright不可用，请安装playwright包")
            return None
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent=self.headers["User-Agent"],
                    viewport={"width": 1920, "height": 1080}
                )
                page = await context.new_page()
                
                # 设置超时
                page.set_default_timeout(self.timeout * 1000)
                
                # 导航到URL
                await page.goto(url)
                
                # 等待页面加载完成
                await page.wait_for_load_state("networkidle")
                
                # 获取HTML内容
                html = await page.content()
                
                await browser.close()
                return html
        except Exception as e:
            print(f"Playwright错误: {str(e)}")
            self.playwright_deps_missing = "Chromium" in str(e)
            return None
    
    async def fetch_page(self, url: str) -> Optional[str]:
        """获取页面内容"""
        # 随机延迟
        await self.random_delay()
        
        # 如果网站需要JavaScript渲染，使用Playwright
        if self.requires_js and PLAYWRIGHT_AVAILABLE and not self.playwright_deps_missing:
            html = await self.fetch_with_playwright(url)
            if html:
                return html
            
            # 如果Playwright失败，尝试使用普通HTTP请求
            print("Playwright失败，尝试使用普通HTTP请求")
        
        # 使用普通HTTP请求
        return await self.fetch_with_requests(url)
    
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
                summary_elem = article.select_one(self.site_config["summary_selector"])
                time_elem = article.select_one(self.site_config["time_selector"])
                
                if title_elem and link_elem:
                    articles.append({
                        "title": title_elem.get_text(strip=True),
                        "url": link_elem.get("href", ""),
                        "summary": summary_elem.get_text(strip=True) if summary_elem else "",
                        "publish_time": time_elem.get_text(strip=True) if time_elem else "",
                        "content": "",
                        "is_top_news": is_top_news
                    })
            except Exception as e:
                print(f"Error parsing article: {str(e)}")
                
        return articles
    
    async def fetch_article_content(self, url: str) -> str:
        """获取文章正文内容"""
        html = await self.fetch_page(url)
        if not html:
            return ""
        
        soup = BeautifulSoup(html, 'lxml')
        content_elements = soup.select(self.site_config["content_selector"])
        return "\n".join([p.get_text(strip=True) for p in content_elements])
    
    def save_to_json(self, articles: List[Dict]):
        """保存文章到JSON文件"""
        # 确保 data 目录存在
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        print(f"保存目录: {data_dir}")
        os.makedirs(data_dir, exist_ok=True)
        
        # 生成文件名 - 使用 @ 符号，替换空格为下划线
        site_name = self.site_config['name'].lower().replace(' ', '_')
        filename = f"@{site_name}_{datetime.now().strftime('%Y%m%d')}.json"
        filepath = os.path.join(data_dir, filename)
        print(f"将保存到文件: {filepath}")
        print(f"文章数量: {len(articles)}")
        
        try:
            # 保存文件
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(articles, f, ensure_ascii=False, indent=2)
            print(f"成功保存到JSON文件: {filepath}")
            
            # 为了调试，打印文件是否存在和大小
            if os.path.exists(filepath):
                print(f"确认文件已创建: {filepath}")
                print(f"文件大小: {os.path.getsize(filepath)} 字节")
                print(f"文件权限: {oct(os.stat(filepath).st_mode)[-3:]}")
                print(f"所有者: {os.stat(filepath).st_uid}")
                print(f"用户组: {os.stat(filepath).st_gid}")
            else:
                print(f"警告：文件似乎未被创建: {filepath}")
            
            return filepath
        except Exception as e:
            print(f"保存JSON文件时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_latest_json_file(self):
        """获取最新的JSON文件路径"""
        # 使用 data 目录
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        if not os.path.exists(data_dir):
            print(f"数据目录不存在: {data_dir}")
            return None
            
        site_name = self.site_config['name'].lower().replace(' ', '_')
        print(f"查找网站 {site_name} 的JSON文件")
        json_files = [f for f in os.listdir(data_dir) if f.startswith(f"@{site_name}") and f.endswith('.json')]
        
        if not json_files:
            print(f"未找到网站 {site_name} 的JSON文件")
            return None
        
        # 按文件修改时间排序，返回最新的
        latest_file = max(json_files, key=lambda f: os.path.getmtime(os.path.join(data_dir, f)))
        full_path = os.path.join(data_dir, latest_file)
        print(f"找到最新的JSON文件: {full_path}")
        return full_path
    
    def get_json_file_by_date(self, date_str):
        """根据日期获取JSON文件路径"""
        # 使用 data 目录
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        if not os.path.exists(data_dir):
            print(f"数据目录不存在: {data_dir}")
            return None
            
        site_name = self.site_config['name'].lower().replace(' ', '_')
        print(f"查找网站 {site_name} 在日期 {date_str} 的JSON文件")
        
        # 构建文件名模式
        file_pattern = f"@{site_name}_{date_str}.json"
        full_path = os.path.join(data_dir, file_pattern)
        
        if os.path.exists(full_path):
            print(f"找到日期 {date_str} 的JSON文件: {full_path}")
            return full_path
        else:
            print(f"未找到日期 {date_str} 的JSON文件: {full_path}")
            return None
    
    def get_available_dates(self):
        """获取可用的新闻日期列表"""
        # 使用 data 目录
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        if not os.path.exists(data_dir):
            print(f"数据目录不存在: {data_dir}")
            return []
            
        site_name = self.site_config['name'].lower().replace(' ', '_')
        print(f"查找网站 {site_name} 的所有可用日期")
        
        # 查找所有匹配的JSON文件
        json_files = [f for f in os.listdir(data_dir) if f.startswith(f"@{site_name}") and f.endswith('.json')]
        
        # 从文件名中提取日期
        dates = []
        for file in json_files:
            # 文件名格式: @site_name_YYYYMMDD.json
            try:
                date_part = file.split('_')[-1].split('.')[0]
                if len(date_part) == 8 and date_part.isdigit():
                    dates.append(date_part)
            except Exception as e:
                print(f"从文件名 {file} 提取日期失败: {str(e)}")
        
        print(f"找到 {len(dates)} 个可用日期")
        return dates
    
    def get_articles_from_file(self, json_file):
        """从指定的JSON文件中获取文章"""
        if not json_file or not os.path.exists(json_file):
            return []
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                articles = json.load(f)
                # 添加来源信息
                for article in articles:
                    if not article.get('source'):
                        article['source'] = self.site_config['name']
                return articles
        except Exception as e:
            print(f"读取JSON文件失败: {str(e)}")
            return []
    
    def get_all_articles(self):
        """获取所有已保存的文章（兼容旧代码）"""
        json_file = self.get_latest_json_file()
        return self.get_articles_from_file(json_file)
    
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
            
            # 解析头条新闻
            top_news = self.parse_article_list(html, is_top_news=True)
            print(f"解析到 {len(top_news)} 条头条新闻")
            
            # 解析普通新闻
            regular_news = self.parse_article_list(html, is_top_news=False)
            print(f"解析到 {len(regular_news)} 条普通新闻")
            
            # 合并新闻列表，优先使用头条新闻
            articles = top_news
            
            # 如果头条新闻数量不足，补充普通新闻
            if len(articles) < self.max_news:
                # 过滤掉已经在头条新闻中的URL
                top_news_urls = {article["url"] for article in top_news}
                filtered_regular_news = [
                    article for article in regular_news 
                    if article["url"] not in top_news_urls
                ]
                
                remaining_slots = self.max_news - len(articles)
                articles.extend(filtered_regular_news[:remaining_slots])
            
            # 按照重要性排序（头条新闻优先，然后是普通新闻）
            # 同一类别内按照位置排序（假设网站将更重要的新闻放在前面）
            for i, article in enumerate(articles):
                # 设置一个重要性分数：头条新闻从100开始，普通新闻从50开始，然后按照顺序递减
                importance = 100 - i if article.get("is_top_news", False) else 50 - i
                article["importance"] = importance
            
            # 按重要性排序
            articles.sort(key=lambda x: x.get("importance", 0), reverse=True)
            
            # 限制总数量
            articles = articles[:self.max_news]
            
            if not articles:
                print(f"未找到任何文章，请检查选择器是否正确")
                return []
            
            print(f"共解析到 {len(articles)} 条新闻")
            
            # 获取文章内容
            for article in articles:
                if not article.get("content"):
                    print(f"获取文章内容: {article['title']}")
                    article["content"] = await self.fetch_article_content(article["url"])
            
            # 保存数据到JSON文件
            self.save_to_json(articles)
            
            return articles
        except Exception as e:
            print(f"爬取 {self.site_config['name']} 失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return [] 