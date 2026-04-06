"""
日志管理模块
提供统一的日志记录功能
"""

import logging
import os
from datetime import datetime

# 创建 logs 目录
if not os.path.exists('logs'):
    os.makedirs('logs')

# 日志文件名（按日期）
log_filename = f"logs/app_{datetime.now().strftime('%Y%m%d')}.log"

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        # 文件处理器
        logging.FileHandler(log_filename, encoding='utf-8'),
        # 控制台处理器
        logging.StreamHandler()
    ]
)

# 创建日志记录器
logger = logging.getLogger('AI_Teaching_Assistant')

# 快捷函数
def debug(msg):
    logger.debug(msg)

def info(msg):
    logger.info(msg)

def warning(msg):
    logger.warning(msg)

def error(msg):
    logger.error(msg)

def critical(msg):
    logger.critical(msg)

# 数据库操作日志
def db_connect_success(db_name):
    info(f"✅ 数据库连接成功：{db_name}")

def db_connect_failed(db_name, error):
    error(f"❌ 数据库连接失败：{db_name} - {error}")

def db_operation_success(operation, details=""):
    info(f"✅ 数据库操作成功：{operation} {details}")

def db_operation_failed(operation, error):
    error(f"❌ 数据库操作失败：{operation} - {error}")

# AI 调用日志
def ai_request_start(model):
    info(f"🤖 开始调用 AI 模型：{model}")

def ai_request_success(model, tokens=None, time_ms=None):
    info(f"✅ AI 调用成功：{model}, Tokens: {tokens}, 耗时：{time_ms}ms")

def ai_request_failed(model, error):
    error(f"❌ AI 调用失败：{model} - {error}")

# 用户操作日志
def user_login(username, success=True):
    if success:
        info(f"👤 用户登录成功：{username}")
    else:
        warning(f"⚠️ 用户登录失败：{username}")

def user_upload_file(username, filename, file_type):
    info(f"📤 用户上传文件：{username} - {filename} ({file_type})")

def user_download_file(username, filename):
    info(f"📥 用户下载文件：{username} - {filename}")

def user_generate_courseware(username, topic, subject):
    info(f"🎓 用户生成课件：{username} - {topic} ({subject})")

# RAG 检索日志
def rag_search(keywords, results_count):
    info(f"🔍 RAG 检索：{keywords} - 找到 {results_count} 条结果")

def rag_add_document(title, subject):
    info(f"📚 添加知识文档：{title} ({subject})")
