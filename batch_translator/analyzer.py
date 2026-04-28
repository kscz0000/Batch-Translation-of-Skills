"""
翻译状态分析器
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional

from .config import TranslationConfig
from .models import SkillAnalysis, TranslationStatus, AnalysisReport
from .utils import count_chinese_chars, check_description_translated, extract_frontmatter
from .validator import TranslationValidator


class TranslationAnalyzer:
    """分析技能翻译状态"""

    def __init__(self, config: TranslationConfig, validator: Optional[TranslationValidator] = None):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._validator = validator or TranslationValidator()

    def get_skills(self) -> List[str]:
        """获取所有技能名称（包括子技能）"""
        if not self.config.base_path or not self.config.base_path.exists():
            return []

        skills = []
        for p in self.config.base_path.iterdir():
            if not p.is_dir():
                continue

            # 主技能
            if (p / self.config.skill_file).exists():
                skills.append(p.name)

            # 子技能（skills/ 子目录）
            # 目录结构: <skill-name>/skills/<sub-skill>/SKILL.md
            # base_path 已经是 skills/，所以 p.name 就是 <skill-name>
            # 技能名称格式: <skill-name>/skills/<sub-skill>
            skills_dir = p / 'skills'
            if skills_dir.is_dir():
                for sub in skills_dir.iterdir():
                    if sub.is_dir() and (sub / self.config.skill_file).exists():
                        skills.append(f"{p.name}/skills/{sub.name}")

        return sorted(skills)

    def get_all_markdown_files(self) -> List[tuple]:
        """获取所有需要翻译的 Markdown 文件

        Returns:
            [(skill_name, file_path, is_main_skill), ...]
        """
        files = []
        base = self.config.base_path

        for skill_dir in base.iterdir():
            if not skill_dir.is_dir():
                continue

            skill_name = skill_dir.name

            # 主 SKILL.md
            main_file = skill_dir / 'SKILL.md'
            if main_file.exists():
                files.append((skill_name, main_file, True))

            # references/ 目录
            refs_dir = skill_dir / 'references'
            if refs_dir.is_dir():
                for ref_file in refs_dir.glob('*.md'):
                    files.append((skill_name, ref_file, False))

            # 子技能（skills/ 子目录）
            skills_dir = skill_dir / 'skills'
            if skills_dir.is_dir():
                for sub_dir in skills_dir.iterdir():
                    if not sub_dir.is_dir():
                        continue

                    sub_name = f"{skill_name}/skills/{sub_dir.name}"

                    # 子技能的 SKILL.md
                    sub_main = sub_dir / 'SKILL.md'
                    if sub_main.exists():
                        files.append((sub_name, sub_main, True))

                    # 子技能的 references/
                    sub_refs = sub_dir / 'references'
                    if sub_refs.is_dir():
                        for ref_file in sub_refs.glob('*.md'):
                            files.append((sub_name, ref_file, False))

        return files

    def analyze(self, skill_name: str) -> SkillAnalysis:
        """分析单个技能"""
        skill_path = self.config.base_path / skill_name / self.config.skill_file
        meta_path = self.config.base_path / skill_name / self.config.meta_file

        analysis = SkillAnalysis(skill_name=skill_name)

        # 检查文件
        if not skill_path.exists():
            return analysis.fail('SKILL.md不存在')

        try:
            content = skill_path.read_text(encoding='utf-8')
            analysis.chinese_chars = count_chinese_chars(content)
            analysis.description_translated = check_description_translated(content)

            # 使用 validator 统一判断状态
            analysis.status = self._validator.check_status(
                content, 
                self.config.min_chinese_chars
            )

            # 添加具体问题描述
            if analysis.status == TranslationStatus.NOT_TRANSLATED:
                analysis.issues.append('英文原文，未翻译')
            elif analysis.status == TranslationStatus.INCOMPLETE:
                if analysis.chinese_chars < self.config.min_chinese_chars:
                    analysis.issues.append(f'中文字符不足: {analysis.chinese_chars}')
                if not analysis.description_translated:
                    analysis.issues.append('description未翻译')
            else:
                analysis.success()

        except Exception as e:
            analysis.fail(f'读取失败: {e}')

        # 检查meta
        if meta_path.exists():
            analysis.has_meta = True
            try:
                meta = json.loads(meta_path.read_text())
                analysis.meta_locale = meta.get('locale')
            except Exception:
                pass

        return analysis

    def analyze_all(self) -> AnalysisReport:
        """分析所有技能"""
        skills = self.get_skills()
        report = AnalysisReport(total_skills=len(skills))

        for skill_name in skills:
            analysis = self.analyze(skill_name)
            report.analyses.append(analysis)

            # 统计
            if analysis.status == TranslationStatus.TRANSLATED:
                report.translated_count += 1
            elif analysis.status == TranslationStatus.INCOMPLETE:
                report.incomplete_count += 1
            elif analysis.status == TranslationStatus.NOT_TRANSLATED:
                report.not_translated_count += 1
            else:
                report.error_count += 1

            if analysis.has_meta:
                report.has_meta_count += 1
            if analysis.meta_locale == 'zh-CN':
                report.locale_zh_count += 1

        # 平均值
        valid_chars = [a.chinese_chars for a in report.analyses if a.chinese_chars > 0]
        if valid_chars:
            report.average_chinese_chars = sum(valid_chars) / len(valid_chars)

        return report

    def filter_by_status(
        self,
        statuses: List[TranslationStatus],
        report: AnalysisReport = None,
    ) -> List[str]:
        """按状态过滤技能"""
        if report is not None:
            return [a.skill_name for a in report.analyses if a.status in statuses]

        # 无缓存时，使用列表推导式直接过滤
        return [
            name for name in self.get_skills()
            if self.analyze(name).status in statuses
        ]

    def get_needs_translation(self, report: AnalysisReport = None) -> List[str]:
        """获取需要翻译的技能"""
        return self.filter_by_status(
            [TranslationStatus.NOT_TRANSLATED, TranslationStatus.INCOMPLETE],
            report=report
        )
