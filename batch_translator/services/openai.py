"""
OpenAI翻译服务

使用OpenAI GPT-4进行翻译
"""

import os
from typing import Optional
from .base import TranslationService
from ..exceptions import TranslationServiceError


class OpenAITranslation(TranslationService):
    """OpenAI翻译服务，支持多语言"""

    def __init__(
        self,
        model: str = 'gpt-4',
        api_key: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4000,
        from_lang: str = "en",
        to_lang: str = "zh",
    ):
        """
        初始化OpenAI翻译服务

        Args:
            model: 模型名称
            api_key: API密钥
            temperature: 温度参数
            max_tokens: 最大token数
            from_lang: 源语言代码 (en, zh, ja)
            to_lang: 目标语言代码 (en, zh, ja)
        """
        super().__init__(model=model, from_lang=from_lang, to_lang=to_lang)
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.temperature = temperature
        self.max_tokens = max_tokens

        if not self.api_key:
            self.logger.warning("OpenAI API key not found in environment")

    def is_available(self) -> bool:
        """检查服务是否可用"""
        return bool(self.api_key)

    def translate(self, content: str) -> str:
        """
        使用OpenAI API翻译

        Args:
            content: 原始内容

        Returns:
            翻译后的内容

        Raises:
            TranslationServiceError: 翻译失败时抛出
        """
        if not self.is_available():
            raise TranslationServiceError(
                "OpenAI API key not available",
                skill_name="openai_translation"
            )

        try:
            # 动态导入openai
            try:
                from openai import OpenAI
            except ImportError:
                raise TranslationServiceError(
                    "OpenAI library not installed. Run: pip install openai",
                    skill_name="openai_translation"
                )

            client = OpenAI(api_key=self.api_key)

            prompt = self.get_translation_prompt(content)

            self.logger.debug(f"Translating content with {self.model}")

            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional translator."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            translated = response.choices[0].message.content

            if not translated:
                raise TranslationServiceError(
                    "Empty response from OpenAI API",
                    skill_name="openai_translation"
                )

            self.logger.info(f"Translation completed successfully")
            return translated

        except TranslationServiceError:
            raise
        except Exception as e:
            self.logger.error(f"OpenAI translation failed: {e}")
            raise TranslationServiceError(
                f"OpenAI API error: {str(e)}",
                skill_name="openai_translation"
            )
