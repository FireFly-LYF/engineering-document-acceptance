# Engineering Document Acceptance

基于 **Agnes Harness（AGH）+ Skill** 的房屋建筑工程竣工资料智能核查与情况说明生成演示项目。

面向「建设工程竣工资料完整性与一致性核查」：对照可配置归档清单做齐套/错传/冲突/重复判定，并生成正式《核查情况说明》Word。确定性步骤由本地脚本完成，Agent 阅读 Skill 与简报做抽查、润色与执笔。

> 演示数据均为**合成材料**，规则参考政府部门公开的归档目录与验收空白表结构，**不含真实工程档案与个人隐私**。

完整「证据库 / 流水线 / Agnes API」系统实现已存档在分支 `[system](https://github.com/FireFly-LYF/engineering-document-acceptance/tree/system)`（对应 v1.0.x）。`**main` 仅保留 Skill + 脚本**，供 Agnes 在 AGH 会话中阅读并完成规则匹配与文书生成。

## 功能概览


| 能力       | Skill                       | 说明                                         |
| -------- | --------------------------- | ------------------------------------------ |
| 齐套与一致性核查 | `engineering-archive-audit` | 清单匹配、字段抽取初稿、缺失/错传/冲突/重复判定                  |
| 情况说明文书生成 | `engineering-doc-generator` | `prepare` → Agent 写正文 → `build` 导出 `.docx` |


不使用 Workflow 编排；不依赖第三方业务模型 API。AGH 会话中应使用 **Agnes** 模型阅读本仓库 Skills。

## 目录结构

```text
engineering-document-acceptance/
├── .agh/skills/
│   ├── engineering-archive-audit/     # 核查 Skill + rules + audit_prepare.py
│   └── engineering-doc-generator/     # 文书 Skill + generate.js（prepare/build）
├── cases/demo-housing-mixed/          # 基础演示：远域错传 / 编号金额冲突 / 重复件
├── cases/demo-housing-near-miss/      # 对照包：近邻混淆 / 开工日期冲突 / 缺检测 / 不可读页
├── reference/public-pdfs/             # 公开目录索引与少量已入库参考 PDF
├── tools/                             # 造数与拉取公开 PDF 的开发脚本
└── README.md
```

演示包 PDF 若缺失，在本地生成：

```bash
python tools/generate_demo_case.py
python tools/generate_near_miss_case.py
python tools/fetch_public_pdfs.py
```

合成 PDF 版式仿公开空白表/国标附录（见 `reference/public-pdfs/` 与 `tools/pdf_forms.py`）：检验批/分项/分部/观感对齐 GB50300-2013 附录 E–H；许可、合同、报告类用双框封面+著录表+签章栏。内容仍为合成填写，**不是**真实工程档案扫描件。

## 环境要求

- [Agnes Harness](https://agnes-ai.cn/) 可运行（Web / CLI）
- Python 3 + `pymupdf`（核查脚本读 PDF 文本层）
- Node.js（文书 `docx` 导出；首次在文书 Skill 目录执行 `npm install`）

```bash
pip install pymupdf
cd .agh/skills/engineering-doc-generator && npm install
```

## 在 AGH 中使用

1. 启动 AGH，将本仓库根目录添加为工作区。
2. Skills 管理中刷新并启用：
  - `engineering-archive-audit`
  - `engineering-doc-generator`
3. 新建会话，可用如下任务描述：

```text
请使用 engineering-archive-audit 对 cases/demo-housing-mixed 做竣工资料齐套与一致性核查；脚本能做的步骤优先用脚本，不要通读全部 PDF。

核查完成后，使用 engineering-doc-generator 生成《竣工资料核查情况说明》并导出 Word。

结论需覆盖：缺失项、错传、字段冲突、重复件。
```

也可直接复制 `cases/demo-housing-mixed/TEST_PROMPT.txt` 或 `cases/demo-housing-near-miss/TEST_PROMPT.txt`。

### 脚本优先（Skill 内约定）

核查（工作区根目录）：

```bash
python .agh/skills/engineering-archive-audit/scripts/audit_prepare.py --case cases/demo-housing-mixed
python .agh/skills/engineering-archive-audit/scripts/audit_prepare.py --case cases/demo-housing-near-miss
```

文书：

```bash
cd .agh/skills/engineering-doc-generator
node scripts/generate.js prepare --case ../../../cases/demo-housing-mixed
# Agent 撰写 cases/.../_work/正文.md 后：
node scripts/generate.js build --case ../../../cases/demo-housing-mixed --out ../../../生成结果
```

## 演示包考点（`demo-housing-mixed`）

合成项目「云港新区示范中学教学楼改扩建工程」，约 24 份 PDF，刻意包含：

- 缺失正式《工程竣工验收报告》（仅有预验收）与消防验收类材料
- 他项工程错传文件
- 项目编号 / 合同金额跨文件冲突
- 检验批记录重复（同文件编号）

对照预期见 `cases/demo-housing-mixed/ground_truth.json`。

## 对照包考点（`demo-housing-near-miss`）

合成项目「云港新区示范中学实验楼加固改造工程」，与 mixed 区分考点：

- 近邻混淆：同校区教学楼合同、同学府路小学正式验收混入正常目录（无「错传」路径）
- 缺失材料检测 D-01、正式竣工验收 E-01、消防 G-01
- 本工程开工日期冲突（施工许可 vs manifest）
- 无文本层不可读扫描页 → `needs_human_review`

对照预期见 `cases/demo-housing-near-miss/ground_truth.json`。

## 规则模板

`engineering-archive-audit/rules/` 下 JSON 可配置，默认 `housing-construction.json`（房屋建筑）。道路/桥梁、市政管线为占位清单，可按公开目录替换，避免写死单一地市全文。

公开参考 PDF 索引：`reference/public-pdfs/SOURCES.txt`。

## 开发辅助脚本（`tools/`）


| 脚本                           | 用途                              |
| ---------------------------- | ------------------------------- |
| `generate_demo_case.py`      | 重新生成 `demo-housing-mixed`       |
| `generate_near_miss_case.py` | 重新生成 `demo-housing-near-miss`   |
| `fetch_public_pdfs.py`       | 拉取公开归档指南/目录类 PDF 到 `reference/` |


## 说明与边界

- 本仓库 `main` 为 AGH Skill 演示工作区，**不是** Agnes Harness 源码本身，也不是完整核查系统服务。
- 归档要求因地区、工程类型、建设单位而异；以可配置规则为准。
- 脚本初稿结论供 Agent 抽查润色；正式行政验收效力以主管部门规定为准。

## License

演示与学习用途。公开参考文件版权归原发布单位；合成数据可自由用于复现实验。