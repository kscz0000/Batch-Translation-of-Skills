"""
翻译服务工厂

使用工厂模式创建翻译服务实例
"""

import logging
from typing import Dict, Type
from .base import TranslationService
from .openai import OpenAITranslation
from .anthropic import AnthropicTranslation
from .mock import MockTranslation
from .minimax import MiniMaxTranslation
from ..exceptions import ServiceNotAvailableError


logger = logging.getLogger(__name__)


class TranslationServiceFactory:
    """
    翻译服务工厂

    使用工厂模式统一创建翻译服务实例
    """

    _services: Dict[str, Type[TranslationService]] = {
        'openai': OpenAITranslation,
        'anthropic': AnthropicTranslation,
        'mock': MockTranslation,
        'minimax': MiniMaxTranslation,
    }

    @classmethod
    def register(cls, name: str, service_class: Type[TranslationService]) -> None:
        """
        注册翻译服务

        Args:
            name: 服务名称
            service_class: 服务类
        """
        cls._services[name] = service_class
        logger.debug(f"Registered translation service: {name}")

    @classmethod
    def create(cls, name: str, **kwargs) -> TranslationService:
        """
        创建翻译服务实例

        Args:
            name: 服务名称
            **kwargs: 传递给服务构造函数的参数

        Returns:
            翻译服务实例

        Raises:
            ServiceNotAvailableError: 服务不可用时抛出
        """
        if name not in cls._services:
            available = ', '.join(cls._services.keys())
            raise ServiceNotAvailableError(
                f"{name}. Available: {available}"
            )

        service_class = cls._services[name]
        service = service_class(**kwargs)

        # 检查服务是否可用
        if not service.is_available() and name != 'mock':
            raise ServiceNotAvailableError(name)

        logger.info(f"Created translation service: {name}")
        return service

    @classmethod
    def list_services(cls) -> list:
        """
        列出所有可用的翻译服务

        Returns:
            服务名称列表
        """
        return list(cls._services.keys())

    @classmethod
    def get_available_services(cls) -> Dict[str, bool]:
        """
        获取所有服务及其可用状态

        Returns:
            服务名称到可用状态的映射
        """
        result = {}
        for name in cls._services:
            try:
                service = cls.create(name)
                result[name] = service.is_available()
            except ServiceNotAvailableError:
                result[name] = False
        return result
