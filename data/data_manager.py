"""
数据管理模块
统一管理数据持久化、缓存和数据库连接
"""
import streamlit as st
from datetime import datetime
import json
import os
from .db_operations import db
from .qa_db_operations import qa_db
from .rag_knowledge_base import rag_kb
from core.logger import info, warning, error


class LearningDataManager:
    """学习数据管理器"""
    
    @staticmethod
    @st.cache_data(ttl=300)
    def save_learning_data():
        """保存学习数据到本地文件"""
        try:
            data_to_save = {
                "questions": st.session_state.learning_data.get("questions", []),
                "interactions": st.session_state.learning_data.get("interactions", []),
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            with open("learning_data_backup.json", "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            error(f"保存学习数据失败：{str(e)}")
            return False
    
    @staticmethod
    def load_learning_data():
        """从本地文件加载学习数据"""
        try:
            if os.path.exists("learning_data_backup.json"):
                with open("learning_data_backup.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    st.session_state.learning_data["questions"] = data.get("questions", [])
                    st.session_state.learning_data["interactions"] = data.get("interactions", [])
                    info(f"✅ 从本地备份恢复了学习数据")
                    return True
        except Exception as e:
            warning(f"⚠️ 加载学习数据失败：{str(e)}")
        return False


class DatabaseManager:
    """数据库连接管理器"""
    
    @staticmethod
    @st.cache_resource(ttl=3600)
    def get_database_connections():
        """缓存数据库连接，1小时内复用"""
        connections = {
            'main': False,
            'qa': False,
            'rag': False
        }
        
        # 主数据库
        try:
            connections['main'] = db.connect()
            if connections['main']:
                info("✅ 主数据库连接成功")
            else:
                error("❌ 主数据库连接失败")
        except Exception as e:
            error(f"主数据库连接异常：{str(e)}")
        
        # 答疑数据库
        try:
            connections['qa'] = qa_db.connect()
            if connections['qa']:
                info("✅ 答疑数据库连接成功")
            else:
                error("❌ 答疑数据库连接失败")
        except Exception as e:
            error(f"答疑数据库连接异常：{str(e)}")
        
        # RAG 知识库
        try:
            connections['rag'] = rag_kb.connect()
            if connections['rag']:
                info("✅ RAG 知识库连接成功")
            else:
                error("❌ RAG 知识库连接失败")
        except Exception as e:
            error(f"RAG 知识库连接异常：{str(e)}")
        
        return connections
    
    @staticmethod
    def check_all_connections():
        """检查所有数据库连接状态"""
        status = {
            'main': db.is_connected() if hasattr(db, 'is_connected') else False,
            'qa': qa_db.is_connected() if hasattr(qa_db, 'is_connected') else False,
            'rag': rag_kb.is_connected() if hasattr(rag_kb, 'is_connected') else False
        }
        return status


class CacheManager:
    """缓存管理器"""
    
    @staticmethod
    @st.cache_data(ttl=3600)
    def load_env_config():
        """加载环境变量配置（带缓存）"""
        from dotenv import load_dotenv
        load_dotenv()
        return {
            'api_key': os.getenv('KIMI_API_KEY', ''),
            'base_url': os.getenv('KIMI_BASE_URL', 'https://api.moonshot.cn/v1')
        }
    
    @staticmethod
    def clear_cache(cache_type="all"):
        """清除缓存"""
        if cache_type in ["all", "data"]:
            st.cache_data.clear()
        if cache_type in ["all", "resource"]:
            st.cache_resource.clear()
