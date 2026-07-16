#!/usr/bin/env python3
"""매일 아침 레짐 데일리 체크 (결정론, 0토큰).

① 발표 감지: 주요 지표(state.json의 release_series)의 FRED 최신 관측일이
   저장된 상태보다 새로우면 '새 발표'로 판정 → 정기간행물 호수(issue_no) 채번.
② 임계 알림: alerts.json 규칙(부호 전환·기준선 돌파·급등)을 평가,
   상태 전환 시에만 알림 텍스트 생성.

출력(JSON): {"new_releases": [...], "gdp_released": bool, "issue_no": N|null, "alerts": ["..."]}
--commit 없이 실행하면 상태를 갱신하지 않는다(드라이런).
--init 은 현재 데이터 기준으로 상태만 저장(트리거 없음).
"""
import argparse
import io
import json
import sys
import urllib.request
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent
STATE = BASE / "state.json"
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={s}"

# 발표 감지 대상: 간행물 트리거가 되는 핵심 월간·분기 지표
RELEASE_SERIES = {
    "UNRATE": "미국 고용보고서(실업률)",
    "CPIAUCSL": "미국 CPI",
    "RSAFS": "미국 소매판매",
    "INDPRO": "미국 산업생산",
    "UMCSENT": "미시간대 소비자심리",
    "A191RL1Q225SBEA": "미국 실질 GDP(분기)",
}


def fetch(series: str) -> pd.Series:
    with urllib.request.urlopen(FRED_CSV.format(s=series), timeout=60) as r:
        raw = r.read().decode()
    df = pd.read_csv(io.StringIO(raw))
    dc = df.columns[0]
    df[dc] = pd.to_datetime(df[dc])
    return pd.to_numeric(df.set_index(dc)[series], errors="coerce").dropna()


def load_state() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {"last_dates": {}, "issue_no": 1, "alerts_active": {}}


def eval_alerts(state: dict, cache: dict) -> list:
    msgs = []
    active = state.setdefault("alerts_active", {})
    for rule in json.loads((BASE / "alerts.json").read_text())["rules"]:
        s = cache.get(rule["series"])
        if s is None:
            s = cache[rule["series"]] = fetch(rule["series"])
        v = s if rule["transform"] == "none" else (s.pct_change(12) * 100).dropna()
        latest = float(v.values[-1])
        if rule["kind"] == "sign_state":
            cur = "neg" if latest < 0 else "pos"
            prev = active.get(rule["id"])
            if prev is not None and prev != cur:
                label = rule["label_down"] if cur == "neg" else rule["label_up"]
                msgs.append(f"{label} — 최신값 {latest:,.2f} ({v.index[-1].date()})")
            active[rule["id"]] = cur
            continue
        fired = False
        if rule["kind"] == "level_cross":
            fired = latest > rule["level"] if rule["direction"] == "up" else latest < rule["level"]
        elif rule["kind"] == "spike":
            lookback = v.values[-rule["window"] - 1:-1]
            fired = len(lookback) > 0 and latest >= lookback.min() + rule["delta"]
        fired = bool(fired)
        was = active.get(rule["id"], False)
        if fired and not was:
            msgs.append(f"{rule['label']} — 최신값 {latest:,.2f} ({v.index[-1].date()})")
        active[rule["id"]] = fired
    return msgs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true")
    ap.add_argument("--init", action="store_true")
    args = ap.parse_args()

    state = load_state()
    cache = {}
    new, gdp = [], False
    for series, label in RELEASE_SERIES.items():
        try:
            s = cache[series] = fetch(series)
        except Exception as e:
            print(f"[WARN] {series} fetch 실패: {e}", file=sys.stderr)
            continue
        latest = str(s.index[-1].date())
        if not args.init and state["last_dates"].get(series) and latest > state["last_dates"][series]:
            new.append(f"{label} ({latest})")
            gdp = gdp or series == "A191RL1Q225SBEA"
        state["last_dates"][series] = latest

    alerts = eval_alerts(state, cache)  # --init 때도 평가해 상태를 심되, 알림은 버린다
    if args.init:
        alerts = []

    issue_no = None
    if new and not args.init:
        state["issue_no"] = state.get("issue_no", 1) + 1
        issue_no = state["issue_no"]

    if args.commit or args.init:
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2))

    print(json.dumps({"new_releases": new, "gdp_released": gdp,
                      "issue_no": issue_no, "alerts": alerts}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
