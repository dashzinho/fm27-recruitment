"""Moneyball mode: rank players on production (season stats) + stars, never on attributes.

Stats come from fmsave's `player-season-history --all` (league + cup + other, all seasons stored in the save).
Per position group we turn per-90 production into percentiles against peers with enough minutes, then
shrink toward average for small samples.
"""
import os, subprocess, sys
import numpy as np
import pandas as pd

from paths import APP, ROOT, DATA, OUT

# group -> list of (key, label, higher_is_better, weight, fmt)
METRICS = {
    "GK": [("save_pct", "Save %", True, 1.5, "{:.0f}%"), ("xg_prev90", "xG prevented /90", True, 2.0, "{:+.2f}"),
           ("ga90", "Goals conceded /90", False, 1.0, "{:.2f}"), ("rating", "Avg rating", True, 2.0, "{:.2f}")],
    "DEF": [("tkl90", "Tackles won /90", True, 1.0, "{:.1f}"), ("int90", "Interceptions /90", True, 1.0, "{:.1f}"),
            ("pw90", "Possession won /90", True, 1.0, "{:.1f}"), ("hdr90", "Headers won /90", True, 1.0, "{:.1f}"),
            ("clr90", "Clearances /90", True, 0.6, "{:.1f}"), ("prog90", "Progressive passes /90", True, 1.0, "{:.1f}"),
            ("pass_pct", "Pass completion", True, 0.8, "{:.0f}%"), ("rating", "Avg rating", True, 2.0, "{:.2f}")],
    "MID": [("prog90", "Progressive passes /90", True, 1.2, "{:.1f}"), ("kp90", "Key passes /90", True, 1.0, "{:.2f}"),
            ("xa90", "xA /90", True, 1.0, "{:.2f}"), ("pass_pct", "Pass completion", True, 0.8, "{:.0f}%"),
            ("tkl90", "Tackles won /90", True, 1.0, "{:.1f}"), ("int90", "Interceptions /90", True, 0.8, "{:.1f}"),
            ("pw90", "Possession won /90", True, 1.0, "{:.1f}"), ("drb90", "Dribbles /90", True, 0.6, "{:.1f}"),
            ("rating", "Avg rating", True, 2.0, "{:.2f}")],
    "ATT": [("npxg90", "npxG /90", True, 1.5, "{:.2f}"), ("xa90", "xA /90", True, 1.2, "{:.2f}"),
            ("g90", "Goals /90", True, 1.0, "{:.2f}"), ("a90", "Assists /90", True, 0.8, "{:.2f}"),
            ("kp90", "Key passes /90", True, 1.0, "{:.2f}"), ("drb90", "Dribbles /90", True, 0.8, "{:.1f}"),
            ("sot90", "Shots on target /90", True, 0.6, "{:.2f}"), ("rating", "Avg rating", True, 2.0, "{:.2f}")],
}
GROUP_BY_LABEL = {"GK": "GK", "LB": "DEF", "RB": "DEF", "CB": "DEF", "LWB": "DEF", "RWB": "DEF",
                  "DM": "MID", "CM": "MID", "LM": "MID", "RM": "MID",
                  "AM": "ATT", "LW": "ATT", "RW": "ATT", "ST": "ATT"}
POS_GROUP = {"gk": "GK", "dl": "DEF", "dc": "DEF", "dr": "DEF", "sw": "DEF", "wbl": "DEF", "wbr": "DEF",
             "dm": "MID", "mc": "MID", "ml": "MID", "mr": "MID", "aml": "ATT", "amc": "ATT", "amr": "ATT", "stc": "ATT"}

SUMS = ["minutes", "starts", "substitute_appearances", "goals", "assists", "expected_goals", "non_penalty_expected_goals",
        "expected_assists", "key_passes", "dribbles", "shots_on_target", "progressive_passes", "tackles_completed",
        "interceptions", "possession_won", "headers_won", "clearances", "passes_attempted", "passes_completed",
        "expected_goals_prevented", "goals_allowed", "saves_held", "saves_parried", "saves_tipped", "shots_on_target_faced",
        "clean_sheets"]


def export_history(save, refresh=True):
    out = os.path.join(DATA, "hist_all.csv")
    if not refresh and os.path.exists(out):
        return out
    r = subprocess.run([sys.executable, "-m", "fmsave", "export", save, "player-season-history", "--all",
                        "--format", "csv", "-o", out], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr[-800:])
    return out


def aggregate(path):
    """One row per player: totals over all stored seasons/competitions + derived per-90 stats."""
    d = pd.read_csv(path, low_memory=False)
    d = d[d.minutes > 0].copy()
    for c in SUMS:
        if c not in d: d[c] = 0
    d["_rw"] = d.average_rating.fillna(0) * d.minutes
    d["_rm"] = np.where(d.average_rating.notna(), d.minutes, 0)
    g = d.groupby("player_uid")[SUMS + ["_rw", "_rm"]].sum()
    m = g.minutes.clip(lower=1)
    n90 = m / 90.0
    out = pd.DataFrame({"minutes": g.minutes, "starts": g.starts})
    out["rating"] = np.where(g._rm > 0, g._rw / g._rm.clip(lower=1), np.nan)
    out["g90"] = g.goals / n90; out["a90"] = g.assists / n90
    out["npxg90"] = g.non_penalty_expected_goals / n90; out["xa90"] = g.expected_assists / n90
    out["kp90"] = g.key_passes / n90; out["drb90"] = g.dribbles / n90; out["sot90"] = g.shots_on_target / n90
    out["prog90"] = g.progressive_passes / n90; out["tkl90"] = g.tackles_completed / n90
    out["int90"] = g.interceptions / n90; out["pw90"] = g.possession_won / n90
    out["hdr90"] = g.headers_won / n90; out["clr90"] = g.clearances / n90
    out["pass_pct"] = np.where(g.passes_attempted > 0, 100 * g.passes_completed / g.passes_attempted.clip(lower=1), np.nan)
    saves = g.saves_held + g.saves_parried + g.saves_tipped
    out["save_pct"] = np.where(g.shots_on_target_faced > 0, 100 * saves / g.shots_on_target_faced.clip(lower=1), np.nan)
    out["xg_prev90"] = g.expected_goals_prevented / n90; out["ga90"] = g.goals_allowed / n90
    return out


def stars(v):
    """CA/PA (1-200) -> stars in half steps (CA/40). Approximation of the in-game star display."""
    return float(np.floor(np.clip(v, 0, 200) / 40 * 2 + 0.5) / 2)


def score_group(df_stats, players, group, min_minutes, shrink_k):
    """df_stats: aggregate table indexed by uid; players: df with uid + best group. Returns DataFrame
    indexed by uid with columns: prod (0-100 shrunk), pct_<metric>, qualified."""
    metrics = METRICS[group]
    peers_uids = players[players.group == group].uid
    s = df_stats[df_stats.index.isin(peers_uids)]
    ref = s[s.minutes >= min_minutes]
    res = pd.DataFrame(index=df_stats.index)
    wsum = np.zeros(len(res)); acc = np.zeros(len(res)); cnt = np.zeros(len(res))
    for key, label, hib, w, fmt in metrics:
        if key not in df_stats or ref[key].notna().sum() < 20:
            res["pct_" + key] = np.nan; continue
        vals = df_stats[key]
        pct = vals.apply(lambda v: np.nan if pd.isna(v) else 100.0 * ((ref[key] < v).mean() + 0.5 * (ref[key] == v).mean()))
        if not hib: pct = 100 - pct
        res["pct_" + key] = pct
        ok = pct.notna().values
        acc += np.where(ok, pct.fillna(0).values * w, 0); wsum += np.where(ok, w, 0)
    comp = np.where(wsum > 0, acc / np.maximum(wsum, 1e-9), np.nan)
    mins = df_stats.minutes.values
    res["prod"] = 50 + (comp - 50) * (mins / (mins + shrink_k))
    res["ref_n"] = len(ref)
    return res
