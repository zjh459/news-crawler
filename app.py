"""
新闻爬虫Web应用
"""

import os
import sys
import json
import asyncio
import threading
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

# 确保能够导入news_crawler包
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入爬虫相关模块
from news_crawler.utils.crawler_runner import CrawlerRunner
from news_crawler.config import NEWS_SITES

app = Flask(__name__)

# 创建必要的目录
os.makedirs('templates', exist_ok=True)
os.makedirs('static', exist_ok=True)
os.makedirs('news_crawler/data', exist_ok=True)

# 全局变量，存储爬虫任务状态
crawler_tasks = {}
thread_pool = ThreadPoolExecutor(max_workers=4)

def run_async_task(coro):
    """在新的事件循环中运行协程"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

@app.route('/')
def index():
    """首页，显示爬虫配置界面"""
    return render_template('index.html')

@app.route('/start_crawler', methods=['POST'])
def start_crawler():
    """启动爬虫"""
    crawl_type = request.form.get('crawl_type', 'foxnews')
    max_articles = int(request.form.get('max_articles', 10))
    save_to_db = request.form.get('save_to_db') == 'on'
    save_to_file = request.form.get('save_to_file') == 'on'
    custom_url = request.form.get('custom_url', '')
    
    # 创建任务ID
    task_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 启动爬虫任务
    crawler_tasks[task_id] = {
        'crawl_type': crawl_type,
        'url': custom_url if crawl_type == 'url' else None,
        'max_articles': max_articles,
        'save_to_db': save_to_db,
        'save_to_file': save_to_file,
        'status': 'running',
        'start_time': datetime.now().isoformat(),
        'result': None
    }
    
    # 在线程池中运行爬虫任务
    thread_pool.submit(run_async_task, run_crawler(task_id))
    
    return redirect(url_for('tasks'))

@app.route('/tasks')
def tasks():
    """显示爬虫任务列表"""
    return render_template('tasks.html', tasks=crawler_tasks)

@app.route('/task/<task_id>')
def task_detail(task_id):
    """显示爬虫任务详情"""
    if task_id not in crawler_tasks:
        return "任务不存在", 404
    
    task = crawler_tasks[task_id]
    
    # 如果任务已完成且有结果，读取结果文件
    result_data = None
    if task['status'] == 'completed' and task['result']:
        try:
            with open(task['result'], 'r', encoding='utf-8') as f:
                result_data = json.load(f)
        except Exception as e:
            result_data = f"读取结果文件失败: {e}"
    
    return render_template('task_detail.html', task_id=task_id, task=task, result_data=result_data)

@app.route('/download/<task_id>/<format>')
def download_result(task_id, format):
    """下载爬取结果"""
    if task_id not in crawler_tasks:
        return "任务不存在", 404
    
    task = crawler_tasks[task_id]
    if not task['result'] or task['status'] != 'completed':
        return "任务未完成或无结果", 404
    
    # 获取文件路径
    json_file = task['result']
    if not os.path.exists(json_file):
        return "文件不存在", 404
        
    # 根据格式确定下载文件
    if format == 'json':
        return send_file(
            json_file,
            mimetype='application/json',
            as_attachment=True,
            download_name=f"news_data_{task_id}.json"
        )
    elif format == 'excel':
        # 从JSON文件路径获取Excel文件路径
        excel_file = os.path.splitext(json_file)[0] + '.xlsx'
        if not os.path.exists(excel_file):
            # 如果Excel文件不存在，尝试从JSON创建
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # 将数据转换为DataFrame
                if isinstance(data, dict):  # 如果是多个网站的结果
                    # 合并所有网站的数据
                    all_articles = []
                    for site, articles in data.items():
                        for article in articles:
                            article['site'] = site
                            all_articles.append(article)
                    df = pd.DataFrame(all_articles)
                else:  # 如果是单个网站的结果
                    df = pd.DataFrame(data)
                
                # 重新排列列的顺序
                columns = ['title', 'url', 'publish_time', 'content', 'source', 'category', 'author', 'site']
                existing_columns = [col for col in columns if col in df.columns]
                other_columns = [col for col in df.columns if col not in columns]
                final_columns = existing_columns + other_columns
                
                # 保存为Excel
                df[final_columns].to_excel(excel_file, index=False, engine='openpyxl')
            except Exception as e:
                return f"创建Excel文件失败: {str(e)}", 500
        
        return send_file(
            excel_file,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f"news_data_{task_id}.xlsx"
        )
    else:
        return "不支持的格式", 400

async def run_crawler(task_id):
    """运行爬虫任务"""
    task = crawler_tasks[task_id]
    
    try:
        # 创建爬虫运行器
        runner = CrawlerRunner(
            save_to_db=task['save_to_db'],
            save_to_file=task['save_to_file']
        )
        
        # 根据抓取类型选择不同的抓取方式
        if task['crawl_type'] == 'url' and task['url']:
            # 抓取单个 URL
            articles = await runner.scrape_single_url(task['url'])
            total_articles = 1 if articles else 0
        else:
            # 抓取 Fox News 首页
            articles = await runner.run_scraper('foxnews', task['max_articles'])
            total_articles = len(articles)
        
        # 更新任务状态
        task['status'] = 'completed'
        task['end_time'] = datetime.now().isoformat()
        task['total_articles'] = total_articles
        
        # 保存结果到文件
        result_file = f"news_crawler/data/task_{task_id}.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
        
        task['result'] = result_file
    
    except Exception as e:
        # 更新任务状态为失败
        task['status'] = 'failed'
        task['end_time'] = datetime.now().isoformat()
        task['error'] = str(e)
        print(f"爬虫任务失败: {e}")  # 添加错误日志
    
    finally:
        # 关闭爬虫
        runner.close()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)