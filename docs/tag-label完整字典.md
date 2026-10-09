# 工程竣工核查 tag 与 label 完整字典

本文件由 `tools/export_catalog.py` 从配置生成。维护 YAML 后重新生成，不在本文件修改字段定义。

## 资料类型 tag

| code | 中文名称 | 阶段 |
|---|---|---|
| PLANNING_PERMIT | 建设工程规划许可证 | preparation |
| CONSTRUCTION_PERMIT | 建筑工程施工许可证 | preparation |
| DRAWING_REVIEW | 施工图设计文件审查意见 | preparation |
| CONSTRUCTION_CONTRACT | 施工合同 | preparation |
| SUPERVISION_CONTRACT | 监理合同 | preparation |
| SUPERVISION_PLAN | 监理规划 | supervision |
| SUPERVISION_DETAIL | 监理实施细则 | supervision |
| SUPERVISION_QUALITY_REPORT | 监理工程质量评估报告 | supervision |
| CONSTRUCTION_PLAN | 施工组织设计 | construction |
| INSPECTION_BATCH | 检验批质量验收记录 | construction |
| SUBITEM_ACCEPTANCE | 分项工程质量验收记录 | construction |
| DIVISION_ACCEPTANCE | 分部工程质量验收记录 | construction |
| HIDDEN_WORK | 隐蔽工程验收记录 | construction |
| DESIGN_CHANGE | 设计变更通知 | construction |
| MATERIAL_TEST | 材料进场及复试报告 | testing |
| FUNCTIONAL_TEST | 安全及使用功能检测资料 | testing |
| CONSTRUCTION_COMPLETION_REPORT | 施工单位工程竣工报告 | acceptance |
| SURVEY_QUALITY_REPORT | 勘察单位质量检查报告 | acceptance |
| DESIGN_QUALITY_REPORT | 设计单位质量检查报告 | acceptance |
| PRE_ACCEPTANCE_REPORT | 工程竣工预验收报告 | acceptance |
| COMPLETION_ACCEPTANCE_REPORT | 建设单位工程竣工验收报告 | acceptance |
| UNIT_QUALITY_ACCEPTANCE | 单位工程质量竣工验收记录 | acceptance |
| APPEARANCE_CHECK | 单位工程观感质量检查记录 | acceptance |
| HOUSEHOLD_ACCEPTANCE | 住宅工程质量分户验收表 | acceptance |
| QUALITY_WARRANTY | 工程质量保修书 | acceptance |
| AS_BUILT_DRAWING | 竣工图 | drawing |
| FIRE_ACCEPTANCE_OPINION | 特殊建设工程消防验收意见 | special |
| FIRE_FILING_RECEIPT | 其他建设工程消防验收备案凭证 | special |
| FIRE_SPOTCHECK_RESULT | 消防验收备案抽查结果 | special |
| PLANNING_VERIFICATION | 规划核实文件 | special |
| COMPLETION_FILING_RECEIPT | 竣工验收备案资料 | filing |
| ARCHIVE_HANDOVER_RECEIPT | 工程档案移交凭证 | archive |
| DOCUMENT_CATALOG | 资料或图纸目录 | archive |
| UNKNOWN | 未确认资料类型 | unknown |

## 可维护 label

| semantic key | 中文名称 | 类型 | 比较策略 | 比较范围 |
|---|---|---|---|---|
| project_name | 项目名称 | text | normalized_exact | project |
| project_code | 项目编号 | identifier | normalized_exact | project |
| owner | 建设单位 | organization | normalized_exact | project |
| contractor | 施工单位 | organization | normalized_exact | contract |
| supervisor | 监理单位 | organization | normalized_exact | project |
| designer | 设计单位 | organization | normalized_exact | discipline |
| surveyor | 勘察单位 | organization | normalized_exact | project |
| address | 工程地址 | text | normalized_exact | project |
| unit_name | 单位工程名称 | text | normalized_exact | unit |
| discipline | 专业 | text | normalized_exact | unit |
| location | 工程部位 | text | normalized_exact | location |
| document_no | 文件编号 | identifier | normalized_exact | document |
| contract_no | 合同编号 | identifier | normalized_exact | contract |
| permit_no | 许可证号 | identifier | normalized_exact | tag |
| contract_amount | 合同金额 | money | decimal_exact | contract |
| revised_contract_amount | 变更后合同金额 | money | decimal_exact | contract_version |
| settlement_amount | 结算金额 | money | decimal_exact | contract |
| start_date | 实际开工日期 | date | date_exact | unit |
| finish_date | 实际竣工日期 | date | date_exact | unit |
| acceptance_date | 验收日期 | date | date_exact | event |
| issue_date | 文件出具日期 | date | date_exact | document |
| test_date | 检测日期 | date | date_exact | sample |
| sample_no | 样品或批次编号 | identifier | normalized_exact | sample |
| material_name | 材料名称 | text | normalized_exact | sample |
| specification | 规格型号 | text | normalized_exact | sample |
| conclusion | 文载结论 | text | none | document |
| drawing_no | 图号 | identifier | normalized_exact | drawing |
| revision | 版本号 | identifier | normalized_exact | document |
| change_no | 设计变更编号 | identifier | normalized_exact | change |
| building_area | 建筑面积 | area | decimal_exact | unit_stage |
| building_height | 建筑高度 | length | decimal_exact | unit |
| fire_receipt_no | 消防文书编号 | identifier | normalized_exact | tag |
| signature_observation | 签署栏观察 | text | none | document |
| seal_observation | 印章观察 | text | none | document |

## 每类资料的完整字段绑定

绑定表示有则提取，不是法定必填字段。UNKNOWN 的基础字段用于归属调查，不可直接判清单通过。

| tag | label semantic keys |
|---|---|
| PLANNING_PERMIT | project_name, project_code, owner, address, document_no, issue_date, unit_name, revision, permit_no, building_area, building_height |
| CONSTRUCTION_PERMIT | project_name, project_code, owner, address, document_no, issue_date, unit_name, revision, permit_no, contractor, supervisor, start_date |
| DRAWING_REVIEW | project_name, project_code, owner, address, document_no, issue_date, unit_name, revision, designer, surveyor, discipline, drawing_no, conclusion |
| CONSTRUCTION_CONTRACT | project_name, project_code, owner, address, document_no, issue_date, unit_name, revision, contract_no, contractor, contract_amount, revised_contract_amount, settlement_amount |
| SUPERVISION_CONTRACT | project_name, project_code, owner, address, document_no, issue_date, unit_name, revision, contract_no, supervisor |
| SUPERVISION_PLAN | project_name, project_code, owner, address, document_no, issue_date, unit_name, revision, supervisor, start_date, finish_date |
| SUPERVISION_DETAIL | project_name, project_code, owner, address, document_no, issue_date, unit_name, revision, supervisor, discipline |
| SUPERVISION_QUALITY_REPORT | project_name, project_code, owner, address, document_no, issue_date, unit_name, revision, supervisor, contractor, designer, start_date, finish_date, conclusion, signature_observation |
| CONSTRUCTION_PLAN | project_name, project_code, owner, address, document_no, issue_date, unit_name, revision, contractor, discipline, start_date, finish_date |
| INSPECTION_BATCH | project_name, project_code, owner, address, document_no, issue_date, unit_name, revision, contractor, supervisor, discipline, location, acceptance_date, sample_no, conclusion |
| SUBITEM_ACCEPTANCE | project_name, project_code, owner, address, document_no, issue_date, unit_name, revision, contractor, supervisor, discipline, location, acceptance_date, conclusion |
| DIVISION_ACCEPTANCE | project_name, project_code, owner, address, document_no, issue_date, unit_name, revision, contractor, supervisor, discipline, location, acceptance_date, conclusion |
| HIDDEN_WORK | project_name, project_code, owner, address, document_no, issue_date, unit_name, revision, contractor, supervisor, discipline, location, acceptance_date, conclusion |
| DESIGN_CHANGE | project_name, project_code, owner, address, document_no, issue_date, unit_name, revision, designer, discipline, location, change_no, drawing_no, revised_contract_amount |
| MATERIAL_TEST | project_name, project_code, owner, address, document_no, issue_date, unit_name, revision, contractor, location, sample_no, material_name, specification, test_date, conclusion |
| FUNCTIONAL_TEST | project_name, project_code, owner, address, document_no, issue_date, unit_name, revision, contractor, discipline, location, test_date, conclusion |
| CONSTRUCTION_COMPLETION_REPORT | project_name, project_code, owner, address, document_no, issue_date, unit_name, revision, contractor, supervisor, contract_no, contract_amount, start_date, finish_date, conclusion, signature_observation |
| SURVEY_QUALITY_REPORT | project_name, project_code, owner, address, document_no, issue_date, unit_name, revision, surveyor, conclusion, signature_observation |
| DESIGN_QUALITY_REPORT | project_name, project_code, owner, address, document_no, issue_date, unit_name, revision, designer, discipline, change_no, conclusion, signature_observation |
| PRE_ACCEPTANCE_REPORT | project_name, project_code, owner, address, document_no, issue_date, unit_name, revision, contractor, supervisor, designer, surveyor, acceptance_date, conclusion |
| COMPLETION_ACCEPTANCE_REPORT | project_name, project_code, owner, address, document_no, issue_date, unit_name, revision, contractor, supervisor, designer, surveyor, start_date, finish_date, acceptance_date, conclusion, signature_observation |
| UNIT_QUALITY_ACCEPTANCE | project_name, project_code, owner, address, document_no, issue_date, unit_name, revision, contractor, supervisor, designer, surveyor, acceptance_date, conclusion, signature_observation |
| APPEARANCE_CHECK | project_name, project_code, owner, address, document_no, issue_date, unit_name, revision, contractor, supervisor, acceptance_date, conclusion |
| HOUSEHOLD_ACCEPTANCE | project_name, project_code, owner, address, document_no, issue_date, unit_name, revision, contractor, supervisor, location, acceptance_date, conclusion |
| QUALITY_WARRANTY | project_name, project_code, owner, address, document_no, issue_date, unit_name, revision, contractor, finish_date, signature_observation |
| AS_BUILT_DRAWING | project_name, project_code, owner, address, document_no, issue_date, unit_name, revision, designer, discipline, drawing_no, change_no, seal_observation |
| FIRE_ACCEPTANCE_OPINION | project_name, project_code, owner, address, document_no, issue_date, unit_name, revision, fire_receipt_no, building_area, building_height, acceptance_date, conclusion |
| FIRE_FILING_RECEIPT | project_name, project_code, owner, address, document_no, issue_date, unit_name, revision, fire_receipt_no, building_area, building_height, conclusion |
| FIRE_SPOTCHECK_RESULT | project_name, project_code, owner, address, document_no, issue_date, unit_name, revision, fire_receipt_no, acceptance_date, conclusion |
| PLANNING_VERIFICATION | project_name, project_code, owner, address, document_no, issue_date, unit_name, revision, permit_no, building_area, conclusion |
| COMPLETION_FILING_RECEIPT | project_name, project_code, owner, address, document_no, issue_date, unit_name, revision, acceptance_date, conclusion |
| ARCHIVE_HANDOVER_RECEIPT | project_name, project_code, owner, address, document_no, issue_date, unit_name, revision, conclusion |
| DOCUMENT_CATALOG | project_name, project_code, owner, address, document_no, issue_date, unit_name, revision, discipline, drawing_no, change_no |
| UNKNOWN | project_name, project_code, owner, address, document_no, issue_date, unit_name, revision |
