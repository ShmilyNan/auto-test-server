"""
数据清洗管理器
支持通过 API 和 SQL 删除测试数据
"""

from typing import Dict, Any, Optional, List
from loguru import logger

from src.core.client import create_client
from src.core.context import get_context


class DataCleaner:
    """
    数据清洗管理器

    支持两种清洗方式：
    1. API 清洗：调用删除接口删除数据
    2. SQL 清洗：执行 SQL 语句删除数据

    使用示例：
    ```python
    cleaner = DataCleaner()

    # API 清洗
    cleanup_config = {
        'enabled': True,
        'type': 'api',
        'api': {
            'method': 'DELETE',
            'url': '/api/users/${$extract.user_id}',
            'headers': {
                'Authorization': 'Bearer ${$extract.access_token}'
            }
        }
    }
    cleaner.cleanup(cleanup_config)

    # SQL 清洗
    cleanup_config = {
        'enabled': True,
        'type': 'sql',
        'sql': {
            'connection': 'default',
            'statement': 'DELETE FROM users WHERE id = ${extract.user_id}'
        }
    }
    cleaner.cleanup(cleanup_config)
    ```
    """

    def __init__(self):
        """初始化数据清洗管理器"""
        self.http_client = None
        self.db_connections: Dict[str, Any] = {}

    def cleanup(self, cleanup_config: Dict[str, Any]) -> bool:
        """
        执行数据清洗
        Args:
            cleanup_config: 清洗配置
                - enabled: 是否启用清洗
                - type: 清洗类型 (api/sql)
                - api: API 清洗配置
                - sql: SQL 清洗配置
        Returns:
            bool: 清洗是否成功
        """
        # 检查是否启用清洗
        if not cleanup_config.get('enabled', False):
            logger.debug("数据清洗未启用，跳过")
            return True

        cleanup_type = cleanup_config.get('type', 'api')

        try:
            if cleanup_type == 'api':
                return self._cleanup_by_api(cleanup_config.get('api', {}))
            elif cleanup_type == 'sql':
                return self._cleanup_by_sql(cleanup_config.get('sql', {}))
            else:
                logger.error(f"不支持的清洗类型: {cleanup_type}")
                return False
        except Exception as e:
            logger.error(f"数据清洗失败: {str(e)}")
            return False

    def _cleanup_by_api(self, api_config: Dict[str, Any]) -> bool:
        """
        通过 API 删除数据
        Args:
            api_config: API 配置
                - method: 请求方法 (GET/POST/PUT/DELETE)
                - url: 请求URL
                - headers: 请求头
                - params: URL参数
                - body: 请求体
        Returns:
            bool: 删除是否成功
        """
        logger.info("开始通过 API 清洗数据")

        # 获取上下文
        context = get_context()

        # 替换变量
        url = context.replace_vars(api_config.get('url', ''))
        method = api_config.get('method', 'DELETE').upper()
        headers = context.replace_vars_dict(api_config.get('headers', {}))
        params = context.replace_vars_dict(api_config.get('params', {}))
        body = api_config.get('body')

        if body is not None:
            body = context.replace_vars_dict(body)

        # 构建 URL
        if not url.startswith(('http://', 'https://')):
            # 需要拼接 base_url
            from src.utils.yaml_loader import load_yaml_dict
            config = load_yaml_dict("config/config.yaml", default={})
            default_env = config.get('default_env', 'test')
            env_config = load_yaml_dict(f"config/env/{default_env}.yaml", default={})
            base_url = env_config.get('base_url', '')
            if base_url:
                if not url.startswith('/'):
                    url = f'/{url}'
                url = f'{base_url}{url}'

        logger.info(f"发送清洗请求: {method} {url}")

        # 创建 HTTP 客户端
        if self.http_client is None:
            self.http_client = create_client('requests', {})

        # 发送请求
        request_data = {}
        if headers:
            request_data['headers'] = headers
        if params:
            request_data['params'] = params
        if body is not None:
            content_type = headers.get('Content-Type', '') if headers else ''
            if 'application/json' in content_type.lower():
                request_data['json'] = body
            else:
                request_data['data'] = body

        response = self.http_client.request(
            method=method,
            url=url,
            **request_data
        )

        # 检查响应
        status_code = response.get('status_code', 0)
        if 200 <= status_code < 300:
            logger.info(f"数据清洗成功: {method} {url}, 状态码: {status_code}")
            return True
        else:
            logger.error(f"数据清洗失败: {method} {url}, 状态码: {status_code}")
            return False

    def _cleanup_by_sql(self, sql_config: Dict[str, Any]) -> bool:
        """
        通过 SQL 删除数据
        Args:
            sql_config: SQL 配置
                - connection: 数据库连接名称
                - statement: SQL 语句
                - params: SQL 参数
        Returns:
            bool: 删除是否成功
        """
        logger.info("开始通过 SQL 清洗数据")

        # 获取上下文
        context = get_context()

        # 替换变量
        statement = context.replace_vars(sql_config.get('statement', ''))
        params = sql_config.get('params')

        if params is not None:
            params = context.replace_vars_dict(params)

        logger.info(f"执行 SQL: {statement}")

        try:
            # 这里需要调用数据库集成服务
            # 使用 integration-postgre-database 集成
            result = self._execute_sql(statement, params)

            if result:
                logger.info(f"SQL 清洗成功: {statement}")
                return True
            else:
                logger.error(f"SQL 清洗失败: {statement}")
                return False
        except Exception as e:
            logger.error(f"执行 SQL 失败: {str(e)}")
            return False

    def _execute_sql(self, statement: str, params: Optional[Dict] = None) -> bool:
        """
        执行 SQL 语句
        Args:
            statement: SQL 语句
            params: 参数
        Returns:
            bool: 执行是否成功
        """
        try:
            # 这里调用 exec_sql 工具执行 SQL
            # 注意：由于 SQL 集成服务可能需要在运行时调用，这里使用占位符
            # 实际实现需要根据项目中的数据库集成方式进行调用

            # 方式1：使用 PostgreSQL 集成（如果已配置）
            # from integration_postgre_database import execute_sql
            # result = execute_sql(statement)

            # 方式2：使用 SQLAlchemy 直接连接数据库
            # 需要在 config.yaml 中配置数据库连接信息
            config = self._get_db_config()
            if config:
                return self._execute_with_sqlalchemy(statement, params, config)
            else:
                logger.warning("未配置数据库连接，SQL 清洗将跳过")
                return False

        except Exception as e:
            logger.error(f"执行 SQL 异常: {str(e)}")
            return False

    def _get_db_config(self) -> Optional[Dict]:
        """
        获取数据库配置
        Returns:
            Optional[Dict]: 数据库配置
        """
        try:
            from src.utils.yaml_loader import load_yaml_dict
            config = load_yaml_dict("config/config.yaml", default={})
            db_config = config.get('database', {})

            # 检查必要配置
            if not db_config.get('host'):
                return None

            return db_config
        except Exception as e:
            logger.error(f"获取数据库配置失败: {str(e)}")
            return None

    def _execute_with_sqlalchemy(self, statement: str, params: Optional[Dict], db_config: Dict) -> bool:
        """
        使用 SQLAlchemy 执行 SQL
        Args:
            statement: SQL 语句
            params: 参数
            db_config: 数据库配置
        Returns:
            bool: 执行是否成功
        """
        try:
            from sqlalchemy import create_engine, text

            # 构建数据库连接 URL
            db_type = db_config.get('type', 'mysql')
            host = db_config.get('host')
            port = db_config.get('port', 3306)
            user = db_config.get('user')
            password = db_config.get('password')
            database = db_config.get('database')

            if db_type == 'mysql':
                url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
            elif db_type == 'postgresql':
                url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
            else:
                logger.error(f"不支持的数据库类型: {db_type}")
                return False

            # 创建引擎
            engine = create_engine(url)

            # 执行 SQL
            with engine.connect() as conn:
                result = conn.execute(text(statement))
                conn.commit()
                affected_rows = result.rowcount
                logger.info(f"SQL 执行成功，影响行数: {affected_rows}")

            return True

        except ImportError:
            logger.error("未安装 sqlalchemy 或 pymysql，请先安装: pip install sqlalchemy pymysql")
            return False
        except Exception as e:
            logger.error(f"使用 SQLAlchemy 执行 SQL 失败: {str(e)}")
            return False

    def cleanup_batch(self, cleanup_configs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        批量执行数据清洗
        Args:
            cleanup_configs: 清洗配置列表
        Returns:
            Dict: 清洗结果统计
                - total: 总数
                - success: 成功数
                - failed: 失败数
                - errors: 错误信息列表
        """
        results = {
            'total': len(cleanup_configs),
            'success': 0,
            'failed': 0,
            'errors': []
        }

        for idx, config in enumerate(cleanup_configs):
            try:
                success = self.cleanup(config)
                if success:
                    results['success'] += 1
                else:
                    results['failed'] += 1
                    results['errors'].append({
                        'index': idx,
                        'config': config,
                        'message': '清洗失败'
                    })
            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'index': idx,
                    'config': config,
                    'message': str(e)
                })

        logger.info(f"批量清洗完成: 成功 {results['success']}, 失败 {results['failed']}")
        return results

    def close(self):
        """关闭资源"""
        if self.http_client:
            self.http_client.close()
            self.http_client = None

        # 关闭数据库连接
        for conn in self.db_connections.values():
            try:
                conn.close()
            except:
                pass
        self.db_connections.clear()


# 全局实例
_cleaner = None


def get_cleaner() -> DataCleaner:
    """
    获取全局数据清洗管理器实例
    Returns:
        DataCleaner: 清洗管理器实例
    """
    global _cleaner
    if _cleaner is None:
        _cleaner = DataCleaner()
    return _cleaner
