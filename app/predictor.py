"""
predictor.py
Loads disk_model.pkl and runs prediction on a scanned disk row.
Returns a structured result dict with label, confidence, and per-feature breakdown.
"""

import joblib
import pandas as pd
import numpy as np
from pathlib import Path


# Features the model was trained on — order must match model.feature_names_in_ exactly
MODEL_FEATURES = [
    'capacity_gigabytes',
    'smart_1_raw',
    'smart_3_raw',
    'smart_4_raw',
    'smart_5_raw',
    'smart_7_raw',
    'smart_9_raw',
    'smart_12_raw',
    'smart_187_raw',
    'smart_188_raw',
    'smart_191_raw',
    'smart_192_raw',
    'smart_193_raw',
    'smart_197_raw',
    'smart_198_raw',
    'is_ssd',
    'any_critical_error',
    'total_error_count',
    'error_per_gb',
]

# Human-readable names for SMART attributes shown in the breakdown
FEATURE_LABELS = {
    'smart_1_raw':       'Read Error Rate (1)',
    'smart_3_raw':       'Spin-Up Time (3)',
    'smart_4_raw':       'Start/Stop Count (4)',
    'smart_5_raw':       'Reallocated Sectors (5)',
    'smart_7_raw':       'Seek Error Rate (7)',
    'smart_9_raw':       'Power-On Hours (9)',
    'smart_12_raw':      'Power Cycle Count (12)',
    'smart_187_raw':     'Uncorrectable Errors (187)',
    'smart_188_raw':     'Command Timeout (188)',
    'smart_191_raw':     'G-Sense Error Rate (191)',
    'smart_192_raw':     'Power-Off Retract Count (192)',
    'smart_193_raw':     'Load/Unload Cycle Count (193)',
    'smart_197_raw':     'Pending Sectors (197)',
    'smart_198_raw':     'Uncorrectable Sector Count (198)',
    'capacity_gigabytes':'Disk Capacity (GB)',
    'is_ssd':            'Disk Type (SSD=1 / HDD=0)',
    'any_critical_error':'Any Critical Error Flag',
    'total_error_count': 'Total Critical Error Count',
    'error_per_gb':      'Errors per GB',
}

# Critical SMART attributes — shown with warning highlight in breakdown
CRITICAL_ATTRS = {
    'smart_5_raw', 'smart_187_raw', 'smart_197_raw',
    'smart_198_raw', 'any_critical_error', 'total_error_count'
}


class Predictor:
    def __init__(self, model_path: str = 'disk_model.pkl'):
        model_file = Path(model_path)
        if not model_file.exists():
            raise FileNotFoundError(
                f"Model file not found at '{model_path}'.\n"
                "Make sure disk_model.pkl is in the same directory as the app."
            )
        self.model = joblib.load(model_path)

        # Load feature importances if available
        self.feature_importances = {}
        if hasattr(self.model, 'feature_importances_'):
            importances = self.model.feature_importances_
            self.feature_importances = dict(zip(MODEL_FEATURES, importances))

    def predict(self, scan_row: pd.DataFrame) -> dict:
        """
        Runs prediction on a scanned disk row.

        Returns a dict:
        {
            'label':       'Healthy' | 'Failed',
            'confidence':  float (0.0 - 1.0),
            'verdict':     str (human readable summary),
            'breakdown':   list of dicts per feature,
            'disk_name':   str,
            'disk_path':   str,
        }
        """
        # Extract display info before dropping metadata columns
        disk_name = scan_row['_model_name'].iloc[0] if '_model_name' in scan_row.columns else 'Unknown'
        disk_path = scan_row['_disk_path'].iloc[0] if '_disk_path' in scan_row.columns else ''

        # Prepare feature matrix — drop metadata, fill any missing features with 0
        X = scan_row.drop(columns=[c for c in scan_row.columns if c.startswith('_')], errors='ignore')
        for feature in MODEL_FEATURES:
            if feature not in X.columns:
                X[feature] = 0
        X = X[MODEL_FEATURES]

        # Predict
        prediction = self.model.predict(X)[0]
        probabilities = self.model.predict_proba(X)[0]

        label = 'Failed' if prediction == 1 else 'Healthy'
        confidence = float(probabilities[prediction])

        # Build per-feature breakdown
        breakdown = []
        for feature in MODEL_FEATURES:
            value = float(X[feature].iloc[0])
            importance = self.feature_importances.get(feature, 0.0)
            is_critical = feature in CRITICAL_ATTRS
            is_triggered = is_critical and value > 0

            breakdown.append({
                'feature':     feature,
                'label':       FEATURE_LABELS.get(feature, feature),
                'value':       value,
                'importance':  round(importance * 100, 2),  # as percentage
                'is_critical': is_critical,
                'is_triggered': is_triggered,
            })

        # Sort breakdown by importance descending
        breakdown.sort(key=lambda x: x['importance'], reverse=True)

        # Human readable verdict
        if label == 'Healthy':
            verdict = f"This disk appears healthy with {confidence*100:.1f}% confidence."
        else:
            verdict = (
                f"This disk is predicted to FAIL with {confidence*100:.1f}% confidence. "
                f"Immediate attention recommended."
            )

        return {
            'label':      label,
            'confidence': confidence,
            'verdict':    verdict,
            'breakdown':  breakdown,
            'disk_name':  disk_name,
            'disk_path':  disk_path,
        }
