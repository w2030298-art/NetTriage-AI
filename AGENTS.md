# AGENTS.md — 项目执行规范

> 全局规范见 `~/.config/opencode/AGENTS.md`，定义了自治迭代规则和 Web 模式契约。
> 本文件只补充项目特定信息。

## 项目信息
- **项目名称**：NetTriage-AI
- **技术栈**：FastAPI + DeepSeek API + Pydantic v2 + Pandas + SQLModel/SQLite

## 启动协议

每次新对话：
1. 检查 `docs/inbox/` 有无新文件 → 有则 merge-back
2. 读 report.md → 上次执行状态
3. 读 plan.md Status 区块 → 当前进度
4. 判断任务来源（dispatch / 口头 / 无）→ 对应处理
5. 简短报告状态

## 代码规范
- 格式化：Ruff（格式化 + Lint）
- 缩进：4 空格
- 命名：PEP 8（snake_case 变量/函数，PascalCase 类，UPPER_CASE 常量）
- Git 提交：Conventional Commits + 中文描述（feat: 添加xxx / fix: 修复xxx）
- 类型标注：Pydantic v2 模型优先，辅助 Python type hints

## 项目特定规则
- **安全第一**：不得在代码、文档或配置文件中记录 API Key、密钥、Token 等敏感信息
- 所有敏感变量一律使用环境变量（.env），且 .env 文件必须加入 .gitignore
- DeepSeek API Key 等凭据仅通过环境变量注入，不得硬编码
- API 错误响应不得泄露内部实现细节（栈追踪、数据库结构等）

## 禁止
- 硬编码密钥、Token、API Key
- 提交 .env 文件
- 使用 `as any`、`@ts-ignore` 等类型绕过（Python 中对应：`# type: ignore` 需注释理由）
- 空 except 块（`except: pass`）
- 在错误响应中暴露栈追踪或内部路径
