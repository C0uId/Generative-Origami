"""Finite experimental parameter domain. No physical certification is implied."""
import math

PRESETS = {"short": 0.25, "medium": 0.5, "long": 0.75}

def project(requested, *, policy="reject"):
    if policy not in {"reject", "snap"}:
        raise ValueError("policy must be reject or snap")
    expected = {"body_to_leg_ratio", "tail_ratio"}
    if set(requested) != expected:
        raise ValueError("exactly body_to_leg_ratio and tail_ratio are required")
    implemented, notes = {}, []
    for name, value in requested.items():
        if isinstance(value, str) and value in PRESETS:
            implemented[name] = value
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError("parameter must be a preset or finite normalized experimental value")
        closest = min(PRESETS, key=lambda key: (abs(PRESETS[key] - value), PRESETS[key]))
        if value != PRESETS[closest]:
            if policy == "reject":
                raise ValueError("OUTSIDE_EXPERIMENTAL_PRESET_DOMAIN")
            notes.append(f"{name}: requested {value}, selected {closest} ({PRESETS[closest]}); normalized design coordinate, not measured anatomy")
        implemented[name] = closest
    return {"requested": dict(requested), "implemented": implemented,
            "approximation_notes": notes, "domain_status": "EXPERIMENTAL_NOT_CERTIFIED",
            "geometry_status": "BLOCKED_PENDING_PHYSICAL_BASE_COMPILER"}

def grid():
    return [project({"body_to_leg_ratio": a, "tail_ratio": b}) for a in PRESETS for b in PRESETS]