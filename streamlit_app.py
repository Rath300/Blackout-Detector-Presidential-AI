import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
from sklearn.ensemble import IsolationForest, RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from sklearn.preprocessing import StandardScaler
from datetime import date, datetime, timedelta
import json
import warnings
import requests
warnings.filterwarnings('ignore')

# ==================== CONFIGURATION ====================
MAX_FILE_SIZE = 100_000_000  # 100MB
MIN_DATA_ROWS = 10
DEFAULT_CONTAMINATION = 0.02

# ==================== CUSTOM STYLING ====================
# ==================== CUSTOM STYLING ====================
def apply_custom_styling():
    """Apply custom CSS with dark blue, light blue, yellow, white theme."""
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
    /* HUGE Main title - FIXED */
    .main-title {
    font-size: 8rem !important;
    font-weight: 900 !important;
    background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 25%, #3b82f6 75%, #1e3a8a 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-align: center;
    margin: 2rem 0 1rem 0 !important;
    padding: 1rem 0;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    letter-spacing: -2px;
    line-height: 1.1 !important;
}
    
    .tagline {
    font-size: 3rem !important;
    font-weight: 600 !important;
    color: white;
    text-align: center;
    margin: 0 0 3rem 0 !important;
    letter-spacing: 3px;
    line-height: 1.2 !important;
}
    
    .subtitle {
        font-size: 1.5rem;
        color: #1e3a8a;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: 500;
    }
    
    /* Dark blue cards */
    .metric-card-dark {
        background: linear-gradient(135deg, #1e3a8a 0%, #1e40af 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        box-shadow: 0 10px 30px rgba(30, 58, 138, 0.4);
        margin: 0.5rem 0;
    }
    
    /* Light blue cards */
    .metric-card-light {
        background: linear-gradient(135deg, #3b82f6 0%, #60a5fa 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        box-shadow: 0 10px 30px rgba(59, 130, 246, 0.4);
        margin: 0.5rem 0;
    }
    
    /* Yellow cards */
    .metric-card-yellow {
        background: linear-gradient(135deg, #fbbf24 0%, #fcd34d 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: #1e3a8a;
        box-shadow: 0 10px 30px rgba(251, 191, 36, 0.4);
        margin: 0.5rem 0;
    }
    
    /* Light blue background cards with dark text */
    .blue-card {
        background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: #1e3a8a;
        box-shadow: 0 5px 20px rgba(59, 130, 246, 0.2);
        margin: 1rem 0;
        border-left: 5px solid #3b82f6;
    }
    
    .blue-card h3, .blue-card h4 {
        color: #1e3a8a;
    }
    
    .blue-card p {
        color: #1e40af;
    }
    
    /* Yellow background cards */
    .yellow-card {
        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: #1e3a8a;
        box-shadow: 0 5px 20px rgba(251, 191, 36, 0.2);
        margin: 1rem 0;
        border-left: 5px solid #fbbf24;
    }
    
    .yellow-card h3, .yellow-card h4 {
        color: #1e3a8a;
    }
    
    .yellow-card p {
        color: #1e40af;
    }
    
    /* Info boxes */
    .info-box {
        background: linear-gradient(135deg, #3b82f6 0%, #60a5fa 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        margin: 1rem 0;
        box-shadow: 0 10px 30px rgba(59, 130, 246, 0.3);
    }
    
    .info-box h3, .info-box h4 {
        color: white;
    }
    
    .success-box {
        background: linear-gradient(135deg, #10b981 0%, #34d399 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        margin: 1rem 0;
    }
    
    .warning-box {
        background: linear-gradient(135deg, #fbbf24 0%, #fcd34d 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: #1e3a8a;
        margin: 1rem 0;
    }
    
    .warning-box h3 {
        color: #1e3a8a;
    }
    
    /* Buttons */
    .stButton>button {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        color: white;
        border: none;
        padding: 0.75rem 2rem;
        border-radius: 25px;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s ease;
        box-shadow: 0 5px 15px rgba(30, 58, 138, 0.4);
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(30, 58, 138, 0.6);
    }
    
    .section-header {
        font-size: 2rem;
        font-weight: 700;
        color: #1e3a8a;
        margin: 2rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 3px solid #fbbf24;
    }
    
    /* Testimonials */
    .testimonial {
        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
        padding: 1.5rem;
        border-radius: 15px;
        margin: 1rem 0;
        font-style: italic;
        border-left: 4px solid #1e3a8a;
        color: #1e3a8a;
        box-shadow: 0 5px 15px rgba(0,0,0,0.08);
    }
    
    .step-number {
        display: inline-block;
        width: 40px;
        height: 40px;
        background: linear-gradient(135deg, #fbbf24 0%, #fcd34d 100%);
        color: #1e3a8a;
        border-radius: 50%;
        text-align: center;
        line-height: 40px;
        font-weight: 700;
        margin-right: 1rem;
    }
    
    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1rem;
        background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
        padding: 0.5rem;
        border-radius: 10px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: white;
        color: #1e3a8a;
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
    }
    
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        color: white;
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        background: linear-gradient(135deg, #3b82f6 0%, #60a5fa 100%);
        color: white;
        border-radius: 10px;
        font-weight: 600;
    }
    
    /* AI Insights card */
    .ai-insight-card {
        background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
        padding: 2rem;
        border-radius: 15px;
        color: #1e3a8a;
        box-shadow: 0 10px 30px rgba(59, 130, 246, 0.3);
        margin: 1.5rem 0;
        border: 3px solid #3b82f6;
    }
    
    .ai-insight-card h3 {
        color: #1e3a8a;
        margin-top: 0;
        font-size: 1.8rem;
    }
    
    /* ========== SIDEBAR STYLING ========== */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
        padding: 1.5rem 1rem;
    }
    
    [data-testid="stSidebar"] * {
        font-family: 'Inter', sans-serif !important;
    }
    
    [data-testid="stSidebar"] .stMarkdown {
        color: white;
    }
    
    /* Section headers in sidebar */
    [data-testid="stSidebar"] h3 {
        color: #fbbf24 !important;
        font-weight: 700 !important;
        font-size: 0.85rem !important;
        margin-top: 0 !important;
        margin-bottom: 1rem !important;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        text-align: center;
    }
    
    /* Horizontal rules */
    [data-testid="stSidebar"] hr {
        margin: 1.5rem 0 !important;
        border: none !important;
        height: 1px !important;
        background: rgba(251, 191, 36, 0.3) !important;
    }
    
    /* Hide collapse button text but keep button functional */
    [data-testid="stSidebar"] [data-testid="collapsedControl"] span {
        font-size: 0 !important;
        width: 0 !important;
        height: 0 !important;
        overflow: hidden !important;
        text-indent: -9999px !important;
    }
    
    [data-testid="stSidebar"] button[kind="header"] span {
        font-size: 0 !important;
        text-indent: -9999px !important;
        display: inline-block !important;
        width: 0 !important;
        overflow: hidden !important;
    }
    
    [data-testid="stSidebar"] button[kind="header"] {
        color: #fbbf24 !important;
        background: rgba(251, 191, 36, 0.1) !important;
        border-radius: 8px !important;
        padding: 0.5rem !important;
    }
    
    [data-testid="stSidebar"] button[kind="header"]:hover {
        background: rgba(251, 191, 36, 0.2) !important;
    }
    
    /* ========== FILE UPLOADER ========== */
    [data-testid="stSidebar"] [data-testid="stFileUploader"] {
        background: rgba(255, 255, 255, 0.03);
        border: 2px dashed rgba(251, 191, 36, 0.4);
        border-radius: 12px;
        padding: 1.5rem 1rem;
    }
    
    [data-testid="stSidebar"] [data-testid="stFileUploader"] label {
        color: #fbbf24 !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        text-align: center !important;
        display: block !important;
    }
    
    [data-testid="stSidebar"] [data-testid="stFileUploader"] button {
        background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%) !important;
        color: #0f172a !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.6rem 1.5rem !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        width: 100% !important;
        margin-top: 0.5rem !important;
    }
    
    /* ========== SETTINGS SECTION ========== */
    [data-testid="stSidebar"] .stSlider,
    [data-testid="stSidebar"] .stSelectbox {
        background: rgba(255, 255, 255, 0.03);
        padding: 1rem;
        border-radius: 10px;
        border: 1px solid rgba(251, 191, 36, 0.2);
        margin-bottom: 1rem;
    }
    
    [data-testid="stSidebar"] .stSlider label,
    [data-testid="stSidebar"] .stSelectbox label {
        color: rgba(255, 255, 255, 0.95) !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        margin-bottom: 0.75rem !important;
        display: block !important;
    }
    
    /* Slider styling - DEFAULT STREAMLIT BEHAVIOR */
    
    /* Selectbox styling */
    [data-testid="stSidebar"] .stSelectbox select {
        background: rgba(255, 255, 255, 0.1) !important;
        border: 1px solid rgba(251, 191, 36, 0.3) !important;
        border-radius: 8px !important;
        color: white !important;
        padding: 0.65rem !important;
        font-size: 0.9rem !important;
        font-weight: 500 !important;
    }
    
    [data-testid="stSidebar"] .stSelectbox select:focus {
        border-color: #fbbf24 !important;
        box-shadow: 0 0 0 1px #fbbf24 !important;
    }
    
    /* ========== TEXT INPUT (ZAPIER) ========== */
    [data-testid="stSidebar"] .stTextInput {
        background: rgba(255, 255, 255, 0.03);
        padding: 1rem;
        border-radius: 10px;
        border: 1px solid rgba(251, 191, 36, 0.2);
        margin-bottom: 1rem;
    }
    
    [data-testid="stSidebar"] .stTextInput label {
        color: rgba(255, 255, 255, 0.95) !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        margin-bottom: 0.5rem !important;
    }
    
    [data-testid="stSidebar"] .stTextInput input {
        background: rgba(255, 255, 255, 0.1) !important;
        border: 1px solid rgba(251, 191, 36, 0.3) !important;
        border-radius: 8px !important;
        color: white !important;
        padding: 0.65rem !important;
        font-size: 0.85rem !important;
    }
    
    [data-testid="stSidebar"] .stTextInput input:focus {
        border-color: #fbbf24 !important;
        box-shadow: 0 0 0 1px #fbbf24 !important;
    }
    
    [data-testid="stSidebar"] .stTextInput input::placeholder {
        color: rgba(255, 255, 255, 0.4) !important;
    }
    
    /* ========== SIDEBAR BUTTONS ========== */
    [data-testid="stSidebar"] .stButton button {
        background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%) !important;
        color: #0f172a !important;
        border: none !important;
        padding: 0.7rem 1.5rem !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        transition: all 0.2s ease !important;
        width: 100% !important;
        box-shadow: 0 2px 8px rgba(251, 191, 36, 0.3) !important;
    }
    
    [data-testid="stSidebar"] .stButton button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 12px rgba(251, 191, 36, 0.5) !important;
    }
    
    /* Primary button style (selected navigation) */
    [data-testid="stSidebar"] .stButton button[kind="primary"] {
        background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%) !important;
        color: #0f172a !important;
        font-weight: 700 !important;
    }
    
    /* Secondary button style (unselected navigation) */
    [data-testid="stSidebar"] .stButton button[kind="secondary"] {
        background: rgba(255, 255, 255, 0.05) !important;
        color: rgba(255, 255, 255, 0.9) !important;
        font-weight: 500 !important;
        border: 1px solid rgba(251, 191, 36, 0.2) !important;
    }
    
    [data-testid="stSidebar"] .stButton button[kind="secondary"]:hover {
        background: rgba(251, 191, 36, 0.1) !important;
        border-color: rgba(251, 191, 36, 0.3) !important;
    }
    
    /* ========== EXPANDER (ZAPIER GUIDE) - FIXED ========== */
    [data-testid="stSidebar"] .streamlit-expanderHeader {
        background: rgba(251, 191, 36, 0.08) !important;
        color: white !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        padding: 0.75rem 0.85rem !important;
        border: 1px solid rgba(251, 191, 36, 0.25) !important;
        white-space: normal !important;
        word-wrap: break-word !important;
        line-height: 1.3 !important;
        min-height: auto !important;
        height: auto !important;
    }
    
    [data-testid="stSidebar"] .streamlit-expanderHeader p {
        margin: 0 !important;
        padding: 0 !important;
        font-size: 0.85rem !important;
    }
    
    [data-testid="stSidebar"] .streamlit-expanderHeader:hover {
        background: rgba(251, 191, 36, 0.15) !important;
        border-color: rgba(251, 191, 36, 0.4) !important;
    }
    
    [data-testid="stSidebar"] [data-testid="stExpander"] {
        border: none !important;
        background: transparent !important;
    }
    
    [data-testid="stSidebar"] .streamlit-expanderContent {
        background: rgba(255, 255, 255, 0.02) !important;
        border: 1px solid rgba(251, 191, 36, 0.15) !important;
        border-radius: 8px !important;
        padding: 1rem !important;
        margin-top: 0.5rem !important;
    }
    
    /* ========== HELPER TEXT ========== */
    [data-testid="stSidebar"] .stMarkdown p {
        color: rgba(255, 255, 255, 0.8) !important;
        font-size: 0.85rem !important;
        line-height: 1.5 !important;
    }
    
    /* ========== SUCCESS/ERROR MESSAGES ========== */
    [data-testid="stSidebar"] .stSuccess {
        background: rgba(16, 185, 129, 0.15) !important;
        color: #10b981 !important;
        font-size: 0.85rem !important;
        padding: 0.65rem !important;
        border-radius: 6px !important;
        border: 1px solid rgba(16, 185, 129, 0.3) !important;
    }
    
    [data-testid="stSidebar"] .stError {
        background: rgba(239, 68, 68, 0.15) !important;
        color: #ef4444 !important;
        font-size: 0.85rem !important;
        padding: 0.65rem !important;
        border-radius: 6px !important;
        border: 1px solid rgba(239, 68, 68, 0.3) !important;
    }
    </style>
    """, unsafe_allow_html=True)

# ==================== SMART COLUMN DETECTION ====================
@st.cache_data
def intelligent_column_mapper(df):
    """Advanced column detection for solar data."""
    col_map = {}
    aliases = {
        'timestamp': ['timestamp', 'datetime', 'date_time', 'date', 'time', 'recorded', 'period', 'ts', 'dt'],
        'ac_power': ['ac_power', 'acpower', 'ac_output', 'ac', 'ac(kw)', 'ac_kw', 'ac_watts', 'output'],
        'dc_power': ['dc_power', 'dcpower', 'dc_input', 'dc', 'dc(kw)', 'dc_kw', 'dc_watts', 'input'],
        'efficiency': ['efficiency', 'eff', 'conversion', 'yield', 'performance'],
        'energy': ['energy', 'kwh', 'wh', 'generation', 'production'],
        'source': ['source_key', 'source', 'inverter', 'device', 'id', 'unit', 'device_id']
    }

    for key, alias_list in aliases.items():
        for alias in alias_list:
            exact = [c for c in df.columns if c.lower() == alias.lower()]
            if exact:
                col_map[key] = exact[0]
                break
            partial = [c for c in df.columns if alias.lower() in c.lower()]
            if partial:
                col_map[key] = partial[0]
                break
    return col_map

# ==================== DATA LOADING ====================
def preprocess_inverter_data(df):
    """Preprocess inverter-specific data with enhanced accuracy."""
    try:
        df['SOURCE_KEY'] = df['SOURCE_KEY'].fillna('UNKNOWN')
        unique_ids = df['SOURCE_KEY'].unique()
        id_mapping = {uid: f"S{i+1}" for i, uid in enumerate(unique_ids)}
        df['SOURCE_ID'] = df['SOURCE_KEY'].map(id_mapping)
        df['SOURCE_ID_NUMBER'] = df['SOURCE_ID'].str.extract(r'(\d+)').astype(int)
        df['DATE_TIME'] = pd.to_datetime(df['DATE_TIME'], errors='coerce')
        df = df.dropna(subset=['DATE_TIME'])
        
        df.rename(columns={'AC_POWER': 'AC_POWER_OUTPUT', 'DC_POWER': 'DC_POWER_INPUT'}, inplace=True)
        df['AC_POWER_FIXED'] = df['AC_POWER_OUTPUT'] * 10
        df['DC_POWER_INPUT'] = df['DC_POWER_INPUT'].replace(0, np.nan)
        df['EFFICIENCY'] = df['AC_POWER_FIXED'] / df['DC_POWER_INPUT']
        df['EFFICIENCY_%'] = df['EFFICIENCY'] * 100
        df['EFFICIENCY_%'] = df['EFFICIENCY_%'].clip(0, 100)
        
        df['Value'] = df['AC_POWER_FIXED']
        df = df.loc[:, ~df.columns.duplicated()]
        
        if 'TIME_STAMP' not in df.columns:
            df.rename(columns={'DATE_TIME': 'TIME_STAMP'}, inplace=True)
        
        df = df[['TIME_STAMP', 'SOURCE_ID', 'SOURCE_ID_NUMBER', 'Value', 'EFFICIENCY_%', 'AC_POWER_FIXED']]
        df = df.sort_values("TIME_STAMP").reset_index(drop=True)
        df["time_index"] = range(len(df))
        return df
    except Exception as e:
        st.error(f"❌ Error preprocessing data: {str(e)}")
        return None

@st.cache_data
def load_clean_data(file_content):
    """Universal solar data loader with enhanced validation."""
    try:
        df = pd.read_csv(file_content)
    except Exception as e:
        st.error(f"❌ Could not read file: {str(e)}")
        return pd.DataFrame()
    
    if df.empty:
        st.warning("⚠️ The file appears to be empty")
        return pd.DataFrame()
    
    with st.expander("📋 Detected Columns in Your File"):
        st.write(", ".join(df.columns.tolist()))
    
    if 'SOURCE_KEY' in df.columns and 'DATE_TIME' in df.columns:
        processed = preprocess_inverter_data(df)
        if processed is not None and not processed.empty:
            st.success("✅ Recognized as solar inverter data format")
            return processed
    
    col_map = intelligent_column_mapper(df)
    if not col_map or 'timestamp' not in col_map:
        st.error("❌ Could not find required columns")
        return pd.DataFrame()
    
    df['TIME_STAMP'] = pd.to_datetime(df[col_map['timestamp']], errors='coerce')
    df = df.dropna(subset=['TIME_STAMP'])
    
    value_candidates = [col_map.get('ac_power'), col_map.get('dc_power'), col_map.get('energy')]
    value_col = next((c for c in value_candidates if c and c in df.columns), None)
    
    if not value_col:
        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        value_col = num_cols[0] if num_cols else None
    
    if not value_col:
        st.error("❌ Could not find numeric data")
        return pd.DataFrame()
    
    df['Value'] = pd.to_numeric(df[value_col], errors='coerce')
    df = df.dropna(subset=['Value'])
    df = df.sort_values("TIME_STAMP").reset_index(drop=True)
    df['time_index'] = range(len(df))
    
    if 'ac_power' in col_map and 'dc_power' in col_map:
        df['AC_POWER_FIXED'] = pd.to_numeric(df[col_map['ac_power']], errors='coerce').fillna(0)
        df['DC_POWER_INPUT'] = pd.to_numeric(df[col_map['dc_power']], errors='coerce').replace(0, np.nan)
        df['EFFICIENCY_%'] = (df['AC_POWER_FIXED'] / df['DC_POWER_INPUT']) * 100
        df['EFFICIENCY_%'] = df['EFFICIENCY_%'].clip(0, 100)
    elif 'efficiency' in col_map:
        df['EFFICIENCY_%'] = pd.to_numeric(df[col_map['efficiency']], errors='coerce')
    else:
        df['EFFICIENCY_%'] = np.nan
    
    if 'AC_POWER_FIXED' not in df.columns:
        df['AC_POWER_FIXED'] = df['Value']
    
    if 'source' in col_map:
        df['SOURCE_ID'] = df[col_map['source']].astype(str)
        df['SOURCE_ID_NUMBER'] = pd.factorize(df['SOURCE_ID'])[0] + 1
    else:
        df['SOURCE_ID'] = 'Main System'
        df['SOURCE_ID_NUMBER'] = 1
    
    st.success(f"✅ Successfully loaded **{len(df):,}** data points")
    return df

# ==================== ANOMALY DETECTION ====================
@st.cache_data
def detect_anomalies(df, contamination=DEFAULT_CONTAMINATION):
    """Enhanced anomaly detection with better accuracy."""
    df = df.copy()
    if len(df) < MIN_DATA_ROWS:
        df["anomaly"] = False
        return df
    
    try:
        features = df[["Value"]].copy()
        
        if 'TIME_STAMP' in df.columns:
            df['hour'] = pd.to_datetime(df['TIME_STAMP']).dt.hour
            df['day_of_week'] = pd.to_datetime(df['TIME_STAMP']).dt.dayofweek
            features['hour_normalized'] = df['hour'] / 24
            features['day_normalized'] = df['day_of_week'] / 7
        
        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(features)
        
        model = IsolationForest(
            contamination=contamination, 
            random_state=42, 
            n_estimators=200,
            max_samples='auto',
            max_features=1.0
        )
        df["anomaly"] = model.fit_predict(features_scaled) == -1
        df["anomaly_score"] = model.score_samples(features_scaled)
        
    except Exception as e:
        st.error(f"❌ Anomaly detection error: {str(e)}")
        df["anomaly"] = False
        df["anomaly_score"] = 0
    
    return df

@st.cache_data
def detect_efficiency_anomalies(df, contamination=DEFAULT_CONTAMINATION):
    """Enhanced efficiency anomaly detection with dropdown."""
    try:
        df_clean = df[df['EFFICIENCY_%'].between(0.1, 100)].copy()
        if df_clean.empty:
            return None
        
        df_clean['TIME_STAMP'] = pd.to_datetime(df_clean['TIME_STAMP'])
        df_clean = df_clean.sort_values(['SOURCE_ID', 'TIME_STAMP'])
        full_range = pd.date_range(start=df_clean['TIME_STAMP'].min(), end=df_clean['TIME_STAMP'].max(), freq='15T')
        
        all_data = []
        inverter_list = sorted(df_clean['SOURCE_ID'].unique())

        for inv in inverter_list:
            inv_df = df_clean[df_clean['SOURCE_ID'] == inv].copy()
            inv_df = inv_df.set_index('TIME_STAMP')
            inv_df = inv_df.reindex(full_range)
            inv_df['SOURCE_ID'] = inv
            inv_df = inv_df.rename_axis('TIME_STAMP').reset_index()
            inv_df['anomaly'] = False
            mask = inv_df['EFFICIENCY_%'] > 0
            
            if mask.sum() > 10:
                model = IsolationForest(
                    contamination=contamination, 
                    random_state=42, 
                    n_estimators=200,
                    max_samples='auto'
                )
                inv_df.loc[mask, 'anomaly'] = model.fit_predict(inv_df.loc[mask, ['EFFICIENCY_%']]) == -1
            all_data.append(inv_df)

        final_df = pd.concat(all_data, ignore_index=True)
        final_df['Status'] = final_df['anomaly'].map({True: 'Anomaly', False: 'Normal'})

        fig = go.Figure()
        dropdowns = []

        for i, inv in enumerate(inverter_list):
            temp = final_df[final_df['SOURCE_ID'] == inv]
            fig.add_trace(go.Scatter(
                x=temp['TIME_STAMP'], 
                y=temp['EFFICIENCY_%'], 
                mode='lines', 
                name=f'{inv} Efficiency', 
                visible=(i == 0), 
                line=dict(color='#3b82f6', width=2),
                hovertemplate='<b>Time:</b> %{x}<br><b>Efficiency:</b> %{y:.2f}%<extra></extra>'
            ))
            fig.add_trace(go.Scatter(
                x=temp[temp['anomaly']]['TIME_STAMP'], 
                y=temp[temp['anomaly']]['EFFICIENCY_%'], 
                mode='markers', 
                name=f'{inv} Anomaly', 
                visible=(i == 0), 
                marker=dict(color='#ef4444', size=10, symbol='x'),
                hovertemplate='<b>⚠️ Anomaly</b><br><b>Time:</b> %{x}<br><b>Efficiency:</b> %{y:.2f}%<extra></extra>'
            ))
            
            vis_flags = [False] * (2 * len(inverter_list))
            vis_flags[2 * i] = True
            vis_flags[2 * i + 1] = True
            dropdowns.append(dict(
                label=inv, 
                method='update', 
                args=[
                    {'visible': vis_flags}, 
                    {'title': f'Efficiency Analysis for {inv}'}
                ]
            ))

        fig.update_layout(
            updatemenus=[dict(
                active=0, 
                buttons=dropdowns, 
                x=1.05, 
                xanchor='left', 
                y=1.15, 
                yanchor='top',
                bgcolor='#3b82f6',
                bordercolor='#1e3a8a',
                font=dict(color='white')
            )],
            title=f'Efficiency Analysis for {inverter_list[0]}',
            xaxis_title='Timestamp',
            yaxis_title='Efficiency (%)',
            height=600,
            template='plotly_white',
            hovermode='x unified'
        )
        return fig
    except Exception as e:
        st.error(f"❌ Error in efficiency anomaly detection: {str(e)}")
        return None

# ==================== ENHANCED FORECASTING ====================
@st.cache_data(show_spinner=False)
def run_forecast(df, model_type='gradient_boosting'):
    """Enhanced forecasting with improved accuracy and features."""
    try:
        df = df.copy()
        df["TIME_STAMP"] = pd.to_datetime(df["TIME_STAMP"], errors='coerce')
        df = df.dropna(subset=["TIME_STAMP", "AC_POWER_FIXED"])
        
        if len(df) < 50:
            return pd.DataFrame(), {}, "Need at least 50 data points for forecasting"
        
        df["time_index"] = range(len(df))
        df["hour"] = df["TIME_STAMP"].dt.hour
        df["day_of_week"] = df["TIME_STAMP"].dt.dayofweek
        df["month"] = df["TIME_STAMP"].dt.month
        df["day_of_year"] = df["TIME_STAMP"].dt.dayofyear
        df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
        
        df["rolling_mean_3"] = df["AC_POWER_FIXED"].rolling(window=3, min_periods=1).mean()
        df["rolling_std_3"] = df["AC_POWER_FIXED"].rolling(window=3, min_periods=1).std().fillna(0)
        df["rolling_mean_7"] = df["AC_POWER_FIXED"].rolling(window=7, min_periods=1).mean()
        
        df["lag_1"] = df["AC_POWER_FIXED"].shift(1).fillna(df["AC_POWER_FIXED"].mean())
        df["lag_2"] = df["AC_POWER_FIXED"].shift(2).fillna(df["AC_POWER_FIXED"].mean())
        
        feature_cols = [
            "time_index", "hour", "day_of_week", "month", "day_of_year",
            "is_weekend", "rolling_mean_3", "rolling_std_3", "rolling_mean_7", 
            "lag_1", "lag_2"
        ]
        
        X = df[feature_cols].fillna(0)
        y = df["AC_POWER_FIXED"]
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, shuffle=False
        )
        
        # Train model based on type
        if model_type == 'linear_regression':
            # Simple linear regression uses ONLY time as predictor
            model = LinearRegression()
            X_train_simple = X_train[['time_index']]
            X_test_simple = X_test[['time_index']]
            model.fit(X_train_simple, y_train)
            y_pred = model.predict(X_test_simple)
            y_train_pred = model.predict(X_train_simple)
            # Use simple features for cross-validation
            cv_scores = cross_val_score(model, X_train_simple, y_train, cv=min(5, len(X_train)//10), scoring='r2')
        
        elif model_type == 'gradient_boosting':
            model = GradientBoostingRegressor(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=5,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42
            )
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)
            y_train_pred = model.predict(X_train)
            cv_scores = cross_val_score(model, X_train, y_train, cv=min(5, len(X_train)//10), scoring='r2')
        
        elif model_type == 'random_forest':
            model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42
            )
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)
            y_train_pred = model.predict(X_train)
            cv_scores = cross_val_score(model, X_train, y_train, cv=min(5, len(X_train)//10), scoring='r2')
        
        # Calculate metrics (same for all models)
        mse = mean_squared_error(y_test, y_pred)
        rmse = np.sqrt(mse)
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        train_r2 = r2_score(y_train, y_train_pred)
        
        # Calculate MAPE with error handling for zero/near-zero values
        mape_values = np.abs((y_test - y_pred) / np.where(y_test != 0, y_test, 1))
        mape_values = mape_values[np.isfinite(mape_values)]  # Remove inf/nan
        mape = np.mean(mape_values) * 100 if len(mape_values) > 0 else 999.9
        mape = min(mape, 999.9)  # Cap at 999.9% for display purposes
        
        forecast_df = pd.DataFrame({
            'Index': X_test.index,
            'Actual': y_test.values,
            'Predicted': y_pred,
            'Error': np.abs(y_test.values - y_pred),
            'Percent_Error': np.abs((y_test.values - y_pred) / y_test.values) * 100
        })
        
        metrics = {
            'mse': mse,
            'rmse': rmse,
            'mae': mae,
            'r2': r2,
            'train_r2': train_r2,
            'cv_mean': cv_scores.mean(),
            'cv_std': cv_scores.std(),
            'mape': mape,
            'mean_actual': y_test.mean(),
            'mean_predicted': np.mean(y_pred),
            'model_type': model_type,
            'test_points': len(y_test)
        }
        
        return forecast_df, metrics, None
        
    except Exception as e:
        return pd.DataFrame(), {}, str(e)

# ==================== AI INSIGHTS ====================
def generate_ai_insights(df, anomalies):
    """Generate detailed, user-friendly insights."""
    insights = []
    total_energy = df['Value'].sum()
    avg_output = df['Value'].mean()
    max_output = df['Value'].max()
    
    insights.append({
        'title': '🌞 Overall Performance',
        'message': f"Your solar system generated <strong>{total_energy:,.2f} kW</strong> total energy with an average output of <strong>{avg_output:.2f} kW</strong> per reading. Peak performance reached <strong>{max_output:.2f} kW</strong>, showing your system's maximum capacity."
    })
    
    if 'TIME_STAMP' in df.columns:
        df_copy = df.copy()
        df_copy['hour'] = pd.to_datetime(df_copy['TIME_STAMP']).dt.hour
        hourly_avg = df_copy.groupby('hour')['Value'].mean()
        peak_hour = hourly_avg.idxmax()
        peak_value = hourly_avg.max()
        
        insights.append({
            'title': '⏰ Peak Production Time',
            'message': f"Your solar panels produce the most energy around <strong>{peak_hour}:00</strong> (averaging <strong>{peak_value:.2f} kW</strong>). This is your system's optimal performance window. Consider scheduling high-energy tasks during this period to maximize solar usage."
        })
    
    anomaly_count = len(anomalies)
    anomaly_pct = (anomaly_count / len(df)) * 100 if len(df) > 0 else 0
    
    if anomaly_count > 0:
        if anomaly_pct < 2:
            insights.append({
                'title': '🟢 System Health: Excellent',
                'message': f"Detected <strong>{anomaly_count} unusual readings</strong> ({anomaly_pct:.1f}% of data). This low percentage is completely normal and typically caused by passing clouds, weather changes, or brief shading. Your system is performing well."
            })
        elif anomaly_pct < 5:
            insights.append({
                'title': '🟡 System Health: Good',
                'message': f"Found <strong>{anomaly_count} unusual readings</strong> ({anomaly_pct:.1f}% of data). This moderate level suggests occasional issues like temporary shading, dust accumulation, or minor equipment variations. Consider a visual inspection of your panels."
            })
        else:
            insights.append({
                'title': '🟠 System Health: Needs Attention',
                'message': f"Detected <strong>{anomaly_count} unusual readings</strong> ({anomaly_pct:.1f}% of data). This higher percentage may indicate persistent shading, equipment inefficiency, or maintenance needs. We recommend a professional inspection."
            })
    else:
        insights.append({
            'title': '🟢 System Health: Perfect',
            'message': "No anomalies detected in your solar data. Your system is operating consistently and efficiently within expected parameters. Keep up the excellent maintenance!"
        })
    
    if 'EFFICIENCY_%' in df.columns:
        eff_data = df['EFFICIENCY_%'].dropna()
        if not eff_data.empty and len(eff_data) > 0:
            avg_eff = eff_data.mean()
            max_eff = eff_data.max()
            min_eff = eff_data[eff_data > 0].min() if len(eff_data[eff_data > 0]) > 0 else 0
            
            if avg_eff > 85:
                rating = "excellent"
                emoji = "⭐"
                recommendation = "Your system is operating at peak efficiency. Continue your current maintenance schedule."
            elif avg_eff > 75:
                rating = "good"
                emoji = "✅"
                recommendation = "Your system efficiency is solid. Regular cleaning and inspections will help maintain this level."
            elif avg_eff > 65:
                rating = "fair"
                emoji = "⚠️"
                recommendation = "Efficiency could be improved. Check for dust, debris, or shading issues. Consider panel cleaning."
            else:
                rating = "needs improvement"
                emoji = "❗"
                recommendation = "Low efficiency detected. Professional inspection recommended to identify potential equipment or installation issues."
            
            insights.append({
                'title': f'{emoji} System Efficiency: {rating.title()}',
                'message': f"Your system operates at <strong>{avg_eff:.1f}% average efficiency</strong> (range: {min_eff:.1f}%-{max_eff:.1f}%). Most well-maintained solar systems operate between 75-85%. {recommendation}"
            })
    
    return insights

def generate_comprehensive_ai_summary(df, anomalies, forecast_metrics=None):
    """Generate comprehensive AI-powered analysis summary."""
    summary = []
    
    total_points = len(df)
    date_range = ""
    if 'TIME_STAMP' in df.columns:
        start_date = df['TIME_STAMP'].min()
        end_date = df['TIME_STAMP'].max()
        # Fix: Convert to datetime if it's a string
        if isinstance(start_date, str):
            start_date = pd.to_datetime(start_date)
        if isinstance(end_date, str):
            end_date = pd.to_datetime(end_date)
        date_range = f" from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
    
    summary.append(f"📊 <strong>Dataset Analysis</strong>: Analyzed <strong>{total_points:,} data points</strong>{date_range}.")
    
    total_energy = df['Value'].sum()
    avg_output = df['Value'].mean()
    max_output = df['Value'].max()
    min_output = df['Value'].min()
    std_output = df['Value'].std()
    
    summary.append(f"⚡ <strong>Energy Production</strong>: Total generation of <strong>{total_energy:,.2f} kW</strong> with an average of <strong>{avg_output:.2f} kW</strong> per reading. Your system shows a standard deviation of <strong>{std_output:.2f} kW</strong>, indicating {'consistent' if std_output < avg_output * 0.3 else 'variable'} performance.")
    
    if std_output < avg_output * 0.2:
        stability = "highly stable"
    elif std_output < avg_output * 0.4:
        stability = "moderately stable"
    else:
        stability = "variable"
    
    summary.append(f"📈 <strong>Performance Stability</strong>: Your system exhibits <strong>{stability}</strong> output patterns. Peak output reached <strong>{max_output:.2f} kW</strong> while minimum recorded was <strong>{min_output:.2f} kW</strong>.")
    
    anomaly_count = len(anomalies)
    anomaly_pct = (anomaly_count / total_points) * 100 if total_points > 0 else 0
    
    if anomaly_count == 0:
        summary.append(f"✅ <strong>Anomaly Analysis</strong>: No anomalies detected. Your system is performing optimally with consistent output patterns.")
    else:
        summary.append(f"⚠️ <strong>Anomaly Analysis</strong>: Detected <strong>{anomaly_count} anomalies</strong> ({anomaly_pct:.2f}% of data). {get_anomaly_interpretation(anomaly_pct)}")
    
    if 'TIME_STAMP' in df.columns:
        df_temp = df.copy()
        df_temp['TIME_STAMP'] = pd.to_datetime(df_temp['TIME_STAMP'])  # Ensure it's datetime
        df_temp['hour'] = df_temp['TIME_STAMP'].dt.hour
        df_temp['day_of_week'] = df_temp['TIME_STAMP'].dt.dayofweek
        
        hourly_avg = df_temp.groupby('hour')['Value'].mean()
        peak_hour = hourly_avg.idxmax()
        peak_value = hourly_avg.max()
        low_hour = hourly_avg.idxmin()
        low_value = hourly_avg.min()
        
        summary.append(f"🕐 <strong>Temporal Patterns</strong>: Peak production occurs at <strong>{peak_hour}:00</strong> ({peak_value:.2f} kW average), while lowest production is at <strong>{low_hour}:00</strong> ({low_value:.2f} kW average). This {get_production_pattern_interpretation(peak_hour)} typical solar behavior.")
        
        daily_avg = df_temp.groupby('day_of_week')['Value'].mean()
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        best_day = day_names[daily_avg.idxmax()]
        worst_day = day_names[daily_avg.idxmin()]
        
        summary.append(f"📅 <strong>Weekly Patterns</strong>: <strong>{best_day}</strong> shows the highest average production, while <strong>{worst_day}</strong> shows the lowest. This may indicate weather patterns or environmental factors affecting specific days.")
    
    if 'EFFICIENCY_%' in df.columns:
        eff_data = df['EFFICIENCY_%'].dropna()
        if not eff_data.empty and len(eff_data) > 0:
            avg_eff = eff_data.mean()
            eff_std = eff_data.std()
            
            summary.append(f"⚙️ <strong>Conversion Efficiency</strong>: Average efficiency of <strong>{avg_eff:.1f}%</strong> with standard deviation of <strong>{eff_std:.1f}%</strong>. {get_efficiency_interpretation(avg_eff, eff_std)}")
    
    if forecast_metrics and 'r2' in forecast_metrics:
        r2 = forecast_metrics['r2']
        mape = forecast_metrics.get('mape', 0)
        
        summary.append(f"🔮 <strong>Forecast Reliability</strong>: Predictive model achieved <strong>{r2*100:.1f}% accuracy</strong> (R² = {r2:.3f}) with an average error of <strong>{mape:.1f}%</strong>. {get_forecast_interpretation(r2)}")
    
    if 'SOURCE_ID' in df.columns and len(df['SOURCE_ID'].unique()) > 1:
        inverter_count = len(df['SOURCE_ID'].unique())
        inverter_avg = df.groupby('SOURCE_ID')['Value'].mean()
        best_inverter = inverter_avg.idxmax()
        worst_inverter = inverter_avg.idxmin()
        performance_gap = ((inverter_avg.max() - inverter_avg.min()) / inverter_avg.mean()) * 100
        
        summary.append(f"🔌 <strong>Inverter Performance</strong>: Monitoring <strong>{inverter_count} inverters</strong>. Top performer: <strong>{best_inverter}</strong> ({inverter_avg.max():.2f} kW avg). Lowest performer: <strong>{worst_inverter}</strong> ({inverter_avg.min():.2f} kW avg). Performance gap: <strong>{performance_gap:.1f}%</strong>. {get_inverter_gap_interpretation(performance_gap)}")
    
    recommendations = generate_recommendations(df, anomalies, anomaly_pct)
    if recommendations:
        summary.append(f"💡 <strong>Key Recommendations</strong>: {recommendations}")
    
    return "\n\n".join(summary)

def get_anomaly_interpretation(anomaly_pct):
    """Interpret anomaly percentage."""
    if anomaly_pct < 1:
        return "This is excellent and within normal operational parameters."
    elif anomaly_pct < 3:
        return "This is normal and typically caused by environmental factors like passing clouds or temporary shading."
    elif anomaly_pct < 5:
        return "This is moderately elevated and may warrant a visual inspection of panels for dust, debris, or persistent shading."
    else:
        return "This is elevated and suggests potential equipment issues or environmental challenges requiring professional assessment."

def get_production_pattern_interpretation(peak_hour):
    """Interpret production patterns."""
    if 10 <= peak_hour <= 14:
        return "aligns perfectly with"
    elif 8 <= peak_hour < 10 or 14 < peak_hour <= 16:
        return "is consistent with"
    else:
        return "deviates from"

def get_efficiency_interpretation(avg_eff, eff_std):
    """Interpret efficiency metrics."""
    if avg_eff > 85 and eff_std < 5:
        return "Excellent and highly consistent performance."
    elif avg_eff > 75 and eff_std < 10:
        return "Good performance with acceptable variation."
    elif avg_eff > 65:
        return "Fair performance with room for optimization."
    else:
        return "Below optimal levels—professional inspection recommended."

def get_forecast_interpretation(r2):
    """Interpret forecast reliability."""
    if r2 > 0.85:
        return "High confidence in predictions."
    elif r2 > 0.7:
        return "Good predictive capability."
    elif r2 > 0.5:
        return "Moderate reliability—more data may improve accuracy."
    else:
        return "Limited predictive power—consider collecting additional historical data."

def get_inverter_gap_interpretation(gap):
    """Interpret inverter performance gap."""
    if gap < 10:
        return "All inverters performing uniformly well."
    elif gap < 20:
        return "Minor performance variations—monitor lower performers."
    else:
        return "Significant performance gap—investigate underperforming units."

def generate_recommendations(df, anomalies, anomaly_pct):
    """Generate actionable recommendations."""
    recommendations = []
    
    if anomaly_pct > 5:
        recommendations.append("Schedule professional inspection")
    elif anomaly_pct > 2:
        recommendations.append("Visual panel inspection recommended")
    
    if 'EFFICIENCY_%' in df.columns:
        avg_eff = df['EFFICIENCY_%'].dropna().mean()
        if avg_eff < 75:
            recommendations.append("Panel cleaning may improve efficiency")
    
    if 'SOURCE_ID' in df.columns and len(df['SOURCE_ID'].unique()) > 1:
        inverter_avg = df.groupby('SOURCE_ID')['Value'].mean()
        performance_gap = ((inverter_avg.max() - inverter_avg.min()) / inverter_avg.mean()) * 100
        if performance_gap > 20:
            recommendations.append("Investigate underperforming inverters")
    
    if len(anomalies) == 0:
        recommendations.append("Maintain current maintenance schedule")
    
    if not recommendations:
        return "System operating optimally—continue current practices"
    
    return " | ".join(recommendations)

# ==================== INVERTER ANALYSIS ====================
@st.cache_data
def analyze_inverter_performance(df):
    """Enhanced inverter quartile analysis with detailed statistics."""
    try:
        df_eff = df[df['EFFICIENCY_%'].between(0.01, 100)].copy()
        if df_eff.empty:
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), {}
        
        res2 = df_eff.groupby('SOURCE_ID_NUMBER')['AC_POWER_FIXED'].mean()
        res_std = df_eff.groupby('SOURCE_ID_NUMBER')['AC_POWER_FIXED'].std()
        res_max = df_eff.groupby('SOURCE_ID_NUMBER')['AC_POWER_FIXED'].max()
        
        res_df = pd.DataFrame({
            'SOURCE_ID_NUMBER': res2.index,
            'AC_POWER_FIXED': res2.values,
            'Std_Dev': res_std.values,
            'Max_Power': res_max.values
        }).reset_index(drop=True)
        
        q1 = res2.quantile(0.25)
        q2 = res2.quantile(0.50)
        q3 = res2.quantile(0.75)
        
        low = res_df[res_df['AC_POWER_FIXED'] <= q1]
        medium_low = res_df[(res_df['AC_POWER_FIXED'] > q1) & (res_df['AC_POWER_FIXED'] <= q2)]
        medium_high = res_df[(res_df['AC_POWER_FIXED'] > q2) & (res_df['AC_POWER_FIXED'] <= q3)]
        high = res_df[res_df['AC_POWER_FIXED'] > q3]
        
        summary = {
            'Inverter Distribution': {
                'High Performers (Top 25%)': len(high),
                'Above Average (50-75%)': len(medium_high),
                'Below Average (25-50%)': len(medium_low),
                'Low Performers (Bottom 25%)': len(low),
            },
            'Performance Thresholds': {
                'Top Quartile (Q3)': f"{q3:.2f} kW",
                'Median (Q2)': f"{q2:.2f} kW",
                'Bottom Quartile (Q1)': f"{q1:.2f} kW"
            }
        }
        
        if len(low) > 0:
            summary['Alert'] = f"⚠️ {len(low)} inverter(s) underperforming - may need maintenance, cleaning, or inspection"
        
        if not res_df.empty:
            max_row = res_df.loc[res_df['AC_POWER_FIXED'].idxmax()]
            min_row = res_df.loc[res_df['AC_POWER_FIXED'].idxmin()]
            summary['Best Performer'] = {
                'Inverter': f"S{int(max_row['SOURCE_ID_NUMBER'])}",
                'Average Output': f"{max_row['AC_POWER_FIXED']:.2f} kW",
                'Peak Output': f"{max_row['Max_Power']:.2f} kW"
            }
            summary['Worst Performer'] = {
                'Inverter': f"S{int(min_row['SOURCE_ID_NUMBER'])}",
                'Average Output': f"{min_row['AC_POWER_FIXED']:.2f} kW",
                'Peak Output': f"{min_row['Max_Power']:.2f} kW"
            }
        
        return high, medium_high, medium_low, low, summary
    except Exception as e:
        st.error(f"❌ Error analyzing inverters: {str(e)}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), {}

# ==================== ZAPIER ====================
def send_to_zapier(data, webhook_url):
    """Send to Zapier webhook with timeout and error handling."""
    try:
        response = requests.post(webhook_url, json=data, timeout=10)
        return response.status_code == 200, response.status_code
    except Exception as e:
        return False, str(e)

def show_zapier_guide():
    """Display detailed Zapier setup guide in expandable section."""
    with st.expander("📖 Complete Zapier Setup Guide", expanded=False):
        st.markdown("""
        ### 🔗 Step-by-Step Zapier Integration
        
        #### Step 1: Create a Zapier Account
        - Go to [Zapier.com](https://zapier.com)
        - Click "Sign Up" (free tier available)
        - Complete the registration process
        
        #### Step 2: Create Your Zap
        - Log into your Zapier dashboard
        - Click the **"Create Zap"** or **"Make a Zap"** button
        - You'll be taken to the Zap editor
        
        #### Step 3: Set Up the Trigger
        - In the trigger section, search for **"Webhooks by Zapier"**
        - Select **"Webhooks by Zapier"** from the results
        - Choose **"Catch Hook"** as the event type
        - Click **"Continue"**
        
        #### Step 4: Get Your Webhook URL
        - Zapier will generate a unique webhook URL
        - It looks like: `https://hooks.zapier.com/hooks/catch/123456/abcdef/`
        - **Copy this entire URL** - you'll need it for Solixa
        
        #### Step 5: Connect to Solixa
        - Return to Solixa (this app)
        - In the sidebar, paste your webhook URL in the **"Webhook URL"** field
        - Click the **"🧪 Send Test to Zapier"** button
        
        #### Step 6: Test in Zapier
        - Go back to your Zapier editor
        - Click **"Test trigger"**
        - Zapier should find the test data from Solixa
        - Click **"Continue"**
        
        #### Step 7: Set Up Actions
        - Choose what happens when anomalies are detected
        - **Popular options:**
          - Send email (Gmail, Outlook)
          - Send SMS (Twilio)
          - Create Slack message
          - Add to Google Sheets
          - Create calendar event
        - Configure your chosen action with the data fields
        
        #### Step 8: Activate Your Zap
        - Review all settings
        - Click **"Turn on Zap"** or **"Publish"**
        - Your Zap is now live! ✅
        
        #### 📊 Data You'll Receive
        When you export anomalies from Solixa, Zapier receives:
        - **date**: The date of the anomalies
        - **total_anomalies**: Number of anomalies detected
        - **anomalies**: Array containing:
          - timestamp: When each anomaly occurred
          - value: Power reading at that time
          - source: Which inverter/system
        
        #### 💡 Pro Tips
        - Set up multiple actions (email + SMS + Slack)
        - Use filters to only notify for high-priority anomalies
        - Create a daily digest instead of immediate alerts
        - Log all data to Google Sheets for record keeping
        
        #### ❓ Troubleshooting
        - **Test fails?** Make sure you copied the entire webhook URL
        - **No data received?** Check that your Zap is turned ON
        - **Wrong data?** Review the data mapping in your action step
        - **Still stuck?** Contact Zapier support - they're very helpful!
        """)

# ==================== MAIN APP ====================
def main():
    # --- AUTHENTICATION ROUTING ---
    from auth import show_login, show_signup
    page = st.session_state.get("page", "login")
    authenticated = st.session_state.get("authenticated", False)

    # Handle query params for navigation
    query_params = st.query_params
    if "page" in query_params:
        page = query_params["page"]
        st.session_state["page"] = page

    if not authenticated:
        if page == "signup":
            show_signup()
        else:
            show_login()
        return
    st.set_page_config(page_title="Solixa", page_icon="☀️", layout="wide", initial_sidebar_state="expanded")
    apply_custom_styling()
    
    # Initialize session state for navigation
    if 'current_tab' not in st.session_state:
        st.session_state.current_tab = "🏠 Home"
    
    # Set defaults
    tab_selection = st.session_state.current_tab
    contamination = 0.02
    forecast_model = 'gradient_boosting'
    zapier_url = ""
    
    with st.sidebar:
        st.markdown('<h1 style="font-size: 2.5rem; font-weight: 900; color: #fbbf24; margin: 0; line-height: 1.2; text-align: center;">SOLIXA</h1>', unsafe_allow_html=True)
        st.markdown("---")

        st.markdown("""
        <div style="text-align: center; margin-bottom: 1rem;">
            <h3 style="color: #fbbf24; font-size: 0.9rem; font-weight: 700; margin: 0; letter-spacing: 1px;">
                📁 UPLOAD YOUR SOLAR DATA
            </h3>
        </div>
        """, unsafe_allow_html=True)

        uploaded_file = st.file_uploader("", type=["csv"], label_visibility="collapsed")
        
        # Only show navigation, settings, and Zapier if file is uploaded
        if uploaded_file:
            st.markdown("---")
            
            st.markdown('<h3 style="color: #fbbf24; font-weight: 700; font-size: 0.85rem; margin: 1.5rem 0 1rem 0; letter-spacing: 1.5px; text-transform: uppercase; text-align: center;">📍 NAVIGATION</h3>', unsafe_allow_html=True)

            if st.button("🏠 Home", use_container_width=True, key="nav_home", type="primary" if st.session_state.current_tab == "🏠 Home" else "secondary"):
                st.session_state.current_tab = "🏠 Home"
                st.rerun()
        
            if st.button("📊 Summary", use_container_width=True, key="nav_summary", type="primary" if st.session_state.current_tab == "📊 Energy Summary" else "secondary"):
                st.session_state.current_tab = "📊 Energy Summary"
                st.rerun()
        
            if st.button("🔍 Anomalies", use_container_width=True, key="nav_anomalies", type="primary" if st.session_state.current_tab == "🔍 Anomalies & Groupings" else "secondary"):
                st.session_state.current_tab = "🔍 Anomalies & Groupings"
                st.rerun()
        
            if st.button("📈 Forecast", use_container_width=True, key="nav_forecast", type="primary" if st.session_state.current_tab == "📈 Forecasting" else "secondary"):
                st.session_state.current_tab = "📈 Forecasting"
                st.rerun()

            tab_selection = st.session_state.current_tab
            
            st.markdown("---")
            
            st.markdown('<h3 style="color: #fbbf24; font-weight: 700; font-size: 0.85rem; margin: 1.5rem 0 1rem 0; letter-spacing: 1.5px; text-transform: uppercase; text-align: center;">⚙️ SETTINGS</h3>', unsafe_allow_html=True)
            
            sensitivity = st.slider("Anomaly Sensitivity", 1, 10, 2, 
                                  help="Lower values detect only major anomalies. Higher values detect subtle variations.")
            contamination = sensitivity / 100
            
            forecast_model = st.selectbox("Forecasting Model", 
                                          ['gradient_boosting', 'random_forest', 'linear_regression'],
                                          help="Gradient Boosting: Most accurate\nRandom Forest: Good balance\nLinear: Fastest")
            
            st.markdown("---")
            
            st.markdown('<h3 style="color: #fbbf24; font-weight: 700; font-size: 0.85rem; margin: 1.5rem 0 1rem 0; letter-spacing: 1.5px; text-transform: uppercase; text-align: center;">🔗 ZAPIER</h3>', unsafe_allow_html=True)
            
            zapier_url = st.text_input("Webhook URL", placeholder="https://hooks.zapier.com/...",
                                       help="Paste your Zapier webhook URL here")
            
            if zapier_url:
                if st.button("🧪 Test Connection", use_container_width=True, key="zapier_test"):
                    test_data = {
                        "test": True,
                        "message": "Test from Solixa",
                        "timestamp": str(datetime.now())
                    }       
                    success, result = send_to_zapier(test_data, zapier_url)
                    if success:
                        st.success("✅ Connected!")
                    else:
                        st.error(f"❌ Failed: {result}")
            
            show_zapier_guide()
        
        else:
            # Show helpful message when no file is uploaded
            st.markdown("---")
            st.markdown("""
            <div style="padding: 1.5rem 1rem; background: rgba(251, 191, 36, 0.08); border: 1px solid rgba(251, 191, 36, 0.25); border-radius: 10px; margin-top: 1rem; text-align: center;">
                <p style="color: #fbbf24; margin: 0; font-size: 2rem;">👆</p>
                <p style="color: rgba(255, 255, 255, 0.9); margin: 0.5rem 0 0 0; font-size: 0.9rem; font-weight: 500; line-height: 1.5;">
                    Upload your CSV file to begin analysis
                </p>
            </div>
            """, unsafe_allow_html=True)
    
    # REST OF THE TABS REMAIN THE SAME - Just use tab_selection variable
    if tab_selection == "🏠 Home":
        st.markdown('<div style="text-align: center;"><h1 class="main-title">☀️ SOLIXA</h1></div>', unsafe_allow_html=True)
        st.markdown('<div style="text-align: center;"><h2 class="tagline">Decode the Sun.</h2></div>', unsafe_allow_html=True)
        
        # ... rest of home tab code stays the same ...
        col1, col2 = st.columns([3, 2])
        
        with col1:
            st.markdown("""
            <div class="blue-card">
                <h2 style="color: #1e3a8a;">🌟 Why Solixa?</h2>
                <p style="font-size: 1.1rem; color: #1e40af; line-height: 1.8;">
                We created Solixa because solar data analysis shouldn't require technical expertise. The inspiration 
                came from recognizing a growing gap between the potential of renewable energy and the accessibility 
                of tools to manage it. While volunteering with a local sustainability group, we met energy analysts 
                who spent hours cleaning and interpreting datasets. Many community solar projects and homeowners were 
                collecting valuable data but lacked the means to interpret it in real time.
                </p>
                <p style="font-size: 1.1rem; color: #1e40af; margin-top: 1rem; font-weight: 600;">
                That sparked our idea: bring advanced machine learning within reach of anyone involved in solar energy. 
                No technical knowledge needed. Just upload your data and get instant, meaningful insights.
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.markdown("""
                <div class="yellow-card">
                    <h4 style="color: #1e3a8a;">🔍 Smart Detection</h4>
                    <p style="color: #1e40af;">Advanced ML algorithms find unusual patterns and potential issues automatically</p>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("""
                <div class="blue-card">
                    <h4 style="color: #1e3a8a;">📊 Clear Reports</h4>
                    <p style="color: #1e40af;">Beautiful visualizations and explanations anyone can understand</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col_b:
                st.markdown("""
                <div class="blue-card">
                    <h4 style="color: #1e3a8a;">📈 Accurate Forecasting</h4>
                    <p style="color: #1e40af;">Predict future energy production with enhanced ML models</p>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("""
                <div class="yellow-card">
                    <h4 style="color: #1e3a8a;">🔔 Smart Alerts</h4>
                    <p style="color: #1e40af;">Get notified via Zapier when your system needs attention</p>
                </div>
                """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="info-box">
                <h3 style="color: white; margin-top: 0;">🚀 Get Started in 3 Steps</h3>
                <div style="margin: 1.5rem 0;">
                    <div style="margin-bottom: 1.5rem;">
                        <span class="step-number">1</span>
                        <strong style="font-size: 1.1rem; color: white;">Upload Your Data</strong>
                        <p style="margin-left: 56px; margin-top: 0.5rem; color: white;">Any CSV file with timestamps and power readings. We auto-detect the format!</p>
                    </div>
                    <div style="margin-bottom: 1.5rem;">
                        <span class="step-number">2</span>
                        <strong style="font-size: 1.1rem; color: white;">Review Insights</strong>
                        <p style="margin-left: 56px; margin-top: 0.5rem; color: white;">Our AI analyzes your data and provides clear, actionable recommendations</p>
                    </div>
                    <div style="margin-bottom: 1rem;">
                        <span class="step-number">3</span>
                        <strong style="font-size: 1.1rem; color: white;">Take Action</strong>
                        <p style="margin-left: 56px; margin-top: 0.5rem; color: white;">Export alerts, forecast future production, and optimize your system</p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("""
            <div class="warning-box">
                <h4 style="color: #1e3a8a; margin-top: 0;">📁 Supported Data Formats</h4>
                <ul style="color: #1e3a8a; line-height: 2;">
                    <li>Solar inverter logs (any brand)</li>
                    <li>Energy monitoring systems</li>
                    <li>Panel performance data</li>
                    <li>Custom CSV formats</li>
                    <li>Multi-inverter setups</li>
                </ul>
                <p style="color: #1e3a8a; margin-top: 1rem; font-weight: 600;">✨ Solixa automatically detects your data format!</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown('<h2 class="section-header">💬 What People Are Saying</h2>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            <div class="testimonial">
                <p>"Before Solixa, I spent hours trying to understand if my panels were working properly. Now I just upload and know instantly. The anomaly detection caught a failing inverter weeks before it completely died!"</p>
                <strong style="color: #1e3a8a;">— Sarah M., Community Solar Manager</strong>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="testimonial">
                <p>"I'm not tech-savvy at all, but Solixa makes it incredibly easy. The plain-English explanations are perfect, and the forecasting helps me plan when to run my appliances."</p>
                <strong style="color: #1e3a8a;">— James K., Homeowner</strong>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div class="testimonial">
                <p>"As an energy analyst, I used to juggle multiple tools. Solixa brings everything together beautifully. The accuracy of the forecasting models is impressive!"</p>
                <strong style="color: #1e3a8a;">— Dr. Patel, Energy Analyst</strong>
            </div>
            """, unsafe_allow_html=True)
    
    elif tab_selection == "📊 Energy Summary":
        st.markdown('<div style="text-align: center;"><h1 class="main-title">📊 ENERGY SUMMARY</h1></div>', unsafe_allow_html=True)
        
        if not uploaded_file:
            st.markdown("""
            <div class="info-box">
                <h3 style="color: white;">👈 Upload Your Solar Data to Get Started</h3>
                <p style="color: white; font-size: 1.1rem;">Use the file uploader in the sidebar to begin analyzing your solar panel performance.</p>
            </div>
            """, unsafe_allow_html=True)
            return
        
        with st.spinner("🔄 Loading and analyzing your data..."):
            df = load_clean_data(uploaded_file)
        
        if df.empty:
            return
        
        with st.spinner("🔍 Detecting anomalies..."):
            df = detect_anomalies(df, contamination)
        
        st.markdown('<h3 class="section-header">🤖 AI-Powered Comprehensive Analysis</h3>', unsafe_allow_html=True)
        
        anomalies = df[df['anomaly']]
        comprehensive_summary = generate_comprehensive_ai_summary(df, anomalies)
        
        st.markdown(f"""
        <div class="ai-insight-card">
            <h3>🧠 Intelligent System Analysis</h3>
            <div style="color: #1e40af; font-size: 1.05rem; line-height: 1.9;">
                {comprehensive_summary.replace(chr(10), '<br>')}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        st.markdown('<h3 class="section-header">📈 Key Performance Metrics</h3>', unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_energy = df['Value'].sum()
            st.markdown(f"""
            <div class="metric-card-dark">
                <h4 style="color: white; margin: 0;">Total Energy</h4>
                <h2 style="color: white; margin: 0.5rem 0;">{total_energy:,.2f} kW</h2>
                <p style="color: rgba(255,255,255,0.8); margin: 0;">Cumulative output</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            avg_output = df['Value'].mean()
            st.markdown(f"""
            <div class="metric-card-light">
                <h4 style="color: white; margin: 0;">Average Output</h4>
                <h2 style="color: white; margin: 0.5rem 0;">{avg_output:.2f} kW</h2>
                <p style="color: rgba(255,255,255,0.8); margin: 0;">Per measurement</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            peak_output = df['Value'].max()
            st.markdown(f"""
            <div class="metric-card-yellow">
                <h4 style="color: #1e3a8a; margin: 0;">Peak Output</h4>
                <h2 style="color: #1e3a8a; margin: 0.5rem 0;">{peak_output:.2f} kW</h2>
                <p style="color: #1e3a8a; margin: 0;">Maximum recorded</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            anomaly_count = df['anomaly'].sum()
            st.markdown(f"""
            <div class="metric-card-dark">
                <h4 style="color: white; margin: 0;">Data Points</h4>
                <h2 style="color: white; margin: 0.5rem 0;">{len(df):,}</h2>
                <p style="color: rgba(255,255,255,0.8); margin: 0;">Total readings</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        st.markdown('<h3 class="section-header">📊 Production Pattern Analysis</h3>', unsafe_allow_html=True)
        
        if 'TIME_STAMP' in df.columns:
            df_hourly = df.copy()
            df_hourly['hour'] = pd.to_datetime(df_hourly['TIME_STAMP']).dt.hour
            hourly_stats = df_hourly.groupby('hour')['Value'].agg(['mean', 'std', 'max', 'min']).reset_index()
            
            fig_hourly = go.Figure()
            
            fig_hourly.add_trace(go.Scatter(
                x=hourly_stats['hour'],
                y=hourly_stats['mean'],
                mode='lines+markers',
                name='Average Production',
                line=dict(color='#3b82f6', width=3),
                marker=dict(size=8),
                hovertemplate='<b>Hour:</b> %{x}:00<br><b>Avg Output:</b> %{y:.2f} kW<extra></extra>'
            ))
            
            fig_hourly.add_trace(go.Scatter(
                x=hourly_stats['hour'],
                y=hourly_stats['max'],
                mode='lines',
                name='Peak Production',
                line=dict(color='#fbbf24', width=2, dash='dash'),
                hovertemplate='<b>Hour:</b> %{x}:00<br><b>Peak:</b> %{y:.2f} kW<extra></extra>'
            ))
            
            fig_hourly.update_layout(
                height=400,
                template='plotly_white',
                hovermode='x unified',
                xaxis_title='Hour of Day',
                yaxis_title='Power Output (kW)',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            
            st.plotly_chart(fig_hourly, use_container_width=True)
        
        st.markdown("---")
        
        st.markdown('<h3 class="section-header">📈 Energy Production Over Time</h3>', unsafe_allow_html=True)
        
        fig = go.Figure()
        
        normal_data = df[~df['anomaly']]
        fig.add_trace(go.Scatter(
            x=normal_data['TIME_STAMP'],
            y=normal_data['Value'],
            mode='lines',
            name='Normal Production',
            line=dict(color='#3b82f6', width=2),
            hovertemplate='<b>Time:</b> %{x}<br><b>Power:</b> %{y:.2f} kW<extra></extra>'
        ))
        
        anomaly_data = df[df['anomaly']]
        if not anomaly_data.empty:
            fig.add_trace(go.Scatter(
                x=anomaly_data['TIME_STAMP'],
                y=anomaly_data['Value'],
                mode='markers',
                name='Anomalies',
                marker=dict(color='#fbbf24', size=10, symbol='x'),
                hovertemplate='<b>⚠️ Anomaly</b><br><b>Time:</b> %{x}<br><b>Power:</b> %{y:.2f} kW<extra></extra>'
            ))
        
        fig.update_layout(
            height=500,
            template='plotly_white',
            hovermode='x unified',
            xaxis_title='Date & Time',
            yaxis_title='Power Output (kW)',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        if 'TIME_STAMP' in df.columns:
            df_daily = df.copy()
            df_daily['date'] = pd.to_datetime(df_daily['TIME_STAMP']).dt.date
            
            if len(df_daily['date'].unique()) > 1:
                st.markdown('<h3 class="section-header">📅 Daily Production Trends</h3>', unsafe_allow_html=True)
                
                daily_stats = df_daily.groupby('date')['Value'].agg(['sum', 'mean', 'max']).reset_index()
                
                fig_daily = go.Figure()
                
                fig_daily.add_trace(go.Bar(
                    x=daily_stats['date'],
                    y=daily_stats['sum'],
                    name='Total Daily Energy',
                    marker_color='#3b82f6',
                    hovertemplate='<b>Date:</b> %{x}<br><b>Total Energy:</b> %{y:.2f} kW<extra></extra>'
                ))
                
                fig_daily.update_layout(
                    height=400,
                    template='plotly_white',
                    xaxis_title='Date',
                    yaxis_title='Total Energy (kW)',
                    showlegend=False
                )
                
                st.plotly_chart(fig_daily, use_container_width=True)
        
        st.markdown("---")
        
        st.markdown('<h3 class="section-header">💡 Key Insights & Recommendations</h3>', unsafe_allow_html=True)
        
        insights = generate_ai_insights(df, anomalies)
        
        cols = st.columns(2)
        for idx, insight in enumerate(insights):
            with cols[idx % 2]:
                card_class = "blue-card" if idx % 2 == 0 else "yellow-card"
                st.markdown(f"""
                <div class="{card_class}">
                    <h3 style="color: #1e3a8a;">{insight['title']}</h3>
                    <p style="color: #1e40af; font-size: 1.05rem; line-height: 1.7;">{insight['message']}</p>
                </div>
                """, unsafe_allow_html=True)
    
    elif tab_selection == "🔍 Anomalies & Groupings":
        st.markdown('<div style="text-align: center;"><h1 class="main-title">🔍 ANOMALIES</h1></div>', unsafe_allow_html=True)
        
        if not uploaded_file:
            st.markdown("""
            <div class="info-box">
                <h3 style="color: white;">👈 Upload Your Solar Data to Get Started</h3>
                <p style="color: white; font-size: 1.1rem;">Use the file uploader in the sidebar to begin analyzing your solar panel performance.</p>
            </div>
            """, unsafe_allow_html=True)
            return
        
        with st.spinner("🔄 Loading and analyzing your data..."):
            df = load_clean_data(uploaded_file)
        
        if df.empty:
            return
        
        with st.spinner("🔍 Detecting anomalies..."):
            df = detect_anomalies(df, contamination)
        
        if 'EFFICIENCY_%' in df.columns and 'SOURCE_ID' in df.columns and len(df['SOURCE_ID'].unique()) > 1:
            st.markdown('<h3 class="section-header">⚡ Efficiency Anomalies by Inverter</h3>', unsafe_allow_html=True)
            
            with st.spinner("Analyzing efficiency anomalies across all inverters..."):
                eff_fig = detect_efficiency_anomalies(df, contamination)
            
            if eff_fig:
                st.plotly_chart(eff_fig, use_container_width=True)
                
                st.markdown("""
                <div class="info-box">
                    <h4 style="color: white;">📊 How to Use This Chart</h4>
                    <p style="color: white; font-size: 1.05rem;">Use the dropdown menu in the top-right corner to switch between different inverters. 
                    The <strong>blue line</strong> shows efficiency over time, and <strong>red X marks</strong> indicate detected anomalies. 
                    Hover over data points for detailed information.</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.warning("⚠️ Could not generate efficiency anomaly chart. Ensure your data includes efficiency metrics.")
        
        st.markdown("---")
        
        st.markdown('<h3 class="section-header">🚨 Anomaly Detection Results</h3>', unsafe_allow_html=True)
        
        anomalies = df[df['anomaly']].copy()
        
        st.markdown(f"""
        <div class="ai-insight-card">
            <h3>🤖 AI Anomaly Analysis</h3>
            <div style="color: #1e40af; font-size: 1.05rem; line-height: 1.9;">
                {generate_comprehensive_ai_summary(df, anomalies).split('Anomaly Analysis:')[1].split('Temporal Patterns:')[0] if 'Anomaly Analysis:' in generate_comprehensive_ai_summary(df, anomalies) else 'Analyzing anomaly patterns...'}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if not anomalies.empty:
            anomalies['TIME_STAMP'] = pd.to_datetime(anomalies['TIME_STAMP'])
            anomalies['Formatted Time'] = anomalies['TIME_STAMP'].dt.strftime('%Y-%m-%d %H:%M')
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"""
                <div class="warning-box">
                    <h3 style="color: #1e3a8a; margin-top: 0;">⚠️ Found {len(anomalies)} Anomalies ({(len(anomalies)/len(df)*100):.1f}% of data)</h3>
                    <p style="color: #1e3a8a; font-size: 1.05rem; line-height: 1.7;">These unusual readings might indicate:</p>
                    <ul style="color: #1e3a8a; font-size: 1rem; line-height: 1.7;">
                        <li><strong>Equipment issues:</strong> Malfunctions or inefficiencies in inverters or panels</li>
                        <li><strong>Environmental factors:</strong> Shading from trees, buildings, or passing clouds</li>
                        <li><strong>Maintenance needs:</strong> Dust, dirt, or debris accumulation on panels</li>
                        <li><strong>Weather events:</strong> Storms, heavy cloud cover, or atmospheric conditions</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="metric-card-yellow">
                    <h4 style="color: #1e3a8a; margin: 0;">Anomaly Rate</h4>
                    <h2 style="color: #1e3a8a; margin: 0.5rem 0;">{(len(anomalies)/len(df)*100):.1f}%</h2>
                    <p style="color: #1e3a8a; margin: 0;">{len(anomalies)} out of {len(df):,} readings</p>
                </div>
                """, unsafe_allow_html=True)
                
                anomaly_pct = (len(anomalies)/len(df)*100)
                if anomaly_pct < 2:
                    severity_color = "success-box"
                    severity_text = "Low - Normal"
                elif anomaly_pct < 5:
                    severity_color = "warning-box"
                    severity_text = "Moderate"
                else:
                    severity_color = "warning-box"
                    severity_text = "High - Review Needed"
                
                st.markdown(f"""
                <div class="{severity_color}">
                    <h4 style="margin: 0;">Severity Level</h4>
                    <p style="margin: 0.5rem 0 0 0; font-weight: 600;">{severity_text}</p>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown('<h4 class="section-header">📊 Anomaly Distribution Over Time</h4>', unsafe_allow_html=True)
            
            if 'TIME_STAMP' in anomalies.columns:
                anomalies_hourly = anomalies.copy()
                anomalies_hourly['hour'] = anomalies_hourly['TIME_STAMP'].dt.hour
                hourly_anomaly_count = anomalies_hourly.groupby('hour').size().reset_index(name='count')
                
                fig_anom_dist = go.Figure()
                fig_anom_dist.add_trace(go.Bar(
                    x=hourly_anomaly_count['hour'],
                    y=hourly_anomaly_count['count'],
                    marker_color='#fbbf24',
                    hovertemplate='<b>Hour:</b> %{x}:00<br><b>Anomalies:</b> %{y}<extra></extra>'
                ))
                
                fig_anom_dist.update_layout(
                    height=350,
                    template='plotly_white',
                    xaxis_title='Hour of Day',
                    yaxis_title='Number of Anomalies',
                    showlegend=False
                )
                
                st.plotly_chart(fig_anom_dist, use_container_width=True)
            
            with st.expander(f"📋 View All {len(anomalies)} Anomalies", expanded=False):
                display_cols = ['Formatted Time', 'Value']
                if 'SOURCE_ID' in anomalies.columns:
                    display_cols.append('SOURCE_ID')
                if 'EFFICIENCY_%' in anomalies.columns:
                    display_cols.append('EFFICIENCY_%')
                if 'anomaly_score' in anomalies.columns:
                    display_cols.append('anomaly_score')
                
                anomaly_display = anomalies[display_cols].copy()
                anomaly_display = anomaly_display.rename(columns={
                    'Formatted Time': 'Time',
                    'Value': 'Power (kW)',
                    'SOURCE_ID': 'Inverter',
                    'EFFICIENCY_%': 'Efficiency (%)',
                    'anomaly_score': 'Anomaly Score'
                })
                
                st.dataframe(anomaly_display, use_container_width=True)
            
            if zapier_url:
                st.markdown("---")
                st.markdown('<h4 class="section-header">🔗 Export to Zapier</h4>', unsafe_allow_html=True)
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown("""
                    <div class="blue-card">
                        <h4 style="color: #1e3a8a; margin-top: 0;">📤 Ready to Send Anomalies</h4>
                        <p style="color: #1e40af;">Click the button to export today's anomalies to your Zapier workflow. 
                        This will trigger any actions you've configured (email, SMS, Slack, etc.).</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    if st.button("📤 Export Today's Anomalies", type="primary", use_container_width=True):
                        today = pd.Timestamp(date.today()).date()
                        anomalies['DateOnly'] = anomalies['TIME_STAMP'].dt.date
                        anomalies_today = anomalies[anomalies['DateOnly'] == today]
                        
                        if anomalies_today.empty:
                            st.info("ℹ️ No anomalies detected today. Try selecting a different date range.")
                        else:
                            anomaly_data = {
                                'date': str(today),
                                'total_anomalies': len(anomalies_today),
                                'anomaly_rate': f"{(len(anomalies_today)/len(df)*100):.1f}%",
                                'anomalies': [
                                    {
                                        'timestamp': str(row['TIME_STAMP']),
                                        'value': float(row['Value']),
                                        'source': str(row.get('SOURCE_ID', 'Unknown')),
                                        'efficiency': float(row.get('EFFICIENCY_%', 0)) if pd.notna(row.get('EFFICIENCY_%')) else None
                                    }
                                    for _, row in anomalies_today.head(10).iterrows()
                                ]
                            }
                            
                            with st.spinner("Sending to Zapier..."):
                                success, result = send_to_zapier(anomaly_data, zapier_url)
                                if success:
                                    st.success(f"✅ Successfully sent {len(anomalies_today)} anomalies to Zapier!")
                                else:
                                    st.error(f"❌ Failed to send: {result}")
            else:
                st.markdown("""
                <div class="info-box">
                    <h4 style="color: white;">💡 Enable Zapier Integration</h4>
                    <p style="color: white; font-size: 1.05rem;">Add your Zapier webhook URL in the sidebar to automatically export anomalies 
                    and receive alerts via email, SMS, Slack, or any other platform!</p>
                </div>
                """, unsafe_allow_html=True)
        
        else:
            st.markdown("""
            <div class="success-box">
                <h3 style="color: white; margin-top: 0;">✅ All Clear!</h3>
                <p style="color: white; font-size: 1.1rem; line-height: 1.7;">
                No anomalies detected in your solar data. Your system is performing consistently and within normal parameters. 
                This indicates proper maintenance and optimal operating conditions. Keep up the great work!
                </p>
            </div>
            """, unsafe_allow_html=True)
        
        if 'EFFICIENCY_%' in df.columns and 'SOURCE_ID' in df.columns and len(df['SOURCE_ID'].unique()) > 1:
            st.markdown("---")
            st.markdown('<h3 class="section-header">⚡ Inverter Performance Grouping</h3>', unsafe_allow_html=True)
            
            high, medium_high, medium_low, low, summary = analyze_inverter_performance(df)
            
            if not all(x.empty for x in [high, medium_high, medium_low, low]):
                st.markdown("""
                <div class="blue-card">
                    <h4 style="color: #1e3a8a; margin-top: 0;">📊 Understanding Performance Quartiles</h4>
                    <p style="font-size: 1.05rem; color: #1e40af; line-height: 1.7;">
                    Your inverters have been grouped by performance quartiles using statistical analysis. This helps identify 
                    which units are working optimally and which might need attention. Quartiles divide your inverters into 
                    four equal groups based on their average power output.
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("#### 🌟 Top Performers (75-100%)")
                    if not high.empty:
                        high_display = high[['SOURCE_ID_NUMBER', 'AC_POWER_FIXED', 'Max_Power']].copy()
                        high_display.columns = ['Inverter', 'Avg Power (kW)', 'Peak Power (kW)']
                        st.dataframe(high_display, use_container_width=True, hide_index=True)
                        st.markdown("""
                        <div class="success-box">
                            <p style="color: white; margin: 0;">✅ These inverters are your best performers!</p>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.info("No inverters in this category")
                    
                    st.markdown("#### 📊 Below Average (25-50%)")
                    if not medium_low.empty:
                        ml_display = medium_low[['SOURCE_ID_NUMBER', 'AC_POWER_FIXED', 'Max_Power']].copy()
                        ml_display.columns = ['Inverter', 'Avg Power (kW)', 'Peak Power (kW)']
                        st.dataframe(ml_display, use_container_width=True, hide_index=True)
                        st.markdown("""
                        <div class="warning-box">
                            <p style="color: #1e3a8a; margin: 0;">⚠️ Monitor these inverters for improvements</p>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.info("No inverters in this category")
                
                with col2:
                    st.markdown("#### ✅ Above Average (50-75%)")
                    if not medium_high.empty:
                        mh_display = medium_high[['SOURCE_ID_NUMBER', 'AC_POWER_FIXED', 'Max_Power']].copy()
                        mh_display.columns = ['Inverter', 'Avg Power (kW)', 'Peak Power (kW)']
                        st.dataframe(mh_display, use_container_width=True, hide_index=True)
                        st.markdown("""
                        <div class="info-box">
                            <p style="color: white; margin: 0;">👍 Solid performance from these units</p>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.info("No inverters in this category")
                    
                    st.markdown("#### ⚠️ Needs Attention (0-25%)")
                    if not low.empty:
                        low_display = low[['SOURCE_ID_NUMBER', 'AC_POWER_FIXED', 'Max_Power']].copy()
                        low_display.columns = ['Inverter', 'Avg Power (kW)', 'Peak Power (kW)']
                        st.dataframe(low_display, use_container_width=True, hide_index=True)
                        st.markdown("""
                        <div class="warning-box">
                            <p style="color: #1e3a8a; margin: 0; font-weight: 600;">🔧 Priority: These inverters need maintenance or inspection</p>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown("""
                        <div class="success-box">
                            <p style="color: white; margin: 0;">✅ No underperforming inverters detected!</p>
                        </div>
                        """, unsafe_allow_html=True)
                
                st.markdown("### 📋 Detailed Performance Summary")
                
                with st.expander("View Complete Statistics", expanded=True):
                    st.json(summary)
    
    elif tab_selection == "📈 Forecasting":
        st.markdown('<div style="text-align: center;"><h1 class="main-title">📈 FORECASTING</h1></div>', unsafe_allow_html=True)
        
        if not uploaded_file:
            st.markdown("""
            <div class="info-box">
                <h3 style="color: white;">👈 Upload Your Solar Data to Get Started</h3>
                <p style="color: white; font-size: 1.1rem;">Use the file uploader in the sidebar to begin analyzing your solar panel performance.</p>
            </div>
            """, unsafe_allow_html=True)
            return
        
        with st.spinner("🔄 Loading your data..."):
            df = load_clean_data(uploaded_file)
        
        if df.empty:
            return
        
        st.markdown("""
        <div class="blue-card">
            <h3 style="color: #1e3a8a;">🔮 How Our Forecasting Works</h3>
            <p style="color: #1e40af; font-size: 1.05rem; line-height: 1.7;">
            We use advanced machine learning algorithms to predict your solar panel output based on historical patterns. 
            Our models analyze temporal features (time of day, day of week, seasonality), rolling averages, and sequential 
            patterns to generate accurate forecasts. This helps you plan energy usage, identify potential issues, and 
            understand when production might be lower than expected.
            </p>
            <p style="color: #1e40af; font-size: 1.05rem; line-height: 1.7; margin-top: 1rem;">
            <strong>Current Model:</strong> {model_name} — Selected for optimal balance of accuracy and performance for your dataset.
            </p>
        </div>
        """.format(model_name=forecast_model.replace('_', ' ').title()), unsafe_allow_html=True)
        
        progress_container = st.empty()
        
        with progress_container:
            with st.spinner(f"🤖 Training {forecast_model.replace('_', ' ').title()} model on your data..."):
                forecast_df, metrics, error = run_forecast(df, model_type=forecast_model)
        
        progress_container.empty()
        
        if error:
            st.error(f"❌ Forecasting error: {error}")
            st.info("💡 Tip: Forecasting requires at least 50 data points for reliable predictions. Try uploading more data.")
            return
        
        if not forecast_df.empty and metrics:
            st.markdown('<h3 class="section -header">📊 Forecast Accuracy Metrics</h3>', unsafe_allow_html=True)
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(f"""
                <div class="metric-card-dark">
                    <h4 style="color: white; margin: 0;">R² Score</h4>
                    <h2 style="color: white; margin: 0.5rem 0;">{metrics['r2']:.3f}</h2>
                    <p style="color: rgba(255,255,255,0.8); margin: 0;">Model accuracy</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="metric-card-light">
                    <h4 style="color: white; margin: 0;">RMSE</h4>
                    <h2 style="color: white; margin: 0.5rem 0;">{metrics['rmse']:.2f}</h2>
                    <p style="color: rgba(255,255,255,0.8); margin: 0;">Root mean sq error</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div class="metric-card-yellow">
                    <h4 style="color: #1e3a8a; margin: 0;">MAPE</h4>
                    <h2 style="color: #1e3a8a; margin: 0.5rem 0;">{metrics['mape']:.1f}%</h2>
                    <p style="color: #1e3a8a; margin: 0;">Avg prediction error</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col4:
                st.markdown(f"""
                <div class="metric-card-dark">
                    <h4 style="color: white; margin: 0;">CV Score</h4>
                    <h2 style="color: white; margin: 0.5rem 0;">{metrics['cv_mean']:.3f}</h2>
                    <p style="color: rgba(255,255,255,0.8); margin: 0;">Cross-validation</p>
                </div>
                """, unsafe_allow_html=True)
            
            r2 = metrics['r2']
            model_name = metrics.get('model_type', 'unknown')
            
            if model_name == 'linear_regression' and r2 < 0:
                accuracy_msg = "⚠️ Simple linear regression shows negative R² because solar energy has complex daily/seasonal patterns that a straight line cannot capture. Try Gradient Boosting or Random Forest for better accuracy with pattern-rich data."
                box_class = "warning-box"
            elif r2 > 0.85:
                accuracy_msg = "🌟 Excellent forecasting accuracy! Your predictions are highly reliable."
                box_class = "success-box"
            elif r2 > 0.7:
                accuracy_msg = "✅ Good forecasting accuracy. Predictions are generally reliable."
                box_class = "info-box"
            elif r2 > 0.5:
                accuracy_msg = "⚠️ Moderate accuracy. Consider collecting more data for better predictions."
                box_class = "warning-box"
            elif r2 > 0:
                accuracy_msg = "❗ Limited accuracy. Try a different model or collect more historical data."
                box_class = "warning-box"
            else:
                accuracy_msg = "❌ Negative R² indicates this model type is not suitable for your data's patterns. Please select a different forecasting model."
                box_class = "warning-box"
            
            st.markdown(f"""
            <div class="{box_class}">
                <h4 style="margin-top: 0;">📈 Model Performance Assessment</h4>
                <p style="font-size: 1.1rem; margin: 0;">{accuracy_msg}</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            st.markdown('<h3 class="section-header">📊 Forecast vs Actual Comparison</h3>', unsafe_allow_html=True)
            
            fig_forecast = go.Figure()
            
            fig_forecast.add_trace(go.Scatter(
                x=forecast_df['Index'],
                y=forecast_df['Actual'],
                mode='lines',
                name='Actual Values',
                line=dict(color='#3b82f6', width=2),
                hovertemplate='<b>Actual:</b> %{y:.2f} kW<extra></extra>'
            ))
            
            fig_forecast.add_trace(go.Scatter(
                x=forecast_df['Index'],
                y=forecast_df['Predicted'],
                mode='lines',
                name='Predicted Values',
                line=dict(color='#fbbf24', width=2, dash='dash'),
                hovertemplate='<b>Predicted:</b> %{y:.2f} kW<extra></extra>'
            ))
            
            fig_forecast.update_layout(
                height=500,
                template='plotly_white',
                hovermode='x unified',
                xaxis_title='Data Point Index',
                yaxis_title='Power Output (kW)',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            
            st.plotly_chart(fig_forecast, use_container_width=True)
            
            st.markdown("---")
            
            st.markdown('<h3 class="section-header">📉 Prediction Error Analysis</h3>', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig_error = go.Figure()
                fig_error.add_trace(go.Scatter(
                    x=forecast_df['Index'],
                    y=forecast_df['Error'],
                    mode='lines',
                    name='Absolute Error',
                    fill='tozeroy',
                    line=dict(color='#ef4444', width=2),
                    hovertemplate='<b>Error:</b> %{y:.2f} kW<extra></extra>'
                ))
                
                fig_error.update_layout(
                    height=400,
                    template='plotly_white',
                    xaxis_title='Data Point Index',
                    yaxis_title='Absolute Error (kW)',
                    showlegend=False
                )
                
                st.plotly_chart(fig_error, use_container_width=True)
            
            with col2:
                fig_pct_error = go.Figure()
                fig_pct_error.add_trace(go.Scatter(
                    x=forecast_df['Index'],
                    y=forecast_df['Percent_Error'],
                    mode='lines',
                    name='Percent Error',
                    fill='tozeroy',
                    line=dict(color='#f59e0b', width=2),
                    hovertemplate='<b>Error:</b> %{y:.1f}%<extra></extra>'
                ))
                
                fig_pct_error.update_layout(
                    height=400,
                    template='plotly_white',
                    xaxis_title='Data Point Index',
                    yaxis_title='Percentage Error (%)',
                    showlegend=False
                )
                
                st.plotly_chart(fig_pct_error, use_container_width=True)
            
            st.markdown("---")
            
            st.markdown('<h3 class="section-header">🎯 Detailed Forecast Statistics</h3>', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"""
                <div class="blue-card">
                    <h4 style="color: #1e3a8a; margin-top: 0;">📊 Statistical Summary</h4>
                    <ul style="color: #1e40af; font-size: 1.05rem; line-height: 2;">
                        <li><strong>Test Points:</strong> {metrics['test_points']:,}</li>
                        <li><strong>Mean Absolute Error:</strong> {metrics['mae']:.2f} kW</li>
                        <li><strong>Training R²:</strong> {metrics['train_r2']:.3f}</li>
                        <li><strong>CV Std Dev:</strong> {metrics['cv_std']:.3f}</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="yellow-card">
                    <h4 style="color: #1e3a8a; margin-top: 0;">💡 Interpretation Guide</h4>
                    <p style="color: #1e40af; font-size: 1.05rem; line-height: 1.7;">
                    <strong>R² Score:</strong> Measures prediction accuracy (1.0 = perfect, 0.0 = poor)<br>
                    <strong>RMSE:</strong> Average prediction error magnitude<br>
                    <strong>MAPE:</strong> Average percentage difference from actual values<br>
                    <strong>CV Score:</strong> Model consistency across different data subsets
                    </p>
                </div>
                """, unsafe_allow_html=True)
            
            with st.expander("📋 View Detailed Forecast Data", expanded=False):
                display_forecast = forecast_df.copy()
                display_forecast.columns = ['Index', 'Actual (kW)', 'Predicted (kW)', 'Error (kW)', 'Error (%)']
                st.dataframe(display_forecast, use_container_width=True, hide_index=True)
            
            anomalies_for_forecast = df[df['anomaly']] if 'anomaly' in df.columns else pd.DataFrame()
            comprehensive_summary = generate_comprehensive_ai_summary(df, anomalies_for_forecast, metrics)
            
            st.markdown("---")
            st.markdown(f"""
            <div class="ai-insight-card">
                <h3>🤖 Complete AI Analysis with Forecasting</h3>
                <div style="color: #1e40af; font-size: 1.05rem; line-height: 1.9;">
                    {comprehensive_summary.replace(chr(10), '<br>')}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        else:
            st.warning("⚠️ Unable to generate forecast. Ensure your data has sufficient historical records (at least 50 points).")

if __name__ == "__main__":
    main()