# 虾说（Xiashuo）

> 社交平台 + AI 工作流平台，持续生长中。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI + Uvicorn |
| 数据库 | SQLite（SQLAlchemy 异步 ORM） |
| 认证 | JWT（python-jose + bcrypt） |
| 前端 | 原生 HTML + Alpine.js + 自定义 CSS |
| AI | OpenAI API |
| 任务调度 | APScheduler |
| 消息队列 | 自研 ConsumerWorker |
| 反向代理 | Caddy |
| 进程管理 | systemd |

## 项目结构

```
xiashuo/
├── app/                          # 后端
│   ├── api/v2/endpoints/         #   API 接口
│   ├── services/                 #   业务逻辑（AI 服务、各功能模块）
│   ├── database/                 #   数据模型 + ORM
│   ├── worker/                   #   后台任务（队列 + 定时调度）
│   ├── core/                     #   核心模块（配置、安全、日志）
│   ├── middleware/               #   中间件
│   └── main.py                   #   入口
├── frontend/                     # 前端
│   ├── index.html                #   主页面
│   └── static/                   #   JS / CSS
├── config/                       # 配置文件
├── scripts/                      # 运维脚本
├── prompts/                      # Prompt 模板库（待创建）
├── tests/                        # 测试
├── requirements.txt              # Python 依赖
├── PROJECT_DESIGN.md             # 架构设计文档（必读）
└── .gitignore
```

## 已有功能

- 用户注册 / 登录 / JWT 认证
- 发推文、点赞、评论
- 图片上传
- 私聊 / 群聊（WebSocket）
- AI 聊天（OpenAI）
- 后台任务队列 + 定时清理
- 监控面板

## 规划中

- 项目文档模块（Agent 中间产物管理 + 在线批注）
- 稿件审阅工作流
- 上市公司价值分析
- 趣味数学科普
- 视频脚本分镜

## 部署

```bash
# 启动
systemctl start myapp

# 重启（修改后端代码后）
systemctl restart myapp

# 查看状态
systemctl status myapp

# 查看日志
tail -f /home/admin/python_project/app.log
```

## 文档

- [PROJECT_DESIGN.md](./PROJECT_DESIGN.md) — 架构设计总纲，方案设计前必读
- [ARCHITECTURE_AND_LIKE_FEATURE.md](./ARCHITECTURE_AND_LIKE_FEATURE.md) — 架构与点赞功能设计
- [VIDEO_FEATURE_DESIGN.md](./VIDEO_FEATURE_DESIGN.md) — 视频功能设计
