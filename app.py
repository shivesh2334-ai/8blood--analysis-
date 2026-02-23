"""
Comprehensive Lab Investigation Analysis Tool
=============================================
AI-Powered Multi-Panel Clinical Laboratory Analysis Platform
CBC · LFT · KFT · Lipid Profile · Diabetes · TFT · Vit D · Vit B12 · Urine R/M · Rheumatology · Oncology
"""

import re
import io
import json
import math
import datetime
import streamlit as st
from typing import Any, Dict, List, Optional

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="LabIQ — Lab Analysis Platform",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Internal imports ─────────────────────────────────────────────────────────
try:
    from utils.ocr_parser import (
        process_uploaded_file, parse_parameters,
        extract_patient_info, preprocess_text,
    )
except ImportError:
    from ocr_parser import (
        process_uploaded_file, parse_parameters,
        extract_patient_info, preprocess_text,
    )

try:
    from utils.analysis_engine import (
        REFERENCE_RANGES, PANEL_PARAMETER_MAP, PANEL_LABELS, PANEL_ICONS,
        analyze_panel, analyze_all, get_overall_severity,
        SEV_NORMAL, SEV_MILD, SEV_MODERATE, SEV_SEVERE, SEV_CRITICAL,
        STATUS_NORMAL,
    )
except ImportError:
    from analysis_engine import (
        REFERENCE_RANGES, PANEL_PARAMETER_MAP, PANEL_LABELS, PANEL_ICONS,
        analyze_panel, analyze_all, get_overall_severity,
        SEV_NORMAL, SEV_MILD, SEV_MODERATE, SEV_SEVERE, SEV_CRITICAL,
        STATUS_NORMAL,
    )

# ── Anthropic (optional) ─────────────────────────────────────────────────────
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# ─────────────────────────────────────────────────────────────────────────────
# THEME & CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;1,300&display=swap');

:root {
  --bg:        #0d1117;
  --surface:   #161b22;
  --surface2:  #1c2330;
  --border:    #30363d;
  --accent:    #2da44e;
  --accent2:   #388bfd;
  --warn:      #e3b341;
  --danger:    #f85149;
  --critical:  #ff6e40;
  --text:      #e6edf3;
  --text2:     #8b949e;
  --text3:     #6e7681;
  --normal:    #3fb950;
}

html, body, [class*="css"] {
  font-family: 'DM Sans', sans-serif;
  color: var(--text);
  background: var(--bg);
}

h1, h2, h3 { font-family: 'DM Serif Display', Georgia, serif; }

/* Sidebar */
section[data-testid="stSidebar"] {
  background: var(--surface) !important;
  border-right: 1px solid var(--border);
}
section[data-testid="stSidebar"] * { color: var(--text) !important; }

/* Main */
.main .block-container { padding: 1.5rem 2rem; max-width: 1400px; }

/* Cards */
.lab-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1.25rem 1.5rem;
  margin-bottom: 1rem;
}
.lab-card-header {
  display: flex; align-items: center; gap: .6rem;
  font-size: 1.05rem; font-weight: 600;
  margin-bottom: .75rem; padding-bottom: .5rem;
  border-bottom: 1px solid var(--border);
}

/* Status badges */
.badge-normal   { background:#0f3d2a; color:#3fb950; border:1px solid #2da44e; border-radius:20px; padding:2px 10px; font-size:.75rem; font-weight:600; }
.badge-low      { background:#1a2d4a; color:#79c0ff; border:1px solid #388bfd; border-radius:20px; padding:2px 10px; font-size:.75rem; font-weight:600; }
.badge-high     { background:#3a2000; color:#e3b341; border:1px solid #bb8009; border-radius:20px; padding:2px 10px; font-size:.75rem; font-weight:600; }
.badge-critical { background:#3d0f0f; color:#f85149; border:1px solid #da3633; border-radius:20px; padding:2px 10px; font-size:.75rem; font-weight:600; }
.badge-borderline { background:#2d2000; color:#ffa657; border:1px solid #e36209; border-radius:20px; padding:2px 10px; font-size:.75rem; font-weight:600; }

/* Parameter row */
.param-row {
  display:grid; grid-template-columns:2.5fr 1fr 1.2fr 1.8fr;
  align-items:center; gap:.5rem; padding:.45rem .5rem;
  border-radius:8px; margin-bottom:3px; font-size:.875rem;
}
.param-row:hover { background: var(--surface2); }
.param-name { font-weight:500; color:var(--text); }
.param-value { font-weight:700; color:var(--text); text-align:right; }
.param-range { color:var(--text3); font-size:.78rem; }
.param-flag-normal   { color:var(--normal); font-weight:600; }
.param-flag-low      { color:var(--accent2); font-weight:600; }
.param-flag-high     { color:var(--warn); font-weight:600; }
.param-flag-critical { color:var(--danger); font-weight:700; }

/* Alert boxes */
.alert-critical { background:#3d0f0f; border:1px solid #da3633; border-radius:8px; padding:.75rem 1rem; margin:.4rem 0; color:#f85149; }
.alert-warn     { background:#2d2200; border:1px solid #bb8009; border-radius:8px; padding:.75rem 1rem; margin:.4rem 0; color:#e3b341; }
.alert-info     { background:#0d2238; border:1px solid #1f6feb; border-radius:8px; padding:.75rem 1rem; margin:.4rem 0; color:#79c0ff; }
.alert-ok       { background:#0f3d2a; border:1px solid #2da44e; border-radius:8px; padding:.75rem 1rem; margin:.4rem 0; color:#3fb950; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
  background: var(--surface); border-radius:10px;
  border: 1px solid var(--border); padding: 4px; gap: 2px;
}
.stTabs [data-baseweb="tab"] {
  background: transparent; border-radius: 7px;
  color: var(--text2); font-weight: 500; padding: .4rem 1.1rem;
}
.stTabs [aria-selected="true"] {
  background: var(--accent) !important; color: white !important;
}

/* Buttons */
.stButton>button {
  background: var(--accent); color: white; border: none;
  border-radius: 8px; font-weight: 600; padding: .45rem 1.2rem;
  transition: all .2s;
}
.stButton>button:hover { background: #2ea043; transform: translateY(-1px); }

/* Metric override */
[data-testid="stMetricValue"] { color: var(--text) !important; }
[data-testid="stMetricLabel"] { color: var(--text2) !important; }
[data-testid="stMetricDelta"] { font-size:.8rem !important; }

/* Number inputs */
.stNumberInput input {
  background: var(--surface2) !important;
  border: 1px solid var(--border) !important;
  color: var(--text) !important; border-radius: 8px !important;
}

/* Selectbox / multiselect */
.stSelectbox>div, .stMultiSelect>div {
  background: var(--surface2) !important; color: var(--text) !important;
}

/* Text input */
.stTextInput input, .stTextArea textarea {
  background: var(--surface2) !important;
  border: 1px solid var(--border) !important;
  color: var(--text) !important; border-radius: 8px !important;
}

/* File uploader */
[data-testid="stFileUploader"] {
  background: var(--surface2); border: 2px dashed var(--border);
  border-radius: 12px;
}

/* Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: var(--surface); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }

/* Print report section */
.report-header {
  text-align:center; padding: 1.5rem 0;
  border-bottom: 2px solid var(--accent);
  margin-bottom: 1.5rem;
}
.divider { border:none; border-top:1px solid var(--border); margin:1rem 0; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE INIT
# ─────────────────────────────────────────────────────────────────────────────
def _init_state():
    defaults = {
        "extracted_text": "",
        "parsed_values":  {},
        "patient_info":   {},
        "analysis_results": {},
        "ai_review": "",
        "active_panels": ["CBC", "LFT", "KFT", "LIPID", "DIABETES", "TFT"],
        "api_key": "",
        "sex": "male",
        "age": 35,
        "manual_values": {},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
SEVERITY_COLOURS = {
    SEV_NORMAL:   "#3fb950",
    SEV_MILD:     "#e3b341",
    SEV_MODERATE: "#ffa657",
    SEV_SEVERE:   "#f85149",
    SEV_CRITICAL: "#ff6e40",
}
SEVERITY_LABELS = {
    SEV_NORMAL: "Normal", SEV_MILD: "Mild", SEV_MODERATE: "Moderate",
    SEV_SEVERE: "Severe", SEV_CRITICAL: "Critical",
}


def _sev_colour(sev: int) -> str:
    return SEVERITY_COLOURS.get(sev, "#8b949e")


def _status_badge(status: str) -> str:
    mapping = {
        "Normal": "badge-normal", "Low": "badge-low",
        "High": "badge-high",
        "Critically Low": "badge-critical", "Critically High": "badge-critical",
        "Borderline": "badge-borderline",
    }
    cls = mapping.get(status, "badge-normal")
    icons = {"Normal": "✓", "Low": "↓", "High": "↑",
              "Critically Low": "⚠", "Critically High": "⚠", "Borderline": "~"}
    icon = icons.get(status, "·")
    return f'<span class="{cls}">{icon} {status}</span>'


def _flag_class(status: str) -> str:
    mapping = {
        "Normal": "param-flag-normal",
        "Low": "param-flag-low",
        "High": "param-flag-high",
    }
    if "Critical" in status:
        return "param-flag-critical"
    return mapping.get(status, "param-flag-normal")


def safe_number_input(label, *, min_value=0.0, max_value=999_999.0,
                      value=0.0, step=0.01, fmt=None, key=None, help=None):
    """Crash-proof number_input that always clamps value into [min, max]."""
    lo = float(min_value) if min_value is not None else 0.0
    hi = float(max_value) if max_value is not None else 999_999.0
    if lo > hi:
        lo, hi = hi, lo
    v = float(value) if value is not None and not math.isnan(float(value if value else 0)) else lo
    v = max(lo, min(hi, v))
    st_fmt = fmt or ("%.3f" if step < 0.01 else "%.2f" if step < 1 else "%.1f")
    kwargs = dict(label=label, min_value=lo, max_value=hi,
                  value=v, step=float(step), format=st_fmt)
    if key:   kwargs["key"]  = key
    if help:  kwargs["help"] = help
    return st.number_input(**kwargs)


# Widget bounds per parameter (never let max_value be the normal ceiling)
_WIDGET_BOUNDS = {
    "RBC": (0.0, 15.0, 0.01), "Hemoglobin": (0.0, 25.0, 0.1),
    "Hematocrit": (0.0, 70.0, 0.1), "MCV": (0.0, 150.0, 0.1),
    "MCH": (0.0, 60.0, 0.1), "MCHC": (0.0, 45.0, 0.1),
    "RDW_CV": (0.0, 30.0, 0.1), "RDW_SD": (0.0, 80.0, 0.1),
    "WBC": (0.0, 200.0, 0.1), "Neutrophils": (0.0, 100.0, 0.1),
    "Lymphocytes": (0.0, 100.0, 0.1), "Monocytes": (0.0, 100.0, 0.1),
    "Eosinophils": (0.0, 100.0, 0.1), "Basophils": (0.0, 100.0, 0.1),
    "Bands": (0.0, 100.0, 0.1), "Platelets": (0.0, 2000.0, 1.0),
    "MPV": (0.0, 20.0, 0.1), "PDW": (0.0, 30.0, 0.1), "PCT": (0.0, 5.0, 0.01),
    "ESR": (0.0, 150.0, 1.0), "Reticulocytes": (0.0, 10.0, 0.01),
    "ANC": (0.0, 50.0, 0.1), "ALC": (0.0, 50.0, 0.1),
    "ALT": (0.0, 5000.0, 1.0), "AST": (0.0, 5000.0, 1.0),
    "ALP": (0.0, 2000.0, 1.0), "GGT": (0.0, 2000.0, 1.0), "LDH": (0.0, 5000.0, 1.0),
    "Total_Bilirubin": (0.0, 50.0, 0.01), "Direct_Bilirubin": (0.0, 30.0, 0.01),
    "Indirect_Bilirubin": (0.0, 30.0, 0.01), "Total_Protein": (0.0, 15.0, 0.1),
    "Albumin": (0.0, 10.0, 0.1), "Globulin": (0.0, 10.0, 0.1),
    "AG_Ratio": (0.0, 5.0, 0.01), "PT": (0.0, 120.0, 0.1),
    "INR": (0.0, 15.0, 0.01), "APTT": (0.0, 120.0, 0.1),
    "Serum_Ammonia": (0.0, 500.0, 1.0),
    "Serum_Creatinine": (0.0, 50.0, 0.01), "BUN": (0.0, 300.0, 1.0),
    "Serum_Urea": (0.0, 500.0, 1.0), "Serum_Uric_Acid": (0.0, 30.0, 0.1),
    "eGFR": (0.0, 200.0, 1.0), "Serum_Sodium": (80.0, 180.0, 1.0),
    "Serum_Potassium": (1.0, 10.0, 0.1), "Serum_Chloride": (70.0, 130.0, 1.0),
    "Serum_Bicarbonate": (0.0, 60.0, 1.0), "Serum_Calcium": (0.0, 20.0, 0.1),
    "Ionised_Calcium": (0.0, 5.0, 0.01), "Serum_Phosphorus": (0.0, 20.0, 0.1),
    "Serum_Magnesium": (0.0, 10.0, 0.1), "ACR": (0.0, 5000.0, 1.0),
    "Urine_Microalbumin": (0.0, 5000.0, 1.0), "Cystatin_C": (0.0, 10.0, 0.01),
    "Total_Cholesterol": (0.0, 800.0, 1.0), "HDL_Cholesterol": (0.0, 200.0, 1.0),
    "LDL_Cholesterol": (0.0, 600.0, 1.0), "VLDL_Cholesterol": (0.0, 200.0, 1.0),
    "Triglycerides": (0.0, 5000.0, 1.0), "Non_HDL_Cholesterol": (0.0, 600.0, 1.0),
    "TC_HDL_Ratio": (0.0, 20.0, 0.01), "LDL_HDL_Ratio": (0.0, 15.0, 0.01),
    "Lipoprotein_a": (0.0, 500.0, 1.0), "ApoA1": (0.0, 400.0, 1.0), "ApoB": (0.0, 400.0, 1.0),
    "Fasting_Blood_Glucose": (0.0, 600.0, 1.0), "Postprandial_Glucose": (0.0, 600.0, 1.0),
    "Random_Blood_Glucose": (0.0, 600.0, 1.0), "HbA1c": (0.0, 20.0, 0.1),
    "eAG": (0.0, 600.0, 1.0), "Fasting_Insulin": (0.0, 300.0, 0.1),
    "HOMA_IR": (0.0, 50.0, 0.01), "C_Peptide": (0.0, 20.0, 0.01),
    "TSH": (0.0, 100.0, 0.01), "Free_T3": (0.0, 30.0, 0.01),
    "Total_T3": (0.0, 500.0, 1.0), "Free_T4": (0.0, 10.0, 0.01),
    "Total_T4": (0.0, 30.0, 0.1), "Anti_TPO": (0.0, 10000.0, 1.0),
    "Anti_Thyroglobulin": (0.0, 10000.0, 1.0), "TSH_Receptor_Ab": (0.0, 100.0, 0.01),
    "Thyroglobulin": (0.0, 10000.0, 1.0), "Calcitonin": (0.0, 500.0, 0.1),
    "Vitamin_D_25OH": (0.0, 200.0, 0.1), "Vitamin_D3": (0.0, 200.0, 0.1),
    "PTH": (0.0, 2000.0, 1.0),
    "Vitamin_B12": (0.0, 3000.0, 1.0), "Serum_Folate": (0.0, 60.0, 0.1),
    "RBC_Folate": (0.0, 1500.0, 1.0), "Homocysteine": (0.0, 200.0, 0.1),
    "RA_Factor": (0.0, 500.0, 1.0), "Anti_CCP": (0.0, 500.0, 1.0),
    "CRP": (0.0, 500.0, 0.1), "hs_CRP": (0.0, 100.0, 0.01),
    "Anti_dsDNA": (0.0, 1000.0, 1.0), "C3_Complement": (0.0, 300.0, 1.0),
    "C4_Complement": (0.0, 100.0, 1.0), "ASO_Titre": (0.0, 2000.0, 1.0),
    "Ferritin": (0.0, 50000.0, 1.0), "Serum_Iron": (0.0, 500.0, 1.0),
    "TIBC": (0.0, 1000.0, 1.0), "Transferrin_Saturation": (0.0, 100.0, 0.1),
    "PSA_Total": (0.0, 10000.0, 0.01), "PSA_Free": (0.0, 1000.0, 0.01),
    "CEA": (0.0, 1000.0, 0.1), "CA_125": (0.0, 10000.0, 1.0),
    "CA_19_9": (0.0, 10000.0, 1.0), "CA_15_3": (0.0, 1000.0, 1.0),
    "CA_72_4": (0.0, 500.0, 0.1), "AFP": (0.0, 100000.0, 1.0),
    "Beta_HCG": (0.0, 1000000.0, 1.0), "NSE": (0.0, 1000.0, 0.1),
    "CYFRA_21_1": (0.0, 500.0, 0.1), "SCC_Antigen": (0.0, 100.0, 0.1),
    "Chromogranin_A": (0.0, 10000.0, 1.0), "HE4": (0.0, 3000.0, 1.0),
    "Urine_pH": (4.0, 9.0, 0.5), "Urine_Specific_Gravity": (1.000, 1.040, 0.001),
    "Urine_Pus_Cells": (0.0, 200.0, 1.0), "Urine_RBC": (0.0, 200.0, 1.0),
}

def _widget_bounds(key: str):
    return _WIDGET_BOUNDS.get(key, (0.0, 999999.0, 0.1))


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚕️ Configuration")

    # API Key
    with st.expander("🔑 Claude API Key", expanded=not bool(st.session_state.api_key)):
        api_input = st.text_input(
            "API Key", type="password",
            value=st.session_state.api_key,
            placeholder="sk-ant-...",
            help="Required for AI Review tab",
            key="api_key_input",
        )
        if api_input:
            st.session_state.api_key = api_input
        if st.session_state.api_key:
            st.success("API Key configured ✓")

    st.divider()

    # Panel selector
    st.markdown("### 🔬 Active Panels")
    all_panel_opts = list(PANEL_LABELS.keys())
    selected = st.multiselect(
        "Select investigation panels",
        options=all_panel_opts,
        default=st.session_state.active_panels,
        format_func=lambda p: f"{PANEL_ICONS.get(p, '🧪')} {PANEL_LABELS[p]}",
        key="panel_selector",
    )
    if selected:
        st.session_state.active_panels = selected

    st.divider()

    # Patient info
    st.markdown("### 👤 Patient Info")
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.sex = st.selectbox(
            "Sex", ["male", "female"],
            index=0 if st.session_state.sex == "male" else 1,
        )
    with col2:
        st.session_state.age = st.number_input(
            "Age", min_value=1, max_value=120, value=st.session_state.age,
        )

    # If patient info was extracted from OCR, show it
    pi = st.session_state.patient_info
    if pi:
        st.markdown("**Extracted patient details:**")
        for field, val in pi.items():
            st.caption(f"**{field.title()}:** {val}")

    st.divider()
    st.caption("⚠️ Educational tool only. Not for clinical decisions.")


# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center; padding:1.5rem 0 .5rem;">
  <h1 style="font-size:2.1rem; margin-bottom:.2rem;">
    🔬 Comprehensive Lab Investigation Analysis
  </h1>
  <p style="color:#8b949e; font-size:.95rem;">
    AI-Powered Multi-Panel Clinical Laboratory Analysis Platform
  </p>
  <p style="color:#6e7681; font-size:.82rem; letter-spacing:.08em;">
    CBC &bull; LFT &bull; KFT &bull; Lipid Profile &bull; Diabetes &bull;
    TFT &bull; Vit D &bull; Vit B12 &bull; Urine R/M &bull; Rheumatology &bull; Oncology
  </p>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────────
tab_upload, tab_manual, tab_analysis, tab_ai, tab_report = st.tabs([
    "📤 Upload & Extract",
    "✏️ Manual Entry",
    "📊 Analysis",
    "🤖 AI Review",
    "📄 Report",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — UPLOAD & EXTRACT
# ══════════════════════════════════════════════════════════════════════════════
with tab_upload:
    st.markdown("### 📤 Upload Lab Report")
    st.caption("Upload a PDF or image of your lab report. Text is extracted via OCR and values are auto-populated.")

    col_up, col_raw = st.columns([1, 1], gap="large")

    with col_up:
        uploaded = st.file_uploader(
            "Drop your lab report here",
            type=["pdf", "png", "jpg", "jpeg"],
            help="Supported: PDF, PNG, JPG",
        )

        if uploaded:
            with st.spinner("🔍 Extracting text and parsing values…"):
                try:
                    result = process_uploaded_file(uploaded)
                    # Handle both 4-tuple and 5-tuple returns
                    if len(result) == 5:
                        raw_text, params, grouped, panel_summary, patient_info = result
                    else:
                        raw_text, params, grouped, patient_info = result

                    st.session_state.extracted_text = raw_text
                    st.session_state.parsed_values  = {
                        k: v["value"] if isinstance(v, dict) else v
                        for k, v in params.items()
                        if isinstance(v, dict) and isinstance(v.get("value"), (int, float))
                           or isinstance(v, (int, float))
                    }
                    st.session_state.patient_info   = patient_info

                    n_found = len(st.session_state.parsed_values)
                    st.success(f"✅ Extracted {n_found} parameter{'s' if n_found != 1 else ''} successfully!")

                    # Show parsed count per panel
                    for panel_key in st.session_state.active_panels:
                        panel_params = PANEL_PARAMETER_MAP.get(panel_key, [])
                        found = [p for p in panel_params if p in st.session_state.parsed_values]
                        if found:
                            st.caption(
                                f"{PANEL_ICONS.get(panel_key, '🧪')} **{PANEL_LABELS[panel_key]}:** "
                                f"{len(found)} values found"
                            )

                except Exception as e:
                    st.error(f"Extraction error: {e}")

        # Manual text paste fallback
        with st.expander("Or paste raw lab text"):
            pasted = st.text_area(
                "Paste lab report text here",
                height=200,
                placeholder="Haemoglobin: 13.2 g/dL\nWBC: 7.5 x10⁹/L\n...",
            )
            if st.button("Parse Text", key="parse_pasted"):
                if pasted.strip():
                    with st.spinner("Parsing…"):
                        params = parse_parameters(preprocess_text(pasted))
                        pi = extract_patient_info(pasted)
                        st.session_state.extracted_text = pasted
                        st.session_state.parsed_values  = {
                            k: v["value"] if isinstance(v, dict) else v
                            for k, v in params.items()
                            if isinstance(v, dict) and isinstance(v.get("value"), (int, float))
                               or isinstance(v, (int, float))
                        }
                        st.session_state.patient_info = pi
                        st.success(f"✅ Parsed {len(st.session_state.parsed_values)} parameters.")

    with col_raw:
        if st.session_state.extracted_text:
            st.markdown("**Extracted Text Preview**")
            st.text_area(
                label="",
                value=st.session_state.extracted_text[:3000]
                      + ("…[truncated]" if len(st.session_state.extracted_text) > 3000 else ""),
                height=350,
                disabled=True,
                key="ocr_preview",
            )
        else:
            st.markdown(
                '<div class="lab-card" style="text-align:center; padding:3rem; color:#6e7681;">'
                '📄<br><br>Upload a file to see extracted text here.'
                '</div>',
                unsafe_allow_html=True,
            )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — MANUAL ENTRY
# ══════════════════════════════════════════════════════════════════════════════
with tab_manual:
    st.markdown("### ✏️ Manual Parameter Entry")
    st.caption("Enter values for any parameters not captured by OCR, or fill in manually.")

    prefilled = st.session_state.parsed_values

    # Panel sections
    active = st.session_state.active_panels

    # Show 2 panels per row
    for row_start in range(0, len(active), 2):
        row_panels = active[row_start:row_start + 2]
        cols = st.columns(len(row_panels), gap="large")
        for col, panel_key in zip(cols, row_panels):
            with col:
                icon = PANEL_ICONS.get(panel_key, "🧪")
                st.markdown(f"#### {icon} {PANEL_LABELS[panel_key]}")

                panel_params = PANEL_PARAMETER_MAP.get(panel_key, [])
                for key in panel_params:
                    ref  = REFERENCE_RANGES.get(key, {})
                    unit = ref.get("unit", "") if isinstance(ref, dict) else ""
                    desc = ref.get("description", key.replace("_", " ")) if isinstance(ref, dict) else key.replace("_", " ")
                    lo, hi, step = _widget_bounds(key)
                    prefill_val = float(prefilled.get(key, 0.0) or 0.0)

                    widget_label = f"{desc}" + (f" ({unit})" if unit else "")
                    val = safe_number_input(
                        widget_label,
                        min_value=lo, max_value=hi,
                        value=prefill_val, step=step,
                        key=f"manual_{panel_key}_{key}",
                        fmt="%.3f" if step < 0.01 else "%.2f" if step < 1.0 else "%.1f",
                    )
                    lo_thresh = lo + 1e-9
                    if val > lo_thresh:
                        st.session_state.manual_values[key] = val

    st.divider()
    if st.button("▶ Run Analysis with Manual Values", type="primary", use_container_width=True):
        # Merge OCR + manual (manual takes priority)
        merged = {**st.session_state.parsed_values, **st.session_state.manual_values}
        with st.spinner("Analysing…"):
            results = analyze_all(
                merged,
                sex=st.session_state.sex,
                age=st.session_state.age,
                active_panels=st.session_state.active_panels,
            )
            st.session_state.analysis_results = results
        st.success("✅ Analysis complete! Switch to the Analysis tab.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
with tab_analysis:
    st.markdown("### 📊 Analysis Results")

    # Auto-run if we have parsed values but no results yet
    if st.session_state.parsed_values and not st.session_state.analysis_results:
        merged = {**st.session_state.parsed_values, **st.session_state.manual_values}
        st.session_state.analysis_results = analyze_all(
            merged, sex=st.session_state.sex, age=st.session_state.age,
            active_panels=st.session_state.active_panels,
        )

    if not st.session_state.analysis_results:
        st.markdown(
            '<div class="lab-card" style="text-align:center; padding:3rem; color:#6e7681;">'
            '📊<br><br>Upload a report or enter values manually to see analysis here.'
            '</div>',
            unsafe_allow_html=True,
        )
        st.stop()

    results = st.session_state.analysis_results
    overall_sev = get_overall_severity(results)
    overall_colour = _sev_colour(overall_sev)

    # ── Overview metrics ──────────────────────────────────────────────────────
    total_params = sum(len(r.get("results", {})) for r in results.values())
    total_abnormal = sum(len(r.get("abnormal", [])) for r in results.values())
    total_critical = sum(len(r.get("critical", [])) for r in results.values())

    st.markdown(f"""
    <div class="lab-card" style="border-left:4px solid {overall_colour};">
      <div class="lab-card-header">
        Overall Status &nbsp;
        <span style="color:{overall_colour}; font-size:1rem;">
          ● {SEVERITY_LABELS.get(overall_sev, 'Unknown')}
        </span>
      </div>
      <div style="display:grid; grid-template-columns:repeat(4,1fr); gap:1rem; text-align:center;">
        <div>
          <div style="font-size:1.8rem; font-weight:700; color:var(--text)">{total_params}</div>
          <div style="color:var(--text2); font-size:.8rem">Parameters</div>
        </div>
        <div>
          <div style="font-size:1.8rem; font-weight:700; color:#3fb950">{total_params - total_abnormal}</div>
          <div style="color:var(--text2); font-size:.8rem">Normal</div>
        </div>
        <div>
          <div style="font-size:1.8rem; font-weight:700; color:#e3b341">{total_abnormal}</div>
          <div style="color:var(--text2); font-size:.8rem">Abnormal</div>
        </div>
        <div>
          <div style="font-size:1.8rem; font-weight:700; color:#f85149">{total_critical}</div>
          <div style="color:var(--text2); font-size:.8rem">Critical</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Critical alerts ───────────────────────────────────────────────────────
    all_critical = []
    for panel_key, panel_result in results.items():
        for pkey in panel_result.get("critical", []):
            r = panel_result["results"][pkey]
            all_critical.append((panel_key, pkey, r))

    if all_critical:
        st.markdown("#### ⚠️ Critical Values — Immediate Attention Required")
        for panel_key, pkey, r in all_critical:
            st.markdown(
                f'<div class="alert-critical">🚨 <strong>{r["description"]}</strong> = '
                f'{r["value"]:.2f} {r["unit"]} &nbsp;·&nbsp; {r["flag"]} &nbsp;·&nbsp; '
                f'{PANEL_LABELS.get(panel_key, panel_key)}</div>',
                unsafe_allow_html=True,
            )

    st.divider()

    # ── Per-panel results ─────────────────────────────────────────────────────
    for panel_key, panel_result in results.items():
        if not panel_result.get("results"):
            continue

        panel_sev = panel_result.get("overall_severity", SEV_NORMAL)
        panel_col = _sev_colour(panel_sev)
        icon = PANEL_ICONS.get(panel_key, "🧪")
        label = PANEL_LABELS.get(panel_key, panel_key)
        n_ab  = len(panel_result.get("abnormal", []))
        n_tot = len(panel_result.get("results", {}))

        # Collapsible panel card
        with st.expander(
            f"{icon}  {label}   —   "
            f"{n_ab}/{n_tot} abnormal",
            expanded=(panel_sev >= SEV_MILD),
        ):
            # Header row
            st.markdown(
                f'<div style="color:{panel_col}; font-size:.85rem; margin-bottom:.75rem;">'
                f'● {SEVERITY_LABELS.get(panel_sev, "Normal")}  &nbsp;|&nbsp;  '
                f'{panel_result.get("summary","")}'
                f'</div>',
                unsafe_allow_html=True,
            )

            # Column headers
            st.markdown(
                '<div class="param-row" style="border-bottom:1px solid var(--border); '
                'color:var(--text3); font-size:.78rem; font-weight:600; margin-bottom:6px;">'
                '<div>Parameter</div><div style="text-align:right">Value</div>'
                '<div>Reference Range</div><div>Status</div>'
                '</div>',
                unsafe_allow_html=True,
            )

            # Parameter rows
            for pkey, r in panel_result["results"].items():
                val_str = f"{r['value']:.2f}" if isinstance(r['value'], float) else str(r['value'])
                lo = r.get("reference_min")
                hi = r.get("reference_max")
                ref_str = (
                    f"{lo:.2f}–{hi:.2f}" if lo is not None and hi is not None
                    else f"≥{lo:.2f}" if lo is not None
                    else f"≤{hi:.2f}" if hi is not None
                    else "—"
                )
                flag_cls = _flag_class(r["status"])
                badge = _status_badge(r["status"])
                row_bg = (
                    "background:rgba(248,81,73,.06);" if "Critical" in r["status"]
                    else "background:rgba(227,179,65,.04);" if r["status"] in ("High", "Low")
                    else ""
                )
                st.markdown(
                    f'<div class="param-row" style="{row_bg}">'
                    f'<div class="param-name">{r["description"]}</div>'
                    f'<div class="param-value">{val_str} <span style="color:var(--text3);font-size:.75rem">{r["unit"]}</span></div>'
                    f'<div class="param-range">{ref_str} {r["unit"]}</div>'
                    f'<div>{badge}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                # Show interpretation for abnormals
                if r["status"] != STATUS_NORMAL and r.get("interpretation"):
                    st.caption(f"↳ {r['interpretation']}")

            # Derived values
            derived = panel_result.get("derived", {})
            if derived:
                st.markdown(
                    '<div style="color:var(--text3); font-size:.78rem; '
                    'margin-top:.75rem; margin-bottom:.3rem; font-weight:600;">'
                    'CALCULATED VALUES</div>',
                    unsafe_allow_html=True,
                )
                for dk, dv in derived.items():
                    dval = dv.get("value", "")
                    dunit = dv.get("unit", "")
                    dref  = dv.get("reference", "")
                    ddesc = dv.get("description", dk)
                    dinterp = dv.get("interpretation", "")
                    st.markdown(
                        f'<div class="param-row">'
                        f'<div class="param-name" style="color:var(--text2)">{ddesc}</div>'
                        f'<div class="param-value">{dval:.3f} <span style="color:var(--text3);font-size:.75rem">{dunit}</span></div>'
                        f'<div class="param-range">{dref}</div>'
                        f'<div style="color:var(--text3); font-size:.8rem">{dinterp}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

            # Recommendations
            recs = panel_result.get("recommendations", [])
            if recs and not (len(recs) == 1 and "No urgent" in recs[0]):
                st.markdown("**Recommendations:**")
                for rec in recs:
                    sev_class = (
                        "alert-critical" if "🚨" in rec
                        else "alert-warn" if "⚠" in rec
                        else "alert-ok"
                    )
                    st.markdown(
                        f'<div class="{sev_class}" style="font-size:.85rem;">{rec}</div>',
                        unsafe_allow_html=True,
                    )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — AI REVIEW
# ══════════════════════════════════════════════════════════════════════════════
with tab_ai:
    st.markdown("### 🤖 AI Clinical Review")
    st.caption(
        "Claude analyses your lab results holistically and provides an educational summary. "
        "**Not a substitute for medical advice.**"
    )

    if not ANTHROPIC_AVAILABLE:
        st.warning("Install the `anthropic` package: `pip install anthropic`")
    elif not st.session_state.api_key:
        st.info("Add your Claude API key in the sidebar to enable AI review.")
    elif not st.session_state.analysis_results:
        st.info("Run analysis first (upload a report or enter values manually).")
    else:
        col_opt, col_go = st.columns([3, 1])
        with col_opt:
            review_focus = st.multiselect(
                "Focus areas for AI review",
                options=st.session_state.active_panels,
                default=st.session_state.active_panels,
                format_func=lambda p: f"{PANEL_ICONS.get(p,'🧪')} {PANEL_LABELS[p]}",
            )
            clinical_context = st.text_area(
                "Clinical context (symptoms, medications, history)",
                placeholder="e.g. Type 2 DM on metformin, fatigue, family history of IHD…",
                height=80,
            )
        with col_go:
            st.markdown("<br>", unsafe_allow_html=True)
            run_ai = st.button("🤖 Generate AI Review", type="primary", use_container_width=True)

        if run_ai:
            results = st.session_state.analysis_results

            # Build compact summary for prompt
            def _fmt_results_for_prompt(results, focus):
                lines = []
                for panel_key in focus:
                    pr = results.get(panel_key, {})
                    if not pr.get("results"):
                        continue
                    lines.append(f"\n### {PANEL_LABELS.get(panel_key, panel_key)}")
                    lines.append(f"Summary: {pr.get('summary','')}")
                    for pkey, r in pr["results"].items():
                        flag = "" if r["status"] == "Normal" else f" [{r['flag']}]"
                        lines.append(
                            f"- {r['description']}: {r['value']} {r['unit']}{flag}"
                        )
                    for dk, dv in pr.get("derived", {}).items():
                        lines.append(f"  (calc) {dv.get('description',dk)}: {dv.get('value',''):.2f} {dv.get('unit','')}")
                return "\n".join(lines)

            pi = st.session_state.patient_info
            age_sex = f"Age {st.session_state.age}, {st.session_state.sex}"
            if pi.get("name"):
                age_sex = f"Patient: {pi['name']}, {age_sex}"

            lab_text = _fmt_results_for_prompt(results, review_focus)
            context_block = f"Clinical context: {clinical_context}" if clinical_context.strip() else ""

            prompt = f"""You are a clinical pathologist reviewing laboratory results for educational purposes.

Patient demographics: {age_sex}
{context_block}

LAB RESULTS:
{lab_text}

Please provide:
1. **Overall Clinical Impression** — 2-3 sentences summarising the key findings.
2. **Key Abnormalities** — Discuss each significant abnormal finding, its likely clinical significance, and differential diagnoses.
3. **Patterns & Correlations** — Identify any clinically relevant patterns across panels (e.g., anaemia + iron deficiency; CKD + hyperphosphataemia).
4. **Suggested Follow-up Investigations** — What additional tests would help clarify the picture.
5. **Clinical Recommendations** — Prioritised, actionable points (educational only).

Be concise but thorough. Use clear medical terminology. Always note that this is for educational purposes only and not a substitute for clinical evaluation."""

            with st.spinner("🤖 Claude is analysing your results…"):
                try:
                    client = anthropic.Anthropic(api_key=st.session_state.api_key)
                    response = client.messages.create(
                        model="claude-3-opus-20240229",
                        max_tokens=2000,
                        messages=[{"role": "user", "content": prompt}],
                    )
                    ai_text = response.content[0].text
                    st.session_state.ai_review = ai_text
                except Exception as e:
                    st.error(f"API error: {e}")
                    st.session_state.ai_review = ""

        if st.session_state.ai_review:
            st.markdown(
                '<div class="lab-card" style="border-left:4px solid var(--accent2);">',
                unsafe_allow_html=True,
            )
            st.markdown(st.session_state.ai_review)
            st.markdown("</div>", unsafe_allow_html=True)
            st.caption("⚠️ AI-generated educational content. Not a clinical diagnosis.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — REPORT
# ══════════════════════════════════════════════════════════════════════════════
with tab_report:
    st.markdown("### 📄 Generate Report")

    if not st.session_state.analysis_results:
        st.info("Run analysis first to generate a report.")
    else:
        pi    = st.session_state.patient_info
        today = datetime.date.today().strftime("%d %B %Y")
        results = st.session_state.analysis_results

        col_meta, col_action = st.columns([2, 1])
        with col_meta:
            report_title = st.text_input("Report Title", value="Comprehensive Lab Investigation Report")
            report_footer = st.text_input("Footer Note", value="Educational tool only — not for clinical use.")
        with col_action:
            st.markdown("<br>", unsafe_allow_html=True)
            gen_report = st.button("📄 Render Report", type="primary", use_container_width=True)

        if gen_report:
            # Build HTML report
            overall_sev  = get_overall_severity(results)
            overall_col  = _sev_colour(overall_sev)
            overall_label = SEVERITY_LABELS.get(overall_sev, "")
            total_params  = sum(len(r.get("results", {})) for r in results.values())
            total_ab      = sum(len(r.get("abnormal", [])) for r in results.values())
            total_crit    = sum(len(r.get("critical", [])) for r in results.values())

            patient_html = ""
            for field, val in pi.items():
                patient_html += f"<span><strong>{field.title()}:</strong> {val}</span> &nbsp;&nbsp; "

            def _status_col(status):
                return {"Normal": "#3fb950", "Low": "#79c0ff", "High": "#e3b341",
                        "Critically Low": "#f85149", "Critically High": "#f85149"}.get(status, "#8b949e")

            panel_sections = ""
            for panel_key, pr in results.items():
                if not pr.get("results"):
                    continue
                icon  = PANEL_ICONS.get(panel_key, "🧪")
                label = PANEL_LABELS.get(panel_key, panel_key)
                p_sev = pr.get("overall_severity", 0)
                p_col = _sev_colour(p_sev)
                rows = ""
                for pkey, r in pr["results"].items():
                    stat_col = _status_col(r["status"])
                    lo = r.get("reference_min")
                    hi = r.get("reference_max")
                    ref_str = (
                        f"{lo:.2f}–{hi:.2f}" if lo is not None and hi is not None
                        else "—"
                    )
                    bg = "#2a0f0f" if "Critical" in r["status"] else "#2a2200" if r["status"] in ("High","Low") else "transparent"
                    rows += f"""
                    <tr style="background:{bg}">
                      <td>{r['description']}</td>
                      <td style="text-align:right;font-weight:600">{r['value']:.2f}</td>
                      <td>{r['unit']}</td>
                      <td>{ref_str} {r['unit']}</td>
                      <td style="color:{stat_col};font-weight:600">{r['flag']}</td>
                    </tr>"""
                for dk, dv in pr.get("derived", {}).items():
                    rows += f"""
                    <tr style="color:#6e7681">
                      <td><em>{dv.get('description',dk)} (calc)</em></td>
                      <td style="text-align:right">{dv.get('value',0):.3f}</td>
                      <td>{dv.get('unit','')}</td>
                      <td>{dv.get('reference','')}</td>
                      <td>—</td>
                    </tr>"""

                recs_html = ""
                for rec in pr.get("recommendations", []):
                    c = "#f85149" if "🚨" in rec else "#e3b341" if "⚠" in rec else "#3fb950"
                    recs_html += f'<li style="color:{c}; margin:.2rem 0">{rec}</li>'

                panel_sections += f"""
                <div style="margin-bottom:2rem">
                  <h3 style="color:{p_col};border-bottom:1px solid #30363d;padding-bottom:.4rem">
                    {icon} {label}
                    <span style="font-size:.8rem;color:{p_col}"> ● {SEVERITY_LABELS.get(p_sev,'')}</span>
                  </h3>
                  <table style="width:100%;border-collapse:collapse;font-size:.88rem">
                    <thead><tr style="background:#1c2330;color:#8b949e;font-size:.78rem">
                      <th style="text-align:left;padding:.4rem">Parameter</th>
                      <th style="text-align:right;padding:.4rem">Value</th>
                      <th style="padding:.4rem">Unit</th>
                      <th style="padding:.4rem">Reference</th>
                      <th style="padding:.4rem">Status</th>
                    </tr></thead>
                    <tbody>{rows}</tbody>
                  </table>
                  {"<ul style='margin-top:.75rem;padding-left:1.2rem'>" + recs_html + "</ul>" if recs_html else ""}
                </div>"""

            ai_section = ""
            if st.session_state.ai_review:
                ai_section = f"""
                <div style="margin-top:2rem;padding:1rem;background:#0d2238;border-radius:8px;border:1px solid #1f6feb">
                  <h3 style="color:#79c0ff">🤖 AI Clinical Review</h3>
                  <div style="font-size:.88rem;color:#e6edf3;white-space:pre-wrap">{st.session_state.ai_review}</div>
                  <p style="color:#6e7681;font-size:.78rem;margin-top:.75rem"><em>AI-generated educational content. Not a clinical diagnosis.</em></p>
                </div>"""

            html_report = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{report_title}</title>
<style>
  body{{font-family:'Segoe UI',Arial,sans-serif;background:#0d1117;color:#e6edf3;padding:2rem;max-width:960px;margin:0 auto}}
  h1,h2,h3{{font-family:Georgia,serif}}
  table{{width:100%;border-collapse:collapse;margin:.5rem 0}}
  th,td{{padding:.35rem .5rem;border-bottom:1px solid #30363d}}
  @media print{{body{{background:white;color:black}}}}
</style>
</head>
<body>
<div style="text-align:center;padding:1.5rem 0;border-bottom:2px solid {overall_col};margin-bottom:1.5rem">
  <h1>🔬 {report_title}</h1>
  <p style="color:#8b949e">Generated: {today}</p>
  <div style="margin:.5rem 0">{patient_html}</div>
  <div style="margin-top:.75rem">
    <span style="color:{overall_col};font-size:1.1rem;font-weight:600">
      Overall: {overall_label}
    </span> &nbsp;·&nbsp;
    <span>{total_params} parameters &nbsp;·&nbsp; {total_ab} abnormal &nbsp;·&nbsp; {total_crit} critical</span>
  </div>
</div>
{panel_sections}
{ai_section}
<p style="color:#6e7681;font-size:.78rem;border-top:1px solid #30363d;padding-top:1rem;margin-top:2rem;text-align:center">
  {report_footer}
</p>
</body>
</html>"""

            st.download_button(
                label="⬇️ Download HTML Report",
                data=html_report.encode("utf-8"),
                file_name=f"lab_report_{datetime.date.today().isoformat()}.html",
                mime="text/html",
                use_container_width=True,
            )

            # Also render inline
            with st.expander("👁️ Preview Report", expanded=True):
                st.components.v1.html(html_report, height=900, scrolling=True)

        # JSON export
        with st.expander("📦 Export raw analysis JSON"):
            export = {
                "generated": today,
                "patient": st.session_state.patient_info,
                "parameters": {
                    k: v for k, v in {
                        **st.session_state.parsed_values,
                        **st.session_state.manual_values,
                    }.items()
                },
                "panels": {
                    pk: {
                        "summary": pr.get("summary", ""),
                        "overall_severity": pr.get("overall_severity", 0),
                        "abnormal": pr.get("abnormal", []),
                        "critical": pr.get("critical", []),
                    }
                    for pk, pr in st.session_state.analysis_results.items()
                },
                "ai_review": st.session_state.ai_review,
            }
            st.download_button(
                label="⬇️ Download JSON",
                data=json.dumps(export, indent=2, default=str).encode("utf-8"),
                file_name=f"lab_analysis_{datetime.date.today().isoformat()}.json",
                mime="application/json",
            )
