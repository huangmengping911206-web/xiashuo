import json
import pytest
from websocket import create_connection

# 测试配置
WS_URL = "ws://127.0.0.1:8002/api/v2/chat/ws"
MESSAGE_TEMPLATE = {
    "action": "send_message",
    "data": {
        "conversation_id": 1,
        "content": "test  string，今晚吃什么？",
        "type": "text"
    }
}

@pytest.fixture
def user_connection():
    """
    返回一个函数，用于根据 user_cookie 创建 WebSocket 连接。
    使用 yield 确保测试结束后关闭连接。
    """
    connections = []  # 记录所有创建的连接，方便统一清理

    def _make_connection(cookie_str):
        ws = create_connection(
            WS_URL,
            header={"Cookie": cookie_str}  # 关键：传递 Cookie
        )
        connections.append(ws)
        return ws

    yield _make_connection

    # 测试结束后关闭所有连接
    for conn in connections:
        conn.close()


def test_single_user_message(user_connection):
    """测试单个用户发送消息"""
    cookie = 'access_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjo2LCJ1c2VyX25hbWUiOiJ0ZXN0IiwiWC1DU1Atbm9uY2UiOiJsRkhqYzNJbXp3NGs0aUY3Zm5OMml3IiwiZXhwIjoxNzcyOTUyNTYyfQ.n6hAFgQ77OvfvUkB8YhdZ47YJQSMmvm8XIjtNFe6n9w'
    ws = user_connection(cookie)

    # 发送消息
    ws.send(json.dumps(MESSAGE_TEMPLATE))

    # 可选：接收并验证服务器响应（根据实际协议调整）
    response = ws.recv()
    data = json.loads(response)
    print(data)
    assert data.get("status") == "ok"  # 假设服务器返回 {"status": "ok"}