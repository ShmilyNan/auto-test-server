# -*- coding: utf-8 -*-
"""
FastAPI主应用
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy import text
from server.api import auth, users, roles, projects, testcases
from server.models.database import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    print("\n" + "=" * 60)
    print("🚀 启动自动化测试平台...")
    print("=" * 60)

    # 测试数据库连接
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ 数据库连接成功")
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        raise

    print("\n📚 API文档地址:")
    print("   - Swagger UI: http://localhost:8899/docs")
    print("   - ReDoc: http://localhost:8899/redoc")
    print("=" * 60 + "\n")

    yield

    # 关闭时执行
    print("\n👋 关闭服务...")


# 创建FastAPI应用
app = FastAPI(
    title="接口自动化测试平台API",
    description="测试用例管理、项目管理、用户权限管理",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, tags=["认证"])
app.include_router(users.router, tags=["用户管理"])
app.include_router(roles.router, tags=["角色权限管理"])
app.include_router(projects.router, tags=["项目管理"])
app.include_router(testcases.router, tags=["测试用例管理"])


# 根路径
@app.get("/", tags=["系统"])
def root():
    """API根路径"""
    return {
        "name": "接口自动化测试平台API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running"
    }


# 健康检查
@app.get("/health", tags=["系统"])
def health_check():
    """健康检查接口"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8899,
        reload=True,
        log_level="info"
    )
