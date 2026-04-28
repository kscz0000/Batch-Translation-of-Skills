"""
MiniMax 翻译服务实现
"""

import os
import json
import re
import time
import logging
import urllib.request
import urllib.error
import socket
from typing import Optional

from .base import TranslationService
from ..exceptions import TranslationServiceError
from ..utils import count_chinese_chars, count_target_chars


class MiniMaxTranslation(TranslationService):
    """MiniMax API 翻译服务，支持多语言"""

    API_URL = "https://api.minimax.chat/v1/text/chatcompletion_v2"
    DEFAULT_TIMEOUT = 300
    MAX_RETRIES = 3
    MAX_TOKENS = 16000
    MAX_CONTENT_LENGTH = 6000
    TEMPERATURE = 0.3
    CODE_BLOCK_PLACEHOLDER = "[KEEP_CODE_BLOCK_"
    CODE_BLOCK_PLACEHOLDER_END = "_DO_NOT_REMOVE]"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "MiniMax-M2.7-HighSpeed",
        from_lang: str = "en",
        to_lang: str = "zh",
    ):
        """初始化 MiniMax 翻译服务

        Args:
            api_key: API密钥
            model: 模型名称
            from_lang: 源语言代码 (en, zh, ja)
            to_lang: 目标语言代码 (en, zh, ja)
        """
        super().__init__(model=model, from_lang=from_lang, to_lang=to_lang)
        self.api_key = api_key or os.getenv("MINIMAX_API_KEY")
        self.logger = logging.getLogger(self.__class__.__name__)

    def _preprocess_content(self, content: str) -> tuple:
        """预处理内容，标记需要保护的编程语言代码块和代码注释"""
        code_blocks = []

        protected_langs = [
            'bash', 'sh', 'python', 'py', 'js', 'javascript', 'typescript', 'ts',
            'json', 'yaml', 'yml', 'toml', 'html', 'css', 'scss', 'sql',
            'go', 'rust', 'java', 'cpp', 'c', 'ruby', 'php', 'perl',
            'shell', 'powershell', 'cli', 'cmd', 'dockerfile', 'makefile',
            'xml', 'graphql', 'regex', 'nginx', 'apache'
        ]

        def replace_code_block(match):
            full_match = match.group(0)
            first_line = full_match.split('\n')[0].strip()

            for lang in protected_langs:
                if first_line == f'```{lang}' or first_line == f'```{lang}.*':
                    code_blocks.append(full_match)
                    return f"{self.CODE_BLOCK_PLACEHOLDER}{len(code_blocks) - 1}{self.CODE_BLOCK_PLACEHOLDER_END}"

            return full_match

        processed = re.sub(r'```[\s\S]*?```', replace_code_block, content)
        return processed, code_blocks

    def _preprocess_code_file(self, content: str, filename: str) -> tuple:
        """预处理代码文件，保护代码行，只翻译注释"""
        code_lines = []
        comment_lines = []
        
        ext = filename.split('.')[-1].lower() if '.' in filename else ''
        
        for line in content.split('\n'):
            stripped = line.strip()
            
            if ext in ('sh', 'bash'):
                if stripped.startswith('#'):
                    comment_lines.append(line)
                else:
                    code_lines.append(line)
            elif ext in ('py', 'python'):
                if stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
                    comment_lines.append(line)
                else:
                    code_lines.append(line)
            elif ext in ('js', 'ts', 'jsx', 'tsx', 'javascript', 'typescript'):
                if stripped.startswith('//') or stripped.startswith('/*') or stripped.startswith('*'):
                    comment_lines.append(line)
                else:
                    code_lines.append(line)
            elif ext in ('java', 'cpp', 'c', 'go', 'rust', 'ruby', 'php'):
                if stripped.startswith('//') or stripped.startswith('/*') or stripped.startswith('*'):
                    comment_lines.append(line)
                else:
                    code_lines.append(line)
            else:
                code_lines.append(line)
        
        return '\n'.join(code_lines), '\n'.join(comment_lines)

    def _postprocess_content(self, content: str, code_blocks: list) -> str:
        """后处理内容，恢复代码块"""
        def replace_placeholder(match):
            idx = int(match.group(1))
            if idx < len(code_blocks):
                return code_blocks[idx]
            # 占位符索引越界，返回原文（避免异常）
            return match.group(0)

        pattern = f'{re.escape(self.CODE_BLOCK_PLACEHOLDER)}(\\d+){re.escape(self.CODE_BLOCK_PLACEHOLDER_END)}'
        result = re.sub(pattern, replace_placeholder, content)

        # 检查是否有占位符被 LLM 吞掉
        remaining_placeholders = re.findall(pattern, result)
        if remaining_placeholders:
            self.logger.warning(
                f"仍有 {len(remaining_placeholders)} 个代码块占位符未被恢复，"
                f"可能 LLM 吞掉了部分占位符"
            )

        return result

    def _ensure_frontmatter(self, original: str, translated: str) -> str:
        """确保翻译结果包含 YAML frontmatter

        如果 AI 丢失了 frontmatter，从原始内容中提取并添加
        支持 --- 和 *** 两种分隔符

        修复：当 frontmatter 丢失时，不能直接使用原始 frontmatter，
        因为 description 可能已经被翻译了
        """
        if not translated or not isinstance(translated, str):
            return translated if translated else original or ""

        if translated.strip().startswith(('---', '***')):
            return translated

        if not original:
            return translated

        fm_match = re.match(r'^(?:---|\*\*\*)\n.*?\n(?:---|\*\*\*)\n', original, re.DOTALL)
        if not fm_match:
            return translated

        original_frontmatter = fm_match.group(0)

        translated_lines = translated.split('\n')
        if translated_lines[0].strip() in ('---', '***'):
            return translated

        self.logger.warning("Frontmatter missing in translation, attempting to restore...")

        extracted_fm = self._extract_frontmatter_from_content(original, translated)
        if extracted_fm:
            return extracted_fm + '\n' + translated
        return original_frontmatter + translated

    def _extract_frontmatter_from_content(self, original: str, translated: str) -> str:
        """从原始内容中提取 frontmatter 结构，用翻译内容中的 description 替换

        当 AI 没有正确翻译 frontmatter 时使用此方法
        """
        fm_match = re.match(r'^(---|\*\*\*)', original.strip())
        if not fm_match:
            return ""

        delimiter = fm_match.group(1)
        end_delimiter = delimiter

        lines = original.split('\n')
        fm_lines = [lines[0]]

        in_frontmatter = True
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == end_delimiter:
                fm_lines.append(line)
                break
            fm_lines.append(line)

        frontmatter_str = '\n'.join(fm_lines)

        name_value = ""
        if 'name:' in frontmatter_str:
            name_match = re.search(r'^name:\s*(.+)$', frontmatter_str, re.MULTILINE)
            name_value = name_match.group(1).strip() if name_match else ""

        chinese_chars = sum(1 for c in translated if '\u4e00' <= c <= '\u9fff')

        if chinese_chars > 50:
            description_value = self._extract_description_candidate(translated)
            if description_value:
                desc_placeholder = f'description: "{description_value}"'
                if name_value:
                    new_frontmatter = f'{delimiter}\nname: {name_value}\n{desc_placeholder}\n{end_delimiter}\n'
                else:
                    new_frontmatter = f'{delimiter}\n{desc_placeholder}\n{end_delimiter}\n'
                self.logger.info(f"Restored frontmatter with translated description (chars: {chinese_chars})")
                return new_frontmatter

        return ""

    def _extract_description_candidate(self, content: str) -> str:
        """从翻译后的内容中提取可能的 description

        策略：找到第一个标题（#）之前的中文文本
        """
        lines = content.split('\n')

        candidate_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('#'):
                break
            if stripped and not stripped.startswith('```'):
                chinese_in_line = sum(1 for c in stripped if '\u4e00' <= c <= '\u9fff')
                if chinese_in_line > 0:
                    candidate_lines.append(stripped)

        if candidate_lines:
            desc = ' '.join(candidate_lines)
            return desc[:500]

        return ""

    def _clean_translation(self, text: str) -> str:
        """清理翻译结果中多余的包裹代码块标记

        只移除 LLM 将整个响应包裹在一个 ```...``` 中的情况。
        不会误删文件末尾正当的代码块闭合标记。
        """
        text = text.strip()

        # 检测整个响应被 ```...``` 包裹的情况：
        # 首行 ``` + 末行 ```，且内部没有其他 ```（说明这是一个包裹层而非内容代码块）
        match = re.match(r'^```[a-z]*\n([\s\S]*?)\n```$', text)
        if match:
            inner = match.group(1)
            if '```' not in inner:
                return inner

        return text

    def _translate_chunk(self, content: str) -> str:
        """翻译单个内容块"""
        processed_content, code_blocks = self._preprocess_content(content)
        prompt = self.get_translation_prompt(processed_content)

        for attempt in range(self.MAX_RETRIES):
            try:
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }

                payload = {
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": self.TEMPERATURE,
                    "max_tokens": self.MAX_TOKENS
                }

                req = urllib.request.Request(
                    self.API_URL,
                    data=json.dumps(payload).encode('utf-8'),
                    headers=headers,
                    method='POST'
                )

                with urllib.request.urlopen(req, timeout=self.DEFAULT_TIMEOUT) as response:
                    result = json.loads(response.read().decode('utf-8'))
                    self.logger.debug(f"MiniMax raw response: {result}")

                    translated = self._extract_translation(result)
                    restored = self._postprocess_content(translated, code_blocks)
                    cleaned = self._clean_translation(restored)
                    return cleaned

            except (TimeoutError, socket.timeout) as e:
                self.logger.warning(f"Timeout (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise TimeoutError(f"MiniMax timeout after {self.MAX_RETRIES} attempts") from e
            except urllib.error.HTTPError as e:
                error_body = e.read().decode('utf-8') if e.fp else ''
                self.logger.error(f"MiniMax API error {e.code}: {error_body}")
                raise Exception(f"MiniMax API error: {e.code}")
            except urllib.error.URLError as e:
                self.logger.warning(f"Network error (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise Exception(f"MiniMax network error after {self.MAX_RETRIES} attempts")
            except Exception as e:
                self.logger.error(f"MiniMax translation failed: {e}")
                raise

    def _split_into_chunks(self, content: str) -> list:
        """智能分割：优先按##标题分段，保持结构完整"""
        sections = re.split(r'\n(?=##\s)', content)
        chunks, current, length = [], [], 0

        for section in sections:
            section_len = len(section)
            if length + section_len > self.MAX_CONTENT_LENGTH and current:
                chunks.append('\n'.join(current))
                current, length = [], 0
            current.append(section)
            length += section_len

        if current:
            chunks.append('\n'.join(current))

        return chunks

    def translate(self, content: str) -> str:
        """翻译内容（分段翻译：frontmatter 保护机制，支持多语言）

        流程：
        1. 分离 frontmatter 和 body
        2. 单独翻译 description 字段
        3. 单独翻译 body（不含 frontmatter）
        4. 重新组装：原 frontmatter 结构 + 翻译后的 description + 翻译后的 body
        """
        if not self.api_key:
            raise ValueError("MiniMax API key not configured")

        from_lang, to_lang = self.get_language_pair()

        # 提取 frontmatter 和 body
        from ..utils import extract_frontmatter
        frontmatter, body = extract_frontmatter(content)

        if not frontmatter:
            self.logger.debug("No frontmatter found, translating whole content")
            translated = self._translate_chunk(content)
            return self._ensure_frontmatter(content, translated)

        # 1. 翻译 description
        original_desc = frontmatter.get('description', '')
        translated_desc = ''
        if original_desc:
            try:
                translated_desc = self._translate_description(original_desc)
                self.logger.debug(f"Description translated: {len(translated_desc)} chars")
            except Exception as e:
                raise TranslationServiceError(f"description翻译失败: {e}")

        # 2. 翻译 body
        translated_body = ''
        if body.strip():
            try:
                translated_body = self._translate_body(body)
            except Exception as e:
                raise TranslationServiceError(f"body翻译失败: {e}")

        # 3. 重新组装 frontmatter
        assembled = self._assemble_frontmatter(content, frontmatter, translated_desc)

        # 4. 组合最终结果
        result = assembled + '\n' + translated_body if translated_body else assembled

        # 5. 翻译结果校验
        self._validate_translation(content, result, from_lang, to_lang)

        return result

    def _validate_translation(self, original: str, translated: str, from_lang: str, to_lang: str) -> None:
        """验证翻译结果"""
        from ..utils import count_target_chars

        original_chars = count_target_chars(original, to_lang)
        result_chars = count_target_chars(translated, to_lang)

        if original_chars > 0:
            if result_chars < 10:
                raise TranslationServiceError(
                    f"翻译结果无效：目标语言字符数仅 {result_chars}"
                )
        else:
            min_chars = 10
            if result_chars - original_chars < min_chars:
                raise TranslationServiceError(
                    f"翻译结果无效：目标语言字符数仅增加 {result_chars - original_chars}（原文{original_chars}→译文{result_chars}）"
                )

    def _translate_description(self, description: str) -> str:
        """单独翻译 description 字段"""
        clean_desc = description.strip()
        if clean_desc.startswith('|') or clean_desc.startswith('>'):
            lines = [l.strip() for l in clean_desc.split('\n') if l.strip()]
            if lines and lines[0] in ('|', '>', '>-', '|+'):
                lines = lines[1:]
            clean_desc = ' '.join(lines)

        prompt = self.get_description_prompt(clean_desc)
        translated = self._call_api(prompt)
        return translated.strip().strip('"').strip("'")

    def _translate_body(self, body: str) -> str:
        """翻译 body 部分（不含 frontmatter）"""
        processed_content, code_blocks = self._preprocess_content(body)
        prompt = self.get_body_prompt(processed_content)

        translated = self._call_api(prompt)
        restored = self._postprocess_content(translated, code_blocks)
        return self._clean_translation(restored)

    def _call_api(self, prompt: str) -> str:
        """调用 MiniMax API（含重试）"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.TEMPERATURE,
            "max_tokens": self.MAX_TOKENS
        }

        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                req = urllib.request.Request(
                    self.API_URL,
                    data=json.dumps(payload).encode('utf-8'),
                    headers=headers,
                    method='POST'
                )

                with urllib.request.urlopen(req, timeout=self.DEFAULT_TIMEOUT) as response:
                    result = json.loads(response.read().decode('utf-8'))
                    return self._extract_translation(result)

            except (TimeoutError, socket.timeout) as e:
                self.logger.warning(f"Timeout (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}")
                last_error = e
            except urllib.error.HTTPError as e:
                error_body = e.read().decode('utf-8') if e.fp else ''
                self.logger.error(f"MiniMax API error {e.code}: {error_body}")
                raise Exception(f"MiniMax API error: {e.code}")
            except urllib.error.URLError as e:
                self.logger.warning(f"Network error (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}")
                last_error = e
            except Exception as e:
                # _extract_translation 抛出的异常（如空响应），进行重试
                self.logger.warning(f"Response parsing error (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}")
                last_error = e

            if attempt < self.MAX_RETRIES - 1:
                time.sleep(2 ** attempt)

        raise Exception(f"MiniMax API failed after {self.MAX_RETRIES} attempts: {last_error}")

    def _assemble_frontmatter(self, original: str, frontmatter: dict, translated_desc: str) -> str:
        """重新组装 frontmatter

        保留原始结构和非翻译字段，替换 description 为翻译后的版本
        """
        # 确定分隔符（保持与原文一致）
        delimiter = '---'
        if original.strip().startswith('***'):
            delimiter = '***'

        lines = []
        in_original_fm = False
        fm_ended = False

        for line in original.split('\n'):
            stripped = line.strip()

            if not fm_ended:
                if stripped == delimiter and not in_original_fm:
                    in_original_fm = True
                    lines.append(line)
                    continue
                elif stripped == delimiter and in_original_fm:
                    fm_ended = True
                    lines.append(line)
                    continue

                if in_original_fm:
                    # 处理 description 字段
                    if stripped.startswith('description:'):
                        if translated_desc:
                            # 转义双引号
                            escaped_desc = translated_desc.replace('"', '\\"')
                            lines.append(f'description: "{escaped_desc}"')
                        else:
                            lines.append(line)
                        # 跳过多行 description 的后续行
                        continue

                    # 跳过多行 description 的续行（缩进的行）
                    if line.startswith('  ') and not any(
                        stripped.startswith(k + ':') for k in ('name', 'version', 'metadata', 'origin', 'category', 'tags')
                    ):
                        # 这可能是多行 description 的续行，跳过
                        continue

                    # 其他字段保持原样
                    lines.append(line)
            else:
                break

        result = '\n'.join(lines)
        return result

    def _extract_translation(self, result: dict) -> str:
        """从 API 响应中提取翻译结果"""
        if choices := result.get('choices'):
            first_choice = choices[0]
            message = first_choice.get('message', {})

            if translated := message.get('content'):
                return translated

            if translated := message.get('reasoning_content'):
                return translated

            if translated := first_choice.get('text'):
                return translated

        if translated := result.get('text'):
            return translated

        # 记录原始响应以便诊断
        self.logger.debug(f"Unexpected MiniMax response: {json.dumps(result, ensure_ascii=False)[:500]}")
        raise Exception(f"Unexpected MiniMax response format")

    def is_available(self) -> bool:
        """检查服务是否可用"""
        return bool(self.api_key)
