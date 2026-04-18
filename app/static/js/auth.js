// static/js/auth.js
import { api } from './api.js';
import { showToast } from './utils.js';

console.log('[Module] auth.js loaded');

export function initAuthEvents() {
  console.log('[Auth] Initializing events...');

  // UI 元素
  const loginForm = document.getElementById('loginForm');
  const registerForm = document.getElementById('registerForm');

  // 切换表单
  document.getElementById('showRegisterLink').addEventListener('click', (e) => {
    e.preventDefault();
    loginForm.classList.add('hidden');
    registerForm.classList.remove('hidden');
  });

  document.getElementById('showLoginLink').addEventListener('click', (e) => {
    e.preventDefault();
    registerForm.classList.add('hidden');
    loginForm.classList.remove('hidden');
  });

  // 绑定登录按钮
  document.getElementById('loginBtn').addEventListener('click', handleLogin);

  // 绑定注册按钮
  document.getElementById('registerBtn').addEventListener('click', handleRegister);
}

/**
 * 处理登录逻辑
 */
async function handleLogin() {
  const usernameInput = document.getElementById('loginUsername');
  const passwordInput = document.getElementById('loginPassword');
  const btn = document.getElementById('loginBtn');

  const user_name = usernameInput.value.trim();
  const password = passwordInput.value;

  if (!user_name || !password) {
    showToast('请输入用户名和密码');
    return;
  }

  try {
    // 添加加载状态
    btn.classList.add('loading');
    btn.textContent = '登录中...';

    // 调用 API
    const response = await api.login({ user_name, password });

    // 假设后端返回 { "access_token": "...", "token_type": "bearer" }
    if (response.access_token) {
      localStorage.setItem('access_token', response.access_token);
      showToast('登录成功');

      // 触发全局事件，通知 app.js 更新状态
      window.dispatchEvent(new CustomEvent('userLoggedIn', { detail: response }));

      // 这里可以根据需要跳转页面，例如跳转到主页
      // window.location.href = '/home';
      console.log('Login successful, token saved.');
    } else {
      throw new Error('登录响应格式错误');
    }

  } catch (error) {
    showToast(`登录失败: ${error.message}`);
    console.error(error);
  } finally {
    // 移除加载状态
    btn.classList.remove('loading');
    btn.textContent = '登录';
  }
}

/**
 * 处理注册逻辑
 */
async function handleRegister() {
  const user_name = document.getElementById('regUsername').value.trim();
  const email = document.getElementById('regEmail').value.trim();
  const phone = document.getElementById('regPhone').value.trim();
  const password = document.getElementById('regPassword').value;
  const confirmPassword = document.getElementById('regConfirmPassword').value;
  const btn = document.getElementById('registerBtn');

  // 前端校验
  if (!user_name || !email || !password) {
    showToast('请填写必填项（用户名、邮箱、密码）');
    return;
  }

  if (password !== confirmPassword) {
    showToast('两次输入的密码不一致');
    return;
  }

  // 简单的邮箱格式校验
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(email)) {
    showToast('请输入有效的邮箱地址');
    return;
  }

  try {
    btn.classList.add('loading');
    btn.textContent = '注册中...';

    // 构造符合 API 要求的数据结构
    const payload = {
      user_name,
      email,
      password,
      phone: phone || "string" // 如果后端要求非空，这里处理一下空字符串
    };

    const response = await api.register(payload);

    showToast('注册成功！请登录');

    // 自动切换回登录表单
    document.getElementById('registerForm').classList.add('hidden');
    document.getElementById('loginForm').classList.remove('hidden');

    // 自动填充用户名
    document.getElementById('loginUsername').value = user_name;

  } catch (error) {
    showToast(`注册失败: ${error.message}`);
    console.error(error);
  } finally {
    btn.classList.remove('loading');
    btn.textContent = '注册';
  }
}
