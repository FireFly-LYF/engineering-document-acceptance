import argparse
from pathlib import Path
import pymupdf
if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('pdf')
    parser.add_argument('--out',required=True)
    args = parser.parse_args()
    output = Path(args.out)
    output.mkdir(parents=True,exist_ok=True)
    with pymupdf.open(args.pdf) as document:
        for n,page in enumerate(document,1):
            page.get_pixmap(matrix=pymupdf.Matrix(1.5,1.5),alpha=False).save(output/f'page-{n}.png')
        print('Rendered pages:',len(document))
