"""
模拟翻译服务

用于测试，不实际翻译
"""

from .base import TranslationService


class MockTranslation(TranslationService):
    """模拟翻译服务"""

    def __init__(self, model: str = 'mock'):
        """
        初始化模拟翻译服务

        Args:
            model: 模型名称
        """
        super().__init__(model)
        self.logger.info("Mock translation service initialized")

    def is_available(self) -> bool:
        """检查服务是否可用"""
        return True

    def translate(self, content: str) -> str:
        """
        模拟翻译（直接返回原始内容）

        Args:
            content: 原始内容

        Returns:
            原始内容（不做翻译）
        """
        self.logger.debug("Mock translation - returning original content")
        return content
