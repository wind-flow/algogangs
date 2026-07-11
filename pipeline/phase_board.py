#!/usr/bin/env python3
"""위폴 경기 사이클 국면 장표 생성 — 매호 리포트 상단에 들어가는 시그니처 그래픽.

4국면 × (선행/동행/후행/시장 함의) 매트릭스에 현재 국면을 하이라이트하고
'지금 여기' 마커 + 느낌 문장을 표시한다.
사용: phase_board.py --phase 회복 --feel "둔화 탈피 초기 회복, 다만 회복의 질은 불안정" [--sub "회복 초입"]
"""
import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

BASE = Path(__file__).resolve().parent

import theme
C_HL, C_HL_BG = theme.LINE, theme.HL_BG
C_INK, C_MUTED, C_GRID, C_HEAD_BG = theme.INK, theme.MUTED, theme.GRID, theme.HEAD_BG

plt.rcParams.update(theme.RC)

PHASES = ["회복", "성장", "둔화", "침체"]
ROWS = [
    ("국면 정의", [
        "바닥 통과,\n반등이 시작되는 구간", "지표 전반이\n넓게 확장되는 구간", "정점 통과,\n속도가 꺾이는 구간", "수축이 확인된\n방어 구간",
    ]),
    ("선행지표\n(주가·심리·금리차·PMI)", [
        "반등 ↗", "상승 ↗", "하락 ↘", "하락 ↘",
    ]),
    ("동행지표\n(산업생산·소매판매)", [
        "바닥 다지기 (↘→↗)", "상승 ↗", "고점 전환 (↗→↘)", "하락 ↘",
    ]),
    ("후행지표\n(GDP·실업률)", [
        "아직 하락 ↘", "상승 ↗", "아직 상승 ↗\n(착시 주의)", "하락 ↘",
    ]),
    ("스타일·자산", [
        "미국 > 비미국 · DM > EM\n나스닥 > S&P · 대형·성장주\nUSD 우위", "신흥국·비미국 선호\n중소형(러셀2000)·시클리컬\nUSD 약세", "미국 > 비미국 · DM > EM\n다우 > S&P > 나스닥\n배당·방어·가치 · USD 강세", "DM > EM · 메가캡\n방어주·퀄리티\nUSD 초강세",
    ]),
    ("유망 섹터", [
        "IT S/W·반도체·서비스\n커뮤니케이션\n자유소비재·운송", "금융·산업재·자유소비재\n바이오·의료기기·리츠\nIT H/W·미디어·에너지·소재", "통신·제약\n필수소비재\n유틸리티", "메가캡\n유틸리티·통신",
    ]),
    ("위험자산 대응", [
        "선호 (비중 확대 국면)", "수익 실현", "분할 매수", "포지션 완료",
    ]),
]
ARROW_ROWS = {1, 2, 3}   # 화살표 방향 행 — 상승/하락 색 힌트
ACTION_ROW = len(ROWS) - 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", required=True, choices=PHASES)
    ap.add_argument("--feel", required=True, help="현재 국면에 대한 한 줄 느낌")
    ap.add_argument("--sub", default="", help="국면 부제 (예: 회복 초입)")
    args = ap.parse_args()
    return render(args.phase, args.feel, args.sub)


def render(phase, feel, sub_arg=""):
    cur = PHASES.index(phase)

    fig, ax = plt.subplots(figsize=(11.5, 8.2))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    label_w, top, head_h = 16.0, 78.0, 8.0
    col_w = (100 - label_w) / 4
    row_h = (top - head_h) / len(ROWS)

    # 현재 국면 열 배경
    x_cur = label_w + cur * col_w
    ax.add_patch(FancyBboxPatch((x_cur + 0.4, 2), col_w - 0.8, top - 1,
                                boxstyle="round,pad=0.3,rounding_size=1.2",
                                fc=C_HL_BG, ec=C_HL, lw=1.8, zorder=0))

    # 헤더
    for i, p in enumerate(PHASES):
        x = label_w + i * col_w
        if i != cur:
            ax.add_patch(FancyBboxPatch((x + 0.9, top - head_h), col_w - 1.8, head_h - 1,
                                        boxstyle="round,pad=0.2,rounding_size=0.8",
                                        fc=C_HEAD_BG, ec=C_GRID, lw=0.8))
        ax.text(x + col_w / 2, top - head_h / 2 - 0.4, p, ha="center", va="center",
                fontsize=14, fontweight="bold",
                color=(C_HL if i == cur else C_INK))

    # 셀
    for r, (label, cells) in enumerate(ROWS):
        y = top - head_h - (r + 0.5) * row_h
        ax.text(label_w - 1.5, y, label, ha="right", va="center",
                fontsize=8.8, color=C_MUTED, linespacing=1.4)
        if r > 0:
            ax.plot([1, 99], [top - head_h - r * row_h] * 2, color=C_GRID, lw=0.7, zorder=1)
        for i, cell in enumerate(cells):
            x = label_w + i * col_w + col_w / 2
            color = C_INK if i == cur else C_MUTED
            if r in ARROW_ROWS and i == cur:
                color = theme.GOOD if "↗" in cell and "착시" not in cell else (theme.BAD if "↘" in cell and "→↗" not in cell else C_INK)
            fs = 10.5 if r in ARROW_ROWS else (9.0 if r in (4, 5) else 9.3)
            ax.text(x, y, cell, ha="center", va="center", fontsize=fs,
                    color=color,
                    fontweight=("bold" if i == cur else "normal"), linespacing=1.45)
    # 대응 행 배경 강조
    y0 = top - head_h - len(ROWS) * row_h
    ax.add_patch(FancyBboxPatch((label_w + 0.6, y0 + 0.6), 100 - label_w - 1.6, row_h - 1.2,
                                boxstyle="round,pad=0.2,rounding_size=0.8",
                                fc=C_HEAD_BG, ec="none", zorder=-1))

    # '지금 여기' 마커 + 느낌 문장
    sub = f" · {sub_arg}" if sub_arg else ""
    ax.annotate(f"▼ 지금 여기{sub}", xy=(x_cur + col_w / 2, top + 4.0),
                ha="center", fontsize=12, fontweight="bold", color=C_HL)
    ax.text(50, 92.5, f"“{feel}”", ha="center", fontsize=11.5, color=C_INK, style="italic")

    ax.text(1, -3.5, "프레임: 위폴 「경기를 보고 투자하라」 · 국면 판정: 알고갱즈 레짐 리포트",
            fontsize=8, color=C_MUTED)

    fig.tight_layout()
    out = BASE / "charts" / "phase_board.png"
    fig.savefig(out, bbox_inches="tight")
    print(f"[OK] {out} phase={phase}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
