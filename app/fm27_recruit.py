#!/usr/bin/env python
"""FM27 recruitment helper: export players from a save (via fmsave), then find
replacements / similar profiles.

  python fm27_recruit.py export [--save PATH]
  python fm27_recruit.py similar "Gabri Veiga" [filters]
  python fm27_recruit.py squad [--club "FC Porto"]
  python fm27_recruit.py search --pos MC --min-ca 120 [filters]

Requires: pip install fmsave pandas
"""
import argparse, glob, os, subprocess, sys, warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

SAVES = os.path.expanduser(r"~\Documents\Sports Interactive\Football Manager 27\games")
from paths import DATA
CACHE = os.path.join(DATA, "players.csv")

OUTFIELD = ["crossing", "dribbling", "finishing", "first_touch", "heading", "long_shots", "marking",
            "passing", "tackling", "technique", "corners", "free_kick_taking", "long_throws",
            "penalty_taking", "aggression", "anticipation", "bravery", "composure", "concentration",
            "decisions", "determination", "flair", "leadership", "off_the_ball", "positioning",
            "teamwork", "vision", "work_rate", "acceleration", "agility", "balance", "jumping_reach",
            "natural_fitness", "pace", "stamina", "strength"]
GK = ["handling", "aerial_reach", "command_of_area", "communication", "kicking", "throwing",
      "one_on_ones", "reflexes", "rushing_out", "punching", "anticipation", "decisions", "positioning",
      "concentration", "composure", "agility", "first_touch", "passing"]
POS = ["gk", "sw", "dl", "dc", "dr", "dm", "ml", "mc", "mr", "aml", "amc", "amr", "stc", "wbl", "wbr"]
# small-weight attributes that rarely decide a replacement
LOW_W = {"corners", "free_kick_taking", "long_throws", "penalty_taking", "natural_fitness"}


def latest_save():
    files = glob.glob(os.path.join(SAVES, "*.fm"))
    files = [f for f in files if "overwrite backup" not in f.lower()]
    if not files:
        sys.exit(f"No .fm saves in {SAVES}")
    return max(files, key=os.path.getmtime)


def export(save=None):
    save = save or latest_save()
    print(f"Exporting {os.path.basename(save)} ...")
    r = subprocess.run([sys.executable, "-m", "fmsave", "export", save, "players", "--all",
                        "--format", "csv", "-o", CACHE], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        err = r.stderr.strip().splitlines()
        sys.exit("Could not read the save: " + (err[-1] if err else "unknown error") +
                 " (If FM is saving or open, wait a moment and press Update again.)")
    df = pd.read_csv(CACHE, low_memory=False)
    print(f"{len(df):,} players -> {CACHE}")
    info = subprocess.run([sys.executable, "-m", "fmsave", "info", save], capture_output=True, text=True).stdout
    print(info.strip())


def load():
    if not os.path.exists(CACHE):
        export()
    df = pd.read_csv(CACHE, low_memory=False)
    df["club"] = df["club_short_name"].fillna(df["club_name"]).fillna("Free agent")
    df["value_m"] = (df["transfer_value"] / 1e6).round(1)
    df["wage_k"] = (df["contract_wage"] / 1e3).round(0)
    df["best_pos"] = df[[f"positions_{p}" for p in POS]].idxmax(axis=1).str.replace("positions_", "").str.upper()
    return df


def find(df, name):
    m = df[df["name"].str.lower() == name.lower()]
    if m.empty:
        m = df[df["name"].str.contains(name, case=False, na=False, regex=False)]
    if m.empty:
        sys.exit(f"No player matching '{name}'")
    if len(m) > 1:
        print("Multiple matches, using highest CA:\n",
              m.sort_values("ability_current", ascending=False)[["name", "age", "club", "ability_current"]].head(6).to_string(index=False))
    return m.sort_values("ability_current", ascending=False).iloc[0]


def apply_filters(df, a, pos_cols):
    if a.max_age is not None: df = df[df.age <= a.max_age]
    if a.min_age is not None: df = df[df.age >= a.min_age]
    if a.max_value is not None: df = df[df.value_m <= a.max_value]
    if a.max_wage is not None: df = df[df.wage_k <= a.max_wage]
    if a.min_ca is not None: df = df[df.ability_current >= a.min_ca]
    if a.min_pa is not None: df = df[df.ability_potential >= a.min_pa]
    if a.expiring_by:
        df = df[pd.to_datetime(df.contract_end, errors="coerce") <= pd.Timestamp(a.expiring_by)]
    if a.nation is not None: df = df[df.nation_id == a.nation]
    if a.exclude_club:
        df = df[~df.club.str.contains(a.exclude_club, case=False, na=False)]
    if a.free_only: df = df[df.club == "Free agent"]
    for c in pos_cols:  # must be able to play the position(s)
        df = df[df[c] >= a.min_pos]
    return df


def similar(a):
    df = load()
    t = find(df, a.player)
    is_gk = t["positions_gk"] >= 15
    attrs = GK if is_gk else OUTFIELD
    cols = [f"attributes_{x}" for x in attrs]
    tv = t[cols].astype(float).values
    # weights: emphasise what the target is good at, de-emphasise set pieces
    w = (tv / 20.0) ** 2 + 0.3
    for i, x in enumerate(attrs):
        if x in LOW_W: w[i] *= 0.3
    pos_cols = [f"positions_{p.lower()}" for p in (a.pos.split(",") if a.pos else [])]
    if not pos_cols:  # default: positions the target is genuinely good at (>=15), top 2
        top = sorted(POS, key=lambda p: -t[f"positions_{p}"])[:2]
        pos_cols = [f"positions_{p}" for p in top if t[f"positions_{p}"] >= 15]
    pool = df[(df.uid != t.uid) & (df.positions_gk >= 15 if is_gk else df.positions_gk < 15)]
    pool = apply_filters(pool, a, pos_cols)
    if pool.empty:
        sys.exit("No candidates after filters.")
    X = pool[cols].astype(float).values
    diff = X - tv
    # shortfalls vs the target hurt more than surpluses (we're replacing him)
    pen = np.where(diff < 0, 1.0, 0.35) * diff**2
    dist = np.sqrt((pen * w).sum(axis=1) / w.sum())
    pool = pool.assign(match=(100 * np.exp(-dist / 3.0)).round(1))
    # top shortfall attrs for transparency
    def gaps(i):
        d = diff[i]; idx = np.argsort(d)[:2]
        return ", ".join(f"{attrs[j]} {int(d[j]):+d}" for j in idx if d[j] < 0)
    pool = pool.assign(weakest_vs_target=[gaps(i) for i in range(len(pool))])
    print(f"\nTarget: {t['name']} ({int(t.age)}, {t.club}, {t.best_pos}) CA {int(t.ability_current)}/PA {int(t.ability_potential)} "
          f"| EUR {t.value_m}M | wage {t.wage_k}k | to {t.contract_end}")
    print(f"Pool: {len(pool):,} players | positions: {','.join(c.split('_')[1].upper() for c in pos_cols) or 'any'}\n")
    out = pool.sort_values("match", ascending=False).head(a.top)
    print(out[["name", "age", "club", "best_pos", "ability_current", "ability_potential", "value_m", "wage_k",
               "contract_end", "match", "weakest_vs_target"]].rename(columns={
        "ability_current": "CA", "ability_potential": "PA", "value_m": "val_M", "wage_k": "wage_k",
        "contract_end": "ends", "best_pos": "pos"}).to_string(index=False))


def squad(a):
    df = load()
    d = df[df.club.str.contains(a.club, case=False, na=False)]
    print(d.sort_values("ability_current", ascending=False)[["name", "age", "best_pos", "ability_current",
          "ability_potential", "value_m", "wage_k", "contract_end", "contract_squad_status"]].to_string(index=False))


def search(a):
    df = load()
    pos_cols = [f"positions_{p.lower()}" for p in a.pos.split(",")] if a.pos else []
    d = apply_filters(df, a, pos_cols)
    sort = a.sort
    print(d.sort_values(sort, ascending=False).head(a.top)[["name", "age", "club", "best_pos", "ability_current",
          "ability_potential", "value_m", "wage_k", "contract_end"]].to_string(index=False))


def add_filters(p):
    p.add_argument("--pos", help="position(s), comma separated: GK,DL,DC,DR,DM,ML,MC,MR,AML,AMC,AMR,STC,WBL,WBR")
    p.add_argument("--min-pos", type=int, default=15, help="min position rating 1-20 (default 15)")
    p.add_argument("--max-age", type=int); p.add_argument("--min-age", type=int)
    p.add_argument("--max-value", type=float, help="max transfer value, EUR millions")
    p.add_argument("--max-wage", type=float, help="max weekly wage, thousands")
    p.add_argument("--min-ca", type=int); p.add_argument("--min-pa", type=int)
    p.add_argument("--expiring-by", help="contract end on/before YYYY-MM-DD")
    p.add_argument("--nation", type=int, help="nation_id"); p.add_argument("--exclude-club")
    p.add_argument("--free-only", action="store_true"); p.add_argument("--top", type=int, default=25)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
    e = sp.add_parser("export"); e.add_argument("--save")
    s = sp.add_parser("similar"); s.add_argument("player"); add_filters(s)
    q = sp.add_parser("squad"); q.add_argument("--club", default="FC Porto")
    r = sp.add_parser("search"); add_filters(r); r.add_argument("--sort", default="ability_current")
    a = ap.parse_args()
    {"export": lambda: export(a.save), "similar": lambda: similar(a),
     "squad": lambda: squad(a), "search": lambda: search(a)}[a.cmd]()
