import argparse
import json
from app.pipeline import run_case
from app.storage import open_database


def main():
    parser = argparse.ArgumentParser(description='工程竣工资料核查')
    commands = parser.add_subparsers(dest='command',required=True)
    run = commands.add_parser('run')
    run.add_argument('--case',required=True)
    run.add_argument('--reference')
    run.add_argument('--use-agnes',action='store_true',help='调用配置的 Agnes OCR、字段提取和正文说明')
    run.add_argument('--word',action='store_true')
    run.add_argument('--db')
    rev = commands.add_parser('review')
    for name in ('db','run','finding','decision','reason','reviewer'):
        rev.add_argument('--'+name,required=True)
    rev.add_argument('--evidence',nargs='*',default=[])
    args = parser.parse_args()
    if args.command=='run':
        result = run_case(args.case,reference=args.reference,use_agnes=args.use_agnes,word=args.word,db=args.db)
        print(json.dumps(result,ensure_ascii=False,indent=2))
    else:
        from app.review import review as apply_review
        conn = open_database(args.db)
        try:
            print(apply_review(conn,args.run,args.finding,args.decision,args.reason,args.reviewer,args.evidence))
        finally:
            conn.close()


if __name__=='__main__':
    main()
