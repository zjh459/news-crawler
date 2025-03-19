"""
Flask Web应用，用于展示爬取的新闻数据
"""
import os
import asyncio
import json
import glob
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request, send_file
from news_crawler.scrapers.foxnews_scraper import FoxNewsScraper
from news_crawler.scrapers.nytimes_scraper import NYTimesScraper
from news_crawler.scrapers.washingtonpost_scraper import WashingtonPostScraper
from news_crawler.scrapers.cnn_scraper import CNNScraper
from news_crawler.scrapers.bbc_scraper import BBCScraper
from news_crawler.scrapers.wsj_scraper import WSJScraper
from news_crawler.config.config import CRAWLER_CONFIG, NEWS_SITES
import pandas as pd
from io import BytesIO

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("news_crawler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 确保数据目录存在
os.makedirs(CRAWLER_CONFIG["save_path"], exist_ok=True)

# 爬虫类映射
SCRAPERS = {
    "foxnews": FoxNewsScraper,
    "nytimes": NYTimesScraper,
    "washingtonpost": WashingtonPostScraper,
    "cnn": CNNScraper,
    "bbc": BBCScraper,
    "wsj": WSJScraper
}

@app.route('/')
def index():
    """首页"""
    return render_template('index.html', news_sites=NEWS_SITES)

@app.route('/modern')
def modern():
    """现代风格首页"""
    return render_template('modern.html', news_sites=NEWS_SITES)

@app.route('/light')
def light():
    """浅色风格首页"""
    return render_template('light.html', news_sites=NEWS_SITES)

@app.route('/api/scrape')
async def scrape():
    """执行爬虫任务"""
    try:
        site = request.args.get('site', 'all')
        results = []
        
        logger.info(f"开始爬取网站: {site}")
        
        if site == 'all':
            # 爬取所有网站
            for site_id, scraper_class in SCRAPERS.items():
                try:
                    logger.info(f"爬取网站: {site_id}")
                    scraper = scraper_class()
                    articles = await scraper.scrape()
                    results.extend(articles)
                    logger.info(f"成功爬取 {site_id}: {len(articles)} 条新闻")
                except Exception as e:
                    logger.error(f"爬取 {site_id} 失败: {str(e)}")
        elif site in SCRAPERS:
            # 爬取指定网站
            try:
                scraper = SCRAPERS[site]()
                results = await scraper.scrape()
                logger.info(f"成功爬取 {site}: {len(results)} 条新闻")
            except Exception as e:
                logger.error(f"爬取 {site} 失败: {str(e)}")
                return jsonify({"status": "error", "message": f"爬取 {site} 失败: {str(e)}"})
        else:
            logger.error(f"无效的网站: {site}")
            return jsonify({"status": "error", "message": "无效的网站"})
        
        return jsonify({"status": "success", "count": len(results)})
    except Exception as e:
        logger.error(f"爬取失败: {str(e)}")
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/news')
async def get_news():
    """获取新闻列表"""
    try:
        site = request.args.get('site', 'all')
        date = request.args.get('date', None)  # 新增日期参数
        
        logger.info(f"获取新闻列表: 网站={site}, 日期={date}")
        
        news = []
        
        if site == 'all':
            # 获取所有网站的新闻文件
            for site_id, scraper_class in SCRAPERS.items():
                try:
                    scraper = scraper_class()
                    logger.info(f"尝试获取 {site_id} 的新闻文件")
                    if date:
                        # 获取指定日期的新闻
                        json_file = scraper.get_json_file_by_date(date)
                    else:
                        # 获取最新的新闻
                        json_file = scraper.get_latest_json_file()
                    
                    if json_file:
                        logger.info(f"{site_id} 的JSON文件: {json_file}")
                        site_news = scraper.get_articles_from_file(json_file)
                        logger.info(f"从 {site_id} 读取到 {len(site_news)} 条新闻")
                        news.extend(site_news)
                except Exception as e:
                    logger.error(f"获取 {site_id} 新闻失败: {str(e)}")
        else:
            # 获取指定网站的新闻文件
            if site in SCRAPERS:
                scraper = SCRAPERS[site]()
                logger.info(f"尝试获取 {site} 的新闻文件")
                if date:
                    # 获取指定日期的新闻
                    json_file = scraper.get_json_file_by_date(date)
                else:
                    # 获取最新的新闻
                    json_file = scraper.get_latest_json_file()
                
                if json_file:
                    logger.info(f"{site} 的JSON文件: {json_file}")
                    news = scraper.get_articles_from_file(json_file)
                    logger.info(f"从 {site} 读取到 {len(news)} 条新闻")
            else:
                logger.error(f"无效的网站: {site}")
                return jsonify({"status": "error", "message": "无效的网站"})
        
        # 按重要性排序
        news.sort(key=lambda x: x.get("importance", 0), reverse=True)
        
        logger.info(f"获取到 {len(news)} 条新闻")
        return jsonify({"status": "success", "news": news})
    except Exception as e:
        logger.error(f"获取新闻列表失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/dates')
async def get_available_dates():
    """获取可用的新闻日期列表"""
    try:
        site = request.args.get('site', 'all')
        
        logger.info(f"获取可用日期: {site}")
        
        dates = set()
        
        if site == 'all':
            # 获取所有网站的日期
            for site_id, scraper_class in SCRAPERS.items():
                try:
                    scraper = scraper_class()
                    site_dates = scraper.get_available_dates()
                    dates.update(site_dates)
                except Exception as e:
                    logger.error(f"获取 {site_id} 日期失败: {str(e)}")
        else:
            # 获取指定网站的日期
            if site in SCRAPERS:
                scraper = SCRAPERS[site]()
                dates = scraper.get_available_dates()
            else:
                logger.error(f"无效的网站: {site}")
                return jsonify({"status": "error", "message": "无效的网站"})
        
        # 将日期转换为列表并排序（最新的日期在前）
        date_list = sorted(list(dates), reverse=True)
        
        return jsonify({"status": "success", "dates": date_list})
    except Exception as e:
        logger.error(f"获取可用日期失败: {str(e)}")
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/status')
def status():
    """获取爬虫状态"""
    try:
        # 获取所有JSON文件
        json_files = glob.glob(os.path.join(CRAWLER_CONFIG["save_path"], "*.json"))
        
        # 统计每个网站的文章数量
        site_counts = {}
        total_count = 0
        
        for site_id in SCRAPERS.keys():
            site_files = [f for f in json_files if f.startswith(os.path.join(CRAWLER_CONFIG["save_path"], site_id.lower()))]
            
            if site_files:
                # 获取最新的文件
                latest_file = max(site_files, key=os.path.getmtime)
                
                try:
                    with open(latest_file, 'r', encoding='utf-8') as f:
                        articles = json.load(f)
                        site_counts[site_id] = len(articles)
                        total_count += len(articles)
                except Exception as e:
                    logger.error(f"读取JSON文件失败: {str(e)}")
                    site_counts[site_id] = 0
            else:
                site_counts[site_id] = 0
        
        return jsonify({
            "status": "success",
            "total_count": total_count,
            "site_counts": site_counts,
            "sites": list(SCRAPERS.keys()),
            "last_update": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"获取状态失败: {str(e)}")
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/export')
async def export_news():
    """导出新闻数据为Excel"""
    try:
        site = request.args.get('site', 'all')
        date = request.args.get('date', None)  # 新增日期参数
        logger.info(f"导出新闻数据: 网站={site}, 日期={date}")
        
        news = []
        
        if site == 'all':
            # 获取所有网站的新闻文件
            for site_id, scraper_class in SCRAPERS.items():
                try:
                    scraper = scraper_class()
                    if date:
                        # 获取指定日期的新闻
                        json_file = scraper.get_json_file_by_date(date)
                    else:
                        # 获取最新的新闻
                        json_file = scraper.get_latest_json_file()
                    
                    if json_file:
                        site_news = scraper.get_articles_from_file(json_file)
                        news.extend(site_news)
                except Exception as e:
                    logger.error(f"获取 {site_id} 新闻失败: {str(e)}")
        else:
            # 获取指定网站的新闻文件
            if site in SCRAPERS:
                scraper = SCRAPERS[site]()
                if date:
                    # 获取指定日期的新闻
                    json_file = scraper.get_json_file_by_date(date)
                else:
                    # 获取最新的新闻
                    json_file = scraper.get_latest_json_file()
                
                if json_file:
                    news = scraper.get_articles_from_file(json_file)
            else:
                return jsonify({"status": "error", "message": "无效的网站"})
        
        if not news:
            return jsonify({"status": "error", "message": "没有找到新闻数据"})
        
        # 创建DataFrame
        df = pd.DataFrame(news)
        
        # 选择要导出的列
        columns = ['title', 'url', 'summary', 'content', 'publish_time', 'crawl_time', 'source', 'is_top_news']
        df = df[columns]
        
        # 重命名列
        column_names = {
            'title': '标题',
            'url': '链接',
            'summary': '摘要',
            'content': '内容',
            'publish_time': '发布时间',
            'crawl_time': '抓取时间',
            'source': '来源',
            'is_top_news': '是否头条'
        }
        df = df.rename(columns=column_names)
        
        # 创建Excel文件
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='新闻数据')
        
        output.seek(0)
        
        # 生成文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        date_str = date if date else "latest"
        filename = f"news_data_{site}_{date_str}_{timestamp}.xlsx"
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"导出新闻数据失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    app.run(debug=True) 