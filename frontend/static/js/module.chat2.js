// static/js/module.chat.js

/**
 * 聊天业务模块
 * 包含：会话列表、创建群聊、添加成员、消息收发、用户搜索
 */

console.log('>>> [Debug] module.chat.js 开始加载');

window.AppChat = {

    // 1. 状态
    chatMessages: [],

    // 2. 消息模板
    // 【修正】后端文档要求字段是 "event"，原模板是 "action"，已修正
    MESSAGE_TEMPLATE: {
        action: "send_message",
        data: {
            conversation_id: 1,
            content: "123string，今晚吃什么？",
            type: "text"
        }
    },

    // 3. 初始化方法
    initChat: function() {
        console.log('[Chat] initChat 执行了');

        // 【新增】监听连接成功事件
        window.addEventListener('ws-connected', () => {
            console.log('[Chat] 检测到 WS 连接成功，1秒后自动发送测试消息...');

            // 延迟1秒发送，确保连接稳定
            setTimeout(() => {
                this.sendDefaultMessage();
            }, 1000);
        });

        // 监听收到消息
        window.addEventListener('ws-message', (e) => {
            console.log('[Chat] 收到推送:', e.detail);
            this.chatMessages.push(e.detail);
        });

        // 启动连接
        if (this.token) {
            window.WS.connect(this.token);
        }
    },

    // 4. 发送测试消息方法
    sendDefaultMessage: function() {
        console.log('[Chat] 正在发送消息...', this.MESSAGE_TEMPLATE);
        const success = window.WS.send(this.MESSAGE_TEMPLATE);
        if (success) {
            console.log('[Chat] 消息已写入 WebSocket 缓冲区');
        } else {
            console.error('[Chat] 发送失败，连接未就绪');
        }
    },
    //-----------------------------------------------
    // === 状态定义 ===
    conversations: [],       // 会话列表
    currentChat: null,       // 当前聊天对象
    messages: [],            // 当前聊天消息
    newMessage: '',          // 输入框内容

    // 弹窗状态
    showCreateGroup: false,  // 创建群聊弹窗
    showAddMember: false,    // 添加成员弹窗

    // 搜索与选择
    searchKeyword: '',       // 搜索关键词
    searchResults: [],       // 搜索结果
    selectedUsers: [],       // 已选择的用户（用于创建群聊）
    newGroupName: '',        // 新群名称

    // === 会话列表 ===

    async loadConversations() {
        try {
            const res = await this.api('/v2/chat/conversations');
            this.conversations = res.data || [];
        } catch (error) {
            console.error('[Load Conversations Error]', error);
        }
    },

    async openChat(conv) {
        this.currentChat = conv;
        this.page = 'chat_detail';
        this.pageHistory.push('chat_detail');
        this.messages = [];
        await this.loadMessages(conv.id, 0);
    },

    async loadMessages(convId, beforeId = 0) {
        try {
            const res = await this.api(`/v2/chat/conversations/${convId}/messages?before_id=${beforeId}&limit=20`);
            // 处理返回的数据格式：列表套字典，字典key为id等
            const msgList = res || [];
            // 如果是加载更多，追加到头部；否则直接赋值
            if (beforeId > 0) {
                this.messages = [...msgList, ...this.messages];
            } else {
                this.messages = msgList;
            }
            this.$nextTick(() => this.scrollToBottom());
        } catch (error) {
            console.error('[Load Messages Error]', error);
        }
    },

    // === 消息发送 ===

    async sendMessage() {
        if (!this.newMessage.trim()) return;

        const content = this.newMessage;
        this.newMessage = '';

        // 构造发送数据
        const data = {
            conversation_id: this.currentChat.id,
            content: content,
            type: 'text'
        };

        // 通过 WebSocket 发送
        const sent = window.AppWS.send('new_message', data);

        if (!sent) {
            this.showToast('连接已断开，正在重连...', 'error');
            // 如果发送失败，可以存入本地队列，待重连后重发
        }
    },

    async sendImage(event) {
        const file = event.target.files[0];
        if (!file) return;

        // 上传图片
        const formData = new FormData();
        formData.append('file', file);

        try {
            const res = await this.api('/v2/image/upload', 'POST', formData, true);

            // 发送图片消息
            const data = {
                conversation_id: this.currentChat.id,
                content: res.id.toString(), // 发送图片ID
                type: 'image'
            };

            window.AppWS.send('new_message', data);
        } catch (error) {
            this.showToast('图片上传失败', 'error');
        }
        event.target.value = '';
    },

    // 接收推送消息
    handleIncomingMessage(msg) {
        // 如果是当前聊天窗口的消息，直接添加
        if (this.currentChat && msg.conversation_id === this.currentChat.id) {
            this.messages.push(msg);
            this.$nextTick(() => this.scrollToBottom());
        }

        // 更新会话列表中的最后一条消息
        const conv = this.conversations.find(c => c.id === msg.conversation_id);
        if (conv) {
            conv.last_message = msg.content;
            conv.last_message_time = msg.created_at;
        }
    },

    scrollToBottom() {
        const container = document.getElementById('chat-messages-container');
        if (container) {
            container.scrollTop = container.scrollHeight;
        }
    },

    // === 用户搜索 ===

    async searchUsers() {
        if (!this.searchKeyword.trim()) {
            this.searchResults = [];
            return;
        }

        try {
            const res = await this.api(`/v2/chat/users/search?keyword=${encodeURIComponent(this.searchKeyword)}`);
            this.searchResults = res.data || [];
        } catch (error) {
            console.error('[Search Users Error]', error);
        }
    },

    toggleSelectUser(user) {
        const index = this.selectedUsers.findIndex(u => u.id === user.id);
        if (index >= 0) {
            this.selectedUsers.splice(index, 1);
        } else {
            this.selectedUsers.push(user);
        }
    },

    isSelected(user) {
        return this.selectedUsers.some(u => u.id === user.id);
    },

    // === 创建群聊 ===

    openCreateGroupModal() {
        this.searchKeyword = '';
        this.searchResults = [];
        this.selectedUsers = [];
        this.newGroupName = '';
        this.showCreateGroup = true;
    },

    async createGroup() {
        if (this.selectedUsers.length === 0) {
            this.showToast('请至少选择一位成员', 'error');
            return;
        }

        try {
            // API 要求传入用户ID数组
            const userIds = this.selectedUsers.map(u => u.id);
            await this.api('/v2/chat/conversations/group', 'POST', userIds);

            this.showToast('群聊创建成功', 'success');
            this.showCreateGroup = false;
            this.loadConversations();
        } catch (error) {
            this.showToast('创建失败: ' + error.message, 'error');
        }
    },

    // === 添加群成员 ===

    openAddMemberModal() {
        this.searchKeyword = '';
        this.searchResults = [];
        this.selectedUsers = [];
        this.showAddMember = true;
    },

    async addMembers() {
        if (this.selectedUsers.length === 0) {
            this.showToast('请选择要添加的成员', 'error');
            return;
        }

        try {
            const userIds = this.selectedUsers.map(u => u.id);
            await this.api(`/v2/chat/conversations/${this.currentChat.id}/members`, 'POST', userIds);

            this.showToast('成员添加成功', 'success');
            this.showAddMember = false;
        } catch (error) {
            this.showToast('添加失败: ' + error.message, 'error');
        }
    }
};

console.log('>>> [Debug] module.chat.js 加载完毕, AppChat=', window.AppChat);

