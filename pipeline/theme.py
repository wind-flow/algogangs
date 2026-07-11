"""알고갱즈 차트 공용 테마 — 기본 다크(사이트가 다크). REGIME_THEME=light 로 라이트 전환.

색은 dataviz 검증 팔레트의 모드별 스텝(라이트/다크는 '변환'이 아니라 각각 선택된 값).
"""
import os

DARK = os.environ.get("REGIME_THEME", "dark") != "light"

if DARK:
    SURFACE = "#1a1a19"
    INK = "#ffffff"
    MUTED = "#c3c2b7"
    GRID = "#3a3a38"
    LINE = "#3987e5"      # slot1 dark
    THRESH = "#e66767"    # slot6 dark
    SHADE = "#c3c2b7"     # 침체 음영(저알파)
    GOOD = "#3fa650"      # 상태색: 다크 서피스 3:1 확보 그린
    BAD = "#e66767"
    NEUT = "#c3c2b7"
    SECTION_BG = "#26262a"
    HEAD_BG = "#232325"
    HL_BG = "#1e2b40"     # 현재 국면 배경 틴트(블루)
else:
    SURFACE = "#ffffff"
    INK = "#202124"
    MUTED = "#5f6368"
    GRID = "#e8eaed"
    LINE = "#2a78d6"
    THRESH = "#e34948"
    SHADE = "#9aa0a6"
    GOOD = "#008300"
    BAD = "#e34948"
    NEUT = "#5f6368"
    SECTION_BG = "#f1f3f4"
    HEAD_BG = "#f1f3f4"
    HL_BG = "#e3edf9"

RC = {
    # Mac=Apple SD Gothic Neo, Linux(GitHub Actions)=NanumGothic 순으로 폴백
    "font.family": ["Apple SD Gothic Neo", "AppleGothic", "NanumGothic", "sans-serif"],
    "axes.unicode_minus": False,
    "figure.dpi": 150,
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
}
