// static/js/app.js
import { initAuthEvents } from './auth.js';

console.log('[App] Application starting...');

document.addEventListener('DOMContentLoaded', () => {
  // 初始化认证相关事件
  initAuthEvents();

  // 监听登录成功事件，可以在这里处理页面跳转或状态更新
  window.addEventListener('userLoggedIn', (e) => {
    console.log('[App] User logged in event received', e.detail);
    // 示例：如果是单页应用，这里应该加载主页模块
  });
});
