"""
对照备份自检修复模块

翻译完成后，对照备份检查翻译结果，发现格式/结构问题自动修复，汇报结果。

检查项：
1. frontmatter 丢失或损坏 → 从备份恢复
2. 代码块丢失 → 标记需重翻（不自动恢复，避免追加到末尾产生重复）
3. description 未翻译 → 标记（需重翻）
4. 代码块内注释未翻译 → 仅记录（已知限制：代码块被占位符保护，注释不翻译是正常行为）
5. references 未翻译 → 标记
"""

import re
import logging
from pathlib import Path
from typing import List, Optional

from .config import TranslationConfig
from .file_manager import FileManager
from .validator import TranslationValidator
from .models import ReviewCheckResult
from .utils import count_chinese_chars, extract_frontmatter, is_description_translated


class TranslationReviewer:
    """对照备份自检修复"""

    def __init__(self, config: TranslationConfig, validator: Optional[TranslationValidator] = None):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.file_manager = FileManager(config)
        self._validator = validator or TranslationValidator()

    def check_and_fix(self, skill_name: str) -> ReviewCheckResult:
        """对照备份检查翻译结果，发现问题自动修复

        能自动修的：frontmatter丢失、代码块丢失
        不能自动修的：description未翻译、注释未翻译 → 标记，由 core 负责重翻
        """
        issues_found = []
        issues_fixed = []
        issues_remaining = []

        # 读取备份（原文）和当前文件（译文）
        backup_content = self.file_manager.restore(skill_name)
        if not backup_content:
            self.logger.info(f"[自检] {skill_name}: 无备份文件，仅做基本检查")
            return self._basic_check(skill_name)

        try:
            current_content = self.file_manager.read(skill_name)
        except Exception as e:
            return ReviewCheckResult(
                skill_name=skill_name,
                is_ok=False,
                issues_found=[f"读取当前文件失败: {e}"],
                issues_remaining=[f"读取当前文件失败: {e}"],
            )

        chinese_chars = count_chinese_chars(current_content)

        # --- 检查 1: frontmatter ---
        fm_backup, _ = extract_frontmatter(backup_content)
        fm_current, _ = extract_frontmatter(current_content)

        if not fm_current and fm_backup:
            issues_found.append("frontmatter丢失")
            fixed = self._restore_frontmatter(current_content, backup_content)
            if fixed:
                self.file_manager.write(skill_name, fixed)
                issues_fixed.append("frontmatter丢失→已从备份恢复")
            else:
                issues_remaining.append("frontmatter丢失→恢复失败，需重翻")
        elif fm_current and fm_backup:
            for key in ('name', 'trigger'):
                if key in fm_backup and key not in fm_current:
                    issues_found.append(f"frontmatter字段'{key}'丢失")
                    fixed = self._restore_frontmatter(current_content, backup_content)
                    if fixed:
                        self.file_manager.write(skill_name, fixed)
                        issues_fixed.append(f"frontmatter字段'{key}'丢失→已从备份恢复")
                    else:
                        issues_remaining.append(f"frontmatter字段'{key}'丢失→恢复失败，需重翻")
                    break

        # --- 检查 2: 代码块 ---
        backup_code_blocks = re.findall(r'```[\s\S]*?```', backup_content)
        current_code_blocks = re.findall(r'```[\s\S]*?```', current_content)

        if len(backup_code_blocks) > len(current_code_blocks):
            lost_count = len(backup_code_blocks) - len(current_code_blocks)
            issues_found.append(f"代码块丢失({lost_count}个)")
            # 不自动恢复：追加到末尾会产生重复且位置错误，改为触发重翻
            issues_remaining.append(f"代码块丢失({lost_count}个)→需重翻")

        # --- 检查 3: description ---
        # 重新读（可能被上面的修复改了）
        try:
            current_content = self.file_manager.read(skill_name)
        except Exception:
            pass

        fm, _ = extract_frontmatter(current_content)
        desc = fm.get('description', '') if fm else ''
        if not is_description_translated(desc, 10):
            issues_found.append("description未翻译")
            issues_remaining.append("description未翻译→需重翻")

        # --- 检查 4: 代码块内注释 ---
        # 已知限制：代码块被占位符保护后 LLM 无法看到注释，注释不翻译是正常行为
        # 仅记录，不阻塞通过；如将来需翻译注释，需引入语言感知的 parser（如 tree-sitter）
        code_comment_issues = self._check_code_comments(backup_content, current_content)
        if code_comment_issues:
            issues_found.extend(code_comment_issues)

        # --- 检查 5: references ---
        ref_issues = self._check_references(skill_name)
        issues_found.extend(ref_issues)
        issues_remaining.extend(ref_issues)

        is_ok = len(issues_remaining) == 0
        return ReviewCheckResult(
            skill_name=skill_name,
            is_ok=is_ok,
            chinese_chars=chinese_chars,
            issues_found=issues_found,
            issues_fixed=issues_fixed,
            issues_remaining=issues_remaining,
        )

    def check_and_fix_all(self, skill_names: List[str]) -> List[ReviewCheckResult]:
        """批量自检修复"""
        results = []
        for name in skill_names:
            result = self.check_and_fix(name)
            results.append(result)
            status = "OK" if result.is_ok else "需处理"
            self.logger.info(
                f"[自检] {name}: {status} | "
                f"发现{len(result.issues_found)}问题, "
                f"修复{len(result.issues_fixed)}, "
                f"剩余{len(result.issues_remaining)}"
            )
        return results

    def generate_report(self, results: List[ReviewCheckResult]) -> str:
        """生成自检报告"""
        if not results:
            return "无自检结果"

        total = len(results)
        ok_count = sum(1 for r in results if r.is_ok)
        total_found = sum(len(r.issues_found) for r in results)
        total_fixed = sum(len(r.issues_fixed) for r in results)
        total_remaining = sum(len(r.issues_remaining) for r in results)

        lines = [
            "# 翻译自检报告",
            f"",
            f"**检查总数**: {total}",
            f"**通过**: {ok_count} | **需处理**: {total - ok_count}",
            f"**发现问题**: {total_found} | **已修复**: {total_fixed} | **剩余**: {total_remaining}",
        ]

        need_attention = [r for r in results if not r.is_ok]
        if need_attention:
            lines.append("")
            lines.append("## 需处理的技能")
            for r in need_attention:
                lines.append("")
                lines.append(f"### {r.skill_name}")
                for fixed in r.issues_fixed:
                    lines.append(f"- [已修复] {fixed}")
                for remaining in r.issues_remaining:
                    lines.append(f"- [待处理] {remaining}")

        ok_skills = [r for r in results if r.is_ok and r.issues_fixed]
        if ok_skills:
            lines.append("")
            lines.append("## 已通过（有自动修复）")
            for r in ok_skills:
                lines.append(f"- **{r.skill_name}**: {', '.join(r.issues_fixed)}")

        return '\n'.join(lines)

    # ---- 内部方法 ----

    def _restore_frontmatter(self, current_content: str, backup_content: str) -> Optional[str]:
        """从备份恢复 frontmatter 到当前内容"""
        fm_backup, _ = extract_frontmatter(backup_content)
        if not fm_backup:
            return None

        fm_lines = ['---']
        for key, value in fm_backup.items():
            if isinstance(value, list):
                fm_lines.append(f"{key}:")
                for item in value:
                    fm_lines.append(f"  - {item}")
            elif isinstance(value, str) and ('\n' in value or ':' in value):
                fm_lines.append(f"{key}: |-")
                for line in value.split('\n'):
                    fm_lines.append(f"  {line}")
            else:
                fm_lines.append(f"{key}: {value}")
        fm_lines.append('---')

        _, body = extract_frontmatter(current_content)
        return '\n'.join(fm_lines) + '\n' + body

    def _check_code_comments(self, backup_content: str, current_content: str) -> List[str]:
        """检查代码块内的注释是否翻译"""
        issues = []
        backup_blocks = re.findall(r'```[\s\S]*?```', backup_content)
        current_blocks = re.findall(r'```[\s\S]*?```', current_content)

        # 只检查代码块数量一致的情况（数量不一致已经在上面的丢失检查中处理了）
        if len(backup_blocks) != len(current_blocks):
            return issues

        for i, (bak_block, cur_block) in enumerate(zip(backup_blocks, current_blocks)):
            # 提取注释行
            bak_comments = re.findall(r'//.*$|#.*$', bak_block, re.MULTILINE)
            cur_comments = re.findall(r'//.*$|#.*$', cur_block, re.MULTILINE)

            if not bak_comments:
                continue

            # 检查译文代码块中是否有中文注释
            has_chinese_comment = any(
                any('\u4e00' <= c <= '\u9fff' for c in comment)
                for comment in cur_comments
            )

            # 原文有注释，译文代码块注释中没有中文 → 注释没翻译
            if bak_comments and not has_chinese_comment and len(cur_comments) > 0:
                issues.append(f"代码块{i + 1}注释未翻译→需重翻")
                break  # 只报一次，避免刷屏

        return issues

    def _check_references(self, skill_name: str) -> List[str]:
        """检查 references 目录的翻译状态"""
        issues = []
        refs_dir = self._get_refs_dir(skill_name)
        if not refs_dir or not refs_dir.exists():
            return issues

        for ref_file in refs_dir.glob('*.md'):
            try:
                content = ref_file.read_text(encoding='utf-8')
                if count_chinese_chars(content) < 20:
                    issues.append(f"reference未翻译: {ref_file.name}")
            except Exception:
                issues.append(f"reference读取失败: {ref_file.name}")

        return issues

    def _get_refs_dir(self, skill_name: str) -> Optional[Path]:
        """获取 references 目录路径"""
        skill_dir = self.config.base_path / skill_name
        if skill_dir.is_dir():
            refs = skill_dir / 'references'
            if refs.is_dir():
                return refs
        return None

    def _basic_check(self, skill_name: str) -> ReviewCheckResult:
        """无备份时的基本检查：description、references"""
        issues_found = []
        issues_remaining = []

        try:
            current_content = self.file_manager.read(skill_name)
        except Exception as e:
            return ReviewCheckResult(
                skill_name=skill_name,
                is_ok=False,
                issues_found=[f"读取文件失败: {e}"],
                issues_remaining=[f"读取文件失败: {e}"],
            )

        chinese_chars = count_chinese_chars(current_content)

        # description
        fm, _ = extract_frontmatter(current_content)
        desc = fm.get('description', '') if fm else ''
        if not is_description_translated(desc, 10):
            issues_found.append("description未翻译")
            issues_remaining.append("description未翻译→需重翻或人工修改")

        # references
        ref_issues = self._check_references(skill_name)
        issues_found.extend(ref_issues)
        issues_remaining.extend(ref_issues)

        return ReviewCheckResult(
            skill_name=skill_name,
            is_ok=len(issues_remaining) == 0,
            chinese_chars=chinese_chars,
            issues_found=issues_found,
            issues_remaining=issues_remaining,
        )
