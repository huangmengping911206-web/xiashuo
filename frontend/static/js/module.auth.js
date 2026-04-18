// static/js/module.auth.js

/**
 * 认证模块
 * 处理用户登录、注册、登出及会话状态管理
 */
window.AppAuth = {

    // ========== 状态定义 ==========

    // 登录表单数据
    loginForm: {
        user_name: '',
        password: ''
    },

    // 注册表单数据
    registerForm: {
        user_name: '',
        email: '',
        phone: '',
        password: ''
    },

    // ========== 业务方法 ==========

    /**
     * 处理用户登录
     */
    async handleLogin() {
        // 防止重复提交
        if (this.loading) return;

        // 表单验证
        if (!this.loginForm.user_name || !this.loginForm.password) {
            this.showToast('请填写用户名和密码', 'error');
            return;
        }

        this.loading = true;

        try {
            // 1. 调用登录接口
            const res = await this.api('/v2/users/login', 'POST', {
                user_name: this.loginForm.user_name,
                password: this.loginForm.password
            });

            // 2. 更新全局状态
            this.token = res.access_token;
            this.user = {
                id: res.user_id,
                user_name: res.user_name
            };

            // 3. 持久化存储到 LocalStorage
            localStorage.setItem('token', this.token);
            localStorage.setItem('user', JSON.stringify(this.user));

            // 4. 更新UI提示与页面跳转
            this.showToast('登录成功！', 'success');
            this.page = 'home';
            this.pageHistory = ['home']; // 重置页面历史

            // 5. 加载初始数据
            this.loadTweets();
            this.loadUserInfo();

            // 6. 重置表单
            this.loginForm = { user_name: '', password: '' };

        } catch (error) {
            this.showToast('登录失败：' + error.message, 'error');
        } finally {
            this.loading = false;
        }
    },

    /**
     * 处理用户注册
     */
    async handleRegister() {
        // 防止重复提交
        if (this.loading) return;

        // 表单验证
        if (!this.registerForm.user_name || !this.registerForm.email || !this.registerForm.password) {
            this.showToast('请填写必填项', 'error');
            return;
        }

        this.loading = true;

        try {
            // 调用注册接口
            await this.api('/v2/users/create', 'POST', {
                user_name: this.registerForm.user_name,
                email: this.registerForm.email,
                phone: this.registerForm.phone || '', // 手机号选填
                password: this.registerForm.password
            });

            // 注册成功提示并跳转登录页
            this.showToast('注册成功，请登录！', 'success');
            this.page = 'login';

            // 重置表单
            this.registerForm = { user_name: '', email: '', phone: '', password: '' };

        } catch (error) {
            this.showToast('注册失败：' + error.message, 'error');
        } finally {
            this.loading = false;
        }
    },

    /**
     * 处理用户登出
     */
    async handleLogout() {
        // 确认对话框
        if (!confirm('确定要退出登录吗？')) return;

        try {
            // 尝试调用服务端登出接口 (忽略错误，即使失败也继续客户端登出流程)
            await this.api('/v2/users/logout', 'GET');
        } catch (error) {
            console.error('Logout API error:', error);
        }

        // 1. 清除客户端状态
        this.token = null;
        this.user = {};
        this.tweets = [];      // 清空推文缓存
        this.myTweets = [];    // 清空个人推文
        this.usersCache = {};  // 清空用户信息缓存

        // 2. 清除本地存储
        localStorage.removeItem('token');
        localStorage.removeItem('user');

        // 3. 重置页面状态
        this.page = 'login';
        this.pageHistory = ['login'];

        this.showToast('已退出登录', 'info');
    }
};
