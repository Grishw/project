from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, Any, Tuple
import numpy as np
import tensorflow as tf


@dataclass
class ModelConfig:
    model_type: str  # mlp|cnn|rnn
    window: int
    horizon: int
    epochs: int = 10
    batch_size: int = 32
    learning_rate: float = 1e-3
    val_split: float = 0.2


def make_dataset(series: np.ndarray, window: int, horizon: int) -> Tuple[np.ndarray, np.ndarray]:
    X, y = [], []
    for i in range(0, len(series) - window - horizon + 1):
        X.append(series[i:i+window])
        y.append(series[i+window:i+window+horizon])
    X = np.array(X)[..., np.newaxis]
    y = np.array(y)
    return X, y


def build_mlp(window: int, horizon: int, lr: float) -> tf.keras.Model:
    inp = tf.keras.Input(shape=(window, 1))
    x = tf.keras.layers.Flatten()(inp)
    x = tf.keras.layers.Dense(128, activation='relu')(x)
    x = tf.keras.layers.Dense(64, activation='relu')(x)
    out = tf.keras.layers.Dense(horizon)(x)
    model = tf.keras.Model(inp, out)
    model.compile(optimizer=tf.keras.optimizers.Adam(lr), loss='mse', metrics=['mae'])
    return model


def build_cnn(window: int, horizon: int, lr: float) -> tf.keras.Model:
    inp = tf.keras.Input(shape=(window, 1))
    x = tf.keras.layers.Conv1D(32, 3, activation='relu', padding='causal')(inp)
    x = tf.keras.layers.Conv1D(32, 3, activation='relu', padding='causal')(x)
    x = tf.keras.layers.GlobalAveragePooling1D()(x)
    x = tf.keras.layers.Dense(64, activation='relu')(x)
    out = tf.keras.layers.Dense(horizon)(x)
    model = tf.keras.Model(inp, out)
    model.compile(optimizer=tf.keras.optimizers.Adam(lr), loss='mse', metrics=['mae'])
    return model


def build_rnn(window: int, horizon: int, lr: float) -> tf.keras.Model:
    inp = tf.keras.Input(shape=(window, 1))
    x = tf.keras.layers.SimpleRNN(64, return_sequences=False)(inp)
    x = tf.keras.layers.Dense(64, activation='relu')(x)
    out = tf.keras.layers.Dense(horizon)(x)
    model = tf.keras.Model(inp, out)
    model.compile(optimizer=tf.keras.optimizers.Adam(lr), loss='mse', metrics=['mae'])
    return model


def build_model(cfg: ModelConfig) -> tf.keras.Model:
    if cfg.model_type == 'mlp':
        return build_mlp(cfg.window, cfg.horizon, cfg.learning_rate)
    if cfg.model_type == 'cnn':
        return build_cnn(cfg.window, cfg.horizon, cfg.learning_rate)
    if cfg.model_type == 'rnn':
        return build_rnn(cfg.window, cfg.horizon, cfg.learning_rate)
    raise ValueError('unknown model_type')


def _load_or_build_model(cfg: ModelConfig, save_dir: str | None) -> tuple[tf.keras.Model, bool]:
    """Пытается загрузить ранее сохранённую модель для дообучения.
    Возвращает (model, continued)."""
    continued = False
    if save_dir:
        path = os.path.join(save_dir, 'model.keras')
        if os.path.exists(path):
            try:
                mdl = tf.keras.models.load_model(path)
                # Проверка совместимости форм: (None, window, 1) и выход horizon
                ok = True
                try:
                    in_shape = mdl.input_shape
                    out_shape = mdl.output_shape
                    if isinstance(in_shape, (list, tuple)):
                        in_shape = in_shape[0]
                    if isinstance(out_shape, (list, tuple)):
                        out_shape = out_shape[0]
                    if in_shape and len(in_shape) >= 3:
                        ok = ok and (in_shape[1] == cfg.window)
                    if out_shape and len(out_shape) >= 2:
                        ok = ok and (out_shape[-1] == cfg.horizon)
                except Exception:
                    ok = True
                if ok:
                    continued = True
                    return mdl, continued
            except Exception:
                pass
    return build_model(cfg), continued


def train_and_predict(series: np.ndarray, cfg: ModelConfig, save_dir: str | None = None) -> Dict[str, Any]:
    X, y = make_dataset(series, cfg.window, cfg.horizon)
    if len(X) < 2:
        raise ValueError('Недостаточно данных для обучения')
    model = build_model(cfg)
    history = model.fit(X, y, epochs=cfg.epochs, batch_size=cfg.batch_size, verbose=0)
    last_window = series[-cfg.window:][np.newaxis, ..., np.newaxis]
    pred = model.predict(last_window, verbose=0)[0]
    result = {
        'loss': float(history.history['loss'][-1]),
        'prediction': pred.tolist(),
    }
    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
        model.save(os.path.join(save_dir, 'model.keras'))
        with open(os.path.join(save_dir, 'train_meta.txt'), 'w', encoding='utf-8') as f:
            f.write(str(cfg))
    return result


def train_model(series: np.ndarray, cfg: ModelConfig, save_dir: str | None = None) -> Dict[str, Any]:
    """Только обучение и сохранение модели.
    Возвращает финальный loss.
    """
    X, y = make_dataset(series, cfg.window, cfg.horizon)
    if len(X) < 2:
        raise ValueError('Недостаточно данных для обучения')
    model, continued = _load_or_build_model(cfg, save_dir)
    history = model.fit(
        X, y,
        epochs=cfg.epochs,
        batch_size=cfg.batch_size,
        validation_split=max(0.0, min(0.5, float(cfg.val_split))),
        verbose=0
    )
    train_loss = float(history.history['loss'][-1])
    val_loss = float(history.history.get('val_loss', [train_loss])[-1])
    val_mae = float(history.history.get('val_mae', [0.0])[-1])
    loss_curve = [float(v) for v in history.history.get('loss', [])]
    val_loss_curve = [float(v) for v in history.history.get('val_loss', [])]
    mae_curve = [float(v) for v in history.history.get('mae', [])]
    val_mae_curve = [float(v) for v in history.history.get('val_mae', [])]
    saved_name = None
    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
        # Информативное имя файла (повышенная точность и train loss вместо val_loss)
        safe_lr = f"{cfg.learning_rate:.6f}".rstrip('0').rstrip('.')
        safe_loss = f"{train_loss:.6f}"
        filename = f"model_{cfg.model_type}_win{cfg.window}_hor{cfg.horizon}_ep{cfg.epochs}_bs{cfg.batch_size}_lr{safe_lr}_loss{safe_loss}.keras"
        model.save(os.path.join(save_dir, filename))
        # Копия по умолчанию для прогнозатора
        model.save(os.path.join(save_dir, 'model.keras'))
        with open(os.path.join(save_dir, 'train_meta.txt'), 'w', encoding='utf-8') as f:
            f.write(str(cfg))
        saved_name = filename
    return {
        'loss': train_loss,
        'val_loss': val_loss,
        'val_mae': val_mae,
        'model_file': saved_name,
        'loss_curve': loss_curve,
        'val_loss_curve': val_loss_curve,
        'mae_curve': mae_curve,
        'val_mae_curve': val_mae_curve,
        'continued': continued,
    }


def iterative_forecast(series: np.ndarray, model_path: str, window: int, steps: int, horizon: int, context: int | None = None) -> np.ndarray:
    """Итеративный прогноз: модель предсказывает horizon точек, которые
    по мере необходимости добавляются в хвост ряда, пока не наберём steps.
    """
    if steps <= 0:
        return np.array([], dtype=float)
    model = tf.keras.models.load_model(model_path)
    buffer = np.array(series, dtype=float).copy()
    # если задано количество точек контекста для первого прогноза — обрежем
    if context is not None and context > 0 and context <= buffer.shape[0]:
        buffer = buffer[-context:]
    out: list[float] = []
    while len(out) < steps*horizon:
        last_window = buffer[-window:][np.newaxis, ..., np.newaxis]
        pred = model.predict(last_window, verbose=0)[0]
        # добираем столько, сколько нужно
        need = min(horizon, steps*horizon - len(out))
        out.extend(pred[:need].tolist())
        buffer = np.concatenate([buffer, pred[:need]])
    return np.array(out, dtype=float)
