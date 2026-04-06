"""
AI 答疑专用数据库操作模块（JSON 格式存储）
提供问答记录的 CRUD 操作，所有复杂数据以 JSON 格式存储
"""

import mysql.connector
import json
import time
from qa_db_config import QA_DB_CONFIG
from datetime import datetime

class QADatabase:
    def __init__(self):
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """连接数据库"""
        try:
            self.conn = mysql.connector.connect(**QA_DB_CONFIG)
            self.cursor = self.conn.cursor(dictionary=True)
            return True
        except Exception as e:
            print(f"❌ 答答疑数据库连接失败：{str(e)}")
            return False
    
    def close(self):
        """关闭连接"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
    
    # ========== 用户相关操作 ==========
    def add_user(self, username, email, role='student'):
        """添加用户（同步到答疑数据库）"""
        try:
            self.connect()
            sql = "INSERT INTO users (username, email, role) VALUES (%s, %s, %s)"
            self.cursor.execute(sql, (username, email, role))
            self.conn.commit()
            return self.cursor.lastrowid
        except mysql.connector.errors.IntegrityError:
            # 用户已存在，获取用户信息
            return self.get_user_by_username(username)['id']
        except Exception as e:
            print(f"❌ 添加用户失败：{str(e)}")
            return None
        finally:
            self.close()
    
    def get_user_by_username(self, username):
        """根据用户名获取用户"""
        try:
            self.connect()
            sql = "SELECT * FROM users WHERE username = %s"
            self.cursor.execute(sql, (username,))
            return self.cursor.fetchone()
        except Exception as e:
            print(f"❌ 获取用户失败：{str(e)}")
            return None
        finally:
            self.close()
    
    # ========== 问答记录相关操作（JSON 格式） ==========
    def add_qa_record(self, user_id, question_text, scenario, ai_response,
                      model_used='moonshot-v1-8k', tokens_used=None, response_time_ms=None):
        """添加问答记录（JSON 格式存储）"""
        try:
            self.connect()
            
            # 构建 JSON 数据
            question_data = {
                "text": question_text,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "scenario": scenario,
                "metadata": {
                    "source": "web",
                    "version": "1.0"
                }
            }
            
            ai_response_data = {
                "response": ai_response,
                "model": model_used,
                "tokens_used": tokens_used,
                "response_time_ms": response_time_ms,
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            sql = """INSERT INTO qa_records 
                    (user_id, question_data, scenario, ai_response_data, model_used, tokens_used, response_time_ms) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s)"""
            self.cursor.execute(sql, (
                user_id,
                json.dumps(question_data, ensure_ascii=False),
                scenario,
                json.dumps(ai_response_data, ensure_ascii=False),
                model_used,
                tokens_used,
                response_time_ms
            ))
            self.conn.commit()
            record_id = self.cursor.lastrowid
            return record_id
        except Exception as e:
            print(f"❌ 添加问答记录失败：{str(e)}")
            return None
        finally:
            self.close()
    
    def get_qa_records_by_user(self, user_id, limit=100, scenario=None):
        """获取用户的问答记录（解析 JSON 数据）"""
        try:
            self.connect()
            if scenario:
                sql = """SELECT * FROM qa_records 
                        WHERE user_id = %s AND scenario = %s 
                        ORDER BY created_at DESC LIMIT %s"""
                self.cursor.execute(sql, (user_id, scenario, limit))
            else:
                sql = """SELECT * FROM qa_records 
                        WHERE user_id = %s 
                        ORDER BY created_at DESC LIMIT %s"""
                self.cursor.execute(sql, (user_id, limit))
            
            results = self.cursor.fetchall()
            
            # 解析 JSON 字段
            for record in results:
                if record.get('question_data'):
                    record['question_data'] = json.loads(record['question_data'])
                    # 兼容旧代码：提取 text 字段
                    record['question_text'] = record['question_data'].get('text', '')
                
                if record.get('ai_response_data'):
                    record['ai_response_data'] = json.loads(record['ai_response_data'])
                    # 兼容旧代码：提取 response 字段
                    record['ai_response'] = record['ai_response_data'].get('response', '')
            
            return results
        except Exception as e:
            print(f"❌ 获取问答记录失败：{str(e)}")
            return []
        finally:
            self.close()
    
    def get_qa_record_by_id(self, record_id):
        """根据 ID 获取问答记录"""
        try:
            self.connect()
            sql = "SELECT * FROM qa_records WHERE id = %s"
            self.cursor.execute(sql, (record_id,))
            return self.cursor.fetchone()
        except Exception as e:
            print(f"❌ 获取问答记录失败：{str(e)}")
            return None
        finally:
            self.close()
    
    def search_similar_questions(self, question_text, limit=5):
        """搜索相似问题（基于关键词匹配）"""
        try:
            self.connect()
            # 使用全文索引或 LIKE 进行模糊匹配
            # 提取问题中的关键词
            keywords = question_text.split()
            
            # 构建搜索条件
            search_conditions = []
            params = []
            for keyword in keywords[:3]:  # 取前 3 个关键词
                if len(keyword) > 1:  # 忽略单字词
                    search_conditions.append("question_text LIKE %s OR ai_response LIKE %s")
                    params.extend([f"%{keyword}%", f"%{keyword}%"])
            
            if not search_conditions:
                # 如果没有有效关键词，直接返回空
                return []
            
            search_sql = " OR ".join(search_conditions)
            sql = f"""SELECT id, question_text, scenario, ai_response, model_used, created_at,
                            MATCH(question_text, ai_response) AGAINST (%s IN NATURAL LANGUAGE MODE) as similarity
                     FROM qa_records
                     WHERE {search_sql}
                     ORDER BY similarity DESC, created_at DESC
                     LIMIT %s"""
            
            # 如果数据库不支持全文索引，使用简单的 LIKE 查询
            try:
                params_for_like = [f"%{kw}%" for kw in keywords[:3] if len(kw) > 1]
                like_conditions = []
                for _ in range(len(params_for_like)):
                    like_conditions.append("question_text LIKE %s OR ai_response LIKE %s")
                
                like_sql = " OR ".join(like_conditions)
                sql = f"""SELECT id, question_text, scenario, ai_response, model_used, created_at,
                                0.5 as similarity
                         FROM qa_records
                         WHERE {like_sql}
                         ORDER BY created_at DESC
                         LIMIT %s"""
                
                all_params = params_for_like * 2 + [limit]
                self.cursor.execute(sql, all_params)
                results = self.cursor.fetchall()
                
                # 计算简单的相似度（基于共同词数）
                question_words = set(w.lower() for w in question_text.split() if len(w) > 1)
                for result in results:
                    answer_words = set(w.lower() for w in (result['question_text'] + ' ' + result['ai_response']).split() if len(w) > 1)
                    common_words = len(question_words & answer_words)
                    total_words = len(question_words | answer_words)
                    result['similarity'] = common_words / total_words if total_words > 0 else 0
                
                # 按相似度排序
                results.sort(key=lambda x: x['similarity'], reverse=True)
                return results[:limit]
                
            except Exception as fulltext_error:
                # 全文索引失败，回退到简单匹配
                print(f"ℹ️ 使用简单匹配：{str(fulltext_error)}")
                return []
                
        except Exception as e:
            print(f"❌ 搜索相似问题失败：{str(e)}")
            return []
        finally:
            self.close()
    
    def update_feedback(self, record_id, rating, comment=None):
        """更新反馈"""
        try:
            self.connect()
            sql = "UPDATE qa_records SET feedback_rating = %s, feedback_comment = %s WHERE id = %s"
            self.cursor.execute(sql, (rating, comment, record_id))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"❌ 更新反馈失败：{str(e)}")
            return False
        finally:
            self.close()
    
    # ========== 会话相关操作 ==========
    def create_session(self, user_id, session_title=None, scenario=None):
        """创建新会话"""
        try:
            self.connect()
            sql = "INSERT INTO sessions (user_id, session_title, scenario) VALUES (%s, %s, %s)"
            self.cursor.execute(sql, (user_id, session_title, scenario))
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            print(f"❌ 创建会话失败：{str(e)}")
            return None
        finally:
            self.close()
    
    def add_message_to_session(self, session_id, qa_record_id, message_order):
        """添加消息到会话"""
        try:
            self.connect()
            sql = "INSERT INTO session_messages (session_id, qa_record_id, message_order) VALUES (%s, %s, %s)"
            self.cursor.execute(sql, (session_id, qa_record_id, message_order))
            
            # 更新会话的消息数和最后活动时间
            sql = """UPDATE sessions 
                    SET message_count = message_count + 1, 
                        last_activity = CURRENT_TIMESTAMP 
                    WHERE id = %s"""
            self.cursor.execute(sql, (session_id,))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"❌ 添加消息到会话失败：{str(e)}")
            return False
        finally:
            self.close()
    
    def get_session_messages(self, session_id):
        """获取会话的所有消息"""
        try:
            self.connect()
            sql = """SELECT qr.* FROM qa_records qr
                    JOIN session_messages sm ON qr.id = sm.qa_record_id
                    WHERE sm.session_id = %s
                    ORDER BY sm.message_order ASC"""
            self.cursor.execute(sql, (session_id,))
            return self.cursor.fetchall()
        except Exception as e:
            print(f"❌ 获取会话消息失败：{str(e)}")
            return []
        finally:
            self.close()
    
    def get_user_sessions(self, user_id, limit=50):
        """获取用户的会话列表"""
        try:
            self.connect()
            sql = """SELECT * FROM sessions 
                    WHERE user_id = %s 
                    ORDER BY last_activity DESC LIMIT %s"""
            self.cursor.execute(sql, (user_id, limit))
            return self.cursor.fetchall()
        except Exception as e:
            print(f"❌ 获取会话列表失败：{str(e)}")
            return []
        finally:
            self.close()
    
    # ========== 统计相关操作 ==========
    def update_user_statistics(self, user_id):
        """更新用户统计信息"""
        try:
            self.connect()
            
            # 计算统计数据
            stats_sql = """
                SELECT 
                    COUNT(*) as total_questions,
                    AVG(response_time_ms) as avg_response_time,
                    MAX(created_at) as last_question_time
                FROM qa_records
                WHERE user_id = %s
            """
            self.cursor.execute(stats_sql, (user_id,))
            stats = self.cursor.fetchone()
            
            # 获取最常用的场景
            scenario_sql = """
                SELECT scenario, COUNT(*) as cnt
                FROM qa_records
                WHERE user_id = %s
                GROUP BY scenario
                ORDER BY cnt DESC
                LIMIT 1
            """
            self.cursor.execute(scenario_sql, (user_id,))
            scenario_result = self.cursor.fetchone()
            most_used_scenario = scenario_result['scenario'] if scenario_result else None
            
            # 获取会话数
            session_sql = "SELECT COUNT(*) as total_sessions FROM sessions WHERE user_id = %s"
            self.cursor.execute(session_sql, (user_id,))
            session_result = self.cursor.fetchone()
            total_sessions = session_result['total_sessions']
            
            # 插入或更新统计
            upsert_sql = """
                INSERT INTO user_statistics 
                (user_id, total_questions, total_sessions, avg_response_time_ms, 
                 most_used_scenario, last_question_time)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                total_questions = VALUES(total_questions),
                total_sessions = VALUES(total_sessions),
                avg_response_time_ms = VALUES(avg_response_time_ms),
                most_used_scenario = VALUES(most_used_scenario),
                last_question_time = VALUES(last_question_time)
            """
            self.cursor.execute(upsert_sql, (
                user_id,
                stats['total_questions'],
                total_sessions,
                int(stats['avg_response_time']) if stats['avg_response_time'] else None,
                most_used_scenario,
                stats['last_question_time']
            ))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"❌ 更新统计信息失败：{str(e)}")
            return False
        finally:
            self.close()
    
    def get_user_statistics(self, user_id):
        """获取用户统计信息"""
        try:
            self.connect()
            sql = "SELECT * FROM user_statistics WHERE user_id = %s"
            self.cursor.execute(sql, (user_id,))
            return self.cursor.fetchone()
        except Exception as e:
            print(f"❌ 获取统计信息失败：{str(e)}")
            return None
        finally:
            self.close()

# 创建全局答疑数据库实例
qa_db = QADatabase()
