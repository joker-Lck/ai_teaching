"""
课件生成服务模块
"""
import streamlit as st
from datetime import datetime
import time
import json
import os
import re
from openai import OpenAI
from data.db_operations import db
from core.prompts import CoursewarePrompts, ClarificationPrompts, DocumentAnalysisPrompts
from services.image_service import ImageService
from services.animation_service import AnimationService
from core.utils import clean_json_string, safe_json_loads
from core.logger import error as log_error


class CoursewareService:
    """课件生成业务逻辑服务"""
    
    def __init__(self):
        """初始化服务"""
        self.client = None
        self.image_service = ImageService()
        self.animation_service = AnimationService()
    
    def _get_client(self, api_key, base_url):
        """获取 OpenAI 客户端"""
        if not self.client:
            self.client = OpenAI(api_key=api_key, base_url=base_url)
        return self.client
    
    def start_clarification(self, topic, api_key, base_url):
        """开始需求澄清对话"""
        result = {"success": False, "question": "", "error": None}
        
        try:
            client = self._get_client(api_key, base_url)
            
            # 生成初始澄清问题
            clarification_prompt = ClarificationPrompts.get_initial_clarification_prompt(topic)
            
            response = client.chat.completions.create(
                model="moonshot-v1-8k",
                messages=[{"role": "user", "content": clarification_prompt}]
            )
            
            result["question"] = response.choices[0].message.content
            result["success"] = True
            
        except Exception as e:
            result["error"] = str(e)
            result["success"] = False
        
        return result
    
    def continue_clarification(self, topic, conversation_history, api_key, base_url):
        """继续澄清或总结需求"""
        result = {
            "success": False, 
            "response": "", 
            "confirmed": False,
            "requirements": [],
            "error": None
        }
        
        try:
            client = self._get_client(api_key, base_url)
            
            # 构建消息列表
            messages = [{"role": m["role"], "content": m["content"]} for m in conversation_history]
            
            # 添加总结提示
            summary_prompt = ClarificationPrompts.get_clarification_continue_prompt(
                topic, conversation_history
            )
            messages.append({"role": "user", "content": summary_prompt})
            
            response = client.chat.completions.create(
                model="moonshot-v1-8k",
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            ai_response = response.choices[0].message.content
            result["response"] = ai_response
            result["success"] = True
            
            # 检查是否已确认需求
            if "需求已确认" in ai_response:
                result["confirmed"] = True
                # 提取需求（简化处理，实际可以更复杂）
                result["requirements"] = [m["content"] for m in conversation_history if m["role"] == "user"]
            
        except Exception as e:
            result["error"] = str(e)
            result["success"] = False
        
        return result
    
    def generate_courseware(self, topic, requirements_text, api_key, base_url, fast_mode=True):
        """生成课件
        
        参数：
        - topic: 课件主题
        - requirements_text: 需求描述
        - api_key: API 密钥
        - base_url: API 基础 URL
        - fast_mode: 是否启用快速模式（默认 True），快速模式下禁用图片生成、简化装饰
        """
        result = {
            "success": False,
            "subject": "",
            "outline": "",
            "slides": [],
            "theme": {},
            "generated_images": {},
            "ppt_content": None,
            "error": None
        }
        
        try:
            client = self._get_client(api_key, base_url)
            
            # Step 1: 学科识别和大纲生成
            identify_prompt = CoursewarePrompts.get_identify_prompt(
                topic=topic,
                requirements_text=requirements_text,
                rag_context=None  # 可以传入 RAG 上下文
            )
            
            response = client.chat.completions.create(
                model="moonshot-v1-8k",
                messages=[{"role": "user", "content": identify_prompt}],
                temperature=0.7,
                max_tokens=1000,
                timeout=30
            )
            
            # 解析 JSON
            response_content = clean_json_string(response.choices[0].message.content)
            
            # 去除 Markdown 代码块标记
            if response_content.startswith('```'):
                # 找到第一个换行符
                first_newline = response_content.find('\n')
                if first_newline != -1:
                    response_content = response_content[first_newline:].strip()
                # 去除末尾的代码块标记
                if response_content.endswith('```'):
                    response_content = response_content[:-3].strip()
                # 也可能有 json 或 JSON 语言标识
                if response_content.startswith('json') or response_content.startswith('JSON'):
                    response_content = response_content[4:].strip()
            
            # 尝试提取 JSON 对象（处理 AI 返回多余文本的情况）
            json_match = re.search(r'\{[\s\S]*\}', response_content)
            if json_match:
                response_content = json_match.group(0)
            
            # 使用安全的 JSON 解析函数
            outline_data = safe_json_loads(response_content)
            if outline_data is None:
                log_error(f"JSON 解析失败：内容为空\n原始内容前500字符：{response_content[:500]}")
                raise ValueError("AI 返回的 JSON 内容为空")
            
            result["outline_json"] = response_content  # 保存原始 JSON 文本用于调试
            subject = outline_data.get("subject", "综合")
            outline = outline_data.get("outline", "")
            
            result["subject"] = subject
            result["outline"] = outline
            
            # Step 2: PPT 结构生成
            ppt_prompt = CoursewarePrompts.get_ppt_prompt(
                subject=subject,
                topic=topic,
                requirements_text=requirements_text,
                fast_mode=fast_mode  # 传递快速模式参数
            )
            
            ppt_response = client.chat.completions.create(
                model="moonshot-v1-8k",
                messages=[{"role": "user", "content": ppt_prompt}],
                temperature=0.7,
                max_tokens=2500,
                timeout=45
            )
            
            # 解析 PPT JSON
            ppt_content = clean_json_string(ppt_response.choices[0].message.content)
            
            # 去除 Markdown 代码块标记
            if ppt_content.startswith('```'):
                first_newline = ppt_content.find('\n')
                if first_newline != -1:
                    ppt_content = ppt_content[first_newline:].strip()
                if ppt_content.endswith('```'):
                    ppt_content = ppt_content[:-3].strip()
                if ppt_content.startswith('json') or ppt_content.startswith('JSON'):
                    ppt_content = ppt_content[4:].strip()
            
            # 尝试提取 JSON 对象
            json_match = re.search(r'\{[\s\S]*\}', ppt_content)
            if json_match:
                ppt_content = json_match.group(0)
            
            # 使用安全的 JSON 解析函数
            ppt_json = safe_json_loads(ppt_content)
            if ppt_json is None:
                log_error(f"PPT JSON 解析失败：内容为空\n原始内容前500字符：{ppt_content[:500]}")
                raise ValueError("AI 返回的课件 JSON 内容为空")
            
            result["ppt_json_raw"] = ppt_content  # 保存原始 JSON 文本用于调试
            theme = ppt_json.get("theme", {})
            slides = ppt_json.get("slides", [])
            
            if not slides or len(slides) == 0:
                raise ValueError("AI 返回的课件内容为空")
            
            # 数据验证和修复：确保每张幻灯片都有 content 字段
            validated_slides = []
            for slide in slides:
                # 确保必要字段存在
                if 'title' not in slide or not slide['title']:
                    slide['title'] = '无标题'
                
                # 确保 content 是列表且包含实际内容
                if 'content' not in slide or not isinstance(slide['content'], list) or len(slide['content']) == 0:
                    # 如果 content 为空，根据标题生成有意义的默认内容
                    title = slide.get('title', '')
                    if '封面' in title or 'cover' in title.lower():
                        # 封面页：添加欢迎语和主题
                        slide['content'] = [f"欢迎学习本课程", f"主题：{topic}", ""]
                    elif '目录' in title or 'content' in title.lower() or '大纲' in title:
                        # 目录页：添加基本结构
                        slide['content'] = ['一、课程介绍', '二、核心知识点', '三、实例讲解', '四、课堂小结']
                    elif '目标' in title or 'objective' in title.lower():
                        slide['content'] = ['知识目标：掌握核心概念', '能力目标：培养实践能力', '情感目标：激发学习兴趣']
                    elif '小结' in title or 'summary' in title.lower() or '总结' in title:
                        slide['content'] = ['回顾本课重点内容', '巩固所学知识', '布置课后作业']
                    elif '例题' in title or 'example' in title.lower() or '练习' in title:
                        slide['content'] = ['典型例题分析', '解题思路讲解', '常见错误提醒']
                    else:
                        # 其他内容页：添加占位内容
                        slide['content'] = [f'{title} 核心要点', '重要概念讲解', '实践应用示例']
                else:
                    # content 存在但可能包含空字符串，过滤掉纯空的条目
                    slide['content'] = [item for item in slide['content'] if item and item.strip()]
                    # 如果过滤后为空，添加默认内容
                    if not slide['content']:
                        slide['content'] = [f'{title} 内容要点']
                
                # 确保 decorations 是列表
                if 'decorations' not in slide or not isinstance(slide['decorations'], list):
                    slide['decorations'] = []
                
                # 确保 background 是字典
                if 'background' not in slide or not isinstance(slide['background'], dict):
                    slide['background'] = {'type': 'solid', 'colors': ['#ffffff']}
                
                # 确保 layout 字段存在
                if 'layout' not in slide or not slide['layout']:
                    slide['layout'] = 'title_content'
                
                validated_slides.append(slide)
            
            slides = validated_slides
            
            result["theme"] = theme
            result["slides"] = slides
            
            # Step 3: 生成配图（可选，默认禁用以提高速度）
            # 如需启用图片生成，请将 generate_images 参数设为 True
            generated_images = {}
            # if kwargs.get('generate_images', False):
            #     for i, slide in enumerate(slides):
            #         image_suggestion = slide.get('image_suggestion', '')
            #         if image_suggestion and image_suggestion.strip():
            #             try:
            #                 img_result = self.image_service.generate_image_from_suggestion(
            #                     suggestion=image_suggestion,
            #                     topic=topic,
            #                     subject=subject,
            #                     slide_index=i
            #                 )
            #                 if img_result.get('success'):
            #                     generated_images[i] = img_result
            #             except Exception:
            #                 pass  # 图片生成失败不影响主流程
            
            result["generated_images"] = generated_images
            
            # Step 4: 保存到数据库
            ppt_content_json = json.dumps({
                "theme": theme,
                "slides": slides
            }, ensure_ascii=False)
            
            courseware_id = db.add_courseware(
                title=topic,
                subject=subject,
                grade_level="",
                content=ppt_content_json,
                created_by=1
            )
            
            result["ppt_content"] = ppt_content_json
            result["courseware_id"] = courseware_id
            result["success"] = True
            
        except Exception as e:
            result["error"] = str(e)
            result["success"] = False
        
        return result
    
    def refine_courseware(self, feedback, topic, subject, slides, api_key, base_url):
        """基于反馈调整课件"""
        result = {
            "success": False,
            "slides": [],
            "theme": {},
            "error": None
        }
        
        try:
            client = self._get_client(api_key, base_url)
            
            # 构建调整提示词
            refine_prompt = CoursewarePrompts.get_refine_prompt(
                topic=topic,
                subject=subject,
                slides_json=json.dumps(slides[:5], ensure_ascii=False),
                feedback=feedback
            )
            
            response = client.chat.completions.create(
                model="moonshot-v1-8k",
                messages=[{"role": "user", "content": refine_prompt}],
                temperature=0.7,
                max_tokens=3000
            )
            
            # 解析响应
            response_content = clean_json_string(response.choices[0].message.content)
            if response_content.startswith('```'):
                first_newline = response_content.find('\n')
                if first_newline != -1:
                    response_content = response_content[first_newline:].strip()
                if response_content.endswith('```'):
                    response_content = response_content[:-3].strip()
            
            refined_json = json.loads(response_content)
            result["slides"] = refined_json.get("slides", slides)
            result["theme"] = refined_json.get("theme", {})
            result["success"] = True
            
        except Exception as e:
            result["error"] = str(e)
            result["success"] = False
        
        return result
    
    def load_history_courseware(self, courseware_id=None):
        """加载历史课件"""
        try:
            if courseware_id:
                return db.get_courseware_by_id(courseware_id)
            else:
                return db.get_all_courseware()
        except Exception as e:
            return []
    
    def analyze_uploaded_files(self, uploaded_files, api_key, base_url):
        """AI 解析上传的文件内容"""
        result = {"success": False, "analysis": "", "error": None}
        
        try:
            client = self._get_client(api_key, base_url)
            
            # 构建文件信息
            file_list = "\n".join([f"- {file.name} ({file.size} bytes)" for file in uploaded_files])
            
            prompt = DocumentAnalysisPrompts.get_courseware_analysis_prompt(file_list)
            
            response = client.chat.completions.create(
                model="moonshot-v1-8k",
                messages=[{"role": "user", "content": prompt}]
            )
            
            result["analysis"] = response.choices[0].message.content
            result["success"] = True
            
        except Exception as e:
            result["error"] = str(e)
            result["success"] = False
        
        return result
