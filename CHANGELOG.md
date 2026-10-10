# 版本更新记录

每轮更新以独立提交追加到 `main`。已发布提交保留，版本 tag 指向对应快照。

## v1.1.6 2026-10-10

- 新增前端框架 `web/`：用户→工程批次、ZIP/PDF/文件夹上传、核查后目录/文件打标（演示启发式，待接 audit_prepare）。

## v1.1.5 2026-10-10

- `engineering-doc-generator` 大纲与执笔规则改为竣工资料核查文书结构：工程概况 → 完整性 → 一致性 → 问题与证据 → 处理意见 → 结论。
- `engineering-archive-audit` 简报/报告用语对齐：完整性核查统计（已提供/缺失/错传或重复/需复核），交接文书 Skill 时指向上述章节顺序。

## v1.1.4 2026-10-10

- 新增完全正确对照包 `demo-housing-complete`（`tools/generate_complete_case.py`）：全量必需项含正式 E-01 与消防 G-01，字段与 manifest 一致，无错传/冲突/重复/不可读。
- `pdf_forms.py` 新增 `make_fire_acceptance_opinion`（消防验收意见书版式）。
- `audit_prepare` 冒烟：全部 required `provided`，无缺陷类 findings。

## v1.1.3 2026-10-09

- 消除合成 PDF 同质化：按文种拆分 builder（规划/施工许可、GF 合同、监理合同、技术文件、检测报告、竣工封面、竣工图目录、规划核实、GB50300 附录表），不再共用「双框封面报告」。
- 增补并索引公开参考 PDF：施工许可样表、GF-2017 合同、单位竣工验收报告、浙江统一用表等（`tools/fetch_public_pdfs.py`）。
- 字段抽取兼容异构样表别名（工程名称/证号/签约合同价等），并截断同行多字段粘连；收紧 E-01 正式验收命中，避免竣工报告页脚误配。
- 重生成两套 case；GT 核心结论不变（mixed：缺 E-01/G-01、FIELD×2、错传×2、检验批 DUP；near-miss：缺 D-01/E-01/G-01、开工日期冲突、近邻错传、UNREADABLE）。

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
