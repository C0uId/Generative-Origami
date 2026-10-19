from __future__ import annotations
import html

def render_svg(spec, fold, validation) -> str:
    V=fold["vertices_coords"]
    E=fold["edges_vertices"]
    A=fold["edges_assignment"]
    w=640; pad=40; scale=560

    def xy(p):
        return pad+p[0]*scale, pad+(1-p[1])*scale

    parts=[
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{w}" viewBox="0 0 {w} {w}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="40" y="24" font-size="16">{html.escape(spec.query)} · {html.escape(spec.family)}</text>',
    ]
    for ei,(i,j) in enumerate(E):
        x1,y1=xy(V[i]); x2,y2=xy(V[j])
        a=A[ei]
        if a=="B":
            dash=""
            width=2.0
        elif a=="M":
            dash=' stroke-dasharray="10 6"'
            width=1.5
        else:
            dash=' stroke-dasharray="4 5"'
            width=1.5
        parts.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="black" stroke-width="{width}"{dash}/>')
    for vid,label in fold.get("go:featureLabels",{}).items():
        x,y=xy(V[int(vid)])
        parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3" fill="black"/>')
        parts.append(f'<text x="{x+6:.2f}" y="{y-6:.2f}" font-size="10">{html.escape(label)}</text>')
    verdict="PASS" if validation.passed else "FAIL"
    parts.append(f'<text x="40" y="625" font-size="12">Validation: {verdict} · {html.escape(validation.level)}</text>')
    parts.append('</svg>')
    return "".join(parts)