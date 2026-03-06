# -*- coding: utf-8 -*-
"""
FastAPI主应用
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from server.models.database import init_db
from server.models.init_db import init_database
from server.api import auth, users, roles, projects, testcases


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    print("\n" + "=" * 60)
    print("🚀 启动测试平台API服务...")
    print("=" * 60)

    # 初始化数据库
    print("\n📦 初始化数据库...")
    init_db()

    # 初始化默认数据
    print("\n🔧 初始化默认数据...")
    init_database()

    print("\n" + "=" * 60)
    print("✅ API服务启动成功")
    print("=" * 60)
    print("\n📚 API文档地址:")
    print("   - Swagger UI: http://localhost:5000/docs")
    print("   - ReDoc: http://localhost:5000/redoc")
    print("=" * 60 + "\n")

    yield

    # 关闭时执行
    print("\n👋 关闭API服务...")


# 创建FastAPI应用
app = FastAPI(
    title="接口自动化测试平台API",
    description="提供测试用例管理、项目管理、用户权限管理等功能的RESTful API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置CORS（允许前端跨域访问）
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
        port=5000,
        reload=True,
        log_level="info"
    )
