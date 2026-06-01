"""Challenge 2019 data loader.

Loads PhysioNet Challenge 2019 .psv files into a DataFrame suitable for
model training and metric computation.

Each .psv file is one patient; rows are hourly observations.
Columns: HR, O2Sat, Temp, SBP, MAP, DBP, Resp, EtCO2, 26 lab values,
         Age, Gender, Unit1, Unit2, HospAdmTime, ICULOS, SepsisLabel.
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

DATA_ROOT = Path(__file__).resolve().parents[1] / "data" / "challenge2019" / "training"
SET_A_DIR = DATA_ROOT / "training_setA"
SET_B_DIR = DATA_ROOT / "training_setB"

FEATURES = [
    "HR", "O2Sat", "Temp", "SBP", "MAP", "DBP", "Resp",
    "BUN", "Creatinine", "Glucose", "Lactate", "WBC",
    "Bilirubin_total", "Platelets",
    "ICULOS",
]

LABEL_COL = "SepsisLabel"
PATIENT_ID_COL = "patient_id"


def load_set(set_dir: Path, max_patients: int | None = None) -> pd.DataFrame:
    """Load all .psv files from a set directory into a single DataFrame.

    Adds a patient_id column derived from the filename.
    """
    frames = []
    files = sorted(set_dir.glob("*.psv"))
    if max_patients:
        files = files[:max_patients]
    for f in files:
        df = pd.read_csv(f, sep="|")
        df[PATIENT_ID_COL] = f.stem
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def make_patient_level(df: pd.DataFrame, hours_before_onset: int = 6) -> pd.DataFrame:
    """Convert hourly rows to one row per patient for classification.

    Label: 1 if patient develops sepsis, 0 otherwise.
    Features: last observation before the prediction horizon.
    For sepsis patients, prediction horizon = onset_hour - hours_before_onset.
    For non-sepsis patients, use the last available hour.
    """
    rows = []
    for pid, group in df.groupby(PATIENT_ID_COL):
        group = group.reset_index(drop=True)
        sepsis_rows = group[group[LABEL_COL] == 1]
        if len(sepsis_rows) > 0:
            onset_idx = sepsis_rows.index[0]
            cutoff = max(0, onset_idx - hours_before_onset)
            obs = group.iloc[cutoff]
            label = 1
        else:
            obs = group.iloc[-1]
            label = 0
        row = {col: obs.get(col, np.nan) for col in FEATURES}
        row[LABEL_COL] = label
        row[PATIENT_ID_COL] = pid
        rows.append(row)
    return pd.DataFrame(rows)


def impute(df: pd.DataFrame) -> pd.DataFrame:
    """Forward-fill then median-impute remaining NaNs per feature column."""
    df = df.copy()
    for col in FEATURES:
        if col in df.columns:
            df[col] = df[col].fillna(df[col].median())
    return df
