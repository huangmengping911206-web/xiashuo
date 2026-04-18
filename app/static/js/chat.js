// static/js/chat.js
import { db } from './store.js';
import { showToast, escapeHtml, getAvatarColor, getInitial, formatDate } from './utils.js';
import { showPage } from './app.js';

export function initChatEvents() {
  document.getElementById('sendMessageBtn').addEventListener('click', sendMessage);
  document.getElementById('chatInput').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
  });
}

export function renderChatList() {
  const container = document.getElementById('chatList');
  const myChats = db.chats.filter(c =>
    c.user1Id === db.currentUser.id || c.user2Id === db.currentUser.id
  );

  if (myChats.length === 0) {
    container.innerHTML = `<div class="text-center py-12 text-ghibli-textLight"><i class="fas fa-paper-plane text-4xl mb-4 opacity-50"></i><p>还没有聊天记录</p></div>`;
    return;
  }

  container.innerHTML = myChats.map(chat => {
    const partnerId = chat.user1Id === db.currentUser.id ? chat.user2Id : chat.user1Id;
    const partner = db.users.find(u => u.id === partnerId);
    if (!partner) return '';

    const lastMessage = chat.messages[chat.messages.length - 1];
    const avatarColor = getAvatarColor(partner.username);

    return `
      <div onclick="window.openChat('${partnerId}')" class="ghibli-card rounded-xl p-4 cursor-pointer">
        <div class="flex items-center gap-3">
          <div class="w-12 h-12 rounded-full flex items-center justify-center text-white font-bold" style="background-color: ${avatarColor}">
            ${partner.avatar ? `<img src="${partner.avatar}" class="w-full h-full rounded-full object-cover">` : getInitial(partner.nickname || partner.username)}
          </div>
          <div class="flex-1 min-w-0">
            <div class="font-medium text-ghibli-text">${escapeHtml(partner.nickname || partner.username)}</div>
            <p class="text-sm text-ghibli-textLight truncate">${lastMessage ? escapeHtml(lastMessage.content) : '开始聊天吧'}</p>
          </div>
          <span class="text-xs text-ghibli-textLight">${lastMessage ? formatDate(lastMessage.createdAt) : ''}</span>
        </div>
      </div>
    `;
  }).join('');
}

window.openChat = (userId) => {
  if (!db.currentUser) { showToast('请先登录'); return; }
  if (userId === db.currentUser.id) { showToast('不能和自己聊天哦'); return; }

  const user = db.users.find(u => u.id === userId);
  if (!user) return;

  let chat = db.chats.find(c =>
    (c.user1Id === db.currentUser.id && c.user2Id === userId) ||
    (c.user1Id === userId && c.user2Id === db.currentUser.id)
  );

  if (!chat) {
    chat = {
      id: generateId(),
      user1Id: db.currentUser.id,
      user2Id: userId,
      messages: [],
      createdAt: Date.now()
    };
    db.chats.push(chat);
    db.save();
  }

  const avatarColor = getAvatarColor(user.username);
  document.getElementById('chatPartnerAvatar').style.backgroundColor = avatarColor;
  document.getElementById('chatPartnerAvatar').innerHTML = user.avatar
    ? `<img src="${user.avatar}" class="w-full h-full rounded-full object-cover">`
    : getInitial(user.nickname || user.username);
  document.getElementById('chatPartnerName').textContent = user.nickname || user.username;
  document.getElementById('chatDetailPage').dataset.chatId = chat.id;
  document.getElementById('chatDetailPage').dataset.partnerId = userId;

  renderChatMessages(chat);
  showPage('chatDetailPage');
};

function renderChatMessages(chat) {
  const container = document.getElementById('chatMessages');
  const partnerId = document.getElementById('chatDetailPage').dataset.partnerId;
  const partner = db.users.find(u => u.id === partnerId);

  container.innerHTML = chat.messages.map(msg => {
    const isSent = msg.senderId === db.currentUser.id;
    const sender = isSent ? db.currentUser : partner;
    const avatarColor = getAvatarColor(sender.username);

    return `
      <div class="flex ${isSent ? 'justify-end' : 'justify-start'} items-end gap-2">
        ${!isSent ? `<div class="w-6 h-6 rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0" style="background-color: ${avatarColor}">${sender.avatar ? `<img src="${sender.avatar}" class="w-full h-full rounded-full object-cover">` : getInitial(sender.nickname || sender.username)}</div>` : ''}
        <div class="message-bubble ${isSent ? 'sent' : 'received'} px-4 py-2">
          <p class="text-sm">${escapeHtml(msg.content)}</p>
          <p class="text-xs ${isSent ? 'text-white/70' : 'text-ghibli-textLight'} mt-1">${formatDate(msg.createdAt)}</p>
        </div>
      </div>
    `;
  }).join('');

  container.scrollTop = container.scrollHeight;
}

function sendMessage() {
  const input = document.getElementById('chatInput');
  const content = input.value.trim();
  if (!content) return;

  const chatId = document.getElementById('chatDetailPage').dataset.chatId;
  const chat = db.chats.find(c => c.id === chatId);
  if (!chat) return;

  chat.messages.push({
    id: generateId(),
    senderId: db.currentUser.id,
    content,
    createdAt: Date.now()
  });

  db.save();
  input.value = '';
  renderChatMessages(chat);
}
