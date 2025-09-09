import numpy as np
from scipy.signal import find_peaks
import pandas as pd

class DisorderResult:
    def __init__(self, B, indMax):
        self.B = B
        self.indMax = indMax

def cusum(A):
    average = np.mean(A)
    dispersion_sum = np.sqrt(np.sum((A - average) ** 2) * len(A))
    B = np.zeros(len(A))
    indMax = 0
    for i in range(len(A)):
        sum_val = np.sum(A[:i+1] - average)
        B[i] = sum_val / dispersion_sum
        indMax = i if abs(B[i]) > abs(B[indMax]) else indMax
    return DisorderResult(B, indMax)

def min_info_error(A):
        B = np.zeros(len(A))
        c = np.log(2 * np.pi) + 1
        indMax = 0
        for i in range(len(A) - 2):
            c1 = -(i + 1) * (np.log(np.mean(A[:i + 1] ** 2)) + c) / 2
            c2 = -(len(A) - i - 1) * (np.log(np.mean(A[i + 1:] ** 2)) + c) / 2
            c3 = len(A) * (np.log(np.mean(A ** 2)) + c) / 2
            B[i] = c1 + c2 + c3
            indMax = i if abs(B[i]) > abs(B[indMax]) else indMax
        return DisorderResult(B, indMax)

def get_more_points(pointnow, points_data = [], procents = 0.1):
    plus = points_data[pointnow] + points_data[pointnow]*procents
    minus = points_data[pointnow] - (points_data[pointnow]*procents)
    result = []

    if plus < 0:
        l = plus
        plus = minus
        minus = l

    for elem in range(len(points_data)):
        if points_data[elem] < plus:
            if points_data[elem] > minus:
                result.append(elem)
    
    return result

def get_point_with_max_index(points_data = []):
    return points_data[len(points_data)-1]

# Функция для вычисления локальной фрактальной размерности
def local_fractal_dimension(signal, window_size):
    def hurst_exponent(ts):
        N = len(ts)
        T = np.arange(1, N+1)
        Y = np.cumsum(ts - np.mean(ts))
        R = np.maximum.accumulate(Y) - np.minimum.accumulate(Y)
        S = np.std(ts)
        R_S = R / S
        epsilon = 1e-10  # небольшая константа для предотвращения деления на ноль
        return np.polyfit(np.log(T), np.log(R_S + epsilon), 1)[0]
    
    lfd_series = []
    for i in range(len(signal) - window_size + 1):
        window = signal[i:i + window_size]
        lfd = hurst_exponent(window)
        lfd_series.append(lfd)
    
    return np.array(lfd_series)