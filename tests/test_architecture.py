import json
import sqlite3
import pytest
from app.registry import Registry, applicability, read_yaml, ROOT
from app.storage import open_database


@pytest.fixture
def db(tmp_path):
    conn = open_database(tmp_path / 'test.sqlite')
    reg = Registry()
    conn.execute("INSERT INTO project(id,name) VALUES('p1','项目一')")
    conn.execute("INSERT INTO project(id,name) VALUES('p2','项目二')")
    for run_id, project_id in [('r1','p1'),('r2','p2')]:
        conn.execute('INSERT INTO audit_run(id,project_id,bundle_id,run_no,audit_stage,status,input_sha256,config_sha256,context_snapshot_json,coverage_snapshot_json,engine_version) VALUES(?,?,?,1,?,?,?,?,?,?,?)',
            (run_id, project_id, reg.bundle_id, 'post_acceptance','running','a'*64,reg.sha256,'{}','{}','1.0.0'))
        conn.execute('INSERT INTO source_file(id,run_id,relative_path,original_name,storage_path,mime_type,sha256,size_bytes,parse_status) VALUES(?,?,?,?,?,?,?,?,?)',
            ('f'+run_id, run_id,'合同.pdf','合同.pdf','copies/'+run_id+'.pdf','application/pdf','b'*64,100,'readable'))
        conn.execute('INSERT INTO document_unit(id,run_id,project_id,source_file_id,bundle_id,unit_no,tag_code,tag_origin,tag_status,identity_status,scope_status,classification_json) VALUES(?,?,?,?,?,1,?,?,?,?,?,?)',
            ('d'+run_id,run_id,project_id,'f'+run_id,reg.bundle_id,'CONSTRUCTION_CONTRACT','title_rule','verified','target_project','unresolved','{}'))
        conn.execute('INSERT INTO markdown_unit(id,run_id,source_file_id,unit_no,physical_page_no,source_type,markdown_path,source_map_path,text_sha256,read_status) VALUES(?,?,?,1,3,?,?,?,?,?)',
            ('m'+run_id,run_id,'f'+run_id,'native_pdf','unit_001.md','unit_001.source_map.json','c'*64,'readable'))
        conn.execute('INSERT INTO document_markdown VALUES(?,?,?,?)', ('d'+run_id,'m'+run_id,'f'+run_id,run_id))
        conn.execute('INSERT INTO evidence_span(id,run_id,markdown_unit_id,quote_text,grounding_status) VALUES(?,?,?,?,?)',
            ('e'+run_id,run_id,'m'+run_id,'合同金额：8650万元','verified_text'))
    conn.commit()
    yield conn
    conn.close()


def candidate(conn, *, markdown='mr1', evidence='er1', label='contract_amount', confidence=0.9):
    reg = Registry()
    conn.execute('INSERT INTO field_candidate(id,run_id,source_file_id,document_unit_id,markdown_unit_id,bundle_id,label_code,evidence_id,raw_value,value_role,source,confidence,validation_status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
        ('c1','r1','fr1','dr1',markdown,reg.bundle_id,label,evidence,'8650万元','subject','native_rule',confidence,'accepted'))


def test_catalog_and_bindings_are_explicit():
    reg = Registry()
    assert 'contract_amount' in reg.labels_for_tag('CONSTRUCTION_CONTRACT')
    assert 'settlement_amount' != 'contract_amount'
    assert 'FIRE_FILING_RECEIPT' not in reg.rules['rules'][7]['accepted_tags']
    assert set(reg.tags) == set(reg.bindings['bindings'])


def test_fire_unknown_is_not_missing_or_inapplicable():
    assert applicability({'fire_category':'special'}, {}) == 'unknown'
    assert applicability({'fire_category':'special'}, {'fire_category':'other'}) == 'not_applicable'
    assert applicability({'fire_category':'special'}, {'fire_category':'special'}) == 'applicable'


def test_missing_supervision_condition_stays_unknown():
    assert applicability({'supervision_entrusted':True}, {}) == 'unknown'
    assert applicability({'supervision_entrusted':True}, {'supervision_entrusted':False}) == 'not_applicable'


def test_unknown_evaluation_cannot_pass(db):
    reg = Registry()
    with pytest.raises(sqlite3.IntegrityError):
        db.execute('INSERT INTO rule_evaluation VALUES(?,?,?,?,?,?,?,?,?)',
            ('ev1','r1',reg.bundle_id,'FI-001','project','unknown','pass','invalid','{}'))


def test_candidate_must_use_same_run_and_file(db):
    with pytest.raises(sqlite3.IntegrityError):
        candidate(db, markdown='mr2', evidence='er2')


def test_candidate_must_use_same_markdown_evidence(db):
    with pytest.raises(sqlite3.IntegrityError):
        candidate(db, evidence='er2')


def test_unknown_label_is_rejected(db):
    with pytest.raises(sqlite3.IntegrityError):
        candidate(db, label='arbitrary_llm_label')


def test_confidence_range_is_enforced(db):
    with pytest.raises(sqlite3.IntegrityError):
        candidate(db, confidence=1.5)


def test_same_hash_different_paths_can_record_duplicate(db):
    db.execute('INSERT INTO source_file(id,run_id,relative_path,original_name,storage_path,mime_type,sha256,size_bytes,parse_status) VALUES(?,?,?,?,?,?,?,?,?)',
        ('f_copy','r1','03-施工/合同副本.pdf','合同副本.pdf','copies/copy.pdf','application/pdf','b'*64,100,'readable'))
    assert db.execute('SELECT count(*) FROM source_file WHERE run_id=? AND sha256=?', ('r1','b'*64)).fetchone()[0] == 2


def test_selection_cannot_point_to_other_label(db):
    candidate(db)
    with pytest.raises(sqlite3.IntegrityError):
        db.execute('INSERT INTO field_selection VALUES(?,?,?,?,?,?)', ('dr1','settlement_amount','c1','display','','invalid'))


def test_duplicate_yaml_key_rejected(tmp_path):
    path = tmp_path / 'bad.yaml'
    path.write_text('fields:\n  project_code: 1\n  project_code: 2\n', encoding='utf-8')
    with pytest.raises(ValueError, match='重复键'):
        read_yaml(path)


def test_install_is_idempotent(db):
    Registry().install(db)
    Registry().install(db)
    assert db.execute('SELECT count(*) FROM registry_bundle').fetchone()[0] == 1
    assert db.execute('PRAGMA foreign_key_check').fetchall() == []


def test_document_cannot_use_another_projects_scope(db):
    db.execute("INSERT INTO project_scope VALUES('scope2','p2',NULL,'unit','2号楼','{}')")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("UPDATE document_unit SET scope_id='scope2',scope_status='confirmed' WHERE id='dr1'")


def test_finding_cannot_use_another_runs_evidence(db):
    db.execute("INSERT INTO audit_finding VALUES('finding1','r1',NULL,'field_conflict','warning','open','金额冲突','amount_mismatch','复核','{}')")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO finding_evidence VALUES('finding1','er2','r1','supports')")


def test_word_excel_do_not_require_invented_page_numbers(db):
    db.execute('INSERT INTO markdown_unit(id,run_id,source_file_id,unit_no,physical_page_no,logical_locator,source_type,markdown_path,source_map_path,text_sha256,read_status) VALUES(?,?,?,2,NULL,?,?,?,?,?,?)',
        ('logical1','r1','fr1','sheet=第二工作表;cell=A3','native_excel','unit_002.md','unit_002.source_map.json','d'*64,'readable'))
    assert db.execute("SELECT physical_page_no FROM markdown_unit WHERE id='logical1'").fetchone()[0] is None
