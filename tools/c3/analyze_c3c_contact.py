"""Read-only C3-C material-contact root-cause analysis.

Reads completed interval_certificates.json incrementally to avoid holding the
large reference CCD tree in memory. --partial reads current per-interval
checkpoints, labels coverage incomplete, and never upgrades a result.
Negative lower bounds are uncertainty; only a negative UPPER bound proves
negative signed gap throughout its declared interval. Even the latter is
not automatically a transverse intersection / physical collision witness.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ROOT = REPO_ROOT
DEFAULT = REPO_ROOT/'experiments/current/POC01-007C3-C_SINGULAR_CONTACT_EXACT_BRIDGE'


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf8')
    temporary.replace(path)


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while data := stream.read(1024*1024):
            digest.update(data)
    return digest.hexdigest()


def stream_intervals(path):
    """Stream the known report schema's final intervals array, one object at a time."""
    marker = '"intervals": ['
    decoder = json.JSONDecoder()
    with path.open(encoding='utf8') as stream:
        buffer = ''
        while marker not in buffer:
            data = stream.read(65536)
            if not data:
                raise ValueError('final report has no intervals array')
            buffer += data
        buffer = buffer.split(marker, 1)[1]
        while True:
            buffer = buffer.lstrip(' \t\r\n,')
            if buffer.startswith(']'):
                return
            try:
                value, end = decoder.raw_decode(buffer)
            except json.JSONDecodeError:
                data = stream.read(1024*1024)
                if not data:
                    raise ValueError('truncated interval certificate report') from None
                buffer += data
                continue
            yield value
            buffer = buffer[end:]


def leaves(node):
    if node.get('children'):
        for child in node['children']:
            yield from leaves(child)
    else:
        yield node


def is_origin(weights):
    return len(weights) == 3 and weights == [1., 0., 0.]


def analyze(certificates, metadata):
    scanned, summaries = [], []
    negative, ambiguous, zero, positive = [], [], 0, 0
    contact_pairs, events, unavailable, raw_unknown, raw_collision = [], [], [], [], []
    terminal = []
    totals = Counter()
    for interval in certificates:
        index = interval['interval']
        scanned.append(index)
        if index < 70:
            continue
        counts = Counter()
        for cell in interval['cell_certificates']:
            cell_index = cell['interval']
            sa, sb = cell['source_parameter_interval']
            common = {'source_interval': index, 'cell': cell_index,
                      'cell_time_interval': [0., 1.], 'source_time_interval': [sa, sb]}
            active = cell.get('whole_interval_bounds', {}).get('active_set_contact_bounds')
            if active is None:
                unavailable.append({**common, 'reason': 'NO_ACTIVE_SET_MATERIAL_VERTEX_AUDIT_FOR_FALLBACK',
                                    'motion_model': cell.get('motion_model')})
                counts['cells_without_material_vertex_bounds'] += 1
            else:
                for event in active.get('contact_event_isolation', []):
                    # These event coordinates belong to the parent source
                    # interval already; do not apply the cell affine map twice.
                    ea, eb = event['time_interval']
                    if max(ea, sa) <= min(eb, sb):
                        events.append({**common, **event,
                            'event_source_time_interval': [max(ea, sa), min(eb, sb)],
                            'event_scope': 'declared free-crease goal-boundary root; not a general material collision event'})
                for pair in active.get('pairs', []):
                    pair_common = {**common, 'panels': pair['panels']}
                    gaps = pair.get('per_material_vertex_gap_bounds')
                    if gaps is None:
                        if pair.get('state') == 'CONTACT' and pair.get('status') == 'PASS':
                            contact_pairs.append({**pair_common, 'reason': pair['reason'],
                                'vertex_count': pair.get('patch_vertex_count'),
                                'signed_gap_bounds': [pair.get('signed_gap_lower_bound'), pair.get('signed_gap_upper_bound')],
                                'relative_pose_identity': pair.get('relative_pose_identity'),
                                'whole_panel_exemption': pair.get('whole_panel_exemption')})
                            counts['analytic_fixed_material_contact_pairs'] += 1
                        continue
                    mappings = pair.get('material_coordinates', [])
                    for vertex, (lo, hi) in enumerate(gaps):
                        mapping = mappings[vertex] if vertex < len(mappings) else None
                        record = {**pair_common, 'material_vertex': vertex,
                                  'signed_gap_lower_bound': lo, 'signed_gap_upper_bound': hi,
                                  'layer_order': pair.get('layer_order'),
                                  'material_coordinates': mapping}
                        shared_origin = mapping is not None and all(is_origin(w) for w in mapping)
                        if shared_origin and lo == hi == 0.:
                            zero += 1
                            counts['exact_shared_material_origin_vertices'] += 1
                        elif hi < 0.:
                            negative.append({**record,
                                'classification': 'WHOLE_INTERVAL_SIGNED_GAP_STRICTLY_NEGATIVE',
                                'proves_layer_signed_gap_constraint_failure': True,
                                'is_physical_collision_witness': False,
                                'scope': 'conditional reference bound at these corresponding material points; no transverse-intersection witness inferred'})
                            counts['whole_interval_negative_material_vertices'] += 1
                        elif lo < 0. <= hi:
                            ambiguous.append({**record,
                                'classification': 'SIGNED_GAP_SIGN_UNRESOLVED',
                                'is_physical_collision_witness': False,
                                'material_zero_gap_event_enclosure': [sa, sb],
                                'event_occurrence_proven': False,
                                'event_isolation_status': 'UNCERTAIN',
                                'event_enclosure_scope': 'non-origin material vertex; the continuous interval bound contains zero'})
                            counts['ambiguous_material_vertices'] += 1
                        elif lo >= 0.:
                            positive += 1
                            counts['nonnegative_material_vertex_bounds'] += 1
                        else:
                            raise ValueError(f'invalid material gap enclosure {lo}, {hi}')
            for pair in cell.get('pairs', []):
                if pair['status'] == 'PASS':
                    continue
                for leaf in leaves(pair):
                    if leaf['status'] == 'PASS':
                        continue
                    a, b = leaf.get('time_interval', [0., 1.])
                    record = {**common, 'panels': pair['panels'], 'status': leaf['status'],
                              'cell_time_interval': [a, b],
                              'source_time_interval': [sa+(sb-sa)*a, sa+(sb-sa)*b],
                              'reason': leaf['reason'],
                              'feature_reason_counts': dict(Counter(q['reason'] for q in
                                  leaf.get('features', {}).get('records', []) if q['status'] != 'SAFE')),
                              'material_patch': leaf.get('material_patch'),
                              'witness': leaf.get('witness')}
                    if leaf['status'] == 'COLLISION':
                        raw_collision.append(record)
                        counts['raw_ccd_collision_leaves'] += 1
                    else:
                        raw_unknown.append(record)
                        counts['raw_ccd_uncertain_leaves'] += 1
        if index == 161:
            attempt = interval.get('bridge_attempt') or {}
            terminal.append({'source_interval': 161, 'source_time_interval': [0., 1.],
                             'classification': 'GOAL_SINGULAR_CHART_UNRESOLVED',
                             'exact_bridge_passed': interval.get('exact_bridge_passed'),
                             'reason': attempt.get('reason'),
                             'atlas_attempts': attempt.get('atlas_attempts', []),
                             'root_rejection': attempt.get('root_rejection')})
            counts['goal_singular_chart_unresolved'] += int(not interval.get('exact_bridge_passed', False))
        if counts['whole_interval_negative_material_vertices']:
            root = 'CERTIFIED_NEGATIVE_LAYER_SIGNED_GAP_CONSTRAINT'
        elif counts['goal_singular_chart_unresolved']:
            root = 'TERMINAL_GOAL_SINGULAR_CHART_AND_INCOMPLETE_CONTACT_PROOF'
        elif counts['raw_ccd_uncertain_leaves'] and counts['ambiguous_material_vertices']:
            root = 'CONSERVATIVE_CCD_AND_MATERIAL_GAP_EVENT_BOUNDS_UNRESOLVED'
        elif counts['ambiguous_material_vertices']:
            root = 'MATERIAL_GAP_EVENT_BOUNDS_UNRESOLVED'
        elif counts['raw_ccd_uncertain_leaves']:
            root = 'CONSERVATIVE_CCD_UNRESOLVED'
        else:
            root = 'NO_RECORDED_CONTACT_FAILURE'
        summaries.append({'source_interval': index, 'final_status': interval['status'],
                          'raw_ccd_status': interval.get('ccd_status'),
                          'closure_status': interval.get('closure_status'),
                          'exact_bridge_passed': interval.get('exact_bridge_passed'),
                          'cell_count': len(interval['cell_certificates']),
                          'root_cause': root, 'counts': dict(counts)})
        totals.update(counts)
    coverage = scanned == list(range(162))
    return {'schema_version': 1, 'experiment_id': 'POC01-007C3-C_CONTACT_ROOT_CAUSES',
            'source_report': metadata, 'source_intervals_scanned': scanned,
            'complete_162_interval_report_read': coverage,
            'goal_intervals_analyzed': [c['source_interval'] for c in summaries],
            'counts': dict(totals),
            'interpretation': {
                'negative_upper_bound': 'hi<0 proves this material signed gap is negative throughout the declared whole interval under the reference enclosure assumptions',
                'negative_lower_bound_only': 'lo<0<=hi is unresolved; it proves neither penetration nor collision nor that a zero-gap event occurred',
                'material_event_bracket': 'whole cell enclosure containing zero, excluding exact shared-origin identities; root occurrence and isolation are not proved',
                'physical_collision': 'only the conservative CCD transverse/material witness can establish COLLISION; signed-gap sign alone is not promoted',
                'numeric_scope': 'conditional float64 reference enclosure guards inherited from the certificates; not formal verified interval arithmetic'},
            'interval_root_causes': summaries,
            'whole_interval_negative_material_vertices': negative,
            'ambiguous_material_vertices_and_unisolated_event_enclosures': ambiguous,
            'analytic_fixed_material_contact_pairs': contact_pairs,
            'free_crease_boundary_events': events,
            'cells_without_active_set_vertex_audits': unavailable,
            'raw_ccd_uncertain_leaves': raw_unknown,
            'raw_ccd_collision_leaves': raw_collision,
            'terminal_goal_singular_chart': terminal}


def markdown(report):
    counts = report['counts']
    lines = ['# C3-C 材料接触失败根因', '',
        f"完整 162 区间输入：**{report['complete_162_interval_report_read']}**；已分析 Goal 区间：{len(report['goal_intervals_analyzed'])}。", '',
        f"全区间确定负 signed-gap 的材料顶点数（`upper < 0`）：**{counts.get('whole_interval_negative_material_vertices',0)}**。",
        f"仅符号未定的材料顶点数（`lower < 0 <= upper`）：**{counts.get('ambiguous_material_vertices',0)}**。",
        f"原 conservative CCD 未证明叶节点数：**{counts.get('raw_ccd_uncertain_leaves',0)}**；碰撞叶节点数：**{counts.get('raw_ccd_collision_leaves',0)}**。", '',
        '负 lower 只表示 enclosure 包含负值，不能当成穿透或碰撞。负 upper 才证明对应材料点在整段时间违反声明的层序 signed-gap 条件；这仍不自动构成两个三角形的 transverse intersection 证据。', '',
        '未隔离材料事件由非 origin 材料顶点的 gap enclosure 包含零而保守标记；所给时间段只是一段可能含事件的区间，既不声称事件已发生，也不声称求得了精确接触时刻。自由 crease 边界的解析根另列，不能替代材料事件隔离。', '',
        '| 源区间 | 最终状态 | 原 CCD | exact bridge | 未定材料顶点 | 确定负 gap | CCD 未定叶 | 根因 |',
        '| --- | --- | --- | --- | --- | --- | --- | --- |']
    for row in report['interval_root_causes']:
        c = row['counts']
        lines.append(f"| {row['source_interval']} | {row['final_status']} | {row['raw_ccd_status']} | {row['exact_bridge_passed']} | {c.get('ambiguous_material_vertices',0)} | {c.get('whole_interval_negative_material_vertices',0)} | {c.get('raw_ccd_uncertain_leaves',0)} | {row['root_cause']} |")
    lines += ['', '## 具体材料顶点证据', '']
    negative = report['whole_interval_negative_material_vertices']
    if negative:
        lines += ['以下是确定负 gap 的具体证据；完整清单见同目录 `contact_root_causes.json`。', '',
                  '| 源区间 / cell | pair / 材料顶点 | 源时间 | gap bounds |', '| --- | --- | --- | --- |']
        for x in negative[:30]:
            lines.append(f"| {x['source_interval']} / {x['cell']} | {x['panels']} / {x['material_vertex']} | {x['source_time_interval']} | [{x['signed_gap_lower_bound']:.9g}, {x['signed_gap_upper_bound']:.9g}] |")
    else:
        lines += ['当前所有已记录材料顶点均没有 `upper < 0` 证据，不能报告“已证明接触穿透”。', '']
    ambiguous = report['ambiguous_material_vertices_and_unisolated_event_enclosures']
    representatives = []
    seen = set()
    for x in ambiguous:
        key = tuple(x['panels'])
        if key not in seen:
            representatives.append(x); seen.add(key)
    if representatives:
        lines += ['', '每个 pair 的首个符号未定代表如下；完整 JSON 保留每个源区间、cell、非 origin 材料顶点、材料坐标和源时间。', '',
                  '| 源区间 / cell | pair / 材料顶点 | 源时间 | gap bounds |', '| --- | --- | --- | --- |']
        for x in representatives:
            lines.append(f"| {x['source_interval']} / {x['cell']} | {x['panels']} / {x['material_vertex']} | {x['source_time_interval']} | [{x['signed_gap_lower_bound']:.9g}, {x['signed_gap_upper_bound']:.9g}] |")
    lines += ['', '## 独立的未完成门', '',
        '1. 原 CCD 未证明的具体 pair、cell 时间及映射后的源时间、feature 原因，在 JSON 的 `raw_ccd_uncertain_leaves` 中逐项保存。',
        '2. 材料 signed-gap 为符号未定时，其非 origin 材料 zero-gap event 仍未隔离；不是碰撞证据。',
        '3. 区间 161 的 full-goal endpoint 使有限 3R atlas 奇异；所有 dependent triple 及失败原因保存在 `terminal_goal_singular_chart`。无 exact endpoint bridge 证明就不能取得 exact seam 特权。',
        '4. 固定相对 goal Rodrigues pose 的材料接触单独列为解析恒等零 gap；它不豁免其他 pair 或非接触区域的 CCD。', '',
        '以上均来自保存的全区间 enclosure 和 conservative CCD 证书。没有新增帧采样、Dog/RRT 规划、顶点线性运动或状态升格。', '']
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=DEFAULT/'interval_certificates.json')
    parser.add_argument('--out', type=Path, default=DEFAULT)
    parser.add_argument('--partial', action='store_true', help='analyze current interval checkpoints and mark incomplete coverage')
    args = parser.parse_args(argv)
    if args.partial:
        files = sorted((args.input.parent/'certificates').glob('interval_[0-9][0-9][0-9].json'))
        certificates = (json.loads(p.read_text(encoding='utf8')) for p in files)
        metadata = {'mode': 'PARTIAL_CHECKPOINTS', 'checkpoint_count': len(files),
                    'directory': str(args.input.parent/'certificates')}
    else:
        if not args.input.is_file():
            raise SystemExit(f'final report missing: {args.input}')
        metadata = {'mode': 'FINAL_INTERVAL_REPORT', 'file': str(args.input), 'sha256': sha256(args.input)}
        certificates = stream_intervals(args.input)
    report = analyze(certificates, metadata)
    if not args.partial and not report['complete_162_interval_report_read']:
        raise SystemExit('final report does not contain ordered source intervals 0..161')
    write_json(args.out/'contact_root_causes.json', report)
    (args.out/'CONTACT_FAILURES.md').write_text(markdown(report), encoding='utf8')
    print(json.dumps({'complete_162_interval_report_read': report['complete_162_interval_report_read'],
                      'goal_interval_count': len(report['goal_intervals_analyzed']),
                      'counts': report['counts']}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())