from fastapi import WebSocket
from typing import Dict, List


class ConnectionManager:
    def __init__(self):
        # 结构: { user_id: [websocket1, websocket2] } 支持多端登录
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_personal_message(self, message: dict, user_id: int):
        """向特定用户的所有连接发送消息"""
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                print('推送', message)
                await connection.send_json(message)

    async def broadcast_to_conversation(self, conversation_id: int, message: dict, member_ids: List[int]):
        """向会话内的所有在线成员发送消息"""
        for user_id in member_ids:
            await self.send_personal_message(message, user_id)

manager = ConnectionManager()
