from __future__ import annotations
import hashlib
from .models import TargetSpec

ALIASES = {
    "狗": ("dog", "QUADRUPED"),
    "小狗": ("dog", "QUADRUPED"),
    "dog": ("dog", "QUADRUPED"),
    "狐狸": ("fox", "QUADRUPED"),
    "狐": ("fox", "QUADRUPED"),
    "fox": ("fox", "QUADRUPED"),
    "鹿": ("deer", "QUADRUPED"),
    "deer": ("deer", "QUADRUPED"),
    "长颈鹿": ("giraffe", "QUADRUPED"),
    "giraffe": ("giraffe", "QUADRUPED"),
    "狼": ("wolf", "QUADRUPED"),
    "wolf": ("wolf", "QUADRUPED"),
    "猫": ("cat", "QUADRUPED"),
    "cat": ("cat", "QUADRUPED"),
    "老虎": ("tiger", "QUADRUPED"),
    "狮子": ("lion", "QUADRUPED"),
    "马": ("horse", "QUADRUPED"),
    "牛": ("cow", "QUADRUPED"),
    "羊": ("sheep", "QUADRUPED"),
    "兔子": ("rabbit", "QUADRUPED"),
    "兔": ("rabbit", "QUADRUPED"),
    "大象": ("elephant", "QUADRUPED"),
    "霸王龙": ("trex", "DINOSAUR"),
    "暴龙": ("trex", "DINOSAUR"),
    "t-rex": ("trex", "DINOSAUR"),
    "trex": ("trex", "DINOSAUR"),
    "鸟": ("bird", "BIRD"),
    "千纸鹤": ("crane", "BIRD"),
    "鹤": ("crane", "BIRD"),
    "鹰": ("eagle", "BIRD"),
    "鱼": ("fish", "FISH"),
    "鲨鱼": ("shark", "FISH"),
    "蝴蝶": ("butterfly", "INSECT"),
    "蜜蜂": ("bee", "INSECT"),
    "花": ("flower", "FLOWER"),
    "玫瑰": ("rose", "FLOWER"),
    "郁金香": ("tulip", "FLOWER"),
    "盒子": ("box", "BOX"),
    "纸盒": ("box", "BOX"),
    "箱子": ("box", "BOX"),
    "飞机": ("airplane", "VEHICLE"),
    "纸飞机": ("airplane", "VEHICLE"),
    "汽车": ("car", "VEHICLE"),
    "车": ("car", "VEHICLE"),
    "船": ("boat", "VEHICLE"),
    "机器人": ("robot", "HUMANOID"),
    "人": ("human", "HUMANOID"),
    "房子": ("house", "GEOMETRIC"),
    "星星": ("star", "GEOMETRIC"),
    "五角星": ("star", "GEOMETRIC"),
}

FAMILY_KEYWORDS = [
    ("QUADRUPED", ["狗","狐","狼","猫","虎","狮","鹿","马","牛","羊","兔","象","熊","豹","鼠","猪"]),
    ("BIRD", ["鸟","鹤","鹰","鸡","鸭","鹅","鸽","雀","燕"]),
    ("FISH", ["鱼","鲨","鲸","海豚","鳐"]),
    ("INSECT", ["虫","蝶","蜂","蚁","蜻蜓","甲虫"]),
    ("FLOWER", ["花","玫瑰","郁金香","莲"]),
    ("BOX", ["盒","箱","收纳"]),
    ("VEHICLE", ["车","飞机","船","火箭","坦克"]),
    ("DINOSAUR", ["恐龙","龙","霸王龙","暴龙"]),
    ("HUMANOID", ["人","机器人","武士","骑士"]),
    ("GEOMETRIC", ["星","房","塔","球","几何","多面体"]),
]

BASE_PARAMS = {
    "dog": dict(body_length=.38, neck_length=.12, head_size=.20, front_leg_length=.22, rear_leg_length=.22, tail_length=.18, ear_length=.12, snout_length=.14),
    "fox": dict(body_length=.36, neck_length=.12, head_size=.17, front_leg_length=.22, rear_leg_length=.22, tail_length=.35, ear_length=.27, snout_length=.18),
    "deer": dict(body_length=.34, neck_length=.25, head_size=.15, front_leg_length=.30, rear_leg_length=.30, tail_length=.15, ear_length=.20, snout_length=.13),
    "giraffe": dict(body_length=.32, neck_length=.45, head_size=.12, front_leg_length=.32, rear_leg_length=.32, tail_length=.16, ear_length=.10, snout_length=.11),
}

def _stable_unit(text: str, salt: str) -> float:
    h = hashlib.sha256((salt + "::" + text).encode("utf-8")).digest()
    return int.from_bytes(h[:8], "big") / 2**64

def _default_params(name: str, family: str) -> dict[str, float]:
    if family == "QUADRUPED":
        if name in BASE_PARAMS:
            return dict(BASE_PARAMS[name])
        return {
            "body_length": .30 + .12*_stable_unit(name,"body"),
            "neck_length": .10 + .25*_stable_unit(name,"neck"),
            "head_size": .12 + .10*_stable_unit(name,"head"),
            "front_leg_length": .18 + .16*_stable_unit(name,"fl"),
            "rear_leg_length": .18 + .16*_stable_unit(name,"rl"),
            "tail_length": .10 + .30*_stable_unit(name,"tail"),
            "ear_length": .08 + .20*_stable_unit(name,"ear"),
            "snout_length": .08 + .16*_stable_unit(name,"snout"),
        }
    if family == "BIRD":
        return {"wing_span": .45 + .25*_stable_unit(name,"wing"), "tail": .16 + .22*_stable_unit(name,"tail"), "neck": .08 + .22*_stable_unit(name,"neck")}
    if family == "FISH":
        return {"body": .45 + .25*_stable_unit(name,"body"), "tail": .18 + .22*_stable_unit(name,"tail"), "fin": .12 + .18*_stable_unit(name,"fin")}
    if family == "FLOWER":
        return {"petal_count": float(5 + int(4*_stable_unit(name,"petal"))), "petal_length": .25 + .25*_stable_unit(name,"len")}
    if family == "BOX":
        return {"height": .18 + .25*_stable_unit(name,"height"), "lip": .05 + .10*_stable_unit(name,"lip")}
    if family == "VEHICLE":
        return {"length": .45 + .25*_stable_unit(name,"length"), "nose": .12 + .20*_stable_unit(name,"nose")}
    if family == "DINOSAUR":
        return {"body": .38, "neck": .15 + .18*_stable_unit(name,"neck"), "tail": .38 + .22*_stable_unit(name,"tail"), "leg": .22}
    if family == "HUMANOID":
        return {"torso": .34, "arm": .24 + .12*_stable_unit(name,"arm"), "leg": .28 + .12*_stable_unit(name,"leg")}
    if family == "GEOMETRIC":
        return {"symmetry": float(4 + 2*int(3*_stable_unit(name,"symmetry")))}
    return {"variation": _stable_unit(name,"variation")}

def parse_target(query: str) -> TargetSpec:
    raw = (query or "").strip()
    q = raw.lower().replace("折纸","").replace("origami","").strip() or raw.lower().strip() or "unknown"

    # longest alias wins
    found = None
    for alias, value in sorted(ALIASES.items(), key=lambda kv: len(kv[0]), reverse=True):
        if alias.lower() in q:
            found = value
            break
    if found:
        name, family = found
        confidence = .96
        source = "builtin_alias"
    else:
        family = "GENERIC"
        for fam, keys in FAMILY_KEYWORDS:
            if any(k.lower() in q for k in keys):
                family = fam
                break
        name = q.replace(" ","_")[:48] or "unknown"
        confidence = .72 if family != "GENERIC" else .40
        source = "keyword_router" if family != "GENERIC" else "generic_fallback"

    return TargetSpec(
        query=raw,
        canonical_name=name,
        family=family,
        parameters=_default_params(name, family),
        semantic_confidence=confidence,
        semantic_source=source,
    )