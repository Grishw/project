from __future__ import annotations

from typing import Dict, Any, Tuple, List
import numpy as np
import pandas as pd


def fill_missing(df: pd.DataFrame) -> pd.DataFrame:
    # Простая стратегия: forward fill, затем backward fill, затем средним
    filled = df.copy()
    filled = filled.ffill().bfill()
    for c in filled.columns:
        if filled[c].isna().any():
            if pd.api.types.is_numeric_dtype(filled[c]):
                filled[c] = filled[c].fillna(filled[c].mean())
            else:
                filled[c] = filled[c].fillna(method="ffill").fillna(method="bfill")
    return filled


def select_last_segment(df: pd.DataFrame, length: int = 200) -> pd.DataFrame:
    if len(df) <= length:
        return df.copy()
    return df.iloc[-length:].copy()


def cusum_bounds(series: pd.Series, k: float = 0.5, h: float = 5.0) -> List[int]:
    # CUSUM для обнаружения сдвигов среднего, возвращаем индексы границ
    x = series.astype(float).to_numpy()
    s_pos = 0.0
    s_neg = 0.0
    mean = np.mean(x)
    bounds: List[int] = []
    for i in range(len(x)):
        s_pos = max(0.0, s_pos + (x[i] - mean - k))
        s_neg = min(0.0, s_neg + (x[i] - mean + k))
        if s_pos > h or s_neg < -h:
            bounds.append(i)
            s_pos = 0.0
            s_neg = 0.0
            mean = np.mean(x[max(0, i - 100): i + 1])
    return bounds


def select_cusum_segment(df: pd.DataFrame, target: str, back_window: int = 600) -> Tuple[pd.DataFrame, List[int]]:
    # Берём последние back_window наблюдений и находим последнюю границу
    window_df = df.iloc[-back_window:] if len(df) > back_window else df.copy()
    bnds = cusum_bounds(window_df[target]) if target in window_df.columns else []
    if bnds:
        last_idx = bnds[-1]
        seg = window_df.iloc[last_idx:].copy()
    else:
        seg = select_last_segment(window_df, 200)
    return seg, bnds


def change_duration_curve(series: pd.Series, pct: float = 0.05) -> Dict[str, Any]:
    # y: длина цепочки подряд идущих значений в пределах +-pct от стартового
    # знак y зависит от направления изменения: положит., если текущее > стартового; отрицат., если ниже
    x_marks: List[int] = []
    y_vals: List[int] = []
    arr = series.astype(float).to_numpy()
    n = len(arr)
    i = 0
    while i < n:
        start = arr[i]
        if np.isnan(start):
            i += 1
            continue
        limit_low = start * (1 - pct)
        limit_high = start * (1 + pct)
        j = i
        while j < n and not np.isnan(arr[j]) and (limit_low <= arr[j] <= limit_high):
            j += 1
        length = j - i
        if j < n and not np.isnan(arr[j]):
            sign = 1 if arr[j] > start else -1
        else:
            sign = 0
        x_marks.append(j if j < n else n - 1)
        y_vals.append(sign * length)
        i = max(j, i + 1)
    return {"x": x_marks, "y": y_vals}


def preprocess_pipeline(df: pd.DataFrame, target: str, method: str = "cusum") -> Dict[str, Any]:
    clean = fill_missing(df)
    if method == "last":
        seg = select_last_segment(clean, 200)
        bounds = []
    else:
        seg, bounds = select_cusum_segment(clean, target=target)
    curve = change_duration_curve(seg[target]) if target in seg.columns else {"x": [], "y": []}
    return {
        "segment": seg,
        "bounds": bounds,
        "curve": curve,
    }

