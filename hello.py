"""
新闻爬虫Web界面
提供Web界面来配置和运行爬虫
"""

import os
import sys
import json
import asyncio
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for

# 确保能够导入news_crawler包
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入爬虫相关模块
from news_crawler.utils.crawler_runner import CrawlerRunner
from news_crawler.config import NEWS_SITES

app = Flask(__name__)

# 创建templates目录
os.makedirs('templates', exist_ok=True)

# 创建static目录
os.makedirs('static', exist_ok=True)

# 创建数据目录
os.makedirs('news_crawler/data', exist_ok=True)

# 全局变量，存储爬虫任务状态
crawler_tasks = {}

@app.route('/')
def index():
    """首页，显示爬虫配置界面"""
    return render_template('index.html', sites=NEWS_SITES)

@app.route('/start_crawler', methods=['POST'])
def start_crawler():
    """启动爬虫"""
    site = request.form.get('site', 'all')
    max_articles = int(request.form.get('max_articles', 10))
    save_to_db = request.form.get('save_to_db') == 'on'
    save_to_file = request.form.get('save_to_file') == 'on'
    translate = request.form.get('translate') == 'on'
    
    # 创建任务ID
    task_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 启动爬虫任务
    crawler_tasks[task_id] = {
        'site': site,
        'max_articles': max_articles,
        'save_to_db': save_to_db,
        'save_to_file': save_to_file,
        'translate': translate,
        'status': 'running',
        'start_time': datetime.now().isoformat(),
        'result': None
    }
    
    # 异步运行爬虫
    asyncio.run(run_crawler(task_id))
    
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

@app.route('/api/tasks')
def api_tasks():
    """API: 获取所有任务状态"""
    return jsonify(crawler_tasks)

@app.route('/api/task/<task_id>')
def api_task(task_id):
    """API: 获取指定任务状态"""
    if task_id not in crawler_tasks:
        return jsonify({"error": "任务不存在"}), 404
    
    return jsonify(crawler_tasks[task_id])

async def run_crawler(task_id):
    """运行爬虫任务"""
    task = crawler_tasks[task_id]
    
    try:
        # 创建爬虫运行器
        runner = CrawlerRunner(
            save_to_db=task['save_to_db'],
            save_to_file=task['save_to_file'],
            translate=task['translate']
        )
        
        # 运行爬虫
        if task['site'] == 'all':
            results = await runner.run_all(task['max_articles'])
            total_articles = sum(len(articles) for articles in results.values())
            
            # 更新任务状态
            task['status'] = 'completed'
            task['end_time'] = datetime.now().isoformat()
            task['total_articles'] = total_articles
            
            # 保存结果到文件
            result_file = f"news_crawler/data/task_{task_id}.json"
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            task['result'] = result_file
            
        else:
            articles = await runner.run_scraper(task['site'], task['max_articles'])
            
            # 更新任务状态
            task['status'] = 'completed'
            task['end_time'] = datetime.now().isoformat()
            task['total_articles'] = len(articles)
            
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
    
    finally:
        # 关闭爬虫
        runner.close()

# 创建HTML模板
def create_templates():
    """创建HTML模板文件"""
    # 创建index.html
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write("""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>新闻爬虫控制面板</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css">
    <style>
        body { padding-top: 20px; }
        .container { max-width: 800px; }
    </style>
</head>
<body>
    <div class="container">
        <h1 class="mb-4">新闻爬虫控制面板</h1>
        
        <div class="card mb-4">
            <div class="card-header">
                <h5 class="card-title">配置爬虫</h5>
            </div>
            <div class="card-body">
                <form action="/start_crawler" method="post">
                    <div class="mb-3">
                        <label for="site" class="form-label">选择网站</label>
                        <select class="form-select" id="site" name="site">
                            <option value="all">所有网站</option>
                            {% for site_key, site_config in sites.items() %}
                            <option value="{{ site_key }}">{{ site_config.name }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    
                    <div class="mb-3">
                        <label for="max_articles" class="form-label">最大文章数</label>
                        <input type="number" class="form-control" id="max_articles" name="max_articles" value="10" min="1" max="100">
                    </div>
                    
                    <div class="mb-3 form-check">
                        <input type="checkbox" class="form-check-input" id="save_to_db" name="save_to_db" checked>
                        <label class="form-check-label" for="save_to_db">保存到数据库</label>
                    </div>
                    
                    <div class="mb-3 form-check">
                        <input type="checkbox" class="form-check-input" id="save_to_file" name="save_to_file" checked>
                        <label class="form-check-label" for="save_to_file">保存到文件</label>
                    </div>
                    
                    <div class="mb-3 form-check">
                        <input type="checkbox" class="form-check-input" id="translate" name="translate">
                        <label class="form-check-label" for="translate">翻译内容（使用DeepSeek）</label>
                    </div>
                    
                    <button type="submit" class="btn btn-primary">开始爬取</button>
                </form>
            </div>
        </div>
        
        <div class="d-flex justify-content-between mb-4">
            <a href="/tasks" class="btn btn-secondary">查看任务列表</a>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>""")
    
    # 创建tasks.html
    with open('templates/tasks.html', 'w', encoding='utf-8') as f:
        f.write("""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>爬虫任务列表 - 新闻爬虫控制面板</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css">
    <style>
        body { padding-top: 20px; }
        .container { max-width: 800px; }
    </style>
</head>
<body>
    <div class="container">
        <h1 class="mb-4">爬虫任务列表</h1>
        
        <div class="card mb-4">
            <div class="card-header">
                <h5 class="card-title">任务列表</h5>
            </div>
            <div class="card-body">
                {% if tasks %}
                <div class="table-responsive">
                    <table class="table table-striped">
                        <thead>
                            <tr>
                                <th>任务ID</th>
                                <th>网站</th>
                                <th>状态</th>
                                <th>开始时间</th>
                                <th>文章数</th>
                                <th>操作</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for task_id, task in tasks.items() %}
                            <tr>
                                <td>{{ task_id }}</td>
                                <td>{{ task.site }}</td>
                                <td>
                                    {% if task.status == 'running' %}
                                    <span class="badge bg-primary">运行中</span>
                                    {% elif task.status == 'completed' %}
                                    <span class="badge bg-success">已完成</span>
                                    {% elif task.status == 'failed' %}
                                    <span class="badge bg-danger">失败</span>
                                    {% endif %}
                                </td>
                                <td>{{ task.start_time }}</td>
                                <td>{{ task.total_articles if task.status == 'completed' else '-' }}</td>
                                <td>
                                    <a href="/task/{{ task_id }}" class="btn btn-sm btn-info">详情</a>
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
                {% else %}
                <p class="text-center">暂无任务</p>
                {% endif %}
            </div>
        </div>
        
        <div class="d-flex justify-content-between mb-4">
            <a href="/" class="btn btn-secondary">返回首页</a>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // 自动刷新页面，每5秒刷新一次
        setTimeout(function() {
            location.reload();
        }, 5000);
    </script>
</body>
</html>""")
    
    # 创建task_detail.html
    with open('templates/task_detail.html', 'w', encoding='utf-8') as f:
        f.write("""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>任务详情 - 新闻爬虫控制面板</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css">
    <style>
        body { padding-top: 20px; }
        .container { max-width: 800px; }
        pre { background-color: #f8f9fa; padding: 15px; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h1 class="mb-4">任务详情</h1>
        
        <div class="card mb-4">
            <div class="card-header">
                <h5 class="card-title">任务信息</h5>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-6">
                        <p><strong>任务ID:</strong> {{ task_id }}</p>
                        <p><strong>网站:</strong> {{ task.site }}</p>
                        <p><strong>最大文章数:</strong> {{ task.max_articles }}</p>
                        <p><strong>保存到数据库:</strong> {{ '是' if task.save_to_db else '否' }}</p>
                        <p><strong>保存到文件:</strong> {{ '是' if task.save_to_file else '否' }}</p>
                        <p><strong>翻译内容:</strong> {{ '是' if task.translate else '否' }}</p>
                    </div>
                    <div class="col-md-6">
                        <p><strong>状态:</strong> 
                            {% if task.status == 'running' %}
                            <span class="badge bg-primary">运行中</span>
                            {% elif task.status == 'completed' %}
                            <span class="badge bg-success">已完成</span>
                            {% elif task.status == 'failed' %}
                            <span class="badge bg-danger">失败</span>
                            {% endif %}
                        </p>
                        <p><strong>开始时间:</strong> {{ task.start_time }}</p>
                        <p><strong>结束时间:</strong> {{ task.end_time if task.end_time else '-' }}</p>
                        <p><strong>文章数:</strong> {{ task.total_articles if task.status == 'completed' else '-' }}</p>
                        {% if task.error %}
                        <p><strong>错误信息:</strong> {{ task.error }}</p>
                        {% endif %}
                    </div>
                </div>
            </div>
        </div>
        
        {% if result_data %}
        <div class="card mb-4">
            <div class="card-header">
                <h5 class="card-title">爬取结果</h5>
            </div>
            <div class="card-body">
                {% if task.site == 'all' %}
                <ul class="nav nav-tabs" id="resultTabs" role="tablist">
                    {% for site in result_data.keys() %}
                    <li class="nav-item" role="presentation">
                        <button class="nav-link {% if loop.first %}active{% endif %}" 
                                id="{{ site }}-tab" 
                                data-bs-toggle="tab" 
                                data-bs-target="#{{ site }}" 
                                type="button" 
                                role="tab" 
                                aria-controls="{{ site }}" 
                                aria-selected="{% if loop.first %}true{% else %}false{% endif %}">
                            {{ site }}
                        </button>
                    </li>
                    {% endfor %}
                </ul>
                <div class="tab-content mt-3" id="resultTabsContent">
                    {% for site, articles in result_data.items() %}
                    <div class="tab-pane fade {% if loop.first %}show active{% endif %}" 
                         id="{{ site }}" 
                         role="tabpanel" 
                         aria-labelledby="{{ site }}-tab">
                        <h6>共 {{ articles|length }} 篇文章</h6>
                        {% if articles %}
                        <div class="accordion" id="{{ site }}-accordion">
                            {% for article in articles %}
                            <div class="accordion-item">
                                <h2 class="accordion-header" id="{{ site }}-heading-{{ loop.index }}">
                                    <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#{{ site }}-collapse-{{ loop.index }}" aria-expanded="false" aria-controls="{{ site }}-collapse-{{ loop.index }}">
                                        {{ article.title }}
                                        {% if article.title_cn %}
                                        <br><small class="text-muted">{{ article.title_cn }}</small>
                                        {% endif %}
                                    </button>
                                </h2>
                                <div id="{{ site }}-collapse-{{ loop.index }}" class="accordion-collapse collapse" aria-labelledby="{{ site }}-heading-{{ loop.index }}" data-bs-parent="#{{ site }}-accordion">
                                    <div class="accordion-body">
                                        <p><strong>链接:</strong> <a href="{{ article.url }}" target="_blank">{{ article.url }}</a></p>
                                        <p><strong>来源:</strong> {{ article.source }}</p>
                                        <p><strong>发布时间:</strong> {{ article.published_at }}</p>
                                        <p><strong>爬取时间:</strong> {{ article.crawled_at }}</p>
                                        {% if article.summary %}
                                        <p><strong>摘要:</strong> {{ article.summary }}</p>
                                        {% endif %}
                                        {% if article.summary_cn %}
                                        <p><strong>摘要(中文):</strong> {{ article.summary_cn }}</p>
                                        {% endif %}
                                        {% if article.content %}
                                        <div>
                                            <strong>内容:</strong>
                                            <pre>{{ article.content[:500] }}{% if article.content|length > 500 %}...{% endif %}</pre>
                                        </div>
                                        {% endif %}
                                        {% if article.content_cn %}
                                        <div>
                                            <strong>内容(中文):</strong>
                                            <pre>{{ article.content_cn[:500] }}{% if article.content_cn|length > 500 %}...{% endif %}</pre>
                                        </div>
                                        {% endif %}
                                    </div>
                                </div>
                            </div>
                            {% endfor %}
                        </div>
                        {% else %}
                        <p>未找到文章</p>
                        {% endif %}
                    </div>
                    {% endfor %}
                </div>
                {% else %}
                <h6>共 {{ result_data|length }} 篇文章</h6>
                {% if result_data %}
                <div class="accordion" id="articles-accordion">
                    {% for article in result_data %}
                    <div class="accordion-item">
                        <h2 class="accordion-header" id="heading-{{ loop.index }}">
                            <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapse-{{ loop.index }}" aria-expanded="false" aria-controls="collapse-{{ loop.index }}">
                                {{ article.title }}
                                {% if article.title_cn %}
                                <br><small class="text-muted">{{ article.title_cn }}</small>
                                {% endif %}
                            </button>
                        </h2>
                        <div id="collapse-{{ loop.index }}" class="accordion-collapse collapse" aria-labelledby="heading-{{ loop.index }}" data-bs-parent="#articles-accordion">
                            <div class="accordion-body">
                                <p><strong>链接:</strong> <a href="{{ article.url }}" target="_blank">{{ article.url }}</a></p>
                                <p><strong>来源:</strong> {{ article.source }}</p>
                                <p><strong>发布时间:</strong> {{ article.published_at }}</p>
                                <p><strong>爬取时间:</strong> {{ article.crawled_at }}</p>
                                {% if article.summary %}
                                <p><strong>摘要:</strong> {{ article.summary }}</p>
                                {% endif %}
                                {% if article.summary_cn %}
                                <p><strong>摘要(中文):</strong> {{ article.summary_cn }}</p>
                                {% endif %}
                                {% if article.content %}
                                <div>
                                    <strong>内容:</strong>
                                    <pre>{{ article.content[:500] }}{% if article.content|length > 500 %}...{% endif %}</pre>
                                </div>
                                {% endif %}
                                {% if article.content_cn %}
                                <div>
                                    <strong>内容(中文):</strong>
                                    <pre>{{ article.content_cn[:500] }}{% if article.content_cn|length > 500 %}...{% endif %}</pre>
                                </div>
                                {% endif %}
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
                {% else %}
                <p>未找到文章</p>
                {% endif %}
                {% endif %}
            </div>
        </div>
        {% endif %}
        
        <div class="d-flex justify-content-between mb-4">
            <a href="/tasks" class="btn btn-secondary">返回任务列表</a>
            <a href="/" class="btn btn-primary">返回首页</a>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/js/bootstrap.bundle.min.js"></script>
    {% if task.status == 'running' %}
    <script>
        // 如果任务正在运行，自动刷新页面，每5秒刷新一次
        setTimeout(function() {
            location.reload();
        }, 5000);
    </script>
    {% endif %}
</body>
</html>""")

# 创建模板文件
create_templates()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 