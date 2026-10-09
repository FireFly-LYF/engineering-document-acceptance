---
name: engineering-archive-audit
description: 使用给定参考 Markdown、可维护工程 tag/label、Agnes 候选与原文校验核查工程资料，输出证据与运行数据库。
---

# 工程竣工资料核查

先运行项目级核查核心，Agent 仅阅读简报、结果和问题引用片段，避免重新通读所有文件。用户文件与 manifest 只读；运行产物位于 `_work`。

```powershell
.\.venv\Scripts\python.exe .agh/skills/engineering-archive-audit/scripts/audit_prepare.py --case cases/<id> --use-agnes --word
```

离线模式省略 `--use-agnes`。扫描页无法识别时明确复核，不判作未提交。参考入口为 `reference/housing-audit-reference.md`，通过 `--reference` 指定其他项目内参考；旧 JSON 为历史示例，不自动作为当前规则。

查看 `_work/audit-result.json`、`audit-report.md`、`evidence-index.json` 和 `agent-brief.md`。所有字段保留候选、角色和来源；错传不参与主项目共识。按同合同、同事件或同部位比较，不能混合结算金额与原始合同额。

条件未知时 not_evaluated，不无条件通过；类型已提供不代表范围全部齐套。消防验收意见、备案凭证、抽查结果分支独立，预验收不替代正式验收。签署观察和文载合格不是效力或实体质量认定。

人工复核使用 `python -m app.cli review`，带运行、问题、理由及必要证据；不直接覆盖 SQL、原件或候选。需要更正时提交带来源的新资料并重跑，保留历史运行。

文书已经有事实骨架，交给 engineering-doc-generator prepare/build；统计不能脱离 statement-facts.json。原件快照、Markdown/source map 和数据库关系均保留用于追溯。
