from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

import numpy as np

from generative_origami.simulation.single_vertex import SingleVertexMechanism


@dataclass
class _Node:
    q: np.ndarray
    parent: int


class _Tree:
    def __init__(self, roots: list[np.ndarray], side: str):
        self.side = side
        self.nodes = [_Node(np.asarray(q, dtype=float).copy(), -1) for q in roots]

    def add(self, q: np.ndarray, parent: int) -> int:
        self.nodes.append(_Node(np.asarray(q, dtype=float).copy(), parent))
        return len(self.nodes) - 1

    def nearest(self, target: np.ndarray) -> int:
        return min(range(len(self.nodes)), key=lambda i: float(np.linalg.norm(self.nodes[i].q - target)))

    def path_to_root(self, idx: int) -> list[np.ndarray]:
        out: list[np.ndarray] = []
        while idx >= 0:
            out.append(self.nodes[idx].q.copy())
            idx = self.nodes[idx].parent
        return out

    @classmethod
    def from_chain(cls, chain: list[np.ndarray], side: str):
        if not chain:
            raise ValueError("empty chain")
        tree=cls([chain[0]],side)
        parent=0
        for q in chain[1:]:
            parent=tree.add(q,parent)
        return tree


class BidirectionalManifoldPlanner:
    """Projection-based BiRRT for a single-vertex rigid origami mechanism."""

    def __init__(
        self,
        mechanism: SingleVertexMechanism,
        *,
        seed: int = 20261017,
        step_size: float = 0.22,
        bridge_tolerance: float = 0.035,
        closure_tolerance: float = 4e-6,
        collision_check: bool = True,
        contact_aware: bool = False,
        contact_progress_threshold: float = 0.55,
        layer_model = None,
    ):
        self.m = mechanism
        self.rng = np.random.default_rng(seed)
        self.step_size = float(step_size)
        self.bridge_tolerance = float(bridge_tolerance)
        self.closure_tolerance = float(closure_tolerance)
        self.collision_check = collision_check
        self.contact_aware = contact_aware
        self.contact_progress_threshold = float(contact_progress_threshold)
        self.layer_model = layer_model
        self.stats = {
            "projection_rejects": 0,
            "sector_rejects": 0,
            "collision_rejects": 0,
            "edge_rejects": 0,
            "extensions": 0,
        }

    def _state_valid(self, q: np.ndarray) -> tuple[bool, dict[str, Any]]:
        if not self.m.sector_valid(q):
            self.stats["sector_rejects"] += 1
            return False, {"reason": "M_V_SECTOR"}
        closure = float(np.linalg.norm(self.m.closure_residual(q)))
        if closure > self.closure_tolerance:
            self.stats["projection_rejects"] += 1
            return False, {"reason": "LOOP_CLOSURE", "closure": closure}
        if self.collision_check:
            report = self.m.collision_report(
                q, contact_aware=self.contact_aware,
                contact_progress_threshold=self.contact_progress_threshold,
                layer_model=self.layer_model,
            )
            if report["collision"]:
                self.stats["collision_rejects"] += 1
                return False, {"reason": "COLLISION", **report}
        return True, {"reason": "PASS", "closure": closure}

    def _projected_segment_valid(self, a: np.ndarray, b: np.ndarray, samples: int = 3) -> bool:
        # Project intermediate ambient interpolation points back to the manifold;
        # this is only an edge validator, never a displayed animation.
        prev = a
        for k in range(1, samples + 1):
            t = k / (samples + 1)
            raw = (1 - t) * a + t * b
            q, err = self.m.project(raw, anchor=raw, near_weight=0.04, max_nfev=80)
            if err > self.closure_tolerance:
                self.stats["edge_rejects"] += 1
                return False
            ok, _ = self._state_valid(q)
            if not ok:
                self.stats["edge_rejects"] += 1
                return False
            if np.linalg.norm(q - prev) > max(0.45, 2.5 * np.linalg.norm(b-a)):
                self.stats["edge_rejects"] += 1
                return False
            prev = q
        return True

    def _steer(self, q: np.ndarray, target: np.ndarray) -> np.ndarray | None:
        direction = target - q
        basis, _, _ = self.m.tangent_basis(q)
        tangent = basis @ (basis.T @ direction)
        norm = float(np.linalg.norm(tangent))
        if norm < 1e-9:
            # Explore another tangent direction instead of stalling.
            tangent = basis @ self.rng.normal(size=basis.shape[1])
            norm = float(np.linalg.norm(tangent))
            if norm < 1e-9:
                return None
        step = min(self.step_size, max(0.06, float(np.linalg.norm(direction))))
        raw = q + step * tangent / norm
        low = np.where(self.m.signs > 0, 0.0, -math.pi)
        high = np.where(self.m.signs > 0, math.pi, 0.0)
        raw = np.clip(raw, low, high)
        candidate, err = self.m.project(raw, anchor=raw, near_weight=0.045, max_nfev=100)
        if err > self.closure_tolerance or np.linalg.norm(candidate - q) < 1e-4:
            self.stats["projection_rejects"] += 1
            return None
        ok, _ = self._state_valid(candidate)
        if not ok:
            return None
        if not self._projected_segment_valid(q, candidate, samples=2):
            return None
        self.stats["extensions"] += 1
        return candidate

    def _extend(self, tree: _Tree, start_idx: int, target: np.ndarray, max_steps: int) -> int:
        current = start_idx
        for _ in range(max_steps):
            candidate = self._steer(tree.nodes[current].q, target)
            if candidate is None:
                return current
            current = tree.add(candidate, current)
            if np.linalg.norm(candidate - target) <= self.bridge_tolerance:
                return current
        return current

    def _sample_sector(self) -> np.ndarray:
        magnitudes = self.rng.random(self.m.n) * math.pi
        return self.m.signs * magnitudes

    @staticmethod
    def _dedupe_path(path: list[np.ndarray], tol: float = 1e-8) -> list[np.ndarray]:
        out: list[np.ndarray] = []
        for q in path:
            if not out or np.linalg.norm(q - out[-1]) > tol:
                out.append(q)
        return out

    def _try_bridge(self, ta: _Tree, ia: int, tb: _Tree, ib: int) -> tuple[int,int] | None:
        qa = ta.nodes[ia].q
        current = ib
        for _ in range(16):
            qb = tb.nodes[current].q
            if np.linalg.norm(qb - qa) <= self.bridge_tolerance:
                if self._projected_segment_valid(qb, qa, samples=4):
                    return ia, current
            candidate = self._steer(qb, qa)
            if candidate is None:
                return None
            current = tb.add(candidate, current)
        return None

    def densify_path(self, path: list[np.ndarray], max_angle_step: float = 0.09) -> tuple[list[np.ndarray], dict[str, Any]]:
        dense: list[np.ndarray] = [path[0].copy()]
        max_closure = float(np.linalg.norm(self.m.closure_residual(path[0])))
        for a, b in zip(path[:-1], path[1:]):
            distance = float(np.linalg.norm(b - a))
            steps = max(1, int(math.ceil(distance / max_angle_step)))
            previous = dense[-1]
            for k in range(1, steps + 1):
                if k == steps:
                    q = b.copy()
                else:
                    t = k / steps
                    raw = (1 - t) * a + t * b
                    q, err = self.m.project(raw, anchor=raw, near_weight=0.035, max_nfev=80)
                    if err > self.closure_tolerance:
                        return dense, {"passed":False,"reason":"DENSIFY_PROJECTION","closure":err}
                if np.linalg.norm(q - previous) > max(0.18, 2.5 * max_angle_step):
                    return dense, {"passed":False,"reason":"DENSIFY_JUMP","jump":float(np.linalg.norm(q-previous))}
                # Singular exact endpoints are valid by construction.
                if not (np.allclose(q, self.m.flat, atol=1e-10) or np.allclose(q, self.m.goal, atol=1e-10)):
                    ok, rep = self._state_valid(q)
                    if not ok:
                        return dense, {"passed":False,"reason":"DENSIFY_VALIDITY","detail":rep}
                max_closure = max(max_closure, float(np.linalg.norm(self.m.closure_residual(q))))
                dense.append(q.copy())
                previous = q
        return self._dedupe_path(dense), {"passed":True,"max_closure_error":max_closure}

    def plan(self, *, max_iterations: int = 2500) -> dict[str, Any]:
        start_seeds, start_cone = self.m.endpoint_seeds(goal_side=False, count=12, seed=31)
        goal_seeds, goal_cone = self.m.endpoint_seeds(goal_side=True, count=12, seed=47)
        if self.layer_model is not None and self.layer_model.report.feasible:
            constrained = self.layer_model.goal_seeds()
            if constrained:
                goal_seeds = constrained
        base_report = {
            "flat_cone": start_cone.__dict__,
            "goal_cone": goal_cone.__dict__,
            "flat_seed_count": len(start_seeds),
            "goal_seed_count": len(goal_seeds),
            "layer_contact": (self.layer_model.report.__dict__ if self.layer_model is not None else None),
        }
        if not start_seeds:
            return {"status":"FLAT_MODE_SEED_FAILURE", **base_report, "stats":self.stats}
        if not goal_seeds:
            return {"status":"GOAL_MODE_SEED_FAILURE", **base_report, "stats":self.stats}

        # Ensure seeds themselves are valid. Endpoint singular states are appended later.
        start_seeds = [q for q in start_seeds if self._state_valid(q)[0]]
        goal_seeds = [q for q in goal_seeds if self._state_valid(q)[0]]
        if not start_seeds or not goal_seeds:
            return {"status":"SEEDS_REJECTED_BY_VALIDITY_GATE", **base_report, "stats":self.stats}

        ta = _Tree(start_seeds, "START")
        if self.layer_model is not None:
            prefix=self.layer_model.goal_prefix()
            tb = _Tree.from_chain(prefix, "GOAL") if prefix else _Tree(goal_seeds, "GOAL")
        else:
            tb = _Tree(goal_seeds, "GOAL")
        connection = None
        for iteration in range(max_iterations):
            if self.rng.random() < 0.30:
                target = tb.nodes[int(self.rng.integers(len(tb.nodes)))].q
            else:
                target = self._sample_sector()
            ia = ta.nearest(target)
            ra = self._extend(ta, ia, target, max_steps=4)
            qa = ta.nodes[ra].q
            ib = tb.nearest(qa)
            rb = self._extend(tb, ib, qa, max_steps=10)
            bridge = self._try_bridge(ta, ra, tb, rb)
            if bridge is not None:
                connection = (ta, bridge[0], tb, bridge[1], iteration)
                break
            ta, tb = tb, ta

        if connection is None:
            return {
                "status":"SEARCH_EXHAUSTED",
                **base_report,
                "stats":self.stats,
                "iterations":max_iterations,
                "tree_sizes":[len(ta.nodes),len(tb.nodes)],
            }

        ta, ia, tb, ib, iteration = connection
        pa = ta.path_to_root(ia)   # connection -> root of ta
        pb = tb.path_to_root(ib)   # connection -> root of tb
        if ta.side == "START":
            start_part = list(reversed(pa))
            goal_part = pb
        else:
            start_part = list(reversed(pb))
            goal_part = pa
        path = self._dedupe_path([self.m.flat] + start_part + goal_part + [self.m.goal])

        audit = []
        path_valid = True
        for i, q in enumerate(path):
            # Exact singular endpoints get collision/contact exemptions by definition.
            if i == 0 or i == len(path)-1:
                closure = float(np.linalg.norm(self.m.closure_residual(q)))
                audit.append({"index":i,"closure":closure,"collision":False,"endpoint":True})
                continue
            ok, rep = self._state_valid(q)
            path_valid &= ok
            audit.append({
                "index":i,
                "closure":float(np.linalg.norm(self.m.closure_residual(q))),
                "collision": rep.get("reason") == "COLLISION",
                "endpoint":False,
            })

        dense, dense_audit = self.densify_path(path) if path_valid else (path, {"passed":False,"reason":"PATH_AUDIT_FAILED"})
        if not path_valid or not dense_audit.get("passed"):
            status = "PATH_AUDIT_FAILED"
        elif self.collision_check and self.layer_model is not None:
            status = "RIGID_PATH_LAYER_ORDER_VALIDATED"
        elif self.collision_check and self.contact_aware:
            status = "RIGID_PATH_WITH_LAYER_CONTACT_EXEMPTIONS"
        elif self.collision_check:
            status = "EXACT_RIGID_PATH_FOUND"
        else:
            status = "MANIFOLD_PATH_FOUND_COLLISION_UNCHECKED"
        return {
            "status":status,
            "collision_mode": ("LAYER_ORDER" if self.layer_model is not None else ("LAYER_CONTACT_AWARE" if self.contact_aware else "STRICT")) if self.collision_check else "OFF",
            **base_report,
            "stats":self.stats,
            "iterations":iteration + 1,
            "tree_sizes":[len(ta.nodes),len(tb.nodes)],
            "path_length_nodes":len(path),
            "path":[[float(x) for x in q] for q in path],
            "keyframe_count":len(dense),
            "keyframes":[[float(x) for x in q] for q in dense],
            "densify_audit":dense_audit,
            "path_audit":audit,
            "max_closure_error":max(x["closure"] for x in audit),
        }