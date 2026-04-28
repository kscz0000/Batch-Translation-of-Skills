"""
数据模型模块
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime


class TranslationStatus(Enum):
    """翻译状态枚举"""
    TRANSLATED = "translated"
    INCOMPLETE = "incomplete"
    NOT_TRANSLATED = "not_translated"
    ERROR = "error"
    SKIP = "skip"
    UNKNOWN = "unknown"


@dataclass
class TranslationResult:
    """翻译结果"""
    skill_name: str
    success: bool
    status: TranslationStatus = TranslationStatus.UNKNOWN
    chinese_chars: int = 0
    description_translated: bool = False
    references_translated: bool = False
    references_results: Dict[str, bool] = field(default_factory=dict)
    meta_updated: bool = False
    raw_deleted: bool = False
    error: Optional[str] = None
    processing_time: float = 0.0
    review_rounds: int = 0
    review_issues: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'skill_name': self.skill_name,
            'success': self.success,
            'status': self.status.value,
            'chinese_chars': self.chinese_chars,
            'description_translated': self.description_translated,
            'references_translated': self.references_translated,
            'references_results': self.references_results,
            'meta_updated': self.meta_updated,
            'raw_deleted': self.raw_deleted,
            'error': self.error,
            'processing_time': self.processing_time,
            'review_rounds': self.review_rounds,
            'review_issues': self.review_issues,
        }


@dataclass
class SkillAnalysis:
    """技能分析结果"""
    skill_name: str
    status: TranslationStatus = TranslationStatus.UNKNOWN
    chinese_chars: int = 0
    description_translated: bool = False
    has_meta: bool = False
    meta_locale: Optional[str] = None
    issues: List[str] = field(default_factory=list)

    def success(self) -> 'SkillAnalysis':
        self.status = TranslationStatus.TRANSLATED
        return self

    def fail(self, reason: str) -> 'SkillAnalysis':
        self.issues.append(reason)
        if self.status == TranslationStatus.UNKNOWN:
            self.status = TranslationStatus.ERROR
        return self

    @property
    def needs_translation(self) -> bool:
        return self.status in [
            TranslationStatus.NOT_TRANSLATED,
            TranslationStatus.INCOMPLETE,
        ]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'skill_name': self.skill_name,
            'status': self.status.value,
            'chinese_chars': self.chinese_chars,
            'description_translated': self.description_translated,
            'has_meta': self.has_meta,
            'meta_locale': self.meta_locale,
            'issues': self.issues,
            'needs_translation': self.needs_translation,
        }


@dataclass
class TranslationReport:
    """翻译报告"""
    total: int = 0
    completed: int = 0
    failed: int = 0
    skipped: int = 0
    total_chars: int = 0
    results: List[TranslationResult] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return (self.completed / self.total) * 100

    @property
    def average_chars(self) -> float:
        if self.completed == 0:
            return 0.0
        return self.total_chars / self.completed

    def to_dict(self) -> Dict[str, Any]:
        return {
            'total': self.total,
            'completed': self.completed,
            'failed': self.failed,
            'skipped': self.skipped,
            'total_chars': self.total_chars,
            'success_rate': f"{self.success_rate:.1f}%",
            'average_chars': f"{self.average_chars:.0f}",
        }


@dataclass
class AnalysisReport:
    """分析报告"""
    total_skills: int = 0
    translated_count: int = 0
    incomplete_count: int = 0
    not_translated_count: int = 0
    error_count: int = 0
    has_meta_count: int = 0
    locale_zh_count: int = 0
    average_chinese_chars: float = 0.0
    analyses: List[SkillAnalysis] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_skills': self.total_skills,
            'translated_count': self.translated_count,
            'incomplete_count': self.incomplete_count,
            'not_translated_count': self.not_translated_count,
            'error_count': self.error_count,
            'has_meta_count': self.has_meta_count,
            'locale_zh_count': self.locale_zh_count,
            'average_chinese_chars': f"{self.average_chinese_chars:.0f}",
        }


@dataclass
class ReviewCheckResult:
    """自检修复结果"""
    skill_name: str
    is_ok: bool
    chinese_chars: int = 0
    issues_found: List[str] = field(default_factory=list)
    issues_fixed: List[str] = field(default_factory=list)
    issues_remaining: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'skill_name': self.skill_name,
            'is_ok': self.is_ok,
            'chinese_chars': self.chinese_chars,
            'issues_found': self.issues_found,
            'issues_fixed': self.issues_fixed,
            'issues_remaining': self.issues_remaining,
        }
