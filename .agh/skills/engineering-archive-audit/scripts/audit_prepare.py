"""Skill entry point for the versioned engineering audit core."""
import argparse
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
from app.pipeline import run_case

if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--case',required=True)
    parser.add_argument('--reference',help='给定参考 Markdown')
    parser.add_argument('--use-agnes',action='store_true')
    parser.add_argument('--word',action='store_true')
    args = parser.parse_args()
    case = Path(args.case)
    if not case.exists():
        case = ROOT/case
    result = run_case(case,reference=args.reference,use_agnes=args.use_agnes,word=args.word)
    print('run_id='+result['run_id'])
    print('report='+result['report'])
