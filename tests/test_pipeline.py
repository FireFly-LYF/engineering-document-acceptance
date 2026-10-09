"""Business regressions on realistic synthetic files; never pass truth to the extractor."""
import json
import sqlite3
from pathlib import Path
import pytest
import pymupdf
from app.pipeline import run_case
from app.ingestion import parse_file
from app.registry import Registry
from app.extraction import ground_model_candidate,normalize_value
from app.reporting import validate_statement
from app.review import review
from tools.generate_realistic_cases import build


@pytest.fixture(scope='module')
def cases(tmp_path_factory):
    root = tmp_path_factory.mktemp('realistic')
    build(root)
    return root


@pytest.fixture(scope='module')
def runs(cases):
    return {name:run_case(cases/name,progress=lambda x:None) for name in
        ('school-issues','school-complete','residential-coverage','versions-and-office','scans-and-unreadable')}


def result(runs,name):
    return json.loads((Path(runs[name]['run_dir'])/'audit-result.json').read_text(encoding='utf-8'))


def test_formal_report_cannot_be_replaced_by_pre_acceptance(runs):
    report = result(runs,'school-issues')
    missing = {e['rule_code'] for e in report['evaluations'] if e['kind']=='presence' and e['result']=='fail'}
    assert missing == {'AC-001','FI-001'}


def test_planning_and_filing_do_not_replace_special_fire_opinion(runs):
    report = result(runs,'school-issues')
    fire = next(e for e in report['evaluations'] if e['rule_code']=='FI-001')
    assert fire['result']=='fail'


def test_misfiled_documents_detected_without_filename_hints(runs):
    report = result(runs,'school-issues')
    assert report['summary']['misfiled_documents']==2
    assert sum(f['finding_type']=='misfiled' for f in report['findings'])==2


def test_wrong_subject_code_is_not_hidden_by_correct_attachment_reference(runs):
    report = result(runs,'school-issues')
    assert any(f['reason_code']=='field_mismatch' for f in report['findings'])
    candidates = json.loads((Path(runs['school-issues']['run_dir'])/'candidates.json').read_text(encoding='utf-8'))
    supervision = next(d for d in candidates['documents'] if d['tag']=='SUPERVISION_QUALITY_REPORT')
    assert supervision['identity_status']=='target_project'
    assert any(c['value_role']=='reference' for c in supervision['candidates'] if c['label']=='project_code')


def test_original_contract_amount_conflict_is_detected(runs):
    report = result(runs,'school-issues')
    assert sum(f['reason_code']=='contract_amount_mismatch' for f in report['findings'])==1


def test_third_page_value_has_physical_source(runs):
    db = sqlite3.connect(runs['school-issues']['database'])
    row = db.execute("SELECT c.normalized_value,m.physical_page_no FROM field_candidate c JOIN markdown_unit m ON c.markdown_unit_id=m.id JOIN document_unit d ON d.id=c.document_unit_id WHERE d.tag_code='CONSTRUCTION_CONTRACT' AND c.label_code='contract_amount' AND c.normalized_value='86500000'").fetchone()
    assert row == ('86500000',3)
    db.close()


def test_exact_duplicate_is_one_group(runs):
    report = result(runs,'school-issues')
    assert sum(f['finding_type']=='duplicate' for f in report['findings'])==1


def test_clean_pack_passes_configured_presence_but_never_legal_acceptance(runs):
    report = result(runs,'school-complete')
    assert not any(f['finding_type']=='missing' for f in report['findings'])
    assert report['summary']['legal_acceptance_decision'] is False
    assert any(f['reason_code']=='profile_not_locally_approved' for f in report['findings'])


def test_coverage_gap_is_not_masked_by_one_present_record(runs):
    report = result(runs,'residential-coverage')
    gaps = [f for f in report['findings'] if f['finding_type']=='coverage_gap']
    assert len(gaps)==1
    assert gaps[0]['details']['expected']['unit_name']=='2号楼'
    assert not any(f['finding_type']=='missing' for f in report['findings'])


def test_revised_and_settlement_prices_do_not_create_original_price_conflict(runs):
    report = result(runs,'versions-and-office')
    assert not any(f['reason_code']=='contract_amount_mismatch' for f in report['findings'])
    assert sum(f['finding_type']=='version_conflict' for f in report['findings'])==1


def test_second_excel_sheet_and_word_have_logical_sources(runs):
    db = sqlite3.connect(runs['versions-and-office']['database'])
    rows = db.execute("SELECT logical_locator,physical_page_no FROM markdown_unit WHERE source_type IN ('native_excel','native_word')").fetchall()
    assert ('sheet:竣工目录',None) in rows
    assert ('document',None) in rows
    db.close()


def test_scan_generation_really_has_no_text_layer(cases):
    with pymupdf.open(cases/'scans-and-unreadable/files/04-检测/扫描报告.pdf') as doc:
        assert not doc[0].get_text().strip()
        assert doc[0].get_images()


def test_mixed_pdf_page_requires_ocr_and_does_not_disappear(cases):
    pages,error,count = parse_file(cases/'scans-and-unreadable/files/03-施工/混合记录.pdf')
    assert count==2 and len(pages)==2
    assert pages[0]['source_type']=='native_pdf'
    assert pages[1]['read_status']=='unreadable'
    assert pages[1]['error_code']=='ocr_not_configured'


def test_unknown_fire_context_does_not_pass(runs):
    report = result(runs,'scans-and-unreadable')
    assert all(e['result']=='not_evaluated' for e in report['evaluations'] if e['rule_code'] in ('FI-001','FI-002'))
    assert report['summary']['finding_counts']['unreadable']>=3


def test_binder_splits_two_logical_documents(runs):
    candidates = json.loads((Path(runs['scans-and-unreadable']['run_dir'])/'candidates.json').read_text(encoding='utf-8'))
    docs = [d for d in candidates['documents'] if d['file_name'].endswith('合订报告.pdf')]
    assert {d['tag'] for d in docs}=={'DESIGN_QUALITY_REPORT','SURVEY_QUALITY_REPORT'}


def test_money_units_are_compared_with_decimal():
    definition = Registry().labels['contract_amount']
    assert normalize_value('8650万元',definition)[0]=='86500000'
    assert normalize_value('86500000元',definition)[0]=='86500000'
    assert normalize_value('8650 USD',definition)[1]


def test_fabricated_candidate_and_wrong_page_rejected():
    registry = Registry()
    document = {'id':'d','file_id':'f','tag':'CONSTRUCTION_CONTRACT','units':[{
        'id':'m','unit_no':1,'page_no':3,'source_type':'native_pdf','fragments':[
            {'fragment_id':'frag','text':'合同金额：8650万元'}]}]}
    raw = {'value':'9200万元','unit_no':1,'page':3,'source_label':'合同金额','evidence':'合同金额：8650万元'}
    assert ground_model_candidate(document,'contract_amount',raw,registry)[1]=='not_grounded'
    raw.update(value='8650万元',page=1)
    assert ground_model_candidate(document,'contract_amount',raw,registry)[1]=='invalid_unit_or_empty_evidence'


def test_unknown_model_label_rejected():
    assert ground_model_candidate({'tag':'UNKNOWN'},'guessed_field',{},Registry())[1]=='unknown_field'


def test_model_numeric_substring_is_not_a_real_source_value():
    from app.extraction import source_span
    assert source_span('8650','合同金额：18650万元') is None
    assert source_span('A-01','编号：XA-012') is None
    assert source_span('8650万元','合同金额：８６５０万元')=='８６５０万元'


def test_two_cell_office_row_is_supported():
    from app.extraction import extract_native
    document = {'id':'d','file_id':'f','tag':'CONSTRUCTION_CONTRACT','units':[{'id':'m','unit_no':1,'page_no':None,
        'source_type':'native_word','fragments':[{'fragment_id':'frag','text':'合同金额（万元） | 8650'}]}]}
    candidates = extract_native(document,Registry())
    assert any(c['normalized_value']=='86500000' for c in candidates)


def test_model_cannot_drop_visible_money_unit():
    document = {'id':'d','file_id':'f','tag':'CONSTRUCTION_CONTRACT','units':[{
        'id':'m','unit_no':1,'page_no':3,'source_type':'native_pdf','fragments':[
            {'fragment_id':'frag','text':'合同金额：8650万元'}]}]}
    raw = {'value':'8650','unit_no':1,'page':3,'source_label':'合同金额','evidence':'合同金额：8650万元','value_role':'subject'}
    candidate,error = ground_model_candidate(document,'contract_amount',raw,Registry())
    assert error is None and candidate['normalized_value']=='86500000'


def test_reference_cue_overrides_incorrect_model_subject_role():
    document = {'id':'d','file_id':'f','tag':'SUPERVISION_QUALITY_REPORT','units':[{
        'id':'m','unit_no':1,'page_no':1,'source_type':'native_pdf','fragments':[
            {'fragment_id':'frag','text':'附件引用 项目编号：CC-018'}]}]}
    raw = {'value':'CC-018','unit_no':1,'page':1,'source_label':'项目编号','evidence':'附件引用 项目编号：CC-018','value_role':'subject'}
    candidate,error = ground_model_candidate(document,'project_code',raw,Registry())
    assert candidate['value_role']=='reference'


def test_body_reference_to_report_title_does_not_verify_document_type():
    from app.ingestion import classify_title
    unit = {'fragments':[{'fragment_id':'f','text':'请提供工程竣工验收报告'}]}
    assert classify_title(unit,Registry())[0]=='UNKNOWN'


def test_two_projects_can_share_owner_without_being_merged():
    from app.audit import identity
    from app.extraction import extract_native
    from tools.generate_realistic_cases import PROJECT
    document = {'id':'d','file_id':'f','tag':'CONSTRUCTION_CONTRACT','units':[{
        'id':'m','unit_no':1,'page_no':1,'source_type':'native_pdf','fragments':[
            {'fragment_id':'a','text':'工程名称：另一工程'},
            {'fragment_id':'b','text':'项目编号：OTHER-001'},
            {'fragment_id':'c','text':'建设单位：'+PROJECT['owner']}]}]}
    document['candidates'] = extract_native(document,Registry())
    assert identity(document,PROJECT)=='other_project'


def test_project_name_typo_does_not_remove_document_from_target_comparison():
    from app.audit import identity
    from app.extraction import extract_native
    from tools.generate_realistic_cases import PROJECT
    document = {'id':'d','file_id':'f','tag':'CONSTRUCTION_CONTRACT','units':[{
        'id':'m','unit_no':1,'page_no':1,'source_type':'native_pdf','fragments':[
            {'fragment_id':'a','text':'工程名称：澄川学校错别字'},
            {'fragment_id':'b','text':'项目编号：'+PROJECT['project_code']},
            {'fragment_id':'c','text':'建设单位：'+PROJECT['owner']},
            {'fragment_id':'d','text':'建设地点：'+PROJECT['address']}]}]}
    document['candidates'] = extract_native(document,Registry())
    assert identity(document,PROJECT)=='target_project'
    assert 'project_name' in document['identity_conflicts']


def test_statement_count_tampering_rejected(runs):
    folder = Path(runs['school-issues']['run_dir'])
    facts = json.loads((folder/'statement-facts.json').read_text(encoding='utf-8'))
    body = (folder/'正文.md').read_text(encoding='utf-8')
    assert validate_statement(body,facts)['passed']
    assert not validate_statement(body.replace('共接收文件','共接收文件999'),facts)['passed']


def test_review_decision_preserves_before_after_and_requires_evidence(runs):
    conn = sqlite3.connect(runs['school-issues']['database'])
    conn.execute('PRAGMA foreign_keys=ON')
    row = conn.execute("SELECT id FROM audit_finding WHERE finding_type='field_conflict' LIMIT 1").fetchone()
    with pytest.raises(ValueError):
        review(conn,runs['school-issues']['run_id'],row[0],'dismiss','已核实','test_reviewer')
    decision = review(conn,runs['school-issues']['run_id'],row[0],'request_more','请补充原合同','test_reviewer')
    saved = conn.execute('SELECT before_json,after_json FROM review_decision WHERE id=?',(decision,)).fetchone()
    assert json.loads(saved[0])['status']=='open'
    assert json.loads(saved[1])['status']=='disputed'
    conn.close()


def test_each_run_has_no_cross_run_fk_violations(runs):
    for run in runs.values():
        conn = sqlite3.connect(run['database'])
        assert conn.execute('PRAGMA foreign_key_check').fetchall()==[]
        conn.close()


def test_manifest_boolean_conditions_are_not_coerced():
    from app.pipeline import validate_manifest
    with pytest.raises(ValueError,match='true/false'):
        validate_manifest({'audit_context':{'coverage_plan_confirmed':'false'}},Registry())


def test_negative_conclusion_is_reviewed_not_accepted_as_quality_pass():
    from app.audit import evaluate
    from tools.generate_realistic_cases import PROJECT
    from app.extraction import extract_native
    doc = {'id':'d','file_id':'f','file_name':'行政意见.pdf','tag':'FIRE_ACCEPTANCE_OPINION','tag_status':'verified',
        'candidates':[],'units':[{'id':'m','unit_no':1,'page_no':1,'source_type':'native_pdf','fragments':[
            {'fragment_id':'a','text':'工程名称：'+PROJECT['project_name']},
            {'fragment_id':'b','text':'项目编号：'+PROJECT['project_code']},
            {'fragment_id':'c','text':'验收结论：不合格，整改后申请复查'}]}]}
    reg = Registry()
    doc['candidates'] = extract_native(doc,reg)
    report = evaluate([{'id':'f','sha256':'abc','parse_status':'readable','path':'行政意见.pdf'}],[doc],PROJECT,reg,'run')
    assert any(f['reason_code']=='conclusion_requires_review' for f in report['findings'])
