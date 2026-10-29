# 工程文件核查（Engineering Document Acceptance）

[English](README.md) | 简体中文

基于 **[Agnes Harness（AGH）](https://github.com/AgnesAI-Labs/agnes-harness) + Skill** 的工程文件智能核查与情况说明生成项目。

对上传材料进行解析，根据可配置的文件列表和字段列表检验材料齐全 / 错传 / 冲突 / 重复，并由 Agent 生成正式《核查情况说明》Word。

> **演示数据均为合成材料**，规则参考政府部门公开文件，**不含真实项目内容。**

目录

- [1. 项目介绍](#1-项目介绍project-overview)
- [2. 视频介绍](#2-视频介绍demo-video)
- [3. 架构介绍](#3-架构介绍architecture)
- [4. 集成标准](#4-集成标准integration-standards)
- [环境配置与运行](#环境配置与运行)
- [说明与边界](#说明与边界)
- [来源与授权](#来源与授权)

---

## 1. 项目介绍（Project Overview）

### 项目背景

建设工程验收前，建设单位与档案管理部门需要对资料做完整性与一致性核查：对照可配置清单核对缺失文件，识别其他工程错传、跨文件字段冲突与重复文件，并形成情况说明文件。

传统人工核验依赖经验、耗时长，且各地归档目录与工程类型差异大，难以用单一规则覆盖。

本项目将这一现场验收流程自动化：把清单匹配、字段抽取、冲突判定做成确定性脚本，把情况说明执笔交给 Agent Skill，形成可复现、可配置、可审计的演示与交付形态。

### 核心功能


| 能力         | Skill / 模块                  | 说明                                                     |
| ---------- | --------------------------- | ------------------------------------------------------ |
| 材料齐全与一致性核查 | `engineering-archive-audit` | 对照规则模板做清单匹配、字段抽取初稿、缺失 / 错传 / 冲突 / 重复判定，输出证据链报告         |
| 情况说明文书生成   | `engineering-doc-generator` | `prepare` → Agent 撰写正文 → `build` 导出《工程文件核查情况说明》`.docx` |
| 前端界面       | `web/` + `server/`          | 按工程批次上传材料、指定主参考文件、一键发起 AGH 核查、查看结论并下载说明 Word           |
| 多工程类型规则    | `rules/*.json`              | 房屋建筑、道路 / 桥梁、市政管线；可新增或修改规则                             |


内置三类房屋建筑演示demo，便于对照验收能力：

- `demo-housing-mixed`：存在错传、编号 / 金额冲突、重复件、缺正式验收与消防材料
- `demo-housing-near-miss`：存在开工日期冲突、缺检测、不可读扫描页
- `demo-housing-complete`：材料齐全且字段一致（正确对照）

### 创新亮点

1. **脚本优先**：清单匹配、PDF 文本层抽字段、冲突 / 缺件初判由确定性脚本完成；Agent 只读 brief 做检查与文书生成，降低 token、缩短耗时、提高结果稳定性。
2. **规则可配置**：`rules/*.json` 四段结构可按地区与工程类型替换；
3. **主参考锚定** ：以施工许可证等主参考文件写入工程身份字段，跨文件一致性有明确对比值；主参考文件可修改或自动选择；
4. **结果追溯**每条 finding 带清单编号、相似文件、判断依据与证据摘录，可导出正式 Word 情况说明。
5. **Agnes Harness 底座**：完全以 AGH + Skill完成；Web 工作台经本地 API 发起 Agent对话，过程可在 AGH Trace / 会话页回放。

---

## 2. 视频介绍（Demo Video）

演示视频：**工程文件核查.mp4**

- 网盘链接：[https://pan.baidu.com/s/1X4Yt7zPsa0dvkiozLd251A?pwd=0000](https://pan.baidu.com/s/1X4Yt7zPsa0dvkiozLd251A?pwd=0000)
- 提取码：`0000`

---

## 3. 架构介绍（Architecture）

### 总体架构

```text
┌─────────────────────────────────────────────────────────────┐
│  Web 核查台 (Vite + React, :5173)                            │
│  上传 / 主参考指定 / 发起核查 / 结果展示 / 下载说明 Word        │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTP /api/*
┌────────────────────────────▼────────────────────────────────┐
│  本地 API (Express, :8787)                                   │
│  cases 落盘 · 文件管理 · 启动/取消 AGH · findings / statement │
└────────────────────────────┬────────────────────────────────┘
                             │ CLI / 会话
┌────────────────────────────▼────────────────────────────────┐
│  Agnes Harness Agent (:4177 Web)                             │
│  阅读 Skills → 跑确定性脚本 → 抽查润色 → 文书执笔             │
└───────┬───────────────────────────────┬─────────────────────┘
        │                               │
        ▼                               ▼
 engineering-archive-audit      engineering-doc-generator
 audit_prepare.py               generate.js prepare / build
 rules/*.json                   正文.md → .docx
        │                               │
        └──────────► cases/<id>/ ◄──────┘
                     files/  manifest.json  _work/  doc/
```

### 核心模块


| 模块       | 路径                                       | 职责                                                                                                 |
| -------- | ---------------------------------------- | -------------------------------------------------------------------------------------------------- |
| 核查 Skill | `.agh/skills/engineering-archive-audit/` | 定义核查流程；`scripts/audit_prepare.py` 产出 inventory / classification / fields / findings / audit-report |
| 文书 Skill | `.agh/skills/engineering-doc-generator/` | `prepare` 生成 facts / outline / agent-brief；Agent 写 `正文.md`；`build` 排版导出 Word                       |
| 规则模板     | `rules/housing-construction.json` 等      | 必需资料清单、主参考定义、字段一致性规则（R-001 / R-002 / R-003）                                                        |
| 本地 API   | `server/`                                | 工程批次 CRUD、上传、主参考、触发 AGH 核查、读取 findings 与说明 Word                                                    |
| 前端界面     | `web/`                                   | 用户 → 工程批次交互；`/api` 代理到 8787                                                                        |
| 演示与参考    | `cases/`、`reference/`、`tools/`           | 合成演示包、公开目录索引、造数与拉取脚本                                                                               |


### 实现方式（核查流水线）

1. **文件接收**：将`cases/<id>/files/`或自行上传的文件夹中文件写入 `_work/inventory.json`。
2. **文档分类**：综合文件名别名、标题关键词与规则 `category`，写入 `classification.json`。
3. **主参考选择**：用户指定或脚本自动选中（如建筑工程施工许可证）；无主参考则结束核查并标注 `needs_human_review`。
4. **字段抽取**：PDF 文本层逐页抽取；按 `global` / `scoped` 做跨文件一致性比较。未来可接入OCR实现扫描件文本提取。
5. **完整性与一致性判定**：对照 `required_documents` ，对每个文件输出 provided / missing / suspect_duplicate_or_misfiled / needs_human_review；错传文件不计入已提供、不参与本工程字段冲突。
6. **Agent 文书生成**：阅读 `audit-brief.md` / findings 润色报告；文书 Skill 生成正式情况说明 Word。

---

## 4. 集成标准（Integration Standards）

### 目录约定


| 路径                           | 约定                                              |
| ---------------------------- | ----------------------------------------------- |
| `cases/<id>/manifest.json`   | 工程元数据、`project_type` / `rules_profile`、主参考、字段锚值 |
| `cases/<id>/files/`          | 用户材料（只读于核查过程）                                   |
| `cases/<id>/_work/`          | 脚本与 Agent 可写产物（findings、报告、正文等）                 |
| `cases/<id>/doc/`            | 导出的情况说明 `.docx`                                 |
| `.agh/skills/*/rules/*.json` | 归档规则模板（可按现场替换）                                  |


### 规则模板接口

每个 `rules/*.json` **必须**包含：


| 键                    | 含义                                                  |
| -------------------- | --------------------------------------------------- |
| `manifest_fields`    | 参与一致性比较的结构化字段（含 `consistency`: `global`             |
| `primary_reference`  | 主参考文件定义（`code` / `name` / `aliases`）                |
| `required_documents` | 必需资料清单（完整性匹配）                                       |
| `consistency_rules`  | 至少含 R-001（字段适用范围）、R-002（与 manifest 一致）、R-003（跨文件互比） |


完整性条目状态机：`provided` | `missing` | `suspect_duplicate_or_misfiled` | `needs_human_review`。

### 本地 HTTP API

默认端口：`8787`。前端通过 Vite 将 `/api` 代理至此。


| 方法                | 路径                                  | 说明                           |
| ----------------- | ----------------------------------- | ---------------------------- |
| `GET`             | `/api/health`                       | 健康检查与 AGH 配置摘要               |
| `GET`             | `/api/config`                       | AGH CLI / Web Origin / 工作区路径 |
| `POST`            | `/api/cases`                        | 创建工程批次（需工程身份）                |
| `GET/PATCH`       | `/api/cases/:id`…                   | 读取 / 更新 manifest、主参考         |
| `GET/POST/DELETE` | `/api/cases/:id/files`…             | 列表、上传、重命名、移动、删除              |
| `POST`            | `/api/cases/:id/audit`              | 启动 AGH 核查会话                  |
| `GET`             | `/api/cases/:id/audit/status`       | 核查进程状态                       |
| `POST`            | `/api/cases/:id/audit/cancel`       | 取消核查                         |
| `GET`             | `/api/cases/:id/findings`           | 结构化结论（含 AGH 会话链接）            |
| `GET`             | `/api/cases/:id/audit-detail`       | 字段 / 共识 / 证据明细               |
| `GET`             | `/api/cases/:id/statement`          | 情况说明生成状态                     |
| `GET`             | `/api/cases/:id/statement/download` | 下载 `.docx`                   |


上传限制（默认）：单文件 ≤ 80MB，单次最多 200 个文件。路径均相对 `cases/<id>/files/`。

### 确定性脚本 CLI

以下路径相对于 `engineering-document-acceptance/`（AGH 工作区）：

```bash
# 核查准备（EDA 工作区根目录）
python .agh/skills/engineering-archive-audit/scripts/audit_prepare.py --case cases/demo-housing-mixed

# 文书（在文书 Skill 目录）
cd .agh/skills/engineering-doc-generator
node scripts/generate.js prepare --case ../../../cases/demo-housing-mixed
# Agent 撰写 cases/.../_work/正文.md 后：
node scripts/generate.js build --case ../../../cases/demo-housing-mixed
```

### 技术标准与参考依据

- 住房城乡建设部《建设工程文件归档规范》及相关地方「归档目录 / 办事指南 / 空白样表」作为规则模板来源说明；**具体项目以当前加载的 JSON 清单为准**。
- 演示合成版式参考公开证照 / 合同示范文本 / GB 50300 附录表等（见 `reference/*/SOURCES.txt`）。
- 正式行政验收效力以主管部门规定为准；本项目输出为辅助核查，不替代真实验收结论。

---

## 环境配置与运行

### 安装

项目代码在 `engineering-document-acceptance/`；本 monorepo 内 AGH 源码为同级目录 `agnes-harness/`。

1. 准备环境：Node.js、Python 3。
2. 构建 AGH 本地 CLI（在 `agnes-harness` 目录）：

```bash
pnpm install --frozen-lockfile
pnpm --filter @agnes/cli build:local
```

3. 安装 EDA 依赖（在 monorepo 根目录）：

```bash
pip install pymupdf
cd engineering-document-acceptance/.agh/skills/engineering-doc-generator && npm install
cd ../../../server && npm install
cd ../web && npm install
```

或执行 monorepo 根目录 `.\setup.ps1`，一次完成 AGH 构建与 EDA 依赖安装。Monorepo 布局说明见 [`docs/README.md`](docs/README.md)。

### 一键启动

```powershell
# 在 monorepo 根目录
.\start.ps1
# 或：cd engineering-document-acceptance; .\start-dev.ps1
```

浏览器打开终端提示地址（一般为 `http://127.0.0.1:5173`）。将同时拉起 API（8787）、前端（5173）与 AGH Web（4177）。

### 分步启动

```bash
# 1) API
cd engineering-document-acceptance/server && npm run dev

# 2) 前端
cd engineering-document-acceptance/web && npm run dev

# 3) AGH（工作区必须指向 EDA 目录）
node agnes-harness/packages/cli/dist/local/agnes.mjs serve --cwd <engineering-document-acceptance 绝对路径>
```

### 接入与使用

1. 将 `engineering-document-acceptance` 目录添加为 AGH **工作区**（`--cwd` 指向该目录，与 API 启动 AGH 时一致）。
2. 在 Skills 管理中刷新并启用：
  - `engineering-archive-audit`
  - `engineering-doc-generator`
3. 新建会话，按 case 下 `TEST_PROMPT.txt` 或下列任务描述执行：

```text
请使用 engineering-archive-audit 对 cases/demo-housing-mixed 做竣工资料材料齐全与一致性核查；
脚本能做的步骤优先用脚本，不要通读全部 PDF。

核查完成后，使用 engineering-doc-generator 生成《竣工资料核查情况说明》并导出 Word。

结论需覆盖：缺失项、错传、字段冲突、重复件。
```

也可通过 Web 工作台点击「核查」：API 调用本机 AGH CLI 启动会话，前端可跳转 AGH 网页查看过程。

### 演示 PDF

若 `engineering-document-acceptance/cases/*/files/` 缺失，可本地生成：

```bash
cd engineering-document-acceptance
python tools/generate_demo_case.py
python tools/generate_near_miss_case.py
python tools/generate_complete_case.py
python tools/fetch_public_pdfs.py
```

---

## 说明与边界

- 本仓库为 AGH Skill 演示与本地核查台，**不是** Agnes Harness 源码本身。
- 归档要求因地区、工程类型、建设单位而异；以可配置规则为准，可替换 JSON。
- 脚本初稿结论供 Agent 抽查润色；正式行政验收效力以主管部门规定为准。
- **请勿提交**：模型 API Key、密码、`.env`、真实工程档案、身份证号 / 手机号等个人隐私。仓库演示数据为合成材料。

---

## 来源与授权

- **运行时框架**：[Agnes Harness](https://github.com/AgnesAI-Labs/agnes-harness)（Apache-2.0）
- **公开参考 PDF / 归档目录**：版权归原发布单位；URL 与用途见 `reference/**/SOURCES.txt`。默认不强制入库，可用 `tools/fetch_*.py` 拉取。
- **合成演示 PDF**：版式参考公开样表与示范文本栏目，内容为虚构填写，可自由用于复现实验。
- **本项目演示与学习用途**：使用或二次分发时请保留第三方来源说明与许可证信息。

## License

演示与学习用途。公开参考文件版权归原发布单位；合成数据可自由用于复现实验。