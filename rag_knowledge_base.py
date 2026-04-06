"""
RAG 知识库管理模块（JSON 格式存储）
支持多学科知识文档的上传、解析、向量化存储和语义检索
所有复杂数据以 JSON 格式存储在 MySQL 中
"""

import mysql.connector
import json
from rag_db_config import RAG_DB_CONFIG
from datetime import datetime
import os

class RAGKnowledgeBase:
    def __init__(self):
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """连接数据库"""
        try:
            self.conn = mysql.connector.connect(**RAG_DB_CONFIG)
            self.cursor = self.conn.cursor(dictionary=True)
            return True
        except Exception as e:
            print(f"❌ RAG 知识库连接失败：{str(e)}")
            return False
    
    def close(self):
        """关闭连接"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
    
    # ========== 知识文档相关操作 ==========
    
    def add_document(self, title, subject, file_path, file_type, content_text, 
                     knowledge_points=None, ai_summary=None, uploaded_by='teacher'):
        """
        添加知识文档到库中（JSON 格式存储）
        
        参数：
        - title: 文档标题
        - subject: 所属学科（语文、数学、英语等）
        - file_path: 文件存储路径
        - file_type: 文件类型（pdf/doc/ppt/txt）
        - content_text: 提取的文本内容
        - knowledge_points: 知识点列表（可以是列表或 JSON 字符串）
        - ai_summary: AI 生成的摘要
        - uploaded_by: 上传者
        """
        try:
            self.connect()
            
            # 构建完整的 JSON 数据结构
            document_data = {
                "metadata": {
                    "title": title,
                    "subject": subject,
                    "file_type": file_type,
                    "file_path": file_path,
                    "uploaded_by": uploaded_by,
                    "upload_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "version": "1.0"
                },
                "content": {
                    "raw_text": content_text[:50000] if content_text else "",  # 限制长度
                    "text_length": len(content_text) if content_text else 0,
                    "paragraphs": self._split_paragraphs(content_text) if content_text else []
                },
                "analysis": {
                    "knowledge_points": knowledge_points if isinstance(knowledge_points, list) else [],
                    "summary": ai_summary or "",
                    "difficulty_level": "中等",
                    "tags": []
                }
            }
            
            sql = """INSERT INTO knowledge_documents 
                    (title, subject, file_path, file_type, document_data, uploaded_by, upload_time)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)"""
            
            self.cursor.execute(sql, (
                title, subject, file_path, file_type,
                json.dumps(document_data, ensure_ascii=False),
                uploaded_by, datetime.now()
            ))
            self.conn.commit()
            doc_id = self.cursor.lastrowid
            
            # 如果有关键词，添加到关键词表
            if knowledge_points:
                self._add_knowledge_points(doc_id, knowledge_points)
            
            return doc_id
        except Exception as e:
            print(f"❌ 添加文档失败：{str(e)}")
            return None
        finally:
            self.close()
    
    def _add_knowledge_points(self, doc_id, knowledge_points_str):
        """添加知识点到关联表"""
        try:
            # 解析知识点（支持列表或字符串）
            if isinstance(knowledge_points_str, list):
                points = knowledge_points_str
            else:
                points = [p.strip() for p in str(knowledge_points_str).split(',') if p.strip()]
            
            for point in points:
                sql = """INSERT INTO knowledge_points (doc_id, point_name) 
                        VALUES (%s, %s)
                        ON DUPLICATE KEY UPDATE point_name = point_name"""
                self.cursor.execute(sql, (doc_id, point))
            
            self.conn.commit()
        except Exception as e:
            print(f"❌ 添加知识点失败：{str(e)}")
    
    def _split_paragraphs(self, text, max_length=500):
        """将文本分割为段落"""
        if not text:
            return []
        
        # 按换行符分割
        paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
        
        # 如果段落太长，进一步分割
        result = []
        for para in paragraphs:
            if len(para) <= max_length:
                result.append(para)
            else:
                # 按句子分割
                sentences = para.split('。')
                current = ""
                for sentence in sentences:
                    if len(current + sentence) <= max_length:
                        current += sentence + "。"
                    else:
                        if current:
                            result.append(current.strip())
                        current = sentence + "。"
                if current:
                    result.append(current.strip())
        
        return result[:100]  # 最多保留 100 个段落
    
    def get_documents_by_subject(self, subject, limit=50):
        """获取指定学科的所有文档（解析 JSON 数据）"""
        try:
            self.connect()
            sql = """SELECT * FROM knowledge_documents 
                    WHERE subject = %s 
                    ORDER BY upload_time DESC 
                    LIMIT %s"""
            self.cursor.execute(sql, (subject, limit))
            results = self.cursor.fetchall()
            
            # 解析 JSON 字段
            for record in results:
                if record.get('document_data'):
                    record['document_data'] = json.loads(record['document_data'])
                    # 兼容旧代码：提取常用字段
                    doc_data = record['document_data']
                    record['content_text'] = doc_data.get('content', {}).get('raw_text', '')
                    record['knowledge_points'] = doc_data.get('analysis', {}).get('knowledge_points', [])
                    record['ai_summary'] = doc_data.get('analysis', {}).get('summary', '')
            
            return results
        except Exception as e:
            print(f"❌ 获取学科文档失败：{str(e)}")
            return []
        finally:
            self.close()
    
    def get_all_documents(self, limit=100):
        """获取所有文档（按学科分类，解析 JSON 数据）"""
        try:
            self.connect()
            sql = """SELECT * FROM knowledge_documents 
                    ORDER BY subject, upload_time DESC 
                    LIMIT %s"""
            self.cursor.execute(sql, (limit,))
            results = self.cursor.fetchall()
            
            # 解析 JSON 字段
            for record in results:
                if record.get('document_data'):
                    record['document_data'] = json.loads(record['document_data'])
                    # 兼容旧代码
                    doc_data = record['document_data']
                    
                    # ✅ 兼容两种格式：
                    # 1. 旧格式：doc_data['content']['raw_text']（嵌套对象）
                    # 2. 新格式：doc_data['content']（直接文本字符串，如 CSV 导入）
                    content = doc_data.get('content', '')
                    if isinstance(content, dict):
                        # 旧格式：嵌套对象
                        record['content_text'] = content.get('raw_text', '')
                    else:
                        # 新格式：直接文本字符串
                        record['content_text'] = content
                    
                    record['knowledge_points'] = doc_data.get('analysis', {}).get('knowledge_points', [])
                    record['ai_summary'] = doc_data.get('analysis', {}).get('summary', '')
            
            return results
        except Exception as e:
            print(f"❌ 获取所有文档失败：{str(e)}")
            return []
        finally:
            self.close()
    
    def search_documents(self, keywords, subject=None, limit=10):
        """
        搜索知识文档（基于关键词匹配）
        
        参数：
        - keywords: 搜索关键词
        - subject: 限定学科（可选）
        - limit: 返回数量限制
        """
        try:
            self.connect()
            
            # 构建搜索条件（使用 JSON_EXTRACT 从 document_data 中搜索）
            if subject:
                sql = """SELECT id, title, subject, document_data,
                               MATCH(JSON_EXTRACT(document_data, '$.content.raw_text')) AGAINST (%s IN NATURAL LANGUAGE MODE) as relevance
                        FROM knowledge_documents
                        WHERE subject = %s
                          AND MATCH(JSON_EXTRACT(document_data, '$.content.raw_text')) AGAINST (%s IN NATURAL LANGUAGE MODE)
                        ORDER BY relevance DESC
                        LIMIT %s"""
                self.cursor.execute(sql, (keywords, subject, keywords, limit))
            else:
                sql = """SELECT id, title, subject, document_data,
                               MATCH(JSON_EXTRACT(document_data, '$.content.raw_text')) AGAINST (%s IN NATURAL LANGUAGE MODE) as relevance
                        FROM knowledge_documents
                        WHERE MATCH(JSON_EXTRACT(document_data, '$.content.raw_text')) AGAINST (%s IN NATURAL LANGUAGE MODE)
                        ORDER BY relevance DESC
                        LIMIT %s"""
                self.cursor.execute(sql, (keywords, keywords, limit))
            
            results = self.cursor.fetchall()
            
            # 解析 JSON 数据并计算相似度
            keyword_set = set(keywords.lower().split())
            for result in results:
                doc_data = result.get('document_data')
                if isinstance(doc_data, str):
                    doc_data = json.loads(doc_data)
                
                # 提取字段
                raw_text = doc_data.get('content', {}).get('raw_text', '')
                title = result.get('title', '')
                ai_summary = doc_data.get('analysis', {}).get('summary', '')
                knowledge_points = doc_data.get('analysis', {}).get('knowledge_points', [])
                
                # 添加兼容字段
                result['content_text'] = raw_text
                result['ai_summary'] = ai_summary
                result['knowledge_points'] = knowledge_points
                
                # Jaccard 相似度
                text = f"{title} {ai_summary} {','.join(knowledge_points)}"
                text_words = set(text.lower().split())
                common = len(keyword_set & text_words)
                total = len(keyword_set | text_words)
                result['similarity'] = common / total if total > 0 else 0
            
            # 按相似度排序
            results.sort(key=lambda x: x.get('relevance', 0), reverse=True)
            return results
            
        except mysql.connector.errors.ProgrammingError as e:
            # 全文索引不可用，回退到 LIKE 查询
            print(f"ℹ️ 使用简单匹配：{str(e)}")
            return self._simple_search(keywords, subject, limit)
        except Exception as e:
            print(f"❌ 搜索文档失败：{str(e)}")
            return []
        finally:
            self.close()
    
    def _simple_search(self, keywords, subject=None, limit=10):
        """简单的 LIKE 搜索（回退方案）"""
        try:
            keyword_list = [f"%{kw}%" for kw in keywords.split() if len(kw) > 1]
            
            conditions = []
            params = []
            for kw in keyword_list[:3]:  # 最多 3 个关键词
                conditions.append("(title LIKE %s OR JSON_EXTRACT(document_data, '$.content.raw_text') LIKE %s)")
                params.extend([kw, kw])
            
            where_sql = " AND ".join(conditions)
            
            if subject:
                sql = f"""SELECT id, title, subject, document_data, 0.5 as relevance
                         FROM knowledge_documents
                         WHERE subject = %s AND ({where_sql})
                         LIMIT %s"""
                params = [subject] + params + [limit]
            else:
                sql = f"""SELECT id, title, subject, document_data, 0.5 as relevance
                         FROM knowledge_documents
                         WHERE {where_sql}
                         LIMIT %s"""
                params = params + [limit]
            
            self.cursor.execute(sql, params)
            results = self.cursor.fetchall()
            
            # 解析 JSON 数据并提取所需字段
            for record in results:
                doc_data = record.get('document_data')
                if isinstance(doc_data, str):
                    doc_data = json.loads(doc_data)
                
                record['content_text'] = doc_data.get('content', {}).get('raw_text', '')
                record['ai_summary'] = doc_data.get('analysis', {}).get('summary', '')
                record['knowledge_points'] = doc_data.get('analysis', {}).get('knowledge_points', [])
            
            return results
            
        except Exception as e:
            print(f"❌ 简单搜索失败：{str(e)}")
            return []
    
    def get_document_by_id(self, doc_id):
        """根据 ID 获取文档详情（解析 JSON 数据）"""
        try:
            self.connect()
            sql = "SELECT * FROM knowledge_documents WHERE id = %s"
            self.cursor.execute(sql, (doc_id,))
            record = self.cursor.fetchone()
            
            # 解析 JSON 字段
            if record and record.get('document_data'):
                record['document_data'] = json.loads(record['document_data'])
                # 兼容旧代码
                doc_data = record['document_data']
                record['content_text'] = doc_data.get('content', {}).get('raw_text', '')
                record['knowledge_points'] = doc_data.get('analysis', {}).get('knowledge_points', [])
                record['ai_summary'] = doc_data.get('analysis', {}).get('summary', '')
            
            return record
        except Exception as e:
            print(f"❌ 获取文档详情失败：{str(e)}")
            return None
        finally:
            self.close()
    
    def update_document_usage(self, doc_id):
        """更新文档使用次数"""
        try:
            self.connect()
            sql = "UPDATE knowledge_documents SET usage_count = usage_count + 1 WHERE id = %s"
            self.cursor.execute(sql, (doc_id,))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"❌ 更新使用次数失败：{str(e)}")
            return False
        finally:
            self.close()
    
    def delete_document(self, doc_id):
        """删除文档"""
        try:
            self.connect()
            # 先删除关联的知识点
            sql = "DELETE FROM knowledge_points WHERE doc_id = %s"
            self.cursor.execute(sql, (doc_id,))
            
            # 删除文档
            sql = "DELETE FROM knowledge_documents WHERE id = %s"
            self.cursor.execute(sql, (doc_id,))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"❌ 删除文档失败：{str(e)}")
            return False
        finally:
            self.close()
    
    # ========== 知识点相关操作 ==========
    
    def get_knowledge_points_by_doc(self, doc_id):
        """获取文档的所有知识点"""
        try:
            self.connect()
            sql = "SELECT point_name FROM knowledge_points WHERE doc_id = %s"
            self.cursor.execute(sql, (doc_id,))
            return self.cursor.fetchall()
        except Exception as e:
            print(f"❌ 获取知识点失败：{str(e)}")
            return []
        finally:
            self.close()
    
    def search_by_knowledge_point(self, point_name, limit=20):
        """根据知识点搜索相关文档"""
        try:
            self.connect()
            sql = """SELECT kd.*, kp.point_name
                    FROM knowledge_documents kd
                    JOIN knowledge_points kp ON kd.id = kp.doc_id
                    WHERE kp.point_name LIKE %s
                    ORDER BY kd.upload_time DESC
                    LIMIT %s"""
            self.cursor.execute(sql, (f"%{point_name}%", limit))
            return self.cursor.fetchall()
        except Exception as e:
            print(f"❌ 按知识点搜索失败：{str(e)}")
            return []
        finally:
            self.close()
    
    # ========== 统计功能 ==========
    
    def get_statistics(self):
        """获取知识库统计信息"""
        try:
            self.connect()
            
            # 总文档数
            sql_total = "SELECT COUNT(*) as total_docs FROM knowledge_documents"
            self.cursor.execute(sql_total)
            total_docs = self.cursor.fetchone()['total_docs']
            
            # 各学科文档数
            sql_subject = """SELECT subject, COUNT(*) as count 
                            FROM knowledge_documents 
                            GROUP BY subject"""
            self.cursor.execute(sql_subject)
            subject_stats = self.cursor.fetchall()
            
            # 总知识点数
            sql_points = "SELECT COUNT(DISTINCT point_name) as total_points FROM knowledge_points"
            self.cursor.execute(sql_points)
            total_points = self.cursor.fetchone()['total_points']
            
            # 平均使用次数
            sql_usage = "SELECT AVG(usage_count) as avg_usage FROM knowledge_documents"
            self.cursor.execute(sql_usage)
            avg_usage = self.cursor.fetchone()['avg_usage'] or 0
            
            return {
                'total_documents': total_docs,
                'subject_distribution': subject_stats,
                'total_knowledge_points': total_points,
                'average_usage': round(avg_usage, 2)
            }
        except Exception as e:
            print(f"❌ 获取统计信息失败：{str(e)}")
            return {}
        finally:
            self.close()


# 创建全局 RAG 知识库实例
rag_kb = RAGKnowledgeBase()
