# -*- coding: utf-8 -*-
"""
WebSocket 连接管理器
用于实时推送消息到前端
"""
from typing import Dict, List, Set
from datetime import datetime
from fastapi import WebSocket
from common.utils.logging import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        # 存储所有活跃连接: {user_id: {websocket1, websocket2, ...}}
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        # 存储连接的元数据
        self.connection_metadata: Dict[WebSocket, dict] = {}

    async def connect(self, websocket: WebSocket, user_id: int, client_id: str = None):
        """
        接受新的 WebSocket 连接

        Args:
            websocket: WebSocket 连接对象
            user_id: 用户ID
            client_id: 客户端唯一标识（可选）
        """
        await websocket.accept()

        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()

        self.active_connections[user_id].add(websocket)
        self.connection_metadata[websocket] = {
            "user_id": user_id,
            "client_id": client_id,
            "connected_at": datetime.now()
        }

        logger.info(f"WebSocket 连接建立: user_id={user_id}, client_id={client_id}")

        # 发送连接成功消息
        await self.send_to_connection(websocket, {
            "type": "connected",
            "message": "WebSocket 连接成功",
            "timestamp": datetime.now().isoformat()
        })

    def disconnect(self, websocket: WebSocket):
        """断开 WebSocket 连接"""
        metadata = self.connection_metadata.get(websocket)
        if metadata:
            user_id = metadata["user_id"]
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]

            del self.connection_metadata[websocket]
            logger.info(f"WebSocket 连接断开: user_id={user_id}")

    async def send_to_connection(self, websocket: WebSocket, message: dict):
        """向单个连接发送消息"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"发送消息失败: {e}")

    async def send_to_user(self, user_id: int, message: dict):
        """向指定用户的所有连接发送消息"""
        if user_id in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.add(connection)

            # 清理断开的连接
            for conn in disconnected:
                self.disconnect(conn)

    async def broadcast(self, message: dict, exclude_user: int = None):
        """
        广播消息给所有连接

        Args:
            message: 消息内容
            exclude_user: 排除的用户ID
        """
        for user_id, connections in list(self.active_connections.items()):
            if exclude_user and user_id == exclude_user:
                continue

            disconnected = set()
            for connection in connections:
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.add(connection)

            for conn in disconnected:
                self.disconnect(conn)

    def get_online_users(self) -> List[int]:
        """获取在线用户列表"""
        return list(self.active_connections.keys())

    def get_user_connection_count(self, user_id: int) -> int:
        """获取用户的连接数"""
        return len(self.active_connections.get(user_id, set()))

    def get_total_connections(self) -> int:
        """获取总连接数"""
        return sum(len(conns) for conns in self.active_connections.values())


# 全局 WebSocket 管理器实例
ws_manager = ConnectionManager()


# ==================== 消息类型定义 ====================

class MessageType:
    """WebSocket 消息类型"""
    CONNECTED = "connected"  # 连接成功
    TEST_RUN_START = "test_run_start"  # 测试开始执行
    TEST_RUN_END = "test_run_end"  # 测试执行结束
    TEST_PROGRESS = "test_progress"  # 测试进度更新
    NOTIFICATION = "notification"  # 系统通知
    HEARTBEAT = "heartbeat"  # 心跳


async def send_test_start(user_id: int, test_case_id: int, test_case_name: str):
    """发送测试开始消息"""
    await ws_manager.send_to_user(user_id, {
        "type": MessageType.TEST_RUN_START,
        "data": {
            "test_case_id": test_case_id,
            "test_case_name": test_case_name
        },
        "timestamp": datetime.now().isoformat()
    })


async def send_test_end(user_id: int, test_case_id: int, status: str, duration: int = None):
    """发送测试结束消息"""
    await ws_manager.send_to_user(user_id, {
        "type": MessageType.TEST_RUN_END,
        "data": {
            "test_case_id": test_case_id,
            "status": status,
            "duration": duration
        },
        "timestamp": datetime.now().isoformat()
    })


async def send_test_progress(user_id: int, test_case_id: int, progress: int, message: str = ""):
    """发送测试进度消息"""
    await ws_manager.send_to_user(user_id, {
        "type": MessageType.TEST_PROGRESS,
        "data": {
            "test_case_id": test_case_id,
            "progress": progress,
            "message": message
        },
        "timestamp": datetime.now().isoformat()
    })


async def send_notification(user_id: int, title: str, content: str, level: str = "info"):
    """
    发送系统通知

    Args:
        user_id: 用户ID，如果为 None 则广播给所有用户
        title: 通知标题
        content: 通知内容
        level: 通知级别 (info/warning/error/success)
    """
    message = {
        "type": MessageType.NOTIFICATION,
        "data": {
            "title": title,
            "content": content,
            "level": level
        },
        "timestamp": datetime.now().isoformat()
    }

    if user_id:
        await ws_manager.send_to_user(user_id, message)
    else:
        await ws_manager.broadcast(message)


async def send_heartbeat(websocket: WebSocket):
    """发送心跳消息"""
    await ws_manager.send_to_connection(websocket, {
        "type": MessageType.HEARTBEAT,
        "timestamp": datetime.now().isoformat()
    })
