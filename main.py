"""
新闻爬虫主程序
"""

import asyncio
import argparse
import sys
from news_crawler.utils.crawler_runner import CrawlerRunner

async def main(args):
    """
    主函数
    
    Args:
        args: 命令行参数
    """
    # 创建爬虫运行器
    runner = CrawlerRunner(save_to_db=not args.no_db, save_to_file=not args.no_file)
    
    try:
        if args.site == "all":
            # 运行所有爬虫
            results = await runner.run_all(args.max_articles)
            total_articles = sum(len(articles) for articles in results.values())
            print(f"共爬取 {total_articles} 篇文章")
            for site, articles in results.items():
                print(f"- {site}: {len(articles)} 篇")
        else:
            # 运行指定爬虫
            articles = await runner.run_scraper(args.site, args.max_articles)
            print(f"共爬取 {len(articles)} 篇文章")
    finally:
        # 关闭资源
        runner.close()

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="新闻爬虫")
    parser.add_argument("--site", type=str, default="all", 
                        choices=["all", "sina", "163", "bbc", "foxnews"],
                        help="要爬取的网站，默认为all（所有网站）")
    parser.add_argument("--max-articles", type=int, default=10,
                        help="每个网站最大爬取文章数，默认为10")
    parser.add_argument("--no-db", action="store_true",
                        help="不保存到数据库")
    parser.add_argument("--no-file", action="store_true",
                        help="不保存到文件")
    return parser.parse_args()

if __name__ == "__main__":
    # 解析命令行参数
    args = parse_args()
    
    # 运行主函数
    asyncio.run(main(args)) 