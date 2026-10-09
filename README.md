# 工程竣工资料核查

通过给定参考 Markdown、可维护 tag/label 和条件规则，对工程档案包做资料类型、项目归属、文载一致性、重复版本和明确范围的核查，保存数据库证据链并导出 Word。

仅处理本项目；Agnes key 从环境变量或本地 `.env` 读取。原始资料不修改，每次核查建立独立运行快照。

## 安装与运行

建议 Python 3.10+ 和 Node.js：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm.cmd install --prefix .agh/skills/engineering-doc-generator
.\.venv\Scripts\python.exe tools/generate_realistic_cases.py --missing-only
```

复制 `.env.example` 为 `.env` 并填写 Agnes key。默认接口为 `https://api.agnes-ai.cn/v1`，模型为 `agnes-3.0-flash`。

```powershell
# 本地确定性核查，未配置 OCR 的扫描页会明确进入复核
.\.venv\Scripts\python.exe -m app.cli run --case cases/realistic/school-issues --word

# 使用 Agnes 识别扫描页、提取字段候选和辅助撰写说明
.\.venv\Scripts\python.exe -m app.cli run --case cases/realistic/scans-and-unreadable --use-agnes --word
```

原 AGH Skill 入口继续可用：

```powershell
.\.venv\Scripts\python.exe .agh/skills/engineering-archive-audit/scripts/audit_prepare.py --case cases/realistic/school-issues --use-agnes --word
```

## 架构与可维护配置

- [系统架构](docs/工程竣工核查系统架构.md)
- [34 个 tag、34 个 label 及完整绑定](docs/tag-label完整字典.md)
- [给定核查参考 Markdown](reference/housing-audit-reference.md)
- `config/document_tags.yaml`：资料类型、别名、排除词。
- `config/field_definitions.yaml`：业务字段、含义、类型、单位、比较范围与策略。
- `config/tag_label_bindings.yaml`：每类资料允许提取的字段。
- `config/rules/housing-core.yaml`：17 条核心条件规则，需结合地区完整归档目录配置。

修改字典后运行 `tools/export_catalog.py` 更新可读字典。每次运行冻结配置指纹，不覆盖历史规则版本。`--reference` 可以指定项目内另一份参考 Markdown；不再让孤立的旧 JSON 清单绕过字段、范围和条件契约。

## 输入约定

```text
cases/<id>/
  manifest.json
  files/                   # PDF、DOCX、XLSX/XLS、图片、CSV/TSV/文本，可含子目录
  ground_truth.json        # 仅测试工具读取，核查器和模型不会读取
```

manifest 中保留项目参考值，并显式给出条件和应交范围：

```json
{
  "project_id": "example",
  "project_type": "房屋建筑工程",
  "project_name": "示例项目",
  "project_code": "EX-2026-001",
  "owner": "示例建设单位",
  "address": "示例工程地址",
  "contract_no": "SG-001",
  "contract_amount": "86500000",
  "audit_context": {
    "audit_stage": "post_acceptance",
    "regulatory_scope": "general_civil",
    "fire_regulation_applicable": true,
    "supervision_entrusted": true,
    "use_type": "school",
    "fire_category": "special",
    "fire_category_source": "经核实的项目分类依据",
    "fire_spotcheck_selected": false,
    "coverage_plan_confirmed": true
  },
  "coverage_plan": [
    {"tag": "INSPECTION_BATCH", "unit_name": "教学楼", "discipline": "结构", "location": "一层"}
  ]
}
```

条件未知时留空或 null，不自动判不适用。`regulatory_scope` 确认属于本参考的普通民用工程适用范围；抢险救灾、临时工程、农民自建低层住宅等不能自动套用本组验收规定。`fire_regulation_applicable` 及消防分类由调用方核实，模型不会仅凭名称/面积自动认定。上传 `file_tags` 可按相对路径提供分类线索，核查器仍以正文标题确认。Word/Excel 保存逻辑定位，不伪造物理页。

旧 `demo-housing-mixed` 缺少新规则适用条件与合同关联字段，会产生适用性/合同范围待复核，不能通过隐含假设伪造缺件结论。新的五组案例见 `cases/realistic`。

## 数据库和输出

默认 SQLite：`cases/<id>/_work/audit.sqlite`。MySQL 适配器使用同一证据实体设计；可在 `.env` 配置 `ENGINEERING_DATABASE_URL`，指定已创建的 MySQL 数据库。DDL 为 `database/schema.mysql.sql`，当前未在真实 MySQL 服务执行验证。

27 张表分别保存版本化字典、项目范围、运行、原件、逻辑资料、Markdown、片段、证据、候选、规则、问题、复核和文书。关联外键约束同一运行、同一文件、同一阅读单元及同一项目范围；哈希不唯一，保留重复上传。

每次运行保存：

```text
_work/runs/<run_id>/
  source_files/            # 原件只读副本
  markdown/<file_id>/      # unit_001.md + unit_001.source_map.json
  candidates.json
  audit-result.json        # 权威核查结果
  audit-report.md
  evidence-index.json
  statement-facts.json
  statement-validation.json
  正文.md
  run_stats.json
  deliverables/            # 可选 Word
```

`_work` 根目录保存最近一次运行的兼容产物和 `latest-run.json`。Word 另复制到 `生成结果/`，名称包含 run_id。导出前检查统计、占位符、路径、密钥和无依据的全量通过措辞；自由文本仍需人工校对。

## 人工复核

```powershell
.\.venv\Scripts\python.exe -m app.cli review --db cases/realistic/school-issues/_work/audit.sqlite --run <run_id> --finding <finding_id> --decision request_more --reason "请补充原始合同" --reviewer <reviewer_ref>
```

支持 confirm、dismiss、request_more。dismiss 需要 `--evidence <evidence_id>`，且证据必须属于同次运行。保存前后状态，不覆盖原始候选。复核不自动改写已经生成的文书；资料更正后重新核查，形成新运行和新文书。

## 验证与模拟材料

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
node tests/test_word.js
.\.venv\Scripts\python.exe tools/run_regression.py
```

模拟包包含：学校缺件/错传/编号金额冲突/重复，完整资料，多楼栋住宅范围缺口，合法价格变更和图纸版本/Office，真实像素扫描/混合 PDF/合订/损坏文件。项目和单位均虚构，truth 与模型输入隔离。

合成二进制文件不提交 Git。首次克隆后用 `--missing-only` 补齐已有测试元数据对应的文件，已有文件不覆盖，元数据不一致时拒绝操作。重新造数也可以使用新目录：

```powershell
.\.venv\Scripts\python.exe tools/generate_realistic_cases.py --root cases/realistic-new
```

本系统输出资料核查结论，不代替工程实体质量鉴定、主管部门行政验收或地区完整归档要求。范围计划未确认时，类型存在不能写成全部楼栋和部位齐套；扫描不可辨认时保留读取不足。
