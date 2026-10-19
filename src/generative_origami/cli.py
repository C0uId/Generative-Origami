from __future__ import annotations
import argparse, json
from pathlib import Path
from .pipeline import generate

def main():
    p=argparse.ArgumentParser(description="Generative Origami MVP CLI")
    p.add_argument("query",help="例如：狐狸 / 长颈鹿 / 霸王龙 / 咖啡杯")
    p.add_argument("--out",default="runtime_outputs",help="输出目录")
    args=p.parse_args()
    r=generate(args.query,Path(args.out))
    print(json.dumps(r,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()