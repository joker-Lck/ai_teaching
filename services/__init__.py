"""
Services 包初始化
封装所有核心业务逻辑，实现前后端解耦
"""
from services.qa_service import QAService
from services.courseware_service import CoursewareService
from services.knowledge_service import KnowledgeService
from services.analysis_service import AnalysisService
from services.image_service import ImageService
from services.animation_service import AnimationService
from services.auth_service import AuthService, auth_service
