// static/js/store.js
// 修复：移除未使用的 generateId 导入，避免依赖错误

console.log('[Module] store.js loaded');

const STORAGE_KEYS = {
  USERS: 'ghibli_users',
  TWEETS: 'ghibli_tweets',
  COMMENTS: 'ghibli_comments',
  CHATS: 'ghibli_chats',
  CURRENT_USER: 'ghibli_currentUser'
};

const sampleData = {
  users: [
    { id: 'user1', username: 'totoro', nickname: '龙猫', password: '123456', avatar: null, createdAt: Date.now() },
    { id: 'user2', username: 'chihiro', nickname: '千寻', password: '123456', avatar: null, createdAt: Date.now() },
    { id: 'user3', username: 'howl', nickname: '哈尔', password: '123456', avatar: null, createdAt: Date.now() }
  ],
  tweets: [
    {
      id: 'tweet1', authorId: 'user1', authorName: '龙猫', authorAvatar: null, authorUsername: 'totoro',
      content: '今天在森林里发现了一个神奇的地方！\n\n**这里有好多橡果子**，还有一把破旧的雨伞。',
      likes: ['user2', 'user3'], createdAt: Date.now() - 3600000
    },
    {
      id: 'tweet2', authorId: 'user2', authorName: '千寻', authorAvatar: null, authorUsername: 'chihiro',
      content: '在油屋工作已经有一段时间了。\n\n虽然很累，但我学会了很多事情。',
      likes: ['user1'], createdAt: Date.now() - 7200000
    }
  ],
  comments: [
    { id: 'com1', tweetId: 'tweet1', authorId: 'user2', authorName: '千寻', authorAvatar: null, authorUsername: 'chihiro', content: '龙猫先生，下次带我去！', createdAt: Date.now() - 1800000 }
  ],
  chats: []
};

class Store {
  constructor() {
    console.log('[Store] Initializing...');
    this.users = this.load(STORAGE_KEYS.USERS);
    this.tweets = this.load(STORAGE_KEYS.TWEETS);
    this.comments = this.load(STORAGE_KEYS.COMMENTS);
    this.chats = this.load(STORAGE_KEYS.CHATS);
    this.currentUser = this.load(STORAGE_KEYS.CURRENT_USER);

    if (this.users.length === 0) {
      console.log('[Store] No data found, initializing sample data.');
      this.users = sampleData.users;
      this.tweets = sampleData.tweets;
      this.comments = sampleData.comments;
      this.chats = sampleData.chats;
      this.save();
    } else {
      console.log('[Store] Data loaded from localStorage.', this.users.length, 'users found.');
    }
  }

  load(key) {
    try {
      const data = localStorage.getItem(key);
      return data ? JSON.parse(data) : [];
    } catch (e) {
      console.error('[Store] Error loading key:', key, e);
      return [];
    }
  }

  save() {
    try {
      localStorage.setItem(STORAGE_KEYS.USERS, JSON.stringify(this.users));
      localStorage.setItem(STORAGE_KEYS.TWEETS, JSON.stringify(this.tweets));
      localStorage.setItem(STORAGE_KEYS.COMMENTS, JSON.stringify(this.comments));
      localStorage.setItem(STORAGE_KEYS.CHATS, JSON.stringify(this.chats));
      localStorage.setItem(STORAGE_KEYS.CURRENT_USER, JSON.stringify(this.currentUser));
    } catch (e) {
      console.error('[Store] Error saving data:', e);
    }
  }
}

export const db = new Store();
