#!/usr/bin/env python3
"""알고갱즈 레짐 모니터링 대시보드 — 전 지표를 한 장(4열 그리드 스몰멀티플)으로.

각 칸: 지표명 + 최신값 + 방향 화살표(▲▼, 색=레짐 우호 여부) + 최근 3년 스파크라인.
계층(선행/동행/후행/시장)별로 행을 묶는다. fetch_regime.py가 저장한 data/*.csv를 읽는다(재수집 없음).
"""
import json
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

BASE = Path(__file__).resolve().parent

import theme
C_LINE, C_GOOD, C_BAD, C_NEUT = theme.LINE, theme.GOOD, theme.BAD, theme.NEUT
C_INK, C_MUTED, C_GRID, C_SECTION = theme.INK, theme.MUTED, theme.GRID, theme.SECTION_BG

plt.rcParams.update(theme.RC)

LAYERS = ["선행", "동행", "후행", "시장"]
COLS = 4
SPARK_YEARS = 3


def load(ind_id: str) -> pd.Series:
    df = pd.read_csv(BASE / "data" / f"{ind_id}.csv", index_col=0, parse_dates=True)
    return df.iloc[:, 0].dropna()


def fmt(v: float, unit: str) -> str:
    return f"{v:,.2f}{unit}" if abs(v) < 1000 else f"{v:,.0f}{unit}"


def main() -> int:
    cfg = json.loads((BASE / "indicators.json").read_text())
    by_layer = {L: [i for i in cfg["indicators"] if i.get("layer") == L] for L in LAYERS}

    # 행 구성: 계층 순서대로 이어붙여 4열 그리드에 배치(계층 경계에서 줄바꿈)
    cells, row_layers = [], []
    for L in LAYERS:
        items = by_layer[L]
        for r in range(0, len(items), COLS):
            row = items[r:r + COLS] + [None] * (COLS - len(items[r:r + COLS]))
            cells.append(row)
            row_layers.append(L if r == 0 else "")

    n_rows = len(cells)
    fig, axes = plt.subplots(n_rows, COLS, figsize=(12.5, 2.15 * n_rows + 0.6))
    fig.text(0.02, 1.018, f"알고갱즈 레짐 대시보드 — {date.today()}",
             ha="left", va="bottom", fontsize=15, fontweight="bold", color=C_INK)
    fig.text(0.02, 1.012, "화살표 = 직전 관측 대비 방향 · 초록=레짐 우호 / 빨강=비우호 / 회색=중립 판정 · 스파크라인=최근 3년",
             ha="left", va="top", fontsize=8.5, color=C_MUTED)

    for r in range(n_rows):
        for c in range(COLS):
            ax = axes[r][c] if n_rows > 1 else axes[c]
            ax.set_xticks([]); ax.set_yticks([])
            ind = cells[r][c]
            if ind is None:
                ax.axis("off")
                continue
            for side in ax.spines.values():
                side.set_color(C_GRID)

            s = load(ind["id"])
            cutoff = pd.Timestamp(date.today()) - pd.DateOffset(years=SPARK_YEARS)
            sp = s[s.index >= cutoff]
            last, prev = float(s.values[-1]), float(s.values[-2])
            delta = last - prev
            arrow = "▲" if delta > 0 else ("▼" if delta < 0 else "→")
            good = ind.get("good", "none")
            if good == "none" or delta == 0:
                a_color = C_NEUT
            else:
                a_color = C_GOOD if (delta > 0) == (good == "up") else C_BAD

            ax.plot(sp.index, sp.values, color=C_LINE, lw=1.4)
            ax.plot([sp.index[-1]], [sp.values[-1]], "o", color=C_LINE, ms=3.5)
            th = ind.get("threshold")
            if th is not None and sp.min() <= th["value"] <= sp.max():
                ax.axhline(th["value"], color=C_MUTED, lw=0.7, ls=(0, (3, 3)), alpha=0.6)
            ax.margins(x=0.02, y=0.1)
            ymin, ymax = ax.get_ylim()  # 상단 텍스트 밴드 확보 — 라인과 숫자 겹침 방지
            ax.set_ylim(ymin, ymax + (ymax - ymin) * 0.65)

            # 상단 텍스트 밴드: 지표명 / 최신값 + 화살표 + 델타
            ax.text(0.03, 0.93, ind["short"], transform=ax.transAxes,
                    fontsize=9.5, color=C_MUTED, va="top")
            ax.text(0.03, 0.76, fmt(last, ind["unit"]), transform=ax.transAxes,
                    fontsize=13.5, fontweight="bold", color=C_INK, va="top")
            ax.text(0.97, 0.76, f"{arrow} {delta:+,.2f}", transform=ax.transAxes,
                    fontsize=10.5, fontweight="bold", color=a_color, va="top", ha="right")

            if row_layers[r] and c == 0:
                ax.text(-0.02, 1.14, f"— {row_layers[r]} —", transform=ax.transAxes,
                        fontsize=10.5, fontweight="bold", color=C_INK, ha="left",
                        bbox=dict(fc=C_SECTION, ec="none", pad=3.2))

    fig.tight_layout(rect=(0, 0, 1, 0.96), h_pad=2.2, w_pad=1.2)
    out = BASE / "charts" / "dashboard.png"
    fig.savefig(out, bbox_inches="tight")
    print(f"[OK] {out} ({sum(len(v) for v in by_layer.values())} indicators)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
