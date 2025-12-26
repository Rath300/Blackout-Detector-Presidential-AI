"""
Forecasting Module
Extracted from streamlit_app.py - No modifications to core logic
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error


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
            model = LinearRegression()
            X_train_simple = X_train[['time_index']]
            X_test_simple = X_test[['time_index']]
            model.fit(X_train_simple, y_train)
            y_pred = model.predict(X_test_simple)
            y_train_pred = model.predict(X_train_simple)
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
        
        # Calculate metrics
        mse = mean_squared_error(y_test, y_pred)
        rmse = np.sqrt(mse)
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        train_r2 = r2_score(y_train, y_train_pred)
        
        # Calculate MAPE with error handling
        mape_values = np.abs((y_test - y_pred) / np.where(y_test != 0, y_test, 1))
        mape_values = mape_values[np.isfinite(mape_values)]
        mape = np.mean(mape_values) * 100 if len(mape_values) > 0 else 999.9
        mape = min(mape, 999.9)
        
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


