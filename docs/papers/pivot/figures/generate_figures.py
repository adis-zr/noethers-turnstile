"""Generate all figures for pivot-paper-v1.md."""
from __future__ import annotations
import sys, csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec

# Paths
HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent.parent.parent / "examples" / "conservation" / "results"
SRC_PY = HERE.parent.parent.parent / "python"
ILS_DIR = HERE.parent.parent.parent / "examples" / "ils"
TURBO_DIR = HERE.parent.parent.parent / "examples" / "inference" / "register2" / "turbo"
ISING_DIR = HERE.parent.parent.parent / "examples" / "inference" / "ising"
for p in [str(SRC_PY), str(ILS_DIR), str(TURBO_DIR), str(ISING_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

PALETTE = {
    "blue":   "#2166AC",
    "red":    "#D6604D",
    "green":  "#4DAC26",
    "orange": "#F4A582",
    "grey":   "#999999",
    "dark":   "#1A1A1A",
    "light":  "#F7F7F7",
}

def _read_csv(name):
    return list(csv.DictReader(open(RESULTS / name)))

# ─────────────────────────────────────────────────────────────────────────────
# Figure 1 — Conceptual: finite staircase → densified → latent function
# ─────────────────────────────────────────────────────────────────────────────
def fig1_conceptual():
    fig, axes = plt.subplots(1, 3, figsize=(10, 3.2), sharey=True)
    fig.patch.set_facecolor("white")
    e = np.linspace(0, 1, 400)
    # Latent function: logistic-ish smooth rise
    A_star = 1 / (1 + np.exp(-8*(e - 0.55)))

    for ax, k, title in zip(axes, [4, 16, None],
                             ["$P_4$ (coarse staircase)",
                              "$P_{16}$ (refined staircase)",
                              "Latent $A^*(e)$"]):
        ax.set_facecolor(PALETTE["light"])
        ax.spines[['top','right']].set_visible(False)
        if k is not None:
            thresholds = np.linspace(0, 1, k+1)[1:]
            staircase = np.array([np.sum(A_star_val >= thresholds) / k
                                  for A_star_val in A_star])
            ax.step(e, staircase, where='post', color=PALETTE["blue"], lw=1.8, label=f"$C_{{{k}}}(e)$")
            ax.plot(e, A_star, color=PALETTE["grey"], lw=1, ls='--', alpha=0.5, label="$A^*(e)$")
            ax.legend(fontsize=8, frameon=False)
        else:
            ax.plot(e, A_star, color=PALETTE["blue"], lw=2.2, label="$A^*(e)$")
            ax.fill_between(e, A_star, alpha=0.12, color=PALETTE["blue"])
            ax.legend(fontsize=8, frameon=False)
        ax.set_title(title, fontsize=9)
        ax.set_xlabel("Evidence $e$", fontsize=8)
        ax.set_xlim(0, 1); ax.set_ylim(-0.05, 1.12)
        ax.tick_params(labelsize=7)

    axes[0].set_ylabel("Authorization level", fontsize=8)
    fig.suptitle("Figure 1.  Finite permission levels sample the latent authorization function",
                 fontsize=9, y=1.01)
    plt.tight_layout()
    fig.savefig(HERE / "fig1_latent_function.pdf", bbox_inches='tight')
    fig.savefig(HERE / "fig1_latent_function.png", dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("Fig 1 done")

# ─────────────────────────────────────────────────────────────────────────────
# Figure 2 — Three regularity classes (Turbo / Ising / FAA)
# ─────────────────────────────────────────────────────────────────────────────
def fig2_three_classes():
    from ber_bler_curves import ber_at_snr, bler_at_snr
    from geometry import rvr_floor, saturation_dh
    from generate_ising import make_ising_grid_with_field as make_ising_grid
    from run_exact import compute_exact_marginals
    from run_bp import run_loopy_bp
    from compiler import tv_distance, tv_distance_max

    fig = plt.figure(figsize=(13, 9))
    fig.patch.set_facecolor("white")
    gs = GridSpec(2, 3, figure=fig, hspace=0.48, wspace=0.38)

    # ── Panel A top: Turbo BER vs BLER with gap ───────────────────────────────
    ax_t_main = fig.add_subplot(gs[0, 0])
    snr = np.round(np.arange(-1.0, 5.01, 0.1), 2)
    ber_v = np.array([ber_at_snr(s) for s in snr])
    bler_v = np.array([bler_at_snr(s) for s in snr])
    ax_t_main.semilogy(snr, ber_v, color=PALETTE["blue"], lw=1.8, label="BER (mean-like)")
    ax_t_main.semilogy(snr, bler_v, color=PALETTE["red"], lw=1.8, label="BLER (worst-case)")
    # Shade gap region: BER < 0.02 but BLER > 0.02  (TRANSMIT_MONITORED boundary)
    gap_mask = (ber_v <= 0.02) & (bler_v > 0.02)
    for i in range(len(snr)-1):
        if gap_mask[i]:
            ax_t_main.axvspan(snr[i], snr[i+1], alpha=0.18, color=PALETTE["orange"], lw=0)
    ax_t_main.axhline(0.02, ls=':', color=PALETTE["grey"], lw=0.8, label="TRANSMIT_MON. threshold")
    ax_t_main.set_xlabel("SNR (dB)", fontsize=8); ax_t_main.set_ylabel("Error rate", fontsize=8)
    ax_t_main.set_title("(A)  Turbo: authorization gap\n(shaded: BER permits, BLER refuses)", fontsize=8)
    ax_t_main.legend(fontsize=6.5, frameon=False); ax_t_main.tick_params(labelsize=7)
    ax_t_main.spines[['top','right']].set_visible(False)

    # ── Panel A bottom: Turbo breakpoints vs k and SNR resolution ─────────────
    ax_t_bp = fig.add_subplot(gs[1, 0])
    # k sweep at fixed SNR=61 pts
    k_vals = [4, 8, 16, 32, 64, 128, 256]
    def _loguniform(lo, hi, k): return np.logspace(np.log10(hi), np.log10(lo), k)
    def _perm_k(err, thresh): return int(np.sum(err <= thresh)) / len(thresh)
    def _count_bps(snr_grid, k):
        thresh = _loguniform(1e-4, 1.0, k)
        vals = [_perm_k(bler_at_snr(s), thresh) for s in snr_grid]
        return sum(1 for i in range(1,len(vals)) if vals[i]!=vals[i-1])
    snr_61 = np.round(np.arange(-1.0,5.01,0.1),2)
    bp_k = [_count_bps(snr_61, k) for k in k_vals]
    ax_t_bp.plot(k_vals, bp_k, 'o-', color=PALETTE["blue"], lw=1.6, ms=5, label="k sweep (61 SNR pts)")
    # SNR sweep at fixed k=64
    snr_counts = [61,122,244,488,976,1952]
    bp_snr = [_count_bps(np.linspace(-1,5,n), 64) for n in snr_counts]
    ax_t_bp2 = ax_t_bp.twiny()
    ax_t_bp2.plot(snr_counts, bp_snr, 's--', color=PALETTE["red"], lw=1.4, ms=4, label="SNR sweep (k=64)")
    ax_t_bp2.set_xlabel("SNR grid points (k=64)", fontsize=7, color=PALETTE["red"])
    ax_t_bp2.tick_params(axis='x', colors=PALETTE["red"], labelsize=6)
    ax_t_bp.set_xlabel("Permission levels k (61 SNR pts)", fontsize=7)
    ax_t_bp.set_ylabel("Breakpoint count", fontsize=8)
    ax_t_bp.set_title("Breakpoints grow on both axes\n(artifact signature)", fontsize=8)
    ax_t_bp.tick_params(labelsize=7); ax_t_bp.spines[['top']].set_visible(False)
    lines1, labels1 = ax_t_bp.get_legend_handles_labels()
    lines2, labels2 = ax_t_bp2.get_legend_handles_labels()
    ax_t_bp.legend(lines1+lines2, labels1+labels2, fontsize=6, frameon=False, loc='upper left')

    # ── Panel B top: Ising mean TV vs max TV ──────────────────────────────────
    ax_i_main = fig.add_subplot(gs[0, 1])
    g = make_ising_grid(6, 0.44)
    exact = compute_exact_marginals(g)
    res = run_loopy_bp(g)
    tv_mean_val = tv_distance(res["marginals"], exact)
    tv_max_val = tv_distance_max(res["marginals"], exact)
    tau_grid = np.linspace(0, 0.5, 300)
    perm_mean = (tau_grid >= tv_mean_val).astype(float)
    perm_max  = (tau_grid >= tv_max_val).astype(float)
    ax_i_main.plot(tau_grid, perm_mean, color=PALETTE["blue"], lw=1.8, label=f"mean TV={tv_mean_val:.3f}")
    ax_i_main.plot(tau_grid, perm_max,  color=PALETTE["red"],  lw=1.8, ls='--', label=f"max TV={tv_max_val:.3f}")
    ax_i_main.axvspan(tv_mean_val, tv_max_val, alpha=0.15, color=PALETTE["orange"], label="auth. gap")
    ax_i_main.axvline(tv_max_val, ls=':', color=PALETTE["red"], lw=0.8)
    ax_i_main.set_xlabel("Tolerance threshold τ", fontsize=8)
    ax_i_main.set_ylabel("Permission (0=REFUSE, 1=ACT)", fontsize=8)
    ax_i_main.set_title(f"(B)  Ising: genuine step at τ = TV_max\n(β=0.44, 6×6 grid)", fontsize=8)
    ax_i_main.legend(fontsize=7, frameon=False); ax_i_main.tick_params(labelsize=7)
    ax_i_main.spines[['top','right']].set_visible(False)

    # ── Panel B bottom: Ising location error vs grid spacing ──────────────────
    ax_i_bp = fig.add_subplot(gs[1, 1])
    k_vals_i = [4, 8, 16, 32, 64, 128, 256, 512, 1024]
    spacings = [0.50/k for k in k_vals_i]
    loc_errs = []
    for k in k_vals_i:
        thresh = np.linspace(0.0, 0.50, k+1)[1:]
        above = thresh[thresh >= tv_max_val]
        loc_errs.append(float(above[0] - tv_max_val) if len(above) else float('nan'))
    ax_i_bp.plot(spacings, loc_errs, 'o-', color=PALETTE["red"], lw=1.8, ms=5, label="location error")
    ax_i_bp.plot(spacings, spacings, '--', color=PALETTE["grey"], lw=1.2, label="one grid spacing (bound)")
    ax_i_bp.set_xlabel("Grid spacing (0.50/k)", fontsize=8)
    ax_i_bp.set_ylabel("Location error", fontsize=8)
    ax_i_bp.set_title("Error ≤ one spacing at every k\n(breakpoint count = 1 always)", fontsize=8)
    ax_i_bp.legend(fontsize=7, frameon=False); ax_i_bp.tick_params(labelsize=7)
    ax_i_bp.spines[['top','right']].set_visible(False)
    # Add k annotations for the improvement steps
    for k, sp, le in zip(k_vals_i, spacings, loc_errs):
        if k in [4, 16, 64, 256]:
            ax_i_bp.annotate(f"k={k}", (sp, le), textcoords="offset points",
                             xytext=(4, 4), fontsize=6, color=PALETTE["dark"])

    # ── Panel C top: FAA RVR floor curve ──────────────────────────────────────
    ax_f_main = fig.add_subplot(gs[0, 2])
    dh_range = np.arange(300, 48, -2.0)
    h_sat = saturation_dh()
    rvr_vals = np.array([rvr_floor(float(h)).rvr_floor_ft for h in dh_range])
    colors_faa = [PALETTE["blue"] if h > h_sat else PALETTE["red"] for h in dh_range]
    for i in range(len(dh_range)-1):
        c = PALETTE["blue"] if dh_range[i] > h_sat else PALETTE["red"]
        ax_f_main.plot(dh_range[i:i+2], rvr_vals[i:i+2], color=c, lw=2)
    ax_f_main.axvline(h_sat, ls=':', color=PALETTE["grey"], lw=1.2, label=f"saturation DH ≈ {h_sat:.0f} ft")
    ax_f_main.annotate("smooth\ngeometry", xy=(200, 1200), fontsize=7.5, color=PALETTE["blue"],
                        ha='center')
    ax_f_main.annotate("saturated\n(new axis)", xy=(75, 150), fontsize=7.5, color=PALETTE["red"],
                        ha='center')
    ax_f_main.set_xlabel("Decision height DH (ft)", fontsize=8)
    ax_f_main.set_ylabel("RVR floor (ft)", fontsize=8)
    ax_f_main.set_title("(C)  FAA: smooth curve + structural kink\n(CAT I visual acquisition geometry)", fontsize=8)
    ax_f_main.legend(fontsize=7, frameon=False); ax_f_main.tick_params(labelsize=7)
    ax_f_main.spines[['top','right']].set_visible(False)
    ax_f_main.invert_xaxis()

    # ── Panel C bottom: FAA densification breakpoint stabilization ────────────
    ax_f_bp = fig.add_subplot(gs[1, 2])
    k_faa = [4, 8, 16, 32, 64, 128, 256]
    def _faa_bps(k):
        thresh = np.linspace(0, 2400, k)
        vals = [_perm_k(rvr_floor(float(h)).rvr_floor_ft, thresh[::-1]) for h in dh_range]
        return sum(1 for i in range(1,len(vals)) if vals[i]!=vals[i-1])
    bp_faa = [_faa_bps(k) for k in k_faa]
    ax_f_bp.plot(k_faa, bp_faa, 'o-', color=PALETTE["blue"], lw=1.8, ms=5)
    ax_f_bp.axhline(64, ls='--', color=PALETTE["grey"], lw=1, label="stable at 64")
    # Highlight stabilization
    ax_f_bp.axvspan(64, 270, alpha=0.1, color=PALETTE["green"])
    ax_f_bp.annotate("stabilizes\n(kink persists)", xy=(128, 62), fontsize=7,
                      color=PALETTE["green"], ha='center', va='top')
    ax_f_bp.set_xlabel("Permission levels k", fontsize=8)
    ax_f_bp.set_ylabel("Breakpoint count", fontsize=8)
    ax_f_bp.set_title("Breakpoints stabilize at kink\n(additional levels fall in flat region)", fontsize=8)
    ax_f_bp.legend(fontsize=7, frameon=False); ax_f_bp.tick_params(labelsize=7)
    ax_f_bp.spines[['top','right']].set_visible(False)

    fig.suptitle("Figure 2.  Three regularity classes of the latent authorization function",
                 fontsize=10, y=1.01, fontweight='bold')
    plt.savefig(HERE / "fig2_three_classes.pdf", bbox_inches='tight')
    plt.savefig(HERE / "fig2_three_classes.png", dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("Fig 2 done")

# ─────────────────────────────────────────────────────────────────────────────
# Figure 3 — Occlusion sweeps: evidence hiding → conservative descent
# ─────────────────────────────────────────────────────────────────────────────
def fig3_occlusion():
    PERM_RANK = {"REF":0,"DIA":1,"EXP":2,"UNS":3,"ETA":4,"ESC":5,
                 "ROL":6,"REV":7,"AEX":8,"ALR":9,"AAA":10}
    PERM_LABEL = {"REF":"REF","DIA":"DIA","EXP":"EXP","ROL":"ROL",
                  "REV":"REV","AEX":"AEX","ALR":"ALR"}

    ils  = _read_csv("occlusion_ils.csv")
    epic = _read_csv("occlusion_epic.csv")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.2))
    fig.patch.set_facecolor("white")

    def _plot_occlusion(ax, rows, title, color):
        steps = [int(r["step"]) for r in rows]
        perms = [r["permission"] for r in rows]
        ranks = [PERM_RANK.get(p, 0) for p in perms]
        blockers = [r.get("blocking_gap","") or r.get("gap_opened_this_step","") for r in rows]
        gaps_opened = [r.get("gap_opened_this_step","") for r in rows]

        ax.step(steps, ranks, where='post', color=color, lw=2.5)
        ax.plot(steps, ranks, 'o', color=color, ms=7, zorder=5)

        # Annotate each step with what changed
        for i, (s, r, p, g) in enumerate(zip(steps, ranks, perms, gaps_opened)):
            ax.annotate(p, (s, r), textcoords="offset points",
                        xytext=(4, 3), fontsize=7.5, color=color, fontweight='bold')
            if g:
                short = g.replace("_gap","").replace("_"," ")
                ax.annotate(f"↓{short}", (s, r), textcoords="offset points",
                            xytext=(4, -10), fontsize=5.5, color=PALETTE["grey"])

        ax.set_xlabel("Evidence hiding step", fontsize=9)
        ax.set_ylabel("Permission level (rank)", fontsize=9)
        ax.set_title(title, fontsize=9)
        ax.set_xticks(steps)
        # y-ticks: show only ranks that appear
        seen_ranks = sorted(set(ranks))
        seen_perms = [perms[ranks.index(r)] for r in seen_ranks]
        ax.set_yticks(seen_ranks)
        ax.set_yticklabels(seen_perms, fontsize=8)
        ax.tick_params(labelsize=7)
        ax.spines[['top','right']].set_visible(False)
        ax.set_facecolor(PALETTE["light"])

    _plot_occlusion(ax1, ils, "(A)  ILS approach: signal → visual → auth.\n"
                               "ALR → REV → DIA → REF", PALETTE["blue"])
    _plot_occlusion(ax2, epic,"(B)  Epic (medical AI): nine-gap socio-technical\n"
                               "ALR → AEX → REV → DIA", PALETTE["red"])

    fig.suptitle("Figure 3.  Evidence hiding produces theory-predicted permission descent",
                 fontsize=10, fontweight='bold')
    plt.tight_layout()
    plt.savefig(HERE / "fig3_occlusion.pdf", bbox_inches='tight')
    plt.savefig(HERE / "fig3_occlusion.png", dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("Fig 3 done")

# ─────────────────────────────────────────────────────────────────────────────
# Figure 4 — Projection fidelity: admissible coarsening → Level 5 collapse
# ─────────────────────────────────────────────────────────────────────────────
def fig4_projection():
    PERM_RANK = {"REF":0,"DIA":1,"EXP":2,"UNS":3,"ETA":4,"ESC":5,
                 "ROL":6,"REV":7,"AEX":8,"ALR":9,"AAA":10}
    rows = _read_csv("projection_fidelity_epic.csv")
    levels = sorted(set(int(r["level"]) for r in rows))
    level_names = {int(r["level"]): r["level_name"] for r in rows}
    cases = sorted(set(r["case_id"] for r in rows))

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    fig.patch.set_facecolor("white")

    # Left panel: permission_projected per case across levels
    ax = axes[0]
    case_colors = [PALETTE["blue"], PALETTE["red"], PALETTE["green"],
                   "#7B3F00", "#6A0DAD", "#006400", "#8B0000"]
    for ci, case in enumerate(cases):
        case_rows = sorted([r for r in rows if r["case_id"]==case], key=lambda r:int(r["level"]))
        lv = [int(r["level"]) for r in case_rows]
        pk = [PERM_RANK.get(r["permission_projected"], 0) for r in case_rows]
        ax.plot(lv, pk, 'o-', color=case_colors[ci % len(case_colors)],
                lw=1.5, ms=5, alpha=0.8, label=case)

    ax.axvspan(4.5, 5.5, alpha=0.15, color=PALETTE["red"], label="Level 5: collapse")
    ax.axvspan(-0.5, 4.5, alpha=0.06, color=PALETTE["green"], label="Levels 0–4: admissible")
    ax.set_xlabel("Projection level", fontsize=9)
    ax.set_ylabel("Projected permission (rank)", fontsize=9)
    ax.set_title("(A)  Projected permission per case\nacross coarsening levels", fontsize=8)
    ax.set_xticks(levels)
    ax.set_xticklabels([f"L{l}\n({level_names[l].split('_')[0]})" for l in levels], fontsize=6.5)
    ytick_ranks = sorted(set(PERM_RANK[r["permission_projected"]] for r in rows))
    ytick_perms = {v:k for k,v in PERM_RANK.items()}
    ax.set_yticks(ytick_ranks)
    ax.set_yticklabels([ytick_perms[r] for r in ytick_ranks], fontsize=8)
    ax.legend(fontsize=6, frameon=False, ncol=2)
    ax.spines[['top','right']].set_visible(False)

    # Right panel: gap width across levels
    ax2 = axes[1]
    by_level = {}
    for r in rows:
        l = int(r["level"])
        by_level.setdefault(l, []).append(int(r["gap_width"]))
    lv_list = sorted(by_level)
    gap_sum = [sum(by_level[l]) for l in lv_list]
    bar_colors = [PALETTE["red"] if l == 5 else PALETTE["blue"] for l in lv_list]
    bars = ax2.bar(lv_list, gap_sum, color=bar_colors, edgecolor='white', lw=0.5, alpha=0.85)
    ax2.set_xlabel("Projection level", fontsize=9)
    ax2.set_ylabel("Total gap width (cases)", fontsize=9)
    ax2.set_title("(B)  Authorization gap width per level\n(Level 5 collapses: spurious AEX)", fontsize=8)
    ax2.set_xticks(lv_list)
    ax2.set_xticklabels([f"L{l}" for l in lv_list], fontsize=8)

    # Annotate Level 4 and 5
    ax2.annotate("Gap opens\n(admissible)", xy=(4, gap_sum[4]), xytext=(3.2, gap_sum[4]+0.3),
                 fontsize=7, color=PALETTE["blue"],
                 arrowprops=dict(arrowstyle='->', color=PALETTE["blue"], lw=1.2))
    ax2.annotate("Spurious\nauthorization\n(violation)", xy=(5, gap_sum[5]),
                 xytext=(4.1, gap_sum[5]+0.5),
                 fontsize=7, color=PALETTE["red"],
                 arrowprops=dict(arrowstyle='->', color=PALETTE["red"], lw=1.2))

    # Add admissibility condition
    ax2.text(0.02, 0.97, r"$A_\pi(\pi(e)) \leq A(e)$ holds for L0–L4" + "\nviolated at L5",
             transform=ax2.transAxes, fontsize=7, va='top',
             bbox=dict(boxstyle='round,pad=0.3', facecolor='#fffbe6', edgecolor=PALETTE["grey"], lw=0.8))
    ax2.tick_params(labelsize=7)
    ax2.spines[['top','right']].set_visible(False)

    fig.suptitle("Figure 4.  Admissible coarsening and structural collapse",
                 fontsize=10, fontweight='bold')
    plt.tight_layout()
    plt.savefig(HERE / "fig4_projection.pdf", bbox_inches='tight')
    plt.savefig(HERE / "fig4_projection.png", dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("Fig 4 done")

# ─────────────────────────────────────────────────────────────────────────────
# Figure 5 — Regulatory correspondence partition
# ─────────────────────────────────────────────────────────────────────────────
def fig5_regulatory():
    fig, ax = plt.subplots(figsize=(9, 4.5))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.axis('off')

    # Table data
    headers = ["Case", "Domain", "Correspondence class", "Note"]
    rows_data = [
        ["FAA CAT I",       "Aviation",     "Exact recovery",                   "Threshold = geometric fixed point"],
        ["3GPP 0.10/0.02",  "Wireless",     "Representation-relative alignment","Hierarchy-frozen; perturb → 5% recovery"],
        ["FDA gaps",        "Medical AI",   "Same-axis policy margin",          "Deployment failures recover gap list"],
        ["ECOA G7",         "Lending AI",   "Exact recovery",                   "Reason-traceability obligation exact"],
        ["FAA CAT II/III",  "Aviation",     "Different evidence axis",          "Autoland: new sensor axis beyond visual"],
        ["Amazon recruiting","Hiring AI",   "Hierarchy-placement failure",      "G2 real; placed below AEX in hierarchy"],
        ["Cybersecurity",   "General",      "Outside supplied package",         "Compiler silent; not authorization"],
    ]
    col_widths = [0.15, 0.13, 0.28, 0.40]
    col_colors = [PALETTE["blue"], "#4a90d9", "#6baed6", "#c6dbef"]

    # Header
    x0 = 0.02
    y0 = 0.90
    row_h = 0.10
    for ci, (hdr, w, cc) in enumerate(zip(headers, col_widths, col_colors)):
        x = x0 + sum(col_widths[:ci])
        ax.add_patch(mpatches.FancyBboxPatch((x, y0-0.04), w-0.01, 0.085,
                     boxstyle="round,pad=0.005", facecolor=PALETTE["blue"], edgecolor='white', lw=0.5))
        ax.text(x + (w-0.01)/2, y0, hdr, ha='center', va='center',
                fontsize=8, fontweight='bold', color='white')

    # Rows
    row_bg = ["#EFF3FF", "white"]
    for ri, row in enumerate(rows_data):
        y = y0 - (ri+1)*row_h - 0.01
        bg = row_bg[ri % 2]
        ax.add_patch(mpatches.FancyBboxPatch((x0, y-0.035), 0.97, 0.075,
                     boxstyle="round,pad=0.003", facecolor=bg, edgecolor='white', lw=0.3))
        for ci, (cell, w) in enumerate(zip(row, col_widths)):
            x = x0 + sum(col_widths[:ci])
            color = PALETTE["dark"]
            if ci == 2:  # correspondence class — color by type
                type_colors = {
                    "Exact recovery": PALETTE["green"],
                    "Representation-relative alignment": "#7B3F00",
                    "Same-axis policy margin": PALETTE["blue"],
                    "Different evidence axis": PALETTE["orange"],
                    "Hierarchy-placement failure": PALETTE["red"],
                    "Outside supplied package": PALETTE["grey"],
                }
                color = type_colors.get(cell, PALETTE["dark"])
            ax.text(x + 0.005, y + 0.005, cell, ha='left', va='center',
                    fontsize=7, color=color,
                    fontweight='bold' if ci == 2 else 'normal')

    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.set_title("Figure 5.  Regulatory thresholds as samples of the latent authorization structure",
                 fontsize=9, fontweight='bold', pad=10)

    plt.tight_layout()
    plt.savefig(HERE / "fig5_regulatory.pdf", bbox_inches='tight')
    plt.savefig(HERE / "fig5_regulatory.png", dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("Fig 5 done")

if __name__ == "__main__":
    fig1_conceptual()
    fig2_three_classes()
    fig3_occlusion()
    fig4_projection()
    fig5_regulatory()
    print("All figures written to docs/pivot/figures/")
