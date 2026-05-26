# AGENTS.md

## 项目协作说明

GitDuPan 是一个 Python CLI 项目。修改代码时优先沿用现有目录结构，核心代码位于 `src/gitdupan`，测试位于 `tests`。

处理任务时注意：

- 变更范围要聚焦，避免顺手重构无关模块。
- 行为变更需要补充或更新测试。
- 不要提交 `build/`、`dist/` 等生成产物，除非用户明确要求。
- 修改用户可见功能时，要同步检查 README、版本号、发布说明是否需要更新。

## 发布与 Tag 规则

GitHub Actions 已配置自动发布流程，工作流文件为 `.github/workflows/release.yml`。

发布规则：

- 当推送符合 `v*` 格式的 tag 时，GitHub Actions 会自动构建各平台产物。
- tag 示例：`v0.1.9`、`v0.2.0`。
- 自动构建完成后，工作流会创建 GitHub Release 并上传构建产物。
- 发版前需要编写 release notes，说明本次更新内容、影响范围、兼容性变化和迁移注意事项。
- 发版前要确认版本号一致，重点检查 `pyproject.toml` 和 `src/gitdupan/__init__.py`。

建议发布步骤：

```bash
git status --short
uv run pytest
git tag vX.Y.Z
git push origin vX.Y.Z
```

## Git 提交规范

所有提交必须使用 Conventional Commits。

提交格式：

```text
<type>(<scope>): <description>

<body>

<footer>
```

允许的 `type`：

- `feat`: 新增用户可见功能
- `fix`: 修复问题
- `docs`: 仅文档变更
- `style`: 仅格式或样式变更
- `refactor`: 非功能、非修复的代码重构
- `perf`: 性能优化
- `test`: 添加或更新测试
- `build`: 构建系统或依赖变更
- `ci`: CI 配置变更
- `chore`: 维护类任务
- `revert`: 回滚提交

提交要求：

- 第一行必须简洁、准确、使用祈使句，不要以句号结尾。
- 非平凡变更必须包含 body，说明改了什么、为什么改、影响是什么。
- 有破坏性变更时，footer 必须包含 `BREAKING CHANGE: ...`。
- 推荐使用多个 `-m` 参数提交，确保标题和正文都存在。

示例：

```bash
git commit -m "fix(sync): validate large file pointers" -m "Check large file hashes before pushing so remote uploads cannot publish stale worktree content. This keeps small-file pack behavior unchanged."
```
