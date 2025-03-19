"""
代理管理器类，用于管理和验证代理服务器
"""
import aiohttp
import asyncio
from typing import List, Set
from ..config.config import CRAWLER_CONFIG

class ProxyManager:
    def __init__(self):
        self.proxy_pool = set(CRAWLER_CONFIG["proxy_pool"])
        self.working_proxies: Set[str] = set()
        self.failed_proxies: Set[str] = set()
        self.test_url = "https://www.google.com"  # 用于测试代理的URL
        self.timeout = CRAWLER_CONFIG["timeout"]
        self.headers = CRAWLER_CONFIG["headers"]
    
    async def test_proxy(self, proxy: str) -> bool:
        """测试代理是否可用"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.test_url,
                    proxy=proxy,
                    headers=self.headers,
                    timeout=self.timeout,
                    ssl=False
                ) as response:
                    return response.status == 200
        except Exception:
            return False
    
    async def verify_proxies(self):
        """验证所有代理"""
        tasks = []
        for proxy in self.proxy_pool:
            tasks.append(self.test_proxy(proxy))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        self.working_proxies.clear()
        self.failed_proxies.clear()
        
        for proxy, is_working in zip(self.proxy_pool, results):
            if isinstance(is_working, bool) and is_working:
                self.working_proxies.add(proxy)
            else:
                self.failed_proxies.add(proxy)
    
    def get_working_proxy(self) -> str:
        """获取一个可用的代理"""
        if not self.working_proxies:
            return next(iter(self.proxy_pool))  # 如果没有可用代理，返回第一个代理
        return next(iter(self.working_proxies))
    
    @property
    def has_working_proxies(self) -> bool:
        """检查是否有可用代理"""
        return len(self.working_proxies) > 0
    
    def remove_proxy(self, proxy: str):
        """移除失效的代理"""
        self.proxy_pool.discard(proxy)
        self.working_proxies.discard(proxy)
        self.failed_proxies.add(proxy)
    
    def add_proxy(self, proxy: str):
        """添加新的代理"""
        self.proxy_pool.add(proxy)
    
    def get_proxy_stats(self) -> dict:
        """获取代理统计信息"""
        return {
            "total": len(self.proxy_pool),
            "working": len(self.working_proxies),
            "failed": len(self.failed_proxies)
        } 