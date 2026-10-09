"""Evidence-based output and deterministic prose checks for the document generator."""
from __future__ import annotations
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from app.common import write_json


def artifacts(run_dir,manifest,registry,files,documents,result,run_id):
    candidate_map = {c['id']:c for d in documents for c in d['candidates']}
    doc_map = {d['id']:d for d in documents}
    summary = result['summary']
    lines = ['# 工程竣工资料核查报告','',f"项目：{manifest.get('project_name','未确认')} / {manifest.get('project_code','未确认')}",
        f'运行编号：{run_id}',f'规则版本：{registry.rules["profile_id"]} / {registry.sha256[:16]}',
        f"接收 {summary['files']} 份文件，拆分 {summary['documents']} 份逻辑资料。",
        '核查范围：已配置资料类型、文载信息及已确认的应交范围；不作行政验收或工程实体质量认定。','',
        '## 统计','',json.dumps(summary,ensure_ascii=False,indent=2),'','## 问题与证据','']
    for f in result['findings']:
        lines.extend([f"### {f['title']}",f"问题类型：{f['finding_type']}；原因：{f['reason_code']}",f"建议：{f['suggestion']}"])
        for cid in f['candidate_ids']:
            c = candidate_map[cid]
            d = doc_map[c['document_unit_id']]
            location = f"第{c['page']}页" if c['page'] else f"逻辑单元{c['unit_no']}"
            lines.append(f"- {d['file_name']}，{location}：{c['evidence']}")
        if f['details']:
            lines.append('详情：'+json.dumps(f['details'],ensure_ascii=False))
        lines.append('')
    report = run_dir/'audit-report.md'
    report.write_text('\n'.join(lines),encoding='utf-8')
    # Old Skill compatibility is a projection, not a second source of audit truth.
    compatibility = []
    for e in result['evaluations']:
        if e['kind']!='presence':
            continue
        compatibility.append({'code':e['rule_code'],'name':e['name'],
            'status':'provided' if e['result']=='pass' else 'missing' if e['result']=='fail' else 'needs_human_review',
            'severity':'error' if e['result']=='fail' else 'info','reason':e['reason_code'],
            'suggestion':'按本项目适用条件补充或复核资料','rule_result':e['result']})
    for f in result['findings']:
        if f['finding_type']=='missing':
            continue
        compatibility.append({'code':f['finding_type'],'name':f['title'],
            'status':'suspect_duplicate_or_misfiled' if f['finding_type'] in ('duplicate','misfiled','version_conflict') else 'needs_human_review',
            'severity':f['severity'],'reason':f['reason_code'],'suggestion':f['suggestion'],
            'finding_id':f['id']})
    write_json(run_dir/'findings.json',{'items':compatibility,'rules_profile':registry.rules['profile_id'],'run_id':run_id})
    write_json(run_dir/'audit-result.json',{'run_id':run_id,'rules_fingerprint':registry.sha256,
        'manifest':manifest,'scope':registry.rules['scope'],'profile_status':registry.rules.get('status'),**result})
    write_json(run_dir/'inventory.json',{'count':len(files),'files':[{k:v for k,v in f.items() if k!='units'} for f in files]})
    write_json(run_dir/'classification.json',{'items':[{k:d[k] for k in ('id','file_name','tag','tag_status','identity_status','title')} for d in documents]})
    write_json(run_dir/'candidates.json',{'documents':[{k:v for k,v in d.items() if k!='units'} for d in documents]})
    write_json(run_dir/'fields.json',{d['file_name']+f"#doc{d['unit_no']}":{registry.labels[c['label']]['label']:c['raw_value']
        for c in d['candidates'] if c['value_role']=='subject' and c['validation_status']=='accepted'} for d in documents})
    conflicts = [{'field':registry.labels[candidate_map[f['candidate_ids'][0]]['label']]['label'],
        'values':f['details'],'finding_id':f['id']} for f in result['findings'] if f['finding_type']=='field_conflict' and f['candidate_ids']]
    write_json(run_dir/'field_consensus.json',{'锚值':{registry.labels[k]['label']:v for k,v in manifest.items() if k in registry.labels},
        'conflicts':conflicts,'冲突':conflicts,'excluded_other_project':summary['misfiled_documents']})
    brief = ['# Agent 核查简报','',f"接收文件：{summary['files']}；主项目逻辑资料：{summary['target_documents']}",
        '只依据 audit-result.json 及问题引用的原文核查，不重新通读所有文件。','']
    brief += [f"- {f['id']}：{f['title']}；{f['suggestion']}" for f in result['findings']]
    (run_dir/'agent-brief.md').write_text('\n'.join(brief),encoding='utf-8')
    evidence = [{**c,'file_name':doc_map[c['document_unit_id']]['file_name']} for c in candidate_map.values()]
    write_json(run_dir/'evidence-index.json',evidence)
    return report


def statement_plan(result):
    summary = result['summary']
    finding_counts = summary['finding_counts']
    return {'file_count':summary['files'],'document_count':summary['documents'],
        'missing_items':finding_counts.get('missing',0),'misfiled_documents':summary['misfiled_documents'],
        'field_conflict_items':finding_counts.get('field_conflict',0),'duplicate_groups':finding_counts.get('duplicate',0),
        'version_conflict_groups':finding_counts.get('version_conflict',0),
        'review_items':sum(e['result'] in ('needs_review','not_evaluated') for e in result['evaluations']),
        'coverage_level':summary['coverage_level'],'overall':summary['overall'],'legal_acceptance_decision':False}


def write_statement(run_dir,manifest,result,client=None,documents=()):
    plan = statement_plan(result)
    narrative = {}
    drafting_error = None
    if client:
        # The model writes issue explanations only. Numbers and conclusions remain Python-owned.
        try:
            response = client.json('根据结构化问题写中文工程资料核查说明。只解释输入问题，不新增数量、日期、金额、'
                '合格或合法有效结论，不加入磁盘路径。每项保留 finding_id。'
                '输出 {"items":[{"finding_id":"...","explanation":"..."}]}。',
                {'findings':result['findings']},purpose='statement_drafting',max_tokens=6000)
        except (RuntimeError,ValueError):
            response = {}
            drafting_error = 'agnes_drafting_failed_used_verified_facts'
        allowed = {f['id'] for f in result['findings']}
        for item in response.get('items',[]) if isinstance(response,dict) else []:
            if item.get('finding_id') in allowed and isinstance(item.get('explanation'),str):
                text = item['explanation']
                # Conservative gate: model-added factual identifiers/numbers are not allowed.
                if not re.search(r'\d|[A-Za-z]|合格|通过|合法|有效|真实|齐全|齐套|补齐|已经|满足.*条件|[A-Za-z]:[\\/]',text):
                    narrative[item['finding_id']] = text
    date = datetime.now(timezone(timedelta(hours=8))).strftime('%Y年%m月%d日')
    lines = [f"# 关于{manifest.get('project_name','本工程')}竣工资料核查的情况说明",'',
        '## 一 项目与核查范围','',
        (f"本次核查项目为{manifest['project_name']}" if manifest.get('project_name') else '本次核查以接收资料包为范围')
            +(f"，项目编号{manifest['project_code']}。" if manifest.get('project_code') else '。'),
        f"共接收文件{plan['file_count']}份，拆分为逻辑资料{plan['document_count']}份。按配置规则核查资料类型和文载信息。",
        '本次结论限定于接收资料及已配置的核查范围。地区完整归档目录尚须确认；不替代工程质量鉴定和行政验收。','',
        '## 二 核查结论','',
        f"发现缺失资料{plan['missing_items']}项，他项工程资料{plan['misfiled_documents']}份，字段冲突{plan['field_conflict_items']}项，重复资料{plan['duplicate_groups']}组，版本差异{plan['version_conflict_groups']}组。",
        f"尚需复核或确认适用条件的规则结果{plan['review_items']}项。",
        '已提供某类型资料不等于全部楼栋、专业和部位齐套。','',
        '## 三 主要问题与处理建议','']
    candidate_map = {c['id']:c for d in documents for c in d['candidates']}
    for i,f in enumerate(result['findings'],1):
        public_title = re.sub(r'(?<=：)(?:[^/\n]+/)+','',f['title'])
        lines += [f"### {i} {public_title}",f['suggestion']+'。','']
        if f['id'] in narrative:
            lines.append(narrative[f['id']])
        if f['details'].get('values'):
            raw_values = list(dict.fromkeys(
                candidate_map[c]['normalized_value']+'元' if candidate_map[c]['value_unit']=='CNY' else candidate_map[c]['raw_value']
                for c in f['candidate_ids'] if c in candidate_map))
            lines.append('文载候选取值：'+'；'.join(raw_values or f['details']['values'])+'。')
        lines.append('')
    lines += ['## 四 下一步','',
        '补充缺失材料，核实他项工程资料归属，并依据原始合同、版本和来源证据确认字段差异。完成复核后重新运行核查。',
        '问题资料名称及原文位置见核查报告中的证据索引；缺失材料未作为随文附件。','',date,'']
    body = '\n'.join(lines)
    write_json(run_dir/'statement-facts.json',plan)
    (run_dir/'正文.md').write_text(body,encoding='utf-8')
    validation = validate_statement(body,plan)
    write_json(run_dir/'statement-validation.json',{**validation,'drafting_error':drafting_error})
    if not validation['passed']:
        raise ValueError('情况说明事实校验失败')
    write_json(run_dir/'statement-meta.json',{'title':f"关于{manifest.get('project_name','本工程')}竣工资料核查的情况说明.docx",'current_date':date})
    return run_dir/'正文.md'


def validate_statement(body,plan):
    errors = []
    checks = {'file_count':r'共接收文件(\d+)份','document_count':r'逻辑资料(\d+)份',
        'missing_items':r'缺失资料(\d+)项','misfiled_documents':r'他项工程资料(\d+)份',
        'field_conflict_items':r'字段冲突(\d+)项','duplicate_groups':r'重复资料(\d+)组','version_conflict_groups':r'版本差异(\d+)组'}
    for key,pattern in checks.items():
        matches = re.findall(pattern,body)
        if not matches or any(int(x)!=plan[key] for x in matches):
            errors.append('count_mismatch:'+key)
    if re.search(r'\$\{|XXXX|请 Agent 在此|[A-Za-z]:[\\/]|sk-[A-Za-z0-9]{12}',body):
        errors.append('placeholder_path_or_secret')
    if plan['overall']!='configured_checks_passed' and re.search(r'全部齐套合格|资料全部合格',body):
        errors.append('unsupported_all_pass')
    return {'passed':not errors,'checks':'固定统计、占位符、路径、密钥和全量通过措辞；自由文本仍需人工校对','errors':errors}
