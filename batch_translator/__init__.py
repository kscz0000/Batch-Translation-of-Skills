"""
批量翻译技能模块
"""

from .config import TranslationConfig
from .models import TranslationResult, TranslationStatus, TranslationReport, ReviewCheckResult
from .services.base import TranslationService
from .services.openai import OpenAITranslation
from .services.anthropic import AnthropicTranslation
from .services.mock import MockTranslation
from .services.factory import TranslationServiceFactory
from .file_manager import FileManager
from .core import BatchTranslator
from .analyzer import TranslationAnalyzer
from .reporter import ReportGenerator
from .reviewer import TranslationReviewer
from .exceptions import (
    TranslationError,
    TranslationServiceError,
    BackupError,
    VerificationError,
    FileOperationError,
    ConfigurationError,
    ServiceNotAvailableError,
)
from .languages import Language, get_translation_prompt, get_supported_directions

__all__ = [
    'TranslationConfig',
    'TranslationResult',
    'TranslationStatus',
    'TranslationReport',
    'ReviewCheckResult',
    'TranslationService',
    'OpenAITranslation',
    'AnthropicTranslation',
    'MockTranslation',
    'TranslationServiceFactory',
    'FileManager',
    'BatchTranslator',
    'TranslationAnalyzer',
    'ReportGenerator',
    'TranslationReviewer',
    'TranslationError',
    'TranslationServiceError',
    'BackupError',
    'VerificationError',
    'FileOperationError',
    'ConfigurationError',
    'ServiceNotAvailableError',
    'Language',
    'get_translation_prompt',
    'get_supported_directions',
]

__version__ = '4.1.0'
