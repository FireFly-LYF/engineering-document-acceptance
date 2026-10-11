---
name: engineering-doc-generator
description: >-
  Generates 房屋建筑工程竣工资料完整性与一致性核查情况说明 as evidence-driven Chinese
  prose and Word (.docx). Runs scripts/generate.js prepare then Agent drafts
  正文.md, then build. Use when the user says 生成情况说明, 生成核查说明, 生成文书,
  engineering-doc-generator, 导出docx, or asks to draft an archive-check statement.
---

# 房屋建筑工程竣工资料核查情况说明（文书生成 · 证据驱动）

本 Skill **以文书生成为主**：把核查产物整理成正式《竣工资料完整性与一致性核查情况说明》，并导出 Word。  
文风对齐工程资料核查/档案验收留痕惯例：工程概况 → 完整性 → 一致性 → 问题与证据 → 处理意见 → 结论。  
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
| **本 Skill（你）** | 只读 brief + facts + outline，撰写 `_work/正文.md` |
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
node scripts/generate.js build   --case ../../../cases/demo-housing-mixed
# docx 默认写到 cases/demo-housing-mixed/doc/（不要 --out 到仓库根）
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

### 硬约束

1. 章节顺序对齐 `outline.md`（工程概况 → 完整性 → 一致性 → 问题与证据 → 处理意见 → 结论 → 落款）。  
2. 只用 facts / evidence / agent-brief / findings 中的真实信息。  
3. 书面、克制；只写资料标准名、清单编号、报告编号；**不写磁盘路径**。  
4. 有缺失不得写「全部材料齐全合格」。  
5. 预验收默认不能替代正式《工程竣工验收报告》。  
6. 问题分层：缺失 → 错传（他项）→ 重复 → **本工程**字段冲突；勿把错传级联写成多条本工程冲突。  
7. 段末附件行：`附件：名称1；名称2；…。`（仅名称）

### 文风

口吻：参建或核查方出具的**竣工资料核查情况说明**。可读、可核对，像资料核查记录扩写，不像套公式填空。  
正文用语用「已提供 / 缺失 / 错传或重复 / 需复核」，不要把 `missing`、`suspect_duplicate_or_misfiled` 等英文状态码写进文书。

### 各节怎么写

#### 开场

工程名称 + 参建单位（facts 有则写）+ 本次对照归档清单做完整性与一致性核查的范围；过渡用「现就本工程竣工资料核查有关情况说明如下」。

#### 一、工程及核查基本情况

写清工程概况要点、适用规则档/清单项规模、已归集材料份数。不堆路径，不抄整份 audit-report。

#### 二、资料完整性核查情况

对照归档目录概括：已提供若干、缺失若干、错传或重复若干。有缺项点名清单编号与标准名；全齐则写明按清单已提供，勿编造缺项。

#### 三、资料一致性核查情况

写工程名称、工程编号、日期、签章主体等本工程字段核对结果。无冲突写「未见本工程关键字段冲突」；有冲突见下一节展开，此处可先一句总括。

#### 四、主要问题及证据说明

按 brief 重要问题列表扩写：每项写清事实、影响范围、对应短文件名；错传单独成段。无问题则明确「未发现缺失、错传、重复及本工程字段冲突」。有引用材料时段末写附件行。

#### 五、处理意见与建议

针对问题给可操作意见：补齐缺项、更正错传/冲突取值、退回重报、指定人工复核。无问题可写「建议按现行归档要求继续组卷移交」。

#### 六、核查结论

与 findings 同向收束：是否材料齐全、一致性是否成立、是否具备进入下一阶段归档/验收资料条件（资料结论，不替代实体质量验收）。有缺失必须点明主要缺项。

#### 落款

「特此说明！」+ 日期（`facts.current_date`）。

优先依据 `agent-brief.md` 中的重要问题列表扩写，**不要**整篇粘贴 `audit-report.md`，也**不要**再通读全部 PDF（已由脚本压缩进 brief）。

## 反模式

- 跳过 prepare，直接凭记忆写文书  
- 把全部 PDF 重新读一遍（费 token、慢、不确定）  
- 未 build 就声称已生成 Word  
- 混入与本工程资料核查无关的业务措辞  
- 在文书里使用英文状态码或内部脚本字段名充当结论用语  

## 完成后

告知：`正文.md` 路径、docx 路径、缺失/冲突数量摘要。
