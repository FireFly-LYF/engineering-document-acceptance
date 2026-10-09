"""Engineering-domain rules. Identity, applicability and consistency are independent."""
from __future__ import annotations
from collections import defaultdict
from decimal import Decimal
from app.common import uid, normalized
from app.extraction import values, normalize_value
from app.registry import applicability


def identity(document, manifest):
    evidence = []
    matches, conflicts = set(),set()
    for key in ('project_name','project_code','owner','address'):
        expected = manifest.get(key)
        if not expected:
            continue
        candidates = values(document,key)
        if candidates:
            if any(c['normalized_value']==normalized(expected) for c in candidates):
                matches.add(key)
            if any(c['normalized_value']!=normalized(expected) for c in candidates):
                conflicts.add(key)
            evidence.extend(candidates)
    if ('project_name' in matches and len(matches)>=2) or ('project_code' in matches and (not conflicts or len(matches)>=2)):
        status = 'target_project'
    elif {'project_name','project_code'}.issubset(conflicts) and not {'project_name','project_code'}.intersection(matches):
        status = 'other_project'
    elif 'project_name' in conflicts and len(conflicts)>=2 and not matches:
        status = 'other_project'
    else:
        status = 'unresolved'
    document['identity_status'] = status
    document['identity_evidence'] = [c['id'] for c in evidence]
    document['identity_matches'] = sorted(matches)
    document['identity_conflicts'] = sorted(conflicts)
    return status


def evaluate(files,documents,manifest,registry,run_id):
    context = {**manifest.get('audit_context',{})}
    coverage = manifest.get('coverage_plan',[])
    for doc in documents:
        identity(doc,manifest)
    file_by_id = {f['id']:f for f in files}
    target = [d for d in documents if d['identity_status']=='target_project' and d['tag_status']=='verified']
    candidates_by_id = {c['id']:c for d in documents for c in d['candidates']}
    evaluations,findings = [],[]

    def issue(kind,title,reason,*,evaluation=None,candidates=None,docs=None,severity='warning',suggestion='人工复核原始资料并确认处理方式',details=None):
        candidate_ids = list(dict.fromkeys(candidates or []))
        docs = list(dict.fromkeys(docs or []))
        finding = {'id':uid('finding',run_id,kind,title,reason,len(findings)),
            'run_id':run_id,'evaluation_id':evaluation['id'] if evaluation else None,
            'finding_type':kind,'severity':severity,'status':'open','title':title,
            'reason_code':reason,'suggestion':suggestion,'candidate_ids':candidate_ids,
            'document_ids':docs,'details':details or {}}
        findings.append(finding)
        return finding

    def event(rule,scope,result,reason,*,app=None,docs=None,candidates=None,details=None):
        e = {'id':uid('evaluation',run_id,rule['rule_id'],scope),'rule_code':rule['rule_id'],
            'name':rule['name'],'kind':rule['kind'],'scope_key':scope,
            'applicability':app or 'applicable','result':result,'reason_code':reason,
            'documents':docs or [],'candidates':candidates or [],'details':details or {}}
        evaluations.append(e)
        return e

    for file in files:
        if file['parse_status']!='readable':
            issue('unreadable',f"资料读取不充分：{file['path']}",file['error_code'] or file['parse_status'],
                docs=[d['id'] for d in documents if d['file_id']==file['id']],
                details={'file_id':file['id'],'path':file['path'],'parse_status':file['parse_status']},
                suggestion='补充可读取文件或核对未识别页；不能将读取失败直接视为未提交')
    for doc in documents:
        if doc['identity_status']=='other_project':
            issue('misfiled',f"他项工程资料：{doc['file_name']}",'other_project_identity',
                candidates=doc['identity_evidence'],docs=[doc['id']],
                details={'matches':doc['identity_matches'],'conflicts':doc['identity_conflicts']},
                suggestion='核实资料归属，确认后调整本项目归档资料')
        if doc.get('uploaded_tag') and doc['uploaded_tag']!=doc['tag']:
            issue('content_gap',f"上传分类与正文不符：{doc['file_name']}",'upload_tag_mismatch',docs=[doc['id']],
                details={'uploaded_tag':doc['uploaded_tag'],'verified_tag':doc['tag']})
        if doc.get('extraction_error'):
            issue('content_gap',f"语义提取未完成：{doc['file_name']}",doc['extraction_error'],docs=[doc['id']],
                suggestion='当前保留本地候选；重新提取或人工复核复杂字段')

    for rule in registry.rules['rules']:
        conditions = {**registry.rules.get('source_conditions',{}).get(rule.get('basis_id'),{}),**rule.get('when',{})}
        app = applicability(conditions,context)
        if app!='applicable':
            e = event(rule,'project','not_applicable' if app=='not_applicable' else 'not_evaluated',
                'condition_not_met' if app=='not_applicable' else 'condition_unknown',app=app,
                details={'conditions':conditions,'context':context})
            if app=='unknown':
                issue('rule_gap',f"适用条件未确认：{rule['name']}",'condition_unknown',
                    evaluation=e,severity='info',suggestion='确认项目阶段、消防类别、委托监理或应交范围后重新核查',
                    details={'rule_code':rule['rule_id'],'conditions':conditions})
            continue
        kind = rule['kind']
        if kind=='presence':
            accepted = [d for d in target if d['tag'] in rule['accepted_tags'] and file_by_id[d['file_id']]['parse_status']=='readable']
            similar = [d for d in target if d['tag'] in rule.get('excluded_tags',[])]
            uncertain = [d for d in documents if
                (d['tag'] in rule['accepted_tags'] and (d['identity_status']=='unresolved' or file_by_id[d['file_id']]['parse_status']!='readable'))
                or (d['tag']=='UNKNOWN' and d['identity_status']!='other_project')]
            relations = [{'document_id':d['id'],'relation':'accepted'} for d in accepted]
            relations += [{'document_id':d['id'],'relation':'similar'} for d in similar]
            relations += [{'document_id':d['id'],'relation':'needs_review'} for d in uncertain]
            selected = [c['id'] for d in accepted for c in d['candidates'] if c['validation_status']=='accepted']
            result = 'pass' if accepted else 'needs_review' if uncertain else 'fail'
            e = event(rule,'project',result,'document_present' if accepted else 'unreadable_or_unconfirmed_candidate' if uncertain else 'required_document_missing',
                docs=relations,candidates=[{'candidate_id':c,'relation':'selected'} for c in selected],
                details={'accepted_files':[d['file_name'] for d in accepted],'similar_files':[d['file_name'] for d in similar],
                    'coverage_level':'document_type_only'})
            if result=='fail':
                issue('missing',f"缺少《{rule['name']}》",'required_document_missing',evaluation=e,severity='error',
                    docs=[d['id'] for d in similar],suggestion=f"补充本项目《{rule['name']}》；相似资料不能自动替代",
                    details={'rule_code':rule['rule_id'],'similar_files':[d['file_name'] for d in similar]})
            elif result=='needs_review':
                issue('content_gap',f"尚不能确认《{rule['name']}》已提供",'unreadable_or_unconfirmed_candidate',evaluation=e,
                    docs=[d['id'] for d in uncertain],suggestion='核对类型、归属和读取覆盖；暂不作确定缺件判定')
        elif kind=='identity':
            for doc in documents:
                state = doc['identity_status']
                event(rule,doc['id'],'pass' if state=='target_project' else 'fail' if state=='other_project' else 'needs_review',
                    state,docs=[{'document_id':doc['id'],'relation':'accepted' if state=='target_project' else 'rejected' if state=='other_project' else 'needs_review'}],
                    candidates=[{'candidate_id':c,'relation':'reference'} for c in doc['identity_evidence']],
                    details={'matched_identity_fields':doc['identity_matches'],'conflicting_identity_fields':doc['identity_conflicts']})
        elif kind=='consistency' and rule['comparison_scope']=='project':
            for label in rule['labels']:
                pool = [c for d in target for c in values(d,label)]
                expected,error = normalize_value(manifest.get(label,''),registry.labels[label])
                unique = {c['normalized_value'] for c in pool}
                conflicting = [c for c in pool if expected and c['normalized_value']!=expected]
                result = 'fail' if conflicting or len(unique)>1 else 'pass' if pool else 'needs_review'
                e = event(rule,'project:'+label,result,'field_mismatch' if result=='fail' else 'consistent' if result=='pass' else 'no_grounded_value',
                    candidates=[{'candidate_id':c['id'],'relation':'conflicting' if c in conflicting else 'selected'} for c in pool],
                    details={'label':label,'expected':expected,'values':sorted(unique)})
                if result=='fail':
                    issue('field_conflict',f"{registry.labels[label]['label']}不一致",'field_mismatch',evaluation=e,
                        candidates=[c['id'] for c in pool],details={'label':label,'expected':expected,'values':sorted(unique)})
        elif kind=='consistency' and rule['comparison_scope']=='contract':
            groups = defaultdict(list)
            unresolved = []
            for doc in target:
                amounts = values(doc,'contract_amount')
                if not amounts:
                    continue
                contracts = {c['normalized_value'] for c in values(doc,'contract_no')}
                if len(contracts)==1:
                    groups[next(iter(contracts))].extend(amounts)
                else:
                    unresolved.extend(amounts)
            if not groups:
                event(rule,'contract:unknown','needs_review','contract_scope_unknown',
                    candidates=[{'candidate_id':c['id'],'relation':'reference'} for c in unresolved])
            for number,pool in groups.items():
                unique = {Decimal(c['normalized_value']) for c in pool}
                expected = manifest.get('contract_amount') if normalized(manifest.get('contract_no',''))==number else None
                canonical,_ = normalize_value(expected,registry.labels['contract_amount']) if expected is not None else (None,None)
                bad = [c for c in pool if canonical and Decimal(c['normalized_value'])!=Decimal(canonical)]
                fail = len(unique)>1 or bool(bad)
                e = event(rule,'contract:'+number,'fail' if fail else 'pass','contract_amount_mismatch' if fail else 'consistent',
                    candidates=[{'candidate_id':c['id'],'relation':'conflicting' if fail else 'selected'} for c in pool],
                    details={'contract_no':number,'expected':canonical,'values':sorted(map(str,unique))})
                if fail:
                    issue('field_conflict','同一施工合同原始合同金额不一致','contract_amount_mismatch',evaluation=e,
                        candidates=[c['id'] for c in pool],details=e['details'])
            if unresolved:
                issue('content_gap','合同金额比较范围未确认','contract_scope_unknown',
                    candidates=[c['id'] for c in unresolved],suggestion='补充合同编号或确认关联；不将结算和调整金额混入原始合同额')
        elif kind=='chronology':
            any_event = False
            for doc in target:
                starts,finishes = values(doc,'start_date'),values(doc,'finish_date')
                if not starts or not finishes:
                    continue
                any_event = True
                unit_names = {c['normalized_value'] for c in values(doc,'unit_name')}
                if len(unit_names)>1:
                    event(rule,doc['id'],'needs_review','multiple_unit_date_scope',
                        candidates=[{'candidate_id':c['id'],'relation':'reference'} for c in starts+finishes])
                    continue
                bad = [(a,b) for a in starts for b in finishes if a['normalized_value']>b['normalized_value']]
                pool = starts+finishes
                e = event(rule,doc['id'],'fail' if bad else 'pass','date_order_invalid' if bad else 'date_order_valid',
                    candidates=[{'candidate_id':c['id'],'relation':'conflicting' if bad else 'selected'} for c in pool])
                if bad:
                    issue('field_conflict',f"开工日期晚于竣工日期：{doc['file_name']}",'date_order_invalid',evaluation=e,candidates=[c['id'] for c in pool])
            if not any_event:
                event(rule,'project','needs_review','date_evidence_insufficient')
        elif kind=='duplicate':
            duplicate_groups = defaultdict(list)
            for file in files:
                duplicate_groups[file['sha256']].append(file)
            duplicate_file_ids = set()
            for sha,group in duplicate_groups.items():
                if len(group)<2:
                    continue
                duplicate_file_ids.update(f['id'] for f in group)
                docs = [d for d in documents if d['file_id'] in {f['id'] for f in group}]
                e = event(rule,'sha:'+sha,'fail','identical_file_hash',docs=[{'document_id':d['id'],'relation':'rejected'} for d in docs])
                issue('duplicate','完全相同文件重复上传','identical_file_hash',evaluation=e,docs=[d['id'] for d in docs],
                    details={'files':[f['path'] for f in group]},suggestion='确认重复关系后保留有效归档版本')
            by_number = defaultdict(list)
            for doc in target:
                for c in values(doc,'document_no'):
                    by_number[(doc['tag'],c['normalized_value'])].append(doc)
            for (tag,number),group in by_number.items():
                group = list({d['id']:d for d in group}.values())
                if len(group)<2 or all(d['file_id'] in duplicate_file_ids for d in group):
                    continue
                texts = {normalized('\n'.join(u['plain_text'] for u in d['units'])) for d in group}
                kind = 'duplicate' if len(texts)==1 else 'version_conflict'
                pool = [c['id'] for d in group for c in values(d,'document_no')]
                e = event(rule,'number:'+tag+':'+number,'fail','same_record_duplicate' if kind=='duplicate' else 'same_number_different_content',
                    candidates=[{'candidate_id':c,'relation':'conflicting'} for c in pool])
                issue(kind,f"同编号资料{'重复' if kind=='duplicate' else '内容或版本不同'}：{number}",e['reason_code'],evaluation=e,
                    candidates=pool,docs=[d['id'] for d in group],details={'files':[d['file_name'] for d in group]},
                    suggestion='核对版本、签署和有效范围，不能只凭编号相同删除')
            if not any(e['rule_code']==rule['rule_id'] for e in evaluations):
                event(rule,'project','pass','no_duplicate_detected')
        elif kind=='coverage':
            if not coverage:
                event(rule,'project','needs_review','coverage_plan_empty')
                issue('rule_gap','应交范围计划为空','coverage_plan_empty',severity='info')
                continue
            for n,expected in enumerate(coverage):
                matches = []
                for doc in target:
                    if doc['tag']!=expected.get('tag'):
                        continue
                    if all(any(c['normalized_value']==normalized(v) for c in values(doc,k))
                           for k,v in expected.items() if k!='tag'):
                        matches.append(doc)
                uncertain = [d for d in documents if d['tag']==expected.get('tag') and d['identity_status']!='other_project'
                    and (d['identity_status']=='unresolved' or file_by_id[d['file_id']]['parse_status']!='readable')]
                result_state = 'pass' if matches else 'needs_review' if uncertain else 'fail'
                e = event(rule,f'coverage:{n}',result_state,'scope_covered' if matches else 'scope_unreadable' if uncertain else 'required_scope_missing',
                    docs=[{'document_id':d['id'],'relation':'accepted'} for d in matches],details={'expected':expected})
                if result_state=='fail':
                    issue('coverage_gap','施工记录未覆盖应交范围','required_scope_missing',evaluation=e,severity='error',
                        details={'expected':expected},suggestion='补充该楼栋、专业和部位的资料，不能由其他部位记录替代')
        elif kind=='content':
            candidates = [c for d in target if d['tag'] in rule['accepted_tags'] for c in values(d,'conclusion')]
            flagged = [c for c in candidates if any(term in c['raw_value'] for term in rule['review_terms'])]
            e = event(rule,'project','needs_review' if flagged or not candidates else 'pass',
                'conclusion_requires_review' if flagged else 'no_conclusion_evidence' if not candidates else 'no_adverse_text_detected',
                candidates=[{'candidate_id':c['id'],'relation':'conflicting' if c in flagged else 'selected'} for c in candidates])
            if flagged:
                issue('content_gap','文载结论或整改内容需要复核','conclusion_requires_review',evaluation=e,
                    candidates=[c['id'] for c in flagged],suggestion='核对不合格、整改与复查记录；资料存在不等于文载结论符合要求')
    if registry.rules.get('status')!='approved':
        issue('rule_gap','规则尚未形成项目所在地完整归档目录','profile_not_locally_approved',severity='info',
            suggestion='确认地区、适用版本和完整应交清单；本次仅对已配置规则作资料核查')
    summary = {'files':len(files),'documents':len(documents),'target_documents':len(target),
        'misfiled_documents':sum(d['identity_status']=='other_project' for d in documents),
        'unresolved_documents':sum(d['identity_status']=='unresolved' for d in documents),
        'evaluation_counts':dict(_counts(evaluations,'result')),'finding_counts':dict(_counts(findings,'finding_type')),
        'coverage_level':'configured_scope' if context.get('coverage_plan_confirmed') is True and coverage else 'document_type_only',
        'overall':'issues_found' if any(e['result']=='fail' for e in evaluations) else 'needs_review' if any(e['result'] in ('needs_review','not_evaluated') for e in evaluations) else 'configured_checks_passed',
        'legal_acceptance_decision':False}
    return {'evaluations':evaluations,'findings':findings,'summary':summary,'context':context,'coverage':coverage}


def _counts(items,key):
    counts = defaultdict(int)
    for item in items:
        counts[item[key]]+=1
    return counts
