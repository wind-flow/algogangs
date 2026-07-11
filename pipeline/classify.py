#!/usr/bin/env python3
"""규칙 기반 레짐 국면 분류기 (LLM 불필요).

위폴 프레임의 계층별 방향 규칙을 지표 데이터로 근사한다:
  - 각 지표의 '레짐 우호 방향' 기울기(최근 3개월 추세)를 +1/-1로 판정
  - 선행/동행/후행 계층별 평균 방향 점수를 낸다
  - 4국면 프로토타입과의 거리로 가장 가까운 국면 선택

국면 프로토타입 (선행, 동행, 후행) 방향:
  회복 (+, 0, -) · 성장 (+, +, +) · 둔화 (-, +, +) · 침체 (-, -, -)
반환: {"phase", "sub", "feel", "scores"}
"""
import json
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent

PROTO = {
    "회복": {"선행": +1, "동행": 0, "후행": -1},
    "성장": {"선행": +1, "동행": +1, "후행": +1},
    "둔화": {"선행": -1, "동행": +1, "후행": +1},
    "침체": {"선행": -1, "동행": -1, "후행": -1},
}
SUBS = {
    "회복": "회복 초입", "성장": "성장 국면",
    "둔화": "둔화 진입", "침체": "침체 구간",
}


def _slope_dir(csv: Path, good: str, lookback_days: int = 90) -> float:
    """최근 값 vs 룩백(기본 90일 전) 값의 방향을 레짐 우호 기준으로 부호화.
    날짜 기준이라 월간·일간 지표를 같은 기간으로 비교한다. good=none이면 0."""
    if good == "none":
        return 0.0
    s = pd.read_csv(csv, index_col=0, parse_dates=True).iloc[:, 0].dropna()
    if len(s) < 2:
        return 0.0
    last_ts = s.index[-1]
    past = s[s.index <= last_ts - pd.Timedelta(days=lookback_days)]
    ref = past.iloc[-1] if len(past) else s.iloc[0]
    raw = s.iloc[-1] - ref
    if raw == 0:
        return 0.0
    favorable = (raw > 0) == (good == "up")
    return 1.0 if favorable else -1.0


def classify() -> dict:
    cfg = json.loads((BASE / "indicators.json").read_text())
    layer_dirs = {"선행": [], "동행": [], "후행": []}
    for ind in cfg["indicators"]:
        layer = ind.get("layer")
        if layer not in layer_dirs:
            continue
        csv = BASE / "data" / f"{ind['id']}.csv"
        if not csv.exists():
            continue
        d = _slope_dir(csv, ind.get("good", "none"))
        if d != 0.0:
            layer_dirs[layer].append(d)

    # 계층별 평균 방향 (레짐 우호 기준 → 실제 '상승/하락'으로 환산)
    lead = _avg(layer_dirs["선행"])
    coin = _avg(layer_dirs["동행"])
    lag = _avg(layer_dirs["후행"])
    obs = {"선행": lead, "동행": coin, "후행": lag}

    # 프로토타입과의 거리로 순위 (근접일수록 우세)
    ranked = sorted(PROTO, key=lambda p: sum((obs[k] - PROTO[p][k]) ** 2 for k in obs))
    best, second = ranked[0], ranked[1]
    d1 = sum((obs[k] - PROTO[best][k]) ** 2 for k in obs)
    d2 = sum((obs[k] - PROTO[second][k]) ** 2 for k in obs)
    borderline = (d2 - d1) < 0.6          # 1·2위가 근소하면 경계로 표시

    sub = f"{SUBS[best]} · {second} 경계" if borderline else SUBS[best]
    feel = _feel(best, obs)
    if borderline:
        feel += f" (다만 {second} 국면과의 경계)"
    return {"phase": best, "sub": sub, "feel": feel, "borderline": borderline,
            "second": second, "scores": {k: round(v, 2) for k, v in obs.items()}}


def _avg(xs):
    return sum(xs) / len(xs) if xs else 0.0


def _feel(phase, obs):
    parts = []
    parts.append("선행 개선" if obs["선행"] > 0.2 else ("선행 악화" if obs["선행"] < -0.2 else "선행 혼조"))
    parts.append("동행 개선" if obs["동행"] > 0.2 else ("동행 둔화" if obs["동행"] < -0.2 else "동행 보합"))
    base = {
        "회복": "바닥을 지나 반등을 시도하는 국면",
        "성장": "지표가 넓게 확장되는 국면",
        "둔화": "정점을 지나 속도가 꺾이는 국면",
        "침체": "수축이 확인되는 방어 국면",
    }[phase]
    return f"{base} — {', '.join(parts)}"


if __name__ == "__main__":
    print(json.dumps(classify(), ensure_ascii=False, indent=2))
