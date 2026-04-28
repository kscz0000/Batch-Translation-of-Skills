"""
语言配置模块

定义支持的语言和翻译方向
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Tuple, Optional


class Language(Enum):
    """支持的语言"""
    ENGLISH = "en"
    CHINESE = "zh"
    JAPANESE = "ja"
    KOREAN = "ko"

    @classmethod
    def from_code(cls, code: str) -> Optional['Language']:
        """从语言代码获取语言枚举"""
        code = code.lower().strip()
        for lang in cls:
            if lang.value == code:
                return lang
        return None

    @classmethod
    def is_valid(cls, code: str) -> bool:
        """检查语言代码是否有效"""
        return cls.from_code(code) is not None


@dataclass
class LanguageConfig:
    """语言配置"""
    code: str
    name: str
    native_name: str
    description: str
    character_range: Tuple[int, int]


LANGUAGE_CONFIGS: Dict[str, LanguageConfig] = {
    "en": LanguageConfig(
        code="en",
        name="English",
        native_name="English",
        description="英语",
        character_range=(0x0000, 0x007F),
    ),
    "zh": LanguageConfig(
        code="zh",
        name="Chinese",
        native_name="中文",
        description="中文（简体中文）",
        character_range=(0x4E00, 0x9FFF),
    ),
    "ja": LanguageConfig(
        code="ja",
        name="Japanese",
        native_name="日本語",
        description="日语",
        character_range=(0x3040, 0x30FF),
    ),
    "ko": LanguageConfig(
        code="ko",
        name="Korean",
        native_name="한국어",
        description="韩语",
        character_range=(0xAC00, 0xD7AF),
    ),
}


TRANSLATION_PROMPTS: Dict[Tuple[str, str], str] = {
    ("en", "zh"): """Translate the following English skill documentation to Chinese. Output ONLY the translated content, nothing else.

IMPORTANT: The content has YAML frontmatter at the top (between --- markers). You MUST:
- Keep the name field UNCHANGED (do not translate name)
- Translate the ENTIRE description field to Chinese (this is MANDATORY)
- Translate everything AFTER the frontmatter to Chinese
- PRESERVE EXACT CASE of ALL technical terms: API, SEO, URL, JSON, XML, SQL, HTTP, React, Vue, Python, JavaScript, TypeScript, Google, Meta, Microsoft, Apple, GitHub, Twitter, TikTok, YouTube. NEVER use lowercase like api, seo, url.

Rules:
- Technical terms: MUST preserve EXACT uppercase
- YAML frontmatter: keep name unchanged, translate description to Chinese
- Headings (# ## ###): translate to Chinese
- Body text: translate to fluent Chinese
- Code blocks (```...```): protected by placeholders, do NOT modify them
- Inline code (`code`): keep as-is
- Tables (| col | col |): keep structure, translate text only
- URLs: keep unchanged
- Keep ALL markdown characters: ```, |, #, -, :, >, [, ], (, ), *, _, `

Content to translate:

""",

    ("zh", "en"): """Translate the following Chinese skill documentation to English. Output ONLY the translated content, nothing else.

IMPORTANT: The content has YAML frontmatter at the top (between --- markers). You MUST:
- Keep the name field UNCHANGED (do not translate name)
- Translate the ENTIRE description field to English (this is MANDATORY)
- Translate everything AFTER the frontmatter to English
- Keep technical terms in their original English form when commonly used in English

Rules:
- YAML frontmatter: keep name unchanged, translate description to English
- Headings (# ## ###): translate to English
- Body text: translate to fluent English
- Code blocks (```...```): protected by placeholders, do NOT modify them
- Inline code (`code`): keep as-is
- Tables (| col | col |): keep structure, translate text only
- URLs: keep unchanged
- Keep ALL markdown characters: ```, |, #, -, :, >, [, ], (, ), *, _, `

Content to translate:

""",

    ("ja", "zh"): """Translate the following Japanese skill documentation to Chinese. Output ONLY the translated content, nothing else.

IMPORTANT: The content has YAML frontmatter at the top (between --- markers). You MUST:
- Keep the name field UNCHANGED (do not translate name)
- Translate the ENTIRE description field to Chinese (this is MANDATORY)
- Translate everything AFTER the frontmatter to Chinese
- Keep common Japanese technical terms in their Katakana form when appropriate

Rules:
- YAML frontmatter: keep name unchanged, translate description to Chinese
- Headings (# ## ###): translate to Chinese
- Body text: translate to fluent Chinese
- Code blocks (```...```): protected by placeholders, do NOT modify them
- Inline code (`code`): keep as-is
- Tables (| col | col |): keep structure, translate text only
- URLs: keep unchanged
- Keep Japanese hiragana/katakana technical terms when commonly used
- Keep ALL markdown characters: ```, |, #, -, :, >, [, ], (, ), *, _, `

Content to translate:

""",

    ("zh", "ja"): """Translate the following Chinese skill documentation to Japanese. Output ONLY the translated content, nothing else.

IMPORTANT: The content has YAML frontmatter at the top (between --- markers). You MUST:
- Keep the name field UNCHANGED (do not translate name)
- Translate the ENTIRE description field to Japanese (this is MANDATORY)
- Translate everything AFTER the frontmatter to Japanese
- Use appropriate Japanese politeness level (です/ます form)

Rules:
- YAML frontmatter: keep name unchanged, translate description to Japanese
- Headings (# ## ###): translate to Japanese
- Body text: translate to fluent Japanese
- Code blocks (```...```): protected by placeholders, do NOT modify them
- Inline code (`code`): keep as-is
- Tables (| col | col |): keep structure, translate text only
- URLs: keep unchanged
- Keep technical terms in their Katakana form when appropriate
- Keep ALL markdown characters: ```, |, #, -, :, >, [, ], (, ), *, _, `

Content to translate:

""",

    ("en", "ja"): """Translate the following English skill documentation to Japanese. Output ONLY the translated content, nothing else.

IMPORTANT: The content has YAML frontmatter at the top (between --- markers). You MUST:
- Keep the name field UNCHANGED (do not translate name)
- Translate the ENTIRE description field to Japanese (this is MANDATORY)
- Translate everything AFTER the frontmatter to Japanese
- Use appropriate Japanese politeness level (です/ます form)
- PRESERVE EXACT CASE of ALL technical terms in Latin alphabet

Rules:
- YAML frontmatter: keep name unchanged, translate description to Japanese
- Headings (# ## ###): translate to Japanese
- Body text: translate to fluent Japanese
- Code blocks (```...```): protected by placeholders, do NOT modify them
- Inline code (`code`): keep as-is
- Tables (| col | col |): keep structure, translate text only
- URLs: keep unchanged
- Keep technical terms in Katakana when commonly used in Japanese
- Keep ALL markdown characters: ```, |, #, -, :, >, [, ], (, ), *, _, `

Content to translate:

""",

    ("ja", "en"): """Translate the following Japanese skill documentation to English. Output ONLY the translated content, nothing else.

IMPORTANT: The content has YAML frontmatter at the top (between --- markers). You MUST:
- Keep the name field UNCHANGED (do not translate name)
- Translate the ENTIRE description field to English (this is MANDATORY)
- Translate everything AFTER the frontmatter to English

Rules:
- YAML frontmatter: keep name unchanged, translate description to English
- Headings (# ## ###): translate to English
- Body text: translate to fluent English
- Code blocks (```...```): protected by placeholders, do NOT modify them
- Inline code (`code`): keep as-is
- Tables (| col | col |): keep structure, translate text only
- URLs: keep unchanged
- Keep technical terms in their original form
- Keep ALL markdown characters: ```, |, #, -, :, >, [, ], (, ), *, _, `

Content to translate:

""",

    ("ko", "zh"): """Translate the following Korean skill documentation to Chinese. Output ONLY the translated content, nothing else.

IMPORTANT: The content has YAML frontmatter at the top (between --- markers). You MUST:
- Keep the name field UNCHANGED (do not translate name)
- Translate the ENTIRE description field to Chinese (this is MANDATORY)
- Translate everything AFTER the frontmatter to Chinese
- Keep common Korean technical terms in their Hangul form when appropriate

Rules:
- YAML frontmatter: keep name unchanged, translate description to Chinese
- Headings (# ## ###): translate to Chinese
- Body text: translate to fluent Chinese
- Code blocks (```...```): protected by placeholders, do NOT modify them
- Inline code (`code`): keep as-is
- Tables (| col | col |): keep structure, translate text only
- URLs: keep unchanged
- Keep Korean technical terms when commonly used
- Keep ALL markdown characters: ```, |, #, -, :, >, [, ], (, ), *, _, `

Content to translate:

""",

    ("zh", "ko"): """Translate the following Chinese skill documentation to Korean. Output ONLY the translated content, nothing else.

IMPORTANT: The content has YAML frontmatter at the top (between --- markers). You MUST:
- Keep the name field UNCHANGED (do not translate name)
- Translate the ENTIRE description field to Korean (this is MANDATORY)
- Translate everything AFTER the frontmatter to Korean

Rules:
- YAML frontmatter: keep name unchanged, translate description to Korean
- Headings (# ## ###): translate to Korean
- Body text: translate to fluent Korean
- Code blocks (```...```): protected by placeholders, do NOT modify them
- Inline code (`code`): keep as-is
- Tables (| col | col |): keep structure, translate text only
- URLs: keep unchanged
- Keep technical terms in their Hangul form when appropriate
- Keep ALL markdown characters: ```, |, #, -, :, >, [, ], (, ), *, _, `

Content to translate:

""",

    ("en", "ko"): """Translate the following English skill documentation to Korean. Output ONLY the translated content, nothing else.

IMPORTANT: The content has YAML frontmatter at the top (between --- markers). You MUST:
- Keep the name field UNCHANGED (do not translate name)
- Translate the ENTIRE description field to Korean (this is MANDATORY)
- Translate everything AFTER the frontmatter to Korean
- PRESERVE EXACT CASE of ALL technical terms in Latin alphabet

Rules:
- YAML frontmatter: keep name unchanged, translate description to Korean
- Headings (# ## ###): translate to Korean
- Body text: translate to fluent Korean
- Code blocks (```...```): protected by placeholders, do NOT modify them
- Inline code (`code`): keep as-is
- Tables (| col | col |): keep structure, translate text only
- URLs: keep unchanged
- Keep technical terms in their original form
- Keep ALL markdown characters: ```, |, #, -, :, >, [, ], (, ), *, _, `

Content to translate:

""",

    ("ko", "en"): """Translate the following Korean skill documentation to English. Output ONLY the translated content, nothing else.

IMPORTANT: The content has YAML frontmatter at the top (between --- markers). You MUST:
- Keep the name field UNCHANGED (do not translate name)
- Translate the ENTIRE description field to English (this is MANDATORY)
- Translate everything AFTER the frontmatter to English

Rules:
- YAML frontmatter: keep name unchanged, translate description to English
- Headings (# ## ###): translate to English
- Body text: translate to fluent English
- Code blocks (```...```): protected by placeholders, do NOT modify them
- Inline code (`code`): keep as-is
- Tables (| col | col |): keep structure, translate text only
- URLs: keep unchanged
- Keep technical terms in their original form
- Keep ALL markdown characters: ```, |, #, -, :, >, [, ], (, ), *, _, `

Content to translate:

""",

    ("ja", "ko"): """Translate the following Japanese skill documentation to Korean. Output ONLY the translated content, nothing else.

IMPORTANT: The content has YAML frontmatter at the top (between --- markers). You MUST:
- Keep the name field UNCHANGED (do not translate name)
- Translate the ENTIRE description field to Korean (this is MANDATORY)
- Translate everything AFTER the frontmatter to Korean

Rules:
- YAML frontmatter: keep name unchanged, translate description to Korean
- Headings (# ## ###): translate to Korean
- Body text: translate to fluent Korean
- Code blocks (```...```): protected by placeholders, do NOT modify them
- Inline code (`code`): keep as-is
- Tables (| col | col |): keep structure, translate text only
- URLs: keep unchanged
- Keep technical terms in their original form
- Keep ALL markdown characters: ```, |, #, -, :, >, [, ], (, ), *, _, `

Content to translate:

""",

    ("ko", "ja"): """Translate the following Korean skill documentation to Japanese. Output ONLY the translated content, nothing else.

IMPORTANT: The content has YAML frontmatter at the top (between --- markers). You MUST:
- Keep the name field UNCHANGED (do not translate name)
- Translate the ENTIRE description field to Japanese (this is MANDATORY)
- Translate everything AFTER the frontmatter to Japanese

Rules:
- YAML frontmatter: keep name unchanged, translate description to Japanese
- Headings (# ## ###): translate to Japanese
- Body text: translate to fluent Japanese
- Code blocks (```...```): protected by placeholders, do NOT modify them
- Inline code (`code`): keep as-is
- Tables (| col | col |): keep structure, translate text only
- URLs: keep unchanged
- Keep technical terms in their Katakana form when appropriate
- Keep ALL markdown characters: ```, |, #, -, :, >, [, ], (, ), *, _, `

Content to translate:

""",
}


def get_translation_prompt(from_lang: str, to_lang: str) -> str:
    """
    获取指定语言对的翻译提示词

    Args:
        from_lang: 源语言代码 (en, zh, ja, ko)
        to_lang: 目标语言代码 (en, zh, ja, ko)

    Returns:
        翻译提示词
    """
    key = (from_lang.lower(), to_lang.lower())
    if key in TRANSLATION_PROMPTS:
        return TRANSLATION_PROMPTS[key]
    raise ValueError(f"不支持的翻译方向: {from_lang} -> {to_lang}")


def get_description_prompt(from_lang: str, to_lang: str) -> str:
    """
    获取描述字段翻译的专用提示词

    Args:
        from_lang: 源语言代码
        to_lang: 目标语言代码

    Returns:
        描述翻译提示词
    """
    prompts = {
        ("en", "zh"): "Translate the following English description to Chinese. Output ONLY the Chinese translation, nothing else. Do not add quotes. Preserve technical terms like API, SDK, React, etc. in their original form.\n\nDescription:\n\n",
        ("zh", "en"): "Translate the following Chinese description to English. Output ONLY the English translation, nothing else. Do not add quotes. Preserve technical terms in their English form.\n\nDescription:\n\n",
        ("ja", "zh"): "Translate the following Japanese description to Chinese. Output ONLY the Chinese translation, nothing else. Do not add quotes.\n\nDescription:\n\n",
        ("zh", "ja"): "Translate the following Chinese description to Japanese. Output ONLY the Japanese translation, nothing else. Do not add quotes. Use polite form.\n\nDescription:\n\n",
        ("en", "ja"): "Translate the following English description to Japanese. Output ONLY the Japanese translation, nothing else. Do not add quotes. Use polite form.\n\nDescription:\n\n",
        ("ja", "en"): "Translate the following Japanese description to English. Output ONLY the English translation, nothing else. Do not add quotes.\n\nDescription:\n\n",
        ("ko", "zh"): "Translate the following Korean description to Chinese. Output ONLY the Chinese translation, nothing else. Do not add quotes.\n\nDescription:\n\n",
        ("zh", "ko"): "Translate the following Chinese description to Korean. Output ONLY the Korean translation, nothing else. Do not add quotes.\n\nDescription:\n\n",
        ("en", "ko"): "Translate the following English description to Korean. Output ONLY the Korean translation, nothing else. Do not add quotes.\n\nDescription:\n\n",
        ("ko", "en"): "Translate the following Korean description to English. Output ONLY the English translation, nothing else. Do not add quotes.\n\nDescription:\n\n",
        ("ja", "ko"): "Translate the following Japanese description to Korean. Output ONLY the Korean translation, nothing else. Do not add quotes.\n\nDescription:\n\n",
        ("ko", "ja"): "Translate the following Korean description to Japanese. Output ONLY the Japanese translation, nothing else. Do not add quotes.\n\nDescription:\n\n",
    }
    key = (from_lang.lower(), to_lang.lower())
    if key in prompts:
        return prompts[key]
    return prompts[("en", "zh")]


def get_body_prompt(from_lang: str, to_lang: str) -> str:
    """
    获取正文翻译的专用提示词（不含 frontmatter）

    Args:
        from_lang: 源语言代码
        to_lang: 目标语言代码

    Returns:
        正文翻译提示词
    """
    prompts = {
        ("en", "zh"): """Translate the following English content to Chinese. Output ONLY the translated content, nothing else.

Rules:
- Headings (# ## ###): translate to Chinese
- Body text: translate to fluent Chinese
- Code blocks (```...```): protected by placeholders, do NOT modify them
- Inline code (`code`): keep as-is
- Tables (| col | col |): keep structure, translate text only
- URLs: keep unchanged
- Keep ALL markdown characters: ```, |, #, -, :, >, [, ], (, ), *, _, `

Content to translate:

""",
        ("zh", "en"): """Translate the following Chinese content to English. Output ONLY the translated content, nothing else.

Rules:
- Headings (# ## ###): translate to English
- Body text: translate to fluent English
- Code blocks (```...```): protected by placeholders, do NOT modify them
- Inline code (`code`): keep as-is
- Tables (| col | col |): keep structure, translate text only
- URLs: keep unchanged
- Keep ALL markdown characters: ```, |, #, -, :, >, [, ], (, ), *, _, `

Content to translate:

""",
        ("ja", "zh"): """Translate the following Japanese content to Chinese. Output ONLY the translated content, nothing else.

Rules:
- Headings (# ## ###): translate to Chinese
- Body text: translate to fluent Chinese
- Code blocks (```...```): protected by placeholders, do NOT modify them
- Inline code (`code`): keep as-is
- Tables (| col | col |): keep structure, translate text only
- URLs: keep unchanged
- Keep ALL markdown characters: ```, |, #, -, :, >, [, ], (, ), *, _, `

Content to translate:

""",
        ("zh", "ja"): """Translate the following Chinese content to Japanese. Output ONLY the translated content, nothing else.

Rules:
- Headings (# ## ###): translate to Japanese
- Body text: translate to fluent Japanese
- Code blocks (```...```): protected by placeholders, do NOT modify them
- Inline code (`code`): keep as-is
- Tables (| col | col |): keep structure, translate text only
- URLs: keep unchanged
- Keep ALL markdown characters: ```, |, #, -, :, >, [, ], (, ), *, _, `

Content to translate:

""",
        ("en", "ja"): """Translate the following English content to Japanese. Output ONLY the translated content, nothing else.

Rules:
- Headings (# ## ###): translate to Japanese
- Body text: translate to fluent Japanese
- Code blocks (```...```): protected by placeholders, do NOT modify them
- Inline code (`code`): keep as-is
- Tables (| col | col |): keep structure, translate text only
- URLs: keep unchanged
- Keep ALL markdown characters: ```, |, #, -, :, >, [, ], (, ), *, _, `

Content to translate:

""",
        ("ja", "en"): """Translate the following Japanese content to English. Output ONLY the translated content, nothing else.

Rules:
- Headings (# ## ###): translate to English
- Body text: translate to fluent English
- Code blocks (```...```): protected by placeholders, do NOT modify them
- Inline code (`code`): keep as-is
- Tables (| col | col |): keep structure, translate text only
- URLs: keep unchanged
- Keep ALL markdown characters: ```, |, #, -, :, >, [, ], (, ), *, _, `

Content to translate:

""",
        ("ko", "zh"): """Translate the following Korean content to Chinese. Output ONLY the translated content, nothing else.

Rules:
- Headings (# ## ###): translate to Chinese
- Body text: translate to fluent Chinese
- Code blocks (```...```): protected by placeholders, do NOT modify them
- Inline code (`code`): keep as-is
- Tables (| col | col |): keep structure, translate text only
- URLs: keep unchanged
- Keep ALL markdown characters: ```, |, #, -, :, >, [, ], (, ), *, _, `

Content to translate:

""",
        ("zh", "ko"): """Translate the following Chinese content to Korean. Output ONLY the translated content, nothing else.

Rules:
- Headings (# ## ###): translate to Korean
- Body text: translate to fluent Korean
- Code blocks (```...```): protected by placeholders, do NOT modify them
- Inline code (`code`): keep as-is
- Tables (| col | col |): keep structure, translate text only
- URLs: keep unchanged
- Keep ALL markdown characters: ```, |, #, -, :, >, [, ], (, ), *, _, `

Content to translate:

""",
        ("en", "ko"): """Translate the following English content to Korean. Output ONLY the translated content, nothing else.

Rules:
- Headings (# ## ###): translate to Korean
- Body text: translate to fluent Korean
- Code blocks (```...```): protected by placeholders, do NOT modify them
- Inline code (`code`): keep as-is
- Tables (| col | col |): keep structure, translate text only
- URLs: keep unchanged
- Keep ALL markdown characters: ```, |, #, -, :, >, [, ], (, ), *, _, `

Content to translate:

""",
        ("ko", "en"): """Translate the following Korean content to English. Output ONLY the translated content, nothing else.

Rules:
- Headings (# ## ###): translate to English
- Body text: translate to fluent English
- Code blocks (```...```): protected by placeholders, do NOT modify them
- Inline code (`code`): keep as-is
- Tables (| col | col |): keep structure, translate text only
- URLs: keep unchanged
- Keep ALL markdown characters: ```, |, #, -, :, >, [, ], (, ), *, _, `

Content to translate:

""",
        ("ja", "ko"): """Translate the following Japanese content to Korean. Output ONLY the translated content, nothing else.

Rules:
- Headings (# ## ###): translate to Korean
- Body text: translate to fluent Korean
- Code blocks (```...```): protected by placeholders, do NOT modify them
- Inline code (`code`): keep as-is
- Tables (| col | col |): keep structure, translate text only
- URLs: keep unchanged
- Keep ALL markdown characters: ```, |, #, -, :, >, [, ], (, ), *, _, `

Content to translate:

""",
        ("ko", "ja"): """Translate the following Korean content to Japanese. Output ONLY the translated content, nothing else.

Rules:
- Headings (# ## ###): translate to Japanese
- Body text: translate to fluent Japanese
- Code blocks (```...```): protected by placeholders, do NOT modify them
- Inline code (`code`): keep as-is
- Tables (| col | col |): keep structure, translate text only
- URLs: keep unchanged
- Keep ALL markdown characters: ```, |, #, -, :, >, [, ], (, ), *, _, `

Content to translate:

""",
    }
    key = (from_lang.lower(), to_lang.lower())
    if key in prompts:
        return prompts[key]
    return prompts[("en", "zh")]


def is_supported_direction(from_lang: str, to_lang: str) -> bool:
    """检查是否支持该翻译方向"""
    key = (from_lang.lower(), to_lang.lower())
    return key in TRANSLATION_PROMPTS


def get_supported_languages() -> list:
    """获取支持的语言列表"""
    return list(LANGUAGE_CONFIGS.keys())


def get_supported_directions() -> list:
    """获取支持的翻译方向列表"""
    return list(TRANSLATION_PROMPTS.keys())
