"""
学情分析服务模块
处理所有与学情分析相关的业务逻辑
"""
import streamlit as st
from datetime import datetime
from core.prompts import AnalysisPrompts
from openai import OpenAI
from data.data_manager import LearningDataManager


class AnalysisService:
    """学情分析业务逻辑服务"""
    
    def __init__(self):
        """初始化学情分析服务"""
        self.client = None
    
    def _get_client(self, api_key, base_url):
        """获取 OpenAI 客户端"""
        if not self.client:
            self.client = OpenAI(api_key=api_key, base_url=base_url)
        return self.client
    
    def generate_report(self, analysis_mode, student_info, uploaded_files, 
                       questions_data, api_key, base_url):
        """生成学情报告"""
        result = {"success": False, "report": "", "error": None}
        
        try:
            client = self._get_client(api_key, base_url)
            
            # 构建目标信息
            if analysis_mode == "单个学生":
                target_info = f"【学情分析对象】学生：{student_info.get('name', '某同学')}"
            else:
                total_students = student_info.get('total_students', 45)
                class_name = student_info.get('class_name', '某班')
                target_info = f"【学情分析对象】班级：{class_name}（共{total_students}人）"
            
            # 基础数据摘要
            data_summary = f"【互动数据】\n"
            data_summary += f"- 总问题数：{len(questions_data)}\n"
            
            if questions_data:
                scenarios = {}
                for q in questions_data:
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
            
            # 生成提示词
            prompt = AnalysisPrompts.get_analysis_prompt(
                target_info=target_info,
                data_summary=data_summary,
                file_info=file_info
            )
            
            response = client.chat.completions.create(
                model="moonshot-v1-8k",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=2000
            )
            
            result["report"] = response.choices[0].message.content
            result["success"] = True
            
            # 自动备份学习数据
            LearningDataManager.save_learning_data()
            
        except Exception as e:
            result["error"] = str(e)
            result["success"] = False
        
        return result
    
    def get_statistics(self, questions_data):
        """获取统计数据"""
        stats = {
            "total_questions": len(questions_data),
            "scenarios": {},
            "correct_rate": 0,
            "study_time": 0
        }
        
        if questions_data:
            # 统计场景分布
            for q in questions_data:
                scenario = q.get('scenario', '未知')
                stats["scenarios"][scenario] = stats["scenarios"].get(scenario, 0) + 1
            
            # 计算正确率（如果有相关数据）
            answered = sum(1 for q in questions_data if q.get('answered', False))
            if answered > 0:
                stats["correct_rate"] = int((answered / len(questions_data)) * 100)
        
        return stats
    
    def manage_learning_data(self, action, **kwargs):
        """管理学习数据"""
        result = {"success": False, "data": None, "error": None}
        
        try:
            if action == "backup":
                # 备份数据
                success = LearningDataManager.save_learning_data()
                result["success"] = success
                
            elif action == "restore":
                # 恢复数据
                success = LearningDataManager.load_learning_data()
                result["success"] = success
                
            elif action == "export":
                # 导出数据
                format_type = kwargs.get("format", "json")
                learning_data = st.session_state.get("learning_data", {})
                
                if format_type == "json":
                    import json
                    result["data"] = json.dumps(learning_data, ensure_ascii=False, indent=2)
                else:
                    # TXT 格式
                    text_lines = ["学习数据导出\n", "=" * 50 + "\n\n"]
                    questions = learning_data.get("questions", [])
                    for i, q in enumerate(questions, 1):
                        text_lines.append(f"{i}. [{q.get('time', '')}] {q.get('scenario', '')}\n")
                        text_lines.append(f"   问题：{q.get('question', '')}\n")
                        text_lines.append(f"   回答：{q.get('answer', '')}\n\n")
                    result["data"] = "".join(text_lines)
                
                result["success"] = True
                
            elif action == "clear":
                # 清空数据
                st.session_state.learning_data = {
                    "questions": [],
                    "interactions": [],
                    "correct_rate": 0,
                    "study_time": 0
                }
                result["success"] = True
                
        except Exception as e:
            result["error"] = str(e)
            result["success"] = False
        
        return result
