// static/js/module.user.js

/**
 * 用户模块
 * 处理用户信息缓存、个人主页展示、资料修改及头像上传
 */
window.AppUser = {

    // ========== 状态定义 ==========

    myTweets: [],           // 当前用户的推文列表
    myTweetsPage: 0,        // 当前页码
    myTweetsLoading: false, // 加载中
    hasMoreMyTweets: true,  // 是否还有更多
    totalLikes: 0,          // 总点赞数
    totalTweets: 0,         // 总推文数
    editingName: false,     // 是否处于编辑姓名状态
    editingBio: false,      // 是否处于编辑签名状态
    editNameValue: '',      // 编辑姓名的输入值
    editBioValue: '',       // 编辑签名的输入值
    previewImageId: null,   // 当前预览的图片ID

    // ========== 缓存逻辑 ==========

    /**
     * 批量获取并缓存用户信息
     * 优化性能：避免在渲染推文列表时为每个推文单独请求用户信息
     * @param {Array<number>} userIds - 需要获取的用户ID数组
     */
    async fetchUsersInfo(userIds) {
        // 1. 去重并过滤掉已缓存和无效的ID
        const uniqueIds = [...new Set(userIds)].filter(id => id && !this.usersCache[id]);
        if (uniqueIds.length === 0) return;

        // 2. 并行请求所有缺失的用户信息
        const promises = uniqueIds.map(id =>
            this.api(`/v2/users/get/${id}`)
                .then(userInfo => {
                    if (userInfo) {
                        // 存入缓存：仅保存必要字段减少内存占用
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

    /**
     * 获取用户显示名称 (优先使用缓存)
     * @param {Object} tweet - 推文对象
     * @returns {string} 用户名
     */
    getUserDisplayName(tweet) {
        if (tweet.creater_id && this.usersCache[tweet.creater_id]) {
            return this.usersCache[tweet.creater_id].user_name;
        }
        // 降级处理：使用推文自带名称或默认文本
        return tweet.user_name || '加载中...';
    },

    /**
     * 获取用户头像URL (优先使用缓存)
     * @param {number} userId - 用户ID
     * @returns {string} 头像URL
     */
    getUserAvatar(userId) {
        if (!userId) return this.getDefaultAvatar();

        if (this.usersCache[userId] && this.usersCache[userId].avatar_id) {
            return '/api/v2/image/' + this.usersCache[userId].avatar_id;
        }
        return this.getDefaultAvatar();
    },

    // ========== 个人主页逻辑 ==========

    /**
     * 加载个人主页数据
     */
    async loadMyProfile() {
        if (!this.user.id) return;

        // 先刷新用户详细信息
        await this.loadUserInfo();

        // 重置分页状态
        this.myTweetsPage = 0;
        this.myTweetsLoading = false;
        this.hasMoreMyTweets = true;

        // 加载第一页
        await this.loadMyTweets();
        
        // 加载总点赞数
        try {
            const likes = await this.getTotalLikes();
            this.totalLikes = likes;
            console.log('[Profile] 总点赞数:', likes);
        } catch (error) {
            console.error('[Profile] 获取点赞数失败:', error);
            this.totalLikes = 0;
        }
        
        // 加载总推文数
        try {
            const tweets = await this.getTotalTweets();
            this.totalTweets = tweets;
            console.log('[Profile] 总推文数:', tweets);
        } catch (error) {
            console.error('[Profile] 获取推文数失败:', error);
            this.totalTweets = 0;
        }
    },

    /**
     * 刷新当前登录用户的详细信息
     */
    async loadUserInfo() {
        if (!this.user.id) return;
        try {
            const info = await this.api(`/v2/users/get/${this.user.id}`);
            // 合并最新信息
            this.user = { ...this.user, ...info };
            localStorage.setItem('user', JSON.stringify(this.user));
        } catch (error) {
            console.error('[Load User Info Error]', error);
        }
    },

    /**
     * 加载我的推文（分页）
     */
    async loadMyTweets() {
        if (this.myTweetsLoading || !this.hasMoreMyTweets) return;

        this.myTweetsLoading = true;
        try {
            const skip = this.myTweetsPage * 20;
            const res = await this.api(`/v2/tweet/list?skip=${skip}&limit=20&creater_id=${this.user.id}&order=desc`);
            
            if (!res || res.length === 0) {
                this.hasMoreMyTweets = false;
            } else {
                this.myTweets.push(...res);
                this.myTweetsPage++;
                
                if (res.length < 20) {
                    this.hasMoreMyTweets = false;
                }
            }
        } catch (error) {
            console.error('加载我的推文失败:', error);
        } finally {
            this.myTweetsLoading = false;
        }
    },

    /**
     * 获取总推文数
     */
    async getTotalTweets() {
        console.log('[getTotalTweets] 用户 ID:', this.user.id);
        
        if (!this.user.id) {
            console.log('[getTotalTweets] 用户 ID 为空');
            return 0;
        }
        
        try {
            const url = `/v2/tweet/user/${this.user.id}/tweets`;
            console.log('[getTotalTweets] 请求 URL:', url);
            
            const res = await this.api(url);
            console.log('[getTotalTweets] API 响应:', res);
            
            return res.total_tweets || 0;
        } catch (error) {
            console.error('[getTotalTweets] 错误:', error);
            return 0;
        }
    },

    /**
     * 获取总点赞数
     */
    async getTotalLikes() {
        console.log('[getTotalLikes] 用户 ID:', this.user.id);
        
        if (!this.user.id) {
            console.log('[getTotalLikes] 用户 ID 为空');
            return 0;
        }
        
        try {
            const url = `/v2/tweet/user/${this.user.id}/likes`;
            console.log('[getTotalLikes] 请求 URL:', url);
            
            const res = await this.api(url);
            console.log('[getTotalLikes] API 响应:', res);
            
            return res.total_likes || 0;
        } catch (error) {
            console.error('[getTotalLikes] 错误:', error);
            return 0;
        }
    },

    /**
     * 触发头像文件选择
     */
    uploadAvatar() {
        document.getElementById('avatar-input').click();
    },

    /**
     * 处理头像上传
     * @param {Event} event - 文件选择事件
     */
    async handleAvatarUpload(event) {
        const file = event.target.files[0];
        if (!file) return;

        // 校验文件大小 (限制5MB)
        if (file.size > 5 * 1024 * 1024) {
            this.showToast('图片大小不能超过 5MB', 'error');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        try {
            // 1. 上传图片文件，获取图片ID
            const res = await this.api('/v2/image/upload', 'POST', formData, true);

            // 2. 更新用户资料，关联新头像ID
            await this.api(`/v2/users/put/${this.user.id}`, 'PUT', {
                user_name: this.user.user_name,
                email: this.user.email,
                phone: this.user.phone || '',
                password: '', // 留空表示不修改密码
                is_active: true,
                whats_up: this.user.whats_up || '',
                avatar_id: res.id // 新头像ID
            });

            // 3. 更新本地状态和缓存
            await this.loadUserInfo();
            this.usersCache[this.user.id] = {
                user_name: this.user.user_name,
                avatar_id: res.id
            };

            this.showToast('头像更新成功！', 'success');
        } catch (error) {
            this.showToast('上传失败：' + error.message, 'error');
        }

        // 清空input，允许重复选择同一文件
        event.target.value = '';
    },

    /**
     * 进入编辑姓名模式
     */
    startEditName() {
        this.editingName = true;
        this.editNameValue = this.user.user_name || '';
        // 等待DOM更新后自动聚焦输入框
        this.$nextTick(() => {
            const input = document.querySelector('.edit-input');
            if (input) input.focus();
        });
    },

    /**
     * 保存修改后的姓名
     */
    async saveName() {
        const newName = this.editNameValue.trim();
        if (!newName) {
            this.editingName = false;
            return;
        }

        try {
            // 调用API更新
            await this.api(`/v2/users/put/${this.user.id}`, 'PUT', {
                user_name: newName,
                email: this.user.email,
                phone: this.user.phone || '',
                password: '',
                is_active: true,
                whats_up: this.user.whats_up || '',
                avatar_id: this.user.avatar_id || 0
            });

            // 更新本地数据
            this.user.user_name = newName;
            localStorage.setItem('user', JSON.stringify(this.user));

            // 同步更新缓存，确保推文列表中显示的新名称立即生效
            if (this.usersCache[this.user.id]) {
                this.usersCache[this.user.id].user_name = newName;
            }

            this.showToast('名称已更新', 'success');
        } catch (error) {
            this.showToast('更新失败', 'error');
        } finally {
            this.editingName = false;
        }
    },

    /**
     * 进入编辑签名模式
     */
    startEditBio() {
        this.editingBio = true;
        this.editBioValue = this.user.whats_up || '';
        this.$nextTick(() => {
            // 注意：这里假设签名输入框是第二个 .edit-input
            const inputs = document.querySelectorAll('.edit-input');
            if (inputs[1]) inputs[1].focus();
        });
    },

    /**
     * 保存修改后的签名
     */
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

    /**
     * 图片预览功能
     * @param {number} imgId - 图片ID
     */
    previewImage(imgId) {
        this.previewImageId = imgId;
    }
};
