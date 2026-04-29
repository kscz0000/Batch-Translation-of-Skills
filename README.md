# 批量翻译脚本使用指南

## 🚀 快速开始

```bash
cd batch_translator

# 查看翻译状态
python -m batch_translator analyze

# 使用 MiniMax 翻译未翻译的技能
python -m batch_translator translate --service minimax --filter not_translated

# 演练模式（不实际翻译）
python -m batch_translator translate --service mock --dry-run
```

---

## 📖 使用方法

### 翻译状态分析

```bash
python -m batch_translator analyze
```

生成 `translation-status-report.md`。

### 翻译技能

```bash
# 使用 MiniMax（主力服务）
python -m batch_translator translate --service minimax --filter not_translated

# 使用 OpenAI
python -m batch_translator translate --service openai --filter not_translated

# 使用 Claude
python -m batch_translator translate --service anthropic --filter not_translated

# 演练模式
python -m batch_translator translate --service mock --dry-run

# 限制数量
python -m batch_translator translate --service minimax --limit 10

# 并发翻译（3线程）
python -m batch_translator translate --service minimax --workers 3

# 强制重新翻译
python -m batch_translator translate --service minimax --force
```

### 翻译审核

```bash
# 标记待审核
python -m batch_translator review mark

# 列出待审核
python -m batch_translator review list

# 审核通过
python -m batch_translator review approve --skill "skill-name" --notes "审核通过"

# 审核拒绝
python -m batch_translator review reject --skill "skill-name" --reason "质量问题"
```

---

## 📋 翻译标准

| 部分 | 处理 | 示例 |
|------|------|------|
| name | 不翻译 | `name: seo-strategy` |
| description | 必须翻译 | `description: 当用户想要...` |
| 标题 (# ## ###) | 翻译 | `# SEO策略` |
| 正文 | 意译 | 流畅中文 |
| 代码块 (yaml/bash/js) | 保护 | 保留原样（占位符 `[KEEP_CODE_BLOCK_N_DO_NOT_REMOVE]` 保护） |
| 代码注释 | 翻译 | `# This script...` → `# 此脚本...` |
| 代码行 | 保护 | `mkdir -p "$DIR"` 保持不变 |
| URL | 不翻译 | 保留原样 |
| 工具名 | 不翻译 | Google Ads, GA4 |

**术语保留**: API, SDK, CLI, URL, SEO, CTR, React, Vue, Node.js, Python 等

---

## ✅ 验证机制

翻译后自动验证：

- [x] description 字段已翻译为中文（≥10 字符）
- [x] 正文至少有 1 个中文字符（防止 AI 跳过正文）
- [x] 格式正确（frontmatter、代码块闭合）
- [x] 语义相似度正常（警告，非强制）
- [x] 术语大小写一致（警告，非强制）

**重试机制**：验证失败时自动重试（最多3次），每次重新读取原始内容。

### 错误处理

| 场景 | 处理方式 |
|------|---------|
| API 调用失败 | 抛出 `TranslationServiceError`，触发回滚到原文 |
| 翻译结果无中文 | 抛出 `TranslationServiceError`（中文字符数增加 < 10） |
| 代码块丢失 | 标记为需重翻，不自动恢复（避免追加到末尾产生重复） |
| 占位符被 LLM 吞掉 | `_postprocess_content` 记录警告日志，触发重翻 |

---

## 🔧 模块结构

```
batch_translator/
├── __main__.py          # 包入口
├── main.py              # CLI 命令处理
├── core.py              # 翻译流程编排
├── config.py            # 配置
├── analyzer.py          # 翻译状态分析
├── validator.py         # 质量验证
├── reviewer.py          # 人工审核
├── reporter.py          # 报告生成
├── file_manager.py     # 文件操作（支持子技能+递归）
├── models.py            # 数据模型
├── exceptions.py        # 异常定义
├── utils.py             # 工具函数
└── services/
    ├── base.py          # 翻译服务基类
    ├── factory.py       # 服务工厂（策略模式）
    ├── minimax.py       # MiniMax 翻译（主力）
    ├── openai.py        # OpenAI 翻译
    ├── anthropic.py     # Claude 翻译
    └── mock.py          # Mock 翻译（测试用）
```

详细架构说明请参考 [ARCHITECTURE.md](batch_translator/ARCHITECTURE.md)。

---

## 📁 输出文件

- `translation-status-report.md` - 翻译状态统计报告
- `batch-translation-report.md` - 批量翻译结果报告（文件已存在时自动加时间戳，不覆盖旧报告）

---

## 💡 提示

1. **先测试再批量**: 用 `--limit 5` 测试
2. **使用演练模式**: `--dry-run` 不实际翻译
3. **并发加速**: 用 `--workers 3` 并行翻译
4. **监控进度**: 查看生成的报告文件
5. **备份重要**: `raw/` 目录保存原始文件
6. **已有重复代码块**: 如文件末尾有 `<!-- 从备份恢复的代码块 -->` 标记，可用 `--force` 重翻来清理

---

## 🔌 API Key 配置

在 `.env` 中配置：

```env
MINIMAX_API_KEY=$YOUR_MINIMAX_API_KEY
MINIMAX_MODEL=MiniMax-M2.7-HighSpeed
```
