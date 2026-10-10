---

## name: engineering-archive-audit
description: >-
  Audits a construction project file pack for completeness and cross-document
  consistency against a configurable archive checklist (房屋建筑 / 道路桥梁 /
  市政管线). Classifies files, extracts key fields, flags missing / duplicate /
  mismatched / conflicting items with evidence. Use when the user says 竣工资料核查,
  档案完整性检查, 齐套核验, 归档目录比对, engineering-archive-audit, or asks to
  check a 建设工程竣工资料包.

# 建设工程竣工资料 · 完整性与一致性核查

在 AGH 会话中完成核查，但**确定性步骤必须先跑脚本**，Agent 只做抽查与润色，以降低 token、缩短耗时、提高结果稳定。

**默认演示范围**：房屋建筑工程竣工资料智能完整性与一致性核查。  
道路/桥梁、市政管线通过切换 `rules/*.json` 支持。

## 何时启用

用户指定项目包并要求：竣工资料/档案齐套核查、缺件检查、跨文件一致性、错传/重复/冲突判定。

若还要正式「情况说明」Word：核查完成后点名 `**engineering-doc-generator`**（文书生成 Skill）。

## 目录约定（工作区）

```text
engineering-document-acceptance/
├── .agh/skills/
│   ├── engineering-archive-audit/
│   │   ├── SKILL.md
│   │   ├── rules/
│   │   └── scripts/audit_prepare.py    # 确定性准备（必跑）
│   └── engineering-doc-generator/      # 文书生成（prepare/build）
└── cases/<project-id>/
    ├── manifest.json
    ├── files/
    └── _work/
```

**只读**：`cases/<id>/files/`**、`manifest.json`、本 Skill `rules/**`。  
**可写**：仅 `cases/<id>/_work/`**。

## 规则模板层（可配置，勿写死一地目录）

1. 优先读取用户指定的规则文件路径。
2. 否则读 `cases/<id>/manifest.json` 的 `project_type` / `rules_profile`。
3. 再否则按工程类型加载本 Skill 内：
  - `rules/housing-construction.json` — 房屋建筑工程（默认）
  - `rules/road-bridge.json` — 道路/桥梁（可后续补全）
  - `rules/municipal-pipeline.json` — 市政管线（可后续补全）
4. 若对应 JSON 不存在或 `required_documents` 为空：在报告首页声明「规则模板未就绪」，仍做接收清单、分类与字段抽取，**完整性缺失判定标为「规则不足，未判定」**，禁止虚构地方标准条文。

规则条目最小字段：


| 字段         | 含义                                      |
| ---------- | --------------------------------------- |
| `code`     | 清单编号（如 E-01）                            |
| `name`     | 标准名称                                    |
| `required` | 是否必需                                    |
| `stage`    | 阶段：工程准备 / 监理 / 施工 / 竣工图 / 竣工验收 / 专项验收 等 |
| `category` | 分类标签（与下文分类层对齐）                          |
| `aliases`  | 别名，用于匹配文件名与文内标题                         |
| `notes`    | 可选：不能被何种类文件替代等说明                        |


**上位依据（表述用，勿假装已加载全文）**：住房城乡建设部《建设工程文件归档规范》及相关地方「归档目录 / 办事指南 / 空白样表」仅作规则模板来源说明；具体项目以当前加载的 JSON 清单为准。

## 执行进度（脚本优先）

```text
进度:
- [ ] 1. 确认 cases/<id> 与规则模板
- [ ] 2. 运行 audit_prepare.py（必做，勿用手搓 inventory/findings）
- [ ] 3. 阅读 _work/audit-brief.md + findings.json（不要通读全部 PDF）
- [ ] 4. 仅对本工程字段冲突 / 错传 / 明显误判做抽查修正；勿把错传级联当多条本工程冲突
- [ ] 5. 如需，润色 audit-report.md（不改结论方向）
- [ ] 6. 摘要完整性核查统计（已提供/缺失/错传或重复/需复核）；文书交给 engineering-doc-generator
```

### 确定性脚本（必跑）

在工作区根目录：

```bash
python .agh/skills/engineering-archive-audit/scripts/audit_prepare.py --case cases/demo-housing-mixed
python .agh/skills/engineering-archive-audit/scripts/audit_prepare.py --case cases/demo-housing-near-miss
```

脚本会写入：`inventory.json`、`classification.json`、`fields.json`、`field_consensus.json`、`findings.json`、`audit-report.md`、`audit-brief.md`。  
错传/他项文件不参与齐套命中与字段共识；本工程 FIELD 仅保留相对 manifest 锚值的真冲突。  
空文本/损坏扫描标 `UNREADABLE`（`needs_human_review`），不能据此认定已提供。  
演示对照：`demo-housing-mixed`（远域错传/编号金额/重复）、`demo-housing-near-miss`（近邻混淆/开工日期/缺检测/不可读）。  
**禁止**让 Agent 重新枚举全部文件或对每份 PDF 做完整阅读来「重做」上述产物。

ZIP：先解压到 `cases/<id>/files/` 或 `_work/extracted/`，再跑脚本。

## 1. 文件接收层

对每个文件记录并写入 `_work/inventory.json`：

- `path`（相对项目根）、`filename`、`ext`
- `size_bytes`、可知的 `page_count`
- `container`（若来自 ZIP 内路径）
- `sha256` 或内容指纹（若环境允许；不允许则省略并注明）

支持类型：PDF、JPG/PNG、Word、Excel、ZIP。  
无法打开的文件：列入 inventory，状态 `unreadable`，后续分类为 `unknown`。

## 2. 文档分类层

为每份文件给出 **一个主类** + 可选 `secondary`，写入 `_work/classification.json`。

主类枚举：


| category                | 说明    |
| ----------------------- | ----- |
| `contract`              | 合同类   |
| `preparation`           | 开工准备类 |
| `supervision`           | 监理类   |
| `construction`          | 施工记录类 |
| `material_test`         | 材料检测类 |
| `as_built_drawing`      | 竣工图   |
| `completion_acceptance` | 竣工验收类 |
| `special_acceptance`    | 专项验收类 |
| `other`                 | 其他    |
| `unknown`               | 无法判断  |


**禁止只依赖文件名。** 综合：

1. 文件名与别名；
2. 首页/表头标题、表格栏名、关键词（如「竣工验收报告」「监理」「检验批」）；
3. 可见印章/签署栏语义（「建设单位」「监理单位」等）——无 OCR 时根据可读文本与用户描述降级，并在证据中写明「未做版面 OCR，依据文本/文件名」；
4. 与规则模板 `stage` / `category` / `aliases` 的对应关系。

每条分类须带 `confidence`（high/medium/low）与 `evidence`（引用了标题句、关键词或文件名哪一段）。

## 3. 字段抽取层

尽量从每份文件抽取，写入 `_work/fields.json`（按文件；缺失键省略，禁止填「暂缺/XXXX」）：

- 项目名称、项目编号
- 建设单位、施工单位、监理单位、设计单位
- 工程地址
- 开工日期、竣工日期
- 合同金额
- 文件编号 / 报告编号
- 签字盖章信息（有哪些角色已签、是否见到印章描述）

跨文件汇总到 `_work/field_consensus.json`：

- 各关键字段的「众数/锚值」候选；
- 冲突列表：`field`、`values[]`（值 + 来源文件）、`severity`。

锚值优先级（有则用之）：`manifest.json` 声明 > 竣工验收报告类文件 > 合同 > 其他。

## 4. 完整性与一致性核查层

对照已加载规则，对每个 `required_documents[]` 条目及跨文件约束产出 `_work/findings.json`。

### 完整性核查状态（条目级 `status`）

对照归档清单逐项判定，用语与竣工资料核查记录一致：


| status                          | 文书用语  | 含义                      |
| ------------------------------- | ----- | ----------------------- |
| `provided`                      | 已提供   | 已提供且可对齐该清单项             |
| `missing`                       | 缺失    | 必需项未找到可接受文件             |
| `suspect_duplicate_or_misfiled` | 错传或重复 | 疑似重复或错传（含他项工程文件混入）      |
| `needs_human_review`            | 需复核   | 证据不足、别名近似或本工程字段冲突，需人工确认 |


另可在 finding 上使用 `severity`：`info` / `warning` / `error`。

### 重点规则（有数据才判；无规则则跳过并声明）

1. 必需文件是否存在（名称/别名/分类命中）。
2. 文件类型是否与当前 `project_type` 匹配。
3. 项目名称、项目编号跨文件是否一致。
4. 日期是否符合常理流程（如开工 ≤ 竣工；验收类日期不早于不合理的开工前——仅在日期可解析时检查）。
5. 竣工验收报告类是否有可对应的施工/监理/设计侧支撑文件（按规则模板 notes 与类别存在性，不做无依据的深度内容鉴定）。
6. 检测报告是否能指向材料或分部（有编号/部位字段才判）。
7. 竣工图是否覆盖设计变更（仅当变更记录与图纸目录均被识别时尝试；否则 `needs_human_review`）。
8. 是否混入其他项目（项目名/编号明显不同）。

近似文件（如「预验收」vs「竣工验收」）：可列入 `similar_files`，**默认不能替代**正式项，除非规则 `notes` 明确允许。

## 5. 证据报告层

写入 `_work/audit-report.md`（给人看）与机器可读 findings。  
**禁止**只写「缺少某某文件」。每条问题按下列结构：

```markdown
### [E-01] 缺少《工程竣工验收报告》
- **状态**: missing
- **依据**: 当前规则模板「房屋建筑工程」E-01，要求 1 份（required=true）
- **已检索文件**: 共 N 份（见 inventory）
- **相似文件**: 工程竣工预验收报告.pdf
- **判断**: 预验收报告不能替代正式竣工验收报告
- **建议**: 补充正式《工程竣工验收报告》
- **证据**: （文件名/标题摘录/字段）
```

报告首页还需：

- 工程标识（名称/编号，来自共识或 manifest）
- 所用规则模板文件名与 `project_type`
- 完整性核查统计：已提供 / 缺失 / 错传或重复 / 需复核
- 一致性摘要：本工程字段冲突条数（错传他项已排除）
- 明确声明：本包为用户提供或合成演示数据

## 产物清单（一次核查至少写出）


| 文件                           | 内容      |
| ---------------------------- | ------- |
| `_work/inventory.json`       | 接收清单    |
| `_work/classification.json`  | 分类结果    |
| `_work/fields.json`          | 分文件字段   |
| `_work/field_consensus.json` | 共识与冲突   |
| `_work/findings.json`        | 结构化核查结论 |
| `_work/audit-report.md`      | 证据链报告   |


`_work/audit-brief.md`：核查抽查用精简摘要。文书执笔请读 `engineering-doc-generator` prepare 生成的 `agent-brief.md`。

## 执行方式

1. **脚本**：清单匹配、PDF 文本层抽字段、冲突/缺件/错传/重复初判（确定性）。
2. **Agent**：只处理 brief 中的疑点与润色，不重跑全量抽取。
3. 字段锚优先 `manifest` / 合同 / 验收类文件；完整性状态仅用 provided / missing / suspect_duplicate_or_misfiled / needs_human_review。

不使用 Workflow 编排。

## 异常与边界

- 无文件：停止并请用户指定 `cases/<id>`。
- 扫描件无法读字：分类/字段标 low，finding 用 `needs_human_review`，建议补可检索 PDF 或 OCR 文本层。
- 规则与地方目录不一致：以**当前加载 JSON**为准，在报告中提示「实际归档以建设单位/当地要求为准，规则可替换」。
- 隐私：不把身份证号、手机号、完整签名图片写入报告正文；需要提及签署时写「已见××签署栏」即可。

## 完成后如何交给文书 Skill

使用 **engineering-doc-generator** 生成《竣工资料完整性与一致性核查情况说明》：

```bash
cd .agh/skills/engineering-doc-generator
node scripts/generate.js prepare --case ../../../cases/<id>
# 按 outline.md：工程概况 → 完整性 → 一致性 → 问题与证据 → 处理意见 → 结论
# 撰写 ../../../cases/<id>/_work/正文.md
node scripts/generate.js build --case ../../../cases/<id> --out ../../../生成结果
```

