# 版本更新记录

每轮更新以独立提交追加到 `main`。已发布提交保留，版本 tag 指向对应快照。

## v1.1.2 2026-10-09

- 合成 PDF 改用仿 GB50300 附录与公开空白表版式（`tools/pdf_forms.py`）：检验批/分项/分部/观感表格化，报告类双框封面+著录+签章。
- 对照参考：`reference/public-pdfs/gb50300-2013-acceptance-standard.pdf`、`acceptance-check-forms-unified.pdf` 等；内容仍为合成，非真实档案。
- 重生成 `demo-housing-mixed` 与 `demo-housing-near-miss`；核查结论与既有评分约定保持一致。

## v1.1.1 2026-10-09

- 核查脚本：错传不参与字段共识；FIELD 仅保留本工程真冲突；简报/报告去路径与双重粘贴。
- 加固 `demo-housing-mixed`：错传混入正常目录、去掉「副本」文件名、预验收不带规则 code；收紧 ground_truth 评分说明。
- 新增对照包 `demo-housing-near-miss`：近邻混淆、开工日期冲突、缺 D-01、不可读扫描；造数脚本 `tools/generate_near_miss_case.py`。
- 空文本 PDF 标 `UNREADABLE` / `needs_human_review`。

## v1.1.0 2026-10-09

- `main` 恢复为 AGH 双 Skill + 确定性脚本工作流（对齐 v0.1.1 形态）。
- 移除 `app/` 流水线、数据库、YAML 配置与系统侧测试；Agent 阅读 Skill 完成规则匹配抽查与文书撰写。
- 完整系统实现保留在分支 `system`（对应 v1.0.0 / v1.0.1 快照），不改写已发布历史。

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
- 该系统快照另见分支 `system`。

## v0.1.1 2026-10-08

对应提交：[075b66c](https://github.com/FireFly-LYF/engineering-document-acceptance/commit/075b66c994ff9a60b11d4d65f748b8d91f01a59c)。

- 为演示 PDF 做字体子集处理，并纳入演示与公开参考 PDF。

## v0.1.0 2026-10-08

对应提交：[700aa46](https://github.com/FireFly-LYF/engineering-document-acceptance/commit/700aa46)。

- 初始 AGH 核查 Skill、文书 Skill 和合成演示项目。

早期版本标记根据现有真实提交补录。v1.0.0 的实现当时作为一次提交发布，本记录不拆分或改写那次已发布提交。
