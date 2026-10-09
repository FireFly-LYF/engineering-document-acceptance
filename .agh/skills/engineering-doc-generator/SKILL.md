---
name: engineering-doc-generator
description: 根据已核查事实和证据生成工程竣工资料情况说明，校验统计后导出 Word。
---

# 工程资料情况说明

先运行核查核心。读取 `_work/audit-result.json`、`statement-facts.json`、`evidence-index.json` 与简报，保持项目、数量、金额、日期、规则适用性和问题方向一致。

```powershell
node .agh/skills/engineering-doc-generator/scripts/generate.js prepare --case cases/<id>
node .agh/skills/engineering-doc-generator/scripts/generate.js build --case cases/<id> --out 生成结果
```

正文已有事实骨架，允许依据证据润色；不删除固定统计句以绕过校验。build 会重新检查数量、占位符、路径、密钥和无依据的全量通过。加粗与有序列表转换为 Word 格式。

每项问题表述区分缺件、读取不足、错传、主体字段冲突、合法变更、重复和版本差异。缺失文件不能列为实际附件；正文只用资料短名称，不写目录或磁盘路径。

不认定工程实体质量合格、签名印章真实或行政验收有效。地方目录或应交范围未知时保留限定，不写全部齐套。生成后须渲染检查页面；修改正文后重跑 build 和版面验证，保持历史运行产物。
