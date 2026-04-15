# -*- coding: utf-8 -*-
"""
Allure 钩子模块
处理 Allure 报告相关的钩子函数
"""
import json
import allure
from src.utils.logger import logger


def attach_request_response(test_context):
    """
    自动附加请求和响应到Allure报告
    """
    # 执行请求前钩子
    from src.hooks.custom_hooks import before_request
    try:
        before_request()
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"执行 before_request 钩子失败: {str(e)}")

    yield

    try:
        # 获取最后一个响应
        response = test_context.get_last_response()

        if response and isinstance(response, dict):
            # 附加请求信息
            request = response.get('request', {}) or {}
            request_text = f"""
                        请求方法: {request.get('method', 'N/A')}
                        请求URL: {request.get('url', 'N/A')}
                        请求头: {request.get('headers', {})}
                        请求参数: {request.get('params', {})}
                        请求体: {request.get('body', 'N/A')}
                        """
            allure.attach(request_text, name="请求信息", attachment_type=allure.attachment_type.TEXT)

            # 附加请求JSON（如果请求体是JSON格式）
            request_body = request.get('body')
            if request_body is not None and isinstance(request_body, (dict, list)):
                try:
                    allure.attach(
                        json.dumps(request_body, ensure_ascii=False, indent=2),
                        name="请求JSON",
                        attachment_type=allure.attachment_type.JSON
                    )
                except Exception as e:
                    logger.warning(f"序列化请求JSON失败: {e}")

            # 附加响应信息
            headers = response.get('headers') or {}
            body = response.get('body')

            response_text = f"""
                        状态码: {response.get('status_code', 'N/A')}
                        响应头: {headers}
                        响应体: {body if body else 'N/A'}
                        耗时: {response.get('elapsed', 0):.3f}s
                        """
            allure.attach(response_text, name="响应信息", attachment_type=allure.attachment_type.TEXT)

            # 附加JSON响应
            if body is not None and isinstance(body, (dict, list)):
                try:
                    allure.attach(
                        json.dumps(body, ensure_ascii=False, indent=2),
                        name="响应JSON",
                        attachment_type=allure.attachment_type.JSON
                    )
                except Exception as e:
                    logger.warning(f"序列化JSON响应失败: {e}")

            # 执行请求后钩子
            from src.hooks.custom_hooks import after_request
            try:
                after_request(response)
            except ImportError:
                pass
            except Exception as e:
                logger.warning(f"执行 after_request 钩子失败: {str(e)}")
    except Exception as e:
        logger.warning(f"附加请求响应到Allure报告时出错: {e}")
