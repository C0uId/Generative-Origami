"""Merge proved CCD modes without imposing a world-z order on separated facets.

This is a proof-schema gate, not a new geometric collision detector. It accepts
only the finite set of whole-time proof rules issued by continuous_ccd.py and
checks their coverage and required fields. In particular a cached PASS string,
an unknown proof reason, or an unresolved material contact never establishes a
mode. The original goal-patch z audit is retained verbatim as a diagnostic.
"""
from __future__ import annotations

from copy import deepcopy
import itertools
import math

import numpy as np


SCOPE_CORRECTION = (
    "World-z ordering of corresponding *goal* material points is not a "
    "nonpenetration condition while the two facets are proved separated. "
    "FREE uses whole-time CCD separation (the exact shared material origin "
    "is allowed); shared hinges use their structural sector proof; actual "
    "persistent area contact still requires the finite material patch and "
    "validated layer ranks. Unresolved contact remains UNCERTAIN."
)
FREE_REASONS = frozenset({"SWEPT_AABB_SEPARATION", "CONTINUOUS_CONE_SEPARATION",
                          "ALL_CONTINUOUS_FEATURE_QUERIES_SAFE"})
HINGE_REASONS = frozenset({"ANALYTIC_SHARED_HINGE_SECTOR", "ANALYTIC_CLOSED_SEAM_HINGE_SECTOR"})
CONTACT_REASONS = frozenset({"ANALYTIC_FIXED_GOAL_RELATIVE_POSE", "ACTIVE_SET_FIXED_GOAL_MATERIAL_PATCH"})
ADDITIONAL_REASONS = frozenset({"ANALYTIC_INDUCED_MATERIAL_HINGE", "RELATIVE_FRAME_CONTINUOUS_SEPARATION"})
FEATURE_SAFE_REASONS = frozenset({"ALL_TIME_CELLS_PROVED_SEPARATED", "NATIVE_NO_COLLISION",
    "RADIAL_EDGES_NONCOLLINEAR_FOR_WHOLE_INTERVAL", "RADIAL_EDGES_OPPOSITE_FOR_WHOLE_INTERVAL"})
EXACT_SEAM_REASONS = frozenset({"SPHERICAL_3R_CONTINUOUS_IDENTITY", "WHOLE_INTERVAL_LOCAL_CHART_JETS"})


def _finite(value):
    return isinstance(value, (int, float, np.number)) and not isinstance(value, bool) and math.isfinite(value)


def _span(value):
    return (isinstance(value, (list, tuple)) and len(value) == 2
            and all(_finite(v) for v in value) and 0. <= value[0] < value[1] <= 1.)


def _material_patch(record, pair, rank, *, persistent=False):
    """Check the material evidence schema, never invent geometry from z values."""
    if not isinstance(record, dict) or record.get("panels") != list(pair):
        return False
    if record.get("layer_order") != [rank[pair[0]], rank[pair[1]]]:
        return False
    try:
        weights = np.asarray(record["material_coordinates"], dtype=float)
    except (KeyError, ValueError, TypeError):
        return False
    count = record.get("patch_vertex_count")
    if (not isinstance(count, int) or count < 3 or weights.shape != (count, 2, 3)
            or not np.isfinite(weights).all() or np.min(weights) < -1e-9
            or np.max(weights) > 1.+1e-9
            or np.max(abs(weights.sum(axis=2)-1.)) > 1e-8):
        return False
    if persistent:
        diagnostics = record.get("material_polygon_diagnostics", {})
        error = diagnostics.get("material_mapping_error_diagnostic")
        minimum = diagnostics.get("minimum_barycentric_coordinate")
        return (record.get("status") == "PASS" and record.get("state") == "CONTACT"
                and record.get("reason") == "ACTIVE_SET_FIXED_GOAL_MATERIAL_PATCH"
                and record.get("whole_panel_exemption") is False
                and record.get("signed_gap_lower_bound") == 0.
                and record.get("signed_gap_upper_bound") == 0.
                and record.get("relative_pose_identity") == "R_i^-1 R_j = fixed goal Rodrigues product"
                and _finite(error) and 0. <= error <= 1e-9
                and _finite(minimum) and minimum >= -1e-9)
    return True


def _feature_proof(node, pair):
    features = node.get("features", {})
    records = features.get("records", [])
    if (features.get("all_safe") is not True or features.get("initial_disjointness_proven") is not True
            or len(records) != 13 or features.get("exact_shared_vertex_queries") != 2
            or features.get("surrogate") != "linear chords with minimum-separation inflated by rigid curvature bound"):
        return False
    inflation, separation = features.get("curvature_inflation"), features.get("effective_minimum_separation")
    if not (_finite(inflation) and _finite(separation) and 0. <= inflation <= separation):
        return False
    expected_vf = {(p, v, pair[1-i]) for i, p in enumerate(pair) for v in (1, 2)}
    actual_vf, actual_ee = set(), set()
    for record in records:
        if record.get("status") != "SAFE" or record.get("reason") not in FEATURE_SAFE_REASONS:
            return False
        if record.get("feature") == "VERTEX_FACE":
            if record.get("reason", "").startswith("RADIAL_EDGES_"):
                return False
            actual_vf.add((record.get("vertex_panel"), record.get("vertex"), record.get("face_panel")))
        elif record.get("feature") == "EDGE_EDGE":
            try:
                edge_pair = tuple(tuple(e) for e in record["edges"])
                if record.get("reason", "").startswith("RADIAL_EDGES_") and not all(0 in e for e in edge_pair):
                    return False
                actual_ee.add(edge_pair)
            except (KeyError, TypeError):
                return False
        else:
            return False
        if record.get("reason") in {"ALL_TIME_CELLS_PROVED_SEPARATED", "NATIVE_NO_COLLISION"}:
            if record.get("time_interval") != [0., 1.] and record.get("time_interval") != (0., 1.):
                return False
    edges = ((0, 1), (1, 2), (2, 0))
    return actual_vf == expected_vf and actual_ee == set(itertools.product(edges, repeat=2))


def _leaf_mode(node, pair, material, rank, panel_count, closure_tolerance):
    reason = node.get("reason")
    if node.get("whole_panel_exemption") is True:
        return None, "WHOLE_PANEL_EXEMPTION_REJECTED"
    if reason in FREE_REASONS:
        if isinstance(material, dict) and material.get("state") == "CONTACT":
            return None, "FREE_PROOF_CONTRADICTS_PERSISTENT_MATERIAL_CONTACT"
        if reason == "CONTINUOUS_CONE_SEPARATION":
            margin = node.get("margin_lower_bound")
            normal = np.asarray(node.get("normal", []), dtype=float)
            if (node.get("passed") is not True or not _finite(margin) or margin <= 0.
                    or normal.shape != (3,) or not np.isfinite(normal).all()
                    or abs(float(np.linalg.norm(normal))-1.) > 1e-8
                    or node.get("allowed_contact") != "shared origin only, no radius exclusion"):
                return None, "CONE_SEPARATION_EVIDENCE_INCOMPLETE"
        if reason == "ALL_CONTINUOUS_FEATURE_QUERIES_SAFE" and not _feature_proof(node, pair):
            return None, "CONTINUOUS_FEATURE_EVIDENCE_INCOMPLETE"
        return "FREE", reason
    if reason in HINGE_REASONS:
        closing = reason == "ANALYTIC_CLOSED_SEAM_HINGE_SECTOR"
        if (closing and pair != (0, panel_count-1)) or (not closing and pair[1] != pair[0]+1):
            return None, "HINGE_TOPOLOGY_MISMATCH"
        joint = 0 if closing else pair[1]
        angles = node.get("angle_range", [])
        if (node.get("joint") != joint or len(angles) != 2
                or not all(_finite(v) for v in angles) or angles[0] > angles[1]
                or not (-math.pi <= angles[0] <= angles[1] <= 0.
                        or 0. <= angles[0] <= angles[1] <= math.pi)
                or node.get("whole_panel_exemption") is not False
                or node.get("allowed_set") != "exact shared material hinge; final finite overlap only at goal relative angle"):
            return None, "HINGE_SECTOR_EVIDENCE_INCOMPLETE"
        if closing:
            seam = node.get("closure_structure") or {}
            bound = seam.get("continuous_upper_bound")
            if (seam.get("status") != "PASS" or seam.get("reason") not in EXACT_SEAM_REASONS
                    or not _finite(bound) or not 0. <= bound <= closure_tolerance):
                return None, "EXACT_CLOSING_SEAM_NOT_PROVEN"
        if any(abs(v) == math.pi for v in angles):
            if not _material_patch(material, pair, rank) or node.get("goal_patch_vertices", 0) < 3:
                return None, "HINGE_ENDPOINT_MATERIAL_PATCH_NOT_PROVEN"
        return "TOPOLOGICAL_HINGE", reason
    if reason in CONTACT_REASONS:
        if (node.get("whole_panel_exemption") is not False
                or node.get("layer_order") != [rank[pair[0]], rank[pair[1]]]
                or node.get("patch_vertex_count", 0) < 3
                or not _material_patch(material, pair, rank, persistent=True)):
            return None, "PERSISTENT_CONTACT_MATERIAL_OR_LAYER_NOT_PROVEN"
        if reason == "ACTIVE_SET_FIXED_GOAL_MATERIAL_PATCH" and not _material_patch(node, pair, rank, persistent=True):
            return None, "PERSISTENT_CONTACT_MATERIAL_OR_LAYER_NOT_PROVEN"
        return "CONTACT", reason
    if reason in ADDITIONAL_REASONS:
        proof = node.get("contact_certificate")
        if (not isinstance(proof, dict) or proof.get("status") != "PASS"
                or proof.get("panels") != list(pair)
                or proof.get("time_interval") != node.get("time_interval")
                or proof.get("whole_panel_exemption") is True):
            return None, "ADDITIONAL_CONTACT_PROOF_PAYLOAD_INCOMPLETE"
        cyclic = proof.get("uses_exact_cyclic_closure")
        direct = list(range(pair[0]+1, pair[1]+1))
        complement = list(range(pair[1]+1, panel_count))+[0]+list(range(1, pair[0]+1))
        chain = complement if cyclic is True else direct
        if (not isinstance(cyclic, bool) or proof.get("relative_chain") != chain
                or proof.get("anchor") != (pair[1] if cyclic else pair[0])):
            return None, "RELATIVE_CHAIN_TOPOLOGY_NOT_PROVEN"
        if reason == "RELATIVE_FRAME_CONTINUOUS_SEPARATION":
            normal = np.asarray(proof.get("normal_in_anchor_material_frame", []), dtype=float)
            margin = proof.get("margin_lower_bound")
            upper = proof.get("per_vertex_upper_bounds")
            if (proof.get("reason") not in {"WHOLE_INTERVAL_RELATIVE_FRAME_CONE_SEPARATION", "RELATIVE_FRAME_CONTINUOUS_SEPARATION"}
                    or not _finite(margin) or margin <= 0.
                    or normal.shape != (3,) or not np.isfinite(normal).all()
                    or abs(float(np.linalg.norm(normal))-1.) > 1e-8
                    or not isinstance(upper, (list, tuple)) or len(upper) != 2
                    or not all(_finite(v) and v < 0. for v in upper)
                    or proof.get("allowed_contact") != "same exact material origin only"
                    or proof.get("sampled_plane_used_as_proof") is not False
                    or (isinstance(material, dict) and material.get("state") == "CONTACT")):
                return None, "RELATIVE_FRAME_SEPARATION_EVIDENCE_INCOMPLETE"
            return "FREE", reason
        # The axis/material identity alone does not exclude a transverse
        # crossing on both sides of that axis. An independent unilateral
        # material/layer proof must be explicit; do not turn identity into a
        # blanket contact exemption, including for apparently similar axes.
        if (proof.get("reason") != "ANALYTIC_INDUCED_MATERIAL_HINGE"
                or proof.get("layer_order_gate_proven") is not True
                or proof.get("layer_order") != [rank[pair[0]], rank[pair[1]]]
                or proof.get("whole_panel_exemption") is not False
                or proof.get("distinct_original_axes_retained") is not True
                or not _material_patch(material, pair, rank)
                or not _material_patch(proof, pair, rank)):
            return None, "INDUCED_CONTACT_LAYER_OR_FINITE_MATERIAL_PATCH_NOT_PROVEN"
        layer = proof.get("layer_proof", {})
        mapped = proof.get("material_proof", {})
        mapping_error = proof.get("goal_material_mapping_error_upper_bound")
        joint = proof.get("varying_joint")
        angles = proof.get("signed_angle_range", [])
        triangle = layer.get("containing_triangle")
        containing = pair[0] if triangle == "anchor" else pair[1]
        coefficients = layer.get("coefficient_lower_bounds", [])
        zeros = layer.get("symbolic_zero_vertices", [])
        axis = np.asarray(proof.get("axis_in_factored_frame", []), dtype=float)
        triangles = np.asarray(proof.get("factored_material_triangles", []), dtype=float)
        if (cyclic or joint not in chain or proof.get("fixed_goal_joints") != [k for k in chain if k != joint]
                or len(angles) != 2 or not all(_finite(v) for v in angles)
                or not 0. < angles[0] <= angles[1] <= math.pi
                or axis.shape != (3,) or not np.isfinite(axis).all() or abs(float(np.linalg.norm(axis))-1.) > 1e-8
                or triangles.shape != (2, 3, 3) or not np.isfinite(triangles).all()
                or not _finite(mapping_error) or not 0. <= mapping_error <= 3e-5
                or mapped.get("status") != "PASS"
                or mapped.get("basis") != "same forward subchain at the declared goal; invariant material points on the actual axis"
                or mapped.get("finite_patch_definition") != "intersection of the two finite triangles in their goal relative pose"
                or not _material_patch({**mapped, "panels": list(pair), "layer_order": proof["layer_order"]}, pair, rank)
                or layer.get("status") != "PASS"
                or layer.get("basis") != "affine signed-gap coefficient nonnegative on an entire containing finite triangle"
                or layer.get("signed_gap_lower_bound") != 0.
                or layer.get("whole_interval") is not True
                or layer.get("goal_material_patch_subset_of_proved_triangle") is not True
                or triangle not in {"anchor", "target"} or layer.get("containing_panel") != containing
                or len(coefficients) != 3 or not all(_finite(v) and v >= 0. for v in coefficients)
                or not any(v > 0. for v in coefficients)
                or not isinstance(zeros, list) or set(zeros) != {k for k, v in enumerate(coefficients) if v == 0.}
                or 0 not in zeros
                or layer.get("zero_basis") != "exact origin and same original crease index, never a near-coincident axis"
                or layer.get("rank_sign") != (1. if rank[pair[0]] > rank[pair[1]] else -1.)
                or layer.get("goal_anchor_normal_z_parity") != (-1.)**pair[0]
                or layer.get("sin_angle_sign") not in {-1., 1.}):
            return None, "INDUCED_CONTACT_UNILATERAL_MATERIAL_PROOF_INCOMPLETE"
        for vertex in zeros:
            if vertex == 0:
                continue
            ray = containing if vertex == 1 else (containing+1) % panel_count
            if (ray != joint or (triangle == "anchor" and joint != chain[0])
                    or (triangle == "target" and joint != chain[-1])):
                return None, "INDUCED_CONTACT_SYMBOLIC_AXIS_IDENTITY_NOT_PROVEN"
        return "MATERIAL_HINGE", reason
    return None, "UNKNOWN_CONTINUOUS_PROOF_REASON"


def merge_contact_modes(pair_certificates, material_audit, *, panel_count=8,
                        layer_order=None, closure_tolerance=4e-6):
    """Return a fail-closed mode proof over all panel pairs and normalized time.

    ``material_audit`` is the existing GoalMaterialContact.audit output. Its
    full value remains under original_material_audit; a negative world-z lower
    bound is not promoted to a collision and cannot defeat strict separation.
    Neither a positive z bound nor a material PASS can rescue unknown CCD.
    """
    original = deepcopy(material_audit)
    if material_audit is not None and not isinstance(material_audit, dict):
        return {"status": "UNCERTAIN", "reason": "MALFORMED_MATERIAL_AUDIT", "pairs": [],
                "original_material_audit": original, "scope_correction": SCOPE_CORRECTION}
    order = layer_order if layer_order is not None else (material_audit or {}).get("layer_order")
    valid_order = (isinstance(panel_count, int) and not isinstance(panel_count, bool) and panel_count >= 2
                   and isinstance(order, (list, tuple))
                   and all(isinstance(p, int) and not isinstance(p, bool) for p in order)
                   and sorted(order) == list(range(panel_count)))
    rank = {p: i for i, p in enumerate(order)} if valid_order else {}
    output = {"status": "UNCERTAIN", "reason": "CONTACT_MODE_PROOF_NOT_COMPLETE", "pairs": [],
              "scope_correction": SCOPE_CORRECTION, "original_material_audit": original,
              "layer_order": list(order) if valid_order else None,
              "layer_order_scope": "permutation and rank consistency checked here; mechanism M/V admissibility is established by the contact-model producer",
              "sampled_gap_used_as_proof": False, "world_z_goal_order_used_as_gate": False,
              "proof_scope": "whitelisted continuous separation, structural hinge, or finite persistent material contact"}
    if not valid_order or not _finite(closure_tolerance) or closure_tolerance <= 0.:
        output["reason"] = "INVALID_LAYER_ORDER_OR_CLOSURE_TOLERANCE"
        return output
    expected = set(itertools.combinations(range(panel_count), 2))
    try:
        actual = [tuple(c["panels"]) for c in pair_certificates]
    except (KeyError, TypeError):
        output["reason"] = "MALFORMED_PAIR_CERTIFICATES"
        return output
    if len(actual) != len(expected) or set(actual) != expected:
        output["reason"] = "CONTINUOUS_PAIR_COVERAGE_INCOMPLETE"
        return output
    materials = {}
    for record in (material_audit or {}).get("pairs", []):
        try:
            pair = tuple(record["panels"])
            if pair in materials:
                output["reason"] = "DUPLICATE_MATERIAL_PAIR"
                return output
            materials[pair] = record
        except (KeyError, TypeError):
            output["reason"] = "MALFORMED_MATERIAL_PAIR"
            return output

    def visit(node, pair, span):
        if node.get("status") != "PASS":
            return [], "CCD_PAIR_NOT_PROVEN"
        if not _span(node.get("time_interval")) or tuple(node["time_interval"]) != span:
            return [], "CCD_TIME_COVERAGE_NOT_PROVEN"
        children = node.get("children")
        if children is not None:
            if node.get("reason") != "CURVED_RIGID_INTERVAL_SUBDIVISION" or len(children) != 2:
                return [], "UNKNOWN_SUBDIVISION_PROOF"
            cut = children[0].get("time_interval", [None, None])[1]
            if not _finite(cut) or not span[0] < cut < span[1]:
                return [], "CCD_SUBDIVISION_COVERAGE_NOT_PROVEN"
            left, error = visit(children[0], pair, (span[0], cut))
            if error:
                return [], error
            right, error = visit(children[1], pair, (cut, span[1]))
            return (left+right, None) if not error else ([], error)
        mode, reason = _leaf_mode(node, pair, materials.get(pair), rank, panel_count, closure_tolerance)
        if mode is None:
            return [], reason
        return [{"state": mode, "reason": reason, "time_interval": list(span)}], None

    for pair, certificate in zip(actual, pair_certificates):
        try:
            segments, error = visit(certificate, pair, (0., 1.))
        except (ValueError, KeyError, TypeError, IndexError, AttributeError, OverflowError):
            segments, error = [], "MALFORMED_CONTINUOUS_MODE_PROOF"
        modes = sorted({s["state"] for s in segments})
        output["pairs"].append({"panels": list(pair), "status": "PASS" if not error else "UNCERTAIN",
            "reason": error or "ALL_CONTINUOUS_CONTACT_MODES_PROVEN",
            "state": modes[0] if len(modes) == 1 else "MIXED_PROVEN_MODES" if modes else "UNKNOWN",
            "mode_segments": segments, "ccd_reason": certificate.get("reason"),
            "goal_material_audit_used_as_collision_exemption": False})
    if all(p["status"] == "PASS" for p in output["pairs"]):
        output.update(status="PASS", reason="ALL_CONTINUOUS_CONTACT_MODES_PROVEN")
    return output