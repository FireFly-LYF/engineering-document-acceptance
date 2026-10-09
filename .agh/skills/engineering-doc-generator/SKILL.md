---
name: engineering-doc-generator
description: >-
  Generates 建设工程竣工资料核查情况说明 as evidence-driven Chinese prose and Word
  (.docx). Runs scripts/generate.js prepare then Agent drafts 正文.md, then
  build. Use when the user says 生成情况说明, 生成核查说明, 生成文书,
  engineering-doc-generator, 导出docx, or asks to draft an archive-check statement.
---

# 建设工程竣工资料核查情况说明（文书生成 · 证据驱动）

本 Skill **以文书生成为主**：把核查产物整理成正式「情况说明」，并导出 Word。  
脚本负责确定性准备与排版；Agent **只撰写** `正文.md`，不改用户材料、不做机械 `${占位符}` 填空。

## 目录（本 Skill）

```text
engineering-doc-generator/
├── SKILL.md
├── package.json
└── scripts/generate.js    # prepare / build
```

工作区项目包：`cases/<project-id>/`（含 `manifest.json`、`files/`、`_work/`）。

## 角色分工

| 角色 | 职责 |
|------|------|
| **scripts/generate.js prepare** | 从 `_work/findings.json` 等生成 facts / evidence / outline / agent-brief（确定性，省 token） |
| **本 Skill（你）** | 只读 brief + facts，撰写 `_work/正文.md` |
| **scripts/generate.js build** | `正文.md` → `.docx`（不写正文） |

## 前置条件

`_work/findings.json` 必须已存在。若缺失，先跑核查确定性脚本（不要让 Agent 手搓清单）：

```bash
python .agh/skills/engineering-archive-audit/scripts/audit_prepare.py --case cases/demo-housing-mixed
```

## 命令（在本 Skill 目录执行）

```bash
cd .agh/skills/engineering-doc-generator
npm install   # 首次（勿把 npm script 命名为 prepare，会与 npm 生命周期冲突）

node scripts/generate.js prepare --case ../../../cases/demo-housing-mixed
# 然后撰写 ../../../cases/demo-housing-mixed/_work/正文.md
node scripts/generate.js build   --case ../../../cases/demo-housing-mixed --out ../../../生成结果
```

## 执行进度

```text
进度:
- [ ] 1. 确认 findings.json 存在（否则先 audit_prepare）
- [ ] 2. prepare
- [ ] 3. 读 agent-brief.md / facts.json / evidence.json / outline.md
- [ ] 4. 撰写 正文.md（按下文章节）
- [ ] 5. build 导出 docx
- [ ] 6. 抽查：无占位、结论与 findings 同向、无路径泄露
```

## 三条底线

1. **不改用户材料**：`files/**`、规则 JSON、核查输入只读。  
2. **缺失值不要了**：facts 未给出的字段整句不写。  
3. **禁止**空格/XXXX/「暂缺」填空；禁止编造消防/检测合格等无证据结论。

## 撰写规则（正文.md）

- 书面、克制；只写资料名称、清单编号、报告编号；**不写磁盘路径**。  
- 有 `missing` 不得写「全部齐套合格」。  
- 预验收默认不能替代正式《工程竣工验收报告》。  
- 问题分层：缺失 → 错传（他项）→ 重复 → **本工程**字段冲突；勿把错传级联写成多条本工程冲突。  
- 段末附件行：`附件：名称1；名称2；…。`（仅名称）

### 章节顺序

1. 标题：`关于××项目…核查的情况说明`  
2. 一、项目与核查范围  
3. 二、核查结论摘要（四态）  
4. 三、主要问题与证据  
5. 四、字段一致性说明  
6. 五、处理建议与下一步  
7. 六、落款：「特此说明！」+ 日期（用 facts.current_date）

优先依据 `agent-brief.md` 中的重要问题列表扩写，**不要**整篇粘贴 `audit-report.md`，也**不要**再通读全部 PDF（已由脚本压缩进 brief）。

## 反模式

- 跳过 prepare，直接凭记忆写文书  
- 把全部 PDF 重新读一遍（费 token、慢、不确定）  
- 未 build 就声称已生成 Word  
- 混入与本工程资料核查无关的业务措辞  

## 完成后

告知：`正文.md` 路径、docx 路径、缺失/冲突数量摘要。
