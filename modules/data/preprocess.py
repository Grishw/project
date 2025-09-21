from __future__ import annotations
from modules.ChaosLogic.chaos_logic import cusum, DisorderResult, get_more_points, get_point_with_max_index, local_fractal_dimension

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


def select_cusum_segment(df: pd.DataFrame, target: str) -> Tuple[pd.DataFrame, List[int]]:
    window_df = df.copy()
    result = cusum(window_df[target]) if target in window_df.columns else []
    bnds = result.indMax

    if bnds:
        arr = get_more_points(bnds, result.B, 0.2)
        bnds_last = get_point_with_max_index(arr)
        seg = window_df.iloc[bnds_last:].copy()
    else:
        seg = select_last_segment(window_df, 200)
    return seg, bnds

def change_duration_curve(series: pd.Series, pct: float = 0.05) -> Dict[str, Any]:
    """
    Функция вычисляет изменение длительности серий значений в заданном диапазоне отклонений (+/- pct).
    
    :param series: Входной временной ряд
    :param pct: Процент отклонения от начального значения последовательности
    :return: Словарь с координатами точек ("x" - индексы, "y" - длительность сегментов с направлением изменения)
    """
    x_marks: List[int] = []   # Список позиций начала каждого нового сегмента
    y_vals: List[int] = []    # Значения длины сегментов с учётом знака направления изменений
    arr = series.astype(float).to_numpy()  # Преобразуем серию в массив чисел
    n = len(arr)
    i = 0
    while i < n:
        start = arr[i]
            
        # Определяем границы диапазона (+/- pct% от стартового значения)
        limit_low = start * (1 - pct)
        limit_high = start * (1 + pct)
        
        # Ищем следующую позицию вне диапазона
        j = i
        while j < n and (limit_low <= arr[j] <= limit_high):
            j += 1
        
        # Длина найденного сегмента
        length = j - i
        
        # Определение знака направления следующего элемента относительно первого
        if j >= n or np.isnan(arr[j]):
            sign = 0  # Нет следующего элемента или он NaN
        elif arr[j] > start:
            sign = 1  # Следующее значение выше стартового
        else:
            sign = -1  # Следующее значение ниже стартового
        
        # Добавляем точку графика
        x_marks.append(i)
        y_vals.append(sign * length)
        
        # Переходим к следующей итерации
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

