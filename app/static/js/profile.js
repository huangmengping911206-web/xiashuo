// static/js/profile.js
import { db } from './store.js';
import { showToast, renderMarkdown, getAvatarColor, getInitial, formatDate } from './utils.js';

export function initProfileEvents() {
  document.getElementById('updateProfileBtn').addEventListener('click', updateProfile);

  // 头像上传
  document.getElementById('avatarUploadTrigger').addEventListener('click', () => {
    document.getElementById('avatarInput').click();
  });

  document.getElementById('avatarInput').addEventListener('change', handleAvatarChange);
}

export function renderProfile() {
  if (!db.currentUser) return;

  const avatarColor = getAvatarColor(db.currentUser.username);
  const avatarInitial = getInitial(db.currentUser.nickname || db.currentUser.username);

  const avatarEl = document.getElementById('profileAvatar');
  avatarEl.style.backgroundColor = db.currentUser.avatar ? 'transparent' : avatarColor;
  avatarEl.innerHTML = db.currentUser.avatar
    ? `<img src="${db.currentUser.avatar}" class="w-full h-full rounded-full object-cover">`
    : avatarInitial;

  document.getElementById('profileNickname').value = db.currentUser.nickname || '';

  const myTweets = db.tweets.filter(t => t.authorId === db.currentUser.id);
  const myComments = db.comments.filter(c => c.authorId === db.currentUser.id);
  const totalLikes = myTweets.reduce((sum, t) => sum + t.likes.length, 0);

  document.getElementById('tweetCount').textContent = myTweets.length;
  document.getElementById('commentCount').textContent = myComments.length;
  document.getElementById('likeCount').textContent = totalLikes;

  const container = document.getElementById('myTweets');
  if (myTweets.length === 0) {
    container.innerHTML = `<div class="text-center py-8 text-ghibli-textLight"><p class="text-sm">还没有发布推文</p></div>`;
    return;
  }

  container.innerHTML = myTweets.map(tweet => {
    const comments = db.comments.filter(c => c.tweetId === tweet.id);
    return `
      <div class="ghibli-card rounded-xl p-4">
        <div class="markdown-content text-ghibli-text text-sm mb-2">${renderMarkdown(tweet.content)}</div>
        <div class="flex items-center justify-between text-xs text-ghibli-textLight">
          <div class="flex items-center gap-4">
            <span><i class="fas fa-heart"></i> ${tweet.likes.length}</span>
            <span><i class="fas fa-comment"></i> ${comments.length}</span>
          </div>
          <span>${formatDate(tweet.createdAt)}</span>
        </div>
      </div>
    `;
  }).join('');
}

function handleAvatarChange(event) {
  const file = event.target.files[0];
  if (!file) return;

  if (file.size > 1024 * 1024) {
    showToast('图片大小不能超过1MB');
    return;
  }

  const reader = new FileReader();
  reader.onload = function(e) {
    db.currentUser.avatar = e.target.result;
    const userIndex = db.users.findIndex(u => u.id === db.currentUser.id);
    if (userIndex > -1) db.users[userIndex].avatar = e.target.result;

    db.tweets.forEach(t => { if (t.authorId === db.currentUser.id) t.authorAvatar = e.target.result; });
    db.comments.forEach(c => { if (c.authorId === db.currentUser.id) c.authorAvatar = e.target.result; });

    db.save();
    renderProfile();
    showToast('头像更新成功');
  };
  reader.readAsDataURL(file);
}

function updateProfile() {
  const nickname = document.getElementById('profileNickname').value.trim();
  if (!nickname) {
    showToast('昵称不能为空');
    return;
  }

  db.currentUser.nickname = nickname;
  const userIndex = db.users.findIndex(u => u.id === db.currentUser.id);
  if (userIndex > -1) db.users[userIndex].nickname = nickname;

  db.tweets.forEach(t => { if (t.authorId === db.currentUser.id) t.authorName = nickname; });
  db.comments.forEach(c => { if (c.authorId === db.currentUser.id) c.authorName = nickname; });

  db.save();
  showToast('修改成功');
  renderProfile();
}
