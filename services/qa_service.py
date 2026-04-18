"""
智能答疑服务模块
"""
import streamlit as st
from datetime import datetime
import time
import re
from openai import OpenAI
from data.qa_db_operations import qa_db
from data.rag_knowledge_base import rag_kb
from core.prompts import VoiceQAPrompts
from data.data_manager import LearningDataManager
from core.utils import clean_json_string, extract_urls


class QAService:
    """智能答疑业务逻辑服务"""
    
    def __init__(self):
        """初始化服务"""
        self.client = None
    
    def _get_client(self, api_key, base_url):
        """获取 OpenAI 客户端"""
        if not self.client:
            self.client = OpenAI(api_key=api_key, base_url=base_url)
        return self.client
    
    def handle_text_question(self, question, scenario, api_key, base_url):
        """处理文字提问（支持多轮对话）"""
        start_time = time.time()
        
        # 初始化消息列表
        if "messages" not in st.session_state:
            st.session_state.messages = []
        
        result = {
            "success": False,
            "answer": "",
            "source_info": "",
            "rag_docs_found": [],
            "tokens_used": None,
            "response_time_ms": 0,
            "error": None
        }
        
        try:
            client = self._get_client(api_key, base_url)
            
            # 1. 查询 QA 数据库（历史问答）- 仅在第一轮或无上下文时使用
            if len(st.session_state.messages) == 0:
                similar_qa = qa_db.search_similar_questions(question, limit=2)
                
                if similar_qa and len(similar_qa) > 0:
                    best_match = similar_qa[0]
                    similarity_score = best_match.get('similarity', 0)
                    
                    # 高相似度直接返回
                    if similarity_score > 0.8:
                        result["answer"] = best_match.get('ai_response', '')
                        result["source_info"] = "💾 来源：历史问答记录"
                        result["success"] = True
                        result["response_time_ms"] = int((time.time() - start_time) * 1000)
                        
                        # 保存记录
                        self._save_qa_record(question, result["answer"], scenario, 
                                           result["tokens_used"], result["response_time_ms"])
                        
                        # 添加到消息历史
                        st.session_state.messages.append({"role": "user", "content": question})
                        st.session_state.messages.append({"role": "assistant", "content": result["answer"]})
                        
                        return result
            
            # 2. RAG 知识库检索
            rag_context = ""
            rag_docs_found = []
            
            try:
                rag_results = rag_kb.search_documents(question, limit=2)
                
                if rag_results:
                    rag_context = "\n\n=== 知识库参考资料 ===\n\n"
                    for i, doc in enumerate(rag_results, 1):
                        title = doc.get('title', '未知文档')
                        subject = doc.get('subject', '未知学科')
                        content = doc.get('content_text', '')[:1000]
                        rag_docs_found.append({"title": title, "subject": subject})
                        
                        rag_context += f"📚 参考资料 {i}:《{title}》({subject})\n"
                        rag_context += f"{content}\n\n"
                        
                        # 更新使用次数
                        rag_kb.update_document_usage(doc['id'])
                    
                    rag_context += "=== 参考资料结束 ===\n\n"
            except Exception as e:
                pass  # RAG 检索失败，静默处理
            
            # 3. 构建多轮对话消息
            # 添加用户新问题到历史
            st.session_state.messages.append({"role": "user", "content": question})
            
            # 如果有 RAG 上下文，在系统消息中加入
            system_content = "你是一位专业的教育 AI 助手。请根据对话历史和参考资料回答问题。"
            if rag_context:
                system_content += f"\n\n{rag_context}"
            
            # 构建完整的消息列表（包含系统消息 + 历史对话）
            messages_with_history = [
                {"role": "system", "content": system_content}
            ] + st.session_state.messages
            
            # 限制历史长度，避免超出 token 限制（保留最近 10 轮对话）
            max_history_messages = 20  # 10 轮对话 = 20 条消息
            if len(messages_with_history) > max_history_messages + 1:  # +1 为 system 消息
                messages_with_history = [messages_with_history[0]] + messages_with_history[-max_history_messages:]
            
            # 4. 调用 AI
            response = client.chat.completions.create(
                model="moonshot-v1-8k",
                messages=messages_with_history,
                temperature=0.7,
                max_tokens=1500,
                top_p=0.9
            )
            
            end_time = time.time()
            result["response_time_ms"] = int((end_time - start_time) * 1000)
            result["tokens_used"] = response.usage.total_tokens if hasattr(response, 'usage') else None
            result["answer"] = response.choices[0].message.content
            result["rag_docs_found"] = rag_docs_found
            
            if rag_context:
                result["source_info"] = f"📚 参考了 {len(rag_docs_found)} 篇教学资料"
            else:
                result["source_info"] = "🤖 来源：Kimi AI"
            
            result["success"] = True
            
            # 5. 保存 AI 回复到消息历史
            st.session_state.messages.append({"role": "assistant", "content": result["answer"]})
            
            # 6. 保存记录到数据库
            self._save_qa_record(question, result["answer"], scenario, 
                               result["tokens_used"], result["response_time_ms"])
            
        except Exception as e:
            result["error"] = str(e)
            result["success"] = False
            # 如果失败，移除刚才添加的用户消息
            if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
                st.session_state.messages.pop()
        
        return result
    
    def handle_voice_question(self, transcribed_text, api_key, base_url, rag_context=None):
        """处理语音提问"""
        # 初始化消息列表
        if "messages" not in st.session_state:
            st.session_state.messages = []
        
        result = {
            "success": False,
            "answer": "",
            "error": None
        }
        
        try:
            client = self._get_client(api_key, base_url)
            
            # 添加用户消息到历史
            st.session_state.messages.append({"role": "user", "content": transcribed_text})
            
            # 构建系统消息
            system_content = "你是一位专业的教育 AI 助手，擅长回答学生的各种问题。"
            if rag_context:
                system_content += f"\n\n{rag_context}"
            
            # 构建完整的消息列表（包含系统消息 + 历史对话）
            messages_with_history = [
                {"role": "system", "content": system_content}
            ] + st.session_state.messages
            
            # 限制历史长度
            max_history_messages = 20
            if len(messages_with_history) > max_history_messages + 1:
                messages_with_history = [messages_with_history[0]] + messages_with_history[-max_history_messages:]
            
            response = client.chat.completions.create(
                model="moonshot-v1-8k",
                messages=messages_with_history,
                temperature=0.7,
                max_tokens=1500
            )
            
            result["answer"] = response.choices[0].message.content
            result["success"] = True
            
            # 保存 AI 回复到消息历史
            st.session_state.messages.append({"role": "assistant", "content": result["answer"]})
            
        except Exception as e:
            result["error"] = str(e)
            result["success"] = False
            # 如果失败，移除刚才添加的用户消息
            if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
                st.session_state.messages.pop()
        
        return result
    
    def manage_chat_history(self, action, **kwargs):
        """管理聊天记录"""
        result = {"success": False, "data": None, "error": None}
        
        try:
            if action == "search":
                # 搜索聊天记录
                keyword = kwargs.get("keyword", "")
                messages = st.session_state.get("messages", [])
                filtered = [msg for msg in messages if keyword.lower() in msg.get("content", "").lower()]
                result["data"] = filtered
                result["success"] = True
                
            elif action == "export":
                # 导出聊天记录
                format_type = kwargs.get("format", "txt")
                messages = st.session_state.get("messages", [])
                
                if format_type == "json":
                    import json
                    result["data"] = json.dumps(messages, ensure_ascii=False, indent=2)
                else:
                    text_lines = []
                    for msg in messages:
                        role = "用户" if msg["role"] == "user" else "AI"
                        text_lines.append(f"[{role}] {msg['content']}\n")
                    result["data"] = "\n".join(text_lines)
                
                result["success"] = True
                
            elif action == "clear":
                # 清空聊天记录
                st.session_state.messages = []
                result["success"] = True
                
        except Exception as e:
            result["error"] = str(e)
            result["success"] = False
        
        return result
    
    def _save_qa_record(self, question, answer, scenario, tokens_used, response_time_ms):
        """保存问答记录到数据库"""
        try:
            user_id = 1
            qa_db.add_qa_record(
                user_id=user_id,
                question_text=question,
                scenario=scenario,
                ai_response=answer,
                model_used='moonshot-v1-8k',
                tokens_used=tokens_used,
                response_time_ms=response_time_ms
            )
        except Exception:
            pass  # 静默失败，不影响主流程
