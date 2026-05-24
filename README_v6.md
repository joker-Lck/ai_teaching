# AI 教学智能体 v6.0

> 基于 Next.js 14 + FastAPI 的前后端分离多模态 AI 教学辅助系统

## 🚀 快速启动

### Windows 用户（推荐）

直接双击运行 `启动v6.bat`，脚本会自动：
- ✅ 检测 Python 和 Node.js 环境
- ✅ 安装前后端依赖
- ✅ 启动后端 API 服务（端口 8000）
- ✅ 启动前端开发服务器（端口 3000）
- ✅ 自动打开浏览器访问应用

### 手动启动

#### 1. 环境准备

**必需软件**：
- Python 3.8+ （[下载](https://www.python.org/downloads/)）
- Node.js 18+ （[下载](https://nodejs.org/)）
- MySQL 8.0+ （数据库服务）

#### 2. 配置环境变量

```bash
# 复制配置文件模板
cp .env.example .env

# 编辑 .env 文件，填写以下信息：
# - KIMI_API_KEY: Kimi 大模型 API Key
# - 数据库连接信息（host, port, user, password）
```

#### 3. 初始化数据库

```bash
# 主业务数据库
python init_db.py

# 答疑专用数据库
python init_qa_db.py

# RAG 知识库（包含 93 本电子书）
python init_rag_db.py
```

#### 4. 启动服务

**方式一：使用启动脚本**
```bash
# Windows
启动v6.bat
```

**方式二：手动启动**

启动后端：
```bash
# 安装后端依赖
pip install -r backend/requirements.txt

# 启动 FastAPI 服务
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

启动前端：
```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

## 🌐 访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端应用 | http://localhost:3000 | 用户界面 |
| 后端 API | http://localhost:8000 | REST API 服务 |
| API 文档 | http://localhost:8000/api/docs | Swagger UI |
| ReDoc 文档 | http://localhost:8000/api/redoc | ReDoc 文档 |

## 🏗️ 技术架构

### 前端技术栈

```
┌─────────────────────────────────────────┐
│  Next.js 14 + React 18                  │
│  • TypeScript                            │
│  • Tailwind CSS 3 (样式框架)             │
│  • Framer Motion (动画库)                │
│  • Zustand (状态管理)                    │
│  • Recharts (数据可视化)                 │
│  • Socket.IO Client (实时通信)           │
│  • React Markdown (Markdown 渲染)        │
└───────────────┬─────────────────────────┘
                │ HTTP + WebSocket + SSE
```

### 后端技术栈

```
┌─────────────────────────────────────────┐
│  FastAPI + Uvicorn                      │
│  • Python 3.8+                          │
│  • MySQL 8.0 (三库分离架构)              │
│  • Kimi API (moonshot-v1-8k)            │
│  • RAG 向量检索                         │
│  • JWT 认证                             │
│  • SSE 流式输出                         │
│                                         │
│  复用模块：                              │
│  • services/ (业务逻辑层)                │
│  • data/ (数据访问层)                    │
│  • core/ (核心工具层)                    │
└─────────────────────────────────────────┘
```

### 数据库架构

- **主业务库** (`ai_teaching_assistant`)：用户、课件、学情分析
- **答疑专用库** (`ai_qa_database`)：问答记录、会话管理
- **RAG 知识库** (`ai_rag_knowledge`)：93 本电子书向量化存储

## 📋 核心功能

### 1. 智能答疑系统
- ✅ 双模式提问（文字 + 语音）
- ✅ RAG 优先检索策略
- ✅ 多轮对话支持
- ✅ SSE 流式输出
- ✅ 答案来源追溯

### 2. 课件自动生成
- ✅ AI 智能识别学科
- ✅ 双模式生成（快速/标准）
- ✅ 真实 PPT 预览
- ✅ 一键下载 PPTX
- ✅ 配套教案生成

### 3. 学情智能分析
- ✅ 单个学生分析报告
- ✅ 全班综合评估
- ✅ 多维度数据可视化
- ✅ AI 深度分析建议

### 4. 知识库管理
- ✅ 93 本预置电子书
- ✅ 多格式文档上传
- ✅ AI 智能解析
- ✅ 向量检索 + 全文搜索

### 5. 课堂互动工具
- ✅ 随机点名
- ✅ 互动记录管理
- ✅ 班级管理

## 🔧 开发指南

### 项目结构

```
项目根目录/
├── backend/                  # 后端 API 服务
│   ├── api/                 # API 路由
│   │   ├── auth.py         # 认证接口
│   │   ├── qa.py           # 答疑接口
│   │   ├── courseware.py   # 课件接口
│   │   ├── knowledge.py    # 知识库接口
│   │   ├── analysis.py     # 学情分析接口
│   │   └── ws.py           # WebSocket 接口
│   ├── schemas/            # Pydantic 模型
│   ├── middleware/         # 中间件
│   ├── main.py             # FastAPI 入口
│   └── requirements.txt    # 后端依赖
├── frontend/                # 前端应用
│   ├── app/                # Next.js 页面
│   ├── components/         # React 组件
│   ├── stores/             # Zustand 状态管理
│   ├── lib/                # 工具函数
│   └── package.json        # 前端依赖
├── services/               # 业务逻辑层（复用）
├── data/                   # 数据访问层（复用）
├── core/                   # 核心工具层（复用）
├── init_db.py             # 数据库初始化
├── init_qa_db.py          # 答疑库初始化
├── init_rag_db.py         # RAG 库初始化
└── .env.example           # 环境变量模板
```

### API 开发

所有 API 遵循 RESTful 规范，返回统一格式：

```json
{
  "success": true,
  "data": {...},
  "message": "操作成功"
}
```

错误响应：
```json
{
  "success": false,
  "error": "错误信息",
  "detail": "详细信息"
}
```

### 前端开发

- 使用 TypeScript 编写类型安全的代码
- 组件存放在 `frontend/components/`
- 页面存放在 `frontend/app/`
- 状态管理使用 Zustand（`frontend/stores/`）

## 📝 默认账号

首次使用后，可使用以下测试账号登录：

- **用户名**: admin
- **密码**: admin123

## ⚠️ 注意事项

1. **MySQL 服务**：确保 MySQL 服务已启动
2. **API Key**：必须在 `.env` 中配置有效的 Kimi API Key
3. **端口占用**：确保 3000 和 8000 端口未被占用
4. **首次运行**：首次运行需要安装依赖，可能需要几分钟
5. **数据库初始化**：使用前必须运行三个初始化脚本

## 🐛 常见问题

### Q1: 后端启动失败，提示 MySQL 连接错误

**解决方案**：
1. 检查 MySQL 服务是否启动
2. 确认 `.env` 中的数据库配置正确
3. 运行初始化脚本创建数据库

### Q2: 前端无法连接后端 API

**解决方案**：
1. 确认后端服务已启动（http://localhost:8000）
2. 检查浏览器控制台是否有 CORS 错误
3. 确认前端 `.env.local` 中的 API 地址配置正确

### Q3: 依赖安装失败

**解决方案**：
```bash
# 清除缓存后重新安装
pip cache purge
pip install -r backend/requirements.txt

# 前端
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### Q4: 如何停止服务？

**解决方案**：
- 关闭对应的命令行窗口即可停止服务
- 或使用 Ctrl+C 终止进程

## 📞 技术支持

如有问题，请查看：
- 项目详细方案：`项目详细方案.md`
- 日志文件：`logs/` 目录
- API 文档：http://localhost:8000/api/docs

---

*版本：v6.0 | 更新日期：2026年5月*
*架构：Next.js 14 + FastAPI + MySQL*
