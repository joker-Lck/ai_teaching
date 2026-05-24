"""
WebSocket 端点 - 实时通信
支持课件生成进度推送、实时聊天等场景
"""
import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, List

from core.logger import info, warning

router = APIRouter()


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room: str):
        await websocket.accept()
        if room not in self.active_connections:
            self.active_connections[room] = []
        self.active_connections[room].append(websocket)
        info(f"WebSocket 连接加入房间: {room}, 当前连接数: {len(self.active_connections[room])}")

    def disconnect(self, websocket: WebSocket, room: str):
        if room in self.active_connections:
            if websocket in self.active_connections[room]:
                self.active_connections[room].remove(websocket)
            if not self.active_connections[room]:
                del self.active_connections[room]
        info(f"WebSocket 断开连接, 房间: {room}")

    async def send_to_room(self, room: str, message: dict):
        """向房间内所有连接发送消息"""
        if room in self.active_connections:
            disconnected = []
            for connection in self.active_connections[room]:
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.append(connection)

            # 清理断开的连接
            for conn in disconnected:
                self.disconnect(conn, room)

    async def send_personal(self, websocket: WebSocket, message: dict):
        """向单个连接发送消息"""
        try:
            await websocket.send_json(message)
        except Exception:
            pass


manager = ConnectionManager()


@router.websocket("/generation/{client_id}")
async def generation_progress(websocket: WebSocket, client_id: str):
    """课件生成进度 WebSocket

    客户端连接后, 服务端推送课件生成的实时进度。

    消息格式:
    - 服务端 -> 客户端: {"step": 1, "total": 3, "message": "...", "progress": 30}
    - 服务端 -> 客户端: {"type": "done", "slides": [...], "progress": 100}
    - 服务端 -> 客户端: {"type": "error", "message": "..."}
    """
    room = f"generation_{client_id}"
    await manager.connect(websocket, room)

    try:
        while True:
            # 保持连接, 等待客户端消息 (心跳)
            data = await websocket.receive_text()

            if data == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(websocket, room)
    except Exception as e:
        warning(f"WebSocket 异常: {str(e)}")
        manager.disconnect(websocket, room)


@router.websocket("/chat/{room_id}")
async def chat_room(websocket: WebSocket, room_id: str):
    """实时聊天 WebSocket

    支持多用户在同一房间内实时通信。
    适用于课堂互动、小组讨论等场景。

    消息格式:
    - 客户端 -> 服务端: {"type": "message", "content": "...", "username": "..."}
    - 服务端 -> 客户端: {"type": "message", "content": "...", "username": "...", "timestamp": "..."}
    """
    room = f"chat_{room_id}"
    await manager.connect(websocket, room)

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            # 广播消息到房间
            from datetime import datetime
            broadcast_msg = {
                "type": "message",
                "content": message.get("content", ""),
                "username": message.get("username", "匿名"),
                "timestamp": datetime.now().strftime("%H:%M:%S"),
            }
            await manager.send_to_room(room, broadcast_msg)

    except WebSocketDisconnect:
        manager.disconnect(websocket, room)
        # 通知其他人
        await manager.send_to_room(room, {
            "type": "system",
            "message": "有用户离开了聊天室",
        })
    except Exception as e:
        warning(f"聊天 WebSocket 异常: {str(e)}")
        manager.disconnect(websocket, room)


@router.websocket("/voice/{client_id}")
async def voice_stream(websocket: WebSocket, client_id: str):
    """语音流 WebSocket

    接收客户端的语音数据, 进行实时处理。
    """
    room = f"voice_{client_id}"
    await manager.connect(websocket, room)

    try:
        while True:
            data = await websocket.receive_bytes()
            # 处理语音数据 (后续集成语音识别)
            await websocket.send_json({
                "type": "ack",
                "message": "语音数据已接收",
                "size": len(data),
            })

    except WebSocketDisconnect:
        manager.disconnect(websocket, room)
    except Exception as e:
        warning(f"语音 WebSocket 异常: {str(e)}")
        manager.disconnect(websocket, room)
