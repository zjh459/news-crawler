"""
DeepSeek配置
"""

import os
import logging

logger = logging.getLogger(__name__)

# DeepSeek配置
DEEPSEEK_CONFIG = {
    "API_KEY": "",  # 设置您的OpenRouter API密钥
    "MODEL": "deepseek-chat",
    "BASE_URL": "https://openrouter.ai/api/v1",
    "TEMPERATURE": 0.7,
    "MAX_TOKENS": 4000,
    "TOP_P": 0.9,
    "FREQUENCY_PENALTY": 0.0,
    "PRESENCE_PENALTY": 0.0,
    "STOP": None
}

# 验证配置
def validate_config():
    """验证配置是否有效"""
    if not DEEPSEEK_CONFIG["API_KEY"]:
        logger.warning("请设置正确的 OPENROUTER_API_KEY 环境变量或在配置文件中直接设置API密钥")
        logger.warning("您可以通过以下方式设置环境变量：")
        logger.warning("  - Linux/Mac: export OPENROUTER_API_KEY=您的API密钥")
        logger.warning("  - Windows: set OPENROUTER_API_KEY=您的API密钥")
        logger.warning("或者在 news_crawler/config/deepseek_config.py 文件中设置 API_KEY 值")
        return False
    return True 