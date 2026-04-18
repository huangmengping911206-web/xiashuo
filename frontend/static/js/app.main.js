// static/js/app.main.js

/**
 * 应用程序主入口
 *
 * 这是一个 Alpine.js 组件工厂函数。
 * 它定义了核心状态、生命周期钩子，并通过对象展开运算符 (...)
 * 将各个功能模块（认证、推文、用户、工具）合并到当前组件实例中。
 */
function App() {
    return {
        // ========== 核心状态定义 ==========

        page: 'login',          // 当前页面标识 (login, home, profile, detail 等)
        loading: false,         // 全局加载状态

        // 认证相关状态 (从 LocalStorage 恢复)
        token: localStorage.getItem('token') || null,
        user: JSON.parse(localStorage.getItem('user') || '{}'),

        // 导航与缓存
        pageHistory: ['home'], // 页面历史栈，用于实现 "返回" 功能
        usersCache: {},         // 用户信息全局缓存，减少重复请求

        // UI 交互状态
        toast: {
            show: false,        // 是否显示提示
            message: '',        // 提示内容
            type: 'info'        // 提示类型
        },

        // ========== 混入模块 (关键步骤) ==========
        // 使用展开运算符将分散在各个文件中的功能合并到当前对象
        // 注意：script 标签需按依赖顺序加载

        ...window.AppUtils,     // 工具函数 (纯函数)
        ...window.AppAuth,      // 认证模块 (登录/注册/登出)
        ...window.AppTweet,     // 推文模块 (列表/详情/发布)
        ...window.AppUser,      // 用户模块 (个人中心/缓存)
        ...window.AppChat, // 聊天模块


        // ========== 生命周期钩子 ==========

        /**
         * Alpine.js 初始化钩子
         * 组件加载时自动执行
         */
        init() {
            console.log('[App] Initializing');

            // 从 localStorage 恢复登录状态
            const savedToken = localStorage.getItem('token');
            const savedUser = localStorage.getItem('user');
            if (savedToken) this.token = savedToken;
            if (savedUser) this.user = JSON.parse(savedUser);

            // 会话恢复逻辑：如果存在 token 且有用户 ID，视为已登录
            if (this.token && this.user && this.user.id) {
                this.page = 'home';
                
                // 确保 loadTweets 方法存在
                if (typeof this.loadTweets === 'function') {
                    this.loadTweets();      // 加载首页推文
                } else {
                    console.error('loadTweets 方法不存在，请检查 module.tweet.js 是否正确加载');
                }
                this.loadUserInfo();    // 刷新用户信息


                // 【修复】安全调用 initChat
                if (typeof this.initChat === 'function') {
                    this.initChat();
                } else {
                    console.error('initChat 方法未找到，请检查 module.chat.js 是否正确加载');
                }

            }

            // 启动全局滚动监听 (用于无限滚动加载)
            this.setupScrollListener();
        },

//        this.socket.onopen = () => {
//            console.log('[WS] 连接成功');
//            this.isConnected = true;
//            // 【必须有这一行】通知 Chat 模块连接好了
//            window.dispatchEvent(new CustomEvent('ws-connected'));
//        };

        // 代理调用
        connectWs() { window.ChatModule.connectWs(); },
        disconnectWs() { window.ChatModule.disconnectWs(); },


        // ========== 核心方法 ==========

        /**
         * API 请求统一封装
         * @param {string} endpoint - 接口地址 (如 '/v1/users/login')
         * @param {string} method - 请求方法 (GET, POST, PUT, DELETE)
         * @param {Object|null} data - 请求体数据
         * @param {boolean} isFormData - 是否为文件上传
         */
        async api(endpoint, method = 'GET', data = null, isFormData = false) {
            const url = '/api' + endpoint;
            const opts = { method, headers: {} };

            // 1. 设置 Content-Type
            // 如果不是 FormData，默认为 JSON；如果是 FormData，让浏览器自动设置 boundary
            if (!isFormData) {
                opts.headers['Content-Type'] = 'application/json';
            }

            // 2. 注入认证 Token
            if (this.token) {
                opts.headers['Authorization'] = 'Bearer ' + this.token;
                // 同时设置 Cookie（用于某些需要 Cookie 的 API）
                document.cookie = `access_token=${this.token}; path=/; max-age=86400`;
            }

            // 3. 处理请求体
            if (data) {
                opts.body = isFormData ? data : JSON.stringify(data);
            }

            console.log('[API]', method, url);

            try {
                // 4. 发起请求
                const res = await fetch(url, opts);

                // 5. 错误处理
                if (!res.ok) {
                    const err = await res.json().catch(() => ({ detail: '请求失败' }));
                    throw new Error(err.detail || `HTTP ${res.status}`);
                }

                // 6. 解析响应
                const text = await res.text();
                return text ? JSON.parse(text) : null;

            } catch (error) {
                console.error('[API Error]', error);
                throw error; // 将错误抛出给调用方处理
            }
        },

        /**
         * 显示全局 Toast 提示
         * @param {string} message - 提示文本
         * @param {string} type - 类型
         */
        showToast(message, type = 'info') {
            this.toast = { show: true, message, type };
            // 3秒后自动隐藏
            setTimeout(() => {
                this.toast.show = false;
            }, 3000);
        },

        /**
         * 返回上一页逻辑
         */
        goBack() {
            if (this.pageHistory.length > 1) {
                this.pageHistory.pop(); // 移除当前页
                this.page = this.pageHistory[this.pageHistory.length - 1]; // 回到上一页
            } else {
                // 如果历史栈为空，默认回到首页
                this.page = 'home';
            }
        },

        /**
         * 设置滚动监听器 (无限滚动实现)
         */
        setupScrollListener() {
            let scrollTimeout;

            window.addEventListener('scroll', () => {
                // 防抖处理：滚动停止 200ms 后才执行检测
                clearTimeout(scrollTimeout);
                scrollTimeout = setTimeout(() => {
                    const { scrollTop, scrollHeight, clientHeight } = document.documentElement;

                    // 距离底部小于 300px 时触发加载
                    if (scrollHeight - scrollTop - clientHeight < 300) {
                        // 首页：加载更多推文
                        if (this.page === 'home') {
                            this.loadTweets();
                        }
                        // 个人页面：加载更多我的推文
                        else if (this.page === 'profile' && typeof this.loadMyTweets === 'function') {
                            this.loadMyTweets();
                        }
                    }
                }, 200);
            });
        },

        // ========== 导航辅助方法 ==========

        /**
         * 跳转到首页
         */
        navigateToHome() {
            console.log('[App] navigateToHome 调用');
            console.log('[App] this.refreshTweets:', typeof this.refreshTweets);
            console.log('[App] window.AppTweet:', typeof window.AppTweet);
            console.log('[App] window.AppTweet.refreshTweets:', typeof window.AppTweet?.refreshTweets);
            
            if (this.page === 'home') {
                if (typeof this.refreshTweets === 'function') {
                    this.refreshTweets(); // 如果已在首页，则刷新数据
                } else {
                    console.error('refreshTweets 方法不存在！');
                }
            } else {
                this.page = 'home';
                this.pageHistory.push('home');
            }
        },

        /**
         * 跳转到个人主页
         */
        navigateToProfile() {
            if (this.page === 'profile') {
                this.loadMyProfile(); // 如果已在个人页，则刷新数据
            } else {
                this.page = 'profile';
                this.pageHistory.push('profile');
                this.loadMyProfile();
            }
        },

        // 【新增】导航到聊天页
        navigateToChat() {
            // 如果已经在聊天页，刷新列表
            if (this.page === 'chat') {
                this.loadConversations();
            } else {
                // 切换页面并加载
                this.page = 'chat';
                this.pageHistory.push('chat');
                this.loadConversations();
            }
        },

        /**
         * 自动登录 - 使用保存的账号凭证
         */
        async autoLogin() {
            if (this.token) return true;
            
            const savedToken = localStorage.getItem('token');
            if (savedToken) {
                this.token = savedToken;
                const savedUser = localStorage.getItem('user');
                if (savedUser) this.user = JSON.parse(savedUser);
                return true;
            }
            
            try {
                const res = await this.api('/v2/users/login', 'POST', {
                    user_name: 'OpenClaw',
                    password: 'test123456'
                });
                this.token = res.access_token;
                this.user = { id: res.user_id, user_name: res.user_name };
                localStorage.setItem('token', this.token);
                localStorage.setItem('user', JSON.stringify(this.user));
                console.log('[AutoLogin] 登录成功:', this.user.user_name);
                return true;
            } catch (error) {
                console.error('[AutoLogin] 登录失败:', error);
                return false;
            }
        }
    };
}
