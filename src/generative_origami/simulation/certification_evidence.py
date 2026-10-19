"""Recompute the Goal contact-mode gate from complete cell evidence.

This validates the producer's proof schema and coverage; it does not rerun
geometry or turn a cached PASS label into a geometric proof. In particular
the stored merged audit must equal a fresh merge of the cell's underlying
continuous pair proofs and its retained original material audit.
"""
from __future__ import annotations

import itertools
import json

from .contact_gate import merge_contact_modes


def _pair_records(records, expected, *, complete):
    if not isinstance(records, list):
        return False
    actual = []
    for record in records:
        if not isinstance(record, dict):
            return False
        pair = record.get("panels")
        if (not isinstance(pair, (list, tuple)) or len(pair) != 2
                or any(not isinstance(p, int) or isinstance(p, bool) for p in pair)
                or tuple(pair) not in expected):
            return False
        actual.append(tuple(pair))
    return (len(actual) == len(set(actual))
            and (set(actual) == expected if complete else set(actual) <= expected))


def audit_goal_contact_evidence(cell, layer_order):
    """Return a detailed fail-closed Goal mode-evidence validation result.

    Missing original material records are permitted for strictly FREE proofs;
    the fresh merge still requires finite patches for actual material contact.
    The stored merged audit and the continuous pair certificates always need
    complete, unique pair coverage. Motion, sector, closure and seam gates are
    separate responsibilities of the caller's final path gate.
    """
    def failed(reason):
        return {"status": "UNCERTAIN", "reason": reason,
                "recomputed_from_pair_evidence": True}

    if (not isinstance(layer_order, (list, tuple)) or len(layer_order) < 2
            or any(not isinstance(p, int) or isinstance(p, bool) for p in layer_order)
            or sorted(layer_order) != list(range(len(layer_order)))):
        return failed("INVALID_GOAL_EVIDENCE_LAYER_ORDER")
    if not isinstance(cell, dict):
        return failed("MALFORMED_GOAL_CELL_EVIDENCE")
    order = list(layer_order)
    expected = set(itertools.combinations(range(len(order)), 2))
    pairs = cell.get("pairs")
    if not _pair_records(pairs, expected, complete=True):
        return failed("GOAL_CONTINUOUS_PAIR_COVERAGE_INCOMPLETE")
    bounds = cell.get("whole_interval_bounds")
    active = bounds.get("active_set_contact_bounds") if isinstance(bounds, dict) else None
    if (not isinstance(active, dict) or active.get("status") != "PASS"
            or not _pair_records(active.get("pairs"), expected, complete=True)):
        return failed("STORED_GOAL_MODE_EVIDENCE_INCOMPLETE")
    original = active.get("original_material_audit")
    if (not isinstance(original, dict) or original.get("layer_order") != order
            or not _pair_records(original.get("pairs"), expected, complete=False)):
        return failed("ORIGINAL_GOAL_MATERIAL_AUDIT_MISSING_OR_MALFORMED")
    try:
        fresh = merge_contact_modes(pairs, original, panel_count=len(order), layer_order=order)
        if fresh.get("status") != "PASS" or not _pair_records(fresh.get("pairs"), expected, complete=True):
            return failed("RECOMPUTED_GOAL_CONTACT_MODES_NOT_PROVEN")
        # Canonical serialization also rejects NaN/infinity and prevents a
        # cached extra/missing field or edited mode segment from being hidden
        # by a matching top-level status or pair count.
        serialize = lambda value: json.dumps(value, ensure_ascii=False, sort_keys=True,
                                             separators=(",", ":"), allow_nan=False)
        if serialize(active) != serialize(fresh):
            return failed("STORED_GOAL_MODE_EVIDENCE_DISAGREES_WITH_FRESH_MERGE")
    except (ValueError, KeyError, TypeError, IndexError, AttributeError, OverflowError):
        return failed("MALFORMED_GOAL_CONTACT_PROOF_PAYLOAD")
    return {"status": "PASS", "reason": "GOAL_CONTACT_MODES_RECOMPUTED_AND_STORED_EVIDENCE_MATCHES",
            "pair_count": len(expected), "recomputed_from_pair_evidence": True,
            "stored_audit_exactly_matches_fresh_merge": True}


def validate_goal_contact_evidence(cell, layer_order):
    """Boolean wrapper for a final path gate; no cached PASS-only acceptance."""
    return audit_goal_contact_evidence(cell, layer_order)["status"] == "PASS"