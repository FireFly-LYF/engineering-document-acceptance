"""Append review decisions; candidates and source files are never overwritten."""
import uuid
from app.persistence import insert,json_text


def review(connection,run_id,finding_id,decision,reason,reviewer,evidence_ids=()):
    if decision not in ('confirm','dismiss','request_more'):
        raise ValueError('支持 confirm/dismiss/request_more；字段更正应提交带来源的新资料并重新核查')
    if not reason.strip() or not reviewer.strip():
        raise ValueError('必须提供复核人标识和具体理由')
    row = connection.execute('SELECT status FROM audit_finding WHERE id=? AND run_id=?',(finding_id,run_id)).fetchone()
    if row is None:
        raise ValueError('未找到本次运行的问题')
    if decision=='dismiss' and not evidence_ids:
        raise ValueError('驳回问题必须引用同次运行的证据')
    status = 'resolved' if decision=='dismiss' else 'disputed' if decision=='request_more' else 'open'
    decision_id = 'review_'+uuid.uuid4().hex[:24]
    with connection:
        insert(connection,'review_decision',{'id':decision_id,'run_id':run_id,'finding_id':finding_id,
            'decision':decision,'reviewer_ref':reviewer,'reason':reason,'evidence_ids_json':json_text(list(evidence_ids)),
            'before_json':json_text({'status':row[0]}),'after_json':json_text({'status':status})})
        for eid in evidence_ids:
            insert(connection,'review_evidence',{'decision_id':decision_id,'evidence_id':eid,'run_id':run_id})
        connection.execute('UPDATE audit_finding SET status=? WHERE id=?',(status,finding_id))
    return decision_id
