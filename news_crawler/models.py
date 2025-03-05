"""
数据库模型文件，定义新闻文章的数据结构
"""

import sqlite3
import json
import os
from datetime import datetime
from news_crawler.config import DB_CONFIG

class NewsDatabase:
    """新闻数据库类，用于存储和检索新闻文章"""
    
    def __init__(self, db_path=None):
        """初始化数据库连接"""
        self.db_path = db_path or DB_CONFIG['db_path']
        # 确保数据库目录存在
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self._create_tables()
    
    def _create_tables(self):
        """创建数据库表"""
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS news_articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            url TEXT UNIQUE NOT NULL,
            source TEXT NOT NULL,
            summary TEXT,
            content TEXT,
            published_at TEXT,
            crawled_at TEXT NOT NULL,
            metadata TEXT
        )
        ''')
        self.conn.commit()
    
    def save_article(self, article):
        """保存新闻文章到数据库"""
        try:
            metadata = json.dumps(article.get('metadata', {}), ensure_ascii=False)
            self.cursor.execute('''
            INSERT OR REPLACE INTO news_articles 
            (title, url, source, summary, content, published_at, crawled_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                article.get('title', ''),
                article.get('url', ''),
                article.get('source', ''),
                article.get('summary', ''),
                article.get('content', ''),
                article.get('published_at', ''),
                article.get('crawled_at', datetime.now().isoformat()),
                metadata
            ))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"保存文章失败: {e}")
            return False
    
    def get_article_by_url(self, url):
        """根据URL获取文章"""
        self.cursor.execute('SELECT * FROM news_articles WHERE url = ?', (url,))
        row = self.cursor.fetchone()
        if row:
            column_names = [description[0] for description in self.cursor.description]
            return dict(zip(column_names, row))
        return None
    
    def get_articles_by_source(self, source, limit=50):
        """根据来源获取文章列表"""
        self.cursor.execute('SELECT * FROM news_articles WHERE source = ? ORDER BY crawled_at DESC LIMIT ?', 
                           (source, limit))
        rows = self.cursor.fetchall()
        column_names = [description[0] for description in self.cursor.description]
        return [dict(zip(column_names, row)) for row in rows]
    
    def get_latest_articles(self, limit=50):
        """获取最新的文章列表"""
        self.cursor.execute('SELECT * FROM news_articles ORDER BY crawled_at DESC LIMIT ?', (limit,))
        rows = self.cursor.fetchall()
        column_names = [description[0] for description in self.cursor.description]
        return [dict(zip(column_names, row)) for row in rows]
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close() 