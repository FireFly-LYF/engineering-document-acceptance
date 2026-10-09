# 版本更新记录

每轮更新以独立提交追加到 `main`。已发布提交保留，版本 tag 指向对应快照。

## v1.0.1 2026-10-09

- 补录已有真实提交的版本标记，增加本更新记录。
- 明确后续直接在 main 按轮次提交与推送的工作方式。
- 当前项目文件夹接入原有 Git 历史，便于直接查看后续变更。
- 本版本仅调整版本管理说明，核查业务代码与 v1.0.0 一致。

## v1.0.0 2026-10-09

对应提交：[c6e8ac6](https://github.com/FireFly-LYF/engineering-document-acceptance/commit/c6e8ac6e30d6890e44fc45c37294c80935eacb87)。

- 实现统一 Markdown/source map、全页解析和 Agnes OCR/字段候选。
- 新增可维护 tag、label、条件规则及数据库证据关系。
- 接入项目归属、齐套、字段一致性、范围、重复和版本核查。
- 新增人工复核、事实校验及 Word 导出。
- 验证：49 项 Python 测试、Word 解析校验、5 组模拟案例回归；实际 Agnes 调用和 Word 页面检查已完成。
- MySQL 适配器已提供，真实 MySQL 服务验证尚未完成。

## v0.1.1 2026-10-08

对应提交：[075b66c](https://github.com/FireFly-LYF/engineering-document-acceptance/commit/075b66c994ff9a60b11d4d65f748b8d91f01a59c)。

- 为演示 PDF 做字体子集处理，并纳入演示与公开参考 PDF。

## v0.1.0 2026-10-08

对应提交：[700aa46](https://github.com/FireFly-LYF/engineering-document-acceptance/commit/700aa46)。

- 初始 AGH 核查 Skill、文书 Skill 和合成演示项目。

早期版本标记根据现有真实提交补录。v1.0.0 的实现当时作为一次提交发布，本记录不拆分或改写那次已发布提交。
