"""
Anomaly Detection Module
Extracted from streamlit_app.py - No modifications to core logic
"""
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

MIN_DATA_ROWS = 10
DEFAULT_CONTAMINATION = 0.02


def detect_anomalies(df, contamination=DEFAULT_CONTAMINATION):
    """Enhanced anomaly detection with better accuracy."""
    df = df.copy()
    if len(df) < MIN_DATA_ROWS:
        df["anomaly"] = False
        return df, None
    
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
        
        return df, None
        
    except Exception as e:
        df["anomaly"] = False
        df["anomaly_score"] = 0
        return df, f"Anomaly detection error: {str(e)}"


def detect_efficiency_anomalies(df, contamination=DEFAULT_CONTAMINATION):
    """Enhanced efficiency anomaly detection with dropdown."""
    try:
        df_clean = df[df['EFFICIENCY_%'].between(0.1, 100)].copy()
        if df_clean.empty:
            return None, "No valid efficiency data"
        
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
        return fig, None
    except Exception as e:
        return None, f"Error in efficiency anomaly detection: {str(e)}"

