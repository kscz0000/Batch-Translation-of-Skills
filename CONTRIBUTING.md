# 贡献指南

感谢您对本项目的兴趣！我们欢迎各种形式的贡献。

---

## 一、开发环境设置

### 1.1 克隆项目

```bash
git clone https://github.com/kscz0000/Batch-Translation-of-Skills.git
cd batch_translator
```

### 1.2 创建虚拟环境

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
.\venv\Scripts\activate  # Windows
```

### 1.3 安装依赖

```bash
pip install -r requirements.txt
```

### 1.4 配置环境变量

```bash
# 复制模板
cp .env.example .env

# 编辑 .env 填入你的 API keys
```

---

## 二、安全开发规范

### 2.1 敏感信息处理

**绝对禁止**在代码中硬编码任何敏感信息：

| 禁止类型 | 正确做法 |
|---------|---------|
| API Key | 使用环境变量 `os.getenv('API_KEY')` |
| 数据库密码 | 使用环境变量或密钥管理服务 |
| 个人路径 | 使用相对路径或 `os.getenv('BASE_PATH')` |
| 访问令牌 | 使用环境变量 |
| 私钥 | 绝不提交，使用密钥管理服务 |

### 2.2 提交前检查清单

在提交代码前，确保：

- [ ] 未在代码中硬编码任何 API Key 或令牌
- [ ] 未提交 `.env` 文件
- [ ] 未包含个人绝对路径
- [ ] 未包含个人联系方式（邮箱、电话等）
- [ ] 所有敏感配置使用环境变量

### 2.3 发现敏感信息泄露

如果您发现代码中存在敏感信息泄露，请：

1. **不要**在公开 Issue 中提及具体敏感信息
2. 发送邮件至 security@example.com 或通过私人消息联系维护者
3. 我们会在 24 小时内确认并在 72 小时内修复

---

## 三、代码规范

### 3.1 Python 代码风格

遵循 PEP 8 规范：

```bash
# 使用 black 格式化
pip install black
black .

# 使用 flake8 检查
pip install flake8
flake8 .
```

### 3.2 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 模块 | 小写下划线 | `file_manager.py` |
| 类 | 大驼峰 | `BatchTranslator` |
| 函数 | 小写下划线 | `translate_single` |
| 常量 | 全大写下划线 | `MAX_RETRIES` |

### 3.3 文档字符串

所有公共模块、类和函数应包含文档字符串：

```python
def translate(content: str) -> str:
    """
    翻译内容。

    Args:
        content: 原始内容

    Returns:
        翻译后的内容
    """
    pass
```

---

## 四、测试

### 4.1 运行测试

```bash
pytest tests/
```

### 4.2 编写测试

- 每个新功能应包含单元测试
- 使用 `pytest` 框架
- 测试文件命名：`test_<module_name>.py`

---

## 五、提交规范

### 5.1 Commit 消息格式

```
<类型>: <简短描述>

<详细说明（可选）>
```

类型：
- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更新
- `refactor`: 重构
- `security`: 安全相关
- `chore`: 构建/工具更新

示例：
```
feat: 添加多语言翻译支持

- 支持英语、中文、日语互译
- 新增 --from 和 --to 命令行参数
```

### 5.2 Pull Request

1. Fork 本仓库
2. 创建特性分支 `git checkout -b feature/your-feature`
3. 提交更改
4. 推送分支 `git push origin feature/your-feature`
5. 创建 Pull Request

---

## 六、问题反馈

### 6.1 Bug 报告

请使用 GitHub Issues，标签选择 `bug`。

### 6.2 功能请求

请使用 GitHub Issues，标签选择 `enhancement`。

### 6.3 安全问题

请通过以下方式私下联系：

- GitHub 私人消息
- 邮件至 security@example.com

---

## 七、许可证

通过贡献代码，您同意将您的贡献按照项目许可证发布。

---

*最后更新：2026-04-28*
