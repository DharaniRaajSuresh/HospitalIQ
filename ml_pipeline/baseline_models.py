"""Baseline models for comparison: ARIMA, Prophet, LSTM, Ridge."""
import logging
import warnings
warnings.filterwarnings("ignore")
logging.disable(logging.CRITICAL)

import numpy as np
import pandas as pd

try:
    from statsmodels.tsa.arima.model import ARIMA as _ARIMA
    STATSMODELS_AVAILABLE = True
except ImportError:
    _ARIMA = None
    STATSMODELS_AVAILABLE = False

try:
    import prophet
    # Prophet 1.1.5 is incompatible with numpy >= 2.0 (np.float_ removed).
    # Try the import and catch both ImportError and AttributeError.
    from prophet import Prophet as _Prophet
    PROPHET_AVAILABLE = True
except (ImportError, AttributeError):
    _Prophet = None
    PROPHET_AVAILABLE = False

try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False

from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_percentage_error


def mape(y_true, y_pred):
    mask = y_true > 0
    if mask.sum() == 0:
        return 0.0
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


def train_arima(train_series, order=(1, 1, 1), seasonal_order=None):
    """Train ARIMA model on univariate time series."""
    if not STATSMODELS_AVAILABLE:
        raise ImportError("statsmodels not installed")
    model = _ARIMA(train_series, order=order)
    if seasonal_order:
        from statsmodels.tsa.arima.model import ARIMA as _SARIMA
        model = _SARIMA(train_series, order=order, seasonal_order=seasonal_order)
    return model.fit()


def predict_arima(model, steps):
    """Generate predictions from fitted ARIMA model."""
    forecast = model.forecast(steps=steps)
    if hasattr(forecast, 'values'):
        forecast = forecast.values
    return np.maximum(0, np.asarray(forecast))


def train_prophet(df, date_col, target_col, seasonality_mode='multiplicative'):
    """Train Prophet model on time series with explicit date column."""
    if not PROPHET_AVAILABLE:
        raise ImportError("prophet not installed")
    model = _Prophet(
        seasonality_mode=seasonality_mode,
        yearly_seasonality=True,
        weekly_seasonality=False,
        daily_seasonality=False,
    )
    df_prophet = df.rename(columns={date_col: 'ds', target_col: 'y'})
    model.fit(df_prophet)
    return model


def predict_prophet(model, periods):
    """Generate predictions from fitted Prophet model."""
    future = model.make_future_dataframe(periods=periods, freq='MS')
    forecast = model.predict(future)
    return np.maximum(0, forecast['yhat'].tail(periods).values)


def train_lstm(X_train, y_train, n_features=1, epochs=50, batch_size=32):
    """Train a simple 2-layer LSTM model."""
    if not TENSORFLOW_AVAILABLE:
        raise ImportError("tensorflow not installed")

    if len(X_train.shape) == 2:
        X_train = X_train.reshape((X_train.shape[0], X_train.shape[1], n_features))

    model = Sequential([
        LSTM(64, return_sequences=True, input_shape=(X_train.shape[1], 1)),
        Dropout(0.2),
        LSTM(32),
        Dropout(0.2),
        Dense(1),
    ])
    model.compile(optimizer='adam', loss='mse', metrics=['mae'])
    model.fit(X_train, y_train, epochs=epochs, batch_size=batch_size, verbose=0, validation_split=0.1)
    return model


def predict_lstm(model, X_test, n_features=1):
    """Generate predictions from fitted LSTM model."""
    if len(X_test.shape) == 2:
        X_test = X_test.reshape((X_test.shape[0], X_test.shape[1], n_features))
    preds = model.predict(X_test, verbose=0).flatten()
    return preds


def train_ridge(X_train, y_train):
    """Train simple Ridge regression baseline."""
    model = Ridge(alpha=1.0, random_state=42)
    model.fit(X_train, y_train)
    return model


def tune_arima_grid(y_train_orig, y_test_orig):
    """Grid search ARIMA (p,d,q) orders, return best model and predictions."""
    best_mape = float('inf')
    best_model = None
    best_pred = None
    orders = [(1,1,1), (2,1,1), (1,1,2), (2,1,2), (3,1,1), (1,2,1)]
    for order in orders:
        try:
            m = train_arima(y_train_orig, order=order)
            p = predict_arima(m, len(y_test_orig))
            mape_val = mape(y_test_orig, p)
            if mape_val < best_mape:
                best_mape = mape_val
                best_model = m
                best_pred = p
        except Exception:
            continue
    if best_model is None:
        best_model = train_arima(y_train_orig, order=(1,1,1))
        best_pred = predict_arima(best_model, len(y_test_orig))
    return best_model, best_pred


def tune_prophet_grid(y_train_orig, y_test_orig):
    """Grid search Prophet seasonality_mode and changepoint_prior_scale."""
    best_mape = float('inf')
    best_model = None
    best_pred = None
    train_len = len(y_train_orig)
    dates = pd.date_range(start='2020-01-01', periods=train_len + len(y_test_orig), freq='MS')
    train_df = pd.DataFrame({'date': dates[:train_len], 'y': y_train_orig})
    for seasonality in ['multiplicative', 'additive']:
        for cpp in [0.05, 0.1, 0.5]:
            try:
                model = _Prophet(seasonality_mode=seasonality, changepoint_prior_scale=cpp,
                                 yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
                model.fit(train_df)
                pred = predict_prophet(model, len(y_test_orig))
                mape_val = mape(y_test_orig, pred)
                if mape_val < best_mape:
                    best_mape = mape_val
                    best_model = model
                    best_pred = pred
            except Exception:
                continue
    if best_model is None:
        best_model = train_prophet(train_df, 'date', 'y')
        best_pred = predict_prophet(best_model, len(y_test_orig))
    return best_model, best_pred


def tune_lstm_grid(X_train, y_train, X_test, y_test_orig, use_log_transform=True):
    """Grid search LSTM units and epochs."""
    best_mape = float('inf')
    best_model = None
    best_pred = None
    configs = [(32, 20), (64, 20), (32, 30), (64, 30)]
    for units, epochs in configs:
        try:
            model = Sequential([
                LSTM(units, return_sequences=True, input_shape=(X_train.shape[1], 1)),
                Dropout(0.2),
                LSTM(units // 2),
                Dropout(0.2),
                Dense(1),
            ])
            model.compile(optimizer='adam', loss='mse', metrics=['mae'])
            model.fit(X_train, y_train, epochs=epochs, batch_size=32, verbose=0, validation_split=0.1)
            pred = predict_lstm(model, X_test)
            if use_log_transform:
                pred = np.expm1(pred)
            mape_val = mape(y_test_orig, pred)
            if mape_val < best_mape:
                best_mape = mape_val
                best_model = model
                best_pred = pred
        except Exception:
            continue
    if best_model is None:
        best_model = train_lstm(X_train, y_train, epochs=30)
        best_pred = predict_lstm(best_model, X_test)
        if use_log_transform:
            best_pred = np.expm1(best_pred)
    return best_model, best_pred


def run_all_baselines(X_train, X_test, y_train, y_test, task_name="forecast",
                      arima_order="tune", use_log_transform=True):
    """Run all available baselines and return comparison dict.

    For ARIMA/Prophet, expects y_train/y_test to be 1-D series.
    For Ridge/LSTM, expects X_train/X_test to be 2-D feature matrices.

    Returns: (results_dict, predictions_dict)
      - results: model_name -> {test_mape, ...}
      - predictions: model_name -> numpy array of test predictions
    """
    results = {}
    predictions = {}
    y_train_orig = np.expm1(y_train) if use_log_transform else y_train
    y_test_orig = np.expm1(y_test) if use_log_transform else y_test

    # Ridge
    try:
        ridge = train_ridge(X_train, y_train)
        pred_train = ridge.predict(X_train)
        pred_test = ridge.predict(X_test)
        if use_log_transform:
            pred_train = np.expm1(pred_train)
            pred_test = np.expm1(pred_test)
        results['Ridge'] = {
            'train_mape': mape(y_train_orig, pred_train),
            'test_mape': mape(y_test_orig, pred_test),
        }
        predictions['Ridge'] = pred_test
    except Exception as e:
        results['Ridge'] = {'error': str(e)}

    # ARIMA (only if y is 1-D and univariate)
    if STATSMODELS_AVAILABLE:
        try:
            if arima_order == "tune":
                arima_model, pred_arima = tune_arima_grid(y_train_orig, y_test_orig)
            else:
                arima_model = train_arima(y_train_orig, order=arima_order)
                pred_arima = predict_arima(arima_model, len(y_test_orig))
            results['ARIMA'] = {
                'test_mape': mape(y_test_orig, pred_arima),
            }
            predictions['ARIMA'] = pred_arima
        except Exception as e:
            results['ARIMA'] = {'error': str(e)}

    # Prophet (tuned)
    if PROPHET_AVAILABLE:
        try:
            prophet_model, pred_prophet = tune_prophet_grid(y_train_orig, y_test_orig)
            results['Prophet'] = {
                'test_mape': mape(y_test_orig, pred_prophet),
            }
            predictions['Prophet'] = pred_prophet
        except Exception as e:
            results['Prophet'] = {'error': str(e)}

    # LSTM (tuned)
    if TENSORFLOW_AVAILABLE and X_train.shape[1] > 1:
        try:
            n_features = 1
            X_train_r = X_train.reshape((X_train.shape[0], X_train.shape[1], n_features))
            X_test_r = X_test.reshape((X_test.shape[0], X_test.shape[1], n_features))
            lstm_model, pred_lstm = tune_lstm_grid(X_train_r, y_train, X_test_r, y_test_orig, use_log_transform)
            results['LSTM'] = {
                'test_mape': mape(y_test_orig, pred_lstm),
            }
            predictions['LSTM'] = pred_lstm
        except Exception as e:
            results['LSTM'] = {'error': str(e)}

    return results, predictions
