"""
Data Loading and Processing Module
Extracted from streamlit_app.py - No modifications to core logic
"""
import pandas as pd
import numpy as np
from datetime import datetime

# Constants
MAX_FILE_SIZE = 100_000_000  # 100MB
MIN_DATA_ROWS = 10
DEFAULT_CONTAMINATION = 0.02


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
        return df, None
    except Exception as e:
        return None, f"Error preprocessing data: {str(e)}"


def load_clean_data(file_path):
    """Universal solar data loader with enhanced validation."""
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        return pd.DataFrame(), f"Could not read file: {str(e)}", []
    
    if df.empty:
        return pd.DataFrame(), "The file appears to be empty", []
    
    detected_columns = df.columns.tolist()
    
    # Check if it's inverter data format
    if 'SOURCE_KEY' in df.columns and 'DATE_TIME' in df.columns:
        processed, error = preprocess_inverter_data(df)
        if processed is not None and not processed.empty:
            return processed, None, detected_columns
        return pd.DataFrame(), error, detected_columns
    
    col_map = intelligent_column_mapper(df)
    if not col_map or 'timestamp' not in col_map:
        return pd.DataFrame(), "Could not find required timestamp column", detected_columns
    
    df['TIME_STAMP'] = pd.to_datetime(df[col_map['timestamp']], errors='coerce')
    df = df.dropna(subset=['TIME_STAMP'])
    
    value_candidates = [col_map.get('ac_power'), col_map.get('dc_power'), col_map.get('energy')]
    value_col = next((c for c in value_candidates if c and c in df.columns), None)
    
    if not value_col:
        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        value_col = num_cols[0] if num_cols else None
    
    if not value_col:
        return pd.DataFrame(), "Could not find numeric data column", detected_columns
    
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
    
    return df, None, detected_columns


