"""Metric computation for MED-001 model evaluation.

Computes all metrics needed for token payload construction:
  AUC-ROC, AUC-PR, Brier score, sensitivity, specificity, PPV, NPV at threshold.
Also computes the AUC contract floor check for approximation_quality_gap.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
)

from adapter.models import AUC_CONTRACT_FLOOR


@dataclass
class ThresholdMetrics:
    threshold: float
    sensitivity: float  # recall / TPR
    specificity: float  # TNR
    ppv: float          # precision
    npv: float
    nnt: float          # 1/ppv — alerts per true positive
    false_alert_rate: float  # FPR = 1 - specificity
    n_pos: int
    n_neg: int
    n_tp: int
    n_fp: int
    n_tn: int
    n_fn: int


@dataclass
class ModelMetricsComputed:
    model_id: str
    dataset_id: str
    auc_roc: float
    auc_pr: float
    brier_score: float
    approximation_quality_gap_open: bool  # True if AUC < AUC_CONTRACT_FLOOR
    threshold_metrics: dict[float, ThresholdMetrics]  # threshold → metrics


def compute_metrics(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    model_id: str,
    dataset_id: str,
    thresholds: list[float] | None = None,
) -> ModelMetricsComputed:
    """Compute all MED-001 metrics for a model's predicted probabilities."""
    if thresholds is None:
        thresholds = [0.1, 0.2, 0.3, 0.4, 0.5]

    auc_roc = roc_auc_score(y_true, y_prob)
    auc_pr  = average_precision_score(y_true, y_prob)
    # Brier requires probabilities in [0,1]; clip for rule-based scores (e.g. raw mmol/L)
    y_prob_clipped = np.clip(y_prob / max(y_prob.max(), 1.0), 0.0, 1.0)
    brier   = brier_score_loss(y_true, y_prob_clipped)

    threshold_metrics = {}
    for thr in thresholds:
        y_pred = (y_prob >= thr).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
        sens = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        spec = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        ppv  = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        npv  = tn / (tn + fn) if (tn + fn) > 0 else 0.0
        nnt  = 1.0 / ppv if ppv > 0 else float("inf")
        threshold_metrics[thr] = ThresholdMetrics(
            threshold=thr,
            sensitivity=round(sens, 4),
            specificity=round(spec, 4),
            ppv=round(ppv, 4),
            npv=round(npv, 4),
            nnt=round(nnt, 2),
            false_alert_rate=round(1.0 - spec, 4),
            n_pos=int(tp + fn),
            n_neg=int(tn + fp),
            n_tp=int(tp), n_fp=int(fp),
            n_tn=int(tn), n_fn=int(fn),
        )

    return ModelMetricsComputed(
        model_id=model_id,
        dataset_id=dataset_id,
        auc_roc=round(auc_roc, 4),
        auc_pr=round(auc_pr, 4),
        brier_score=round(brier, 4),
        approximation_quality_gap_open=auc_roc < AUC_CONTRACT_FLOOR,
        threshold_metrics=threshold_metrics,
    )
