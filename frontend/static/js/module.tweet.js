// static/js/module.tweet.js

/**
 * 推文模块
 * 处理推文列表、详情、发布、评论等核心业务逻辑
 */
window.AppTweet = {

    // ========== 状态定义 ==========

    // 搜索状态
    showSearch: false,          // 是否显示搜索框
    searchKeyword: '',          // 搜索关键词

    // 推文列表状态
    tweets: [],                 // 推文列表数据
    tweetsLoading: false,       // 列表加载中状态
    tweetsPage: 0,              // 当前页码
    hasMoreTweets: true,        // 是否还有更多数据
    expandedTweets: {},         // 记录长推文是否展开 { id: boolean }

    // 推文详情状态
    currentTweet: {},           // 当前查看的推文对象
    comments: [],               // 当前推文的评论列表
    commentsLoading: false,     // 评论加载状态
    newComment: '',             // 新评论内容
    commentSubmitting: false,   // 评论提交中状态
    showDeleteTweetModal: false,// 删除推文确认弹窗

    // 发布推文状态
    composeContent: '',         // 发布内容
    composeImages: [],          // 待上传图片预览列表
    composeImageIds: [],        // 已上传图片ID列表
    composeSubmitting: false,   // 发布提交中状态
    showTagInput: false,        // 是否显示标签输入
    composeTags: [],            // 标签列表
    tagInputValue: '',          // 标签输入框内容

    // ========== 列表逻辑 ==========

    /**
     * 加载推文列表 (分页加载)
     */
    async loadTweets() {
        // 防止重复加载 或 无更多数据
        if (this.tweetsLoading || !this.hasMoreTweets) return;

        this.tweetsLoading = true;
        try {
            const data = await this.api(`/v2/tweet/list?skip=${this.tweetsPage * 10}&limit=10&order=desc`);

            if (!data || data.length === 0) {
                this.hasMoreTweets = false;
            } else {
                // 追加新数据
                this.tweets.push(...data);

                // 关键优化：批量获取推文作者信息
                this.fetchUsersInfo(data.map(t => t.creater_id));

                // 判断是否还有更多
                if (data.length < 10) this.hasMoreTweets = false;
                else this.tweetsPage++;
            }
        } catch (error) {
            this.showToast('加载失败', 'error');
            this.hasMoreTweets = false;
        } finally {
            this.tweetsLoading = false;
        }
    },

    /**
     * 刷新推文列表 (重置状态并重新加载)
     */
    refreshTweets() {
        this.tweets = [];
        this.tweetsPage = 0;
        this.hasMoreTweets = true;
        this.expandedTweets = {};
        this.loadTweets();
    },

    /**
     * 搜索推文
     */
    async searchTweets() {
        // 如果关键词为空，视为刷新列表
        if (!this.searchKeyword.trim()) {
            this.refreshTweets();
            return;
        }

        this.tweets = [];
        this.tweetsLoading = true;
        this.hasMoreTweets = false; // 搜索结果不分页

        try {
            const res = await this.api(`/v2/tweet/search/?keyword=${encodeURIComponent(this.searchKeyword)}&skip=0&limit=50`);
            this.tweets = res.results || [];

            if (this.tweets.length > 0) {
                // 搜索结果也需要获取作者信息
                this.fetchUsersInfo(this.tweets.map(t => t.creater_id));
            }
        } catch (error) {
            this.showToast('搜索失败', 'error');
        } finally {
            this.tweetsLoading = false;
        }
    },

    // ========== 详情逻辑 ==========

    /**
     * 查看推文详情
     * @param {number} tweetId - 推文ID
     */
    async viewTweetDetail(tweetId) {
        this.page = 'detail';
        this.pageHistory.push('detail');

        // 重置详情页状态
        this.currentTweet = {};
        this.comments = [];
        this.newComment = '';

        // 优先从列表中获取缓存数据，提升体验
        const tweetFromList = this.tweets.find(t => t.id === tweetId);
        if (tweetFromList) this.currentTweet = { ...tweetFromList };

        try {
            // 获取服务端最新数据
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

        // 加载评论
        this.loadComments(tweetId);
    },

    /**
     * 加载评论列表
     * @param {number} tweetId - 推文ID
     */
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

    /**
     * 提交评论
     */
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

    /**
     * 删除评论
     * @param {number} commentId - 评论ID
     */
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

    /**
     * 删除当前推文
     */
    async deleteCurrentTweet() {
        this.showDeleteTweetModal = false;
        try {
            await this.api(`/v2/tweet/delete/${this.currentTweet.id}`, 'DELETE');
            this.showToast('推文已删除', 'success');
            this.refreshTweets(); // 刷新列表
            this.goBack();        // 返回上一页
        } catch (error) {
            this.showToast('删除失败', 'error');
        }
    },

    // ========== 发布逻辑 ==========

    /**
     * 打开发布页面
     */
    openCompose() {
        this.page = 'compose';
        this.pageHistory.push('compose');
        // 重置发布表单
        this.composeContent = '';
        this.composeImages = [];
        this.composeImageIds = [];
        this.composeTags = [];
        this.tagInputValue = '';
        this.showTagInput = false;
    },

    /**
     * 触发图片选择器
     */
    selectImage() {
        document.getElementById('compose-image-input').click();
    },

    /**
     * 处理图片选择与上传
     * @param {Event} event - 文件选择事件
     */
    async handleImageSelect(event) {
        const files = event.target.files;
        if (!files || files.length === 0) return;

        // 计算剩余可上传数量 (最多9张)
        const remaining = 9 - this.composeImages.length;
        const toUpload = Array.from(files).slice(0, remaining);

        for (const file of toUpload) {
            // 大小限制 5MB
            if (file.size > 5 * 1024 * 1024) {
                this.showToast('图片大小不能超过 5MB', 'error');
                continue;
            }

            const preview = URL.createObjectURL(file); // 生成本地预览URL
            const formData = new FormData();
            formData.append('file', file);

            try {
                // 上传图片到服务器
                const res = await this.api('/v2/image/upload', 'POST', formData, true);
                this.composeImages.push({ id: res.id, preview });
                this.composeImageIds.push(res.id);
            } catch (error) {
                this.showToast('图片上传失败', 'error');
                URL.revokeObjectURL(preview); // 上传失败释放内存
            }
        }
        event.target.value = ''; // 清空 input 以便重复选择相同文件
    },

    /**
     * 移除已选图片
     * @param {number} index - 图片索引
     */
    removeImage(index) {
        URL.revokeObjectURL(this.composeImages[index].preview); // 释放内存
        this.composeImages.splice(index, 1);
        this.composeImageIds.splice(index, 1);
    },

    /**
     * 添加标签
     */
    addTag() {
        const tag = this.tagInputValue.trim().replace(/,/g, '');
        if (tag && !this.composeTags.includes(tag)) {
            this.composeTags.push(tag);
        }
        this.tagInputValue = '';
    },

    /**
     * 移除标签
     * @param {number} index - 标签索引
     */
    removeTag(index) {
        this.composeTags.splice(index, 1);
    },

    /**
     * 发布推文
     */
    async publishTweet() {
        // 自动登录
        await this.autoLogin();
        // 验证内容
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

            // 清理并跳转
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

    // ========== 展示辅助 ==========

    /**
     * 获取推文展示内容 (处理折叠逻辑)
     * @param {Object} tweet - 推文对象
     * @returns {string} 处理后的内容
     */
    getTweetDisplayContent(tweet) {
        if (!tweet.tweet) return '';

        
        // 清理内容：去除首尾换行和空格，合并连续换行（最多保留 2 个）
        let cleaned = tweet.tweet.trim().replace(/\n{3,}/g, '\n\n');
        // 如果已展开，显示全文
        if (this.expandedTweets[tweet.id]) return cleaned;

        // 如果是长文，截取前300字
        if (this.isTweetLong(cleaned)) return cleaned.substring(0, 200);

        return cleaned;
    },

    /**
     * 切换推文展开状态
     * @param {number} tweetId - 推文ID
     */
    toggleTweetExpand(tweetId) {
        this.expandedTweets[tweetId] = !this.expandedTweets[tweetId];
    },

    /**
     * 判断推文是否为长文（超过 10 行）
     * @param {string} text - 推文内容
     * @returns {boolean} 是否为长文
     */
    isTweetLong(text) {
        if (!text) return false;
        
        const lines = text.split('\n').length;
        const chars = text.length;
        
        return lines > 10 || chars > 150;
    },

    /**
     * 与推文作者开始私聊
     * @param {number} userId - 用户 ID
     */
    async startChatWithUser(userId) {
        if (!userId) return;
        
        try {
            // 1. 创建私聊会话
            const res = await this.api(`/v2/chat/conversations/private/${userId}`, 'POST');
            const convId = res.id;
            
            this.showToast('已创建私聊', 'success');
            
            // 2. 获取 App 实例（用于跳转）
            const app = window.App();
            
            // 3. 加载会话列表并跳转
            const convs = await this.api('/v2/chat/conversations');
            const conversation = convs.data.find(c => c.id === convId);
            
            if (conversation) {
                // 设置当前聊天
                app.currentChat = conversation;
                app.page = 'chat_detail';
                app.pageHistory.push('chat_detail');
                app.messages = [];
                
                // 加载消息
                await app.loadMessages(convId, 0);
                
                // 强制更新视图
                if (app.$dispatch) {
                    app.$dispatch('refresh');
                }
            }
        } catch (error) {
            this.showToast('创建私聊失败：' + error.message, 'error');
        }
    },


    // ========== 点赞功能 ==========
    
    /**
     * 切换点赞状态
     */
    async toggleLike(tweet) {
        try {
            const isLiked = tweet.is_liked;
            const tweetId = tweet.id;
            
            // 乐观更新 UI
            tweet.is_liked = !isLiked;
            tweet.like_count = (tweet.like_count || 0) + (isLiked ? -1 : 1);
            
            // 调用 API
            const res = await this.api(`/v2/tweet/${tweetId}/like`, 'POST');
            
            // 同步服务器返回的结果
            tweet.is_liked = res.liked;
            tweet.like_count = res.count;
            
        } catch (error) {
            this.showToast('点赞失败：' + error.message, 'error');
            // 恢复状态
            tweet.is_liked = !tweet.is_liked;
            tweet.like_count = (tweet.like_count || 0) + (tweet.is_liked ? -1 : 1);
        }
    },
    
    /**
     * 加载推文点赞信息
     */
    async loadTweetLikes(tweetId) {
        try {
            const res = await this.api(`/v2/tweet/${tweetId}/likes`);
            return res;
        } catch (error) {
            console.error('加载点赞失败:', error);
            return { count: 0, is_liked: false };
        }
    }
};

