"""One complete run; original files are read-only and every run has its own artifacts."""
from __future__ import annotations
import json
import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path
from app.agnes import AgnesClient,load_env
from app.common import digest, write_json, now
from app.registry import Registry,ROOT
from app.storage import open_database
from app.ingestion import ingest
from app.extraction import extract
from app.audit import evaluate
from app.persistence import create_run,save_run,add_artifact
from app.reporting import artifacts,write_statement


def _progress(message):
    print(message,flush=True)


def run_case(case,*,reference=None,use_agnes=False,word=False,db=None,progress=_progress):
    started = time.perf_counter()
    case = Path(case).resolve()
    if not (case/'files').is_dir() or not (case/'manifest.json').is_file():
        raise ValueError('case 需要 manifest.json 和 files 目录')
    manifest = json.loads((case/'manifest.json').read_text(encoding='utf-8-sig'))
    if not isinstance(manifest,dict):
        raise ValueError('manifest 必须为对象')
    registry = Registry(reference)
    if manifest.get('project_type') and manifest['project_type']!=registry.rules['project_type']:
        raise ValueError('工程类型与给定参考不一致，请配置对应工程类型的参考 Markdown')
    validate_manifest(manifest,registry)
    load_env()
    client = AgnesClient() if use_agnes else None
    run_id = 'run_'+uuid.uuid4().hex[:24]
    work = case/'_work'
    run_dir = work/'runs'/run_id
    run_dir.mkdir(parents=True,exist_ok=False)
    database_config = db or os.getenv('ENGINEERING_DATABASE_URL')
    database = database_config if database_config and str(database_config).startswith('mysql://') else Path(database_config) if database_config else work/'audit.sqlite'
    # Return a redacted location, never expose a DSN with credentials in JSON/logs.
    public_database = 'mysql (configured connection)' if str(database).startswith('mysql://') else str(database)
    connection = open_database(database)
    registry.install(connection)
    expected = {p.relative_to(case/'files').as_posix():digest(p) for p in (case/'files').rglob('*') if p.is_file()}
    input_sha = digest(json.dumps({'manifest':manifest,'files':expected},ensure_ascii=False,sort_keys=True))
    project_id = create_run(connection,registry,manifest,case,run_id,input_sha)
    write_json(run_dir/'input-manifest.json',manifest)
    write_json(run_dir/'config-snapshot.json',registry.snapshot)
    timings = {}
    try:
        progress('[1/6] 全页解析、OCR 与来源映射')
        stage = time.perf_counter()
        files,documents = ingest(case/'files',run_dir,run_id,registry,client,manifest.get('file_tags'))
        if {f['path']:f['sha256'] for f in files}!=expected:
            raise RuntimeError('运行中输入发生变化，请重新提交稳定资料包')
        timings['ingestion'] = round(time.perf_counter()-stage,3)
        progress(f'[2/6] 按 tag-label 提取字段候选：{len(documents)} 份逻辑资料')
        stage = time.perf_counter()
        extract(documents,registry,client,workers=int(os.getenv('AGNES_MAX_WORKERS','3')))
        timings['extraction'] = round(time.perf_counter()-stage,3)
        progress('[3/6] 归属、适用性、齐套、一致性和重复版本核查')
        result = evaluate(files,documents,manifest,registry,run_id)
        progress('[4/6] 保存证据关系与运行快照')
        save_run(connection,registry,run_id,project_id,files,documents,result,client.stats() if client else {})
        progress('[5/6] 生成核查报告与情况说明')
        report = artifacts(run_dir,manifest,registry,files,documents,result,run_id)
        body = write_statement(run_dir,manifest,result,client,documents)
        stats = client.stats() if client else {'total_calls':0,'total_tokens':0,'calls':[]}
        if client:
            from app.persistence import insert,json_text
            saved = connection.execute('SELECT count(*) FROM model_call WHERE run_id=?',(run_id,)).fetchone()[0]
            with connection:
                for i,c in enumerate(stats['calls'][saved:],saved):
                    insert(connection,'model_call',{'id':run_id+'_draft_'+str(i),'run_id':run_id,'purpose':c['purpose'],
                        'model_name':c['model'],'prompt_sha256':c['prompt_sha256'],'input_sha256':c['input_sha256'],
                        'status':c['status'],'latency_ms':round(c['elapsed_seconds']*1000),'usage_json':json_text(c['usage']),
                        'error_code':c.get('error_code')})
        for filename,kind in [('audit-result.json','audit_json'),('audit-report.md','audit_markdown'),
                              ('正文.md','statement_markdown'),('evidence-index.json','evidence_index')]:
            add_artifact(connection,run_id,run_dir/filename,kind)
        published = None
        if word:
            progress('[6/6] 导出经过事实校验的 Word')
            word_path = run_dir/'deliverables'/'竣工资料核查情况说明.docx'
            word_path.parent.mkdir(parents=True,exist_ok=True)
            cmd = ['node',str(ROOT/'tools/export_word.js'),'--body',str(body),'--facts',str(run_dir/'statement-facts.json'),'--out',str(word_path)]
            completed = subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8')
            if completed.returncode:
                raise RuntimeError('Word 导出失败：'+completed.stderr[:300])
            add_artifact(connection,run_id,word_path,'statement_docx',validation='needs_review')
            import re
            project_filename = re.sub(r'[\\/:*?"<>|\x00-\x1f]','_',str(manifest.get('project_id','工程')))[:80]
            published = ROOT/'生成结果'/f"{project_filename}_{run_id}_核查情况说明.docx"
            published.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(word_path,published)
        else:
            progress('[6/6] 完成；正文可由文书 Skill build 导出')
        timings['total'] = round(time.perf_counter()-started,3)
        write_json(run_dir/'run_stats.json',{'timings':timings,'model_usage':stats})
        for path in run_dir.iterdir():
            if path.is_file():
                destination = work/path.name
                temporary = destination.with_suffix(destination.suffix+'.tmp')
                shutil.copy2(path,temporary)
                temporary.replace(destination)
        write_json(work/'latest-run.json',{'run_id':run_id,'run_dir':str(run_dir),'database':public_database,'input_sha256':input_sha})
        return {'run_id':run_id,'run_dir':str(run_dir),'database':public_database,'summary':result['summary'],
            'word_path':str(published) if published else None,'report':str(report),
            'model_usage':{k:v for k,v in stats.items() if k!='calls'}}
    except Exception:
        with connection:
            connection.execute('UPDATE audit_run SET status=?,finished_at=? WHERE id=?',('failed',now(),run_id))
        raise
    finally:
        connection.close()


def validate_manifest(manifest,registry):
    context = manifest.get('audit_context',{})
    if not isinstance(context,dict):
        raise ValueError('audit_context 必须为对象')
    for key in ('supervision_entrusted','fire_spotcheck_selected','coverage_plan_confirmed','fire_regulation_applicable'):
        if key in context and context[key] is not None and not isinstance(context[key],bool):
            raise ValueError(key+' 必须为 true/false 或 null')
    if context.get('fire_category') not in (None,'special','other','not_applicable','unknown'):
        raise ValueError('fire_category 枚举无效')
    for expected in manifest.get('coverage_plan',[]):
        if not isinstance(expected,dict) or expected.get('tag') not in registry.tags:
            raise ValueError('应交范围条目需要合法 tag')
        if not any(k in expected for k in ('unit_name','discipline','location')):
            raise ValueError('应交范围必须明确单位工程、专业或部位，不能仅填写 tag')
        if any(k not in registry.labels and k!='tag' for k in expected):
            raise ValueError('应交范围含未配置字段')
