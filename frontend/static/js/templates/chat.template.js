// Template Version: 2026-03-12-1925
// static/js/templates/chat.template.js

window.ChatTemplates = {
    // 会话列表页
    conversationList: `
        <div x-show="page === 'chat'" x-transition class="page-container chat-page-bg">
            <header class="page-header">
                <h1>🦞 虾说</h1>
                <button class="header-btn" @click="openCreateGroupModal">+</button>
            </header>

            <div class="chat-list-container">
                <template x-for="conv in conversations" :key="conv.id">
                    <div @click="openChat(conv)" class="chat-list-item">
                        <img :src="getConversationAvatar(conv)" class="chat-avatar chat-avatar-lg">

                        <div class="chat-info">
                            <div class="chat-info-hd">
                                <span class="chat-name" 
                                      x-text="conv.type === 'private' ? getPrivateChatName(conv) : (conv.group_name || '群聊')"></span>
                                <span class="chat-time" x-text="formatTime(conv.last_message_time)"></span>
                            </div>
                            <div class="chat-info-bd">
                                <p class="chat-msg-text" x-text="conv.last_message || '暂无消息'"></p>
                                <span x-show="conv.unread_count > 0" class="chat-unread" x-text="conv.unread_count > 99 ? '99+' : conv.unread_count"></span>
                            </div>
                        </div>
                    </div>
                </template>

                <div x-show="conversations.length === 0" class="empty-state">
                    <p class="text-6xl mb-4">💬</p>
                    <p>还没有消息</p>
                    <p class="text-sm mt-2" style="color: var(--text-light);">点击右上角 + 发起聊天</p>
                </div>
            </div>
        </div>
    `,

    // 聊天详情页
    chatDetail: `
        <div x-show="page === 'chat_detail'" x-transition class="chat-detail-page">
            <header class="page-header">
                <button @click="goBack" class="header-btn">←</button>
                <h1 x-text="getChatTitle(currentChat)"></h1>
                
                <template x-if="currentChat?.type === 'group'">
                    <div style="display: flex; gap: 8px;">
                        <button @click="openAddMemberModal" class="header-btn" style="font-size: 16px;">+</button>
                        <button @click="openEditGroupNameModal" class="header-btn" style="font-size: 14px;">✏️</button>
                    </div>
                </template>
                
                <template x-if="currentChat?.type !== 'group'">
                    <span style="width: 80px;"></span>
                </template>
            </header>

            <div id="chat-messages-container" class="chat-msg-area">
                <template x-for="msg in messages" :key="msg.id">
                    <div class="msg-row" :class="msg.sender_id === user.id ? 'is-self' : 'is-other'">
                        <template x-if="msg.sender_id !== user.id">
                            <div class="msg-block">
                                <img :src="getUserAvatar(msg.sender_avatar_id || msg.sender_id)" class="chat-avatar chat-avatar-sm">
                                <div class="msg-body">
                                    <div x-show="currentChat?.type === 'group'" class="msg-nickname" x-text="msg.sender_name"></div>
                                    <div class="bubble bubble-other">
                                        <span x-show="msg.type === 'text'" x-html="renderMarkdown(msg.content)"></span>
                                        <img x-if="msg.type === 'image' || msg.type === 'img'" :src="(msg.type === 'image' || msg.type === 'img') ? getUserAvatar_chat(msg.content) : ''" class="bubble-img" @click="previewImage(msg.content)">
                                    </div>
                                    <span class="msg-time msg-time-other" x-text="formatTime(msg.created_at)"></span>
                                </div>
                            </div>
                        </template>

                        <template x-if="msg.sender_id === user.id">
                            <div class="msg-block" style="flex-direction: row-reverse;">
                                <img :src="getUserAvatar_chat(user.avatar_id)" class="chat-avatar chat-avatar-sm">
                                <div class="msg-body" style="align-items: flex-end;">
                                    <div x-show="currentChat?.type === 'group'" class="msg-sender-name" x-text="user.user_name"></div>
                                    <div class="bubble bubble-self">
                                        <span x-show="msg.type === 'text'" x-html="renderMarkdown(msg.content)"></span>
                                        <img x-if="msg.type === 'image' || msg.type === 'img'" :src="(msg.type === 'image' || msg.type === 'img') ? getUserAvatar_chat(msg.content) : ''" class="bubble-img" @click="previewImage(msg.content)">
                                    </div>
                                    <span class="msg-time msg-time-self" x-text="formatTime(msg.created_at)"></span>
                                </div>
                            </div>
                        </template>
                    </div>
                </template>
            </div>

            <footer class="chat-input-bar">
                <label class="input-action-btn">
                    <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="16"></line><line x1="8" y1="12" x2="16" y2="12"></line></svg>
                    <input type="file" accept="image/*" class="hidden" @change="sendImage">
                </label>

                <div class="input-wrapper">
                    <input type="text" x-model="newMessage" placeholder="输入消息..." class="input-text-field" @keyup.enter="sendMessage">
                </div>

                <button @click="sendMessage" class="input-send-btn" :class="{ 'active': newMessage.trim().length > 0 }">
                    <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
                </button>
            </footer>
        </div>
    `,

    createGroupModal: `
        <div x-show="showCreateGroup" class="modal-overlay" @click.self="showCreateGroup = false">
            <div class="modal-box">
                <div class="modal-header">
                    <h3>创建群聊</h3>
                    <button @click="showCreateGroup = false" class="modal-close-btn">×</button>
                </div>
                <div class="modal-body">
                    <input type="text" x-model="searchKeyword" @input="searchUsers()" placeholder="搜索用户..." class="form-input">
                    <div x-show="selectedUsers.length > 0" class="selected-tags">
                        <template x-for="u in selectedUsers" :key="u.id">
                            <span class="tag-item">
                                <span x-text="u.user_name"></span>
                                <button @click="toggleSelectUser(u)" class="tag-close">×</button>
                            </span>
                        </template>
                    </div>
                    <div class="user-list">
                        <template x-for="u in searchResults" :key="u.id">
                            <div @click="toggleSelectUser(u)" class="user-item" :class="isSelected(u) ? 'active' : ''">
                                <img :src="getUserAvatar(u.avatar_id)" class="chat-avatar chat-avatar-sm">
                                <span x-text="u.user_name"></span>
                                <span x-show="isSelected(u)" class="check-icon">✓</span>
                            </div>
                        </template>
                    </div>
                </div>
                <div class="modal-footer">
                    <button @click="showCreateGroup = false" class="btn btn-cancel">取消</button>
                    <button @click="createGroup" class="btn btn-confirm">创建</button>
                </div>
            </div>
        </div>
    `,

    addMemberModal: `
        <div x-show="showAddMember" class="modal-overlay" @click.self="showAddMember = false">
            <div class="modal-box">
                <div class="modal-header">
                    <h3>添加成员</h3>
                    <button @click="showAddMember = false" class="modal-close-btn">×</button>
                </div>
                <div class="modal-body">
                    <input type="text" x-model="searchKeyword" @input="searchUsers()" placeholder="搜索用户..." class="form-input">
                    <div class="user-list">
                        <template x-for="u in searchResults" :key="u.id">
                            <div @click="toggleSelectUser(u)" class="user-item" :class="isSelected(u) ? 'active' : ''">
                                <img :src="getUserAvatar(u.avatar_id)" class="chat-avatar chat-avatar-sm">
                                <span x-text="u.user_name"></span>
                                <span x-show="isSelected(u)" class="check-icon">✓</span>
                            </div>
                        </template>
                    </div>
                </div>
                <div class="modal-footer">
                    <button @click="showAddMember = false" class="btn btn-cancel">取消</button>
                    <button @click="addMembers" class="btn btn-confirm">添加</button>
                </div>
            </div>
        </div>
    `,

    editGroupNameModal: `
        <div x-show="showEditGroupName" class="modal-overlay" @click.self="showEditGroupName = false">
            <div class="modal-box">
                <div class="modal-header">
                    <h3>修改群聊名称</h3>
                    <button @click="showEditGroupName = false" class="modal-close-btn">×</button>
                </div>
                <div class="modal-body">
                    <input type="text" 
                           x-model="editGroupNameValue" 
                           placeholder="输入新的群聊名称" 
                           class="form-input"
                           @keyup.enter="updateGroupName()"
                           maxlength="50">
                </div>
                <div class="modal-footer">
                    <button @click="showEditGroupName = false" class="btn btn-cancel">取消</button>
                    <button @click="updateGroupName()" class="btn btn-confirm">保存</button>
                </div>
            </div>
        </div>
    `
};
