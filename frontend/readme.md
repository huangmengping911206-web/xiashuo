
static/js/
├── utils.js           # 1. 工具函数 (无状态)
├── module.auth.js     # 2. 认证模块
├── module.tweet.js    # 3. 推文模块
├── module.user.js     # 4. 用户模块
└── app.main.js        # 5. 主入口 (组合器)


第一部分：JS 逻辑分析
在拆分代码之前，我们需要先理清 app.js 的整体架构和运行逻辑。这个文件是一个典型的 Alpine.js 单文件组件，它承载了整个前端应用的生命周期。
1. 核心架构
状态机模式: 变量 page 充当路由控制器，通过 pageHistory 实现简单的页面栈管理（类似 App 的导航跳转和返回）。
持久化登录: 初始化时读取 localStorage 中的 token 和 user，实现“刷新不退出”的效果。
API 封装: 封装了 fetch，统一处理 Token 注入、JSON 序列化和错误捕获，这是所有业务逻辑的基石。
2. 业务模块划分
代码逻辑清晰地分为四个主要板块：
认证模块: 处理登录 (handleLogin)、注册 (handleRegister)、登出 (handleLogout)。
推文模块: 核心业务，包含列表加载 (loadTweets)、详情查看 (viewTweetDetail)、发布 (publishTweet)、评论管理。
用户模块: 个人资料编辑 (saveName, saveBio)、头像上传、用户信息缓存机制 (usersCache，用于避免重复请求用户信息)。
工具模块: 纯函数集合，如时间格式化 (formatTime)、文本截断 (truncateText)，不依赖组件状态。
3. 性能优化点
用户信息缓存: usersCache 对象的设计非常关键。推文列表只返回 creater_id，前端通过批量获取并缓存用户详情，避免了列表渲染时发起大量重复的 HTTP 请求。
滚动加载: setupScrollListener 实现了无限滚动加载推文。
第二部分：拆分后的完整代码
基于上述分析，我们将代码拆分为 5个独立文件。这种拆分方式利用 JavaScript 的对象展开特性，既保持了代码整洁，又避免了复杂的打包工具依赖。

static/
├── js/
│   ├── utils.js              # 工具函数
│   ├── module.auth.js        # 认证模块
│   ├── module.tweet.js       # 推文模块
│   ├── module.user.js        # 用户模块
│   ├── module.chat.js        # 【新增】聊天业务逻辑
│   ├── module.ws.js          # 【新增】WebSocket管理
│   ├── templates/
│   │   └── chat.template.js  # 【新增】聊天页面HTML模板
│   └── app.main.js           # 主入口
└── index.html                # 主页面（变得非常简洁）


