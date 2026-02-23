"""
╔══════════════════════════════════════════════════════════════╗
║  OMEGA SOVEREIGN — THE COMMAND DECK v2.0                   ║
║  Exact Mockup Replica                                      ║
║  Streamlit + Plotly | Glassmorphism Dark Theme             ║
║                                                            ║
║  Start: streamlit run command_deck.py                      ║
╚══════════════════════════════════════════════════════════════╝
"""

import sys
import io
import math
import random
import time
from datetime import datetime, timedelta

# --- Windows UTF-8 ---
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import streamlit as st
import plotly.graph_objects as go
import numpy as np

# ══════════════════════════════════════════════════════════════
# PAGINA CONFIGURATIE
# ══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="OMEGA SOVEREIGN — Command Deck",
    page_icon="Ω",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ══════════════════════════════════════════════════════════════
# KLEUR CONSTANTEN
# ══════════════════════════════════════════════════════════════
K = {
    "bg":           "#060818",
    "card":         "rgba(12, 15, 35, 0.85)",
    "glass":        "rgba(255, 255, 255, 0.025)",
    "border":       "rgba(0, 180, 255, 0.12)",
    "cyan":         "#00E5FF",
    "blue":         "#2979FF",
    "amber":        "#FFB300",
    "emerald":      "#00C853",
    "red":          "#FF1744",
    "violet":       "#7C4DFF",
    "txt":          "#C8CCD8",
    "dim":          "rgba(255,255,255,0.35)",
    "bright":       "#FFFFFF",
    "green":        "#00FF88",
    "orange":       "#FF9100",
    "node_glow":    "#FFA726",
}

# ══════════════════════════════════════════════════════════════
# MASTER CSS — GLASSMORPHISM + HEAVY TECH v3.0
# ══════════════════════════════════════════════════════════════
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700&family=Inter:wght@300;400;500;600;700;800;900&display=swap');

    /* === GLOBALE BASIS + GRID OVERLAY === */
    .stApp {{
        background: radial-gradient(ellipse at 50% 0%, #0d1030 0%, {K["bg"]} 60%);
        color: {K["txt"]};
        font-family: 'Inter', sans-serif;
    }}
    .stApp::before {{
        content: '';
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background:
            linear-gradient(rgba(0,229,255,0.015) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0,229,255,0.015) 1px, transparent 1px);
        background-size: 60px 60px;
        pointer-events: none;
        z-index: 0;
    }}
    .stApp::after {{
        content: '';
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background: repeating-linear-gradient(
            0deg,
            transparent,
            transparent 2px,
            rgba(0,229,255,0.008) 2px,
            rgba(0,229,255,0.008) 4px
        );
        pointer-events: none;
        z-index: 0;
    }}

    #MainMenu, footer, header, .stDeployButton,
    div[data-testid="stToolbar"],
    div[data-testid="stDecoration"] {{ display:none !important; visibility:hidden !important; }}
    .block-container {{
        padding: 0.5rem 1rem 0 1rem !important;
        max-width: 100% !important;
        position: relative;
        z-index: 1;
    }}

    /* === ANIMATED SCAN LINE === */
    @keyframes scanline {{
        0% {{ top: -2px; }}
        100% {{ top: 100%; }}
    }}

    /* === TOP NAV BAR — HEAVY GLASS === */
    .topbar {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px 20px;
        background: linear-gradient(180deg, rgba(13,16,48,0.95) 0%, rgba(6,8,24,0.88) 100%);
        backdrop-filter: blur(40px) saturate(1.8);
        -webkit-backdrop-filter: blur(40px) saturate(1.8);
        border-bottom: 1px solid rgba(0,229,255,0.15);
        margin: -0.5rem -1rem 12px -1rem;
        box-shadow: 0 4px 30px rgba(0,0,0,0.5), 0 1px 0 rgba(255,255,255,0.04) inset;
        position: relative;
        overflow: hidden;
    }}
    .topbar::after {{
        content: '';
        position: absolute;
        bottom: 0; left: 0; right: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, {K["cyan"]}40, {K["violet"]}30, transparent);
    }}

    .logo-omega {{
        font-size: 38px;
        font-weight: 900;
        background: linear-gradient(135deg, {K["cyan"]}, {K["blue"]}, {K["violet"]});
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        filter: drop-shadow(0 0 20px rgba(0,229,255,0.7));
        font-family: 'Inter', sans-serif;
        animation: omega-pulse 3s ease-in-out infinite;
        position: relative;
    }}
    @keyframes omega-pulse {{
        0%, 100% {{ filter: drop-shadow(0 0 20px rgba(0,229,255,0.7)); }}
        50% {{ filter: drop-shadow(0 0 35px rgba(0,229,255,1.0)); }}
    }}

    /* Icon tabs — frosted glass capsule */
    .icon-tabs {{
        display: flex;
        gap: 2px;
        background: rgba(255,255,255,0.025);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 12px;
        padding: 3px;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.04), 0 2px 10px rgba(0,0,0,0.3);
    }}
    .icon-tab {{
        width: 36px;
        height: 30px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 8px;
        color: {K["dim"]};
        font-size: 14px;
        cursor: pointer;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    }}
    .icon-tab:hover {{
        background: rgba(0,229,255,0.1);
        color: {K["cyan"]};
        box-shadow: 0 0 12px rgba(0,229,255,0.15);
    }}
    .icon-tab.active {{
        background: linear-gradient(135deg, rgba(0,229,255,0.18), rgba(124,77,255,0.12));
        color: {K["cyan"]};
        box-shadow: 0 0 15px rgba(0,229,255,0.25), inset 0 1px 0 rgba(255,255,255,0.08);
    }}

    /* Right controls — glass orbs */
    .top-controls {{
        display: flex;
        gap: 6px;
        -webkit-app-region: no-drag;
    }}
    .ctrl-btn {{
        width: 30px; height: 30px;
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 50%;
        background: rgba(255,255,255,0.03);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        color: {K["dim"]};
        font-size: 12px;
        display: flex; align-items: center; justify-content: center;
        cursor: pointer;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        -webkit-app-region: no-drag;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.05);
    }}
    .ctrl-btn:hover {{
        background: rgba(255,255,255,0.1);
        color: {K["txt"]};
        border-color: rgba(255,255,255,0.15);
        box-shadow: 0 0 12px rgba(255,255,255,0.05);
    }}
    .ctrl-btn.btn-x:hover {{
        background: rgba(255,23,68,0.35);
        border-color: rgba(255,23,68,0.5);
        color: #fff;
        box-shadow: 0 0 15px rgba(255,23,68,0.3);
    }}

    /* === GLASS PANEL — DEEP FROSTED + TECH BORDERS === */
    .panel {{
        background: linear-gradient(135deg, rgba(12,16,45,0.55) 0%, rgba(6,8,28,0.7) 100%);
        backdrop-filter: blur(30px) saturate(1.5);
        -webkit-backdrop-filter: blur(30px) saturate(1.5);
        border: 1px solid rgba(0,180,255,0.1);
        border-radius: 16px;
        padding: 16px;
        margin-bottom: 10px;
        box-shadow:
            0 8px 32px rgba(0,0,0,0.4),
            0 0 0 1px rgba(255,255,255,0.02) inset,
            0 1px 0 rgba(255,255,255,0.04) inset;
        transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }}
    .panel::before {{
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent 10%, rgba(0,229,255,0.2) 50%, transparent 90%);
    }}
    .panel:hover {{
        border-color: rgba(0,180,255,0.25);
        box-shadow:
            0 8px 32px rgba(0,100,255,0.1),
            0 0 0 1px rgba(0,229,255,0.05) inset,
            0 1px 0 rgba(255,255,255,0.06) inset,
            0 0 40px rgba(0,229,255,0.04);
        transform: translateY(-1px);
    }}
    .panel-header {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 10px;
        font-weight: 600;
        letter-spacing: 3px;
        color: rgba(0,229,255,0.6);
        text-transform: uppercase;
        margin-bottom: 14px;
        position: relative;
        padding-left: 12px;
    }}
    .panel-header::before {{
        content: '';
        position: absolute;
        left: 0; top: 50%;
        transform: translateY(-50%);
        width: 4px; height: 4px;
        background: {K["cyan"]};
        border-radius: 50%;
        box-shadow: 0 0 8px {K["cyan"]};
    }}

    /* === VANGUARD STATUS — GLASS AGENT CARDS === */
    .vanguard-row {{
        display: flex;
        gap: 10px;
        margin-bottom: 14px;
    }}
    .vanguard-card {{
        flex: 1;
        background: linear-gradient(180deg, rgba(0,200,83,0.08) 0%, rgba(0,200,83,0.02) 100%);
        backdrop-filter: blur(15px);
        -webkit-backdrop-filter: blur(15px);
        border: 1px solid rgba(0,200,83,0.25);
        border-radius: 14px;
        padding: 16px 8px 12px 8px;
        text-align: center;
        transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow:
            0 4px 20px rgba(0,200,83,0.06),
            inset 0 1px 0 rgba(0,200,83,0.1),
            inset 0 0 20px rgba(0,200,83,0.03);
        animation: vanguard-glow 4s ease-in-out infinite;
        position: relative;
        overflow: hidden;
    }}
    .vanguard-card::before {{
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(0,200,83,0.4), transparent);
    }}
    .vanguard-card::after {{
        content: '';
        position: absolute;
        top: -50%; left: -50%;
        width: 200%; height: 200%;
        background: radial-gradient(circle, rgba(0,200,83,0.03) 0%, transparent 60%);
        pointer-events: none;
    }}
    .vanguard-card:nth-child(2) {{ animation-delay: 1.3s; }}
    .vanguard-card:nth-child(3) {{ animation-delay: 2.6s; }}
    @keyframes vanguard-glow {{
        0%, 100% {{ box-shadow: 0 4px 20px rgba(0,200,83,0.06), inset 0 1px 0 rgba(0,200,83,0.1), inset 0 0 20px rgba(0,200,83,0.03); }}
        50% {{ box-shadow: 0 4px 30px rgba(0,200,83,0.15), inset 0 1px 0 rgba(0,200,83,0.15), inset 0 0 30px rgba(0,200,83,0.06); }}
    }}
    .vanguard-card:hover {{
        border-color: rgba(0,200,83,0.5);
        box-shadow: 0 8px 35px rgba(0,200,83,0.2), inset 0 0 25px rgba(0,200,83,0.08);
        transform: translateY(-3px) scale(1.02);
    }}
    .vanguard-icon {{
        width: 52px; height: 52px;
        margin: 0 auto 8px auto;
        display: flex; align-items: center; justify-content: center;
    }}
    .vanguard-icon svg {{
        filter: drop-shadow(0 0 10px rgba(0,200,83,0.7));
    }}
    .vanguard-name {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 9px;
        font-weight: 600;
        color: {K["txt"]};
        letter-spacing: 1.5px;
        text-transform: uppercase;
    }}

    /* === HEX STATUS GRID === */
    .hex-grid {{
        display: flex;
        flex-wrap: wrap;
        justify-content: center;
        gap: 4px;
        padding: 4px 0;
    }}
    .hex-cell {{
        width: 18px; height: 18px;
        clip-path: polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%);
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    }}
    .hex-cell:hover {{ transform: scale(1.4); filter: brightness(1.5); }}
    .hex-cell.active {{ background: rgba(0,229,255,0.55); box-shadow: 0 0 8px rgba(0,229,255,0.4); }}
    .hex-cell.warm {{ background: rgba(124,77,255,0.45); }}
    .hex-cell.hot {{ background: rgba(255,167,38,0.55); }}
    .hex-cell.idle {{ background: rgba(255,255,255,0.05); }}
    .hex-cell.alert {{ background: rgba(255,23,68,0.55); animation: hex-blink 1.2s ease-in-out infinite; }}
    @keyframes hex-blink {{
        0%, 100% {{ opacity: 1; transform: scale(1); }}
        50% {{ opacity: 0.3; transform: scale(0.95); }}
    }}

    /* === CIRCULAR GAUGES (mini donuts) === */
    .gauges-row {{
        display: flex;
        gap: 10px;
        margin-top: 10px;
    }}
    .mini-gauge {{
        flex: 1;
        text-align: center;
    }}
    .gauge-circle {{
        position: relative;
        width: 56px; height: 56px;
        margin: 0 auto;
    }}
    .gauge-svg {{
        transform: rotate(-90deg);
        filter: drop-shadow(0 0 6px currentColor);
    }}
    .gauge-bg {{
        fill: none;
        stroke: rgba(255,255,255,0.04);
        stroke-width: 5;
    }}
    .gauge-fill {{
        fill: none;
        stroke-width: 5;
        stroke-linecap: round;
        transition: stroke-dashoffset 1s cubic-bezier(0.4, 0, 0.2, 1);
        filter: drop-shadow(0 0 6px currentColor);
    }}
    .gauge-val {{
        position: absolute;
        top: 50%; left: 50%;
        transform: translate(-50%, -50%);
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px;
        font-weight: 700;
        color: {K["bright"]};
        text-shadow: 0 0 8px rgba(255,255,255,0.3);
    }}
    .gauge-label {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 7px;
        color: {K["dim"]};
        letter-spacing: 1.5px;
        text-transform: uppercase;
        margin-top: 4px;
    }}

    /* === CORTEX TITLE — HOLOGRAPHIC === */
    .cortex-title {{
        text-align: center;
        margin-top: -8px;
        position: relative;
    }}
    .cortex-big {{
        font-family: 'Inter', sans-serif;
        font-size: 30px;
        font-weight: 900;
        letter-spacing: 10px;
        background: linear-gradient(135deg, {K["bright"]}, {K["cyan"]}, {K["violet"]}, {K["cyan"]});
        background-size: 300% 100%;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        filter: drop-shadow(0 0 20px rgba(0,229,255,0.4));
        text-transform: uppercase;
        animation: cortex-shimmer 6s linear infinite;
    }}
    @keyframes cortex-shimmer {{
        0% {{ background-position: 0% 50%; }}
        100% {{ background-position: 300% 50%; }}
    }}
    .cortex-sub {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 10px;
        letter-spacing: 6px;
        color: {K["dim"]};
        text-transform: uppercase;
    }}

    /* === LISTENER BAR === */
    .listener-bar {{
        text-align: center;
        padding: 10px 0 4px 0;
    }}
    .listener-label {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 10px;
        letter-spacing: 3px;
        color: rgba(0,229,255,0.5);
        animation: listener-pulse 2s ease-in-out infinite;
    }}
    @keyframes listener-pulse {{
        0%, 100% {{ color: rgba(0,229,255,0.4); }}
        50% {{ color: rgba(0,229,255,0.8); }}
    }}

    /* === PULSE PROTOCOL + FUEL GAUGE — GLASS CARDS === */
    .right-top-row {{
        display: flex;
        gap: 10px;
        margin-bottom: 10px;
    }}
    .right-top-card {{
        flex: 1;
        background: linear-gradient(135deg, rgba(12,16,45,0.5) 0%, rgba(6,8,28,0.6) 100%);
        backdrop-filter: blur(25px) saturate(1.4);
        -webkit-backdrop-filter: blur(25px) saturate(1.4);
        border: 1px solid {K["border"]};
        border-radius: 14px;
        padding: 14px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.04);
        position: relative;
        overflow: hidden;
    }}
    .right-top-card::before {{
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(0,229,255,0.15), transparent);
    }}
    .right-card-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
    }}
    .right-card-title {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 9px;
        font-weight: 600;
        letter-spacing: 2.5px;
        color: rgba(0,229,255,0.5);
        text-transform: uppercase;
    }}
    .three-dots {{
        color: {K["dim"]};
        font-size: 16px;
        cursor: pointer;
        letter-spacing: 2px;
        transition: color 0.2s;
    }}
    .three-dots:hover {{ color: {K["cyan"]}; }}

    /* === TERMINAL PANEL — DEEP GLASS + CRT === */
    .terminal-panel {{
        background: linear-gradient(180deg, rgba(6,8,22,0.92) 0%, rgba(4,6,18,0.96) 100%);
        backdrop-filter: blur(30px) saturate(1.3);
        -webkit-backdrop-filter: blur(30px) saturate(1.3);
        border: 1px solid rgba(0,180,255,0.1);
        border-radius: 14px;
        overflow: hidden;
        box-shadow: 0 8px 32px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.03);
        position: relative;
    }}
    .terminal-panel::before {{
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        background: repeating-linear-gradient(
            0deg,
            transparent,
            transparent 2px,
            rgba(0,229,255,0.006) 2px,
            rgba(0,229,255,0.006) 4px
        );
        pointer-events: none;
        z-index: 1;
    }}
    .terminal-titlebar {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 14px;
        background: linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.01));
        border-bottom: 1px solid rgba(0,229,255,0.08);
    }}
    .terminal-title {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 10px;
        font-weight: 600;
        letter-spacing: 3px;
        color: rgba(0,229,255,0.5);
    }}
    .terminal-btns {{
        display: flex; gap: 6px;
    }}
    .term-btn {{
        width: 12px; height: 12px;
        border-radius: 50%;
        border: none;
        cursor: pointer;
        box-shadow: 0 0 6px currentColor;
        transition: all 0.2s;
    }}
    .term-btn:hover {{ transform: scale(1.2); }}
    .term-btn.minimize {{ background: {K["amber"]}; box-shadow: 0 0 6px rgba(255,179,0,0.5); }}
    .term-btn.maximize {{ background: {K["emerald"]}; box-shadow: 0 0 6px rgba(0,200,83,0.5); }}
    .term-btn.close {{ background: {K["red"]}; box-shadow: 0 0 6px rgba(255,23,68,0.5); }}
    .terminal-body {{
        padding: 14px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px;
        line-height: 1.9;
        max-height: 280px;
        overflow-y: auto;
        color: {K["dim"]};
        position: relative;
        z-index: 2;
    }}
    .t-cyan {{ color: {K["cyan"]}; text-shadow: 0 0 8px rgba(0,229,255,0.3); }}
    .t-green {{ color: {K["emerald"]}; text-shadow: 0 0 8px rgba(0,200,83,0.3); }}
    .t-red {{ color: {K["red"]}; text-shadow: 0 0 8px rgba(255,23,68,0.3); }}
    .t-amber {{ color: {K["amber"]}; text-shadow: 0 0 8px rgba(255,179,0,0.3); }}
    .t-dim {{ color: rgba(255,255,255,0.3); }}
    .t-bright {{ color: rgba(255,255,255,0.75); }}

    /* === STAT TILES — GLASS + GLOW === */
    .stat-tile {{
        backdrop-filter: blur(15px);
        -webkit-backdrop-filter: blur(15px);
        border-radius: 10px;
        padding: 10px;
        text-align: center;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }}
    .stat-tile::before {{
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, currentColor, transparent);
        opacity: 0.15;
    }}
    .stat-tile:hover {{
        transform: translateY(-2px);
    }}

    /* === PLOTLY OVERRIDES === */
    .stPlotlyChart {{ border-radius: 14px; overflow: hidden; }}

    /* === SCROLLBAR — THIN GLOW === */
    ::-webkit-scrollbar {{ width: 3px; }}
    ::-webkit-scrollbar-track {{ background: transparent; }}
    ::-webkit-scrollbar-thumb {{ background: rgba(0,229,255,0.25); border-radius: 3px; box-shadow: 0 0 4px rgba(0,229,255,0.2); }}

    /* === STREAMLIT OVERRIDES === */
    div[data-testid="stHorizontalBlock"] {{ gap: 0.6rem !important; }}

    /* === STATUS BLINK === */
    @keyframes status-blink {{
        0%, 100% {{ opacity: 1; box-shadow: 0 0 8px rgba(0,200,83,0.6); }}
        50% {{ opacity: 0.5; box-shadow: 0 0 4px rgba(0,200,83,0.3); }}
    }}

    /* === TECH FRAME — corner brackets around cortex === */
    .tech-frame {{
        position: relative;
        padding: 8px;
    }}
    .tech-frame::before,
    .tech-frame::after {{
        content: '';
        position: absolute;
        width: 24px; height: 24px;
        border-color: rgba(0,229,255,0.2);
        border-style: solid;
    }}
    .tech-frame::before {{
        top: 0; left: 0;
        border-width: 1px 0 0 1px;
    }}
    .tech-frame::after {{
        top: 0; right: 0;
        border-width: 1px 1px 0 0;
    }}
    .tech-frame-bot {{
        position: relative;
    }}
    .tech-frame-bot::before,
    .tech-frame-bot::after {{
        content: '';
        position: absolute;
        width: 24px; height: 24px;
        border-color: rgba(0,229,255,0.2);
        border-style: solid;
    }}
    .tech-frame-bot::before {{
        bottom: 0; left: 8px;
        border-width: 0 0 1px 1px;
    }}
    .tech-frame-bot::after {{
        bottom: 0; right: 8px;
        border-width: 0 1px 1px 0;
    }}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# PLOTLY GENERATORS
# ══════════════════════════════════════════════════════════════

def cortex_neural_network() -> go.Figure:
    """3D neural network — batched traces voor pywebview compatibiliteit.
    Alle edges gebundeld in 3 traces (blauw/paars/cyan) ipv 40+ individuele."""
    np.random.seed(42)

    fig = go.Figure()

    # === LAAG 1: Wireframe-bol — ALLE ringen in 1 trace ===
    ring_x, ring_y, ring_z = [], [], []
    for ring_phi in np.linspace(0.3, 2.8, 6):
        ring_t = np.linspace(0, 2 * np.pi, 40)
        r_ring = 2.8 * np.sin(ring_phi)
        rx = r_ring * np.cos(ring_t)
        ry = r_ring * np.sin(ring_t)
        rz = np.full_like(ring_t, 2.8 * np.cos(ring_phi))
        ring_x.extend(rx.tolist() + [None])
        ring_y.extend(ry.tolist() + [None])
        ring_z.extend(rz.tolist() + [None])

    fig.add_trace(go.Scatter3d(
        x=ring_x, y=ring_y, z=ring_z, mode="lines",
        line=dict(color="rgba(0,229,255,0.06)", width=1),
        hoverinfo="skip", showlegend=False,
    ))

    # === LAAG 2: Kernpunten op bol (fibonacci) ===
    n_core = 45
    phi_gold = (1 + math.sqrt(5)) / 2
    idx = np.arange(n_core, dtype=float)
    theta = 2 * np.pi * idx / phi_gold
    phi_a = np.arccos(1 - 2 * (idx + 0.5) / n_core)
    r_core = 2.0 + np.random.uniform(-0.25, 0.25, n_core)
    x = r_core * np.sin(phi_a) * np.cos(theta)
    y = r_core * np.sin(phi_a) * np.sin(theta)
    z = r_core * np.cos(phi_a)

    # === LAAG 3: Binnenste cluster ===
    n_inner = 10
    idx2 = np.arange(n_inner, dtype=float)
    th2 = 2 * np.pi * idx2 / phi_gold
    ph2 = np.arccos(1 - 2 * (idx2 + 0.5) / n_inner)
    r_in = 0.9 + np.random.uniform(-0.1, 0.1, n_inner)
    xi = r_in * np.sin(ph2) * np.cos(th2)
    yi = r_in * np.sin(ph2) * np.sin(th2)
    zi = r_in * np.cos(ph2)

    all_x = np.concatenate([x, xi])
    all_y = np.concatenate([y, yi])
    all_z = np.concatenate([z, zi])
    n_all = len(all_x)

    # === EDGES: nearest-neighbor — 1 batched trace ===
    edge_x, edge_y, edge_z = [], [], []
    for i in range(n_all):
        dists = np.sqrt((all_x - all_x[i])**2 + (all_y - all_y[i])**2 + (all_z - all_z[i])**2)
        nearest = np.argsort(dists)[1:4]  # 3 nearest (was 5)
        for j in nearest:
            edge_x.extend([float(all_x[i]), float(all_x[j]), None])
            edge_y.extend([float(all_y[i]), float(all_y[j]), None])
            edge_z.extend([float(all_z[i]), float(all_z[j]), None])

    fig.add_trace(go.Scatter3d(
        x=edge_x, y=edge_y, z=edge_z, mode="lines",
        line=dict(color="rgba(80, 130, 255, 0.14)", width=1.2),
        hoverinfo="skip", showlegend=False,
    ))

    # === Paarse cross-cluster edges — 1 batched trace ===
    px, py, pz = [], [], []
    for _ in range(15):
        i = random.randint(0, n_core - 1)
        j = random.randint(n_core, n_all - 1)
        px.extend([float(all_x[i]), float(all_x[j]), None])
        py.extend([float(all_y[i]), float(all_y[j]), None])
        pz.extend([float(all_z[i]), float(all_z[j]), None])

    fig.add_trace(go.Scatter3d(
        x=px, y=py, z=pz, mode="lines",
        line=dict(color="rgba(124, 77, 255, 0.22)", width=2),
        hoverinfo="skip", showlegend=False,
    ))

    # === Cyan highlight-edges — 1 batched trace ===
    cx, cy, cz = [], [], []
    for _ in range(8):
        i, j = random.sample(range(n_core), 2)
        cx.extend([float(all_x[i]), float(all_x[j]), None])
        cy.extend([float(all_y[i]), float(all_y[j]), None])
        cz.extend([float(all_z[i]), float(all_z[j]), None])

    fig.add_trace(go.Scatter3d(
        x=cx, y=cy, z=cz, mode="lines",
        line=dict(color="rgba(0, 229, 255, 0.2)", width=2.5),
        hoverinfo="skip", showlegend=False,
    ))

    # === NODES: glow-halo + kern in 2 traces ===
    node_colors = [K["node_glow"]] * n_core + [K["cyan"]] * n_inner
    node_sizes = [5] * n_core + [6] * n_inner

    fig.add_trace(go.Scatter3d(
        x=all_x.tolist(), y=all_y.tolist(), z=all_z.tolist(), mode="markers",
        marker=dict(size=10, color="rgba(255,167,38,0.12)", line=dict(width=0)),
        hoverinfo="skip", showlegend=False,
    ))

    fig.add_trace(go.Scatter3d(
        x=all_x.tolist(), y=all_y.tolist(), z=all_z.tolist(), mode="markers",
        marker=dict(size=node_sizes, color=node_colors, opacity=0.95, line=dict(width=0)),
        hovertemplate="Node %{pointNumber}<extra></extra>",
        showlegend=False,
    ))

    fig.update_layout(
        scene=dict(
            xaxis=dict(visible=False), yaxis=dict(visible=False), zaxis=dict(visible=False),
            bgcolor="rgba(0,0,0,0)",
            camera=dict(eye=dict(x=1.5, y=1.5, z=0.8)),
            aspectmode="cube",
        ),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=0, b=0), height=420,
        showlegend=False,
    )
    return fig


def agent_radar_chart() -> go.Figure:
    """Radar/spider chart — agent performance metrics. Vervangt bars."""
    categories = ["FORGE", "VERIFY", "RESEARCH", "DREAM", "SCAN", "GUARD", "PLAN", "HEAL"]
    values = [82, 91, 65, 74, 88, 48, 70, 85]
    values_closed = values + [values[0]]
    cats_closed = categories + [categories[0]]

    fig = go.Figure()

    # Achtergrond-fill (violet)
    fig.add_trace(go.Scatterpolar(
        r=values_closed, theta=cats_closed,
        fill="toself",
        fillcolor="rgba(124,77,255,0.1)",
        line=dict(color=K["violet"], width=2),
        hoverinfo="skip",
    ))

    # Bovenliggende lijn (cyan accent)
    fig.add_trace(go.Scatterpolar(
        r=[v * 0.7 for v in values_closed], theta=cats_closed,
        fill="toself",
        fillcolor="rgba(0,229,255,0.06)",
        line=dict(color=K["cyan"], width=1.5),
        hoverinfo="skip",
    ))

    # Datapunten (glow dots)
    fig.add_trace(go.Scatterpolar(
        r=values, theta=categories,
        mode="markers",
        marker=dict(size=7, color=K["node_glow"], line=dict(width=0)),
        hovertemplate="%{theta}: %{r}%<extra></extra>",
    ))

    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(
                visible=True, range=[0, 100],
                gridcolor="rgba(255,255,255,0.04)",
                tickfont=dict(size=0), showticklabels=False,
                linewidth=0,
            ),
            angularaxis=dict(
                gridcolor="rgba(255,255,255,0.06)",
                tickfont=dict(family="JetBrains Mono", size=8, color=K["dim"]),
                linewidth=0,
            ),
        ),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=30, r=30, t=20, b=20), height=200,
        showlegend=False,
    )
    return fig


def pulse_protocol_chart() -> go.Figure:
    """ECG-style heartbeat lijn — cyan op donker."""
    t = np.linspace(0, 6 * np.pi, 300)
    y = (
        np.sin(t) * 0.2
        + np.exp(-((t % (2 * np.pi) - 1.0) ** 2) / 0.015) * 1.2
        - np.exp(-((t % (2 * np.pi) - 1.4) ** 2) / 0.04) * 0.5
        + np.random.normal(0, 0.015, len(t))
    )
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=list(range(len(t))), y=y,
        mode="lines",
        line=dict(color=K["cyan"], width=1.5, shape="spline"),
        fill="tozeroy",
        fillcolor="rgba(0,229,255,0.04)",
        hoverinfo="skip",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=0, b=0), height=80,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False, range=[-0.8, 1.5]),
        showlegend=False,
    )
    return fig


def fuel_gauge_chart(pct: float = 85) -> go.Figure:
    """Cirkelvormige fuel gauge — amber/groen."""
    bar_color = K["amber"] if pct > 70 else K["emerald"]
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=pct,
        number=dict(suffix="%", font=dict(family="JetBrains Mono", size=32, color=K["bright"])),
        gauge=dict(
            axis=dict(range=[0, 100], tickwidth=0, tickfont=dict(size=8, color=K["dim"]),
                      tickvals=[0, 30, 70, 100, 128], dtick=30),
            bar=dict(color=bar_color, thickness=0.35),
            bgcolor="rgba(255,255,255,0.03)",
            borderwidth=0,
            steps=[
                dict(range=[0, 50], color="rgba(0,200,83,0.06)"),
                dict(range=[50, 80], color="rgba(255,179,0,0.06)"),
                dict(range=[80, 100], color="rgba(255,23,68,0.06)"),
            ],
        ),
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=15, r=15, t=25, b=5), height=155,
        font=dict(color=K["dim"]),
    )
    return fig


def voice_waveform_chart() -> go.Figure:
    """Audio waveform — THE LISTENER."""
    np.random.seed(77)
    n = 200
    t = np.linspace(0, 8 * np.pi, n)
    y = (np.sin(t * 3) * 0.2 + np.sin(t * 7) * 0.12 + np.sin(t * 13) * 0.06
         + np.random.normal(0, 0.02, n))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=list(range(n)), y=np.maximum(y, 0), mode="lines",
        line=dict(color=K["cyan"], width=1.5),
        fill="tozeroy", fillcolor="rgba(0,229,255,0.1)",
        hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=list(range(n)), y=np.minimum(y, 0), mode="lines",
        line=dict(color=K["violet"], width=1.5),
        fill="tozeroy", fillcolor="rgba(124,77,255,0.1)",
        hoverinfo="skip",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=0, b=0), height=55,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False, range=[-0.4, 0.4]),
        showlegend=False,
    )
    return fig


# ══════════════════════════════════════════════════════════════
# SVG ICONS
# ══════════════════════════════════════════════════════════════

SVG_VOIDWALKER = """<svg width="42" height="50" viewBox="0 0 42 50" fill="none">
  <circle cx="21" cy="10" r="7" stroke="#00C853" stroke-width="1.5" fill="rgba(0,200,83,0.1)"/>
  <path d="M10 48 L14 28 L21 32 L28 28 L32 48" stroke="#00C853" stroke-width="1.5" fill="rgba(0,200,83,0.05)"/>
  <line x1="21" y1="18" x2="21" y2="32" stroke="#00C853" stroke-width="1.5"/>
  <line x1="10" y1="24" x2="32" y2="24" stroke="#00C853" stroke-width="1.5"/>
</svg>"""

SVG_ARTIFICER = """<svg width="42" height="50" viewBox="0 0 42 50" fill="none">
  <polygon points="21,2 38,14 34,36 8,36 4,14" stroke="#00C853" stroke-width="1.5" fill="rgba(0,200,83,0.06)"/>
  <circle cx="21" cy="20" r="6" stroke="#00C853" stroke-width="1.2" fill="rgba(0,200,83,0.1)"/>
  <line x1="21" y1="26" x2="21" y2="36" stroke="#00C853" stroke-width="1"/>
  <line x1="15" y1="31" x2="27" y2="31" stroke="#00C853" stroke-width="1"/>
</svg>"""

SVG_AUTONOMOUS = """<svg width="42" height="50" viewBox="0 0 42 50" fill="none">
  <circle cx="21" cy="25" r="18" stroke="#00C853" stroke-width="1.5" fill="rgba(0,200,83,0.04)" stroke-dasharray="4 3"/>
  <circle cx="21" cy="25" r="10" stroke="#00C853" stroke-width="1.2" fill="rgba(0,200,83,0.08)"/>
  <circle cx="21" cy="25" r="3" fill="#00C853" opacity="0.6"/>
  <line x1="21" y1="7" x2="21" y2="15" stroke="#00C853" stroke-width="1"/>
  <line x1="21" y1="35" x2="21" y2="43" stroke="#00C853" stroke-width="1"/>
  <line x1="3" y1="25" x2="11" y2="25" stroke="#00C853" stroke-width="1"/>
  <line x1="31" y1="25" x2="39" y2="25" stroke="#00C853" stroke-width="1"/>
</svg>"""


# ══════════════════════════════════════════════════════════════
# HELPER: SVG circulaire gauge
# ══════════════════════════════════════════════════════════════

def svg_donut(pct: int, color: str, label: str) -> str:
    r = 23
    circ = 2 * math.pi * r
    offset = circ * (1 - pct / 100)
    return f"""
    <div class="mini-gauge">
        <div class="gauge-circle">
            <svg class="gauge-svg" width="56" height="56" viewBox="0 0 56 56">
                <circle class="gauge-bg" cx="28" cy="28" r="{r}"/>
                <circle class="gauge-fill" cx="28" cy="28" r="{r}"
                    stroke="{color}"
                    stroke-dasharray="{circ:.1f}"
                    stroke-dashoffset="{offset:.1f}"/>
            </svg>
            <div class="gauge-val">{pct}%</div>
        </div>
        <div class="gauge-label">{label}</div>
    </div>"""


# ══════════════════════════════════════════════════════════════
# HELPER: Progress bar
# ══════════════════════════════════════════════════════════════

def hex_grid_html(n_cells: int = 48) -> str:
    """Genereer een hex status grid — elke cel representeert een systeemcomponent."""
    random.seed(99)
    states = ["active"] * 18 + ["warm"] * 10 + ["hot"] * 6 + ["idle"] * 12 + ["alert"] * 2
    random.shuffle(states)
    cells = "".join(f'<div class="hex-cell {states[i % len(states)]}"></div>' for i in range(n_cells))
    return f'<div class="hex-grid">{cells}</div>'


# ══════════════════════════════════════════════════════════════
# SECTIE 1: TOP NAVIGATION BAR
# ══════════════════════════════════════════════════════════════

st.markdown(f"""
<div class="topbar">
    <div style="display:flex;align-items:center;gap:14px;">
        <span class="logo-omega">Ω</span>
        <div style="display:flex;flex-direction:column;gap:2px;">
            <span style="font-family:JetBrains Mono;font-size:8px;letter-spacing:3px;color:rgba(0,229,255,0.4);text-transform:uppercase;">Command Deck</span>
            <div style="display:flex;align-items:center;gap:6px;">
                <div style="width:6px;height:6px;border-radius:50%;background:#00C853;box-shadow:0 0 8px rgba(0,200,83,0.6);animation:status-blink 2s ease-in-out infinite;"></div>
                <span style="font-family:JetBrains Mono;font-size:7px;letter-spacing:2px;color:rgba(0,200,83,0.5);">SYSTEMS NOMINAL</span>
            </div>
        </div>
    </div>
    <div class="icon-tabs">
        <div class="icon-tab active">&#8962;</div>
        <div class="icon-tab">&#9881;</div>
        <div class="icon-tab">&#9633;</div>
        <div class="icon-tab">&#9432;</div>
        <div class="icon-tab">&#9638;</div>
        <div class="icon-tab">&#9788;</div>
    </div>
    <div style="display:flex;align-items:center;gap:14px;">
        <span style="font-family:JetBrains Mono;font-size:8px;letter-spacing:2px;color:rgba(255,255,255,0.2);">v6.1.0</span>
        <div class="top-controls">
            <div class="ctrl-btn" onclick="if(window.pywebview)pywebview.api.minimize()">&#8722;</div>
            <div class="ctrl-btn" onclick="if(window.pywebview)pywebview.api.maximize()">&#9633;</div>
            <div class="ctrl-btn btn-x" onclick="if(window.pywebview)pywebview.api.close()">&#10005;</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# SECTIE 2: DRIEKOLOMS LAYOUT
# ══════════════════════════════════════════════════════════════

col_left, col_center, col_right = st.columns([1.15, 2.1, 1.15])


# ── LINKS: VANGUARD STATUS ──────────────────────────────────
with col_left:
  try:
    # === VANGUARD STATUS ===
    vanguard_html = f"""<div class="panel">
<div class="panel-header">Vanguard Status</div>
<div class="vanguard-row">
<div class="vanguard-card">
<div class="vanguard-icon">{SVG_VOIDWALKER}</div>
<div class="vanguard-name">VoidWalker</div>
</div>
<div class="vanguard-card">
<div class="vanguard-icon">{SVG_ARTIFICER}</div>
<div class="vanguard-name">Artificer</div>
</div>
<div class="vanguard-card">
<div class="vanguard-icon">{SVG_AUTONOMOUS}</div>
<div class="vanguard-name">Autonomous Will</div>
</div>
</div>
</div>"""
    st.markdown(vanguard_html, unsafe_allow_html=True)

    # === RADAR CHART ===
    radar_fig = agent_radar_chart()
    st.plotly_chart(radar_fig, use_container_width=True, config={"displayModeBar": False})

    # === HEX STATUS GRID ===
    hex_html = f"""<div class="panel" style="padding:12px;">
<div class="panel-header">System Heatmap</div>
{hex_grid_html(48)}
<div style="display:flex;justify-content:center;gap:12px;margin-top:8px;">
<span style="font-family:JetBrains Mono;font-size:7px;color:{K['dim']};">&#9632; ACTIVE</span>
<span style="font-family:JetBrains Mono;font-size:7px;color:{K['violet']};">&#9632; WARM</span>
<span style="font-family:JetBrains Mono;font-size:7px;color:{K['amber']};">&#9632; HOT</span>
<span style="font-family:JetBrains Mono;font-size:7px;color:{K['red']};">&#9632; ALERT</span>
</div>
</div>"""
    st.markdown(hex_html, unsafe_allow_html=True)

    # === VIOLET WAVEFORM ===
    np.random.seed(33)
    t_disc = np.linspace(0, 8 * np.pi, 200)
    y_disc = np.sin(t_disc * 1.5) * 0.4 + np.sin(t_disc * 4) * 0.15 + np.random.normal(0, 0.03, 200)
    fig_disc = go.Figure()
    fig_disc.add_trace(go.Scatter(
        x=list(range(200)), y=y_disc, mode="lines",
        line=dict(color=K["violet"], width=1.5),
        fill="tozeroy", fillcolor="rgba(124,77,255,0.08)",
        hoverinfo="skip",
    ))
    fig_disc.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=0, b=0), height=65,
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        showlegend=False,
    )
    st.plotly_chart(fig_disc, use_container_width=True, config={"displayModeBar": False})

    # === GAUGES + STATS ===
    gauges_html = f"""<div class="gauges-row">
{svg_donut(72, K["violet"], "DISCOVERY")}
{svg_donut(54, K["amber"], "NET.FS")}
{svg_donut(10, K["cyan"], "LOAD")}
</div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:10px;">
<div class="stat-tile" style="background:rgba(0,229,255,0.04);border:1px solid rgba(0,229,255,0.1);color:{K['cyan']};">
<div style="font-family:JetBrains Mono;font-size:20px;font-weight:800;color:{K['cyan']};text-shadow:0 0 12px rgba(0,229,255,0.4);">847</div>
<div style="font-family:JetBrains Mono;font-size:7px;color:{K['dim']};letter-spacing:2px;">EVENTS</div>
</div>
<div class="stat-tile" style="background:rgba(124,77,255,0.04);border:1px solid rgba(124,77,255,0.1);color:{K['violet']};">
<div style="font-family:JetBrains Mono;font-size:20px;font-weight:800;color:{K['violet']};text-shadow:0 0 12px rgba(124,77,255,0.4);">8</div>
<div style="font-family:JetBrains Mono;font-size:7px;color:{K['dim']};letter-spacing:2px;">AGENTS</div>
</div>
<div class="stat-tile" style="background:rgba(255,23,68,0.04);border:1px solid rgba(255,23,68,0.1);color:{K['red']};">
<div style="font-family:JetBrains Mono;font-size:20px;font-weight:800;color:{K['red']};text-shadow:0 0 12px rgba(255,23,68,0.4);">23</div>
<div style="font-family:JetBrains Mono;font-size:7px;color:{K['dim']};letter-spacing:2px;">FAILURES</div>
</div>
<div class="stat-tile" style="background:rgba(0,200,83,0.04);border:1px solid rgba(0,200,83,0.1);color:{K['emerald']};">
<div style="font-family:JetBrains Mono;font-size:20px;font-weight:800;color:{K['emerald']};text-shadow:0 0 12px rgba(0,200,83,0.4);">148</div>
<div style="font-family:JetBrains Mono;font-size:7px;color:{K['dim']};letter-spacing:2px;">VECTORS</div>
</div>
</div>"""
    st.markdown(gauges_html, unsafe_allow_html=True)
  except Exception as e:
    st.error(f"LEFT PANEL ERROR: {e}")


# ── CENTRUM: THE CORTEX ─────────────────────────────────────
with col_center:
  try:
    # Tech frame top
    st.markdown('<div class="tech-frame">', unsafe_allow_html=True)

    # 3D Neural Network
    cortex_fig = cortex_neural_network()
    st.plotly_chart(cortex_fig, use_container_width=True, config={
        "displayModeBar": False, "scrollZoom": True,
    })

    # CORTEX title
    st.markdown("""<div class="cortex-title">
<div class="cortex-big">CORTEX</div>
<div class="cortex-sub">Knowledge Core</div>
</div>""", unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # THE LISTENER — voice waveform
    st.markdown("""<div style="margin-top:6px;padding:10px 0 4px 0;border-top:1px solid rgba(0,229,255,0.06);">
<div style="font-family:JetBrains Mono;font-size:8px;letter-spacing:3px;color:rgba(0,229,255,0.3);text-align:center;margin-bottom:4px;">AUDIO FREQUENCY ANALYSIS</div>
</div>""", unsafe_allow_html=True)
    wave_fig = voice_waveform_chart()
    st.plotly_chart(wave_fig, use_container_width=True, config={"displayModeBar": False})
    st.markdown("""<div class="listener-bar">
<span class="listener-label">THE LISTENER &bull; VOICE ACTIVE</span>
</div>""", unsafe_allow_html=True)
  except Exception as e:
    st.error(f"CENTER PANEL ERROR: {e}")


# ── RECHTS: PULSE PROTOCOL + FUEL GAUGE + TERMINAL ──────────
with col_right:
  try:
    # Bovenste rij: Pulse Protocol + API Fuel Gauge
    st.markdown(f"""
    <div class="right-top-row">
        <div class="right-top-card">
            <div class="right-card-header">
                <span class="right-card-title">Pulse Protocol</span>
                <span class="three-dots">&bull;&bull;&bull;</span>
            </div>
        </div>
        <div class="right-top-card">
            <div class="right-card-header">
                <span class="right-card-title">API Fuel Gauge</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Pulse chart + Fuel gauge (Streamlit columns)
    c_pulse, c_fuel = st.columns(2)
    with c_pulse:
        pulse_fig = pulse_protocol_chart()
        st.plotly_chart(pulse_fig, use_container_width=True, config={"displayModeBar": False})
    with c_fuel:
        fuel_fig = fuel_gauge_chart(85)
        st.plotly_chart(fuel_fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown(f"""
        <div style="text-align:center; margin-top:-12px;">
            <span style="font-family:'JetBrains Mono'; font-size:9px; color:{K['dim']}; letter-spacing:1.5px;">
                FUEL GAUGE
            </span>
        </div>
        """, unsafe_allow_html=True)

    # === TERMINAL ===
    term_lines = [
        ("t-dim",    "/// code OFS"),
        ("t-dim",    ""),
        ("t-dim",    "const manager: CortexBridge&lt;65f8f520&gt;"),
        ("t-dim",    ""),
        ("t-bright", "function reader() &#123;"),
        ("t-bright", "  if (context.accepted) &#123;"),
        ("t-bright", "    if (ctx.fade_in_metadata()) &#123;"),
        ("t-bright", "      return coreLiaset();"),
        ("t-bright", "    &#125; else &#123;"),
        ("t-bright", "      return exits;"),
        ("t-bright", "    &#125;"),
        ("t-bright", "  &#125;"),
        ("t-bright", "&#125;"),
        ("t-dim",    ""),
        ("t-amber",  "Awaiting command &gt; _"),
    ]
    term_rows = []
    for cls, txt in term_lines:
        if txt:
            term_rows.append('<div class="' + cls + '">' + txt + '</div>')
        else:
            term_rows.append('<div>&nbsp;</div>')
    term_body = "\n".join(term_rows)

    terminal_html = (
        '<div class="terminal-panel">'
        '<div class="terminal-titlebar">'
        '<span class="terminal-title">TERMINAL</span>'
        '<div class="terminal-btns">'
        '<div class="term-btn minimize"></div>'
        '<div class="term-btn maximize"></div>'
        '<div class="term-btn close"></div>'
        '</div></div>'
        '<div class="terminal-body">'
        + term_body +
        '</div></div>'
    )
    st.markdown(terminal_html, unsafe_allow_html=True)
  except Exception as e:
    st.error(f"RIGHT PANEL ERROR: {e}")
