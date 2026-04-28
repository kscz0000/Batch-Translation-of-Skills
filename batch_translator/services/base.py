"""
翻译服务基类

使用策略模式定义翻译接口，支持多语言翻译
"""

from abc import ABC, abstractmethod
from typing import Optional, Tuple
import logging


PRESERVE_TERMS = (
    'API', 'SEO', 'URL', 'JSON', 'XML', 'SQL', 'HTTP',
    'React', 'Vue', 'Angular', 'Node.js', 'Python', 'Go', 'Rust',
    'JavaScript', 'TypeScript', 'Google', 'Meta', 'Microsoft',
    'Apple', 'GitHub', 'Twitter', 'TikTok', 'YouTube',
)


class TranslationService(ABC):
    """
    翻译服务抽象基类

    使用策略模式，让不同的翻译服务实现统一的接口
    支持多语言翻译
    """

    def __init__(
        self,
        model: Optional[str] = None,
        prompt_template: Optional[str] = None,
        from_lang: str = "en",
        to_lang: str = "zh",
    ):
        """
        初始化翻译服务

        Args:
            model: 模型名称
            prompt_template: 自定义提示词模板（可选）
            from_lang: 源语言代码 (en, zh, ja)
            to_lang: 目标语言代码 (en, zh, ja)
        """
        self.model = model
        self.logger = logging.getLogger(self.__class__.__name__)
        self._prompt_template = prompt_template
        self._from_lang = from_lang
        self._to_lang = to_lang

    @abstractmethod
    def translate(self, content: str) -> str:
        """
        翻译内容

        Args:
            content: 原始内容

        Returns:
            翻译后的内容
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        检查服务是否可用

        Returns:
            是否可用
        """
        pass

    def get_translation_prompt(self, content: str) -> str:
        """
        获取翻译提示词（兼容旧接口）

        Args:
            content: 待翻译内容

        Returns:
            提示词
        """
        from ..languages import get_translation_prompt
        template = get_translation_prompt(self._from_lang, self._to_lang)
        return template + content

    def get_description_prompt(self, description: str) -> str:
        """
        获取描述字段翻译的专用提示词

        Args:
            description: 待翻译的描述内容

        Returns:
            提示词
        """
        from ..languages import get_description_prompt
        return get_description_prompt(self._from_lang, self._to_lang) + description

    def get_body_prompt(self, body: str) -> str:
        """
        获取正文翻译的专用提示词

        Args:
            body: 待翻译的正文内容

        Returns:
            提示词
        """
        from ..languages import get_body_prompt
        return get_body_prompt(self._from_lang, self._to_lang) + body

    def get_language_pair(self) -> Tuple[str, str]:
        """
        获取当前语言对

        Returns:
            (源语言, 目标语言)
        """
        return (self._from_lang, self._to_lang)

    def set_language_pair(self, from_lang: str, to_lang: str) -> None:
        """
        设置语言对

        Args:
            from_lang: 源语言代码
            to_lang: 目标语言代码
        """
        self._from_lang = from_lang
        self._to_lang = to_lang

    @classmethod
    def set_default_prompt_template(cls, template: str) -> None:
        """
        设置默认提示词模板（类级别，已废弃）

        Args:
            template: 新的提示词模板
        """
        import warnings
        warnings.warn(
            "set_default_prompt_template is deprecated. "
            "Use TranslationService.__init__ with from_lang and to_lang parameters.",
            DeprecationWarning,
            stacklevel=2
        )
