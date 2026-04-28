"""
报告生成器模块

生成各种格式的报告
"""

import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from .models import TranslationResult, TranslationReport, AnalysisReport, SkillAnalysis, ReviewCheckResult, TranslationStatus


class ReportGenerator:
    """报告生成器"""

    @staticmethod
    def generate_translation_report(report: TranslationReport) -> str:
        """
        生成翻译报告

        Args:
            report: 翻译报告

        Returns:
            Markdown格式的报告
        """
        lines = []
        lines.append("# 翻译完成报告\n")
        lines.append(f"**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        lines.append(f"**总数**: {report.total}\n")
        lines.append(f"**完成**: {report.completed}\n")
        lines.append(f"**失败**: {report.failed}\n")
        lines.append(f"**跳过**: {report.skipped}\n")
        lines.append(f"**成功率**: {report.success_rate:.1f}%\n")
        lines.append(f"**平均中文字符数**: {report.average_chars:.0f}\n\n")

        # 详细结果表
        if report.results:
            lines.append("## 详细结果\n")
            lines.append("| # | 技能名 | 中文字符数 | description | 自检轮次 | raw已删除 | 耗时 | 状态 |\n")
            lines.append("|---|--------|-----------|------------|---------|----------|------|------|\n")

            for i, result in enumerate(report.results, 1):
                lines.append(f"| {i} | {result.skill_name} | {result.chinese_chars} | ")
                lines.append("[OK]" if result.description_translated else "[FAIL]")
                lines.append(" | ")
                # 自检轮次：区分已修复/未修复/记录
                if result.review_rounds:
                    fixed_count = sum(1 for issue in result.review_issues if '[已修复]' in issue)
                    unfixed_count = sum(1 for issue in result.review_issues if '[未修复]' in issue)
                    record_count = sum(1 for issue in result.review_issues if '[记录]' in issue)
                    parts = []
                    if fixed_count:
                        parts.append(f"修复{fixed_count}项")
                    if unfixed_count:
                        parts.append(f"未修复{unfixed_count}项")
                    if record_count:
                        parts.append(f"记录{record_count}项")
                    if parts:
                        lines.append(f"{result.review_rounds}({', '.join(parts)})")
                    else:
                        lines.append(f"{result.review_rounds}")
                else:
                    lines.append("-")
                lines.append(" | ")
                lines.append("[OK]" if result.raw_deleted else "[FAIL]")
                lines.append(f" | {result.processing_time:.1f}s | ")
                if result.success:
                    lines.append("[OK]")
                elif result.status == TranslationStatus.SKIP:
                    lines.append("[SKIP]")
                else:
                    lines.append("[FAIL]")
                lines.append(" |\n")

        # 自检修复记录
        fixed_results = [r for r in report.results if r.success and r.review_issues]
        if fixed_results:
            lines.append("\n## 自检修复记录\n")
            for result in fixed_results:
                lines.append(f"- **{result.skill_name}**:\n")
                for issue in result.review_issues:
                    lines.append(f"  - {issue}\n")

        # 问题汇总（失败的）
        failed_results = [r for r in report.results if not r.success]
        if failed_results:
            lines.append("\n## 问题汇总\n")
            for result in failed_results:
                lines.append(f"- **{result.skill_name}**: {result.error}\n")
                if result.review_issues:
                    for issue in result.review_issues:
                        lines.append(f"  - {issue}\n")

        return ''.join(lines)

    @staticmethod
    def generate_analysis_report(report: AnalysisReport) -> str:
        """
        生成分析报告

        Args:
            report: 分析报告

        Returns:
            Markdown格式的报告
        """
        lines = []
        lines.append("# 技能翻译状态统计报告\n")
        lines.append(f"**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        lines.append(f"**总数**: {report.total_skills}\n\n")

        # 统计摘要
        lines.append("## 统计摘要\n")
        total = report.total_skills or 1  # 避免除零
        lines.append(f"- **已翻译**: {report.translated_count} "
                    f"({report.translated_count/total*100:.1f}%)\n")
        lines.append(f"- **部分翻译**: {report.incomplete_count} "
                    f"({report.incomplete_count/total*100:.1f}%)\n")
        lines.append(f"- **未翻译**: {report.not_translated_count} "
                    f"({report.not_translated_count/total*100:.1f}%)\n")
        lines.append(f"- **错误**: {report.error_count} "
                    f"({report.error_count/total*100:.1f}%)\n")
        lines.append(f"- **有_meta.json**: {report.has_meta_count} "
                    f"({report.has_meta_count/total*100:.1f}%)\n")
        lines.append(f"- **标记zh-CN**: {report.locale_zh_count} "
                    f"({report.locale_zh_count/total*100:.1f}%)\n")
        lines.append(f"- **平均中文字符数**: {report.average_chinese_chars:.0f}\n\n")

        # 分类列出
        not_translated = [a for a in report.analyses
                         if a.status.value == 'not_translated']
        incomplete = [a for a in report.analyses
                     if a.status.value == 'incomplete']
        errors = [a for a in report.analyses
                 if a.status.value == 'error']

        if not_translated:
            lines.append(f"## 未翻译技能 ({len(not_translated)})\n")
            lines.append("| # | 技能名 | 中文字符数 | 问题 |\n")
            lines.append("|---|--------|-----------|------|\n")
            for i, a in enumerate(not_translated, 1):
                lines.append(f"| {i} | {a.skill_name} | {a.chinese_chars} | "
                           f"{', '.join(a.issues)} |\n")
            lines.append("\n")

        if incomplete:
            lines.append(f"## 部分翻译技能 ({len(incomplete)})\n")
            lines.append("| # | 技能名 | 中文字符数 | 问题 |\n")
            lines.append("|---|--------|-----------|------|\n")
            for i, a in enumerate(incomplete, 1):
                lines.append(f"| {i} | {a.skill_name} | {a.chinese_chars} | "
                           f"{', '.join(a.issues)} |\n")
            lines.append("\n")

        if errors:
            lines.append(f"## 错误技能 ({len(errors)})\n")
            lines.append("| # | 技能名 | 问题 |\n")
            lines.append("|---|--------|------|\n")
            for i, a in enumerate(errors, 1):
                lines.append(f"| {i} | {a.skill_name} | {', '.join(a.issues)} |\n")
            lines.append("\n")

        return ''.join(lines)

    @staticmethod
    def save_report(content: str, filename: str, report_dir: Path) -> Path:
        """
        保存报告到文件。如果文件已存在，在文件名中插入时间戳避免覆盖。

        Args:
            content: 报告内容
            filename: 文件名
            report_dir: 报告目录

        Returns:
            保存的文件路径
        """
        report_path = report_dir / filename
        if report_path.exists():
            stem = report_path.stem
            suffix = report_path.suffix
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_path = report_dir / f"{stem}_{timestamp}{suffix}"
        report_path.write_text(content, encoding='utf-8')
        return report_path

    @staticmethod
    def save_json_report(report_data: dict, filename: str, report_dir: Path) -> Path:
        """
        保存JSON格式的报告。如果文件已存在，在文件名中插入时间戳避免覆盖。

        Args:
            report_data: 报告数据字典
            filename: 文件名
            report_dir: 报告目录

        Returns:
            保存的文件路径
        """
        report_path = report_dir / filename
        if report_path.exists():
            stem = report_path.stem
            suffix = report_path.suffix
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_path = report_dir / f"{stem}_{timestamp}{suffix}"
        report_path.write_text(
            json.dumps(report_data, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
        return report_path

    @staticmethod
    def generate_review_report(results: List[ReviewCheckResult]) -> str:
        """生成自检报告"""
        if not results:
            return "无自检结果"

        total = len(results)
        ok_count = sum(1 for r in results if r.is_ok)
        total_found = sum(len(r.issues_found) for r in results)
        total_fixed = sum(len(r.issues_fixed) for r in results)
        total_remaining = sum(len(r.issues_remaining) for r in results)

        lines = [
            "# 翻译自检报告\n",
            f"**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
            f"**检查总数**: {total}\n",
            f"**通过**: {ok_count} | **需处理**: {total - ok_count}\n",
            f"**发现问题**: {total_found} | **已修复**: {total_fixed} | **剩余**: {total_remaining}\n\n",
        ]

        need_attention = [r for r in results if not r.is_ok]
        if need_attention:
            lines.append("## 需处理的技能\n")
            for r in need_attention:
                lines.append(f"\n### {r.skill_name}\n")
                for fixed in r.issues_fixed:
                    lines.append(f"- [已修复] {fixed}\n")
                for remaining in r.issues_remaining:
                    lines.append(f"- [待处理] {remaining}\n")

        ok_skills = [r for r in results if r.is_ok and r.issues_found]
        if ok_skills:
            lines.append("\n## 已通过但有修复记录\n")
            for r in ok_skills:
                lines.append(f"- **{r.skill_name}**: {', '.join(r.issues_fixed)}\n")

        return ''.join(lines)
