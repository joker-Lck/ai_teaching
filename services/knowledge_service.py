"""知识库管理服务模块"""
import streamlit as st
from data.rag_knowledge_base import rag_kb
from data.document_parser import doc_parser
from core.prompts import DocumentAnalysisPrompts
from openai import OpenAI


class KnowledgeService:
    """知识库管理业务逻辑服务"""
    
    def __init__(self):
        """初始化知识库服务"""
        self.client = None
    
    def _get_client(self, api_key, base_url):
        """获取 OpenAI 客户端"""
        if not self.client:
            self.client = OpenAI(api_key=api_key, base_url=base_url)
        return self.client
    
    def upload_documents(self, uploaded_files, category="通用"):
        """上传文档到知识库"""
        result = {
            "success": False,
            "uploaded_count": 0,
            "failed_files": [],
            "error": None
        }
        
        try:
            for file in uploaded_files:
                try:
                    # 解析文档
                    content_text = doc_parser.parse_file(file)
                    
                    if content_text:
                        # 向量化并存储
                        success = rag_kb.add_document(
                            title=file.name,
                            content_text=content_text,
                            file_type=file.type,
                            file_size=file.size,
                            subject=category,
                            metadata={
                                "original_filename": file.name,
                                "upload_time": str(__import__('datetime').datetime.now())
                            }
                        )
                        
                        if success:
                            result["uploaded_count"] += 1
                        else:
                            result["failed_files"].append(file.name)
                    else:
                        result["failed_files"].append(f"{file.name} (解析失败)")
                        
                except Exception as e:
                    result["failed_files"].append(f"{file.name} ({str(e)})")
            
            result["success"] = result["uploaded_count"] > 0
            
        except Exception as e:
            result["error"] = str(e)
            result["success"] = False
        
        return result
    
    def analyze_documents(self, documents, api_key, base_url):
        """AI 智能解析文档"""
        result = {"success": False, "analysis": "", "error": None}
        
        try:
            client = self._get_client(api_key, base_url)
            
            # 构建文档列表
            doc_list = "\n".join([
                f"- {doc['name']} ({doc['type']}, {doc['size']} bytes)" 
                for doc in documents
            ])
            
            prompt = DocumentAnalysisPrompts.get_knowledge_base_analysis_prompt(doc_list)
            
            response = client.chat.completions.create(
                model="moonshot-v1-8k",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=1500
            )
            
            result["analysis"] = response.choices[0].message.content
            result["success"] = True
            
        except Exception as e:
            result["error"] = str(e)
            result["success"] = False
        
        return result
    
    def search_documents(self, query, subject=None, limit=10):
        """RAG 智能检索"""
        try:
            results = rag_kb.search_documents(query, subject=subject, limit=limit)
            return results
        except Exception as e:
            return []
    
    def get_documents_by_category(self, category=None):
        """按分类获取文档"""
        try:
            if category and category != "全部":
                # 过滤特定分类
                all_docs = rag_kb.get_all_documents()
                return [doc for doc in all_docs if doc.get('subject') == category]
            else:
                return rag_kb.get_all_documents()
        except Exception as e:
            return []
