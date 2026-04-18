function App() {
    return {
        // ========== 状态 ==========
        page: 'login',
        loading: false,
        token: localStorage.getItem('token') || null,
        user: JSON.parse(localStorage.getItem('user') || '{}'),
        pageHistory: ['login'],
        // 用户信息缓存 { id: { user_name, avatar_id } }
        usersCache: {},

        // 表单
        loginForm: { user_name: '', password: '' },
        registerForm: { user_name: '', email: '', phone: '', password: '' },

        // 搜索
        showSearch: false,
        searchKeyword: '',

        // 推文列表
        tweets: [],
        tweetsLoading: false,
        tweetsPage: 0,
        hasMoreTweets: true,
        expandedTweets: {},

        // 推文详情
        currentTweet: {},
        comments: [],
        commentsLoading: false,
        newComment: '',
        commentSubmitting: false,
        showDeleteTweetModal: false,

        // 发布推文
        composeContent: '',
        composeImages: [],
        composeImageIds: [],
        composeSubmitting: false,
        showTagInput: false,
        composeTags: [],
        tagInputValue: '',

        // 个人主页
        myTweets: [],
        editingName: false,
        editingBio: false,
        editNameValue: '',
        editBioValue: '',

        // 图片预览
        previewImageId: null,

        // Toast
        toast: { show: false, message: '', type: 'info' },

        // ========== 初始化 ==========
        init() {
            console.log('[App] Initializing');

            if (this.token && this.user.id) {
                this.page = 'home';
                this.loadTweets();
                this.loadUserInfo();
            }

            this.setupScrollListener();
        },

        // ========== API 封装 ==========
        async api(endpoint, method = 'GET', data = null, isFormData = false) {
            const url = '/api' + endpoint;
            const opts = {
                method,
                headers: {}
            };

            if (!isFormData) {
                opts.headers['Content-Type'] = 'application/json';
            }

            if (this.token) {
                opts.headers['Authorization'] = 'Bearer ' + this.token;
            }

            if (data) {
                if (isFormData) {
                    opts.body = data;
                } else {
                    opts.body = JSON.stringify(data);
                }
            }

            console.log('[API]', method, url);

            try {
                const res = await fetch(url, opts);

                if (!res.ok) {
                    const err = await res.json().catch(() => ({ detail: '请求失败' }));
                    throw new Error(err.detail || `HTTP ${res.status}`);
                }

                const text = await res.text();
                if (!text) return null;
                return JSON.parse(text);
            } catch (error) {
                console.error('[API Error]', error);
                throw error;
            }
        },

        // ========== 认证 ==========
        async handleLogin() {
            if (this.loading) return;

            if (!this.loginForm.user_name || !this.loginForm.password) {
                this.showToast('请填写用户名和密码', 'error');
                return;
            }

            this.loading = true;

            try {
                const res = await this.api('/v1/users/login', 'POST', {
                    user_name: this.loginForm.user_name,
                    password: this.loginForm.password
                });

                this.token = res.access_token;
                this.user = {
                    id: res.user_id,
                    user_name: res.user_name
                };

                localStorage.setItem('token', this.token);
                localStorage.setItem('user', JSON.stringify(this.user));

                this.showToast('登录成功！', 'success');
                this.page = 'home';
                this.pageHistory = ['home'];

                this.loadTweets();
                this.loadUserInfo();

                this.loginForm = { user_name: '', password: '' };
            } catch (error) {
                this.showToast('登录失败：' + error.message, 'error');
            } finally {
                this.loading = false;
            }
        },

        async handleRegister() {
            if (this.loading) return;

            if (!this.registerForm.user_name || !this.registerForm.email || !this.registerForm.password) {
                this.showToast('请填写必填项', 'error');
                return;
            }

            this.loading = true;

            try {
                await this.api('/v1/users/create', 'POST', {
                    user_name: this.registerForm.user_name,
                    email: this.registerForm.email,
                    phone: this.registerForm.phone || '',
                    password: this.registerForm.password
                });

                this.showToast('注册成功，请登录！', 'success');
                this.page = 'login';

                this.registerForm = { user_name: '', email: '', phone: '', password: '' };
            } catch (error) {
                this.showToast('注册失败：' + error.message, 'error');
            } finally {
                this.loading = false;
            }
        },

        async handleLogout() {
            if (!confirm('确定要退出登录吗？')) return;

            try {
                await this.api('/v2/users/logout', 'GET');
            } catch (error) {
                console.error('Logout API error:', error);
            }

            this.token = null;
            this.user = {};
            this.tweets = [];
            this.myTweets = [];
            this.usersCache = {}; // 清空用户缓存
            this.page = 'login';
            this.pageHistory = ['login'];
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            this.showToast('已退出登录', 'info');
        },

        async loadUserInfo() {
            if (!this.user.id) return;

            try {
                const info = await this.api(`/v2/users/get/${this.user.id}`);
                this.user = { ...this.user, ...info };
                localStorage.setItem('user', JSON.stringify(this.user));
            } catch (error) {
                console.error('[Load User Info Error]', error);
            }
        },

        // ========== 用户信息获取逻辑 ==========
        // 批量获取用户信息并缓存
        async fetchUsersInfo(userIds) {
            const uniqueIds = [...new Set(userIds)].filter(id => id && !this.usersCache[id]);
            if (uniqueIds.length === 0) return;

            // 并行请求用户信息
            const promises = uniqueIds.map(id =>
                this.api(`/v2/users/get/${id}`)
                    .then(userInfo => {
                        if (userInfo) {
                            // 存入缓存
                            this.usersCache[id] = {
                                user_name: userInfo.user_name,
                                avatar_id: userInfo.avatar_id
                            };
                        }
                    })
                    .catch(err => console.error(`Failed to fetch user ${id}`, err))
            );

            await Promise.all(promises);
        },

        // 获取用户显示名称
        getUserDisplayName(tweet) {
            // 优先使用缓存中的名称
            if (tweet.creater_id && this.usersCache[tweet.creater_id]) {
                return this.usersCache[tweet.creater_id].user_name;
            }
            // 其次使用推文自带的名称（如果有）
            if (tweet.user_name) return tweet.user_name;
            return '加载中...';
        },

        // 获取用户头像
        getUserAvatar(userId) {
            if (!userId) return this.getDefaultAvatar();
            // 优先使用缓存
            if (this.usersCache[userId] && this.usersCache[userId].avatar_id) {
                return '/api/v2/image/' + this.usersCache[userId].avatar_id;
            }
            return this.getDefaultAvatar();
        },

        getDefaultAvatar() {
            return 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"%3E%3Ccircle cx="24" cy="24" r="24" fill="%2387CEEB"/%3E%3Ctext x="24" y="30" text-anchor="middle" font-size="20" fill="white"%3E👤%3C/text%3E%3C/svg%3E';
        },

        // ========== 推文列表 ==========
        async loadTweets() {
            if (this.tweetsLoading || !this.hasMoreTweets) return;

            this.tweetsLoading = true;

            try {
                const data = await this.api(`/v2/tweet/list?skip=${this.tweetsPage * 10}&limit=10&order=desc`);

                if (!data || data.length === 0) {
                    this.hasMoreTweets = false;
                } else {
                    this.tweets.push(...data);

                    // 关键步骤：收集所有创建者ID并获取信息
                    const creatorIds = data.map(t => t.creater_id);
                    this.fetchUsersInfo(creatorIds);

                    if (data.length < 10) {
                        this.hasMoreTweets = false;
                    } else {
                        this.tweetsPage++;
                    }
                }
            } catch (error) {
                this.showToast('加载失败', 'error');
                this.hasMoreTweets = false;
            } finally {
                this.tweetsLoading = false;
            }
        },

        refreshTweets() {
            this.tweets = [];
            this.tweetsPage = 0;
            this.hasMoreTweets = true;
            this.expandedTweets = {};
            this.loadTweets();
        },

        async searchTweets() {
            if (!this.searchKeyword.trim()) {
                this.refreshTweets();
                return;
            }

            this.tweets = [];
            this.tweetsLoading = true;
            this.hasMoreTweets = false;

            try {
                const res = await this.api(`/v2/tweet/search/?keyword=${encodeURIComponent(this.searchKeyword)}&skip=0&limit=50`);
                this.tweets = res.results || [];

                // 搜索结果也需要获取用户信息
                if (this.tweets.length > 0) {
                     const creatorIds = this.tweets.map(t => t.creater_id);
                     this.fetchUsersInfo(creatorIds);
                }
            } catch (error) {
                this.showToast('搜索失败', 'error');
            } finally {
                this.tweetsLoading = false;
            }
        },

        setupScrollListener() {
            let scrollTimeout;
            window.addEventListener('scroll', () => {
                if (this.page !== 'home') return;

                clearTimeout(scrollTimeout);
                scrollTimeout = setTimeout(() => {
                    const scrollTop = window.scrollY;
                    const scrollHeight = document.documentElement.scrollHeight;
                    const clientHeight = window.innerHeight;

                    if (scrollHeight - scrollTop - clientHeight < 300) {
                        this.loadTweets();
                    }
                }, 200);
            });
        },

        // ========== 导航刷新 ==========
        navigateToHome() {
            if (this.page === 'home') {
                this.refreshTweets();
            } else {
                this.page = 'home';
                this.pageHistory.push('home');
            }
        },

        navigateToProfile() {
            if (this.page === 'profile') {
                this.loadMyProfile();
            } else {
                this.page = 'profile';
                this.pageHistory.push('profile');
                this.loadMyProfile();
            }
        },

        // ========== 推文详情 ==========
        async viewTweetDetail(tweetId) {
            this.page = 'detail';
            this.pageHistory.push('detail');
            this.currentTweet = {};
            this.comments = [];
            this.newComment = '';

            const tweetFromList = this.tweets.find(t => t.id === tweetId);
            if (tweetFromList) {
                this.currentTweet = { ...tweetFromList };
            }

            try {
                const tweetData = await this.api(`/v2/tweet/get/${tweetId}`);
                this.currentTweet = { ...this.currentTweet, ...tweetData };

                // 确保作者信息已加载
                if (this.currentTweet.creater_id) {
                    this.fetchUsersInfo([this.currentTweet.creater_id]);
                }
            } catch (error) {
                this.showToast('推文加载失败', 'error');
                this.goBack();
                return;
            }

            this.loadComments(tweetId);
        },

        async loadComments(tweetId) {
            this.commentsLoading = true;

            try {
                this.comments = await this.api(`/v2/comment/list/${tweetId}?skip=0&limit=50`);
            } catch (error) {
                console.error('[Load Comments Error]', error);
                this.comments = [];
            } finally {
                this.commentsLoading = false;
            }
        },

        async submitComment() {
            if (!this.newComment.trim() || this.commentSubmitting) return;

            this.commentSubmitting = true;

            try {
                await this.api('/v2/comment/create', 'POST', {
                    tweet_id: this.currentTweet.id,
                    content: this.newComment,
                    tags: ''
                });

                this.newComment = '';
                await this.loadComments(this.currentTweet.id);
                this.showToast('评论成功', 'success');
            } catch (error) {
                this.showToast('评论失败：' + error.message, 'error');
            } finally {
                this.commentSubmitting = false;
            }
        },

        async deleteComment(commentId) {
            if (!confirm('确定要删除这条评论吗？')) return;

            try {
                await this.api(`/v2/comment/delete/${commentId}`, 'DELETE');
                await this.loadComments(this.currentTweet.id);
                this.showToast('评论已删除', 'success');
            } catch (error) {
                this.showToast('删除失败', 'error');
            }
        },

        async deleteCurrentTweet() {
            this.showDeleteTweetModal = false;

            try {
                await this.api(`/v2/tweet/delete/${this.currentTweet.id}`, 'DELETE');
                this.showToast('推文已删除', 'success');
                this.refreshTweets();
                this.goBack();
            } catch (error) {
                this.showToast('删除失败', 'error');
            }
        },

        // ========== 发布推文 ==========
        openCompose() {
            this.page = 'compose';
            this.pageHistory.push('compose');
            this.composeContent = '';
            this.composeImages = [];
            this.composeImageIds = [];
            this.composeTags = [];
            this.tagInputValue = '';
            this.showTagInput = false;
        },

        selectImage() {
            document.getElementById('compose-image-input').click();
        },

        async handleImageSelect(event) {
            const files = event.target.files;
            if (!files || files.length === 0) return;

            const remaining = 9 - this.composeImages.length;
            const toUpload = Array.from(files).slice(0, remaining);

            for (const file of toUpload) {
                if (file.size > 5 * 1024 * 1024) {
                    this.showToast('图片大小不能超过 5MB', 'error');
                    continue;
                }

                const preview = URL.createObjectURL(file);
                const formData = new FormData();
                formData.append('file', file);

                try {
                    const res = await this.api('/v2/image/upload', 'POST', formData, true);
                    this.composeImages.push({
                        id: res.id,
                        preview: preview,
                        file: file
                    });
                    this.composeImageIds.push(res.id);
                } catch (error) {
                    this.showToast('图片上传失败', 'error');
                    URL.revokeObjectURL(preview);
                }
            }

            event.target.value = '';
        },

        removeImage(index) {
            URL.revokeObjectURL(this.composeImages[index].preview);
            this.composeImages.splice(index, 1);
            this.composeImageIds.splice(index, 1);
        },

        addTag() {
            const tag = this.tagInputValue.trim().replace(/,/g, '');
            if (tag && !this.composeTags.includes(tag)) {
                this.composeTags.push(tag);
            }
            this.tagInputValue = '';
        },

        removeTag(index) {
            this.composeTags.splice(index, 1);
        },

        async publishTweet() {
            if ((!this.composeContent.trim() && this.composeImages.length === 0) || this.composeSubmitting) return;

            this.composeSubmitting = true;

            try {
                await this.api('/v2/tweet/create', 'POST', {
                    tweet: this.composeContent,
                    tags: this.composeTags.join(','),
                    is_published: true,
                    image_ids: this.composeImageIds
                });

                this.showToast('发布成功！', 'success');
                this.composeContent = '';
                this.composeImages = [];
                this.composeImageIds = [];
                this.composeTags = [];

                this.page = 'home';
                this.pageHistory.pop();
                this.refreshTweets();
            } catch (error) {
                this.showToast('发布失败：' + error.message, 'error');
            } finally {
                this.composeSubmitting = false;
            }
        },

        // ========== 个人主页 ==========
        async loadMyProfile() {
            if (!this.user.id) return;

            await this.loadUserInfo();

            try {
                this.myTweets = await this.api(`/v2/tweet/list?creater_id=${this.user.id}&limit=20&order=desc`);
            } catch (error) {
                console.error('[Load My Tweets Error]', error);
            }
        },

        uploadAvatar() {
            document.getElementById('avatar-input').click();
        },

        async handleAvatarUpload(event) {
            const file = event.target.files[0];
            if (!file) return;

            if (file.size > 5 * 1024 * 1024) {
                this.showToast('图片大小不能超过 5MB', 'error');
                return;
            }

            const formData = new FormData();
            formData.append('file', file);

            try {
                const res = await this.api('/v2/image/upload', 'POST', formData, true);

                await this.api(`/v2/users/put/${this.user.id}`, 'PUT', {
                    user_name: this.user.user_name,
                    email: this.user.email,
                    phone: this.user.phone || '',
                    password: '',
                    is_active: true,
                    whats_up: this.user.whats_up || '',
                    avatar_id: res.id
                });

                await this.loadUserInfo();
                // 更新缓存
                this.usersCache[this.user.id] = {
                     user_name: this.user.user_name,
                     avatar_id: res.id
                };
                this.showToast('头像更新成功！', 'success');
            } catch (error) {
                this.showToast('上传失败：' + error.message, 'error');
            }

            event.target.value = '';
        },

        startEditName() {
            this.editingName = true;
            this.editNameValue = this.user.user_name || '';
            this.$nextTick(() => {
                const input = document.querySelector('.edit-input');
                if (input) input.focus();
            });
        },

        async saveName() {
            if (!this.editNameValue.trim()) {
                this.editingName = false;
                return;
            }

            try {
                await this.api(`/v2/users/put/${this.user.id}`, 'PUT', {
                    user_name: this.editNameValue.trim(),
                    email: this.user.email,
                    phone: this.user.phone || '',
                    password: '',
                    is_active: true,
                    whats_up: this.user.whats_up || '',
                    avatar_id: this.user.avatar_id || 0
                });

                this.user.user_name = this.editNameValue.trim();
                localStorage.setItem('user', JSON.stringify(this.user));
                // 更新缓存
                if (this.usersCache[this.user.id]) {
                    this.usersCache[this.user.id].user_name = this.editNameValue.trim();
                }
                this.showToast('名称已更新', 'success');
            } catch (error) {
                this.showToast('更新失败', 'error');
            } finally {
                this.editingName = false;
            }
        },

        startEditBio() {
            this.editingBio = true;
            this.editBioValue = this.user.whats_up || '';
            this.$nextTick(() => {
                const inputs = document.querySelectorAll('.edit-input');
                if (inputs[1]) inputs[1].focus();
            });
        },

        async saveBio() {
            try {
                await this.api(`/v2/users/put/${this.user.id}`, 'PUT', {
                    user_name: this.user.user_name,
                    email: this.user.email,
                    phone: this.user.phone || '',
                    password: '',
                    is_active: true,
                    whats_up: this.editBioValue.trim(),
                    avatar_id: this.user.avatar_id || 0
                });

                this.user.whats_up = this.editBioValue.trim();
                localStorage.setItem('user', JSON.stringify(this.user));
                this.showToast('签名已更新', 'success');
            } catch (error) {
                this.showToast('更新失败', 'error');
            } finally {
                this.editingBio = false;
            }
        },

        // ========== 工具函数 ==========
        goBack() {
            if (this.pageHistory.length > 1) {
                this.pageHistory.pop();
                this.page = this.pageHistory[this.pageHistory.length - 1];
            } else {
                this.page = 'home';
            }
        },

        getAvatarUrl(avatarId) {
            if (!avatarId) {
                return this.getDefaultAvatar();
            }
            return `/api/v2/image/${avatarId}`;
        },

        formatTime(dateStr) {
            if (!dateStr) return '';

            try {
                const date = new Date(dateStr);
                const now = new Date();
                const diff = (now - date) / 1000;

                if (diff < 60) return '刚刚';
                if (diff < 3600) return Math.floor(diff / 60) + '分钟前';
                if (diff < 86400) return Math.floor(diff / 3600) + '小时前';
                if (diff < 604800) return Math.floor(diff / 86400) + '天前';

                return date.toLocaleDateString('zh-CN', {
                    month: 'numeric',
                    day: 'numeric'
                });
            } catch (e) {
                return dateStr;
            }
        },

        isTweetLong(content) {
            return content && content.length > 300;
        },

        getTweetDisplayContent(tweet) {
            if (!tweet.tweet) return '';
            
            // 清理内容：去除首尾换行和空格，合并连续换行（最多保留 2 个）
            let cleaned = tweet.tweet.trim().replace(/\n{3,}/g, '\n\n');

            if (this.expandedTweets[tweet.id]) {
                return cleaned;
            }

            if (this.isTweetLong(cleaned)) {
                return cleaned.substring(0, 300);
            }

            return cleaned;
        },

        toggleTweetExpand(tweetId) {
            this.expandedTweets[tweetId] = !this.expandedTweets[tweetId];
        },

        getImageGridClass(count) {
            if (count === 1) return 'single';
            if (count === 2) return 'double';
            if (count === 4) return 'grid-2';
            return 'grid-3';
        },

        getDisplayImages(imageIds) {
            if (!imageIds) return [];
            return imageIds.slice(0, 9);
        },

        previewImage(imgId) {
            this.previewImageId = imgId;
        },

        parseTags(tagsStr) {
            if (!tagsStr) return [];
            return tagsStr.split(',').filter(t => t.trim());
        },

        formatTags(tagsStr) {
            if (!tagsStr) return '';
            const tags = tagsStr.split(',').filter(t => t.trim());
            if (tags.length === 0) return '';
            if (tags.length === 1) return tags[0];
            return tags.slice(0, 2).join(', ') + (tags.length > 2 ? '...' : '');
        },

        truncateText(text, maxLength) {
            if (!text) return '';
            if (text.length <= maxLength) return text;
            return text.substring(0, maxLength) + '...';
        },

        showToast(message, type = 'info') {
            this.toast = { show: true, message, type };

            setTimeout(() => {
                this.toast.show = false;
            }, 3000);
        }
    };
}