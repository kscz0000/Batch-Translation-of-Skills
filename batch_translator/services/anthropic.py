"""
Anthropic Claude翻译服务

使用Anthropic Claude进行翻译
"""

import os
from typing import Optional
from .base import TranslationService
from ..exceptions import TranslationServiceError


class AnthropicTranslation(TranslationService):
    """Anthropic Claude翻译服务，支持多语言"""

    def __init__(
        self,
        model: str = 'claude-3-5-sonnet-20241022',
        api_key: Optional[str] = None,
        max_tokens: int = 4000,
        from_lang: str = "en",
        to_lang: str = "zh",
    ):
        """
        初始化Anthropic翻译服务

        Args:
            model: 模型名称
            api_key: API密钥
            max_tokens: 最大token数
            from_lang: 源语言代码 (en, zh, ja)
            to_lang: 目标语言代码 (en, zh, ja)
        """
        super().__init__(model=model, from_lang=from_lang, to_lang=to_lang)
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        self.max_tokens = max_tokens

        if not self.api_key:
            self.logger.warning("Anthropic API key not found in environment")

    def is_available(self) -> bool:
        """检查服务是否可用"""
        return bool(self.api_key)

    def translate(self, content: str) -> str:
        """
        使用Anthropic API翻译

        Args:
            content: 原始内容

        Returns:
            翻译后的内容

        Raises:
            TranslationServiceError: 翻译失败时抛出
        """
        if not self.is_available():
            raise TranslationServiceError(
                "Anthropic API key not available",
                skill_name="anthropic_translation"
            )

        try:
            # 动态导入anthropic
            try:
                import anthropic
            except ImportError:
                raise TranslationServiceError(
                    "Anthropic library not installed. Run: pip install anthropic",
                    skill_name="anthropic_translation"
                )

            client = anthropic.Anthropic(api_key=self.api_key)

            prompt = self.get_translation_prompt(content)

            self.logger.debug(f"Translating content with {self.model}")

            response = client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            translated = response.content[0].text

            if not translated:
                raise TranslationServiceError(
                    "Empty response from Anthropic API",
                    skill_name="anthropic_translation"
                )

            self.logger.info("Translation completed successfully")
            return translated

        except TranslationServiceError:
            raise
        except Exception as e:
            self.logger.error(f"Anthropic translation failed: {e}")
            raise TranslationServiceError(
                f"Anthropic API error: {str(e)}",
                skill_name="anthropic_translation"
            )
