"""Minimal test — render elke sectie apart om crash te vinden."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import streamlit as st
import plotly.graph_objects as go
import numpy as np
import math, random

st.set_page_config(layout="wide", page_title="DEBUG")
st.markdown('<style>.stApp{background:#060818;color:#ccc;}</style>', unsafe_allow_html=True)

# TEST 1: Simple HTML
st.markdown("## TEST 1: HTML")
try:
    st.markdown('<div style="border:1px solid cyan;padding:10px;">HTML OK</div>', unsafe_allow_html=True)
    st.success("TEST 1 PASSED")
except Exception as e:
    st.error(f"TEST 1 FAILED: {e}")

# TEST 2: SVG in HTML
st.markdown("## TEST 2: SVG")
try:
    svg = '<svg width="40" height="40"><circle cx="20" cy="20" r="15" stroke="green" fill="none"/></svg>'
    st.markdown(f'<div style="border:1px solid green;padding:10px;">{svg} SVG OK</div>', unsafe_allow_html=True)
    st.success("TEST 2 PASSED")
except Exception as e:
    st.error(f"TEST 2 FAILED: {e}")

# TEST 3: Plotly Scatter
st.markdown("## TEST 3: Plotly Scatter")
try:
    fig = go.Figure(go.Scatter(x=[1,2,3], y=[1,3,2], mode="lines"))
    fig.update_layout(height=100, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)
    st.success("TEST 3 PASSED")
except Exception as e:
    st.error(f"TEST 3 FAILED: {e}")

# TEST 4: Plotly ScatterPolar (radar)
st.markdown("## TEST 4: Radar Chart")
try:
    fig = go.Figure(go.Scatterpolar(r=[80,90,70,60,80], theta=["A","B","C","D","A"], fill="toself"))
    fig.update_layout(height=150, paper_bgcolor="rgba(0,0,0,0)",
                      polar=dict(bgcolor="rgba(0,0,0,0)"))
    st.plotly_chart(fig, use_container_width=True)
    st.success("TEST 4 PASSED")
except Exception as e:
    st.error(f"TEST 4 FAILED: {e}")

# TEST 5: Plotly Surface + Scatter3d
st.markdown("## TEST 5: 3D Surface + Scatter3d")
try:
    u = np.linspace(0, 2*np.pi, 20)
    v = np.linspace(0, np.pi, 12)
    xm = 2*np.outer(np.cos(u), np.sin(v))
    ym = 2*np.outer(np.sin(u), np.sin(v))
    zm = 2*np.outer(np.ones(np.size(u)), np.cos(v))
    fig = go.Figure()
    fig.add_trace(go.Surface(x=xm, y=ym, z=zm, opacity=0.03, showscale=False))
    fig.add_trace(go.Scatter3d(x=[1,0,-1], y=[0,1,0], z=[0,0,1], mode="markers",
                               marker=dict(size=5, color="orange")))
    fig.update_layout(height=200, paper_bgcolor="rgba(0,0,0,0)",
                      scene=dict(bgcolor="rgba(0,0,0,0)"))
    st.plotly_chart(fig, use_container_width=True)
    st.success("TEST 5 PASSED")
except Exception as e:
    st.error(f"TEST 5 FAILED: {e}")

# TEST 6: Plotly Gauge
st.markdown("## TEST 6: Gauge")
try:
    fig = go.Figure(go.Indicator(mode="gauge+number", value=85,
                                 gauge=dict(axis=dict(range=[0,100]))))
    fig.update_layout(height=150, paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)
    st.success("TEST 6 PASSED")
except Exception as e:
    st.error(f"TEST 6 FAILED: {e}")

# TEST 7: Three columns
st.markdown("## TEST 7: Columns")
try:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c1:
        st.markdown("LEFT")
    with c2:
        st.markdown("CENTER")
    with c3:
        st.markdown("RIGHT")
    st.success("TEST 7 PASSED")
except Exception as e:
    st.error(f"TEST 7 FAILED: {e}")

st.markdown("## ALL TESTS COMPLETE")
