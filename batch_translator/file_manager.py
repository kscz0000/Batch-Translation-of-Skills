"""
文件管理 - 专注文件I/O操作
"""

import shutil
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, TYPE_CHECKING

from .config import TranslationConfig
from .exceptions import FileOperationError, BackupError
from .utils import count_chinese_chars

if TYPE_CHECKING:
    from .services.base import TranslationService


class FileManager:
    """文件I/O操作"""

    # 不需要翻译的文件名
    SKIP_FILENAMES = frozenset({
        'LICENSE', 'LICENSE.txt', 'LICENSE.md',
        '.gitignore', '.clawhubignore',
        'package.json', 'package-lock.json',
    })

    # 已翻译/对照文件的后缀模式
    _SKIP_SUFFIXES = ('-CN.md', '-original.md')
    _SKIP_IN_NAME = '.zh-CN'

    # 二进制文件扩展名（不翻译）
    _BINARY_EXTENSIONS = frozenset({
        '.pdf', '.DS_Store', '.exe', '.dll', '.so', '.dylib',
        '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico',
        '.mp3', '.mp4', '.wav', '.avi', '.mov',
        '.zip', '.tar', '.gz', '.rar', '.7z',
        '.ttf', '.otf', '.woff', '.woff2',
        '.skill', '.claw',
    })

    def __init__(self, config: TranslationConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)

    def read(self, skill_name: str) -> str:
        """读取技能文件内容"""
        path = self._skill_path(skill_name)
        if not path.exists():
            raise FileOperationError(f"文件不存在: {path}", skill_name=skill_name)
        try:
            return path.read_text(encoding='utf-8')
        except (UnicodeDecodeError, IOError) as e:
            raise FileOperationError(f"读取失败: {e}", skill_name=skill_name)

    def write(self, skill_name: str, content: str) -> None:
        """写入技能文件内容"""
        path = self._skill_path(skill_name)
        try:
            path.write_text(content, encoding='utf-8')
        except IOError as e:
            raise FileOperationError(f"写入失败: {e}", skill_name=skill_name)

    def backup(self, skill_name: str) -> bool:
        """创建备份

        Returns:
            bool: 是否成功创建备份
        """
        src = self._skill_path(skill_name)
        dst = self._backup_path(skill_name)
        skill_dir = src.parent

        try:
            dst.mkdir(exist_ok=True)
            if src.exists():
                shutil.copy2(src, dst / self.config.skill_file)
            else:
                self.logger.warning(f"技能文件不存在，跳过备份: {src}")
                return False

            refs_dir = skill_dir / 'references'
            if refs_dir.is_dir():
                shutil.copytree(refs_dir, dst / 'references', dirs_exist_ok=True)

            for f in skill_dir.glob('*.md'):
                if f.name not in (self.config.skill_file, self.config.meta_file):
                    shutil.copy2(f, dst / f.name)

            for subdir in skill_dir.iterdir():
                if subdir.is_dir() and subdir.name not in ('references', 'raw'):
                    for f in subdir.rglob('*'):
                        if f.is_file():
                            rel_path = f.relative_to(skill_dir)
                            dst_path = dst / rel_path
                            dst_path.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(f, dst_path)
            return True
        except (IOError, OSError) as e:
            raise BackupError(f"备份失败: {e}", skill_name=skill_name)

    def restore(self, skill_name: str) -> str:
        """恢复备份内容"""
        bak = self._backup_path(skill_name)
        bak_file = bak / self.config.skill_file
        if not bak_file.exists():
            self.logger.warning(f"备份文件不存在: {bak_file}")
            return ""
        try:
            return bak_file.read_text(encoding='utf-8')
        except Exception as e:
            self.logger.error(f"读取备份失败: {e}")
            return ""

    def cleanup(self, skill_name: str) -> None:
        """删除备份"""
        bak = self._backup_path(skill_name)
        if bak.exists():
            shutil.rmtree(bak)

    def update_meta(self, skill_name: str) -> bool:
        """更新meta.json"""
        meta_file = self._skill_path(skill_name).parent / self.config.meta_file
        try:
            meta = json.loads(meta_file.read_text()) if meta_file.exists() else {}
            meta.update({
                'locale': 'zh-CN',
                'translator': 'Clawd',
                'translatedAt': datetime.now().isoformat()
            })
            meta_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
            return True
        except (json.JSONDecodeError, IOError):
            return False

    def list_files(self, skill_name: str, subdir: Optional[str] = None, translatable_only: bool = False) -> List[str]:
        """获取指定目录下的文件列表

        Args:
            skill_name: 技能名称
            subdir: 子目录名（如 'references'）
            translatable_only: 是否只返回可翻译的 .md 文件（排除已翻译/配置/非Markdown文件）
        """
        skill_dir = self._skill_path(skill_name).parent
        target_dir = skill_dir / subdir if subdir else skill_dir

        if not target_dir.is_dir():
            return []

        exclude = {self.config.skill_file, self.config.meta_file} if not subdir else set()

        files = [
            f.name for f in target_dir.glob('*')
            if f.is_file()
            and f.name not in exclude
            and f.suffix not in self._BINARY_EXTENSIONS
        ]

        if translatable_only:
            files = [f for f in files if self._should_translate_file(f)]

        return files

    def _should_translate_file(self, filename: str) -> bool:
        """判断文件是否应该被翻译

        只翻译 .md 文件，排除：
        - 非 Markdown 文件
        - 配置/法律文件（LICENSE, .gitignore 等）
        - 已翻译文件（.zh-CN.md, *-CN.md, *-original.md）
        """
        if not filename.endswith('.md'):
            return False
        if filename in self.SKIP_FILENAMES:
            return False
        if self._SKIP_IN_NAME in filename:
            return False
        if any(filename.endswith(s) for s in self._SKIP_SUFFIXES):
            return False
        return True

    def read_file(self, skill_name: str, filename: str, subdir: Optional[str] = None) -> str:
        """读取文件"""
        base = self._skill_path(skill_name).parent
        path = base / subdir / filename if subdir else base / filename

        if not path.exists():
            raise FileOperationError(f"文件不存在: {path}", skill_name=skill_name)
        try:
            return path.read_text(encoding='utf-8')
        except (UnicodeDecodeError, IOError) as e:
            raise FileOperationError(f"读取失败: {e}", skill_name=skill_name)

    def write_file(self, skill_name: str, filename: str, content: str, subdir: Optional[str] = None) -> None:
        """写入文件"""
        base = self._skill_path(skill_name).parent
        if subdir:
            (base / subdir).mkdir(exist_ok=True)
        path = base / subdir / filename if subdir else base / filename

        try:
            path.write_text(content, encoding='utf-8')
        except IOError as e:
            raise FileOperationError(f"写入失败: {e}", skill_name=skill_name)

    def translate_directory(
        self,
        skill_name: str,
        translator: 'TranslationService',
        subdir: Optional[str] = None,
        log_prefix: str = "文件"
    ) -> Dict[str, bool]:
        """翻译目录下所有可翻译的 .md 文件（带备份和验证失败恢复）"""
        results = {}
        files = self.list_files(skill_name, subdir, translatable_only=True)
        # 单文件的中文阈值取全局阈值的 1/10（附属文件通常较短），
        # 但不低于 10（避免翻译只产出了极少量中文就通过）
        min_chars = max(10, self.config.min_chinese_chars // 10)

        for filename in files:
            try:
                original = self.read_file(skill_name, filename, subdir)

                translated = translator.translate(original)
                self.write_file(skill_name, filename, translated, subdir)

                chinese_chars = count_chinese_chars(translated)
                if chinese_chars < min_chars:
                    self.logger.warning(f"翻译{log_prefix} {skill_name}/{filename} 中文字符过少({chinese_chars}<{min_chars})，恢复备份")
                    self.write_file(skill_name, filename, original, subdir)
                    results[filename] = False
                else:
                    results[filename] = True
                    self.logger.info(f"翻译{log_prefix} {skill_name}/{filename} 成功")
            except Exception as e:
                self.logger.warning(f"翻译{log_prefix}失败 {skill_name}/{filename}: {e}")
                results[filename] = False

        return results

    def translate_all_references(self, skill_name: str, translator: 'TranslationService') -> Dict[str, bool]:
        """翻译 references/ 目录"""
        return self.translate_directory(skill_name, translator, subdir='references', log_prefix="reference")

    def get_reference_files(self, skill_name: str) -> List[str]:
        """获取 references 目录下的 .md 文件名列表"""
        refs_dir = self._base_path(skill_name) / 'references'
        if not refs_dir.is_dir():
            return []
        return [f.name for f in refs_dir.glob('*.md') if f.is_file()]

    def read_reference(self, skill_name: str, filename: str) -> str:
        """读取 references 目录下的文件"""
        return self.read_file(skill_name, filename, subdir='references')

    def restore_directory(self, skill_name: str, subdir: Optional[str] = None, log_prefix: str = "文件") -> Dict[str, bool]:
        """恢复目录备份"""
        results = {}
        bak_dir = self._backup_path(skill_name) / subdir if subdir else self._backup_path(skill_name)

        if not bak_dir.exists():
            return results

        for bak_file in bak_dir.glob('*'):
            if not bak_file.is_file():
                continue
            try:
                content = bak_file.read_text(encoding='utf-8')
                self.write_file(skill_name, bak_file.name, content, subdir)
                results[bak_file.name] = True
            except Exception as e:
                self.logger.error(f"恢复{log_prefix}失败 {skill_name}/{bak_file.name}: {e}")
                results[bak_file.name] = False

        return results

    def _skill_path(self, skill_name: str) -> Path:
        """获取技能文件路径"""
        return self._base_path(skill_name) / self.config.skill_file

    def _backup_path(self, skill_name: str) -> Path:
        """获取备份目录路径"""
        return self._base_path(skill_name) / self.config.backup_dir

    def _base_path(self, skill_name: str) -> Path:
        """获取技能基础目录"""
        return self.config.base_path.joinpath(*skill_name.split('/'))
