// static/js/tweet.js
import { db } from './store.js';
import { showToast, escapeHtml, renderMarkdown, truncateText, getAvatarColor, getInitial, formatDate } from './utils.js';
import { showPage } from './app.js';

export function initTweetEvents() {
  // 发布推文
  document.getElementById('publishTweetBtn').addEventListener('click', publishTweet);

  // Markdown工具栏
  document.getElementById('mdToolbar').addEventListener('click', (e) => {
    const btn = e.target.closest('button');
    if (btn && btn.dataset.md) {
      insertMarkdown(btn.dataset.md, btn.dataset.md); // 简单处理，前后一致
    }
  });

  // 搜索
  document.getElementById('searchInput').addEventListener('input', (e) => {
    renderTweets(e.target.value.trim());
  });

  // 编辑模态框事件
  document.getElementById('closeEditModalOverlay').addEventListener('click', closeEditModal);
  document.getElementById('cancelEditBtn').addEventListener('click', closeEditModal);
  document.getElementById('saveEditBtn').addEventListener('click', saveEditTweet);
}

function insertMarkdown(before, after) {
  const textarea = document.getElementById('tweetInput');
  const start = textarea.selectionStart;
  const end = textarea.selectionEnd;
  const text = textarea.value;
  const selected = text.substring(start, end);
  textarea.value = text.substring(0, start) + before + selected + after + text.substring(end);
  textarea.focus();
}

function publishTweet() {
  const content = document.getElementById('tweetInput').value.trim();
  if (!content) {
    showToast('请输入推文内容');
    return;
  }

  const tweet = {
    id: generateId(),
    authorId: db.currentUser.id,
    authorName: db.currentUser.nickname || db.currentUser.username,
    authorAvatar: db.currentUser.avatar,
    authorUsername: db.currentUser.username,
    content,
    likes: [],
    createdAt: Date.now()
  };

  db.tweets.unshift(tweet);
  db.save();

  document.getElementById('tweetInput').value = '';
  showToast('发布成功');
  renderTweets();
}

export function renderTweets(searchQuery = '') {
  const container = document.getElementById('tweetList');
  let tweets = db.tweets;

  if (searchQuery) {
    const query = searchQuery.toLowerCase();
    tweets = tweets.filter(t =>
      t.content.toLowerCase().includes(query) ||
      t.authorName.toLowerCase().includes(query)
    );
  }

  if (tweets.length === 0) {
    container.innerHTML = `<div class="text-center py-12 text-ghibli-textLight"><i class="fas fa-feather-alt text-4xl mb-4 opacity-50"></i><p>${searchQuery ? '没有找到相关推文' : '还没有推文，来发布第一条吧'}</p></div>`;
    return;
  }

  container.innerHTML = tweets.map(tweet => {
    const isOwner = db.currentUser && tweet.authorId === db.currentUser.id;
    const isLiked = db.currentUser && tweet.likes.includes(db.currentUser.id);
    const comments = db.comments.filter(c => c.tweetId === tweet.id);
    const { text: displayText, truncated } = truncateText(tweet.content);
    const avatarColor = getAvatarColor(tweet.authorUsername);
    const avatarInitial = getInitial(tweet.authorName);

    return `
      <div class="ghibli-card rounded-2xl p-4">
        <div class="flex items-start gap-3">
          <div onclick="window.openChat('${tweet.authorId}')" class="w-10 h-10 rounded-full flex items-center justify-center text-white font-bold flex-shrink-0 cursor-pointer" style="background-color: ${avatarColor}">
            ${tweet.authorAvatar ? `<img src="${tweet.authorAvatar}" class="w-full h-full rounded-full object-cover">` : avatarInitial}
          </div>
          <div class="flex-1 min-w-0">
            <div class="flex items-center justify-between mb-1">
              <div class="flex items-center gap-2">
                <span class="font-medium text-ghibli-text">${escapeHtml(tweet.authorName)}</span>
                <span class="text-xs text-ghibli-textLight">@${escapeHtml(tweet.authorUsername)}</span>
              </div>
              ${isOwner ? `
                <div class="flex gap-2">
                  <button onclick="window.openEditModal('${tweet.id}')" class="text-ghibli-textLight hover:text-ghibli-forest text-sm"><i class="fas fa-edit"></i></button>
                  <button onclick="window.deleteTweet('${tweet.id}')" class="text-ghibli-textLight hover:text-red-500 text-sm"><i class="fas fa-trash"></i></button>
                </div>
              ` : ''}
            </div>
            <div class="markdown-content text-ghibli-text text-sm mb-2" id="content-${tweet.id}">
              ${renderMarkdown(truncated ? displayText : tweet.content)}
            </div>
            ${truncated ? `<button onclick="window.expandTweet('${tweet.id}')" class="text-ghibli-forest text-sm font-medium hover:underline">展开全文</button>` : ''}
            <div class="flex items-center gap-6 mt-3 pt-3 border-t border-ghibli-forest/10">
              <button onclick="window.toggleLike('${tweet.id}')" class="flex items-center gap-1 text-sm ${isLiked ? 'text-red-400' : 'text-ghibli-textLight'} hover:text-red-400 transition-colors">
                <i class="fas fa-heart"></i><span>${tweet.likes.length || ''}</span>
              </button>
              <button onclick="window.openTweetDetail('${tweet.id}')" class="flex items-center gap-1 text-sm text-ghibli-textLight hover:text-ghibli-forest transition-colors">
                <i class="fas fa-comment"></i><span>${comments.length || ''}</span>
              </button>
              <span class="text-xs text-ghibli-textLight ml-auto">${formatDate(tweet.createdAt)}</span>
            </div>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

// 暴露给全局HTML调用的函数
window.expandTweet = (tweetId) => {
  const tweet = db.tweets.find(t => t.id === tweetId);
  if (!tweet) return;
  const contentEl = document.getElementById(`content-${tweetId}`);
  contentEl.innerHTML = renderMarkdown(tweet.content);
  const btn = contentEl.nextElementSibling;
  if (btn && btn.textContent === '展开全文') btn.remove();
};

window.toggleLike = (tweetId) => {
  if (!db.currentUser) { showToast('请先登录'); return; }
  const tweet = db.tweets.find(t => t.id === tweetId);
  if (!tweet) return;

  const userId = db.currentUser.id;
  const index = tweet.likes.indexOf(userId);
  if (index > -1) tweet.likes.splice(index, 1);
  else tweet.likes.push(userId);

  db.save();
  renderTweets();
};

window.openEditModal = (tweetId) => {
  const tweet = db.tweets.find(t => t.id === tweetId);
  if (!tweet) return;
  document.getElementById('editTweetContent').value = tweet.content;
  document.getElementById('editModal').dataset.tweetId = tweetId;
  document.getElementById('editModal').classList.remove('hidden');
};

function closeEditModal() {
  document.getElementById('editModal').classList.add('hidden');
}

function saveEditTweet() {
  const tweetId = document.getElementById('editModal').dataset.tweetId;
  const content = document.getElementById('editTweetContent').value.trim();
  if (!content) { showToast('推文内容不能为空'); return; }

  const tweet = db.tweets.find(t => t.id === tweetId);
  if (tweet) {
    tweet.content = content;
    db.save();
    showToast('修改成功');
    closeEditModal();
    renderTweets();
  }
}

window.deleteTweet = (tweetId) => {
  if (!confirm('确定要删除这条推文吗？')) return;
  const index = db.tweets.findIndex(t => t.id === tweetId);
  if (index > -1) {
    db.tweets.splice(index, 1);
    db.comments = db.comments.filter(c => c.tweetId !== tweetId);
    db.save();
    showToast('删除成功');
    renderTweets();
  }
};

window.openTweetDetail = (tweetId) => {
  const tweet = db.tweets.find(t => t.id === tweetId);
  if (!tweet) return;

  const comments = db.comments.filter(c => c.tweetId === tweetId);
  const isLiked = db.currentUser && tweet.likes.includes(db.currentUser.id);
  const avatarColor = getAvatarColor(tweet.authorUsername);
  const avatarInitial = getInitial(tweet.authorName);

  const container = document.getElementById('tweetDetailContent');
  container.innerHTML = `
    <div class="ghibli-card rounded-2xl p-4 mb-4">
      <div class="flex items-start gap-3">
        <div class="w-12 h-12 rounded-full flex items-center justify-center text-white font-bold" style="background-color: ${avatarColor}">
          ${tweet.authorAvatar ? `<img src="${tweet.authorAvatar}" class="w-full h-full rounded-full object-cover">` : avatarInitial}
        </div>
        <div class="flex-1">
          <div class="flex items-center gap-2 mb-1">
            <span class="font-medium text-ghibli-text">${escapeHtml(tweet.authorName)}</span>
            <span class="text-xs text-ghibli-textLight">@${escapeHtml(tweet.authorUsername)}</span>
          </div>
          <div class="markdown-content text-ghibli-text mb-3">${renderMarkdown(tweet.content)}</div>
          <div class="text-xs text-ghibli-textLight">${formatDate(tweet.createdAt)}</div>
          <div class="flex items-center gap-6 mt-3 pt-3 border-t border-ghibli-forest/10">
            <button onclick="window.toggleLikeDetail('${tweet.id}')" class="flex items-center gap-1 text-sm ${isLiked ? 'text-red-400' : 'text-ghibli-textLight'}">
              <i class="fas fa-heart"></i><span>${tweet.likes.length}</span>
            </button>
            <span class="text-sm text-ghibli-textLight"><i class="fas fa-comment"></i> ${comments.length}</span>
          </div>
        </div>
      </div>
    </div>

    <div class="ghibli-card rounded-2xl p-4 mb-4">
      <div class="flex items-start gap-3">
        <div class="w-8 h-8 rounded-full bg-ghibli-forest flex items-center justify-center text-white text-sm font-bold flex-shrink-0">
          ${db.currentUser && db.currentUser.avatar ? `<img src="${db.currentUser.avatar}" class="w-full h-full rounded-full object-cover">` : getInitial(db.currentUser?.nickname || 'U')}
        </div>
        <div class="flex-1">
          <textarea id="commentInput" class="ghibli-input w-full px-3 py-2 rounded-xl text-sm resize-none" rows="2" placeholder="写下你的评论..."></textarea>
          <div class="flex justify-end mt-2">
            <button onclick="window.postComment('${tweetId}')" class="ghibli-btn px-4 py-2 rounded-xl text-sm font-medium">发表评论</button>
          </div>
        </div>
      </div>
    </div>

    <div class="mb-4">
      <h3 class="font-medium text-ghibli-forest mb-3">评论 (${comments.length})</h3>
      <div class="space-y-3">
        ${comments.length === 0 ? `<div class="text-center py-8 text-ghibli-textLight"><p class="text-sm">还没有评论</p></div>` :
          comments.map(c => `
            <div class="ghibli-card rounded-xl p-3">
              <div class="flex items-start gap-2">
                <div class="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold" style="background-color: ${getAvatarColor(c.authorUsername)}">
                  ${c.authorAvatar ? `<img src="${c.authorAvatar}" class="w-full h-full rounded-full object-cover">` : getInitial(c.authorName)}
                </div>
                <div class="flex-1">
                  <div class="flex justify-between">
                    <span class="font-medium text-sm text-ghibli-text">${escapeHtml(c.authorName)}</span>
                    <span class="text-xs text-ghibli-textLight">${formatDate(c.createdAt)}</span>
                  </div>
                  <div class="markdown-content text-sm text-ghibli-text mt-1">${renderMarkdown(c.content)}</div>
                </div>
              </div>
            </div>
          `).join('')
        }
      </div>
    </div>
  `;
  showPage('tweetDetailPage');
};

window.postComment = (tweetId) => {
  const content = document.getElementById('commentInput').value.trim();
  if (!content) { showToast('请输入评论内容'); return; }

  const comment = {
    id: generateId(),
    tweetId,
    authorId: db.currentUser.id,
    authorName: db.currentUser.nickname || db.currentUser.username,
    authorAvatar: db.currentUser.avatar,
    authorUsername: db.currentUser.username,
    content,
    createdAt: Date.now()
  };

  db.comments.push(comment);
  db.save();
  showToast('评论成功');
  window.openTweetDetail(tweetId); // 重新渲染详情页
};
