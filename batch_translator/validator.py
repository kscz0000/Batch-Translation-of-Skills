"""
翻译质量验证模块

只做三件事：
1. 检查有没有足够的中文
2. 检查 description 是否翻译
3. 检查 frontmatter 格式是否完整
"""

import re
import logging
from dataclasses import dataclass, field
from typing import List

from .utils import count_chinese_chars, extract_frontmatter, is_description_translated
from .models import TranslationStatus


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    chinese_chars: int = 0
    description_translated: bool = False
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class TranslationValidator:
    """翻译质量验证器"""

    # description 中最少的中文字符数
    MIN_DESC_CHINESE_CHARS = 10

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def check_status(self, content: str, min_chinese_chars: int = 200) -> TranslationStatus:
        """检查翻译状态"""
        chinese_chars = count_chinese_chars(content)
        fm, _ = extract_frontmatter(content)
        description = fm.get('description', '')

        if chinese_chars == 0:
            return TranslationStatus.NOT_TRANSLATED

        if not is_description_translated(description, self.MIN_DESC_CHINESE_CHARS):
            return TranslationStatus.INCOMPLETE

        if chinese_chars < min_chinese_chars:
            return TranslationStatus.INCOMPLETE

        return TranslationStatus.TRANSLATED

    def validate(self, original: str, translated: str, min_chinese_chars: int = 200) -> ValidationResult:
        """验证翻译质量——只检查三件事：中文够不够、description 翻没翻、frontmatter 还在不在"""
        issues = []
        warnings = []

        _, body_trans = extract_frontmatter(translated)
        chinese_count = count_chinese_chars(translated)

        # 1. description 检查
        fm_trans, _ = extract_frontmatter(translated)
        desc = fm_trans.get('description', '')
        desc_translated = is_description_translated(desc, self.MIN_DESC_CHINESE_CHARS)

        if not desc:
            issues.append("description字段缺失")
        elif not desc_translated:
            issues.append("description未翻译")

        # 2. 中文字符数检查
        if chinese_count == 0:
            issues.append("正文完全没有中文翻译")
        elif chinese_count < min_chinese_chars:
            # 看看正文（去 frontmatter）里有没有中文
            body_chinese = count_chinese_chars(body_trans)
            if body_chinese == 0:
                issues.append(f"正文没有中文翻译 (仅frontmatter有{chinese_count}字)")
            else:
                warnings.append(f"中文字符数偏少: {chinese_count}<{min_chinese_chars}")

        # 3. frontmatter 格式检查
        if not translated.strip().startswith(('---', '***')):
            issues.append("缺少YAML frontmatter")

        # 4. 代码块闭合检查
        code_blocks = re.findall(r'```[\s\S]*?```', translated)
        for block in code_blocks:
            if block.count('```') != 2:
                issues.append("代码块未正确闭合")

        return ValidationResult(
            is_valid=len(issues) == 0,
            chinese_chars=chinese_count,
            description_translated=desc_translated,
            issues=issues,
            warnings=warnings,
        )
