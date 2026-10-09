---
version: '1.1.0'
profile_id: housing-core
tags_config: ../config/document_tags.yaml
labels_config: ../config/field_definitions.yaml
bindings_config: ../config/tag_label_bindings.yaml
rules_config: ../config/rules/housing-core.yaml
audit_scope: 资料类型和文载一致性核查
normative_status: draft_localizable
---

# 房屋建筑工程资料核查参考

这是工程核查的给定参考入口。Python 读取 frontmatter 中明确指定的字典、字段绑定与规则；四个 YAML 是可维护的唯一配置来源，不由模型自行创造 tag 或 label。地区和应交范围未确认时，不能把本参考称为完整法定归档目录。

## 项目上下文

调用方需提供项目名称、项目编号及其来源、审查阶段、地区、单位工程范围、是否委托监理、建筑使用性质、消防类别及其确认依据、是否被抽查。还需确认本参考验收规定适用范围 `regulatory_scope=general_civil` 和消防规定是否适用 `fire_regulation_applicable`。条件缺失采用 unknown，不自动按不适用处理。

## 分类和字段约束

- tag 表示一份逻辑资料的类型，不表示整个上传文件的格式、施工阶段、项目归属或核查结果。
- 一个合订 PDF 可以拆出多份逻辑资料，每份资料有一个主 tag；不清楚时使用 UNKNOWN 并复核。
- 上传 tag 仅为 proposed。核查标题和内容后 verified 才能用于清单通过。
- label 表示业务含义，中文显示名可修改，英文 semantic key 保持稳定。
- tag-label 绑定决定允许提取哪些字段，不代表文件依法必须印有所有字段。
- 原始合同额、变更后金额、结算金额分别抽取；实际开工、完工、验收和出具日期分别抽取。

## 统一 MarkdownUnit 契约

严格参考旧项目 `docs/unified_markdown_field_extraction_migration.md` 的统一表示，扫描件经识别后也进入同一结构，模型候选只从该表示中定位。

```json
{
  "document_unit_id": "doc_001",
  "file_id": "file_001",
  "file_name": "01-准备/施工合同.pdf",
  "unit_no": 1,
  "page_no": 3,
  "logical_locator": null,
  "source_type": "native_pdf",
  "markdown": "## 合同价格\n合同金额：8650万元",
  "plain_text": "合同价格\n合同金额：8650万元",
  "fragments": [
    {"fragment_id": "u001_f0001", "text": "合同金额：8650万元", "bbox": [45,110,310,132], "source": "native_pdf", "table_id": null, "row_index": null, "column_index": null}
  ]
}
```

产物保留 `markdown/<file_id>/unit_001.md` 和 `unit_001.source_map.json`。Word 与 Excel 的物理页码为 null，使用段落、表格、worksheet 和单元格逻辑定位。拆分文档与阅读单元的关联单独保存，不能认为一页一定是一份文件。

## 核查顺序

1. 登记原始文件的路径和 SHA-256，按页原生读取或识别，保存读取覆盖范围。
2. 形成统一 Markdown 和 source map；确认逻辑文档 tag。
3. 按显式 tag-label 绑定提取候选，保留所有来源与主体/引用角色。
4. 比较锚值只用于参考搜索；命中不能锁死异常发现，也不能改写文档实际值。
5. Agnes 返回 value、source_label、unit_no、page、evidence、confidence；Python 核验定位、类型和单位。
6. 先判断项目归属，再做清单、覆盖、文载一致性、日期和重复/版本核查。
7. 配置条件不明或证据不足时 needs_review/not_evaluated，不输出无条件通过。
8. 保存候选、规则结果、正负证据、复核记录，生成情况说明。

## 判定边界

模型不直接决定合法有效、工程质量合格或全量齐套。消防类别需确认后选择验收或备案分支，申请表不等于办结凭证。文载结论、可见签署栏、印章观察分别记录，不推断真实性。范围级齐套必须有已确认的应交范围计划。
