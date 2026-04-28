"""
批量翻译技能 - 主程序

命令行入口
"""

import sys
import os
import logging
import argparse
from pathlib import Path

# 加载 .env 文件
_env_file = Path(__file__).parent.parent / '.env'
if _env_file.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_file)
    except ImportError:
        with open(_env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    eq_pos = line.index('=')
                    key = line[:eq_pos].strip()
                    value = line[eq_pos + 1:].strip()
                    if (value.startswith('"') and value.endswith('"')) or \
                       (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]
                    value = value.replace('\\n', '\n').replace('\\t', '\t').replace('\\"', '"')
                    os.environ[key] = value

from .config import TranslationConfig
from .services.factory import TranslationServiceFactory
from .core import BatchTranslator
from .analyzer import TranslationAnalyzer
from .reporter import ReportGenerator
from .reviewer import TranslationReviewer
from .exceptions import ServiceNotAvailableError


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )


def analyze_command(args) -> None:
    """分析命令"""
    base_path = Path(args.base_path) if args.base_path else Path(
        os.getenv('SKILLS_BASE_PATH', './skills')
    )
    config = TranslationConfig(base_path=base_path)
    analyzer = TranslationAnalyzer(config)
    report = analyzer.analyze_all()

    report_content = ReportGenerator.generate_analysis_report(report)
    print("\n" + "="*60)
    print(report_content)

    report_path = ReportGenerator.save_report(
        report_content, 'translation-status-report.md', config.report_dir
    )
    print(f"\n报告已保存到: {report_path}")


def translate_command(args) -> None:
    """翻译命令"""
    base_path = Path(args.base_path) if args.base_path else Path(
        os.getenv('SKILLS_BASE_PATH', './skills')
    )
    config = TranslationConfig(base_path=base_path, min_chinese_chars=args.min_chars)
    analyzer = TranslationAnalyzer(config)
    translator = None

    from_lang = getattr(args, 'from_lang', 'en')
    to_lang = getattr(args, 'to_lang', 'zh')

    try:
        try:
            translator = TranslationServiceFactory.create(
                args.service,
                from_lang=from_lang,
                to_lang=to_lang,
            )
        except ServiceNotAvailableError as e:
            print(f"错误: {e}")
            print("\n可用服务:")
            for name in TranslationServiceFactory.list_services():
                try:
                    available = TranslationServiceFactory.create(name).is_available()
                    status = "✓" if available else "✗"
                    print(f"  {status} {name}")
                except Exception:
                    print(f"  ✗ {name} (创建失败)")
            sys.exit(1)

        if args.filter:
            from .models import TranslationStatus
            skills = analyzer.filter_by_status(
                [TranslationStatus[args.filter.upper().replace('-', '_')]]
            )
        else:
            skills = analyzer.get_skills()

        if args.limit:
            skills = skills[:args.limit]

        max_workers = getattr(args, 'workers', 1)
        if args.dry_run:
            max_workers = 1

        print(f"\n{'='*60}")
        print(f"批量翻译技能")
        print(f"{'='*60}")
        print(f"服务: {args.service}")
        print(f"翻译方向: {from_lang} → {to_lang}")
        print(f"总技能数: {len(skills)}")
        print(f"模式: {'演练' if args.dry_run else '执行'}")
        print(f"并发数: {max_workers}")
        print(f"{'='*60}\n")

        if not skills:
            print("没有需要翻译的技能")
            return

        batch_translator = BatchTranslator(config, max_workers=max_workers)

        if args.dry_run:
            print("演练模式：")
            for skill in skills:
                print(f"  - {skill}")
            return

        def progress_callback(current: int, total: int, skill: str):
            print(f"[{current}/{total}] {skill}...", end='\r')

        report = batch_translator.translate_batch(
            skills=skills,
            translator=translator,
            force=args.force,
            callback=progress_callback,
        )

        report_content = ReportGenerator.generate_translation_report(report)
        print("\n" + "="*60)
        print(report_content)

        report_path = ReportGenerator.save_report(
            report_content, 'batch-translation-report.md', config.report_dir
        )
        print(f"\n报告已保存到: {report_path}")

    finally:
        pass


def review_command(args) -> None:
    """自检命令：对照备份检查翻译结果，发现问题自动修复，汇报"""
    base_path = Path(args.base_path) if args.base_path else Path(
        os.getenv('SKILLS_BASE_PATH', './skills')
    )
    config = TranslationConfig(base_path=base_path)
    reviewer = TranslationReviewer(config)
    analyzer = TranslationAnalyzer(config)

    skills = analyzer.get_skills()

    if args.skill:
        skills = [args.skill]
    elif args.filter:
        from .models import TranslationStatus
        skills = analyzer.filter_by_status(
            [TranslationStatus[args.filter.upper().replace('-', '_')]]
        )

    if not skills:
        print("没有需要自检的技能")
        return

    print(f"\n{'='*60}")
    print(f"翻译自检")
    print(f"{'='*60}")
    print(f"检查技能数: {len(skills)}")
    print(f"{'='*60}\n")

    results = reviewer.check_and_fix_all(skills)

    report_content = reviewer.generate_report(results)
    print("\n" + "="*60)
    print(report_content)

    report_path = ReportGenerator.save_report(
        report_content, 'translation-review-report.md', config.report_dir
    )
    print(f"\n报告已保存到: {report_path}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='批量翻译技能脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 分析所有技能
  python -m batch_translator analyze

  # 使用OpenAI翻译未翻译的技能
  python -m batch_translator translate --service openai --filter not_translated

  # 自检已翻译的技能
  python -m batch_translator review

  # 自检单个技能
  python -m batch_translator review --skill my-skill
        """
    )

    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    parser.add_argument('--base-path', help='技能库路径')

    subparsers = parser.add_subparsers(dest='command', help='子命令')

    subparsers.add_parser('analyze', help='分析技能翻译状态')

    translate_parser = subparsers.add_parser('translate', help='翻译技能')
    translate_parser.add_argument(
        '--service', '-s',
        choices=['openai', 'anthropic', 'minimax', 'mock'],
        default='mock',
        help='翻译服务'
    )
    translate_parser.add_argument(
        '--from', '-f',
        dest='from_lang',
        choices=['en', 'zh', 'ja', 'ko'],
        default='en',
        help='源语言 (source language)'
    )
    translate_parser.add_argument(
        '--to', '-t',
        dest='to_lang',
        choices=['en', 'zh', 'ja', 'ko'],
        default='zh',
        help='目标语言 (target language)'
    )
    translate_parser.add_argument('--dry-run', action='store_true', help='演练模式')
    translate_parser.add_argument('--limit', type=int, help='限制处理数量')
    translate_parser.add_argument('--force', action='store_true', help='强制翻译')
    translate_parser.add_argument('--filter', help='按状态过滤')
    translate_parser.add_argument('--min-chars', type=int, default=200, help='最少目标语言字符数')
    translate_parser.add_argument('--workers', '-w', type=int, default=1, help='并发工作线程数')

    review_parser = subparsers.add_parser('review', help='对照备份自检修复翻译结果')
    review_parser.add_argument('--skill', help='指定单个技能名称')
    review_parser.add_argument('--filter', help='按状态过滤（translated/incomplete）')

    args = parser.parse_args()
    setup_logging(args.verbose)

    if args.command == 'analyze':
        analyze_command(args)
    elif args.command == 'translate':
        translate_command(args)
    elif args.command == 'review':
        review_command(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
