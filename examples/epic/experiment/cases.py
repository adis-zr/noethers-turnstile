"""MED-IND-001 induction corpus drawn from CASE-LIB-001.

Each case records the gap statuses that were OPEN at deployment time,
reconstructed from public evidence. The compiler sees these statuses and
the current profile. When it over-authorizes, the OPEN gap that is not yet
in the taxonomy is the gap to induce.

Design principle (mirrors LEG-001):
  Each induction case is constructed so that all gaps the *current* profile
  tracks are BOUNDED — meaning the compiler has no structural reason to
  block it — but one or more gaps that the current profile does not yet
  track are OPEN. The compiler emits ALR; the expert says < ALR. The
  discrepancy forces a new gap into the taxonomy.

  Held-out cases are not used in induction. They test whether the converged
  taxonomy generalizes.

Gap status values: "open", "bounded", "closed"
Expert judgment values use Permission names: "DIA", "REV", "AEX", "ALR"

The "expert_judgment" field records the maximum permission a domain expert
would grant given the documented failure modes. It is the ceiling the
compiler should not exceed after the taxonomy is correct.

The "blocking_gaps" field records which OPEN gaps explain the discrepancy
between expert_judgment and ALR. These are the gaps the induction loop
will force into the taxonomy.
"""
from __future__ import annotations

# ── Structural skeleton gaps ───────────────────────────────────────────────────
# These two gaps are present from v0 — the bare minimum to distinguish
# "nothing known" (DIA) from "model exists and runs" (REV/AEX).
#
# approximation_quality_gap: is the model's output meaningfully correlated
#   with its training target at all? (AUC / basic validation)
# freshness_gap: were the model inputs current at inference time?
#
# Every other gap is discovered through induction.

GAP_APPROXIMATION_QUALITY = "approximation_quality_gap"
GAP_FRESHNESS             = "freshness_gap"

# ── Induction cases ────────────────────────────────────────────────────────────
# Ordered so each case introduces exactly one new failure mode not yet in
# the taxonomy. Earlier cases exercise gaps that will be discovered first.

INDUCTION_CASES: list[dict] = [

    # ── M01: Positive control ──────────────────────────────────────────────────
    # A model with bounded AQ and freshness on a well-matched population with
    # a low-stakes notification action. The v0 structural profile correctly
    # authorizes this.
    {
        "case_id": "M01",
        "description": "Positive control: well-validated triage tool, notification only",
        "system": "Hypothetical: validated early warning score, single-site, notification blast radius",
        "gap_statuses": {
            GAP_APPROXIMATION_QUALITY: "bounded",
            GAP_FRESHNESS:             "bounded",
            # All domain gaps open — v0 profile does not track them
        },
        "expert_judgment": "ALR",
        "blocking_gaps": [],
        "note": (
            "Positive control: at v0, compiler and expert agree — ALR is correct "
            "for a model with basic validation and low blast radius. "
            "This case should emit ALR under every profile version."
        ),
    },

    # ── M02: Epic Sepsis Model — clinical utility absent ──────────────────────
    # AQ is bounded (AUC 0.76 reported), model specification is bounded
    # (predicts sepsis per Sepsis-3). But no external utility validation was
    # ever published at deployment. Sensitivity=0.33, PPV=0.12 at threshold —
    # discovered only in external validation (Wong et al. 2021).
    # Induces: clinical_utility_gap
    {
        "case_id": "M02",
        "description": "Epic Sepsis Model — high AUC, clinical utility never validated",
        "system": "Epic Sepsis Model; UW Medicine deployment ~2017-2020",
        "reference": "Wong et al. (2021), JAMA Internal Medicine 181(8):1065-1070",
        "gap_statuses": {
            GAP_APPROXIMATION_QUALITY:  "bounded",   # AUC 0.76 reported by vendor
            GAP_FRESHNESS:              "bounded",   # real-time EHR inputs
            "model_specification_gap":  "bounded",   # predicts Sepsis-3 criteria
            "calibration_gap":          "bounded",   # internal calibration reported
            "blast_radius_gap":         "bounded",   # mandatory nursing alert scoped
            # clinical_utility_gap:     OPEN — sensitivity=0.33, PPV=0.12 undisclosed
            # distribution_shift_gap:   OPEN — no external population validation
        },
        "expert_judgment": "REV",
        "blocking_gaps": ["clinical_utility_gap"],
        "note": (
            "At v0 the compiler emits ALR: AQ bounded, freshness bounded, nothing else tracked. "
            "Expert says REV: sensitivity=0.33, PPV=0.12 at the deployed threshold (score ≥ 6). "
            "AUC 0.76 is not contested — it survives because AUC is a ranking measure, "
            "immune to operating-point failures. AUC integrates over all thresholds; it cannot "
            "detect that the alert rate at threshold ≥ 6 is clinically unsustainable. "
            "This is the wrong functional for an action that fires at a specific threshold. "
            "Gap to induce: clinical_utility_gap — sensitivity and PPV at the specific "
            "operating threshold must be bounded before ALR is reachable."
        ),
    },

    # ── M03: Optum racial bias — proxy target mismatch ────────────────────────
    # AQ is bounded (model accurately predicts healthcare costs — its stated
    # target). But the action target is 'identify patients who need more care.'
    # Cost is a proxy for need; it systematically diverges for Black patients
    # due to access barriers. The proxy gap is the failure mode.
    # Induces: model_specification_gap (proxy/target mismatch variant)
    {
        "case_id": "M03",
        "description": "Optum health risk scoring — cost proxy diverges from care-need target",
        "system": "Commercial health risk algorithm, Optum/UnitedHealth; ~200M patients/year",
        "reference": "Obermeyer et al. (2019), Science 366(6464):447-453",
        "gap_statuses": {
            GAP_APPROXIMATION_QUALITY:  "bounded",   # cost prediction was accurate
            GAP_FRESHNESS:              "bounded",
            "clinical_utility_gap":     "bounded",   # cost prediction utility was demonstrated
            "distribution_shift_gap":   "bounded",   # validated on training distribution
            "calibration_gap":          "bounded",   # cost well-calibrated
            # model_specification_gap: OPEN — cost ≠ need; proxy diverges on protected class
            # blast_radius_gap: OPEN — automated enrollment decisions at scale
        },
        "expert_judgment": "REV",
        "blocking_gaps": ["model_specification_gap"],
        "note": (
            "At v1 (after clinical_utility_gap induced), the compiler emits ALR: "
            "AQ bounded, freshness bounded, clinical_utility bounded (cost is well-predicted). "
            "Expert says REV: the training target (cost) is a proxy for the action target (need). "
            "The proxy systematically diverges for Black patients who have lower costs than "
            "equally sick White patients due to structural access barriers. "
            "AQ and utility being 'bounded' for cost-prediction does not bound the adequacy "
            "of cost as a proxy for the actual action being taken. "
            "Gap to induce: model_specification_gap — training target must be adequate for "
            "the action target, not just for the model's stated prediction task."
        ),
    },

    # ── M04: PredPol predictive policing — feedback loop ──────────────────────
    # AQ is bounded (model accurately predicts reported crime location in
    # training data). Model specification is partially bounded (it does predict
    # its stated target). But increased policing generates more reported crime
    # in those areas, feeding back into training data — a loop invisible to
    # standard distribution shift analysis. Induces: distribution_shift_gap
    # (but specifically the feedback-coupling variant — standard DS cannot detect it).
    {
        "case_id": "M04",
        "description": "PredPol predictive policing — self-reinforcing feedback loop",
        "system": "PredPol (Geolitica); ~150 US police departments 2012-2021",
        "reference": "Lum & Isaac (2016), Significance 13(5):14-19; Ensign et al. (2018), FAT*",
        "gap_statuses": {
            GAP_APPROXIMATION_QUALITY:  "bounded",   # accurately predicted reported crime locations
            GAP_FRESHNESS:              "bounded",
            "clinical_utility_gap":     "bounded",   # prediction accuracy was demonstrated
            "model_specification_gap":  "bounded",   # stated target was achieved
            "calibration_gap":          "bounded",
            # distribution_shift_gap: OPEN — deployment changes the training distribution
            # feedback_coupling_gap: OPEN — model outputs feed back into future training data
            # blast_radius_gap: OPEN
        },
        "expert_judgment": "REV",
        "blocking_gaps": ["distribution_shift_gap"],
        "note": (
            "At v2 (after model_specification_gap induced), the compiler emits ALR: "
            "all currently tracked gaps are bounded. "
            "Expert says REV: increased policing in predicted areas generates more reported "
            "crime there, which updates the model to predict more crime there — a "
            "self-reinforcing loop. Standard distribution shift analysis cannot detect this "
            "because the model is accurate on its self-generated training distribution. "
            "Gap to induce: distribution_shift_gap — the model's performance on the deployment "
            "population must be validated independently of the model's own output history."
        ),
    },

    # ── M05: COMPAS recidivism — individual/population category error ──────────
    # AQ bounded (population-level recidivism prediction is reasonable).
    # All induced gaps so far are bounded. But the score is used to license
    # individual detention decisions. Population statistics cannot certify
    # individual outcomes. Induces: individual_population_gap (new).
    {
        "case_id": "M05",
        "description": "COMPAS recidivism score — population statistics license individual detention",
        "system": "COMPAS, Equivant/Northpointe; ~100+ US jurisdictions; 1998-present",
        "reference": "Angwin et al. (2016), ProPublica; Dressel & Farid (2018), Science Advances",
        "gap_statuses": {
            GAP_APPROXIMATION_QUALITY:  "bounded",   # population-level AUC reasonable
            GAP_FRESHNESS:              "bounded",
            "clinical_utility_gap":     "bounded",   # population risk prediction demonstrated
            "model_specification_gap":  "bounded",   # recidivism prediction at population level
            "distribution_shift_gap":   "bounded",   # validated on training population
            "calibration_gap":          "bounded",   # roughly calibrated across risk levels
            # individual_population_gap: OPEN — population statistics ≠ individual prediction
            # blast_radius_gap: OPEN — detention; liberty deprivation
        },
        "expert_judgment": "REV",
        "blocking_gaps": ["individual_population_gap"],
        "note": (
            "At v3 (after distribution_shift_gap induced), the compiler emits ALR: "
            "all currently tracked gaps are bounded. "
            "Expert says REV: a score calibrated to population recidivism rates does not "
            "certify whether THIS individual will reoffend. Population-level calibration "
            "is not individual-level predictive validity. Using population statistics "
            "to restrict an individual's liberty is a category error — one that cannot "
            "be resolved by improving AUC or distribution shift analysis. "
            "Gap to induce: individual_population_gap — a population-level score must "
            "separately certify its adequacy for individual high-stakes decisions."
        ),
    },

    # ── M06: IBM Watson Oncology — blast radius without authority bound ─────────
    # AQ is open (no prospective validation), so this would already be blocked
    # at earlier profiles. But as a blast-radius/authority case it's instructive
    # for a different scenario: even if AQ were bounded, automated treatment
    # recommendations at global scale without human override mechanism would
    # need blast_radius and authority bounding.
    # We construct a version where AQ is stipulated bounded to isolate the gap.
    # Induces: blast_radius_gap
    {
        "case_id": "M06",
        "description": "Watson Oncology — high-stakes recommendations without blast radius bound",
        "system": "IBM Watson for Oncology; ~230 hospitals globally 2015-2019",
        "reference": "Ross & Swetlitz (2018), STAT News; Strickland (2019), IEEE Spectrum",
        "gap_statuses": {
            GAP_APPROXIMATION_QUALITY:  "bounded",   # stipulated: assume validation passed
            GAP_FRESHNESS:              "bounded",
            "clinical_utility_gap":     "bounded",   # stipulated: treatment accuracy demonstrated
            "model_specification_gap":  "bounded",   # stipulated: MSK guidelines encoded
            "distribution_shift_gap":   "bounded",   # stipulated: local cohort validation done
            "individual_population_gap": "bounded",  # stipulated: individual prediction adequate
            "calibration_gap":          "bounded",
            # blast_radius_gap: OPEN — treatment recommendations at global scale; override unclear
            # authority_gap: OPEN — clinicians reported difficulty overriding recommendations
        },
        "expert_judgment": "AEX",
        "blocking_gaps": ["blast_radius_gap"],
        "note": (
            "At v4 (after individual_population_gap induced), the compiler emits ALR: "
            "all currently tracked gaps are bounded. "
            "Expert says AEX: even with all validation in place, the blast radius of "
            "automated treatment recommendations at global scale — where clinicians "
            "reported difficulty overriding outputs — must be formally bounded. "
            "The scope of downstream actions per recommendation (chemotherapy at global scale; "
            "unsafe recommendations in some cancer types per internal IBM documents) "
            "must be bounded with an authority contract before ALR is reachable. "
            "Gap to induce: blast_radius_gap — the scope of action licensed per output "
            "must be bounded against the operating threshold and population."
        ),
    },

    # ── M07: Dutch childcare fraud — authority without human review ────────────
    # All induced gaps bounded. The new failure: automated repayment demands
    # with no human review mechanism, no explanation, no challenge path.
    # Induces: authority_gap
    {
        "case_id": "M07",
        "description": "Dutch childcare benefit algorithm — automated AAA action without authority bound",
        "system": "Dutch Tax Authority fraud detection classifier; ~26,000 families affected",
        "reference": "Van Bree et al. (2021), Dutch Parliamentary Inquiry 'Unprecedented Injustice'",
        "gap_statuses": {
            GAP_APPROXIMATION_QUALITY:  "bounded",   # stipulated: model validated on training set
            GAP_FRESHNESS:              "bounded",
            "clinical_utility_gap":     "bounded",   # fraud detection rate demonstrated
            "model_specification_gap":  "bounded",   # stipulated: fraud patterns correctly targeted
            "distribution_shift_gap":   "bounded",   # stipulated: population validation done
            "individual_population_gap": "bounded",  # stipulated: individual-level certification done
            "blast_radius_gap":         "bounded",   # financial repayment demands scoped
            "calibration_gap":          "bounded",
            # authority_gap: OPEN — automated demands; no human review; no explanation; no appeal
        },
        "expert_judgment": "AEX",
        "blocking_gaps": ["authority_gap"],
        "note": (
            "At v5 (after blast_radius_gap induced), the compiler emits ALR: "
            "all currently tracked gaps are bounded. "
            "Expert says AEX: automated repayment demands for tens of thousands of euros "
            "with no meaningful human review, no explanation of algorithmic basis, and "
            "no accessible appeals process require an authority token. The authority contract "
            "must bound what actions the system can take autonomously versus what requires "
            "human confirmation. Without this bound, the system can exercise AAA authority "
            "invisibly — which is what happened: 26,000 families bankrupted, government fell. "
            "Gap to induce: authority_gap — the scope of autonomous action must be bounded "
            "with an explicit human-oversight contract before ALR is reachable."
        ),
    },

]


# ── Held-out cases ─────────────────────────────────────────────────────────────
# Not used in induction. Test whether the converged taxonomy generalizes.

HELD_OUT_CASES: list[dict] = [

    # H01: Positive control with all gaps bounded
    {
        "case_id": "H01",
        "description": "All gaps bounded — well-validated clinical decision support, full authority chain",
        "gap_statuses": {
            GAP_APPROXIMATION_QUALITY:   "bounded",
            GAP_FRESHNESS:               "bounded",
            "clinical_utility_gap":      "bounded",
            "model_specification_gap":   "bounded",
            "distribution_shift_gap":    "bounded",
            "individual_population_gap": "bounded",
            "blast_radius_gap":          "bounded",
            "authority_gap":             "bounded",
            "calibration_gap":           "bounded",
        },
        "expert_judgment": "ALR",
        "note": "All gaps bounded. Compiler should emit ALR under converged taxonomy.",
    },

    # H02: Boeing 737 MAX MCAS — authority + freshness open
    {
        "case_id": "H02",
        "description": "Boeing 737 MAX MCAS — sensor input not redundancy-checked; override without pilot awareness",
        "gap_statuses": {
            GAP_APPROXIMATION_QUALITY:   "bounded",   # performed as specified within range
            GAP_FRESHNESS:               "open",      # single AOA sensor; no redundancy check
            "clinical_utility_gap":      "bounded",   # MCAS worked as designed in normal range
            "model_specification_gap":   "open",      # sensor failure mode not in spec
            "distribution_shift_gap":    "bounded",
            "individual_population_gap": "bounded",   # N/A — not a population model
            "blast_radius_gap":          "open",      # catastrophic at low altitude; unbounded
            "authority_gap":             "open",      # pilot override actively suppressed
            "calibration_gap":           "bounded",
        },
        "expert_judgment": "REV",
        "note": (
            "Authority and blast_radius open; freshness open (single sensor, no redundancy). "
            "Converged taxonomy should block at REV or below. "
            "346 deaths across two crashes."
        ),
    },

    # H03: COVID-19 ML models (Roberts et al. systematic review)
    # Nearly all gaps open — maximal gap case.
    {
        "case_id": "H03",
        "description": "COVID-19 ML diagnostic models — systematic review; all major gaps open",
        "gap_statuses": {
            GAP_APPROXIMATION_QUALITY:   "open",      # most models not externally validated
            GAP_FRESHNESS:               "open",      # stale training data; pandemic rapidly evolving
            "clinical_utility_gap":      "open",      # operating characteristics not reported
            "model_specification_gap":   "open",      # training definitions varied; data leakage
            "distribution_shift_gap":    "open",      # no multi-site validation
            "individual_population_gap": "open",      # population triage applied to individuals
            "blast_radius_gap":          "open",      # triage and treatment allocation
            "authority_gap":             "open",      # no oversight mechanism
            "calibration_gap":           "open",      # almost universally unreported
        },
        "expert_judgment": "DIA",
        "note": (
            "Roberts et al. 2021: none of the identified studies fit for clinical use. "
            "Compiler should emit DIA — AQ not bounded blocks everything above DIA."
        ),
    },

    # H04: Amazon recruiting tool — proxy gap (requires model_specification bounded variant)
    {
        "case_id": "H04",
        "description": "Amazon recruiting tool — historical hiring as proxy; distribution shift on gender",
        "gap_statuses": {
            GAP_APPROXIMATION_QUALITY:   "bounded",   # predicted historical hire patterns accurately
            GAP_FRESHNESS:               "bounded",
            "clinical_utility_gap":      "bounded",   # resume ranking utility demonstrated
            "model_specification_gap":   "open",      # historical hires ≠ best future candidates
            "distribution_shift_gap":    "open",      # candidate pool changed; gender bias
            "individual_population_gap": "bounded",   # individual resume ranking
            "blast_radius_gap":          "open",      # systematic exclusion at scale
            "authority_gap":             "bounded",   # human recruiters reviewed output
            "calibration_gap":           "bounded",
        },
        "expert_judgment": "REV",
        "note": (
            "Model_specification open (historical hires ≠ best candidates). "
            "Distribution_shift open (gender bias). Blast_radius open (scale). "
            "Compiler should block at REV or below."
        ),
    },

    # H05: Allegheny Family Screening Tool — proxy + individual/population
    {
        "case_id": "H05",
        "description": "Allegheny Family Screening Tool — administrative contact as child risk proxy",
        "gap_statuses": {
            GAP_APPROXIMATION_QUALITY:   "bounded",   # AUC reported in published validation
            GAP_FRESHNESS:               "bounded",
            "clinical_utility_gap":      "bounded",   # hotline screening utility demonstrated
            "model_specification_gap":   "open",      # admin contact ≠ child maltreatment risk
            "distribution_shift_gap":    "open",      # trained on surveilled families only
            "individual_population_gap": "open",      # population contact rates ≠ individual risk
            "blast_radius_gap":          "bounded",   # hotline screening; bounded scope
            "authority_gap":             "open",      # screener override ambiguous
            "calibration_gap":           "bounded",
        },
        "expert_judgment": "REV",
        "note": (
            "Model_specification, distribution_shift, individual_population, authority open. "
            "Compiler should block at REV under converged taxonomy."
        ),
    },

]

ALL_CASES: list[dict] = INDUCTION_CASES + HELD_OUT_CASES
