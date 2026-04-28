"""
自定义异常模块

定义业务相关的自定义异常
"""


class TranslationError(Exception):
    """翻译基础异常"""

    def __init__(self, message: str, skill_name: str = ""):
        self.message = message
        self.skill_name = skill_name
        super().__init__(f"[{skill_name}] {message}" if skill_name else message)


class TranslationServiceError(TranslationError):
    """翻译服务异常"""
    pass


class BackupError(TranslationError):
    """备份异常"""
    pass


class VerificationError(TranslationError):
    """验证异常"""
    pass


class FileOperationError(TranslationError):
    """文件操作异常"""
    pass


class ConfigurationError(Exception):
    """配置异常"""
    pass


class ServiceNotAvailableError(ConfigurationError):
    """服务不可用异常"""

    def __init__(self, service_name: str):
        self.service_name = service_name
        super().__init__(f"Translation service not available: {service_name}")
