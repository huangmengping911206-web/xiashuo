/**
 * WebSocket 管理工具
 * 独立运行，挂载在 window 上，不混入 Alpine 状态
 */
window.WS = {
    socket: null,
    isConnected: false,

    // 建立连接
    connect(token) {
        // 防止重复连接
        if (this.socket && this.socket.readyState === WebSocket.OPEN) return;

        const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        const url = `${protocol}//${location.host}/api/v2/chat/ws`;

        console.log('[WS] 正在连接...', url);
        this.socket = new WebSocket(url);

        this.socket.onopen = () => {
            console.log('[WS] 连接成功');
            this.isConnected = true;

            // 触发全局事件，通知 Alpine 业务层
            window.dispatchEvent(new CustomEvent('ws-connected'));
        };

        this.socket.onmessage = (event) => {
            console.log('[WS] 收到消息:', event.data);
            try {
                const msg = JSON.parse(event.data);
                // 触发全局事件，携带数据
                window.dispatchEvent(new CustomEvent('ws-message', { detail: msg }));
            } catch (e) {
                console.error('[WS] 解析失败', e);
            }
        };

        this.socket.onclose = () => {
            console.log('[WS] 连接断开');
            this.isConnected = false;
            // 可选：简单重连逻辑
            setTimeout(() => this.connect(token), 3000);
        };

        this.socket.onerror = (err) => {
            console.error('[WS] 错误', err);
        };
    },

    // 发送消息
    send(data) {
        if (!this.isConnected) {
            console.warn('[WS] 未连接，无法发送');
            return false;
        }
        const jsonStr = JSON.stringify(data);
        console.log('[WS] 发送数据:', jsonStr);
        this.socket.send(jsonStr);
        return true;
    }
};
