// static/js/api.js

// 配置后端 API 基础地址，根据实际情况修改
const BASE_URL = 'http://localhost:8002/api/v1';

/**
 * 封装 fetch 请求
 */
async function request(url, method = 'GET', data = null) {
  const options = {
    method,
    headers: {
      'Content-Type': 'application/json',
    },
  };

  // 如果本地有 token，携带在 header 中
  const token = localStorage.getItem('access_token');
  if (token) {
    options.headers['Authorization'] = `Bearer ${token}`;
  }

  if (data) {
    options.body = JSON.stringify(data);
  }

  try {
    const response = await fetch(`${BASE_URL}${url}`, options);

    // 处理 HTTP 错误
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      // FastAPI 通常返回 { "detail": "错误信息" }
      throw new Error(errorData.detail || `请求失败: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('[API Error]', error);
    throw error;
  }
}

export const api = {
  // 用户注册
  register(userData) {
    // userData: { user_name, email, phone, password }
    return request('/users/', 'POST', userData);
  },

  // 用户登录
  // 注意：这里假设后端接收 user_name 和 password
  // 如果后端是用 OAuth2PasswordRequestForm，则需要发送 form-data，这里假设是 JSON
  login(credentials) {
    // credentials: { user_name, password }
    return request('/users/login', 'POST', credentials);
  },

  // 获取当前用户信息 (示例)
  getCurrentUser() {
    return request('/users/me', 'GET');
  }
};
