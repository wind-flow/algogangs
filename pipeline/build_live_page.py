#!/usr/bin/env python3
"""자립형 레짐 대시보드 페이지 생성 — WordPress·LLM 없이 정적 HTML 한 장.

GitHub Actions에서 매일 실행:
  fetch_regime.py → dashboard.py → phase_board.py → 이 스크립트
결과: build_live/ 폴더(index.html + charts/) — Pages의 /live/ 로 배포.
데이터·차트는 전부 결정론이라 맥미니·API 키가 필요 없다.
"""
import json
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent
OUT = BASE / "build_live"
KST = timezone(timedelta(hours=9))

LAYER_LABEL = {"선행": "선행지표", "동행": "동행지표", "후행": "후행지표", "시장": "시장·자산"}


def fmt(v, unit):
    return f"{v:,.2f}{unit}" if abs(v) < 1000 else f"{v:,.0f}{unit}"


def main():
    cfg = json.loads((BASE / "indicators.json").read_text())
    OUT.mkdir(exist_ok=True)
    (OUT / "charts").mkdir(exist_ok=True)

    # 규칙 기반 국면 판정 → 국면 장표 생성 (LLM 불필요)
    import classify
    import phase_board
    verdict = classify.classify()
    phase_board.render(verdict["phase"], verdict["feel"], verdict["sub"])
    print(f"[classify] {verdict['phase']} · {verdict['scores']}")

    # 시그니처 이미지 + 지표 카드 데이터
    rows = []
    for ind in cfg["indicators"]:
        csv = BASE / "data" / f"{ind['id']}.csv"
        png = BASE / "charts" / f"{ind['id']}.png"
        if not csv.exists() or not png.exists():
            continue
        shutil.copy(png, OUT / "charts" / f"{ind['id']}.png")
        lines = csv.read_text().strip().splitlines()
        last = float(lines[-1].split(",")[1])
        prev = float(lines[-2].split(",")[1]) if len(lines) > 2 else last
        delta = last - prev
        good = ind.get("good", "none")
        cls = "neutral"
        if good != "none" and delta != 0:
            cls = "good" if (delta > 0) == (good == "up") else "bad"
        rows.append({
            "id": ind["id"], "title": ind.get("short", ind["title"]),
            "layer": ind.get("layer", "시장"),
            "value": fmt(last, ind["unit"]),
            "arrow": "▲" if delta > 0 else ("▼" if delta < 0 else "→"),
            "delta": f"{delta:+,.2f}", "cls": cls,
        })

    for sig in ("dashboard.png", "phase_board.png"):
        if (BASE / "charts" / sig).exists():
            shutil.copy(BASE / "charts" / sig, OUT / "charts" / sig)

    updated = datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")

    # 계층별 지표 카드 (클릭 시 상세 차트)
    cards_html = ""
    for layer in ["선행", "동행", "후행", "시장"]:
        items = [r for r in rows if r["layer"] == layer]
        if not items:
            continue
        cards_html += f'<h2 class="layer">{LAYER_LABEL[layer]}</h2><div class="grid">'
        for r in items:
            cards_html += (
                f'<a class="card" href="charts/{r["id"]}.png" target="_blank">'
                f'<div class="ct">{r["title"]}</div>'
                f'<div class="cv">{r["value"]}</div>'
                f'<div class="cd {r["cls"]}">{r["arrow"]} {r["delta"]}</div></a>'
            )
        cards_html += "</div>"

    html = f"""<!doctype html>
<html lang="ko"><head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>알고갱즈 레짐 대시보드 (실시간)</title>
<meta name="description" content="미국 경기 사이클 레짐을 선행·동행·후행 지표로 읽는 자동 갱신 대시보드. 위폴 프레임 기반."/>
<link rel="canonical" href="https://wind-flow.github.io/algogangs/live/"/>
<style>
:root{{--bg:#131316;--surface:#1a1a19;--card:#1e1e22;--border:#2e2e33;--ink:#e8e8e4;--strong:#fff;--muted:#a9a9a2;--accent:#3987e5;--good:#3fa650;--bad:#e66767}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,"Apple SD Gothic Neo","Noto Sans KR",sans-serif;line-height:1.7;letter-spacing:-.01em;word-break:keep-all}}
.wrap{{max-width:1180px;margin:0 auto;padding:28px 18px 80px}}
header{{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:baseline;gap:8px;border-bottom:1px solid var(--border);padding-bottom:16px;margin-bottom:8px}}
h1{{font-size:1.5rem;color:var(--strong);margin:0}}
.sub{{color:var(--muted);font-size:.85rem}}
.updated{{color:var(--accent);font-size:.85rem}}
.hero{{margin:24px 0}}
.hero img{{width:100%;border:1px solid var(--border);border-radius:12px;background:var(--surface)}}
h2.layer{{font-size:1rem;color:var(--muted);text-transform:uppercase;letter-spacing:.08em;margin:32px 0 12px;border-bottom:1px solid var(--border);padding-bottom:6px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px}}
.card{{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:14px 16px;text-decoration:none;color:inherit;transition:border-color .15s}}
.card:hover{{border-color:var(--accent)}}
.ct{{color:var(--muted);font-size:.82rem;margin-bottom:6px}}
.cv{{color:var(--strong);font-size:1.35rem;font-weight:700}}
.cd{{font-size:.9rem;font-weight:700;margin-top:2px}}
.cd.good{{color:var(--good)}} .cd.bad{{color:var(--bad)}} .cd.neutral{{color:var(--muted)}}
footer{{margin-top:48px;padding-top:20px;border-top:1px solid var(--border);color:var(--muted);font-size:.8rem}}
footer a{{color:var(--accent)}}
.note{{background:var(--card);border:1px solid var(--border);border-left:3px solid var(--accent);border-radius:8px;padding:12px 16px;font-size:.85rem;color:var(--muted);margin:20px 0}}
</style></head>
<body><div class="wrap">
<header>
  <h1>알고갱즈 레짐 대시보드</h1>
  <span class="updated">자동 갱신 · {updated}</span>
</header>
<div class="sub">미국 경기 사이클을 선행·동행·후행 지표로 읽습니다. 화살표 색 = 레짐 우호(초록)/비우호(빨강). 카드를 누르면 전체 차트가 열립니다.</div>

<div class="hero"><img src="charts/phase_board.png" alt="경기 사이클 국면 장표"/></div>
<div class="hero"><img src="charts/dashboard.png" alt="레짐 지표 대시보드"/></div>

{cards_html}

<div class="note">이 페이지는 매일 자동 생성되는 데이터 요약입니다. 특정 종목의 매수·매도, 목표가·손절가를 권유하지 않으며, 투자 판단과 책임은 독자 본인에게 있습니다. 데이터: FRED · Yahoo Finance.</div>

<footer>
프레임 출처: 위폴 「경기를 보고 투자하라」 · 데이터: <a href="https://fred.stlouisfed.org/">FRED</a>, Yahoo Finance · 차트: 알고갱즈 자동 생성<br/>
&larr; <a href="../">알고갱즈 홈</a>
</footer>
</div></body></html>"""

    (OUT / "index.html").write_text(html)
    (OUT / ".nojekyll").write_text("")
    print(f"[OK] build_live/index.html ({len(rows)} indicators, updated {updated})")


if __name__ == "__main__":
    main()
