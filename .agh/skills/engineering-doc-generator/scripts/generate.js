/**
 * 建设工程竣工资料核查情况说明 — 证据驱动生成器
 *
 * prepare: 读取 cases/<id> 的 manifest + audit _work → facts/evidence/outline/agent-brief
 * build:   读取 _work/正文.md → 导出 docx
 *
 * 用法（在 engineering-doc-generator 目录）:
 *   node scripts/generate.js prepare --case ../../../cases/demo-housing-mixed
 *   node scripts/generate.js build   --case ../../../cases/demo-housing-mixed
 *   # 默认输出到 cases/<id>/doc/；勿写到仓库根
 *
 * 正文由 Agent 按 SKILL.md 撰写；脚本不写正文内容，只 prepare 结构化材料与 build 版式。
 */

const fs = require('fs');
const path = require('path');

function log(...args) {
  console.log('[engineering-doc-generator]', ...args);
}

function getCurrentDate() {
  const d = new Date();
  return `${d.getFullYear()}年${String(d.getMonth() + 1).padStart(2, '0')}月${String(d.getDate()).padStart(2, '0')}日`;
}

function readJson(filePath, fallback = null) {
  if (!fs.existsSync(filePath)) return fallback;
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function ensureDir(p) {
  fs.mkdirSync(p, { recursive: true });
}

function workDir(caseDir) {
  return path.join(caseDir, '_work');
}

function loadCaseBundle(caseDir) {
  const wd = workDir(caseDir);
  const manifest = readJson(path.join(caseDir, 'manifest.json'), {}) || {};
  const findings = readJson(path.join(wd, 'findings.json'), null);
  const inventory = readJson(path.join(wd, 'inventory.json'), null);
  const consensus = readJson(path.join(wd, 'field_consensus.json'), null);
  const classification = readJson(path.join(wd, 'classification.json'), null);
  const fields = readJson(path.join(wd, 'fields.json'), null);
  const auditReportPath = path.join(wd, 'audit-report.md');
  const auditReport = fs.existsSync(auditReportPath)
    ? fs.readFileSync(auditReportPath, 'utf8')
    : '';
  return {
    caseDir,
    wd,
    manifest,
    findings,
    inventory,
    consensus,
    classification,
    fields,
    auditReport,
  };
}

function summarizeFindings(findings) {
  const items = Array.isArray(findings)
    ? findings
    : findings && Array.isArray(findings.items)
      ? findings.items
      : [];
  const counts = {
    provided: 0,
    missing: 0,
    suspect_duplicate_or_misfiled: 0,
    needs_human_review: 0,
    other: 0,
  };
  for (const it of items) {
    const st = it.status || 'other';
    if (counts[st] != null) counts[st] += 1;
    else counts.other += 1;
  }
  return { items, counts, total: items.length };
}

function buildFacts(bundle) {
  const m = bundle.manifest || {};
  const c = bundle.consensus || {};
  const inv = bundle.inventory || {};
  const files = Array.isArray(inv.files) ? inv.files : Array.isArray(inv) ? inv : [];
  const summary = summarizeFindings(bundle.findings);

  const available = {};
  const put = (k, v) => {
    if (v == null) return;
    const s = String(v).trim();
    if (!s || /^X{2,}$/i.test(s) || /暂缺|待填写|示例/.test(s)) return;
    available[k] = s;
  };

  put('project_name', m.project_name || c.project_name || c.锚值?.project_name);
  put('project_code', m.project_code || c.project_code || c.锚值?.project_code);
  put('owner', m.owner || c.owner);
  put('contractor', m.contractor || c.contractor);
  put('supervisor', m.supervisor || c.supervisor);
  put('designer', m.designer || c.designer);
  put('address', m.address || c.address);
  put('start_date', m.start_date || c.start_date);
  put('finish_date', m.finish_date || c.finish_date);
  put('contract_amount', m.contract_amount || c.contract_amount);
  put('project_type', m.project_type || '房屋建筑工程');
  put('rules_profile', m.rules_profile || 'housing-construction');
  put('file_count', String(m.file_count || files.length || ''));
  put('current_date', getCurrentDate());

  const conflicts = Array.isArray(c.conflicts)
    ? c.conflicts
    : Array.isArray(c.冲突)
      ? Object.entries(c.冲突).map(([field, info]) => ({
          field,
          values: info.values,
          summary: info.summary,
          scope: 'in_project',
        }))
      : [];

  // Prefer in-project FIELD only; MISFILE/DUP/missing always included.
  const important_findings = summary.items.filter((x) => {
    if (['missing', 'suspect_duplicate_or_misfiled'].includes(x.status)) return true;
    if (x.status === 'needs_human_review' && x.code === 'FIELD') {
      return x.scope !== 'misfile_cascade';
    }
    return x.status === 'needs_human_review';
  });

  return {
    available,
    missing_keys: [],
    finding_counts: summary.counts,
    finding_total: summary.total,
    conflicts,
    important_findings,
    provided_codes: summary.items
      .filter((x) => x.status === 'provided')
      .map((x) => x.code || x.name)
      .filter(Boolean),
    consensus_note: c.note || '',
  };
}

function buildEvidence(bundle) {
  const files = [];
  const inv = bundle.inventory || {};
  const list = Array.isArray(inv.files) ? inv.files : Array.isArray(inv) ? inv : [];
  for (const f of list) {
    const name = f.filename || f.name || f.path || '';
    if (name) files.push({ name: path.basename(String(name)), path: f.path || name });
  }
  return {
    exists: files.length > 0,
    count: files.length,
    files,
    audit_report_excerpt: (bundle.auditReport || '').slice(0, 4000),
  };
}

function statementTitle(projectName) {
  const name = String(projectName || '本工程').trim() || '本工程';
  return `关于${name}竣工资料完整性与一致性核查的情况说明`;
}

function buildOutline(facts) {
  const name = facts.available.project_name || '本工程';
  const c = facts.finding_counts || {};
  const hasGap =
    (c.missing || 0) +
      (c.suspect_duplicate_or_misfiled || 0) +
      (c.needs_human_review || 0) +
      (facts.conflicts || []).length >
    0;
  return [
    `标题：${statementTitle(name)}`,
    '开场：写明工程名称、建设/施工/监理单位（facts 有则写）、核查依据（归档清单与规则档）及本次核查范围；过渡句用「现就本工程竣工资料核查有关情况说明如下」',
    '一、工程及核查基本情况（工程概况、清单项数、已归集材料份数；不写磁盘路径）',
    '二、资料完整性核查情况（对照归档目录：已提供、缺失、错传或重复；用资料标准名与清单编号，不用英文状态码）',
    '三、资料一致性核查情况（工程名称、工程编号、开工/竣工日期、签章主体等本工程字段；错传他项引起的级联差异勿写成多条本工程冲突）',
    hasGap
      ? '四、主要问题及证据说明（分层：缺失 → 错传（他项）→ 重复 → 本工程字段冲突；每段写清事实、影响与短文件名；段末「附件：…」仅名称）'
      : '四、主要问题及证据说明（本次无缺失/错传/重复/本工程冲突时，写明经核对未发现上述问题，勿编造缺项）',
    '五、处理意见与建议（补齐缺项、更正错传/冲突、退回重报、指定人工复核；有期限事实才写期限）',
    hasGap
      ? '六、核查结论（概括材料齐全与一致性总体判断；有缺失不得写全部材料齐全合格；预验收不能替代正式竣工验收报告）'
      : '六、核查结论（资料按清单材料齐全、关键字段未见冲突；结论与 findings 同向，勿夸大）',
    '落款：「特此说明！」+ 日期（用 facts.current_date）',
  ];
}

function statusLabel(st) {
  return (
    {
      provided: '已提供',
      missing: '缺失',
      suspect_duplicate_or_misfiled: '错传或重复',
      needs_human_review: '需复核',
    }[st] || st
  );
}

function writeAgentBrief(bundle, facts, evidence, outline) {
  const a = facts.available;
  const c = facts.finding_counts || {};
  const lines = [];
  lines.push('# Agent 执笔简报（请只据此与 facts/evidence 写正文.md）');
  lines.push('');
  lines.push('## 任务');
  lines.push(
    '撰写《房屋建筑工程竣工资料完整性与一致性核查情况说明》正文。' +
      '口吻为工程资料核查说明（对照归档清单做材料齐全与一致性核查），证据驱动，禁止占位符填空与编造。'
  );
  lines.push('');
  lines.push('## 工程要点（仅列已有值）');
  for (const [k, v] of Object.entries(a)) {
    if (k === 'current_date') continue;
    lines.push(`- ${k}: ${v}`);
  }
  lines.push(`- 落款日期可用: ${a.current_date || getCurrentDate()}`);
  lines.push('');
  lines.push('## 完整性核查统计（对照归档清单）');
  lines.push(
    `- 已提供 ${c.provided || 0}；缺失 ${c.missing || 0}；` +
      `错传或重复 ${c.suspect_duplicate_or_misfiled || 0}；` +
      `需人工复核 ${c.needs_human_review || 0}`
  );
  lines.push(`- 已归集材料份数: ${evidence.count}`);
  lines.push('');
  lines.push('## 须写入正文的重要问题（勿增删结论方向）');
  lines.push('分层：缺失 → 错传（他项工程）→ 重复 → 本工程字段冲突。勿把错传引起的级联差异写成多条本工程冲突。');
  if (!facts.important_findings.length) {
    lines.push('- （无缺失/错传/重复/本工程冲突；结论写资料材料齐全、未见明显一致性问题，勿夸大）');
  } else {
    for (const it of facts.important_findings) {
      const tip = [];
      if (it.similar_files && it.similar_files.length) {
        tip.push('相似: ' + it.similar_files.map((x) => path.basename(String(x))).join('；'));
      } else if (it.matched_file) {
        tip.push('文件: ' + path.basename(String(it.matched_file)));
      }
      lines.push(
        `- [${statusLabel(it.status)}] ${it.code || ''} ${it.name || ''} | ${it.reason || it.judgment || ''} | 建议: ${it.suggestion || ''}` +
          (tip.length ? ` | ${tip.join('；')}` : '')
      );
    }
  }
  lines.push('');
  lines.push('## 本工程字段冲突（摘要，已排除错传）');
  if (!facts.conflicts.length) lines.push('- 无');
  else {
    for (const item of facts.conflicts) {
      lines.push(`- ${item.field || item.name}: ${item.summary || JSON.stringify(item.values || item)}`);
    }
  }
  if (facts.consensus_note) {
    lines.push(`> ${facts.consensus_note}`);
  }
  lines.push('');
  lines.push('## 章节大纲（须按此顺序撰写，对齐竣工资料核查情况说明惯例）');
  for (const o of outline) lines.push(`- ${o}`);
  lines.push('');
  lines.push('## 硬约束');
  lines.push('- 只写工程资料核查用语；不写磁盘路径；附件行只写短文件名/资料标准名');
  lines.push('- 有缺失不得写「全部材料齐全合格」');
  lines.push('- 预验收默认不能替代正式《工程竣工验收报告》');
  lines.push('- 错传单独成段；本工程真冲突写清取值与短文件名');
  lines.push('- 写完后执行: node scripts/generate.js build --case <caseDir>');
  lines.push('');
  return lines.join('\n');
}

function prepareCase(caseDir) {
  const abs = path.resolve(caseDir);
  if (!fs.existsSync(abs)) throw new Error('case 不存在: ' + abs);
  const bundle = loadCaseBundle(abs);
  if (!bundle.findings) {
    throw new Error(
      '缺少 _work/findings.json。请先运行 archive-audit 的确定性脚本:\n' +
        '  python .agh/skills/engineering-archive-audit/scripts/audit_prepare.py --case ' +
        abs
    );
  }
  const wd = bundle.wd;
  ensureDir(wd);
  const facts = buildFacts(bundle);
  const evidence = buildEvidence(bundle);
  const outline = buildOutline(facts);

  fs.writeFileSync(path.join(wd, 'facts.json'), JSON.stringify(facts, null, 2), 'utf8');
  fs.writeFileSync(path.join(wd, 'evidence.json'), JSON.stringify(evidence, null, 2), 'utf8');
  fs.writeFileSync(
    path.join(wd, 'outline.md'),
    [
      '# 竣工资料核查情况说明大纲',
      '',
      '参照房屋建筑竣工资料/档案验收核查惯例组织章节（完整性 → 一致性 → 问题与证据 → 处理意见 → 结论）。',
      '正文只写资料标准名、清单编号与报告编号；不写磁盘路径。',
      '',
      ...outline.map((x) => `- ${x}`),
      '',
    ].join('\n'),
    'utf8'
  );
  fs.writeFileSync(path.join(wd, 'agent-brief.md'), writeAgentBrief(bundle, facts, evidence, outline), 'utf8');

  const bodyPath = path.join(wd, '正文.md');
  if (!fs.existsSync(bodyPath)) {
    fs.writeFileSync(
      bodyPath,
      `# （请 Agent 在此撰写情况说明正文）\n\n` +
        `> 请先阅读同目录 agent-brief.md 与 facts.json。写完后执行 build。\n`,
      'utf8'
    );
  }

  const title = `${statementTitle(facts.available.project_name)}.docx`;
  fs.writeFileSync(
    path.join(wd, 'statement-meta.json'),
    JSON.stringify(
      {
        title,
        current_date: facts.available.current_date,
        rules_profile: facts.available.rules_profile,
        prepared_at: new Date().toISOString(),
      },
      null,
      2
    ),
    'utf8'
  );

  log(`prepare → ${wd}`);
  log(
    `  findings=${facts.finding_total} missing=${facts.finding_counts.missing} conflicts=${facts.conflicts.length} files=${evidence.count}`
  );
  return wd;
}

function parseMarkdownToBlocks(md) {
  const lines = md.replace(/\r\n/g, '\n').split('\n');
  const blocks = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) {
      i++;
      continue;
    }
    if (line.startsWith('```')) {
      i++;
      while (i < lines.length && !lines[i].startsWith('```')) i++;
      i++;
      continue;
    }
    if (/^#\s+/.test(line)) {
      blocks.push({ type: 'h1', text: line.replace(/^#\s+/, '').trim() });
      i++;
      continue;
    }
    if (/^##\s+/.test(line)) {
      blocks.push({ type: 'h2', text: line.replace(/^##\s+/, '').trim() });
      i++;
      continue;
    }
    if (/^###\s+/.test(line)) {
      blocks.push({ type: 'h3', text: line.replace(/^###\s+/, '').trim() });
      i++;
      continue;
    }
    if (line.trim().startsWith('|') && i + 1 < lines.length && /---/.test(lines[i + 1])) {
      const splitRow = (l) => {
        const cells = l.split('|').map((c) => c.trim());
        if (cells[0] === '') cells.shift();
        if (cells.length && cells[cells.length - 1] === '') cells.pop();
        return cells;
      };
      const heads = splitRow(line);
      i += 2;
      const rows = [];
      while (i < lines.length && lines[i].trim().startsWith('|')) {
        rows.push(splitRow(lines[i]));
        i++;
      }
      blocks.push({ type: 'table', heads, rows });
      continue;
    }
    if (/^[-*]\s+/.test(line)) {
      const items = [];
      while (i < lines.length && /^[-*]\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^[-*]\s+/, '').trim());
        i++;
      }
      blocks.push({ type: 'ul', items });
      continue;
    }
    const paras = [];
    while (
      i < lines.length &&
      lines[i].trim() &&
      !/^#/.test(lines[i]) &&
      !lines[i].trim().startsWith('|') &&
      !/^[-*]\s+/.test(lines[i])
    ) {
      paras.push(lines[i].trim());
      i++;
    }
    if (paras.length) blocks.push({ type: 'p', text: paras.join('') });
  }
  return blocks;
}

const TPL_FONT = {
  ascii: 'Calibri',
  hAnsi: 'Calibri',
  eastAsia: '微软雅黑',
  cs: 'Times New Roman',
};
const TPL_SIZE = 21;
const PAGE_CONTENT_WIDTH = 11906 - 1797 - 1797;

function runOpts(text, { bold = false, size = TPL_SIZE } = {}) {
  return { text: text || '', bold, size, font: TPL_FONT };
}

function calcColumnWidths(heads) {
  const n = Math.max(heads.length, 1);
  const total = PAGE_CONTENT_WIDTH;
  const w = Math.floor(total / n);
  return Array(n)
    .fill(w)
    .map((x, i) => (i === n - 1 ? total - w * (n - 1) : w));
}

async function buildDocxFromMarkdown(md, outputPath) {
  let docx;
  try {
    docx = require('docx');
  } catch (e) {
    throw new Error(
      '请先在 engineering-doc-generator 目录执行 npm install（需要 docx 依赖）'
    );
  }
  const {
    Document,
    Packer,
    Paragraph,
    TextRun,
    Table,
    TableRow,
    TableCell,
    WidthType,
    BorderStyle,
    AlignmentType,
    VerticalAlign,
    convertInchesToTwip,
  } = docx;
  const blocks = parseMarkdownToBlocks(md);
  const children = [];
  const border = { style: BorderStyle.SINGLE, size: 4, color: '999999' };
  const borders = { top: border, bottom: border, left: border, right: border };
  const paraSpacing = { after: 60, line: 276 };

  for (const b of blocks) {
    if (b.type === 'h1') {
      children.push(
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: paraSpacing,
          children: [new TextRun(runOpts(b.text, { bold: true }))],
        })
      );
    } else if (b.type === 'h2') {
      children.push(
        new Paragraph({
          spacing: { before: 120, after: 60, line: 276 },
          children: [new TextRun(runOpts(b.text, { bold: true }))],
        })
      );
    } else if (b.type === 'h3') {
      children.push(
        new Paragraph({
          spacing: { before: 100, after: 60, line: 276 },
          children: [new TextRun(runOpts(b.text, { bold: false }))],
        })
      );
    } else if (b.type === 'p') {
      children.push(
        new Paragraph({
          spacing: paraSpacing,
          children: [new TextRun(runOpts(b.text))],
        })
      );
    } else if (b.type === 'ul') {
      for (const item of b.items) {
        children.push(
          new Paragraph({
            spacing: paraSpacing,
            children: [new TextRun(runOpts('• ' + item))],
          })
        );
      }
    } else if (b.type === 'table') {
      const colWidths = calcColumnWidths(b.heads);
      const makeCell = (text, colIdx, bold = false) =>
        new TableCell({
          borders,
          width: { size: colWidths[colIdx], type: WidthType.DXA },
          verticalAlign: VerticalAlign.CENTER,
          children: [
            new Paragraph({
              spacing: { after: 0, line: 240 },
              children: [new TextRun(runOpts(text || '', { bold, size: 18 }))],
            }),
          ],
        });
      const rows = [
        new TableRow({ children: b.heads.map((h, i) => makeCell(h, i, true)) }),
        ...b.rows.map(
          (r) => new TableRow({ children: b.heads.map((_, i) => makeCell(r[i] || '', i)) })
        ),
      ];
      children.push(
        new Table({
          width: { size: PAGE_CONTENT_WIDTH, type: WidthType.DXA },
          columnWidths: colWidths,
          rows,
        })
      );
      children.push(new Paragraph({ children: [] }));
    }
  }

  const doc = new Document({
    sections: [
      {
        properties: {
          page: {
            margin: {
              top: convertInchesToTwip(1),
              bottom: convertInchesToTwip(1),
              left: convertInchesToTwip(1.25),
              right: convertInchesToTwip(1.25),
            },
          },
        },
        children,
      },
    ],
  });
  const buf = await Packer.toBuffer(doc);
  fs.writeFileSync(outputPath, buf);
}

async function buildCase(caseDir, outRoot) {
  const abs = path.resolve(caseDir);
  const wd = workDir(abs);
  const bodyPath = path.join(wd, '正文.md');
  if (!fs.existsSync(bodyPath)) throw new Error('缺少正文.md，请先撰写: ' + bodyPath);
  const md = fs.readFileSync(bodyPath, 'utf8');
  if (/请 Agent 在此撰写/.test(md) && md.length < 400) {
    throw new Error('正文.md 仍是占位稿，请先由 Agent 写完整正文: ' + bodyPath);
  }
  const meta = readJson(path.join(wd, 'statement-meta.json'), {}) || {};
  const title = meta.title || `${statementTitle('本工程')}.docx`;
  // 默认 cases/<id>/doc/；显式 --out 也必须落在本 case 目录内
  const outDir = outRoot ? path.resolve(outRoot) : path.join(abs, 'doc');
  const relOut = path.relative(abs, outDir);
  if (!relOut || relOut.startsWith('..') || path.isAbsolute(relOut)) {
    throw new Error('docx 输出目录必须在本 case 内（默认 cases/<id>/doc）: ' + outDir);
  }
  ensureDir(outDir);
  const docxPath = path.join(outDir, title.replace(/[\\/:*?"<>|]/g, '_'));
  await buildDocxFromMarkdown(md, docxPath);
  log(`build → ${docxPath}`);
  return docxPath;
}

function parseArgs(argv) {
  const args = argv.slice(2);
  const opts = { cmd: null, caseDir: null, out: null };
  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    if (a === 'prepare' || a === 'build') opts.cmd = a;
    else if (a === '--case') opts.caseDir = args[++i];
    else if (a === '--out') opts.out = args[++i];
    else if (a.startsWith('-')) throw new Error('未知参数: ' + a);
  }
  return opts;
}

async function main() {
  const opts = parseArgs(process.argv);
  if (!opts.cmd || !opts.caseDir) {
    console.log(`用法:
  node scripts/generate.js prepare --case <cases/项目目录>
  node scripts/generate.js build   --case <cases/项目目录> [--out <本case内目录，默认doc>]`);
    process.exit(1);
  }
  if (opts.cmd === 'prepare') prepareCase(opts.caseDir);
  else await buildCase(opts.caseDir, opts.out);
}

if (require.main === module) {
  main().catch((e) => {
    console.error(e);
    process.exit(1);
  });
}

module.exports = { prepareCase, buildCase };
