# AI 教学智能体 v6.0

> 基于 **Next.js + FastAPI + Kimi AI** 的多模态 AI 教学平台

## 架构

```
┌─────────────────────────────────────────────┐
│          Next.js 14 + React 18 前端          │
│  Tailwind CSS · Framer Motion · Zustand     │
│         localhost:3000                       │
├─────────────────────────────────────────────┤
│          FastAPI 后端 API 层                  │
│  SSE 流式 · WebSocket · JWT 认证             │
│         localhost:8000                       │
├─────────────────────────────────────────────┤
│          业务服务层 (services/)               │
│  答疑 · 课件 · 知识库 · 学情分析 · 动画      │
├─────────────────────────────────────────────┤
│          数据层 (data/)                       │
│  MySQL × 3 · RAG 向量检索 · 文档解析         │
└─────────────────────────────────────────────┘
```

## 功能模块

| 模块 | 说明 |
|------|------|
| 🎓 智能答疑 | SSE 流式对话、多场景切换、RAG 知识库优先 |
| 📊 课件生成 | 4 步向导、学科自适应策略、PPT 预览/下载 |
| 📈 学情分析 | 7 维度分析、AI 深度解读、图表可视化 |
| 📚 知识库管理 | 93 本教材 RAG、文档上传、向量检索 |
| ✨ 动画系统 | 教学动画组件库、粒子背景、玻璃拟态 UI |

## 快速启动

### 前置要求
- Python 3.8+
- Node.js 18+
- MySQL 8.0

### 一键启动
```bash
双击 启动v6.bat
```

### 手动启动

**1. 配置环境变量**
```bash
copy .env.example .env
# 编辑 .env 填入 KIMI_API_KEY 和数据库配置
```

**2. 安装依赖**
```bash
# 后端
pip install -r backend/requirements.txt

# 前端
cd frontend && npm install
```

**3. 初始化数据库**
```bash
python init_db.py
python init_qa_db.py
python init_rag_db.py
python init_admin.py
```

**4. 启动服务**
```bash
# 后端 (端口 8000)
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# 前端 (端口 3000)
cd frontend && npm run dev
```

**5. 访问**
- 前端：http://localhost:3000
- API 文档：http://localhost:8000/docs
- 默认管理员：admin / admin123

## 技术栈

**前端**: Next.js 14 · React 18 · TypeScript · Tailwind CSS · Framer Motion · Zustand · Recharts

**后端**: FastAPI · Pydantic · PyJWT · SSE · WebSocket

**AI**: Kimi (Moonshot) · RAG 向量检索 · 学科自适应提示词

**数据**: MySQL 8.0 × 3 · SHA-256+Salt 认证 · RBAC 四角色权限

## 项目结构

```
├── backend/              # FastAPI 后端 API 层
│   ├── api/              # 路由模块 (auth, qa, courseware, knowledge, analysis, ws)
│   ├── schemas/          # Pydantic 数据模型
│   ├── main.py           # 入口文件
│   ├── dependencies.py   # 认证与依赖注入
│   └── requirements.txt
├── frontend/             # Next.js 前端
│   ├── app/              # 页面路由
│   ├── components/       # React 组件
│   ├── stores/           # Zustand 状态管理
│   ├── lib/              # API 客户端
│   └── styles/           # 全局样式
├── services/             # 业务服务层
├── data/                 # 数据访问层
├── core/                 # 核心模块
└── init_*.py             # 数据库初始化脚本
```

## 版本历史

- **v6.0** — 架构重构：Streamlit → Next.js + FastAPI，新增 SSE 流式、WebSocket、增强动画
- **v5.0** — Streamlit 多模态版本
