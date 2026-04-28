"""
配置模块
"""

import os
from dataclasses import dataclass, field
from pathlib import Path


def _get_default_base_path() -> Path:
    """获取默认基础路径（跨平台支持）"""
    env_path = os.getenv('SKILLS_BASE_PATH')
    if env_path:
        return Path(env_path)
    cwd = Path.cwd()
    if (cwd / 'skills').exists():
        return cwd / 'skills'
    if (cwd.parent / 'skills').exists():
        return cwd.parent / 'skills'
    return cwd / 'skills'


@dataclass
class TranslationConfig:
    """翻译配置"""
    base_path: Path = field(default_factory=_get_default_base_path)
    skill_file: str = 'SKILL.md'
    meta_file: str = '_meta.json'
    backup_dir: str = 'raw'
    min_chinese_chars: int = 200
    max_retries: int = 3
    report_dir: Path = field(default_factory=lambda: Path.cwd())

    def __post_init__(self):
        if isinstance(self.base_path, str):
            self.base_path = Path(self.base_path)
        if isinstance(self.report_dir, str):
            self.report_dir = Path(self.report_dir)
        if not self.base_path.is_absolute():
            self.base_path = self.base_path.resolve()
        if not self.report_dir.is_absolute():
            self.report_dir = self.report_dir.resolve()
