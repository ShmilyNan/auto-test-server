"""
通知发送器
支持飞书、钉钉、企业微信、邮箱等通知方式
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any
from abc import ABC, abstractmethod
from datetime import datetime
from src.utils.logger import log as logger


class BaseNotifier(ABC):
    """通知器基类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get('enable', False)
    
    @abstractmethod
    def send(self, title: str, content: str, **kwargs) -> bool:
        """
        发送通知
        Args:
            title: 通知标题
            content: 通知内容
            **kwargs: 其他参数
        Returns:
            bool: 是否发送成功
        """
        pass
    
    def _format_message(self, title: str, content: str) -> str:
        """格式化消息"""
        return f"【{title}】\n\n{content}"


class DingTalkNotifier(BaseNotifier):
    """钉钉通知"""
    
    def send(self, title: str, content: str, **kwargs) -> bool:
        """发送钉钉通知"""
        if not self.enabled:
            logger.debug("钉钉通知未启用")
            return False
        
        webhook = self.config.get('webhook')
        secret = self.config.get('secret')
        
        if not webhook:
            logger.error("钉钉webhook未配置")
            return False
        
        try:
            import hmac
            import hashlib
            import base64
            import time
            import urllib.parse
            import requests
            
            # 生成签名
            if secret:
                timestamp = str(round(time.time() * 1000))
                secret_enc = secret.encode('utf-8')
                string_to_sign = f'{timestamp}\n{secret}'
                string_to_sign_enc = string_to_sign.encode('utf-8')
                hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
                sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
                webhook_url = f"{webhook}&timestamp={timestamp}&sign={sign}"
            else:
                webhook_url = webhook
            
            # 构造消息
            data = {
                "msgtype": "markdown",
                "markdown": {
                    "title": title,
                    "text": f"## {title}\n\n{content}"
                }
            }
            
            # @人
            at_mobiles = self.config.get('at_mobiles', [])
            at_all = self.config.get('at_all', False)
            
            if at_mobiles or at_all:
                data["at"] = {
                    "atMobiles": at_mobiles,
                    "isAtAll": at_all
                }
            
            # 发送请求
            response = requests.post(webhook_url, json=data, timeout=10)
            result = response.json()
            
            if result.get('errcode') == 0:
                logger.info("钉钉通知发送成功")
                return True
            else:
                logger.error(f"钉钉通知发送失败: {result.get('errmsg')}")
                return False
                
        except Exception as e:
            logger.error(f"钉钉通知发送异常: {str(e)}")
            return False


class FeishuNotifier(BaseNotifier):
    """飞书通知"""
    
    def send(self, title: str, content: str, **kwargs) -> bool:
        """发送飞书通知"""
        if not self.enabled:
            logger.debug("飞书通知未启用")
            return False
        
        webhook = self.config.get('webhook')
        
        if not webhook:
            logger.error("飞书webhook未配置")
            return False
        
        try:
            import requests
            
            # 构造消息
            data = {
                "msg_type": "interactive",
                "card": {
                    "header": {
                        "title": {
                            "tag": "plain_text",
                            "content": title
                        }
                    },
                    "elements": [
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": content
                            }
                        },
                        {
                            "tag": "hr"
                        },
                        {
                            "tag": "div",
                            "text": {
                                "tag": "plain_text",
                                "content": f"发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                            }
                        }
                    ]
                }
            }
            
            # 发送请求
            response = requests.post(webhook, json=data, timeout=10)
            result = response.json()
            
            if result.get('StatusCode') == 0 or result.get('code') == 0:
                logger.info("飞书通知发送成功")
                return True
            else:
                logger.error(f"飞书通知发送失败: {result}")
                return False
                
        except Exception as e:
            logger.error(f"飞书通知发送异常: {str(e)}")
            return False


class WechatNotifier(BaseNotifier):
    """企业微信通知"""
    
    def send(self, title: str, content: str, **kwargs) -> bool:
        """发送企业微信通知"""
        if not self.enabled:
            logger.debug("企业微信通知未启用")
            return False
        
        webhook = self.config.get('webhook')
        
        if not webhook:
            logger.error("企业微信webhook未配置")
            return False
        
        try:
            import requests
            
            # 构造消息
            data = {
                "msgtype": "markdown",
                "markdown": {
                    "content": f"## {title}\n\n{content}"
                }
            }
            
            # @人
            mentioned_list = self.config.get('mentioned_list', [])
            mentioned_mobile_list = self.config.get('mentioned_mobile_list', [])
            
            if mentioned_list or mentioned_mobile_list:
                data["markdown"]["mentioned_list"] = mentioned_list
                data["markdown"]["mentioned_mobile_list"] = mentioned_mobile_list
            
            # 发送请求
            response = requests.post(webhook, json=data, timeout=10)
            result = response.json()
            
            if result.get('errcode') == 0:
                logger.info("企业微信通知发送成功")
                return True
            else:
                logger.error(f"企业微信通知发送失败: {result.get('errmsg')}")
                return False
                
        except Exception as e:
            logger.error(f"企业微信通知发送异常: {str(e)}")
            return False


class EmailNotifier(BaseNotifier):
    """邮件通知"""
    
    def send(self, title: str, content: str, **kwargs) -> bool:
        """发送邮件通知"""
        if not self.enabled:
            logger.debug("邮件通知未启用")
            return False
        
        smtp_host = self.config.get('smtp_host')
        smtp_port = self.config.get('smtp_port', 587)
        sender = self.config.get('sender')
        password = self.config.get('password')
        receivers = self.config.get('receivers', [])
        
        if not all([smtp_host, sender, password, receivers]):
            logger.error("邮件配置不完整")
            return False
        
        try:
            # 创建邮件
            msg = MIMEMultipart('alternative')
            msg['Subject'] = title
            msg['From'] = sender
            msg['To'] = ', '.join(receivers)
            
            # 添加内容
            html_content = f"""
            <html>
            <body>
                <h2>{title}</h2>
                <pre>{content}</pre>
                <hr>
                <p style="color: gray;">发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))
            
            # 发送邮件
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(sender, password)
                server.sendmail(sender, receivers, msg.as_string())
            
            logger.info("邮件通知发送成功")
            return True
            
        except Exception as e:
            logger.error(f"邮件通知发送异常: {str(e)}")
            return False


class NotificationManager:
    """通知管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化通知管理器
        Args:
            config: 通知配置
        """
        self.notifiers = []
        
        # 初始化各个通知器
        if config.get('dingtalk', {}).get('enable'):
            self.notifiers.append(DingTalkNotifier(config['dingtalk']))
        
        if config.get('feishu', {}).get('enable'):
            self.notifiers.append(FeishuNotifier(config['feishu']))
        
        if config.get('wechat', {}).get('enable'):
            self.notifiers.append(WechatNotifier(config['wechat']))
        
        if config.get('email', {}).get('enable'):
            self.notifiers.append(EmailNotifier(config['email']))
        
        logger.info(f"初始化通知管理器，启用了 {len(self.notifiers)} 个通知渠道")
    
    def send(self, title: str, content: str, **kwargs) -> Dict[str, bool]:
        """
        发送通知到所有渠道
        Args:
            title: 通知标题
            content: 通知内容
            **kwargs: 其他参数
        Returns:
            Dict[str, bool]: 各渠道发送结果
        """
        results = {}
        
        for notifier in self.notifiers:
            notifier_name = notifier.__class__.__name__
            results[notifier_name] = notifier.send(title, content, **kwargs)
        
        return results
    
    def send_test_report(self, report_data: Dict[str, Any]) -> Dict[str, bool]:
        """
        发送测试报告
        Args:
            report_data: 报告数据 {total, passed, failed, duration, etc.}
        Returns:
            Dict[str, bool]: 发送结果
        """
        total = report_data.get('total', 0)
        passed = report_data.get('passed', 0)
        failed = report_data.get('failed', 0)
        duration = report_data.get('duration', 0)
        pass_rate = f"{passed / total * 100:.2f}%" if total > 0 else "0%"
        
        title = f"测试报告 - {pass_rate}"
        
        content = f"""
                **测试概览**
                - 总用例数: {total}
                - 通过: {passed}
                - 失败: {failed}
                - 通过率: {pass_rate}
                - 耗时: {duration:.2f}s
                - 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                """
        
        return self.send(title, content)
