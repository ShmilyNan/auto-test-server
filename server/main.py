# -*- coding: utf-8 -*-
"""
FastAPI 主应用
"""
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy import text
from server.infrastructure.persistence.database import engine
from server.interfaces.http.api import auth, users, roles, projects, testcases
from server.interfaces.ws.websocket import ws_manager, send_heartbeat
from server.auth.auth import get_current_user_from_token, validate_secret_key
from common.config import get_env_str
from common.utils.logging import get_logger, init_logging

init_logging()
logger = get_logger(__name__)


def get_cors_config() -> tuple[list[str], str | None, bool]:
    """根据环境变量生成CORS配置，避免通配符与凭据冲突"""
    origins_raw = get_env_str("CORS_ORIGINS", "")

    # 未配置时保持兼容性：允许全部来源，但不允许凭据
    if not origins_raw:
        return [], r".*", True

    origins = [origin.strip() for origin in origins_raw.split(",") if origin.strip()]
    if not origins:
        return [], r".*", True

    # 显式配置白名单来源时，允许凭据
    return origins, None, True

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    validate_secret_key()
    logger.info("=" * 60)
    logger.info("🚀 启动接口自动化测试平台...")
    logger.info("=" * 60)

    # 测试数据库连接
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ 数据库连接成功")
    except Exception as e:
        logger.exception(f"❌ 数据库连接失败: {e}")
        raise

    logger.info("📚 API 文档:")
    logger.info("   - Swagger UI: http://localhost:8899/docs")
    logger.info("   - ReDoc:      http://localhost:8899/redoc")
    logger.info("🔌 WebSocket:")
    logger.info("   - ws://localhost:5000/ws")
    logger.info("=" * 60 + "\n")

    yield

    logger.info("👋 关闭服务...")


# 创建 FastAPI 应用
cors_origins, cors_origins_regex, cors_allow_credentials = get_cors_config()

app = FastAPI(
    title="接口自动化测试平台 API",
    description="测试用例管理、项目管理、用户权限管理、WebSocket 实时推送",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=cors_origins_regex,
    allow_credentials=cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, tags=["认证"])
app.include_router(users.router, tags=["用户管理"])
app.include_router(roles.router, tags=["角色权限管理"])
app.include_router(projects.router, tags=["项目管理"])
app.include_router(testcases.router, tags=["测试用例管理"])


# ==================== 系统接口 ====================

@app.get("/", tags=["系统"])
def root():
    """API 根路径"""
    return {
        "name": "接口自动化测试平台 API",
        "version": "1.0.0",
        "docs": "/docs",
        "ws_url": "/ws",
        "status": "running"
    }


@app.get("/health", tags=["系统"])
def health_check():
    """健康检查"""
    return {"status": "healthy"}


@app.get("/ws_url", tags=["系统"])
def get_websocket_url():
    """
    获取 WebSocket 连接地址

    返回前端需要连接的 WebSocket URL
    """
    host = get_env_str("SERVER_HOST", "localhost")
    port = get_env_str("SERVER_PORT", "5000")

    return {
        "ws_url": f"ws://{host}:{port}/ws",
        "ws_url_secure": f"wss://{host}:{port}/ws" if get_env_str("HTTPS") else None,
        "message_types": {
            "connected": "连接成功",
            "test_run_start": "测试开始执行",
            "test_run_end": "测试执行结束",
            "test_progress": "测试进度更新",
            "notification": "系统通知",
            "heartbeat": "心跳"
        }
    }


# ==================== WebSocket 接口 ====================

@app.websocket("/ws")
async def websocket_endpoint(
        websocket: WebSocket,
        token: str = Query(..., description="JWT Token 用于身份验证")
):
    """
    WebSocket 实时推送端点

    连接方式:
        ws://host:port/ws?token=YOUR_JWT_TOKEN

    消息格式:
        {
            "type": "message_type",
            "data": {...},
            "timestamp": "2024-01-01T12:00:00"
        }

    消息类型:
        - connected: 连接成功确认
        - test_run_start: 测试开始执行
        - test_run_end: 测试执行结束
        - test_progress: 测试进度更新
        - notification: 系统通知
        - heartbeat: 心跳（每30秒）
    """
    # 验证 Token
    try:
        user = get_current_user_from_token(token)
        user_id = user.id
    except Exception as e:
        await websocket.close(code=4001, reason=f"认证失败: {str(e)}")
        return

    # 建立连接
    await ws_manager.connect(websocket, user_id)

    try:
        # 启动心跳任务
        heartbeat_task = asyncio.create_task(heartbeat_loop(websocket))

        while True:
            # 接收客户端消息
            data = await websocket.receive_json()

            # 处理客户端发来的心跳响应
            if data.get("type") == "pong":
                continue

            # 其他消息处理（可根据需要扩展）
            await ws_manager.send_to_connection(websocket, {
                "type": "echo",
                "data": data,
                "timestamp": datetime.now().isoformat()
            })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.exception(f"WebSocket 错误: {e}")
    finally:
        heartbeat_task.cancel()
        ws_manager.disconnect(websocket)


async def heartbeat_loop(websocket: WebSocket):
    """心跳循环，每30秒发送一次心跳"""
    while True:
        try:
            await asyncio.sleep(30)
            await send_heartbeat(websocket)
        except asyncio.CancelledError:
            break
        except Exception:
            break


# 需要导入 datetime
from datetime import datetime


# ==================== WebSocket 状态接口 ====================

@app.get("/ws/status", tags=["系统"])
def get_websocket_status():
    """获取 WebSocket 连接状态"""
    return {
        "total_connections": ws_manager.get_total_connections(),
        "online_users": ws_manager.get_online_users(),
        "connections_per_user": {
            str(user_id): ws_manager.get_user_connection_count(user_id)
            for user_id in ws_manager.get_online_users()
        }
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "server.main:app",
        host="0.0.0.0",
        port=8899,
        reload=True,
        log_level="info"
    )
