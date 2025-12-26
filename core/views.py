from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import pandas as pd
import json
import os
from datetime import date
import plotly.graph_objects as go

from .models import UploadedFile, AnalysisSession
from .data_science.data_processing import load_clean_data, DEFAULT_CONTAMINATION
from .data_science.anomaly_detection import detect_anomalies, detect_efficiency_anomalies
from .data_science.forecasting import run_forecast
from .data_science.analytics import (
    generate_ai_insights, 
    generate_comprehensive_ai_summary,
    analyze_inverter_performance
)


def login_view(request):
    """Login page"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Invalid username or password')
    
    return render(request, 'login.html')


def signup_view(request):
    """Signup page"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        
        if password != password2:
            messages.error(request, 'Passwords do not match')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
        elif User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered')
        else:
            user = User.objects.create_user(username=username, email=email, password=password)
            login(request, user)
            return redirect('home')
    
    return render(request, 'signup.html')


def logout_view(request):
    """Logout"""
    logout(request)
    return redirect('login')


@login_required
def home_view(request):
    """Home page - Landing"""
    return render(request, 'home.html')


@login_required
def data_overview_view(request):
    """Data Overview page"""
    context = {
        'contamination': request.session.get('contamination', DEFAULT_CONTAMINATION),
        'forecast_model': request.session.get('forecast_model', 'gradient_boosting'),
    }
    
    # Check if file is uploaded
    if 'uploaded_file_path' not in request.session:
        context['no_data'] = True
        return render(request, 'data_overview.html', context)
    
    file_path = request.session['uploaded_file_path']
    if not os.path.exists(file_path):
        context['no_data'] = True
        return render(request, 'data_overview.html', context)
    
    # Load data
    df, error, detected_cols = load_clean_data(file_path)
    if error or df.empty:
        context['error'] = error or "Failed to load data"
        return render(request, 'data_overview.html', context)
    
    # Store in session for other views
    request.session['data_loaded'] = True
    request.session['detected_columns'] = detected_cols
    
    # Calculate statistics
    stats = {
        'total_rows': len(df),
        'date_range': f"{df['TIME_STAMP'].min()} to {df['TIME_STAMP'].max()}",
        'mean': df['Value'].mean(),
        'median': df['Value'].median(),
        'std': df['Value'].std(),
        'min': df['Value'].min(),
        'max': df['Value'].max(),
        'q25': df['Value'].quantile(0.25),
        'q75': df['Value'].quantile(0.75),
    }
    
    # Detect anomalies for insights
    contamination = request.session.get('contamination', DEFAULT_CONTAMINATION)
    df, _ = detect_anomalies(df, contamination)
    anomalies = df[df['anomaly']]
    
    # Generate insights
    insights = generate_ai_insights(df, anomalies)
    
    # Create power output chart
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['TIME_STAMP'],
        y=df['Value'],
        mode='lines',
        name='Power Output',
        line=dict(color='#3b82f6', width=2),
        hovertemplate='<b>Time:</b> %{x}<br><b>Power:</b> %{y:.2f} kW<extra></extra>'
    ))
    
    if not anomalies.empty:
        fig.add_trace(go.Scatter(
            x=anomalies['TIME_STAMP'],
            y=anomalies['Value'],
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
    
    chart_html = fig.to_html(full_html=False, include_plotlyjs='cdn')
    
    # Daily production if multiple days
    daily_chart_html = None
    if 'TIME_STAMP' in df.columns:
        df_daily = df.copy()
        df_daily['date'] = pd.to_datetime(df_daily['TIME_STAMP']).dt.date
        
        if len(df_daily['date'].unique()) > 1:
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
            
            daily_chart_html = fig_daily.to_html(full_html=False, include_plotlyjs='cdn')
    
    context.update({
        'stats': stats,
        'insights': insights,
        'chart_html': chart_html,
        'daily_chart_html': daily_chart_html,
        'detected_columns': ', '.join(detected_cols),
    })
    
    return render(request, 'data_overview.html', context)


@login_required
def anomalies_view(request):
    """Anomalies detection page"""
    context = {
        'contamination': request.session.get('contamination', DEFAULT_CONTAMINATION),
    }
    
    if 'uploaded_file_path' not in request.session:
        context['no_data'] = True
        return render(request, 'anomalies.html', context)
    
    file_path = request.session['uploaded_file_path']
    if not os.path.exists(file_path):
        context['no_data'] = True
        return render(request, 'anomalies.html', context)
    
    # Load data
    df, error, _ = load_clean_data(file_path)
    if error or df.empty:
        context['error'] = error
        return render(request, 'anomalies.html', context)
    
    # Detect anomalies
    contamination = request.session.get('contamination', DEFAULT_CONTAMINATION)
    df, error = detect_anomalies(df, contamination)
    if error:
        context['error'] = error
        return render(request, 'anomalies.html', context)
    
    anomalies = df[df['anomaly']].copy()
    
    # Generate AI summary
    comprehensive_summary = generate_comprehensive_ai_summary(df, anomalies)
    
    context['anomaly_count'] = len(anomalies)
    context['total_rows'] = len(df)
    context['anomaly_pct'] = (len(anomalies) / len(df) * 100) if len(df) > 0 else 0
    context['comprehensive_summary'] = comprehensive_summary
    
    # Efficiency anomaly chart
    eff_chart_html = None
    if 'EFFICIENCY_%' in df.columns and 'SOURCE_ID' in df.columns and len(df['SOURCE_ID'].unique()) > 1:
        eff_fig, eff_error = detect_efficiency_anomalies(df, contamination)
        if eff_fig and not eff_error:
            eff_chart_html = eff_fig.to_html(full_html=False, include_plotlyjs='cdn')
    
    context['eff_chart_html'] = eff_chart_html
    
    # Anomaly distribution chart
    anomaly_dist_html = None
    if not anomalies.empty and 'TIME_STAMP' in anomalies.columns:
        anomalies_hourly = anomalies.copy()
        anomalies_hourly['hour'] = pd.to_datetime(anomalies_hourly['TIME_STAMP']).dt.hour
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
        
        anomaly_dist_html = fig_anom_dist.to_html(full_html=False, include_plotlyjs='cdn')
    
    context['anomaly_dist_html'] = anomaly_dist_html
    
    # Anomaly table data
    if not anomalies.empty:
        anomalies['TIME_STAMP'] = pd.to_datetime(anomalies['TIME_STAMP'])
        anomalies['Formatted_Time'] = anomalies['TIME_STAMP'].dt.strftime('%Y-%m-%d %H:%M')
        
        # Rename columns to avoid template syntax issues with special characters
        anomalies_renamed = anomalies.rename(columns={'EFFICIENCY_%': 'EFFICIENCY_PCT'})
        
        display_cols = ['Formatted_Time', 'Value']
        if 'SOURCE_ID' in anomalies_renamed.columns:
            display_cols.append('SOURCE_ID')
        if 'EFFICIENCY_PCT' in anomalies_renamed.columns:
            display_cols.append('EFFICIENCY_PCT')
        if 'anomaly_score' in anomalies_renamed.columns:
            display_cols.append('anomaly_score')
        
        anomaly_display = anomalies_renamed[display_cols].head(100).to_dict('records')
        context['anomaly_table'] = anomaly_display
    
    # Inverter performance grouping
    inverter_data = None
    if 'EFFICIENCY_%' in df.columns and 'SOURCE_ID' in df.columns and len(df['SOURCE_ID'].unique()) > 1:
        high, medium_high, medium_low, low, summary = analyze_inverter_performance(df)
        
        if not all(x.empty for x in [high, medium_high, medium_low, low]):
            inverter_data = {
                'high': high.to_dict('records') if not high.empty else [],
                'medium_high': medium_high.to_dict('records') if not medium_high.empty else [],
                'medium_low': medium_low.to_dict('records') if not medium_low.empty else [],
                'low': low.to_dict('records') if not low.empty else [],
                'summary': summary
            }
    
    context['inverter_data'] = inverter_data
    
    return render(request, 'anomalies.html', context)


@login_required
def forecasting_view(request):
    """Forecasting page"""
    forecast_model = request.session.get('forecast_model', 'gradient_boosting')
    forecast_model_display = forecast_model.replace('_', ' ').title()
    
    context = {
        'forecast_model': forecast_model,
        'forecast_model_display': forecast_model_display,
    }
    
    if 'uploaded_file_path' not in request.session:
        context['no_data'] = True
        return render(request, 'forecasting.html', context)
    
    file_path = request.session['uploaded_file_path']
    if not os.path.exists(file_path):
        context['no_data'] = True
        return render(request, 'forecasting.html', context)
    
    # Load data
    df, error, _ = load_clean_data(file_path)
    if error or df.empty:
        context['error'] = error
        return render(request, 'forecasting.html', context)
    
    # Run forecast
    forecast_model = request.session.get('forecast_model', 'gradient_boosting')
    forecast_df, metrics, error = run_forecast(df, model_type=forecast_model)
    
    if error:
        context['error'] = error
        return render(request, 'forecasting.html', context)
    
    if forecast_df.empty or not metrics:
        context['error'] = "Unable to generate forecast"
        return render(request, 'forecasting.html', context)
    
    context['metrics'] = metrics
    
    # Forecast chart
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
    
    context['forecast_chart_html'] = fig_forecast.to_html(full_html=False, include_plotlyjs='cdn')
    
    # Error charts
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
    
    context['error_chart_html'] = fig_error.to_html(full_html=False, include_plotlyjs='cdn')
    
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
    
    context['pct_error_chart_html'] = fig_pct_error.to_html(full_html=False, include_plotlyjs='cdn')
    
    # Comprehensive AI summary
    contamination = request.session.get('contamination', DEFAULT_CONTAMINATION)
    df_with_anomalies, _ = detect_anomalies(df, contamination)
    anomalies = df_with_anomalies[df_with_anomalies['anomaly']]
    comprehensive_summary = generate_comprehensive_ai_summary(df, anomalies, metrics)
    context['comprehensive_summary'] = comprehensive_summary
    
    return render(request, 'forecasting.html', context)


@login_required
def upload_file(request):
    """Handle file upload"""
    if request.method == 'POST' and request.FILES.get('file'):
        uploaded_file = request.FILES['file']
        
        # Save file
        file_instance = UploadedFile.objects.create(
            user=request.user if request.user.is_authenticated else None,
            file=uploaded_file,
            filename=uploaded_file.name,
            file_size=uploaded_file.size
        )
        
        # Store path in session
        request.session['uploaded_file_path'] = file_instance.file.path
        request.session['uploaded_filename'] = uploaded_file.name
        
        messages.success(request, f'File "{uploaded_file.name}" uploaded successfully!')
        return redirect('data_overview')
    
    return redirect('home')


@login_required
def update_settings(request):
    """Update analysis settings"""
    if request.method == 'POST':
        contamination = float(request.POST.get('contamination', DEFAULT_CONTAMINATION))
        forecast_model = request.POST.get('forecast_model', 'gradient_boosting')
        
        request.session['contamination'] = contamination
        request.session['forecast_model'] = forecast_model
        
        messages.success(request, 'Settings updated!')
    
    return redirect(request.META.get('HTTP_REFERER', 'home'))
