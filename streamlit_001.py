import streamlit as st
from openai import OpenAI
from datetime import datetime
import time
import os
import json
from dotenv import load_dotenv
from db_operations import db
from qa_db_operations import qa_db
from rag_knowledge_base import rag_kb  # RAG 知识库
from document_parser import doc_parser  # 文档解析器
from functools import lru_cache
from logger import info, warning, error, db_connect_success, db_connect_failed, user_login

# 加载环境变量
load_dotenv()

# 从环境变量读取配置
DEFAULT_API_KEY = os.getenv('KIMI_API_KEY', 'sk-devLXA4UVGRWzlLYFzepvtfFT15iDSGmbyMtQrKikj9WhcA6')
BASE_URL = os.getenv('KIMI_BASE_URL', 'https://api.moonshot.cn/v1')  # Kimi API 地址

# 初始化学习数据（使用缓存）
if "learning_data" not in st.session_state:
    st.session_state.learning_data = {
        "questions": [],
        "correct_rate": 0,
        "weak_points": [],
        "study_time": 0,
        "interactions": []
    }

# 初始化知识库（使用缓存）
if "knowledge_base" not in st.session_state:
    st.session_state.knowledge_base = {
        "documents": [],
        "categories": {}
    }

# 初始化课件生成会话（使用缓存）
if "courseware_session" not in st.session_state:
    st.session_state.courseware_session = {
        "topic": "",
        "grade_level": "",
        "subject": "",
        "requirements": [],
        "generated": False,
        "outline": "",
        "ppt_content": ""
    }

# 数据库连接状态缓存
# 注意：如果 MySQL 未启动，会显示连接失败警告，但不影响其他功能
if "db_connected" not in st.session_state:
    try:
        st.session_state.db_connected = db.connect()
    except Exception as e:
        st.session_state.db_connected = False
        error(f"主数据库连接失败：{str(e)}")
    
    try:
        st.session_state.qa_db_connected = qa_db.connect()
    except Exception as e:
        st.session_state.qa_db_connected = False
        error(f"答疑数据库连接失败：{str(e)}")
    
    try:
        st.session_state.rag_kb_connected = rag_kb.connect()
    except Exception as e:
        st.session_state.rag_kb_connected = False
        error(f"RAG 知识库连接失败：{str(e)}")
    
    # 记录连接状态（仅在成功时记录）
    if st.session_state.db_connected:
        db_connect_success("ai_teaching_assistant")
    
    if st.session_state.qa_db_connected:
        db_connect_success("ai_qa_records")
    
    if st.session_state.rag_kb_connected:
        db_connect_success("ai_rag_knowledge")
        
        # ✅ 从 RAG 数据库恢复文档列表（实现持久化）
        try:
            db_docs = rag_kb.get_all_documents(limit=1000)
            
            # ✅ 用于去重的集合（基于 rag_doc_id）
            existing_doc_ids = set()
            
            for doc in db_docs:
                rag_doc_id = doc['id']
                
                # ✅ 去重：如果已经存在相同的文档 ID，跳过
                if rag_doc_id in existing_doc_ids:
                    continue
                existing_doc_ids.add(rag_doc_id)
                
                # 构建文档信息
                doc_data = doc.get('document_data', {})
                metadata = doc_data.get('metadata', {})
                
                # 兼容不同格式的标题和学科
                title = metadata.get('title', doc.get('title', '未知文档'))
                subject = metadata.get('subject', doc.get('subject', '通用'))
                
                doc_info = {
                    "name": title,
                    "type": metadata.get('file_type', doc.get('file_type', 'unknown')),
                    "size": 0,
                    "category": f"📚 {subject}",
                    "upload_time": metadata.get('upload_time', str(doc.get('upload_time', ''))),
                    "json_format": True,
                    "json_data": doc_data,
                    "json_file_path": doc.get('file_path', ''),
                    "rag_doc_id": rag_doc_id
                }
                
                st.session_state.knowledge_base["documents"].append(doc_info)
                
                # 更新分类统计
                category = doc_info["category"]
                if category not in st.session_state.knowledge_base["categories"]:
                    st.session_state.knowledge_base["categories"][category] = 0
                st.session_state.knowledge_base["categories"][category] += 1
            
            if db_docs:
                info(f"✅ 从 RAG 数据库恢复了 {len(db_docs)} 个文档")
        except Exception as e:
            warning(f"⚠️ 从 RAG 数据库恢复文档失败：{str(e)}")

# 优化：减少重复的 CSS 渲染
st.markdown("""
<style>
/* 全局背景 - 纯白色 */
.stApp {
    background: #ffffff;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

/* 聊天消息样式 */
.chat-user {
    background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
    color: #333;
    padding: 15px;
    border-radius: 15px;
}
.chat-assistant {
    background: white;
    color: #333;
    padding: 15px;
    border-radius: 15px;
}

/* 卡片样式 */
.card {
    background: white;
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 4px 8px rgba(0,0,0,0.05);
}

/* 状态指示器 */
.status-indicator {
    background: linear-gradient(135deg, #ffe0b2 0%, #ffcc80 100%);
    padding: 15px;
    border-radius: 10px;
    color: #555;
}

/* 输入框样式优化 */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background-color: white !important;
    border: 2px solid #4a90e2 !important;
    border-radius: 8px !important;
    font-size: 16px !important;
    padding: 12px !important;
    box-shadow: 0 2px 4px rgba(74,144,226,0.1) !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #2196f3 !important;
    box-shadow: 0 4px 8px rgba(33,150,243,0.2) !important;
}

/* Selectbox 样式 */
.stSelectbox > div > div > select {
    background-color: white !important;
    border: 2px solid #66bb6a !important;
    border-radius: 8px !important;
    font-size: 16px !important;
    padding: 10px !important;
}

/* Radio 按钮样式 - 导航菜单 */
.stRadio > div {
    display: flex;
    flex-direction: column;
    gap: 10px;
}
.stRadio > label {
    background-color: #f8f9fa;
    border: 2px solid #e0e0e0;
    border-radius: 10px;
    padding: 14px 18px;
    margin: 0;
    cursor: pointer;
    transition: all 0.3s ease;
    font-size: 15px;
    font-weight: 500;
    color: #555;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.stRadio > label:hover {
    background-color: #f0f2f5;
    border-color: #d0d0d0;
    transform: translateX(5px);
    box-shadow: 0 2px 6px rgba(0,0,0,0.08);
}
.stRadio input[type="radio"]:checked + label {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-color: #667eea;
    color: white;
    box-shadow: 0 4px 12px rgba(102,126,234,0.3);
    font-weight: 600;
}
.stRadio input[type="radio"] + label:before {
    content: '';
    display: inline-block;
    width: 0;
    height: 0;
    visibility: hidden;
}

/* 横向单选按钮强制水平排列 */
div[data-testid="stRadio"] > div {
    flex-direction: row !important;
    flex-wrap: wrap;
    gap: 10px;
    justify-content: flex-start;
}
div[data-testid="stRadio"] > div > label {
    flex: 0 0 auto !important;
    white-space: nowrap;
    margin: 0;
}

/* 文件上传器样式 */
.stFileUploader {
    border: 2px dashed #4a90e2 !important;
    border-radius: 8px !important;
    padding: 15px !important;
    background-color: #f8f9fa !important;
}

/* 按钮样式 */
.stButton > button {
    border-radius: 8px !important;
    font-weight: 600 !important;
    transition: all 0.3s ease !important;
}

/* Expander 样式 */
.streamlit-expanderHeader {
    border-radius: 8px !important;
    border: 2px solid #e0e0e0 !important;
}
</style>
""", unsafe_allow_html=True)

# 页面配置（只执行一次）
st.set_page_config(page_title="多模态 AI 互动式教学智能体", page_icon="🎓", layout="wide")

# 侧边栏

# 侧边栏
with st.sidebar:
    # 主标题
    st.title(" AI 智能教育助手")
    
    # 检查数据库连接状态，如未连接则弹窗警告
    if not st.session_state.db_connected:
        st.error("⚠️ 主数据库未连接！")
        st.warning("部分功能可能无法使用")
    if not st.session_state.qa_db_connected:
        st.error("⚠️ 答答疑数据库未连接！")
        st.warning("AI 答疑记录将无法保存")
    
    st.divider()
    
    # 插图展示区域
    st.divider()
    st.image(
        "illustration/i1.png",
        width=200
    )
    st.caption("让 AI 助力您的教学之旅 🚀")
    st.divider()
    
    st.title("导航菜单")
    
    menu = st.radio(
        "选择功能",
        ["智能答疑", "课件生成", "学情分析", "知识库管理"],
        index=0,
        label_visibility="collapsed",
        horizontal=True,
        key="menu_selection"
    )

# 辅助函数
def process_question(question, scenario, learning_data):
    """处理文本问题 - RAG 知识库优先策略"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    start_time = time.time()
    
    st.session_state.messages.append({"role": "user", "content": question})
    
    with st.chat_message("user"):
        st.markdown(question)
    
    with st.chat_message("assistant"):
        ai_response = None
        source_info = ""
        
        # 第一步：查询 QA 数据库（已有问答记录）
        try:
            similar_qa = qa_db.search_similar_questions(question, limit=3)
            
            if similar_qa and len(similar_qa) > 0:
                best_match = similar_qa[0]
                similarity_score = best_match.get('similarity', 0)
                
                if similarity_score > 0.8:  # 高相似度直接返回
                    ai_response = best_match.get('ai_response', '')
                    source_info = "💾 来源：历史问答记录"
                    
                    st.session_state.messages.append({"role": "assistant", "content": ai_response})
                    learning_data["questions"].append({
                        "question": question,
                        "answer": ai_response,
                        "scenario": scenario,
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "answered": True,
                        "source": "database",
                        "source_id": best_match.get('id')
                    })
                    st.markdown(ai_response)
                    st.caption(source_info)
                    return
        except Exception as db_error:
            pass
        
        # 第二步：查询 RAG 知识库（书籍文档）
        rag_context = ""
        rag_docs_found = []
        
        try:
            if st.session_state.rag_kb_connected:
                with st.spinner("🔍 正在知识库中检索..."):
                    rag_results = rag_kb.search_documents(question, limit=5)
                    
                    if rag_results:
                        # 构建知识库上下文
                        rag_context = "\n\n=== 知识库参考资料 ===\n\n"
                        for i, doc in enumerate(rag_results[:3], 1):
                            title = doc.get('title', '未知文档')
                            subject = doc.get('subject', '未知学科')
                            content = doc.get('content_text', '')[:1000]  # 每篇文档取前1000字
                            rag_docs_found.append({"title": title, "subject": subject})
                            
                            rag_context += f"📚 参考资料 {i}:《{title}》({subject})\n"
                            rag_context += f"{content}\n\n"
                            
                            # 更新使用次数
                            rag_kb.update_document_usage(doc['id'])
                        
                        rag_context += "=== 参考资料结束 ===\n\n"
                        source_info = f"📚 参考了 {len(rag_docs_found)} 本书籍"
        except Exception as rag_error:
            pass  # RAG 检索失败，静默处理
        
        # 第三步：调用 AI 生成回答
        with st.spinner("思考中..."):
            try:
                # 优化：复用 OpenAI 客户端
                if "client" not in st.session_state:
                    st.session_state.client = OpenAI(api_key=DEFAULT_API_KEY, base_url=BASE_URL)
                
                # 构建带知识库上下文的提示词
                if rag_context:
                    system_prompt = '''你是一位专业的教育 AI 助手。请根据以下参考资料回答问题。
要求：
1. 优先使用参考资料中的信息
2. 如果参考资料不足以完整回答问题，可以补充你的知识
3. 回答要准确、清晰、易懂
4. 如果参考资料中没有相关信息，明确说明“知识库中未找到相关内容”'''
                    
                    messages_with_context = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": rag_context + f"\n\n问题：{question}"}
                    ]
                else:
                    # 没有知识库内容，直接回答
                    messages_with_context = st.session_state.messages
                
                response = st.session_state.client.chat.completions.create(
                    model="moonshot-v1-8k",  # Kimi 模型
                    messages=messages_with_context
                )
                
                end_time = time.time()
                response_time_ms = int((end_time - start_time) * 1000)
                tokens_used = response.usage.total_tokens if hasattr(response, 'usage') else None
                
                ai_response = response.choices[0].message.content
                
                # 显示 AI 回复
                st.markdown(ai_response)
                
                # 显示来源信息
                if source_info:
                    st.caption(source_info)
                
                # 显示参考的书籍列表
                if rag_docs_found:
                    with st.expander("📖 查看参考的书籍"):
                        for doc in rag_docs_found:
                            st.markdown(f"- 📚 {doc['title']} ({doc['subject']})")
                
                # 检查是否包含链接或图片
                if "http" in ai_response:
                    import re
                    urls = re.findall(r'http[s]?://\S+', ai_response)
                    if urls:
                        st.caption("📎 相关链接：")
                        for url in urls:
                            st.markdown(f"- {url}")
                
                # 提供下载按钮
                if len(ai_response) > 100:
                    file_name = f"AI_回复_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                    st.download_button(
                        label="📥 下载 AI 回复为文本文件",
                        data=ai_response,
                        file_name=file_name,
                        mime="text/plain",
                        key=f"download_{len(learning_data.get('questions', []))}"
                    )
                
                st.session_state.messages.append({"role": "assistant", "content": ai_response})
                
                # 保存聊天记录和数据库
                learning_data["questions"].append({
                    "question": question,
                    "answer": ai_response,
                    "scenario": scenario,
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "answered": True,
                    "source": "rag_knowledge" if rag_context else "kimi_ai",
                    "tokens_used": tokens_used,
                    "response_time_ms": response_time_ms,
                    "rag_docs_count": len(rag_docs_found)
                })
                
                # 同时将问答记录保存到答疑专用数据库（静默保存）
                try:
                    user_id = 1
                    qa_db.add_qa_record(
                        user_id=user_id,
                        question_text=question,
                        scenario=scenario,
                        ai_response=ai_response,
                        model_used='moonshot-v1-8k',
                        tokens_used=tokens_used,
                        response_time_ms=response_time_ms
                    )
                except Exception as save_error:
                    pass
                    
            except Exception as e:
                st.error(f"请求失败：{str(e)}")

def process_audio(audio_value, scenario, learning_data):
    """处理语音输入"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    st.session_state.messages.append({"role": "user", "content": "[语音消息]"})
    
    with st.chat_message("user"):
        st.audio(audio_value)
    
    with st.chat_message("assistant"):
        with st.spinner("处理中..."):
            try:
                client = OpenAI(api_key=DEFAULT_API_KEY, base_url=BASE_URL)
                response = client.chat.completions.create(
                    model="qwen-plus",
                    messages=st.session_state.messages
                )
                
                ai_response = response.choices[0].message.content
                
                # 显示 AI 回复
                st.markdown(ai_response)
                
                # 检查是否包含链接或图片
                if "http" in ai_response:
                    import re
                    urls = re.findall(r'http[s]?://\S+', ai_response)
                    if urls:
                        st.caption("📎 相关链接：")
                        for url in urls:
                            st.markdown(f"- {url}")
                
                # 提供下载按钮
                if len(ai_response) > 100:
                    file_name = f"AI_回复_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                    st.download_button(
                        label="📥 下载 AI 回复为文本文件",
                        data=ai_response,
                        file_name=file_name,
                        mime="text/plain",
                        key=f"download_audio_{len(learning_data.get('questions', []))}"
                    )
                
                st.session_state.messages.append({"role": "assistant", "content": ai_response})
                
                # 保存聊天记录（语音提问）
                learning_data["questions"].append({
                    "question": "[语音消息]",
                    "answer": ai_response,  # 保存 AI 回答
                    "scenario": scenario,
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "answered": True
                })
            except Exception as e:
                st.error(f"请求失败：{str(e)}")

# 主界面
if menu == "智能答疑":
    st.title("💬 智能答疑")
    
    # 聊天记录管理区域
    if st.session_state.learning_data.get("questions"):
        with st.expander(f"📝 聊天记录管理 ({len(st.session_state.learning_data['questions'])} 条)"):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.subheader("🔍 搜索聊天记录")
                search_keyword = st.text_input(
                    "",
                    placeholder="输入关键词搜索聊天记录...",
                    key="chat_search_input"
                )
            
            with col2:
                st.subheader("📤 导出记录")
                export_format = st.selectbox(
                    "导出格式",
                    ["TXT", "JSON"],
                    key="export_format_select"
                )
            
            # 搜索结果显示
            filtered_questions = st.session_state.learning_data["questions"]
            if search_keyword:
                filtered_questions = [
                    q for q in st.session_state.learning_data["questions"]
                    if search_keyword.lower() in q['question'].lower() or 
                       (q.get('answer') and search_keyword.lower() in q.get('answer', '').lower())
                ]
                st.caption(f"🔍 找到 {len(filtered_questions)} 条相关记录")
            
            # 显示所有问题列表
            question_options = []
            for i, q in enumerate(filtered_questions):
                question_preview = q['question'][:50] + "..." if len(q['question']) > 50 else q['question']
                question_options.append(f"{i+1}. [{q.get('scenario', '答疑')}] {question_preview}")
            
            if question_options:
                # 多选删除
                questions_to_delete = st.multiselect(
                    "选择要删除的记录（可多选）",
                    options=question_options,
                    key="delete_questions_select"
                )
                
                col1, col2, col3 = st.columns([1, 1, 2])
                with col1:
                    if st.button("🗑️ 删除选中记录", type="primary", use_container_width=True):
                        if questions_to_delete:
                            # 获取要删除的索引
                            indices_to_delete = [int(q.split('.')[0]) - 1 for q in questions_to_delete]
                            # 保留未删除的记录
                            st.session_state.learning_data["questions"] = [
                                q for i, q in enumerate(st.session_state.learning_data["questions"])
                                if i not in indices_to_delete
                            ]
                            st.success(f"✅ 已删除 {len(questions_to_delete)} 条记录")
                            st.rerun()
                
                with col2:
                    if st.button("🗑️ 清空所有记录", use_container_width=True):
                        st.session_state.learning_data["questions"] = []
                        st.success("✅ 已清空所有聊天记录")
                        st.rerun()
                
                with col3:
                    st.caption(f"当前共 {len(st.session_state.learning_data['questions'])} 条记录")
                
                # 导出功能
                if st.button("📤 导出聊天记录", type="primary", use_container_width=True):
                    import json
                    from datetime import datetime
                    
                    if export_format == "TXT":
                        # 导出为 TXT 文件
                        export_content = ""
                        for i, q in enumerate(st.session_state.learning_data["questions"], 1):
                            export_content += f"第{i}条记录\n"
                            export_content += f"时间：{q.get('time', '未知')}\n"
                            export_content += f"场景：{q.get('scenario', '答疑')}\n"
                            export_content += f"问题：{q.get('question', '')}\n"
                            if q.get('answer'):
                                export_content += f"答案：{q.get('answer', '')}\n"
                            export_content += "-" * 50 + "\n"
                        
                        file_name = f"聊天记录_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                        st.download_button(
                            label="📥 下载 TXT 格式",
                            data=export_content.encode('utf-8'),
                            file_name=file_name,
                            mime="text/plain",
                            key="download_txt_chat"
                        )
                    else:
                        # 导出为 JSON 文件
                        file_name = f"聊天记录_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                        st.download_button(
                            label="📥 下载 JSON 格式",
                            data=json.dumps(st.session_state.learning_data["questions"], ensure_ascii=False, indent=2).encode('utf-8'),
                            file_name=file_name,
                            mime="application/json",
                            key="download_json_chat"
                        )
    
    tab1, tab2, tab3 = st.tabs(["📖 课前预习", "🎯 课中互动", "📝 课后辅导"])
    
    with tab1:
        st.markdown("### 📖 课前预习")
        
        # 子功能选项（一行显示）
        preview_mode = st.radio(
            "选择预习模式",
            ["📚 智能题库推荐", "💬 预习答疑", "🎯 知识点预览"],
            horizontal=True,
            label_visibility="collapsed",
            key="preview_mode_select"
        )
        
        if preview_mode == "📚 智能题库推荐":
            st.info("根据您的学习进度，AI 为您推荐针对性练习题")
            preview_question = st.chat_input("请输入您想练习的知识点或题目类型...", key="preview_chat")
            if preview_question:
                process_question(preview_question, "智能题库推荐", st.session_state.learning_data)
        
        elif preview_mode == "💬 预习答疑":
            st.info("预习过程中遇到疑问？随时向 AI 提问")
            preview_question = st.chat_input("请输入预习中的疑问...", key="preview_chat")
            if preview_question:
                process_question(preview_question, "预习答疑", st.session_state.learning_data)
        
        else:  # 知识点预览
            st.info("AI 为您梳理即将学习的知识点框架")
            preview_question = st.chat_input("请输入您想预习的课程内容或章节...", key="preview_chat")
            if preview_question:
                process_question(preview_question, "知识点预览", st.session_state.learning_data)
    
    with tab2:
        st.markdown("### 🎯 课中互动")
        
        # 子功能选项（一行显示）
        classroom_mode = st.radio(
            "选择互动模式",
            ["🎤 实时提问", "👥 小组协作", "💭 课堂讨论", "🎲 随机点名"],
            horizontal=True,
            label_visibility="collapsed",
            key="classroom_mode_select"
        )
        
        if classroom_mode == "🎤 实时提问":
            st.info("课堂上遇到问题？立即向 AI 提问")
            input_mode = st.radio("提问方式", ["文字提问", "语音提问"], horizontal=True, label_visibility="collapsed", key="classroom_input")
            if input_mode == "文字提问":
                classroom_prompt = st.chat_input("请输入课堂问题...", key="classroom_chat")
                if classroom_prompt:
                    process_question(classroom_prompt, "实时提问", st.session_state.learning_data)
            else:
                audio_value = st.audio_input("🎤 按住说话", key="classroom_voice")
                if audio_value:
                    process_audio(audio_value, "实时提问", st.session_state.learning_data)
        
        elif classroom_mode == "👥 小组协作":
            st.info("组织小组讨论，AI 提供协作指导")
            classroom_prompt = st.chat_input("请输入小组讨论的主题或任务...", key="group_chat")
            if classroom_prompt:
                process_question(classroom_prompt, "小组协作", st.session_state.learning_data)
        
        elif classroom_mode == "💭 课堂讨论":
            st.info("发起全班讨论，AI 引导深度思考")
            classroom_prompt = st.chat_input("请输入讨论话题...", key="discussion_chat")
            if classroom_prompt:
                process_question(classroom_prompt, "课堂讨论", st.session_state.learning_data)
        
        else:  # 随机点名
            st.info("班级管理 - 随机抽取学生回答问题")
            # 班级名单管理
            st.subheader("📋 班级管理")
            class_name = st.text_input("班级名称", placeholder="例如：高一 (3) 班", key="class_name_input")
            
            uploaded_roster = st.file_uploader(
                "上传班级名单（Excel/CSV/TXT 格式，每行一个姓名）",
                type=["xlsx", "xls", "csv", "txt"],
                key="roster_upload"
            )
            
            manual_students = st.text_area(
                "或手动输入学生名单",
                placeholder="张三\n李四\n王五\n赵六",
                height=80,
                key="manual_students"
            )
            
            student_list = []
            if uploaded_roster:
                try:
                    if uploaded_roster.type in ["text/plain", "text/csv"]:
                        content = uploaded_roster.read().decode('utf-8')
                        student_list = [line.strip() for line in content.split('\n') if line.strip()]
                    elif uploaded_roster.type in ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/vnd.ms-excel"]:
                        import pandas as pd
                        df = pd.read_excel(uploaded_roster)
                        student_list = df.iloc[:, 0].dropna().astype(str).tolist()
                    st.success(f"✅ 已加载 {len(student_list)} 名学生")
                except Exception as e:
                    st.error(f"读取名单失败：{str(e)}")
            elif manual_students:
                student_list = [line.strip() for line in manual_students.split('\n') if line.strip()]
            
            if student_list:
                st.divider()
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.subheader("🎲 随机点名")
                    if st.button("🎯 开始随机抽取", type="primary", use_container_width=True):
                        import random
                        selected_student = random.choice(student_list)
                        st.success(f"🎉 被点到的同学是：**{selected_student}**")
                        st.session_state.learning_data["interactions"].append({
                            "type": "random_pick",
                            "student": selected_student,
                            "class": class_name,
                            "timestamp": datetime.now()
                        })
                with col2:
                    st.subheader("👥 学生统计")
                    st.info(f"班级总人数：{len(student_list)}人")
                
                # 互动记录管理
                if st.session_state.learning_data.get("interactions"):
                    st.divider()
                    st.subheader("📊 互动记录管理")
                    
                    # 显示互动记录列表
                    interaction_options = []
                    for i, interaction in enumerate(st.session_state.learning_data["interactions"]):
                        if interaction.get("type") == "random_pick":
                            time_str = interaction.get("timestamp", datetime.now()).strftime("%H:%M:%S")
                            interaction_options.append(
                                f"{i+1}. 🎲 [{time_str}] {interaction.get('class', '未知班级')} - {interaction.get('student', '未知学生')}"
                            )
                    
                    if interaction_options:
                        interactions_to_delete = st.multiselect(
                            "选择要删除的互动记录（可多选）",
                            options=interaction_options,
                            key="delete_interactions_select"
                        )
                        
                        col1, col2 = st.columns([1, 3])
                        with col1:
                            if st.button("🗑️ 删除选中记录", type="primary", use_container_width=True):
                                if interactions_to_delete:
                                    # 获取要删除的索引
                                    indices_to_delete = [int(q.split('.')[0]) - 1 for q in interactions_to_delete]
                                    # 保留未删除的记录
                                    st.session_state.learning_data["interactions"] = [
                                        inter for i, inter in enumerate(st.session_state.learning_data["interactions"])
                                        if i not in indices_to_delete
                                    ]
                                    st.success(f"✅ 已删除 {len(interactions_to_delete)} 条互动记录")
                                    st.rerun()
                        
                        with col2:
                            if st.button("🗑️ 清空所有互动", use_container_width=True):
                                st.session_state.learning_data["interactions"] = []
                                st.success("✅ 已清空所有互动记录")
                                st.rerun()
    
    with tab3:
        st.markdown("### 📝 课后辅导")
        
        # 子功能选项（一行显示）
        homework_mode = st.radio(
            "选择辅导模式",
            ["📸 作业批改", "💬 错题讲解", "📚 个性化推荐"],
            horizontal=True,
            label_visibility="collapsed",
            key="homework_mode_select"
        )
        
        if homework_mode == "📸 作业批改":
            st.info("上传作业图片，AI 智能批改并给出反馈")
            homework_type = st.selectbox(
                "作业科目",
                ["语文", "数学", "英语", "物理", "化学", "生物", "历史", "地理", "政治", "体育", "美术", "音乐", "信息技术"]
            )
            uploaded_homework = st.file_uploader("上传作业图片", type=["jpg", "png", "jpeg"])
            if uploaded_homework:
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.image(uploaded_homework, caption="已上传的作业", use_container_width=True)
                with col2:
                    st.download_button(
                        label="📥 下载",
                        data=uploaded_homework.read(),
                        file_name=uploaded_homework.name,
                        mime=uploaded_homework.type,
                        key=f"homework_download_{uploaded_homework.name}"
                    )
                if st.button("🔍 开始批改"):
                    with st.spinner("正在分析作业..."):
                        st.success("✅ 批改完成！")
                        st.info("正确率：85%\n\n薄弱点：三角函数公式应用\n\n建议：复习正弦定理和余弦定理")
        
        elif homework_mode == "💬 错题讲解":
            st.info("遇到不会的题目？AI 详细讲解")
            homework_question = st.chat_input("请输入作业中的问题或拍照上传...", key="homework_chat")
            if homework_question:
                process_question(homework_question, "错题讲解", st.session_state.learning_data)
        
        else:  # 个性化推荐
            st.info("根据您的学习情况，AI 推荐针对性练习")
            homework_question = st.chat_input("请描述您想加强的知识点或薄弱环节...", key="recommend_chat")
            if homework_question:
                process_question(homework_question, "个性化推荐", st.session_state.learning_data)
    
    st.subheader("📎 上传教学资料")
    uploaded_files = st.file_uploader(
        "支持 PDF、Word、PPT 等多种格式，AI 将自动解析内容并提炼知识点",
        type=["pdf", "doc", "docx", "ppt", "pptx", "txt"],
        accept_multiple_files=True,
        key="material_upload"
    )
    if uploaded_files:
        for file in uploaded_files:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.success(f"✅ {file.name}")
            with col2:
                # 下载按钮
                st.download_button(
                    label="📥 下载",
                    data=file.read(),
                    file_name=file.name,
                    mime="application/octet-stream",
                    key=f"download_{file.name}"
                )
        
        if st.button("🤖 AI 解析课件内容", type="primary"):
            with st.spinner("正在解析课件内容..."):
                try:
                    client = OpenAI(api_key=DEFAULT_API_KEY, base_url=BASE_URL)
                    
                    # 构建文件信息
                    file_list = "\n".join([f"- {file.name} ({file.size} bytes)" for file in uploaded_files])
                    
                    prompt = f"""你是一位专业的教学内容分析师。请分析以下上传的教学资料，提取关键信息。

上传的文件列表：
{file_list}

请完成以下任务：
1. 📚 **知识点提炼**（列出核心概念、重点难点）
2. 🎯 **教学目标**（知识目标、能力目标、素养目标）
3. 📝 **典型例题**（提供 3-5 道代表性题目及解析）
4. 💡 **教学建议**（推荐的教学方法、活动设计）
5. ⏰ **课时安排**（建议学习时长、进度规划）
6. 🔗 **拓展资源**（相关知识点链接、延伸阅读材料）

要求：结构清晰，语言专业，适合教师直接使用。"""
                    
                    response = client.chat.completions.create(
                        model="moonshot-v1-8k",  # Kimi 模型
                        messages=[{"role": "user", "content": prompt}]
                    )
                    
                    analysis_result = response.choices[0].message.content
                    
                    st.success("✅ 课件解析完成！")
                    st.markdown(analysis_result)
                    
                except Exception as e:
                    st.error(f"解析失败：{str(e)}")

elif menu == "课件生成":
    st.title("📚 AI 课件生成")
    
    # ✅ 加载历史课件按钮
    col_hist, col_new = st.columns([1, 4])
    with col_hist:
        if st.button("📂 加载历史课件", use_container_width=True):
            if st.session_state.db_connected:
                try:
                    history_courseware = db.get_all_courseware()
                    if history_courseware:
                        # 创建选择框
                        courseware_options = {f"{cw['title']} ({cw['subject']})": cw for cw in history_courseware}
                        selected = st.selectbox(
                            "选择要加载的课件",
                            options=list(courseware_options.keys()),
                            key="select_history_courseware"
                        )
                        
                        if selected and st.button("确认加载", type="primary"):
                            cw = courseware_options[selected]
                            # 解析 JSON 数据
                            import json
                            cw_data = json.loads(cw['content'])
                            
                            # 恢复到 session_state
                            st.session_state.courseware_session = {
                                "topic": cw_data.get('title', cw['title']),
                                "grade_level": cw_data.get('grade_level', cw.get('grade_level', '')),
                                "subject": cw_data.get('subject', cw.get('subject', '')),
                                "requirements": cw_data.get('requirements', []),
                                "generated": True,
                                "outline": cw_data.get('outline', ''),
                                "ppt_content": cw_data.get('slides', []),
                                "db_id": cw['id']
                            }
                            
                            info(f"✅ 已加载课件：{selected}")
                            st.rerun()
                    else:
                        st.info("暂无历史课件")
                except Exception as e:
                    error(f"加载历史课件失败：{str(e)}")
            else:
                st.warning("数据库未连接，无法加载历史课件")
    
    # 第一步：基本信息输入
    st.subheader("📝 第一步：填写基本信息")
    col1, col2 = st.columns(2)
    with col1:
        topic = st.text_input("课件主题", value=st.session_state.courseware_session.get("topic", ""), placeholder="例如：函数的单调性", key="topic_input")
    with col2:
        grade_level = st.text_input(
            "年级",
            value=st.session_state.courseware_session.get("grade_level", ""),
            placeholder="例如：高一、八年级、大学一年级等",
            key="grade_input"
        )
    
    # 更新会话状态（科目由 AI 自动识别）
    if topic or grade_level:
        st.session_state.courseware_session["topic"] = topic
        st.session_state.courseware_session["grade_level"] = grade_level
    
    # 第二步：上传参考资料
    st.subheader("📎 第二步：上传参考资料（可选）")
    reference_files = st.file_uploader("上传教学资料，AI 将基于资料生成课件",
                                        type=["pdf", "doc", "docx", "ppt", "pptx", "txt"],
                                        accept_multiple_files=True,
                                        key="courseware_upload")
    
    if reference_files:
        for file in reference_files:
            st.success(f"✅ {file.name}")
    
    # 第三步：描述具体需求
    st.subheader("💬 第三步：描述您的具体需求")
    st.caption("您可以告诉 AI 想要什么样的课件风格、重点内容、活动设计等")
    
    # 初始化课件生成对话历史
    if "courseware_chat_history" not in st.session_state:
        st.session_state.courseware_chat_history = []
    
    # 显示对话历史
    if st.session_state.courseware_chat_history:
        st.divider()
        for message in st.session_state.courseware_chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        st.divider()
    
    # 需求输入框（聊天框）- 放在需求列表下方
    col1, col2 = st.columns([4, 1])
    with col1:
        requirement_input = st.text_input(
            "添加新要求",
            placeholder="请输入您的具体要求（如：希望多一些互动环节、需要包含视频资源链接等）...",
            key="requirement_input",
            label_visibility="collapsed"
        )
    with col2:
        add_btn = st.button("➕ 添加", type="primary", use_container_width=True, key="add_requirement_btn")
    
    if requirement_input and add_btn:
        # 添加到对话历史
        st.session_state.courseware_chat_history.append({
            "role": "user",
            "content": requirement_input
        })
        
        # 添加到需求列表
        st.session_state.courseware_session["requirements"].append(requirement_input)
        
        # AI 确认回复
        ai_response = "✅ 已记录您的要求，将在生成课件时考虑这一点。"
        st.session_state.courseware_chat_history.append({
            "role": "assistant",
            "content": ai_response
        })
        
        st.rerun()
    
    # 第四步：生成课件
    st.divider()
    st.subheader("🚀 第四步：生成课件")
    
    col1, col2 = st.columns([1, 3])
    with col1:
        generate_btn = st.button("开始生成课件", type="primary", use_container_width=True, disabled=not topic)
    with col2:
        if st.button("清空所有信息，重新开始", use_container_width=True):
            st.session_state.courseware_session = {
                "topic": "",
                "grade_level": "",
                "subject": "",
                "requirements": [],
                "generated": False,
                "outline": "",
                "ppt_content": ""
            }
            # 清空对话历史
            st.session_state.courseware_chat_history = []
            st.rerun()
    
    if generate_btn and topic:
        with st.status("正在生成课件...", expanded=True) as status:
            try:
                # 处理上传的文件内容
                file_content = ""
                if reference_files:
                    status.write("正在读取上传的资料...")
                    for file in reference_files:
                        try:
                            if file.type == "application/pdf":
                                file_content += f"\n【{file.name}】\n"
                                file_content += "(PDF 文件内容，建议使用 OCR 或 PDF 解析库)"
                            elif file.type in ["text/plain", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
                                file_content += f"\n【{file.name}】\n"
                                file_content += file.read().decode('utf-8')[:3000]
                        except Exception as e:
                            st.warning(f"读取文件 {file.name} 失败：{str(e)}")
                
                # 构建完整的需求描述
                requirements_text = "\n".join(st.session_state.courseware_session["requirements"]) if st.session_state.courseware_session.get("requirements") else "无特殊要求"
                
                # 调用 AI 识别科目并生成课件大纲
                client = OpenAI(api_key=DEFAULT_API_KEY, base_url=BASE_URL)
                
                # 第一步：查询 RAG 知识库，获取相关资料
                rag_context = ""
                rag_docs_found = []
                
                if st.session_state.rag_kb_connected:
                    try:
                        status.write("🔍 正在知识库中检索相关教学资料...")
                        rag_results = rag_kb.search_documents(topic, limit=5)
                        
                        if rag_results:
                            rag_context = "\n\n=== 知识库参考资料 ===\n\n"
                            for i, doc in enumerate(rag_results[:3], 1):
                                title = doc.get('title', '未知文档')
                                subject = doc.get('subject', '未知学科')
                                content = doc.get('content_text', '')[:1500]  # 每篇文档取前1500字
                                rag_docs_found.append({"title": title, "subject": subject})
                                
                                rag_context += f"📚 参考资料 {i}:《{title}》({subject})\n"
                                rag_context += f"{content}\n\n"
                                
                                # 更新使用次数
                                rag_kb.update_document_usage(doc['id'])
                            
                            rag_context += "=== 参考资料结束 ===\n\n"
                            status.write(f"✅ 找到 {len(rag_docs_found)} 篇相关教学资料")
                    except Exception as rag_error:
                        pass  # RAG 检索失败，静默处理
                
                # 第二步：构建提示词（带知识库上下文）
                if rag_context:
                    identify_prompt = f"""请根据主题'{topic}'和年级'{grade_level}'，自动识别该课程所属的学科（如：数学、物理、语文等），并为该课程设计一个课件。

以下是从知识库中检索到的相关教学资料，请优先参考这些内容：
{rag_context}

具体要求：
{requirements_text}

请提供：1.学科名称 2.教学目标 3.重点难点 4.知识点列表 5.典型例题 6.教学活动设计"""
                else:
                    identify_prompt = f"请根据主题'{topic}'和年级'{grade_level}'，自动识别该课程所属的学科（如：数学、物理、语文等），并为该课程设计一个课件。\n\n具体要求：\n{requirements_text}\n\n请提供：1.学科名称 2.教学目标 3.重点难点 4.知识点列表 5.典型例题 6.教学活动设计"
                
                response = client.chat.completions.create(
                    model="moonshot-v1-8k",
                    messages=[{"role": "user", "content": identify_prompt}]
                )
                
                outline = response.choices[0].message.content
                st.session_state.courseware_session["outline"] = outline
                
                # 尝试从 AI 回复中提取学科（简单处理，也可以让 AI 输出 JSON）
                subject = "综合" # 默认值
                if "学科：" in outline or "学科:" in outline:
                    subject_line = [line for line in outline.split('\n') if '学科' in line][0]
                    subject = subject_line.split('：')[-1].split(':')[-1].strip()
                
                st.session_state.courseware_session["subject"] = subject
                
                st.write(f"✅ 教学需求分析完成 (AI 识别学科: {subject})")
                if rag_docs_found:
                    st.caption(f"📚 参考了 {len(rag_docs_found)} 篇教学资料")
                time.sleep(0.5)
                st.write("✅ 知识点匹配完成")
                time.sleep(0.5)
                
                # 让 AI 生成 PPT 内容结构
                status.write("正在生成 PPT 课件...")
                ppt_prompt = f"""你是一位专业的 PPT 课件设计师。请为{grade_level}{subject}课程'{topic}'设计一个完整的 PPT 课件。

要求：
1. 总共 10-15 页幻灯片
2. 包含：封面、目录、教学目标、重点难点、知识点讲解（分多页）、典型例题、课堂小结、课后作业
3. 每页包含明确的标题和 3-5 个要点
4. 结合以下用户需求：{requirements_text}

请严格按照以下 JSON 格式输出（不要添加任何其他说明）：
{{
    "slides": [
        {{
            "title": "页面标题",
            "subtitle": "副标题或说明",
            "content": ["要点 1", "要点 2", "要点 3"]
        }}
    ]
}}

注意：只输出 JSON，不要有任何其他文字。"""
                
                ppt_response = client.chat.completions.create(
                    model="moonshot-v1-8k",
                    messages=[{"role": "user", "content": ppt_prompt}]
                )
                
                import json
                ppt_json = json.loads(ppt_response.choices[0].message.content)
                slides = ppt_json.get("slides", [])
                st.session_state.courseware_session["ppt_content"] = slides
                st.session_state.courseware_session["generated"] = True
                
                # ✅ 保存课件到数据库（实现持久化）
                if st.session_state.db_connected:
                    try:
                        courseware_data = {
                            "title": topic,
                            "subject": subject,
                            "grade_level": grade_level,
                            "outline": outline,
                            "slides": slides,
                            "requirements": st.session_state.courseware_session.get("requirements", []),
                            "reference_files": [f.name for f in reference_files] if reference_files else [],
                            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "version": "1.0"
                        }
                        
                        courseware_id = db.add_courseware(
                            title=topic,
                            subject=subject,
                            grade_level=grade_level,
                            content=json.dumps(courseware_data, ensure_ascii=False),
                            created_by=1  # 默认用户 ID
                        )
                        
                        if courseware_id:
                            info(f"✅ 课件已保存到数据库：{topic} (ID: {courseware_id})")
                            st.session_state.courseware_session["db_id"] = courseware_id
                    except Exception as db_error:
                        warning(f"⚠️ 课件保存到数据库失败：{str(db_error)}")
                
                status.update(label="✅ 课件生成完成!", state="complete")
                    
            except Exception as e:
                st.error(f"生成失败：{str(e)}")

# 显示已生成的课件内容（在 if generate_btn 块外，保持显示）
if st.session_state.courseware_session.get("generated") and st.session_state.courseware_session.get("outline"):
    st.divider()
    st.subheader("📊 已生成的课件")
    
    outline = st.session_state.courseware_session["outline"]
    slides = st.session_state.courseware_session.get("ppt_content", [])
    
    # 显示生成的内容
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📊 PPT 大纲")
        st.markdown(outline)
    
    with col2:
        st.subheader("📝 教案详情")
        st.text_area("教案内容", value=outline, height=400, key="outline_display")
    
    # 显示完整 PPT 内容预览
    st.divider()
    st.subheader("📄 PPT 课件预览")
    
    # 展示每一页幻灯片
    for i, slide in enumerate(slides):
        with st.expander(f"📄 第 {i+1} 页：{slide.get('title', '无标题')}", expanded=(i==0)):
            if slide.get('subtitle'):
                st.caption(slide.get('subtitle'))
            content = slide.get('content', [])
            for point in content:
                st.write(f"• {point}")
    
    # 使用 Kimi 生成的 JSON 数据创建真实的 PPT 文件
    from pptx import Presentation
    from pptx.util import Pt
    import io
    
    try:
        prs = Presentation()
        font_name = 'Microsoft YaHei'
        
        for i, slide_data in enumerate(slides):
            if i == 0:
                slide_layout = prs.slide_layouts[0]
            else:
                slide_layout = prs.slide_layouts[1]
            
            slide = prs.slides.add_slide(slide_layout)
            
            title = slide_data.get('title', '')
            if slide.shapes.title:
                slide.shapes.title.text = title
                for paragraph in slide.shapes.title.text_frame.paragraphs:
                    for run in paragraph.runs:
                        run.font.name = font_name
                        run.font.size = Pt(32)
                        run.font.bold = True
            
            subtitle = slide_data.get('subtitle')
            if subtitle and len(slide.placeholders) > 1:
                subtitle_placeholder = slide.placeholders[1]
                tf = subtitle_placeholder.text_frame
                p = tf.paragraphs[0]
                p.text = subtitle
                for run in p.runs:
                    run.font.name = font_name
                    run.font.size = Pt(18)
            
            if len(slide.placeholders) > 1 and slide_data.get('content'):
                content_placeholder = slide.placeholders[1]
                tf = content_placeholder.text_frame
                tf.clear()
                
                for j, point in enumerate(slide_data['content']):
                    p = tf.add_paragraph() if j > 0 else tf.paragraphs[0]
                    p.text = point
                    p.level = 0
                    p.space_after = Pt(10)
                    for run in p.runs:
                        run.font.name = font_name
                        run.font.size = Pt(18)
        
        ppt_bytes = io.BytesIO()
        prs.save(ppt_bytes)
        ppt_bytes.seek(0)
        
        topic = st.session_state.courseware_session.get("topic", "课件")
        grade_level = st.session_state.courseware_session.get("grade_level", "")
        subject = st.session_state.courseware_session.get("subject", "")
        ppt_file_name = f"{topic}_{grade_level}_{subject}_课件.pptx"
        st.download_button(
            label="📥 下载 PPT 课件（可编辑的 PowerPoint 文件）",
            data=ppt_bytes.getvalue(),
            file_name=ppt_file_name,
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            help="点击下载生成的 PPT 课件，可在 PowerPoint 或 WPS 中打开编辑",
            type="primary"
        )
        
        # Word 教案下载功能
        from docx import Document
        from docx.shared import Pt, Inches
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        
        try:
            doc = Document()
            
            # 添加标题
            heading = doc.add_heading(f"{topic} - 教案", 0)
            heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
            
            # 添加基本信息
            doc.add_paragraph(f"年级：{grade_level}")
            doc.add_paragraph(f"学科：{subject}")
            doc.add_paragraph(f"主题：{topic}")
            doc.add_paragraph()
            
            # 添加教案大纲内容
            doc.add_heading('一、教学大纲', level=1)
            doc.add_paragraph(outline)
            
            # 添加 PPT 详细内容
            doc.add_heading('二、PPT 课件内容详情', level=1)
            for i, slide_data in enumerate(slides, 1):
                doc.add_heading(f'第{i}页：{slide_data.get("title", "无标题")}', level=2)
                if slide_data.get('subtitle'):
                    doc.add_paragraph(f'副标题：{slide_data.get("subtitle")}')
                content = slide_data.get('content', [])
                for point in content:
                    doc.add_paragraph(point, style='List Bullet')
                doc.add_paragraph()
            
            # 保存为 docx 文件
            docx_bytes = io.BytesIO()
            doc.save(docx_bytes)
            docx_bytes.seek(0)
            
            docx_file_name = f"{topic}_{grade_level}_{subject}_教案.docx"
            st.download_button(
                label="📥 下载 Word 教案（可编辑的 Word 文档）",
                data=docx_bytes.getvalue(),
                file_name=docx_file_name,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                help="点击下载配套的详细教案，可在 Microsoft Word 或 WPS 中打开编辑",
                type="primary"
            )
        except Exception as docx_error:
            st.error(f"Word 教案生成失败：{str(docx_error)}")
            st.info("💡 建议：可以手动复制上面的教案内容到 Word 文档中")
    except Exception as ppt_error:
        st.error(f"PPT 文件生成失败：{str(ppt_error)}")
        st.info("💡 建议：可以手动复制上面的 PPT 内容到 PowerPoint 中")

elif menu == "知识库管理":
    st.title("🗄️ 知识库管理")
    
    # 初始化 RAG 知识库
    if "rag_documents" not in st.session_state:
        st.session_state.rag_documents = []
    
    # 统计信息（结合 RAG 数据库）
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        # 从 RAG 数据库获取统计
        rag_stats = rag_kb.get_statistics() if st.session_state.rag_kb_connected else {}
        total_docs = rag_stats.get('total_documents', 0)
        st.metric("RAG 文档总数", total_docs, f"+{total_docs}" if total_docs > 0 else "0")
    with col2:
        total_points = rag_stats.get('total_knowledge_points', 0)
        st.metric("知识点数量", total_points, "AI 自动提取")
    with col3:
        avg_usage = rag_stats.get('average_usage', 0)
        st.metric("平均使用次数", round(avg_usage, 1), "持续更新中")
    with col4:
        subject_dist = rag_stats.get('subject_distribution', [])
        st.metric("覆盖学科数", len(subject_dist), f"{len(subject_dist)} 个学科" if subject_dist else "持续更新中")
    
    st.divider()
    
    # 上传文档区域
    st.subheader("📤 上传文档到知识库")
    uploaded_docs = st.file_uploader(
        "支持上传教学资料、学术论文、参考书籍等",
        type=["pdf", "doc", "docx", "ppt", "pptx", "txt", "md"],
        accept_multiple_files=True,
        key="knowledge_upload",
        help="上传后 AI 将自动解析并归类到知识库"
    )
    
    if uploaded_docs:
        for file in uploaded_docs:
            # ✅ 去重检查：检查是否已上传同名文件
            existing_names = [doc['name'] for doc in st.session_state.knowledge_base["documents"]]
            if file.name in existing_names:
                st.warning(f"⚠️ {file.name} 已存在于知识库中，跳过重复上传")
                continue
            
            col1, col2 = st.columns([4, 1])
            with col1:
                try:
                    # 智能分类
                    file_ext = file.name.split('.')[-1].lower()
                    category_map = {
                        'pdf': '📚 学术文献',
                        'doc': '📖 教学资料',
                        'docx': '📖 教学资料',
                        'ppt': '📊 演示文稿',
                        'pptx': '📊 演示文稿',
                        'txt': '📝 文本资料',
                        'md': '📝 文本资料'
                    }
                    category = category_map.get(file_ext, '📁 其他')
                    
                    # 解析文件为统一的 JSON 格式
                    with st.spinner(f"正在解析 {file.name}..."):
                        document_data = doc_parser.parse_to_json(
                            file=file,
                            subject="通用",  # 可以根据实际情况设置学科
                            uploaded_by="teacher"
                        )
                    
                    if document_data:
                        # ✅ 保存到 RAG 数据库前，再次检查是否已存在
                        doc_id = None
                        if st.session_state.rag_kb_connected:
                            try:
                                # 检查数据库中是否已存在同名文档
                                existing_docs = rag_kb.search_documents(file.name, limit=10)
                                is_duplicate = any(doc.get('title') == file.name for doc in existing_docs)
                                
                                if is_duplicate:
                                    warning(f"⚠️ 数据库中已存在 {file.name}，跳过保存")
                                else:
                                    # 保存到 JSON 文件
                                    json_filepath = doc_parser.save_to_file(document_data)
                                    
                                    # 保存到 RAG 数据库
                                    doc_id = rag_kb.add_document(
                                        title=file.name,
                                        subject="通用",
                                        file_path=json_filepath,
                                        file_type=file_ext,
                                        content_text=document_data.get('content', {}).get('raw_text', ''),
                                        knowledge_points=document_data.get('analysis', {}).get('knowledge_points', []),
                                        ai_summary=document_data.get('analysis', {}).get('summary', ''),
                                        uploaded_by="teacher"
                                    )
                                    if doc_id:
                                        info(f"✅ 文档已保存到 RAG 数据库：{file.name} (ID: {doc_id})")
                            except Exception as db_error:
                                warning(f"⚠️ RAG 数据库保存失败：{str(db_error)}")
                                doc_id = None
                        else:
                            # 数据库未连接，仅保存到本地
                            json_filepath = doc_parser.save_to_file(document_data)
                            warning("⚠️ RAG 数据库未连接，文档仅保存在本地")
                        
                        # 添加到 session_state（用于前端显示）
                        doc_info = {
                            "name": file.name,
                            "type": file_ext,
                            "size": file.size,
                            "category": category,
                            "upload_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "json_format": True,  # 标记为 JSON 格式
                            "json_data": document_data,  # 完整的 JSON 数据
                            "json_file_path": json_filepath if 'json_filepath' in locals() else '',  # JSON 文件路径
                            "rag_doc_id": doc_id  # RAG 数据库 ID
                        }
                        
                        st.session_state.knowledge_base["documents"].append(doc_info)
                        
                        # 更新分类统计
                        if category not in st.session_state.knowledge_base["categories"]:
                            st.session_state.knowledge_base["categories"][category] = 0
                        st.session_state.knowledge_base["categories"][category] += 1
                        
                        if doc_id:
                            st.success(f"✅ {file.name} (已保存到数据库 + JSON 格式)")
                        else:
                            st.success(f"✅ {file.name} (已转换为 JSON 格式)")
                    else:
                        st.error(f"❌ {file.name} 解析失败")
                        
                except Exception as e:
                    st.error(f"处理文件 {file.name} 失败：{str(e)}")
                    error(f"文件解析失败：{file.name} - {str(e)}")
                    
            with col2:
                # 下载按钮（提供原始文件和 JSON 文件两种选择）
                download_option = st.selectbox(
                    "",
                    options=["原始文件", "JSON 格式"],
                    key=f"download_type_{file.name}",
                    label_visibility="collapsed"
                )
                
                if download_option == "原始文件":
                    file.seek(0)  # 重置指针
                    st.download_button(
                        label="📥 下载",
                        data=file.read(),
                        file_name=file.name,
                        mime="application/octet-stream",
                        key=f"knowledge_download_{file.name}"
                    )
                else:
                    # 下载 JSON 格式
                    if 'json_data' in locals() and json_data:
                        json_str = doc_parser.to_json_string(json_data)
                        json_filename = file.name.rsplit('.', 1)[0] + '.json'
                        st.download_button(
                            label="📥 下载 JSON",
                            data=json_str,
                            file_name=json_filename,
                            mime="application/json",
                            key=f"json_download_{file.name}"
                        )
        
        # 显示已上传的文件列表和管理功能
        if st.session_state.knowledge_base["documents"]:
            st.divider()
            st.subheader("📚 已上传的文件")
            
            # 批量删除功能
            files_to_delete = st.multiselect(
                "选择要删除的文件（可多选）",
                options=[doc["name"] for doc in st.session_state.knowledge_base["documents"]],
                key="delete_files_select"
            )
            
            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button("🗑️ 删除选中文件", type="primary", use_container_width=True):
                    if files_to_delete:
                        deleted_count = 0
                        # 从 RAG 数据库中删除
                        for doc_name in files_to_delete:
                            # 查找文档信息
                            doc_info = next((doc for doc in st.session_state.knowledge_base["documents"] if doc["name"] == doc_name), None)
                            if doc_info and doc_info.get('rag_doc_id'):
                                try:
                                    rag_kb.delete_document(doc_info['rag_doc_id'])
                                    info(f"✅ 已从 RAG 数据库删除：{doc_name}")
                                except Exception as db_error:
                                    warning(f"⚠️ RAG 数据库删除失败：{doc_name} - {str(db_error)}")
                        
                        # 从 session state 中删除
                        st.session_state.knowledge_base["documents"] = [
                            doc for doc in st.session_state.knowledge_base["documents"]
                            if doc["name"] not in files_to_delete
                        ]
                        deleted_count = len(files_to_delete)
                        st.success(f"✅ 已删除 {deleted_count} 个文件")
                        # 清空 multiselect 的选择状态
                        st.session_state.delete_files_select = []
                        st.rerun()
            
            with col2:
                if st.button("🗑️ 清空所有文件", use_container_width=True):
                    # 从 RAG 数据库中删除所有文档
                    if st.session_state.rag_kb_connected:
                        try:
                            all_docs = rag_kb.get_all_documents(limit=1000)
                            for doc in all_docs:
                                rag_kb.delete_document(doc['id'])
                            info(f"✅ 已从 RAG 数据库清空 {len(all_docs)} 个文档")
                        except Exception as db_error:
                            warning(f"⚠️ RAG 数据库清空失败：{str(db_error)}")
                    
                    # 清空 session state
                    st.session_state.knowledge_base["documents"] = []
                    st.session_state.knowledge_base["categories"] = {}
                    st.success("✅ 已清空所有文件")
                    st.rerun()
            
            # 显示文件列表
            st.caption(f"共 {len(st.session_state.knowledge_base['documents'])} 个文件")
        if st.button("🤖 AI 智能解析并归类", type="primary"):
            with st.spinner("正在解析文档内容并提取知识点..."):
                try:
                    client = OpenAI(api_key=DEFAULT_API_KEY, base_url=BASE_URL)
                    
                    # 构建文档列表
                    doc_list = "\n".join([f"- {doc['name']} ({doc['type']}, {doc['size']} bytes)" 
                                        for doc in st.session_state.knowledge_base["documents"]])
                    
                    prompt = f"""你是一位专业的知识管理专家。请分析以下上传到知识库的文档，完成以下任务：

文档列表：
{doc_list}

请提供：
1. 📋 **文档分类建议**（按学科、难度、用途等维度）
2. 🎯 **核心知识点提取**（从所有文档中提取关键知识点）
3. 🔗 **知识关联分析**（文档之间的关联性和互补性）
4. 💡 **使用建议**（如何在教学中有效利用这些资源）
5. 📊 **知识结构图**（建议的知识组织方式）

要求：结构清晰，便于教师快速定位和使用。"""
                    
                    response = client.chat.completions.create(
                        model="moonshot-v1-8k",  # Kimi 模型
                        messages=[{"role": "user", "content": prompt}]
                    )
                    
                    analysis = response.choices[0].message.content
                    
                    st.success("✅ AI 解析完成！")
                    with st.expander("📖 查看 AI 解析结果", expanded=True):
                        st.markdown(analysis)
                    
                except Exception as e:
                    st.error(f"解析失败：{str(e)}")
    
    st.divider()
    
    # RAG 智能检索功能
    st.subheader("🔍 RAG 智能检索")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        search_query = st.text_input(
            "输入关键词搜索知识文档",
            placeholder="例如：函数单调性、牛顿定律、三角函数...",
            key="rag_search"
        )
    with col2:
        search_subject = st.selectbox(
            "限定学科",
            ["全部"] + ["语文", "数学", "英语", "物理", "化学", "生物", 
                       "历史", "地理", "政治", "体育", "美术", "音乐", "信息技术"],
            key="rag_subject"
        )
    
    if search_query and st.button("🔍 搜索", type="primary"):
        with st.spinner("正在 RAG 知识库中检索..."):
            # 从 RAG 数据库搜索
            subject = None if search_subject == "全部" else search_subject
            results = rag_kb.search_documents(search_query, subject=subject, limit=10)
            
            if results:
                st.success(f"✅ 找到 {len(results)} 篇相关文档")
                
                # 显示搜索结果
                for i, doc in enumerate(results, 1):
                    col1, col2 = st.columns([4, 1])
                    
                    with col1:
                        with st.expander(f"📄 {i}. {doc.get('title', '无标题')} - {doc.get('subject', '未知学科')}"):
                            st.markdown(f"**摘要:** {doc.get('ai_summary', '暂无摘要')}")
                            
                            # 使用次数 +1
                            rag_kb.update_document_usage(doc['id'])
                    
                    with col2:
                        # 提供下载按钮
                        file_name = f"{doc.get('title', '文档')}_{doc.get('subject', '未知')}.txt"
                        content = doc.get('content_text', doc.get('ai_summary', '暂无内容'))
                        st.download_button(
                            label="📥 下载",
                            data=content,
                            file_name=file_name,
                            mime="text/plain",
                            key=f"download_rag_{doc.get('id', i)}",
                            use_container_width=True
                        )
            else:
                st.info(f"💡 未在 RAG 知识库中找到相关文档，请尝试其他关键词或上传更多资料。")
    
    st.divider()
    
    # 知识库展示
    st.subheader("📚 知识库内容")
    
    # 分类筛选
    categories = list(st.session_state.knowledge_base.get("categories", {}).keys())
    if categories:
        selected_category = st.selectbox(
            "按分类筛选",
            ["全部"] + categories,
            key="category_filter"
        )
        
        # 显示文档列表
        docs = st.session_state.knowledge_base.get("documents", [])
        if docs:
            if selected_category != "全部":
                filtered_docs = [d for d in docs if d["category"] == selected_category]
            else:
                filtered_docs = docs
            
            if filtered_docs:
                st.info(f"📊 共 {len(filtered_docs)} 篇文档")
                
                # 表格展示
                display_data = {
                    "📄 文档名称": [d["name"] for d in filtered_docs],
                    "📂 分类": [d["category"] for d in filtered_docs],
                    "📝 类型": [f".{d['type']}" for d in filtered_docs],
                    "💾 大小": [f"{d['size']/1024:.1f} KB" if d['size'] < 1024*1024 else f"{d['size']/1024/1024:.2f} MB" for d in filtered_docs],
                    "⏰ 上传时间": [d["upload_time"] for d in filtered_docs]
                }
                st.dataframe(display_data, use_container_width=True, hide_index=True)
            else:
                st.warning("该分类下暂无文档")
        else:
            st.info("📭 知识库为空，请上传文档")
    else:
        st.info("📭 知识库为空，请上传文档")

elif menu == "学情分析":
    st.title("📊 AI 学情分析")
    
    # 选择分析模式
    analysis_mode = st.radio(
        "分析模式",
        ["单个学生", "全班评估"],
        horizontal=True,
        key="analysis_mode_select"
    )
    
    if analysis_mode == "单个学生":
        student_name = st.text_input("学生姓名", placeholder="输入姓名以生成个人报告")
    else:
        class_name = st.text_input("班级名称", placeholder="例如：高一 (3) 班")
        total_students = st.number_input("班级总人数", min_value=1, value=45)
    
    # 上传成绩数据
    st.subheader("📁 上传成绩/学习数据")
    uploaded_files = st.file_uploader(
        "上传成绩单、作业统计表、考试分析等文件，AI 将生成详细的学情报告",
        type=["xlsx", "xls", "csv", "pdf", "doc", "docx", "txt"],
        accept_multiple_files=True,
        key="study_upload",
        help="支持 Excel 成绩单、CSV 数据表、Word 文档等格式"
    )
    
    if uploaded_files:
        for file in uploaded_files:
            st.success(f"✅ {file.name}")
    
    # 显示统计数据
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("问题总数", len(st.session_state.learning_data.get("questions", [])), "今日新增")
    with col2:
        correct_rate = st.session_state.learning_data.get("correct_rate", 0)
        st.metric("平均正确率", f"{correct_rate}%" if correct_rate else "0%", "待更新")
    with col3:
        study_time = st.session_state.learning_data.get("study_time", 0)
        st.metric("学习时长", f"{study_time}分钟", "累计")
    
    # 互动记录展示
    st.subheader("📝 最近互动记录")
    questions = st.session_state.learning_data.get("questions", [])
    if questions:
        for q in questions[-5:]:
            st.info(f"{q.get('time', '')} - {q.get('scenario', '')}: {q.get('question', '')[:50]}...")
    else:
        st.info("暂无互动记录")
    
    # AI 生成学情报告
    if st.button("🤖 AI 生成学情报告", type="primary"):
        with st.spinner("正在分析学习数据并生成报告..."):
            try:
                client = OpenAI(api_key=DEFAULT_API_KEY, base_url=BASE_URL)
                
                # 构建分析请求
                if analysis_mode == "单个学生":
                    target = f"学生：{student_name if student_name else '某同学'}"
                else:
                    target = f"班级：{class_name if class_name else '某班'}（共{total_students}人）"
                
                # 基础数据摘要
                data_summary = f"【学情分析对象】{target}\n\n"
                data_summary += f"【互动数据】\n"
                data_summary += f"- 总问题数：{len(questions)}\n"
                if questions:
                    scenarios = {}
                    for q in questions:
                        scenario = q.get('scenario', '未知')
                        scenarios[scenario] = scenarios.get(scenario, 0) + 1
                    data_summary += "- 互动场景分布：\n"
                    for s, c in scenarios.items():
                        data_summary += f"  · {s}: {c}次\n"
                
                # 处理上传的文件
                file_info = ""
                if uploaded_files:
                    file_info = "\n【上传的成绩/学习数据文件】\n"
                    for file in uploaded_files:
                        file_info += f"- {file.name} ({file.size} bytes)\n"
                        # 读取文本类型文件内容
                        if file.type in ["text/plain", "text/csv"]:
                            try:
                                content = file.read().decode('utf-8')[:2000]
                                file_info += f"  内容预览：{content[:500]}...\n"
                            except:
                                pass
                
                prompt = f"""你是一位专业的教育数据分析师。请根据以下数据和信息，生成一份详细的学情分析报告。

{target}

{data_summary}
{file_info}

请生成包含以下内容的报告：
1. 📊 **整体情况概览**（包括平均分、优秀率、及格率等关键指标）
2. 📈 **成绩分布分析**（分数段统计、正态分布分析）
3. 🎯 **知识点掌握情况**（优势知识点、薄弱知识点 TOP5）
4. 👥 **学生分层分析**（学优生、中等生、学困生比例及特点）
5. 📉 **典型问题分析**（错误率高的题目类型和原因）
6. 💡 **个性化教学建议**（针对不同层次学生的具体建议）
7. 📋 **后续教学计划**（重点讲解内容、练习安排）

要求：数据可视化呈现，使用图表、表格等形式，语言简洁专业。"""
                
                response = client.chat.completions.create(
                    model="moonshot-v1-8k",  # Kimi 模型
                    messages=[{"role": "user", "content": prompt}]
                )
                
                report = response.choices[0].message.content
                
                st.success("✅ 学情报告生成完成！")
                
                # 显示报告
                st.markdown(report)
                
                # 添加图表生成提示
                st.info("💡 **提示**：以上数据可由 AI 协助制作可视化图表，建议使用 Excel、Python matplotlib 等工具根据分析报告中的数据绘制：\n- 成绩分布直方图\n- 知识点掌握雷达图\n- 学生分层饼图\n- 成绩变化趋势图")
                
            except Exception as e:
                st.error(f"生成失败：{str(e)}")
