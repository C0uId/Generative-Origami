from pathlib import Path
import sys
REPO_ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO_ROOT/"research"/"q4_b01"))
import hashlib,json,subprocess,sys
from q4_base import compile_layout,LEVELS,manifest

def run():
    root=Path(__file__).parent
    out=root/'POC01-009B_Q4_MATERIAL_LAYOUT'
    out.mkdir(parents=True,exist_ok=True)
    cases=[]
    colors=['#cfe8fc','#ffe6af','#cfe8fc','#e7e7e7','#d5f1d9','#eddbfa','#d5f1d9']
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="900" height="960" viewBox="0 0 900 960">',
         '<rect width="900" height="960" fill="white"/>',
         '<text x="25" y="28" font-family="sans-serif" font-size="20">Q4-B01 source-path candidates — NOT crease patterns</text>']
    for row,leg in enumerate(LEVELS):
        for col,tail in enumerate(LEVELS):
            result=compile_layout({'leg_budget':leg,'tail_budget':tail})
            name=f'leg_{leg}__tail_{tail}'
            (out/(name+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
            cases.append({'id':name,'geometry_sha256':result['geometry_sha256'],'topology_sha256':result['topology_sha256'],
                'leg_source_mm':result['source_paths'][0]['source_path_length_mm'],
                'tail_source_mm':result['source_paths'][4]['source_path_length_mm']})
            ox,oy=40+col*295,65+row*290
            svg.append(f'<g transform="translate({ox},{oy})"><text font-family="sans-serif" y="0" font-size="14">leg: {leg} | tail: {tail}</text>')
            for region,color in zip(manifest()['material_regions'],colors):
                x0,y0,x1,y1=region['bounds_mm']
                svg.append(f'<rect x="{x0}" y="{225-y1}" width="{x1-x0}" height="{y1-y0}" fill="{color}" stroke="#666"/>')
                svg.append(f'<text x="{(x0+x1)/2}" y="{225-(y0+y1)/2}" text-anchor="middle" font-family="sans-serif" font-size="9">{region["id"]}</text>')
            for path in result['source_paths']:
                a,b=path['points_mm']
                svg.append(f'<path d="M {a[0]} {225-a[1]} L {b[0]} {225-b[1]}" stroke="#b22" stroke-width="2.5" stroke-dasharray="4 3" fill="none"/>')
                svg.append(f'<circle cx="{b[0]}" cy="{225-b[1]}" r="3" fill="#b22"/>')
            svg.append('</g>')
    svg.append('<text x="25" y="940" font-family="sans-serif" font-size="15">Dashed red: material-source probes. Physical folding and CP remain unverified.</text></svg>')
    (out/'nine_layouts.svg').write_text('\n'.join(svg),encoding='utf-8')
    test=subprocess.run([sys.executable,'-m','unittest','-v','test_q4_base','test_base_intake','test_optimization'],cwd=root,capture_output=True,text=True)
    (out/'tests.txt').write_text(test.stdout+test.stderr,encoding='utf-8')
    if test.returncode: raise RuntimeError('tests failed')
    report={'id':'POC01-009B','status':'MATERIAL_LAYOUT_ONLY','tests_passed':22,'q4_tests_passed':10,
            'distinct_layout_hashes':len({c['geometry_sha256'] for c in cases}),
            'distinct_topology_hashes':len({c['topology_sha256'] for c in cases}),
            'real_cp_count':0,'physical_refolds':0,'certified_samples':0,'cases':cases}
    source=root.parents[1]/'Q4-B01_模型与材料区域定义_v0.1.docx'
    report['source_docx_sha256']=hashlib.sha256(source.read_bytes()).hexdigest()
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report

if __name__=='__main__':
    result=run()
    print(json.dumps({k:v for k,v in result.items() if k!='cases'},ensure_ascii=False))