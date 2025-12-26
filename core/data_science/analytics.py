"""
Analytics and AI Insights Module
Extracted from streamlit_app.py - No modifications to core logic
"""
import pandas as pd
import numpy as np


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
        df_temp['TIME_STAMP'] = pd.to_datetime(df_temp['TIME_STAMP'])
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
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), {}


