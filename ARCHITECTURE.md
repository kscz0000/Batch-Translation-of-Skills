# Batch Translator 架构与设计文档

> 本文档详细梳理了 `batch_translator` 模块的业务逻辑与代码架构。

---

## 一、项目概述

### 1.1 核心定位

`batch_translator` 是一个用于**批量翻译技能文档（Skill）**的 Python 模块，主要用于将英文技能文档翻译为中文。它不是一个通用翻译工具，而是专门针对技能文档场景设计的领域化翻译系统。

### 1.2 版本与依赖

- **当前版本**: 4.1.0
- **核心依赖**:
  - `openai` / `anthropic` - AI 翻译服务
  - `PyYAML` - Frontmatter 解析
  - `python-dotenv` - 环境变量加载

### 1.3 运行方式

```bash
# 分析所有技能翻译状态
python -m batch_translator analyze

# 翻译未翻译的技能
python -m batch_translator translate --service openai --filter not_translated

# 自检已翻译的技能
python -m batch_translator review

# 自检单个技能
python -m batch_translator review --skill my-skill
```

---

## 二、核心业务流

### 2.1 翻译流程总览

```
┌─────────────────────────────────────────────────────────────────┐
│                      翻译流程 (translate)                        │
├─────────────────────────────────────────────────────────────────┤
│  1. [分析阶段] 扫描技能目录，确定需要翻译的技能                    │
│           ↓                                                      │
│  2. [备份阶段] 读取英文原文，创建 raw/ 备份                       │
│           ↓                                                      │
│  3. [翻译阶段] 调用 AI 服务翻译 (最多 3 轮)                      │
│      ┌──────────────────────────────────────┐                    │
│      │ 3.1 调用翻译服务                      │                    │
│      │ 3.2 写入翻译结果                     │                    │
│      │ 3.3 翻译 references/ 目录           │                    │
│      │ 3.4 更新 _meta.json                  │                    │
│      │ 3.5 自检：对照备份检查质量           │                    │
│      │ 3.6 自检通过？ → 4                  │                    │
│      │ 3.7 自检未通过？ → 3.1 (下一轮)     │                    │
│      └──────────────────────────────────────┘                    │
│           ↓                                                      │
│  4. [收尾阶段] 自检通过则删除备份，否则保留备份                    │
│           ↓                                                      │
│  5. [报告阶段] 生成翻译报告                                       │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 自检修复流程

```
┌─────────────────────────────────────────────────────────────────┐
│                      自检修复 (review)                          │
├─────────────────────────────────────────────────────────────────┤
│  检查项：                                                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 1. frontmatter 是否完整 → 丢失则从备份恢复                 │   │
│  │ 2. 代码块数量是否一致 → 丢失则标记需重翻                   │   │
│  │ 3. description 是否翻译 → 未翻译则标记需重翻               │   │
│  │ 4. 代码块内注释 → 仅记录（已知限制，不阻塞）               │   │
│  │ 5. references/ 是否翻译 → 未翻译则标记                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  修复策略：                                                       │
│  - 能自动修：frontmatter 丢失 → 从备份恢复                        │
│  - 不能修：description 未翻译 → 触发重翻                          │
│  - 代码块丢失 → 触发重翻（不自动追加，避免重复）                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 状态模型

| 状态 | 含义 | 处理策略 |
|------|------|---------|
| `TRANSLATED` | 已完成翻译 | 跳过（除非 force） |
| `INCOMPLETE` | 部分翻译 | 需要翻译 |
| `NOT_TRANSLATED` | 未翻译 | 需要翻译 |
| `ERROR` | 错误 | 记录并跳过 |
| `SKIP` | 跳过 | 不处理（如引用链接） |

---

## 三、代码架构

### 3.1 模块依赖图

```
┌─────────────────────────────────────────────────────────────────┐
│                        main.py                                  │
│                    (命令行入口)                                  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           ↓               ↓               ↓
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │  analyzer.py │ │  core.py     │ │  reviewer.py │
    │  (状态分析)   │ │ (翻译流程)   │ │ (自检修复)   │
    └──────────────┘ └──────────────┘ └──────────────┘
           │               │               │
           └───────────────┼───────────────┘
                           ↓
           ┌───────────────────────────────┐
           │        file_manager.py        │
           │      (文件 I/O 操作)          │
           └───────────────────────────────┘
                           │
           ┌───────────────┴───────────────┐
           ↓                               ↓
    ┌──────────────┐              ┌──────────────┐
    │  config.py   │              │   utils.py   │
    │  (配置管理)   │              │  (工具函数)   │
    └──────────────┘              └──────────────┘
           │                               │
           └───────────────┬───────────────┘
                           ↓
           ┌───────────────────────────────┐
           │       services/factory.py    │
           │       (服务工厂)              │
           └───────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ↓                  ↓                  ↓
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  base.py     │  │  minimax.py  │  │  openai.py   │
│ (服务基类)    │  │ (MiniMax)    │  │  (OpenAI)    │
└──────────────┘  └──────────────┘  └──────────────┘
        │                  │                  │
        ↓                  ↓                  ↓
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  anthropic.py│  │   mock.py    │  │              │
│ (Claude)     │  │ (模拟服务)    │  │              │
└──────────────┘  └──────────────┘  └──────────────┘
```

### 3.2 设计模式应用

| 模式 | 应用位置 | 说明 |
|------|---------|------|
| **策略模式** | `services/` | 不同 AI 服务实现统一的 `TranslationService` 接口 |
| **工厂模式** | `services/factory.py` | `TranslationServiceFactory` 统一创建服务实例 |
| **单例模式** | 全局 | `TranslationConfig` 通常单例使用 |
| **模板方法** | `services/base.py` | `get_translation_prompt()` 定义翻译提示词模板 |

---

## 四、核心模块详解

### 4.1 main.py - 命令行入口

**职责**: 解析命令行参数，调度子命令

**支持的命令**:

| 命令 | 功能 | 关键参数 |
|------|------|---------|
| `analyze` | 分析技能翻译状态 | `--base-path` |
| `translate` | 翻译技能 | `--service`, `--filter`, `--force`, `--workers` |
| `review` | 自检修复翻译结果 | `--skill`, `--filter` |

**核心流程**:

```python
# 1. 加载 .env 文件
# 2. 解析命令行参数
# 3. 根据 command 分发到对应 handler
# 4. 生成并保存报告
```

### 4.2 core.py - 翻译流程编排

**职责**: 编排完整的翻译流程（翻译 + 自检循环）

**核心方法**:

| 方法 | 职责 |
|------|------|
| `translate_single()` | 单个技能翻译（含自检循环） |
| `translate_batch()` | 批量翻译（支持并发） |
| `_check_status()` | 检查技能翻译状态 |
| `_rollback()` | 回滚到备份 |
| `_record_failure()` | 记录失败信息 |

**翻译单技能的流程**:

```
1. 检查是否已翻译 → 跳过（除非 force）
2. 读取原文
3. 检测 raw/ 备份是否为英文原文（中文更少）
4. 备份原文到 raw/
5. 循环 (最多 3 轮):
   a. 调用翻译服务
   b. 写入翻译结果
   c. 翻译 references/
   d. 更新 _meta.json
   e. 自检：对照备份检查
   f. 自检通过？ → 完成
   g. 自检未通过？ → 下一轮重翻
6. 自检通过且无修复 → 删除备份
7. 自检通过但有修复 → 保留备份（防止有问题）
8. 达到上限仍未通过 → 兜底处理
```

### 4.3 file_manager.py - 文件操作

**职责**: 封装所有文件 I/O 操作

**核心方法**:

| 方法 | 职责 |
|------|------|
| `read()` | 读取技能文件 |
| `write()` | 写入技能文件 |
| `backup()` | 创建备份（包含 references/ 和子目录） |
| `restore()` | 恢复备份 |
| `cleanup()` | 删除备份 |
| `update_meta()` | 更新 _meta.json |
| `translate_all_references()` | 翻译 references/ 目录 |
| `translate_directory()` | 翻译目录下所有可翻译文件 |

**文件结构约定**:

```
<skill-name>/
├── SKILL.md          # 技能主文件
├── _meta.json        # 元数据（locale: zh-CN）
├── references/       # 参考文档目录
│   ├── ref1.md
│   └── ref2.md
└── raw/              # 英文原文备份（翻译成功后删除）
    ├── SKILL.md
    └── references/
```

**不翻译的文件**:
- 二进制文件（图片、音视频、PDF 等）
- 配置文件（LICENSE, .gitignore, package.json）
- 已翻译文件（`-CN.md`, `-original.md`, `.zh-CN.md`）

### 4.4 analyzer.py - 状态分析

**职责**: 分析技能翻译状态，生成统计报告

**核心方法**:

| 方法 | 职责 |
|------|------|
| `get_skills()` | 获取所有技能名称（含子技能） |
| `analyze()` | 分析单个技能 |
| `analyze_all()` | 分析所有技能 |
| `filter_by_status()` | 按状态过滤技能 |

**分析维度**:
- 中文字符数
- description 是否翻译
- frontmatter 完整性
- _meta.json 存在性
- locale 标记

### 4.5 reviewer.py - 自检修复

**职责**: 对照备份检查翻译质量，自动修复可修复问题

**检查项与修复策略**:

| 检查项 | 问题 | 修复策略 |
|--------|------|---------|
| frontmatter | 丢失 | ✅ 从备份恢复 |
| frontmatter | 字段丢失 | ✅ 从备份恢复 |
| 代码块 | 数量减少 | ❌ 触发重翻（不自动追加） |
| description | 未翻译 | ❌ 触发重翻 |
| 代码块注释 | 未翻译 | ⚠️ 仅记录（已知限制） |
| references/ | 未翻译 | ❌ 标记待处理 |

### 4.6 validator.py - 质量验证

**职责**: 验证翻译质量（仅检查，不修改）

**验证项**:
1. 中文字符数是否达标（默认 200）
2. description 是否包含中文（至少 10 字）
3. frontmatter 格式是否完整
4. 代码块是否正确闭合

### 4.7 services/base.py - 翻译服务基类

**职责**: 定义翻译服务接口和翻译提示词

**关键组件**:

| 组件 | 说明 |
|------|------|
| `PRESERVE_TERMS` | 必须保留大小写的技术术语 |
| `TRANSLATION_PROMPT_TEMPLATE` | 翻译提示词模板 |
| `translate()` | 抽象方法，子类实现 |
| `is_available()` | 检查服务可用性 |

**提示词关键规则**:
- `name` 字段不翻译
- `description` 必须翻译为中文
- 技术术语保留原文大小写
- 代码块受占位符保护，不翻译
- 保持 Markdown 结构

### 4.8 services/minimax.py - MiniMax 实现

**职责**: MiniMax API 翻译服务的完整实现

**核心特性**:

| 特性 | 说明 |
|------|------|
| 代码块保护 | 使用占位符 `[KEEP_CODE_BLOCK_X_DO_NOT_REMOVE]` 保护代码块 |
| frontmatter 分离 | 单独翻译 description 和 body，最后组装 |
| 分段翻译 | 内容过长时按 ## 标题分段 |
| 后处理 | 恢复代码块、清理多余包裹 |
| 超时重试 | 最多 3 次重试，指数退避 |

**预处理流程**:

```
原文 → 提取代码块 → 替换为占位符 → 翻译 → 恢复代码块
```

**分段翻译流程**:

```
1. 分离 frontmatter 和 body
2. 翻译 description（专用 prompt）
3. 翻译 body（分段处理）
4. 组装 frontmatter（保留原始结构）
5. 验证翻译结果（中文增量检查）
```

### 4.9 reporter.py - 报告生成

**职责**: 生成各种格式的报告

| 方法 | 输出 |
|------|------|
| `generate_translation_report()` | 翻译完成报告 |
| `generate_analysis_report()` | 技能翻译状态统计报告 |
| `generate_review_report()` | 自检修复报告 |
| `save_report()` | 保存报告到文件（自动加时间戳） |

---

## 五、数据模型

### 5.1 枚举类型

```python
class TranslationStatus(Enum):
    TRANSLATED = "translated"      # 已完成
    INCOMPLETE = "incomplete"     # 部分翻译
    NOT_TRANSLATED = "not_translated"  # 未翻译
    ERROR = "error"              # 错误
    SKIP = "skip"                # 跳过
    UNKNOWN = "unknown"           # 未知
```

### 5.2 数据类

| 类名 | 用途 |
|------|------|
| `TranslationResult` | 单个技能翻译结果 |
| `TranslationReport` | 批量翻译报告 |
| `SkillAnalysis` | 单个技能分析结果 |
| `AnalysisReport` | 全部分析统计报告 |
| `ReviewCheckResult` | 自检修复结果 |
| `ValidationResult` | 验证结果 |

---

## 六、关键设计决策

### 6.1 为什么要保留英文备份？

- **安全网**: 翻译失败或质量不佳时，可回滚
- **自检依据**: 对照备份检查格式、结构完整性
- **diff 能力**: 可对比翻译前后的差异

### 6.2 为什么要循环自检？

- AI 翻译质量不稳定
- 单次翻译可能遗漏 description 等关键字段
- 通过多轮尝试提高整体成功率

### 6.3 为什么 references/ 只翻译一次？

- references/ 通常是辅助文档
- 重复翻译浪费 API 调用
- 第一轮翻译后内容已足够

### 6.4 为什么要单独处理 frontmatter？

- AI 容易丢失或错误翻译 frontmatter
- description 是用户首先看到的，需要准确
- 分离处理可以精确控制翻译质量

### 6.5 为什么代码块要用占位符保护？

- AI 倾向于翻译代码块内的注释
- 代码块结构需要原样保留
- 占位符确保代码块不被修改

---

## 七、使用示例

### 7.1 Python API

```python
from batch_translator import (
    TranslationConfig,
    TranslationServiceFactory,
    BatchTranslator,
    TranslationAnalyzer,
)

# 1. 配置
config = TranslationConfig(base_path='./skills')

# 2. 创建翻译器
translator = TranslationServiceFactory.create('minimax')

# 3. 分析
analyzer = TranslationAnalyzer(config)
skills = analyzer.get_needs_translation()

# 4. 翻译
batch = BatchTranslator(config, max_workers=1)
report = batch.translate_batch(skills, translator)

# 5. 查看报告
print(f"成功率: {report.success_rate}%")
```

### 7.2 命令行

```bash
# 分析所有技能
python -m batch_translator analyze

# 使用 MiniMax 翻译
python -m batch_translator translate -s minimax

# 使用 OpenAI 强制重翻
python -m batch_translator translate -s openai --force

# 只翻译未翻译的
python -m batch_translator translate -s minimax --filter not_translated

# 自检并自动修复
python -m batch_translator review

# 并发翻译（4 个线程）
python -m batch_translator translate -s minimax -w 4
```

---

## 八、配置项

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `base_path` | `skills/` | 技能库路径 |
| `skill_file` | `SKILL.md` | 技能文件名 |
| `meta_file` | `_meta.json` | 元数据文件名 |
| `backup_dir` | `raw` | 备份目录名 |
| `min_chinese_chars` | `200` | 最少中文字符数 |
| `max_retries` | `3` | 最大重试次数 |

---

## 九、总结

`batch_translator` 是一个**领域化、场景化**的翻译系统，它针对技能文档的特定需求（frontmatter、代码块保护、references 翻译等）做了专门优化。

**核心价值**:
1. **安全**: 备份 + 回滚机制确保不会丢失原文
2. **质量**: 自检循环 + 自动修复提高翻译质量
3. **灵活**: 支持多种 AI 服务，可扩展
4. **高效**: 支持并发翻译
5. **可观测**: 完整的报告体系

**设计亮点**:
- 策略模式让 AI 服务可替换
- 前置处理 + 后置处理保护代码块
- frontmatter 分离翻译确保关键字段准确
- 多轮自检循环提高成功率
