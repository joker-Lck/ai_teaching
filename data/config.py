"""
数据库配置模块 - 统一管理所有数据库连接配置
使用环境变量管理敏感配置
"""

import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()


def get_db_config():
    """获取主数据库配置"""
    return {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', '3306')),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', '123456'),
        'database': os.getenv('DB_NAME', 'ai_teaching_assistant'),
        'charset': 'utf8mb4'
    }


def get_qa_db_config():
    """获取答疑数据库配置"""
    return {
        'host': os.getenv('QA_DB_HOST', 'localhost'),
        'port': int(os.getenv('QA_DB_PORT', '3306')),
        'user': os.getenv('QA_DB_USER', 'root'),
        'password': os.getenv('QA_DB_PASSWORD', '123456'),
        'database': os.getenv('QA_DB_NAME', 'ai_qa_records'),
        'charset': 'utf8mb4'
    }


def get_rag_db_config():
    """获取RAG知识库配置"""
    return {
        'host': os.getenv('RAG_DB_HOST', 'localhost'),
        'port': int(os.getenv('RAG_DB_PORT', '3306')),
        'user': os.getenv('RAG_DB_USER', 'root'),
        'password': os.getenv('RAG_DB_PASSWORD', '123456'),
        'database': os.getenv('RAG_DB_NAME', 'ai_rag_knowledge'),
        'charset': 'utf8mb4'
    }


def get_connection_string(db_type='main'):
    """获取数据库连接字符串"""
    if db_type == 'qa':
        config = get_qa_db_config()
    elif db_type == 'rag':
        config = get_rag_db_config()
    else:
        config = get_db_config()
    
    return f"mysql+pymysql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}?charset=utf8mb4"
