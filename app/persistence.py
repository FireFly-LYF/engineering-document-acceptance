"""Persist the evidence graph using the approved relational schema."""
from __future__ import annotations
import json
from app.common import uid, digest, normalized, now


def insert(connection, table, values):
    columns = ','.join(values)
    connection.execute(f"INSERT INTO {table} ({columns}) VALUES ({','.join('?' for _ in values)})",tuple(values.values()))


def json_text(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True)


def create_run(connection,registry,manifest,case_dir,run_id,input_sha):
    project_id = uid('project',str(case_dir),manifest.get('project_id',manifest.get('project_name','')))
    with connection:
        connection.execute('INSERT OR IGNORE INTO project(id,name,external_code,region_code,use_type,fire_category) VALUES(?,?,?,?,?,?)',
            (project_id,manifest.get('project_name','未确认工程'),manifest.get('project_code'),
             manifest.get('audit_context',{}).get('region_code'),manifest.get('audit_context',{}).get('use_type'),
             manifest.get('audit_context',{}).get('fire_category','unknown')))
        run_no = connection.execute('SELECT COALESCE(MAX(run_no),0)+1 FROM audit_run WHERE project_id=?',(project_id,)).fetchone()[0]
        insert(connection,'audit_run',{'id':run_id,'project_id':project_id,'bundle_id':registry.bundle_id,
            'run_no':run_no,'audit_stage':manifest.get('audit_context',{}).get('audit_stage','unknown'),
            'status':'running','input_sha256':input_sha,'config_sha256':registry.sha256,
            'context_snapshot_json':json_text(manifest),'coverage_snapshot_json':json_text(manifest.get('coverage_plan',[])),
            'engine_version':'1.0.0'})
        for label,value in manifest.items():
            if label in registry.labels and isinstance(value,(str,int,float)):
                insert(connection,'project_reference_value',{'id':uid('ref',run_id,label),'project_id':project_id,
                    'bundle_id':registry.bundle_id,'label_code':label,'raw_value':str(value),
                    'normalized_value':normalized(value),'source_type':'manifest','source_reference':str(case_dir/'manifest.json')})
    return project_id


def save_run(connection,registry,run_id,project_id,files,documents,result,model_stats):
    evidence_ids = {}
    candidate_evidence = {}
    scopes = []
    # Explicitly supplied coverage is also an auditable scope plan; not inferred completeness.
    for expected in result['coverage']:
        scope = {k:v for k,v in expected.items() if k!='tag'}
        sid = uid('scope',project_id,json_text(scope))
        if not any(x[0]==sid for x in scopes):
            scopes.append((sid,scope))
    with connection:
        for sid,scope in scopes:
            connection.execute('INSERT OR IGNORE INTO project_scope(id,project_id,kind,name,attributes_json) VALUES(?,?,?,?,?)',
                (sid,project_id,'location',scope.get('location',scope.get('unit_name','范围')),json_text(scope)))
        for file in files:
            insert(connection,'source_file',{'id':file['id'],'run_id':run_id,'relative_path':file['path'],
                'original_name':file['filename'],'storage_path':file['storage_path'],
                'mime_type':_mime(file['path']),'sha256':file['sha256'],'size_bytes':file['size_bytes'],
                'physical_page_count':file['page_count'],'parse_status':file['parse_status'],'parse_error_code':file['error_code']})
            for unit in file['units']:
                insert(connection,'markdown_unit',{'id':unit['id'],'run_id':run_id,'source_file_id':file['id'],
                    'unit_no':unit['unit_no'],'physical_page_no':unit['page_no'],'logical_locator':unit['logical_locator'],
                    'source_type':unit['source_type'],'markdown_path':unit['markdown_path'],'source_map_path':unit['source_map_path'],
                    'text_sha256':digest(unit['markdown']),'read_status':unit['read_status']})
                for fragment in unit['fragments']:
                    insert(connection,'source_fragment',{'id':fragment['fragment_id'],'markdown_unit_id':unit['id'],
                        'fragment_no':fragment['fragment_no'],'text':fragment['text'],'source':fragment['source'],
                        'bbox_json':json_text(fragment['bbox']),'table_id':fragment['table_id'],
                        'row_index':fragment['row_index'],'column_index':fragment['column_index'],'logical_locator':fragment['logical_locator']})
                    eid = uid('evidence',run_id,fragment['fragment_id'])
                    evidence_ids[fragment['fragment_id']] = eid
                    insert(connection,'evidence_span',{'id':eid,'run_id':run_id,'markdown_unit_id':unit['id'],
                        'fragment_id':fragment['fragment_id'],'quote_text':fragment['text'],
                        'grounding_status':'vision_transcription' if unit['source_type'] in ('ocr','image_ocr') else 'verified_text'})
        for document in documents:
            matching_scopes = [sid for sid,scope in scopes if scope and all(
                any(c['label']==k and c['normalized_value']==normalized(v) and c['validation_status']=='accepted'
                    and c['value_role']=='subject' for c in document['candidates']) for k,v in scope.items())]
            scope_id = matching_scopes[0] if len(matching_scopes)==1 else None
            insert(connection,'document_unit',{'id':document['id'],'run_id':run_id,'project_id':project_id,
                'source_file_id':document['file_id'],'bundle_id':registry.bundle_id,'unit_no':document['unit_no'],
                'tag_code':document['tag'],'tag_origin':document['tag_origin'],'tag_status':document['tag_status'],
                'identity_status':document['identity_status'],'scope_id':scope_id,
                'scope_status':'confirmed' if scope_id else 'unresolved',
                'classification_json':json_text({k:document.get(k) for k in ('title','title_fragment_id','uploaded_tag','identity_matches','identity_conflicts','extraction_error','rejected_candidates')})})
            for unit in document['units']:
                insert(connection,'document_markdown',{'document_unit_id':document['id'],'markdown_unit_id':unit['id'],
                    'source_file_id':document['file_id'],'run_id':run_id})
            selected = {}
            for c in document['candidates']:
                eid = evidence_ids[c['fragment_id']]
                candidate_evidence[c['id']] = eid
                insert(connection,'field_candidate',{'id':c['id'],'run_id':run_id,'source_file_id':c['file_id'],
                    'document_unit_id':document['id'],'markdown_unit_id':c['markdown_unit_id'],'bundle_id':registry.bundle_id,
                    'label_code':c['label'],'evidence_id':eid,'raw_value':c['raw_value'],'normalized_value':c['normalized_value'],
                    'value_unit':c['value_unit'],'source_label':c['source_label'],'value_role':c['value_role'],'source':c['source'],
                    'confidence':c['confidence'],'validation_status':c['validation_status'],'rejection_reason':c['rejection_reason']})
                if c['validation_status']=='accepted' and c['value_role']=='subject':
                    old = selected.get(c['label'])
                    if old is None or c['confidence']>old['confidence']:
                        selected[c['label']] = c
            for label,c in selected.items():
                insert(connection,'field_selection',{'document_unit_id':document['id'],'label_code':label,
                    'candidate_id':c['id'],'purpose':'display','rule_code':'','selection_reason':'highest_confidence_subject_display_only'})
        for e in result['evaluations']:
            insert(connection,'rule_evaluation',{'id':e['id'],'run_id':run_id,'bundle_id':registry.bundle_id,
                'rule_code':e['rule_code'],'scope_key':e['scope_key'],'applicability':e['applicability'],
                'result':e['result'],'reason_code':e['reason_code'],'details_json':json_text(e['details'])})
            for d in e['documents']:
                insert(connection,'rule_document',{'evaluation_id':e['id'],'document_unit_id':d['document_id'],
                    'run_id':run_id,'relation':d['relation'],'reason_code':e['reason_code']})
            for c in { (c['candidate_id'],c['relation']):c for c in e['candidates']}.values():
                insert(connection,'rule_candidate',{'evaluation_id':e['id'],'candidate_id':c['candidate_id'],
                    'run_id':run_id,'relation':c['relation']})
        documents_by_id = {d['id']:d for d in documents}
        for finding in result['findings']:
            insert(connection,'audit_finding',{'id':finding['id'],'run_id':run_id,'evaluation_id':finding['evaluation_id'],
                'finding_type':finding['finding_type'],'severity':finding['severity'],'status':'open',
                'title':finding['title'],'reason_code':finding['reason_code'],'suggestion':finding['suggestion'],
                'details_json':json_text({'details':finding['details'],'candidate_ids':finding['candidate_ids'],'document_ids':finding['document_ids']})})
            evidence = {candidate_evidence[c] for c in finding['candidate_ids'] if c in candidate_evidence}
            for did in finding['document_ids']:
                title_fragment = documents_by_id[did].get('title_fragment_id')
                if title_fragment in evidence_ids:
                    evidence.add(evidence_ids[title_fragment])
            finding['evidence_ids'] = sorted(evidence)
            for eid in evidence:
                insert(connection,'finding_evidence',{'finding_id':finding['id'],'evidence_id':eid,'run_id':run_id,'relation':'supports'})
        for i,call in enumerate(model_stats.get('calls',[])):
            insert(connection,'model_call',{'id':uid('call',run_id,i),'run_id':run_id,'purpose':call['purpose'],
                'model_name':call['model'],'prompt_sha256':call.get('prompt_sha256',digest(call['purpose'])),
                'input_sha256':call.get('input_sha256',digest(str(i))),'status':call.get('status','succeeded'),
                'latency_ms':round(call['elapsed_seconds']*1000),'usage_json':json_text(call['usage']),
                'error_code':call.get('error_code')})
        partial = any(f['parse_status']!='readable' for f in files) or any(d.get('extraction_error') for d in documents)
        connection.execute('UPDATE audit_run SET status=?,finished_at=? WHERE id=?',('partial' if partial else 'succeeded',now(),run_id))
    if connection.execute('PRAGMA foreign_key_check').fetchall():
        raise RuntimeError('持久化证据关系检查失败')
    return evidence_ids


def _mime(path):
    import mimetypes
    return mimetypes.guess_type(path)[0] or 'application/octet-stream'


def add_artifact(connection,run_id,path,kind,validation='passed'):
    from pathlib import Path
    path = Path(path)
    revision = connection.execute('SELECT COALESCE(MAX(revision_no),0)+1 FROM report_artifact WHERE run_id=? AND kind=?',(run_id,kind)).fetchone()[0]
    with connection:
        insert(connection,'report_artifact',{'id':uid('artifact',run_id,kind,revision),'run_id':run_id,'kind':kind,
            'revision_no':revision,'path':str(path.resolve()),'sha256':digest(path),'validation_status':validation})
