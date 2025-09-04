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
    model.compile(optimizer=tf.keras.optimizers.Adam(lr), loss='mse')
    return model


def build_cnn(window: int, horizon: int, lr: float) -> tf.keras.Model:
    inp = tf.keras.Input(shape=(window, 1))
    x = tf.keras.layers.Conv1D(32, 3, activation='relu', padding='causal')(inp)
    x = tf.keras.layers.Conv1D(32, 3, activation='relu', padding='causal')(x)
    x = tf.keras.layers.GlobalAveragePooling1D()(x)
    x = tf.keras.layers.Dense(64, activation='relu')(x)
    out = tf.keras.layers.Dense(horizon)(x)
    model = tf.keras.Model(inp, out)
    model.compile(optimizer=tf.keras.optimizers.Adam(lr), loss='mse')
    return model


def build_rnn(window: int, horizon: int, lr: float) -> tf.keras.Model:
    inp = tf.keras.Input(shape=(window, 1))
    x = tf.keras.layers.SimpleRNN(64, return_sequences=False)(inp)
    x = tf.keras.layers.Dense(64, activation='relu')(x)
    out = tf.keras.layers.Dense(horizon)(x)
    model = tf.keras.Model(inp, out)
    model.compile(optimizer=tf.keras.optimizers.Adam(lr), loss='mse')
    return model


def build_model(cfg: ModelConfig) -> tf.keras.Model:
    if cfg.model_type == 'mlp':
        return build_mlp(cfg.window, cfg.horizon, cfg.learning_rate)
    if cfg.model_type == 'cnn':
        return build_cnn(cfg.window, cfg.horizon, cfg.learning_rate)
    if cfg.model_type == 'rnn':
        return build_rnn(cfg.window, cfg.horizon, cfg.learning_rate)
    raise ValueError('unknown model_type')


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

