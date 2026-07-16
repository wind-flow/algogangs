#!/usr/bin/env python3
"""알고갱즈 매크로 레짐 차트팩 생성기.

indicators.json의 지표를 FRED CSV(키 불필요)에서 받아
data/*.csv 저장 + charts/*.png 차트 + summary.md 최신값 표를 만든다.
반복 실행 전제(주간 레짐 체크) — 실행 주체는 algogangs 크론으로 이관 예정.
"""
import csv
import io
import json
import sys
import urllib.request
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
CHARTS = BASE / "charts"

import theme
C_LINE, C_THRESH, C_SHADE = theme.LINE, theme.THRESH, theme.SHADE
C_INK, C_MUTED, C_GRID = theme.INK, theme.MUTED, theme.GRID

plt.rcParams.update(theme.RC)

FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"


def fetch_fred(series: str) -> pd.Series:
    url = FRED_CSV.format(series=series)
    with urllib.request.urlopen(url, timeout=60) as r:
        raw = r.read().decode()
    df = pd.read_csv(io.StringIO(raw))
    date_col = df.columns[0]  # FRED가 observation_date/DATE 혼용
    df[date_col] = pd.to_datetime(df[date_col])
    s = pd.to_numeric(df.set_index(date_col)[series], errors="coerce").dropna()
    s.name = series
    return s


def fetch_yahoo(symbol: str) -> pd.Series:
    import yfinance as yf
    df = yf.download(symbol, period="max", progress=False, auto_adjust=True)
    if df is None or df.empty:
        raise ValueError(f"yahoo 응답 없음: {symbol}")
    close = df["Close"]
    s = (close.iloc[:, 0] if hasattr(close, "columns") else close).dropna()
    s.index = pd.to_datetime(s.index).tz_localize(None)
    s.name = symbol
    return s


def resolve(spec: dict) -> pd.Series:
    if spec["source"] == "yahoo":
        return fetch_yahoo(spec["series"])
    return fetch_fred(spec["series"])


def load_series(ind: dict) -> pd.Series:
    """일반 지표 또는 ratio(상대강도 = num/den, 표시구간 시작=100 리베이스)."""
    if ind.get("kind") == "ratio":
        num, den = resolve(ind["num"]), resolve(ind["den"])
        s = (num / den).dropna()
        s.name = ind["id"]
        return s
    return resolve(ind)


def transform(s: pd.Series, kind: str) -> pd.Series:
    if kind == "yoy":
        return (s.pct_change(12) * 100).dropna()
    if kind == "ma3":
        return s.rolling(3).mean().dropna()
    return s


def clip_years(s: pd.Series, years: int) -> pd.Series:
    if not years:
        return s
    cutoff = pd.Timestamp(date.today()) - pd.DateOffset(years=years)
    return s[s.index >= cutoff]


def recession_spans(rec: pd.Series):
    """USREC(0/1 월간)를 (시작, 끝) 구간 리스트로."""
    spans, start = [], None
    for ts, v in rec.items():
        if v == 1 and start is None:
            start = ts
        elif v == 0 and start is not None:
            spans.append((start, ts))
            start = None
    if start is not None:
        spans.append((start, rec.index[-1]))
    return spans


def plot_indicator(ind: dict, s: pd.Series, spans) -> Path:
    fig, ax = plt.subplots(figsize=(9, 4.2))
    for a, b in spans:
        if b >= s.index[0]:
            ax.axvspan(max(a, s.index[0]), b, color=C_SHADE, alpha=0.14, lw=0)
    ax.plot(s.index, s.values, color=C_LINE, lw=2)

    th = ind.get("threshold")
    if th is not None:
        ax.axhline(th["value"], color=C_THRESH, lw=1.2, ls=(0, (4, 3)))
        ax.annotate(th["label"], xy=(s.index[0], th["value"]),
                    xytext=(2, 4), textcoords="offset points",
                    color=C_THRESH, fontsize=9)

    last_ts, last_v = s.index[-1], s.values[-1]
    ax.plot([last_ts], [last_v], "o", color=C_LINE, ms=6)
    ax.annotate(f"{last_v:,.2f}{ind['unit']}", xy=(last_ts, last_v),
                xytext=(8, 0), textcoords="offset points",
                color=C_INK, fontsize=10, fontweight="bold", va="center")

    ax.set_title(ind["title"], loc="left", fontsize=13, fontweight="bold", color=C_INK, pad=26)
    src = "Yahoo Finance" if (ind.get("kind") == "ratio" or ind.get("source") == "yahoo") else "FRED"
    ax.text(0.0, 1.03, f"기준일 {last_ts.date()} · 음영=미국 경기침체(NBER) · 출처 {src}",
            transform=ax.transAxes, fontsize=8.5, color=C_MUTED)
    ax.grid(axis="y", color=C_GRID, lw=0.8)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.spines["left"].set_color(C_GRID)
    ax.spines["bottom"].set_color(C_GRID)
    ax.tick_params(colors=C_MUTED, labelsize=9)
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.margins(x=0.01)
    fig.tight_layout()

    out = CHARTS / f"{ind['id']}.png"
    fig.savefig(out)
    plt.close(fig)
    return out


def main() -> int:
    cfg = json.loads((BASE / "indicators.json").read_text())
    DATA.mkdir(exist_ok=True)
    CHARTS.mkdir(exist_ok=True)

    rec = fetch_fred(cfg["shading"]["series"])
    spans = recession_spans(rec)

    rows = []
    for ind in cfg["indicators"]:
        try:
            s = clip_years(transform(load_series(ind), ind.get("transform", "none")), ind.get("years", 0))
            if ind.get("kind") == "ratio":  # 상대강도는 표시구간 시작=100 리베이스
                s = s / s.values[0] * 100
        except Exception as e:  # 지표 하나 실패해도 나머지는 계속
            print(f"[FAIL] {ind['id']}: {e}", file=sys.stderr)
            rows.append({"id": ind["id"], "title": ind["title"], "status": f"FAIL {e}"})
            continue
        s.to_csv(DATA / f"{ind['id']}.csv")
        out = plot_indicator(ind, s, spans)
        prev = s.values[-2] if len(s) > 1 else float("nan")
        rows.append({
            "id": ind["id"], "title": ind["title"],
            "date": str(s.index[-1].date()),
            "value": f"{s.values[-1]:,.2f}{ind['unit']}",
            "prev": f"{prev:,.2f}{ind['unit']}",
            "chart": out.name, "status": "OK",
        })
        print(f"[OK] {ind['id']} -> {out.name} (latest {s.index[-1].date()} {s.values[-1]:,.2f})")

    lines = [f"# 레짐 지표 스냅샷 — {date.today()}", "",
             "| 지표 | 기준일 | 최신값 | 직전값 |", "|---|---|---|---|"]
    for r in rows:
        if r["status"] == "OK":
            lines.append(f"| {r['title']} | {r['date']} | {r['value']} | {r['prev']} |")
        else:
            lines.append(f"| {r['title']} | - | 수집 실패 | - |")
    (BASE / "summary.md").write_text("\n".join(lines) + "\n")
    print(f"summary.md + {sum(1 for r in rows if r['status']=='OK')}/{len(rows)} charts")
    return 0 if any(r["status"] == "OK" for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
