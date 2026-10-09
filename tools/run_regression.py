"""Run stored cases against independent expected highlights (no model sees truth)."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.pipeline import run_case
from app.common import write_json


def check(expected,result):
    issues = []
    findings = result['findings']
    counts = result['summary']['finding_counts']
    missing = sorted(e['rule_code'] for e in result['evaluations'] if e['kind']=='presence' and e['result']=='fail')
    def compare(key,actual):
        if key in expected and expected[key]!=actual:
            issues.append({'key':key,'expected':expected[key],'actual':actual})
    compare('missing_rules',missing)
    compare('misfiled',result['summary']['misfiled_documents'])
    compare('field_conflicts',counts.get('field_conflict',0))
    compare('duplicate_groups',counts.get('duplicate',0))
    compare('coverage_gaps',counts.get('coverage_gap',0))
    compare('version_conflicts',counts.get('version_conflict',0))
    compare('contract_amount_conflicts',sum(f['reason_code']=='contract_amount_mismatch' for f in findings))
    if expected.get('fire_rules_unknown'):
        compare('fire_rules_unknown',all(e['result']=='not_evaluated' for e in result['evaluations'] if e['rule_code'] in ('FI-001','FI-002')))
    if expected.get('offline_unreadable_min') is not None and counts.get('unreadable',0)<expected['offline_unreadable_min']:
        issues.append({'key':'offline_unreadable_min','actual':counts.get('unreadable',0)})
    return issues


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root',default='cases/realistic')
    parser.add_argument('--out',default='tmp/regression-report.json')
    args = parser.parse_args()
    rows = []
    for case in sorted(Path(args.root).iterdir()):
        if not (case/'ground_truth.json').is_file():
            continue
        run = run_case(case,progress=lambda x:None)
        expected = json.loads((case/'ground_truth.json').read_text(encoding='utf-8'))
        result = json.loads((Path(run['run_dir'])/'audit-result.json').read_text(encoding='utf-8'))
        issues = check(expected,result)
        rows.append({'case':case.name,'run_id':run['run_id'],'passed':not issues,'issues':issues,'summary':result['summary']})
    write_json(args.out,{'mode':'offline','cases':rows,'passed':all(r['passed'] for r in rows) and bool(rows)})
    print(f"Regression cases: {sum(r['passed'] for r in rows)}/{len(rows)} passed")
    raise SystemExit(0 if rows and all(r['passed'] for r in rows) else 1)
