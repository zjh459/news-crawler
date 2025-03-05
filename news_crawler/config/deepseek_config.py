"""
OpenRouter配置文件
包含通过OpenRouter接入DeepSeek R1模型的配置信息
"""

import os
import logging

logger = logging.getLogger(__name__)

# OpenRouter配置
DEEPSEEK_CONFIG = {
    # 优先使用环境变量，如果环境变量未设置则使用这里的配置
    "API_KEY": os.getenv("OPENROUTER_API_KEY", ""),  # 请设置您的OpenRouter API密钥或环境变量
    
    # OpenRouter API接口配置
    "API_BASE": os.getenv("OPENROUTER_API_BASE", "https://openrouter.ai/api/v1"),
    
    # 模型配置 - 使用OpenRouter上的DeepSeek R1模型
    "MODEL": os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat"),
    
    # 翻译配置
    "TRANSLATION": {
        "TEMPERATURE": 0.3,        # 温度参数，控制生成文本的随机性
        "MAX_TOKENS": 4000,        # 减少最大生成令牌数到4000
        "RETRY_TIMES": 3,          # 重试次数
        "RETRY_INTERVAL": 1,       # 重试间隔（秒）
    }
}

def validate_config():
    """
    验证OpenRouter配置是否有效
    """
    if not DEEPSEEK_CONFIG["API_KEY"]:
        logger.warning("请设置正确的 OPENROUTER_API_KEY 环境变量或在配置文件中直接设置API密钥")
        logger.warning("您可以通过以下方式设置环境变量:")
        logger.warning("  - Linux/Mac: export OPENROUTER_API_KEY=您的API密钥")
        logger.warning("  - Windows: set OPENROUTER_API_KEY=您的API密钥")
        logger.warning("或者直接在 news_crawler/config/deepseek_config.py 文件中设置 API_KEY 值")
        logger.warning("您可以在 https://openrouter.ai 注册并获取免费的API密钥")
        return False
        
    return True 