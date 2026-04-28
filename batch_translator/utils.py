"""
工具函数模块

提供通用工具函数
"""

import re
import yaml
from typing import Tuple, Dict, List, Any


def count_chinese_chars(text: str) -> int:
    """
    统计中文字符数量

    Args:
        text: 输入文本

    Returns:
        中文字符数量
    """
    return sum(1 for char in text if '\u4e00' <= char <= '\u9fff')


def count_target_chars(text: str, lang: str) -> int:
    """
    统计目标语言的字符数量

    Args:
        text: 输入文本
        lang: 目标语言代码 (en, zh, ja, ko)

    Returns:
        目标语言字符数量
    """
    if lang == "zh":
        return sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
    elif lang == "ja":
        return sum(1 for char in text if (
            '\u3040' <= char <= '\u309f' or
            '\u30a0' <= char <= '\u30ff' or
            '\u4e00' <= char <= '\u9fff'
        ))
    elif lang == "ko":
        return sum(1 for char in text if (
            '\uac00' <= char <= '\ud7af' or
            '\u1100' <= char <= '\u11ff' or
            '\u3130' <= char <= '\u318f'
        ))
    elif lang == "en":
        return sum(1 for char in text if char.isascii() and char.isalpha())
    return 0


YAML_MULTILINE_INDICATORS = ('|', '>', '>-', '|+', '>+')
FRONTMATTER_SEPARATORS = ('---', '***')
_TOP_LEVEL_KEYS = frozenset({
    'name', 'version', 'allowed-tools', 'user-invocable',
    'argument-hint', 'category', 'tags', 'metadata'
})


def _is_separator(line: str) -> bool:
    return line.strip() in FRONTMATTER_SEPARATORS


def _is_top_level_key(line: str) -> bool:
    stripped = line.strip()
    key = stripped.split(':')[0].lower()
    return key in _TOP_LEVEL_KEYS


def _has_multiline_indicator(line: str) -> bool:
    return any(line.strip().endswith(ind) for ind in YAML_MULTILINE_INDICATORS)


def _is_list_item(line: str) -> bool:
    return line.strip().startswith('-')


def _is_continuation_of_multiline(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if _is_list_item(line):
        return False
    if stripped.startswith(' '):
        return False
    if ':' in stripped and not _is_top_level_key(line):
        return True
    if _is_top_level_key(line) and not stripped.endswith(':'):
        return True
    return False


def _fix_frontmatter_indentation(lines: List[str]) -> List[str]:
    """
    修复 frontmatter 行中缺少的缩进

    处理 description: | 等多行值后面没有缩进的情况

    Args:
        lines: frontmatter 行列表

    Returns:
        修复后的行列表
    """
    result: List[str] = []
    in_multiline_value = False

    for line in lines:
        stripped = line.strip()

        if not stripped or _is_separator(stripped):
            result.append(line)
            continue

        if ':' in stripped:
            if _has_multiline_indicator(stripped):
                in_multiline_value = True
                result.append(line)
            elif _is_top_level_key(stripped):
                in_multiline_value = False
                result.append(line)
            else:
                in_multiline_value = True
                result.append('  ' + line if not line.startswith(' ') else line)
        elif in_multiline_value and _is_continuation_of_multiline(line):
            result.append('  ' + line)
        elif in_multiline_value and _is_top_level_key(line):
            in_multiline_value = False
            result.append(line)
        elif in_multiline_value:
            result.append('  ' + line if not line.startswith(' ') else line)
        else:
            result.append(line)

    return result


def is_chinese_content(content: str, min_chars: int = 200, ratio: float = 0.3) -> bool:
    """
    检查内容是否主要是中文

    Args:
        content: 输入内容
        min_chars: 最少中文字符数
        ratio: 最小中文字符比例

    Returns:
        是否主要是中文
    """
    chinese_count = count_chinese_chars(content)
    total_chars = len(content)
    return chinese_count >= min_chars and (chinese_count / total_chars) >= ratio


def extract_frontmatter(content: str) -> Tuple[Dict[str, str], str]:
    """
    从内容中提取 YAML frontmatter

    支持 --- 和 *** 两种分隔符

    Args:
        content: 完整内容

    Returns:
        (frontmatter字典, body内容)
    """
    lines = content.split('\n')

    if len(lines) < 3:
        return {}, content

    start_marker = lines[0].strip()
    if start_marker not in ('---', '***'):
        return {}, content

    end_marker = '---' if start_marker == '---' else '***'
    if end_marker not in lines[1:]:
        return {}, content

    end_idx = 1
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == end_marker:
            end_idx = i
            break

    frontmatter_lines = lines[1:end_idx]
    body = '\n'.join(lines[end_idx + 1:])

    try:
        frontmatter = yaml.safe_load('\n'.join(frontmatter_lines))
        if frontmatter is None:
            frontmatter = {}
        result = {}
        for key, value in frontmatter.items():
            if value is not None:
                result[str(key)] = str(value)
        return result, body
    except yaml.YAMLError:
        fixed_lines = _fix_frontmatter_indentation(frontmatter_lines)
        try:
            frontmatter = yaml.safe_load('\n'.join(fixed_lines))
            if frontmatter is None:
                frontmatter = {}
            result = {}
            for key, value in frontmatter.items():
                if value is not None:
                    result[str(key)] = str(value)
            return result, body
        except yaml.YAMLError:
            frontmatter = {}
            for line in frontmatter_lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    value = value.strip().strip('"').strip("'")
                    if value not in ('|', '>', '>-'):
                        frontmatter[key.strip()] = value
            return frontmatter, body


def is_description_translated(description: str, min_chars: int = 10) -> bool:
    """判断 description 是否已完整翻译为中文

    只要包含足够的中文字符即视为已翻译。
    description 中通常包含大量刻意保留的英文关键词（如触发词列表），
    因此不应要求中文与英文成比例，只要有中文翻译主体即可。

    Args:
        description: description 字段内容
        min_chars: 最少中文字符数（默认10，但实际阈值取 min(5, min_chars)）

    Returns:
        是否已翻译
    """
    chinese = count_chinese_chars(description)
    # 只要包含5个以上中文字符即视为已翻译
    # description 中的英文关键词列表是刻意保留的，不应以此判定翻译不完整
    return chinese >= 5


def check_description_translated(content: str, min_chars: int = 10) -> bool:
    """
    检查内容中 description 字段是否已翻译为中文

    Args:
        content: 完整内容
        min_chars: 最少中文字符数

    Returns:
        是否已翻译
    """
    frontmatter, _ = extract_frontmatter(content)
    description = frontmatter.get('description', '')
    return is_description_translated(description, min_chars)


def parse_metadata(content: str) -> Dict[str, Any]:
    """
    解析frontmatter元数据

    Args:
        content: 完整内容

    Returns:
        元数据字典
    """
    frontmatter, _ = extract_frontmatter(content)

    result = {
        'name': frontmatter.get('name', ''),
        'description': frontmatter.get('description', ''),
        'locale': frontmatter.get('locale', ''),
    }

    # 尝试解析嵌套的metadata
    if 'metadata:' in content:
        metadata_match = re.search(r'metadata:\s*\n((?:\s{2,}.+\n)*)', content)
        if metadata_match:
            metadata_lines = metadata_match.group(1).split('\n')
            for line in metadata_lines:
                if ':' in line:
                    key, value = line.strip().split(':', 1)
                    result[f'metadata_{key.strip()}'] = value.strip()

    return result


def truncate_text(text: str, max_length: int = 100) -> str:
    """
    截断文本

    Args:
        text: 输入文本
        max_length: 最大长度

    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + '...'


def format_time(seconds: float) -> str:
    """
    格式化时间

    Args:
        seconds: 秒数

    Returns:
        格式化的时间字符串
    """
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    else:
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds:.0f}s"


def format_size(bytes_count: int) -> str:
    """
    格式化文件大小

    Args:
        bytes_count: 字节数

    Returns:
        格式化的大小字符串
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_count < 1024:
            return f"{bytes_count:.1f}{unit}"
        bytes_count /= 1024
    return f"{bytes_count:.1f}TB"
