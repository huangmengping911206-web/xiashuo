# 碎碎念平台 - 项目设计文档

> 本文档是碎碎念平台的架构设计总纲。所有方案设计前必须先阅读本文档，方案修改时同步更新本文档。

---

## 一、项目定位

碎碎念不是一个单一功能的项目，而是一个**持续生长的平台**。

```
当前：社交平台（推文、聊天、AI 对话）
  ↓ 扩展
未来：稿件审阅、上市公司价值分析、趣味数学科普、视频脚本分镜...
  ↓ 继续
更远：更多工作流、更多功能模块
```

**核心原则：碎碎念是地基，新功能是一层一层盖上去的楼。**

---

## 二、仓库策略

### 决策：单仓库

| 方案 | 结论 |
|------|------|
| 碎碎念独立仓库 + Agent 独立仓库 | ❌ 拒绝 |
| 所有项目合并到一个仓库 | ✅ 采用 |

### 原因

1. **代码复用**：碎碎念已有用户系统、数据库、AI 服务、部署环境、前端框架，后续功能直接复用
2. **依赖统一**：一份 requirements.txt，不用跨仓库管理依赖
3. **部署统一**：同一台服务器、同一套 systemd + Caddy
4. **开发效率**：直接 import 已有模块，不用重复建设

### 仓库地址

https://github.com/huangmengping911206-web/xiashuo.git

---

## 三、架构总览

```
┌─────────────────────────────────────────────────────┐
│                    碎碎念平台                         │
│                                                     │
│  功能层                                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ 推文/社交 │ │ AI 聊天   │ │ 项目文档  │           │
│  │ (已有)   │ │ (已有)    │ │ (待开发)  │           │
│  └──────────┘ └──────────┘ └──────────┘           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ 稿件审阅  │ │ 价值分析  │ │ 视频分镜  │           │
│  │ (规划中)  │ │ (规划中)  │ │ (规划中)  │           │
│  └──────────┘ └──────────┘ └──────────┘           │
│                                                     │
│  服务层                                             │
│  ┌─────────────────────────────────────────┐        │
│  │ AI 服务 │ 用户认证 │ 任务队列 │ 文档服务  │        │
│  └─────────────────────────────────────────┘        │
│                                                     │
│  基础设施层                                          │
│  ┌─────────────────────────────────────────┐        │
│  │ FastAPI │ SQLite │ Caddy │ systemd │ 前端 │       │
│  └─────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────┘
```

---

## 四、技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 后端框架 | FastAPI + uvicorn | Python 3.11，异步 |
| 数据库 | SQLite（WAL 模式） | 两个库：tweet.sqlite3 + images.sqlite3 |
| ORM | SQLAlchemy 2.0（async） | 异步会话 |
| 认证 | JWT（python-jose + bcrypt） | Bearer Token |
| 前端 | Alpine.js + 原生 CSS | 单页应用，无构建工具 |
| 反向代理 | Caddy | HTTP 80 端口，转发到 localhost:8000 |
| 进程管理 | systemd | myapp.service |
| 后台任务 | APScheduler + 自研 ConsumerWorker | 定时清理 + 消息队列 |
| AI | OpenAI API | 已有 ai_service.py 封装 |
| 缓存 | 自研内存缓存（MY_RedisClient） | 非真实 Redis |

---

## 五、服务器与部署

### 服务器信息

- **IP**：139.224.43.78
- **SSH**：root 用户
- **项目目录**：/home/admin/python_project
- **虚拟环境**：/home/admin/python_project/venv（Python 3.11）
- **systemd 服务**：myapp
- **启动命令**：`uvicorn app.main:app --host 127.0.0.1 --port 8000`（无 --reload）

### 部署架构

```
用户浏览器 → Caddy(:80) → uvicorn(:8000) → FastAPI
                                  ↓
                           SQLite 数据库
```

### 重启判断规则

| 改动类型 | 需要重启 | 操作 |
|----------|:---:|------|
| 前端 HTML/CSS/JS | ❌ | 直接覆盖，刷新即生效 |
| 后端 .py 文件 | ✅ | `systemctl restart myapp` |
| .env / app_config.yaml | ✅ | `systemctl restart myapp` |
| requirements.txt | ✅ | 先 `pip install`，再 restart |
| SQLite 数据库文件 | ❌ | 运行时直接读写 |
| Caddy 配置 | ✅ | `systemctl reload caddy` |
| systemd 服务文件 | ✅ | `systemctl daemon-reload && restart myapp` |

### 部署工作流（Claw 环境）

Claw 环境无法运行完整项目验证，所有代码修改必须推送到远程服务器验证。

```
1. 备份远程项目（paramiko SSH）
   ├─ 打包项目代码（排除 venv/*.log/sqlite-autoconf-*/旧zip/__MACOSX）
   ├─ 打包 venv（单独一份）
   ├─ 备份 systemd 服务文件 + Caddy 配置
   └─ 下载到本地

2. 本地修改代码（从备份解压到工作区）

3. 确认修改内容（diff 对比）

4. 部署到远程
   ├─ 备份远程要修改的文件（.bak）
   ├─ 上传修改后的文件
   └─ 验证远程文件内容

5. 按需重启服务

6. 验证生效（curl 模拟请求）
```

### 回退方案

**单文件回退**：
```bash
cp /home/admin/python_project/xxx.py.bak /home/admin/python_project/xxx.py
systemctl restart myapp
```

**整项目回退**：
```bash
tar -xzf backup_xxx/project.tar.gz -C /home/admin/python_project/
systemctl restart myapp
```

---

## 六、Claw 与碎碎念的协作模式

### 核心矛盾

Claw 是计算引擎（能跑 Agent、处理数据），但无法部署服务（你无法直接访问 Claw 的端口）。
碎碎念是展示层（你能通过浏览器访问），部署在你的服务器上。

### 解决方案：碎碎念作为 Claw 的输出窗口

```
Claw（计算）──API──→ 碎碎念（展示 + 反馈）
     ↑                        │
     └──── 拉取批注数据 ───────┘
```

**中间产物存数据库，不存文件。** 原因：

| 维度 | 存文件 | 存数据库（碎碎念） |
|------|:---:|:---:|
| 查看方式 | 下载文件，本地打开 | 浏览器直接看，手机也能看 |
| 版本对比 | 手动打开两个文件 | v1/v2 diff，改动高亮 |
| 反馈方式 | 口头描述 | 在段落旁批注 |
| 反馈精度 | 模糊 | 精确定位到段落/句子 |
| Agent 回读 | 需要你重新描述 | 直接调 API 拉取结构化数据 |
| 进度追踪 | 靠记忆 | 数据库记录状态 |

---

## 七、项目文档模块设计（待开发）

### 数据模型

```sql
-- 项目
projects (id, user_id, name, type, status, created_at)

-- 文档（一个项目下多个文档）
project_documents (id, project_id, title, doc_type, content, version, created_at)
  -- doc_type: research / draft / review / report / ...

-- 批注（对文档的具体段落进行批注）
document_comments (id, document_id, user_id, content,
  position_start, position_end, status, created_at)
  -- status: pending / resolved

-- 版本记录
document_versions (id, document_id, version, content, diff_from_prev, created_at)
```

### API 设计

```
# 项目管理
POST   /api/v2/projects                    # 创建项目
GET    /api/v2/projects                    # 项目列表
GET    /api/v2/projects/{id}               # 项目详情

# 文档管理
POST   /api/v2/projects/{id}/documents     # 创建/更新文档
GET    /api/v2/projects/{id}/documents     # 文档列表
GET    /api/v2/documents/{doc_id}/versions # 版本历史
GET    /api/v2/documents/{doc_id}/diff?v1=1&v2=2  # 版本对比

# 批注
POST   /api/v2/documents/{doc_id}/comments # 添加批注
GET    /api/v2/documents/{doc_id}/comments # 获取批注
PUT    /api/v2/documents/{doc_id}/comments/{cid}  # 更新批注状态
```

### Claw 工作流闭环

```
1. Claw 创建项目     → POST /api/v2/projects
2. Claw 推送研究资料  → POST /api/v2/projects/{id}/documents
3. Claw 推送初稿     → POST /api/v2/projects/{id}/documents
4. 你打开网页查看    → 浏览器
5. 你批注反馈       → POST /api/v2/documents/{doc_id}/comments
6. Claw 拉取批注    → GET /api/v2/documents/{doc_id}/comments?status=pending
7. Claw 根据批注修改 → 推送 v2
8. 循环直到定稿
```

### 开发优先级

```
第一阶段（核心闭环）：
  数据模型 + API + 前端（项目列表、文档查看、批注）
  → 目标：Claw 能推送，你能看到并批注

第二阶段（体验优化）：
  版本对比（diff）、Markdown 渲染、批注高亮定位

第三阶段（扩展）：
  项目模板、状态流转、导出 Word/PDF
```

---

## 八、已有可复用模块

| 模块 | 路径 | 复用价值 |
|------|------|----------|
| AI 服务封装 | `app/services/ai_service.py` | 所有 Agent 功能共用 |
| AI 模型配置 | `app/services/ai_models.py` | 模型管理 |
| AI 人设 | `app/services/ai_personas.py` | 不同场景的人设切换 |
| 用户认证 | `app/core/security.py` + `app/api/v2/endpoints/user.py` | 需要用户隔离的功能 |
| 数据库 ORM | `app/database/` | 所有新功能的数据持久化 |
| 后台任务 | `app/worker/`（ConsumerWorker + APScheduler） | 定时任务、异步处理 |
| 前端框架 | `frontend/`（Alpine.js） | 新功能的前端 UI |
| 中间件 | `app/middleware/custom_middleware.py` | 请求处理、缓存控制 |

---

## 九、Prompt 模板管理

`prompts/` 目录存放所有 Agent 的 prompt 模板，作为代码的一部分纳入版本管理。

```
prompts/
├── search.md           # 搜索 Agent
├── review.md           # 审阅 Agent
├── writing.md          # 写稿 Agent
├── value_analysis.md   # 价值分析 Agent
└── video_storyboard.md # 视频分镜 Agent
```

---

## 十、环境注意事项

1. **Claw 环境变量冲突**：系统预设 `DATABASE_URL=file:/home/z/my-project/db/custom.db`，会覆盖项目 .env。本地启动时需要 unset 或显式覆盖
2. **Claw 无 SSH 命令**：使用 Python paramiko 库连接远程服务器
3. **生产环境无 --reload**：修改后端代码必须手动 `systemctl restart myapp`
4. **前端无缓存层**：HTML/CSS/JS 修改后立即生效
5. **备份排除项**：venv、*.log、*.log.*、sqlite-autoconf-*、myapp_0310.zip、__MACOSX

---

## 变更记录

| 日期 | 变更内容 |
|------|----------|
| 2026-04-18 | 初版：确定单仓库策略、平台化架构、Claw 协作模式、项目文档模块设计 |
