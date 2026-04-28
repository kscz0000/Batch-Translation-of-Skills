"""
批量翻译器 - 翻译 + 自检循环

流程：翻译(保留备份) → 自检 → 通过则删备份 / 不通过则重翻 → 再自检 → 循环
每次重翻是独立请求，不带上次上下文。
"""

import time
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from .config import TranslationConfig
from .models import TranslationResult, TranslationStatus, TranslationReport
from .services.base import TranslationService
from .file_manager import FileManager
from .validator import TranslationValidator
from .reviewer import TranslationReviewer
from .exceptions import TranslationError, FileOperationError
from .utils import count_chinese_chars


class BatchTranslator:
    """批量翻译流程编排"""

    def __init__(
        self,
        config: TranslationConfig,
        validator: Optional[TranslationValidator] = None,
        max_workers: int = 1,
        max_review_rounds: int = 3,
    ):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.file_manager = FileManager(config)
        self._validator = validator or TranslationValidator()
        self._reviewer = TranslationReviewer(config, self._validator)
        self._max_workers = max(1, max_workers)
        self._max_review_rounds = max(1, max_review_rounds)

    def translate_single(
        self,
        skill_name: str,
        translator: TranslationService,
        force: bool = False,
    ) -> TranslationResult:
        """翻译单个技能：翻译 → 自检 → 修/重翻 → 再自检 → 直到通过或上限"""
        start = time.time()
        original = None

        try:
            # 已翻译且不强制 → 跳过
            if not force:
                status = self._check_status(skill_name)
                if status == TranslationStatus.TRANSLATED:
                    return TranslationResult(
                        skill_name=skill_name,
                        success=True,
                        status=status,
                        processing_time=time.time() - start,
                    )

            original = self.file_manager.read(skill_name)

            # 先检查 raw 备份，再创建新备份（避免中文版覆盖英文备份）
            # 如果 raw 备份存在且含更少中文，优先用备份（英文原文）作为翻译输入
            raw_content = self.file_manager.restore(skill_name)
            if raw_content and count_chinese_chars(raw_content) < count_chinese_chars(original):
                self.logger.info(
                    f"[{skill_name}] 检测到 raw 备份为英文原文"
                    f"（备份{count_chinese_chars(raw_content)}中文 vs 当前{count_chinese_chars(original)}中文），"
                    f"优先使用备份作为翻译输入"
                )
                original = raw_content

            if not self._is_valid_skill_content(original):
                self.logger.warning(f"[{skill_name}] 文件内容无效（可能是引用链接），跳过翻译")
                return TranslationResult(
                    skill_name=skill_name,
                    success=False,
                    status=TranslationStatus.SKIP,
                    error="文件内容无效（可能是引用链接）",
                    processing_time=time.time() - start,
                )

            # 备份原文 — 在 raw_content 检查之后再备份，确保 raw/ 中保留英文原文
            # 如果已有英文原文备份（raw/ 中含更少中文），不覆盖它
            if raw_content and count_chinese_chars(raw_content) < count_chinese_chars(self.file_manager.read(skill_name)):
                self.logger.info(f"[{skill_name}] 已有英文原文备份，跳过覆盖")
            else:
                self.file_manager.backup(skill_name)

            all_review_issues = []
            ref_results = None  # references 只翻译一次

            for round_num in range(self._max_review_rounds):
                self.logger.info(f"[{skill_name}] 第{round_num + 1}轮翻译...")

                # 每次都从原文翻译，独立请求，不带上次上下文
                translated = translator.translate(original)
                self.file_manager.write(skill_name, translated)

                # references 只在第1轮翻译（避免重复翻译浪费API）
                if round_num == 0:
                    ref_results = self.file_manager.translate_all_references(skill_name, translator)

                # 更新 meta
                self.file_manager.update_meta(skill_name)

                # 自检：对照备份检查
                review = self._reviewer.check_and_fix(skill_name)

                # 记录所有发现的问题（区分已修复和未修复）
                for issue in review.issues_fixed:
                    all_review_issues.append(f"第{round_num + 1}轮[已修复]: {issue}")
                for issue in review.issues_remaining:
                    all_review_issues.append(f"第{round_num + 1}轮[未修复]: {issue}")
                # issues_found 中不在 fixed/remaining 的（如不阻塞的代码注释问题）
                fixed_or_remaining = set(review.issues_fixed + review.issues_remaining)
                for issue in review.issues_found:
                    if issue not in fixed_or_remaining and not any(issue in fr for fr in fixed_or_remaining):
                        all_review_issues.append(f"第{round_num + 1}轮[记录]: {issue}")

                if review.issues_fixed:
                    self.logger.info(
                        f"[{skill_name}] 第{round_num + 1}轮自动修复: "
                        f"{', '.join(review.issues_fixed)}"
                    )

                if review.is_ok:
                    # 自检通过
                    # 有修复记录的保留备份（修复≠无问题），干净的通过才删备份
                    if review.issues_fixed:
                        self.logger.info(
                            f"[{skill_name}] 第{round_num + 1}轮自检通过(有修复)，保留备份"
                        )
                        raw_deleted = False
                    else:
                        self.file_manager.cleanup(skill_name)
                        self.logger.info(
                            f"[{skill_name}] 第{round_num + 1}轮自检通过，备份已删除"
                        )
                        raw_deleted = True
                    ref_all_ok = all(ref_results.values()) if ref_results else True
                    return TranslationResult(
                        skill_name=skill_name,
                        success=True,
                        status=TranslationStatus.TRANSLATED,
                        chinese_chars=review.chinese_chars if hasattr(review, 'chinese_chars') else 0,
                        description_translated=True,
                        references_translated=ref_all_ok,
                        references_results=ref_results,
                        meta_updated=True,
                        raw_deleted=raw_deleted,
                        review_rounds=round_num + 1,
                        review_issues=all_review_issues,
                        processing_time=time.time() - start,
                    )

                # 自检未通过 → 记录问题，下一轮重翻
                self.logger.warning(
                    f"[{skill_name}] 第{round_num + 1}轮自检未通过: "
                    f"{review.issues_remaining}"
                )

            # 达到上限仍未通过
            # 兜底：如果有自动修复（如代码块从备份恢复），接受这个版本，但保留备份
            if review.issues_fixed:
                self.logger.warning(
                    f"[{skill_name}] 自检{self._max_review_rounds}轮未完全通过，"
                    f"但有自动修复，接受兜底版本，保留备份"
                )
                # 不删备份——没有真正通过
                ref_all_ok = all(ref_results.values()) if ref_results else True
                return TranslationResult(
                    skill_name=skill_name,
                    success=True,
                    status=TranslationStatus.TRANSLATED,
                    chinese_chars=review.chinese_chars if hasattr(review, 'chinese_chars') else 0,
                    description_translated=True,
                    references_translated=ref_all_ok,
                    references_results=ref_results,
                    meta_updated=True,
                    raw_deleted=False,
                    review_rounds=self._max_review_rounds,
                    review_issues=all_review_issues,
                    processing_time=time.time() - start,
                )

            # 没有任何修复，完全失败 → 保留备份
            self.logger.warning(
                f"[{skill_name}] 自检{self._max_review_rounds}轮未通过，保留备份"
            )
            # 检查 description 是否已翻译（从翻译内容中判断）
            desc_translated = self._check_description_translated(skill_name)
            return TranslationResult(
                skill_name=skill_name,
                success=False,
                status=TranslationStatus.INCOMPLETE,
                chinese_chars=review.chinese_chars if hasattr(review, 'chinese_chars') else 0,
                description_translated=desc_translated,
                raw_deleted=False,
                review_rounds=self._max_review_rounds,
                review_issues=all_review_issues,
                processing_time=time.time() - start,
                error=f"自检{self._max_review_rounds}轮未通过: {review.issues_remaining}",
            )

        except TranslationError as e:
            self.logger.error(f"[{skill_name}] 失败: {e}")
            if original:
                self._rollback(skill_name, original)
            self._record_failure(skill_name, str(e))
            return TranslationResult(
                skill_name=skill_name,
                success=False,
                status=TranslationStatus.ERROR,
                error=str(e),
                processing_time=time.time() - start,
            )

    def translate_batch(
        self,
        skills: List[str],
        translator: TranslationService,
        force: bool = False,
        callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> TranslationReport:
        """批量翻译"""
        report = TranslationReport(total=len(skills))

        if self._max_workers == 1:
            for i, skill in enumerate(skills, 1):
                if callback:
                    callback(i, len(skills), skill)
                result = self.translate_single(skill, translator, force)
                report.results.append(result)
                self._update_report_stats(report, result)
        else:
            with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
                futures = {
                    executor.submit(self.translate_single, skill, translator, force): skill
                    for skill in skills
                }
                for future in as_completed(futures):
                    skill = futures[future]
                    try:
                        result = future.result()
                        report.results.append(result)
                        self._update_report_stats(report, result)
                    except Exception as e:
                        self.logger.error(f"[{skill}] 并发执行异常: {e}")
                        report.results.append(TranslationResult(
                            skill_name=skill,
                            success=False,
                            status=TranslationStatus.ERROR,
                            error=str(e),
                        ))
                        report.failed += 1

        return report

    def _update_report_stats(self, report: TranslationReport, result: TranslationResult) -> None:
        if result.status == TranslationStatus.SKIP:
            report.skipped += 1
        elif result.success and result.chinese_chars > 0:
            report.completed += 1
            report.total_chars += result.chinese_chars
        elif result.success:
            report.skipped += 1
        else:
            report.failed += 1

    def _check_status(self, skill_name: str) -> TranslationStatus:
        try:
            content = self.file_manager.read(skill_name)
        except FileOperationError:
            return TranslationStatus.ERROR
        return self._validator.check_status(content, self.config.min_chinese_chars)

    def _is_valid_skill_content(self, content: str) -> bool:
        """检查是否是有效的 SKILL.md（不是纯引用链接，有 frontmatter）"""
        if not content or not content.strip():
            return False
        lines = content.strip().split('\n')
        if len(lines) <= 2 and ('../' in content or './' in content):
            return False
        first_lines = '\n'.join(lines[:10]).lower()
        if '---' not in first_lines and '***' not in first_lines:
            return False
        if 'description' not in first_lines and 'name' not in first_lines:
            return False
        return True

    def _check_description_translated(self, skill_name: str) -> bool:
        """检查当前翻译文件中的 description 是否已包含中文"""
        try:
            content = self.file_manager.read(skill_name)
            from .utils import extract_frontmatter
            frontmatter, _ = extract_frontmatter(content)
            if frontmatter and frontmatter.get('description'):
                desc = frontmatter['description']
                chinese_count = sum(1 for c in desc if '\u4e00' <= c <= '\u9fff')
                return chinese_count > 0
        except Exception:
            pass
        return False

    def _rollback(self, skill_name: str, original: str) -> None:
        """回滚到原文"""
        try:
            self.file_manager.write(skill_name, original)
            self.file_manager.restore_directory(skill_name, 'references', 'reference')
            self.file_manager.cleanup(skill_name)
        except FileOperationError:
            self.logger.error(f"[{skill_name}] 回滚失败")

    def _record_failure(self, skill_name: str, error: str) -> None:
        try:
            failure_file = Path(self.config.base_path) / '.translation_failures'
            failure_file.parent.mkdir(parents=True, exist_ok=True)
            with open(failure_file, 'a', encoding='utf-8') as f:
                f.write(f"[{datetime.now().isoformat()}] {skill_name}: {error}\n")
        except Exception as e:
            self.logger.warning(f"记录失败信息失败: {e}")


def _max_review_rounds_str(n: int) -> str:
    """格式化上限数字"""
    return f"{n}"
