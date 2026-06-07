"""§3 Data-generating process.

Synthetic worlds w = (T_min, D, V) drawn from a frost-prone climatology with
heterogeneous dwell time D (radiative vs advective regimes) and phenology
stage V (vulnerable post-budbreak vs hardy dormant). The forecast p_hat is a
*calibrated* probabilistic prediction of `1[T_min < tau]`, generated as a
correctly-specified conditional probability of T_min < tau given a noisy
predictor of T_min (so calibration is by construction, but mild miscalibration
can be injected to test the gate).

All numeric constants are PLACEHOLDERS pending citation to cold-hardiness
tables. Values here are chosen for *qualitative* fidelity to the frost
literature, not numerical accuracy.

Heterogeneity knob. The Arm 1 sweep needs to hold p_hat fixed while widening
the (D, V) spread inside the fiber F(e). We expose `heterogeneity_scale`
∈ [0, 1]: 0 collapses the (D, V) distribution to a single deterministic point
(homogeneous-loss control), 1 uses the full bimodal mixture. Intermediate
values interpolate.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np

# ── PLACEHOLDER meteorological constants ──────────────────────────────────────
#
# These are stand-ins. Replace with WSU/OSU cold-hardiness sourced values
# before any of this reaches the paper. The qualitative shape — saturating
# damage in degree-minutes-below-threshold, modulated by phenology stage — is
# what we are demonstrating, not the precise numbers.

# Damaging-frost threshold (°C). Grapevine post-budbreak critical temperature
# is ~ -2 °C in published tables; -2.5 is conservative placeholder.
DAMAGE_THRESHOLD_C = -2.5

# Damage logistic parameters
#   g(w) = sigmoid(alpha * (tau - T_min) * D - beta(V))
# alpha in (°C·min)^-1, beta(V) dimensionless threshold offset.
ALPHA_DAMAGE = 0.003                  # (°C·min)^-1 PLACEHOLDER

# Phenology stages → beta(V): smaller beta = more vulnerable.
PHENOLOGY_BETAS: dict[str, float] = {
    "dormant":    8.0,                # essentially indestructible
    "swollen":    4.0,                # waking, moderate cold-hardiness
    "budbreak":   1.5,                # vulnerable
    "leaf_out":   0.5,                # highly vulnerable
}

# Maximum loss (currency units; arbitrary scale)
L_MAX = 1.0

# Cost of running the protection action (energy + labor) regardless of frost
COST_C = 0.10            # PLACEHOLDER cost-to-loss ratio C/L_max = 0.10

# Scalar loss cost-loss is *handed* (i.e. the loss it assumes; may differ from
# the true heterogeneous L_real)
L_BAR_SCALAR = L_MAX     # cost-loss uses the maximum loss as the scalar loss

# Climatology of overnight minimums for the budbreak window (°C). Skew-normal
# fit shape; chosen so the marginal Pr(T_min < tau) sits in the operating
# region of interest (0.15 - 0.40).
T_MIN_LOC = 1.0                        # °C
T_MIN_SCALE = 3.0                      # °C
T_MIN_SKEW = -2.0                      # left-skewed (long tail toward cold)

# Dwell-time model
#   D | T_min, regime — radiative nights have long dwell; advective short.
#   Radiative regime: D ~ Gamma(shape_r, scale_r), modulated by (tau - T_min)+
#   Advective regime: D ~ Gamma(shape_a, scale_a), shorter
REGIME_RADIATIVE_RATE = 0.55           # 55% of frost nights are radiative
DWELL_RADIATIVE_SHAPE = 4.0
DWELL_RADIATIVE_SCALE = 60.0           # minutes; mean dwell ~ 240 min
DWELL_ADVECTIVE_SHAPE = 2.0
DWELL_ADVECTIVE_SCALE = 25.0           # mean dwell ~ 50 min

# Phenology calendar: probability of each stage over the simulation window.
# In a real run this would be a deterministic function of date; for the
# synthetic experiment we sample to allow varying heterogeneity within the
# fiber.
PHENOLOGY_PROBS = {
    "dormant":  0.20,
    "swollen":  0.25,
    "budbreak": 0.30,
    "leaf_out": 0.25,
}

# Forecast model: T_min has a noisy NWP predictor available the prior evening
FORECAST_NOISE_SD = 1.5                # °C — predictor noise

# ── Sampling ──────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class World:
    t_min: float                       # °C
    dwell_minutes: float               # minutes T < tau (0 if T_min >= tau)
    phenology: str                     # phenology stage
    regime: str                        # "radiative" or "advective"
    forecast_t_min: float              # noisy NWP predictor of T_min
    # Derived (for convenience; computed deterministically from w):
    l_real: float                      # realized loss
    frost_event: bool                  # 1[T_min < tau]


def _skewnorm_sample(rng: np.random.Generator, loc: float, scale: float,
                     a: float, size: int) -> np.ndarray:
    """Skew-normal sampling (Azzalini). Avoids scipy dependency."""
    delta = a / math.sqrt(1.0 + a * a)
    u0 = rng.standard_normal(size)
    v = rng.standard_normal(size)
    u1 = delta * np.abs(u0) + math.sqrt(1.0 - delta * delta) * v
    return loc + scale * u1


def _damage_fraction(t_min: float, dwell: float, phenology: str) -> float:
    """g(w) ∈ [0, 1] — fraction of L_max realized in this world."""
    if t_min >= DAMAGE_THRESHOLD_C or dwell <= 0.0:
        return 0.0
    degree_minutes = (DAMAGE_THRESHOLD_C - t_min) * dwell
    beta = PHENOLOGY_BETAS[phenology]
    return float(1.0 / (1.0 + math.exp(-(ALPHA_DAMAGE * degree_minutes - beta))))


def sample_worlds(
    n: int,
    seed: int = 42,
    heterogeneity_scale: float = 1.0,
    homogeneous_loss: bool = False,
) -> list[World]:
    """Sample n worlds from the synthetic climatology.

    heterogeneity_scale ∈ [0, 1]
      0 → collapse (D, V) to a single deterministic point (mean dwell, fixed
          stage = 'budbreak'). Used for the homogeneous-loss null control.
      1 → full bimodal dwell + four-stage phenology mixture.
      intermediate → blend.

    homogeneous_loss
      If True, override L_real to a single scalar = mean L_real across the
      full bimodal mixture. Used for the §7.2 null control.
    """
    rng = np.random.default_rng(seed)
    t_min = _skewnorm_sample(rng, T_MIN_LOC, T_MIN_SCALE, T_MIN_SKEW, n)

    # Phenology
    stages = list(PHENOLOGY_PROBS.keys())
    probs = np.array([PHENOLOGY_PROBS[s] for s in stages])
    if heterogeneity_scale < 1.0:
        # Interpolate toward a delta at 'budbreak'
        delta = np.array([1.0 if s == "budbreak" else 0.0 for s in stages])
        probs = heterogeneity_scale * probs + (1.0 - heterogeneity_scale) * delta
        probs = probs / probs.sum()
    phenology_idx = rng.choice(len(stages), size=n, p=probs)
    phenology = [stages[i] for i in phenology_idx]

    # Regime
    regime_radiative = rng.random(n) < REGIME_RADIATIVE_RATE
    regime = np.where(regime_radiative, "radiative", "advective")

    # Dwell time
    dwell = np.zeros(n)
    frost = t_min < DAMAGE_THRESHOLD_C
    rad_mask = frost & regime_radiative
    adv_mask = frost & ~regime_radiative
    if rad_mask.any():
        dwell[rad_mask] = rng.gamma(
            DWELL_RADIATIVE_SHAPE, DWELL_RADIATIVE_SCALE, size=int(rad_mask.sum())
        )
    if adv_mask.any():
        dwell[adv_mask] = rng.gamma(
            DWELL_ADVECTIVE_SHAPE, DWELL_ADVECTIVE_SCALE, size=int(adv_mask.sum())
        )
    if heterogeneity_scale < 1.0:
        # Interpolate dwell toward its mean (collapsing variance)
        dwell_mean = float(np.mean(dwell[dwell > 0])) if (dwell > 0).any() else 0.0
        dwell = (heterogeneity_scale * dwell
                 + (1.0 - heterogeneity_scale) * dwell_mean * (dwell > 0))

    # Noisy NWP predictor
    forecast_t_min = t_min + rng.normal(0.0, FORECAST_NOISE_SD, size=n)

    worlds = []
    losses = []
    for i in range(n):
        g = _damage_fraction(float(t_min[i]), float(dwell[i]), phenology[i])
        l_real = L_MAX * g
        losses.append(l_real)
        worlds.append(World(
            t_min=float(t_min[i]),
            dwell_minutes=float(dwell[i]),
            phenology=phenology[i],
            regime=str(regime[i]),
            forecast_t_min=float(forecast_t_min[i]),
            l_real=float(l_real),
            frost_event=bool(t_min[i] < DAMAGE_THRESHOLD_C),
        ))

    if homogeneous_loss:
        scalar_l = float(np.mean(losses))
        worlds = [
            World(
                t_min=w.t_min, dwell_minutes=w.dwell_minutes,
                phenology=w.phenology, regime=w.regime,
                forecast_t_min=w.forecast_t_min,
                l_real=scalar_l, frost_event=w.frost_event,
            )
            for w in worlds
        ]

    return worlds


# ── Calibrated forecast probability ───────────────────────────────────────────
#
# A "correctly specified" forecaster knows the conditional distribution of
# T_min given the noisy predictor and reports:
#   p_hat = Pr(T_min < tau | forecast_t_min)
# This is calibrated by construction. We compute it analytically from the
# Gaussian observation model.

def forecast_probability(forecast_t_min: float) -> float:
    """Pr(T_min < tau | forecast_t_min) under the Gaussian observation model.

    forecast_t_min = T_min + noise,  noise ~ N(0, sigma^2)
    Posterior of T_min given forecast_t_min is approximately Gaussian with
    mean = (sigma_prior^2 * forecast + sigma_obs^2 * mu_prior) / (sigma_prior^2 + sigma_obs^2)
    and variance = sigma_prior^2 * sigma_obs^2 / (sigma_prior^2 + sigma_obs^2)
    (approximating the skew-normal prior by its second moments).
    """
    sigma_prior = T_MIN_SCALE
    sigma_obs = FORECAST_NOISE_SD
    var_post = (sigma_prior**2 * sigma_obs**2) / (sigma_prior**2 + sigma_obs**2)
    mean_post = (
        (sigma_prior**2 * forecast_t_min + sigma_obs**2 * T_MIN_LOC)
        / (sigma_prior**2 + sigma_obs**2)
    )
    std_post = math.sqrt(var_post)
    # Pr(T_min < tau)
    z = (DAMAGE_THRESHOLD_C - mean_post) / std_post
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def add_forecast_probabilities(worlds: list[World]) -> list[dict]:
    """Return a list of world+p_hat dicts."""
    return [
        {**asdict(w), "p_hat": forecast_probability(w.forecast_t_min)}
        for w in worlds
    ]


# ── I/O ───────────────────────────────────────────────────────────────────────

def write_world_table(worlds: list[World], path: Path) -> None:
    import csv
    rows = add_forecast_probabilities(worlds)
    fields = list(rows[0].keys())
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def constants_summary() -> dict:
    return {
        "DAMAGE_THRESHOLD_C": DAMAGE_THRESHOLD_C,
        "ALPHA_DAMAGE": ALPHA_DAMAGE,
        "PHENOLOGY_BETAS": PHENOLOGY_BETAS,
        "L_MAX": L_MAX,
        "COST_C": COST_C,
        "L_BAR_SCALAR": L_BAR_SCALAR,
        "T_MIN_LOC": T_MIN_LOC,
        "T_MIN_SCALE": T_MIN_SCALE,
        "T_MIN_SKEW": T_MIN_SKEW,
        "REGIME_RADIATIVE_RATE": REGIME_RADIATIVE_RATE,
        "DWELL_RADIATIVE_SHAPE": DWELL_RADIATIVE_SHAPE,
        "DWELL_RADIATIVE_SCALE": DWELL_RADIATIVE_SCALE,
        "DWELL_ADVECTIVE_SHAPE": DWELL_ADVECTIVE_SHAPE,
        "DWELL_ADVECTIVE_SCALE": DWELL_ADVECTIVE_SCALE,
        "PHENOLOGY_PROBS": PHENOLOGY_PROBS,
        "FORECAST_NOISE_SD": FORECAST_NOISE_SD,
        "_note": "All constants are PLACEHOLDERS pending citation.",
    }
