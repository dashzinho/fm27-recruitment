#!/usr/bin/env python
"""Builds the FM27 Recruitment Board (single self-contained HTML app) from a save.

  python fm27_report.py [--save PATH] [--no-export] [--open] [-o board.html]
"""
import argparse, json, os, subprocess, sys, warnings, datetime, webbrowser
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
import fm27_recruit as fr
import fm27_roles as roles_lib
import fm27_moneyball as mb

from paths import APP, ROOT, DATA, OUT

FORMATIONS = {
    "4-2-3-1": [
        ("GK", "GK", ["gk"], 50, 91), ("LB", "LB", ["dl", "wbl"], 13, 71), ("CB", "CB", ["dc"], 37, 75),
        ("CB", "CB", ["dc"], 63, 75), ("RB", "RB", ["dr", "wbr"], 87, 71), ("DM", "DM", ["dm", "mc"], 35, 53),
        ("DM", "DM", ["dm", "mc"], 65, 53), ("LW", "LW", ["aml", "ml"], 15, 31), ("AM", "AM", ["amc"], 50, 31),
        ("RW", "RW", ["amr", "mr"], 85, 31), ("ST", "ST", ["stc"], 50, 11)],
    "4-3-3": [
        ("GK", "GK", ["gk"], 50, 91), ("LB", "LB", ["dl", "wbl"], 13, 71), ("CB", "CB", ["dc"], 37, 75),
        ("CB", "CB", ["dc"], 63, 75), ("RB", "RB", ["dr", "wbr"], 87, 71), ("DM", "DM", ["dm", "mc"], 50, 55),
        ("CM", "CM", ["mc", "dm"], 28, 40), ("CM", "CM", ["mc", "amc"], 72, 40), ("LW", "LW", ["aml", "ml"], 16, 20),
        ("RW", "RW", ["amr", "mr"], 84, 20), ("ST", "ST", ["stc"], 50, 10)],
    "4-4-2": [
        ("GK", "GK", ["gk"], 50, 91), ("LB", "LB", ["dl", "wbl"], 13, 71), ("CB", "CB", ["dc"], 37, 75),
        ("CB", "CB", ["dc"], 63, 75), ("RB", "RB", ["dr", "wbr"], 87, 71), ("LM", "LM", ["ml", "aml"], 14, 46),
        ("CM", "CM", ["mc"], 38, 49), ("CM", "CM", ["mc"], 62, 49), ("RM", "RM", ["mr", "amr"], 86, 46),
        ("ST", "ST", ["stc"], 37, 14), ("ST", "ST", ["stc"], 63, 14)],
    "3-5-2": [
        ("GK", "GK", ["gk"], 50, 91), ("CB", "CB", ["dc"], 25, 74), ("CB", "CB", ["dc"], 50, 77),
        ("CB", "CB", ["dc"], 75, 74), ("LWB", "LWB", ["wbl", "dl", "ml"], 9, 49), ("DM", "DM", ["dm", "mc"], 50, 58),
        ("CM", "CM", ["mc"], 32, 43), ("CM", "CM", ["mc", "amc"], 68, 43), ("RWB", "RWB", ["wbr", "dr", "mr"], 91, 49),
        ("ST", "ST", ["stc"], 37, 14), ("ST", "ST", ["stc"], 63, 14)],
}

NATIONS = {  # nation_id: (code, name) - verified against well-known players in the FM27 database
    162: ("PT", "Portugal"), 189: ("BR", "Brazil"), 170: ("ES", "Spain"), 187: ("AR", "Argentina"),
    191: ("CO", "Colombia"), 195: ("UY", "Uruguay"), 190: ("CL", "Chile"), 192: ("EC", "Ecuador"),
    109: ("MX", "Mexico"), 193: ("PY", "Paraguay"), 194: ("PE", "Peru"), 196: ("VE", "Venezuela"),
    188: ("BO", "Bolivia"), 99: ("CR", "Costa Rica"), 112: ("PA", "Panama"), 7: ("CV", "Cape Verde"),
    1: ("AO", "Angola"), 18: ("GW", "Guinea-Bissau"), 30: ("MZ", "Mozambique"), 150: ("IT", "Italy"),
    139: ("EN", "England"), 143: ("FR", "France"), 145: ("DE", "Germany"), 158: ("NL", "Netherlands"),
    131: ("BE", "Belgium"), 135: ("HR", "Croatia"), 172: ("CH", "Switzerland"), 138: ("DK", "Denmark"),
    171: ("SE", "Sweden"), 160: ("NO", "Norway"), 161: ("PL", "Poland"), 129: ("AT", "Austria"),
    173: ("TR", "Turkey"), 176: ("RS", "Serbia"), 167: ("SC", "Scotland"), 163: ("IE", "Ireland"),
    137: ("CZ", "Czechia"), 147: ("HU", "Hungary"), 146: ("GR", "Greece"), 29: ("MA", "Morocco"),
    36: ("SN", "Senegal"), 33: ("NG", "Nigeria"), 16: ("GH", "Ghana"), 19: ("CI", "Ivory Coast"),
    0: ("DZ", "Algeria"), 57: ("EG", "Egypt"), 61: ("JP", "Japan"), 120: ("US", "USA"), 97: ("CA", "Canada"),
    177: ("AU", "Australia"), 168: ("SK", "Slovakia"), 169: ("SI", "Slovenia"), 142: ("FI", "Finland"),
    148: ("IS", "Iceland"), 149: ("IL", "Israel"), 144: ("GE", "Georgia"), 126: ("AL", "Albania"),
    219: ("XK", "Kosovo"), 133: ("BA", "Bosnia"), 155: ("MK", "North Macedonia"), 17: ("GN", "Guinea"),
    26: ("ML", "Mali"), 48: ("CD", "DR Congo"), 14: ("GA", "Gabon"), 78: ("SA", "Saudi Arabia"),
    59: ("IR", "Iran"), 180: ("NZ", "New Zealand"), 108: ("JM", "Jamaica"), 128: ("AM", "Armenia"),
}
NATION_CODES = {k: v[0] for k, v in NATIONS.items()}
NATION_NAMES = {k: v[1] for k, v in NATIONS.items()}


def clean(v):
    if isinstance(v, (np.integer,)): return int(v)
    if isinstance(v, (np.floating,)): return None if np.isnan(v) else round(float(v), 2)
    if pd.isna(v) if not isinstance(v, (list, dict, str)) else False: return None
    return v


def read_history(save, club_uid, refresh=True):
    """Minutes/rating of the managed club's players over the last 15 matches (empty when no matches played)."""
    out = os.path.join(DATA, "pms.csv")
    try:
        if refresh or not os.path.exists(out):
            subprocess.run([sys.executable, "-m", "fmsave", "export", save, "player-match-stats", "--managed-club",
                            "--format", "csv", "-o", out], capture_output=True, text=True)
        d = pd.read_csv(out, low_memory=False)
    except Exception:
        return {}, 0
    if len(d):
        d = d[d.minutes > 0]
    if d.empty:
        return {}, 0
    last = sorted(d.date.unique())[-15:]
    d = d[d.date.isin(last)]
    form = {}
    for uid, g in d.groupby("player_uid"):
        mins = g.minutes.sum(); share = mins / (90.0 * len(last))
        rating = g.rating.dropna(); rating = rating[rating > 0]
        rt = rating.mean() if len(rating) else None
        form[int(uid)] = 25.0 * min(1.0, share) + (6.0 * (rt - 6.8) if rt else 0.0)
    return form, int(d.minutes.sum())


def best_xi(squad, slots, min_rating, form=None, override=None):
    """Assign squad players to formation slots (Hungarian). `override` {slot_index: name} pins players."""
    form = form or {}
    chosen, free_slots = {}, list(range(len(slots)))
    pool = squad.copy()
    for k, name in (override or {}).items():
        k = int(k); m = pool[pool.name.str.contains(name, case=False, regex=False)]
        if len(m) and k in free_slots:
            chosen[k] = m.iloc[0]; free_slots.remove(k); pool = pool[pool.uid != m.iloc[0].uid]
    cost = np.zeros((len(free_slots), len(pool)))
    for a, i in enumerate(free_slots):
        cols = slots[i][2]
        for j, (_, p) in enumerate(pool.iterrows()):
            # first-listed position is the natural one; alternatives count slightly less
            rating = max(p[f"positions_{cols[0]}"], max(p[f"positions_{c}"] for c in cols) - 3)
            pen = max(0, 15 - rating) * 6 + (40 if rating < 10 else 0)
            cost[a, j] = -(p["ability_current"] - pen + 1.0 * rating + form.get(int(p.uid), 0))
    r, c = linear_sum_assignment(cost)
    for a, j in zip(r, c):
        chosen[free_slots[a]] = pool.iloc[j]
    return chosen


def clip01(x):
    return np.clip(x, 0, 1)


def pool_for(df, target, slot_cols, is_gk, prefs, exclude_uids, club_uid, need_ca_floor=True):
    pcols = [f"positions_{c}" for c in slot_cols]
    bp = df[(df.club_uid != club_uid) & (~df.uid.isin(exclude_uids))]
    bp = bp[(bp.positions_gk >= 15) if is_gk else (bp.positions_gk < 15)]
    bp = bp[bp[pcols].max(axis=1) >= prefs["min_pos_rating"]]
    bp = bp[(bp.age <= prefs["max_age"] + 3) & (bp.value_m <= prefs["max_value_m"] * 1.8)]
    if not need_ca_floor:
        return bp
    drop = prefs.get("max_ca_drop", 12)
    for drop in (drop, drop + 8, drop + 16, drop + 28):          # relax the CA floor if the position is thin
        pool = bp[bp.ability_current >= target.ability_current - drop]
        if ((pool.age <= prefs["max_age"]) & (pool.value_m <= prefs["max_value_m"])).sum() >= 15:
            break
    return pool


def role_weights(role_name, attrs, phase):
    lib = roles_lib.IP if phase == "ip" else roles_lib.OOP
    w = lib.get(role_name, {})
    return np.array([w.get(a, 0.0) for a in attrs])


def role_fit(X, w):
    """X: n x attrs (1-20). Weighted mean attribute as a 0-100 rating. 50 when role has no weights here."""
    if w.sum() == 0:
        return np.full(len(X), 50.0)
    return 100.0 * (X * w).sum(axis=1) / (20.0 * w.sum())


def attr_candidates(df, target, slot, attrs, prefs, exclude_uids, club_uid, roles, k_oop):
    cols = [f"attributes_{x}" for x in attrs]
    tv = target[cols].astype(float).values
    w = (tv / 20.0) ** 2 + 0.3
    for i, x in enumerate(attrs):
        if x in fr.LOW_W:
            w[i] *= 0.3
    pool = pool_for(df, target, slot[2], slot[2] == ["gk"], prefs, exclude_uids, club_uid)
    X = pool[cols].astype(float).values
    diff = X - tv
    pen = np.where(diff < 0, 1.0, 0.35) * diff ** 2
    dist = np.sqrt((pen * w).sum(axis=1) / w.sum())
    match = 100 * np.exp(-dist / 5.0)
    fit = (1 - k_oop) * role_fit(X, role_weights(roles["ip"], attrs, "ip")) + k_oop * role_fit(X, role_weights(roles["oop"], attrs, "oop"))
    n = clip01((fit - 50) / 35)
    rest = (20 * clip01((pool.ability_current.values - (target.ability_current - 12)) / 24)
            + 20 * clip01((pool.ability_potential.values - (target.ability_potential - 12)) / 24)
            + 10 * clip01((28 - pool.age.values) / 10))
    return pool.assign(match=match, rest=rest, base=0.25 * match + 25 * n + rest)


def money_candidates(df, target, slot, group, prefs, exclude_uids, club_uid, stats, scored, mprefs):
    """Moneyball pool: production percentile + stars + age + affordability. No attributes."""
    pool = pool_for(df, target, slot[2], slot[2] == ["gk"], prefs, exclude_uids, club_uid, need_ca_floor=False)
    pool = pool[pool.ability_current >= target.ability_current - 40]          # at most ~1 star below the starter
    pool = pool.join(scored[group][["prod"]], on="uid", how="left")
    pool = pool.join(stats[["minutes"]].rename(columns={"minutes": "mins"}), on="uid", how="left")
    pool["mins"] = pool.mins.fillna(0)
    ca_s = pool.ability_current.map(mb.stars); pa_s = pool.ability_potential.map(mb.stars)
    cur_s = mb.stars(target.ability_current)
    star_t = clip01((ca_s - (cur_s - 1.0)) / 2.0) * 0.5 + clip01((pa_s - 3.0) / 2.0) * 0.5
    age_t = clip01((28 - pool.age) / 10)
    afford = 1 - clip01(pool.value_m.fillna(0) / (prefs["max_value_m"] * 1.8))
    has = pool["prod"].notna() & (pool.mins >= mprefs["min_minutes_small"])
    use_stats = int(has.sum()) >= mprefs["min_candidates_with_stats"]
    base_stats = 0.55 * pool["prod"].fillna(50) + 15 * star_t + 10 * age_t + 20 * afford
    base_stars = 45 * star_t + 15 * age_t + 25 * afford                        # stars-only fallback (no data)
    mbase = np.where(has, base_stats, base_stars * 0.8) if use_stats else base_stars
    return pool.assign(star_t=star_t, mbase=mbase, has_stats=has), use_stats


def stat_pack(uid, scored_g, stats_row, group):
    out = []
    for key, label, hib, w, fmt in mb.METRICS[group]:
        v = stats_row.get(key) if stats_row is not None else None
        pct = np.nan
        if scored_g is not None and uid in scored_g.index and ("pct_" + key) in scored_g:
            pct = scored_g.loc[uid, "pct_" + key]
        out.append([None if v is None or pd.isna(v) else round(float(v), 3), None if pd.isna(pct) else round(float(pct), 0)])
    return out


def mini_player(p, balance_m, attrs=None):
    nid = int(p["nation_id"]) if not pd.isna(p["nation_id"]) else -1
    second = []
    if isinstance(p.get("second_nation_ids"), str):
        second = [int(x) for x in p["second_nation_ids"].split(";") if x.strip().isdigit()]
    end = p.get("contract_end")
    d = {"uid": int(p["uid"]), "name": p["name"], "age": int(p["age"]), "club": p["club"],
         "nid": nid, "nat": NATION_CODES.get(nid, "—"), "nat_name": NATION_NAMES.get(nid, f"Nation {nid}"),
         "second": second, "pos": str(p["natural_positions"]).replace(";", " · "), "best_pos": p["best_pos"],
         "ca": int(p["ability_current"]), "pa": int(p["ability_potential"]),
         "sc": mb.stars(p["ability_current"]), "sp": mb.stars(p["ability_potential"]),
         "value": float(p["value_m"]) if not pd.isna(p["value_m"]) else None,
         "wage": float(p["wage_k"]) if not pd.isna(p["wage_k"]) else None,
         "end": None if pd.isna(end) else str(end)[:10],
         "foot": f"L{int(p['left_foot'])}/R{int(p['right_foot'])}",
         "status": None if pd.isna(p.get("contract_squad_status")) else str(p["contract_squad_status"]).replace("_", " ")}
    if attrs is not None:
        d["attrs"] = [int(p[f"attributes_{a}"]) for a in attrs]
    return d


last_build_info = {}


def build(save, do_export, prefs_path, out, open_after, start_mode):
    save = save or fr.latest_save()
    if do_export or not os.path.exists(fr.CACHE):
        fr.export(save)
    prefs = json.load(open(prefs_path, encoding="utf-8"))
    mprefs = {"min_minutes": 900, "min_minutes_small": 300, "shrink_k": 900, "min_candidates_with_stats": 8}
    mprefs.update(prefs.get("moneyball", {}))
    df = fr.load()
    mpath, ipath = os.path.join(DATA, "managed.csv"), os.path.join(DATA, "info.txt")
    if do_export or not (os.path.exists(mpath) and os.path.exists(ipath)):
        subprocess.run([sys.executable, "-m", "fmsave", "export", save, "managed-clubs", "--managed-club",
                        "--format", "csv", "-o", mpath], capture_output=True, text=True)
        open(ipath, "w", encoding="utf-8").write(
            subprocess.run([sys.executable, "-m", "fmsave", "info", save], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout)
    managed = pd.read_csv(mpath).iloc[0]
    info = open(ipath, encoding="utf-8").read()
    date = next((l.split(None, 3)[-1].strip() for l in info.splitlines() if l.startswith("In-game date")), "")
    club_uid = int(managed.club_uid)
    club_players = df[df.club_uid == club_uid]
    team_id = club_players.sort_values("ability_current", ascending=False).iloc[0].team_id
    first = club_players[club_players.team_id == team_id]
    first = first[first.on_loan != True] if "on_loan" in first else first
    slots = FORMATIONS[prefs["formation"]]
    form, hist_minutes = read_history(save, club_uid, refresh=do_export)
    use_form = hist_minutes >= 900
    xi = best_xi(first, slots, prefs["min_pos_rating"], form if use_form else None, prefs.get("xi_override"))
    xi_uids = {int(p.uid) for p in xi.values()}
    balance_m = round(float(managed.balance) / 1e6, 1)
    if prefs.get("xi_override"):
        xi_basis = f"{len(prefs['xi_override'])} slot(s) pinned in prefs.json, the rest picked by " + ("recent matches + ability" if use_form else "ability")
    elif use_form:
        xi_basis = f"ability + recent form ({hist_minutes:,} minutes of match history)"
    else:
        xi_basis = "ability only: no match history in the save yet (you can pin players in prefs.json)"

    # ---- moneyball stats (league-wide) ----
    stats = None; scored = {}; n_qual = 0
    try:
        stats = mb.aggregate(mb.export_history(save, refresh=do_export))
        n_qual = int((stats.minutes >= mprefs["min_minutes"]).sum())
        df["group"] = df.best_pos.str.lower().map(mb.POS_GROUP)
        for g in ("GK", "DEF", "MID", "ATT"):
            scored[g] = mb.score_group(stats, df, g, mprefs["min_minutes"], mprefs["shrink_k"])
    except Exception as e:
        print("moneyball stats unavailable:", e)
    money_note = (f"{n_qual:,} players have at least {mprefs['min_minutes']} minutes of stats" if n_qual
                  else f"No player has {mprefs['min_minutes']}+ minutes of stats yet, so ranking falls back to stars, age and price")

    # ---- roles ----
    role_defaults = roles_lib.default_roles(slots)
    for k, v in (prefs.get("roles") or {}).items():
        role_defaults[int(k)].update(v)
    k_oop = float(prefs.get("oop_weight", 0.5))
    pref_ids = {int(k) for k in prefs["preferred_nations"]}
    mv = prefs["max_value_m"]

    def is_pref(d):
        return bool(d["nid"] in pref_ids or any(sn in pref_ids for sn in d["second"]))

    out_slots, used_a, used_m = [], set(), set()
    for i, slot in enumerate(slots):
        short, label, cols, x, y = slot
        t = xi[i]
        is_gk = cols == ["gk"]
        attrs = fr.GK if is_gk else fr.OUTFIELD
        group = mb.GROUP_BY_LABEL.get(label, "MID")
        ap = attr_candidates(df, t, slot, attrs, prefs, used_a | xi_uids, club_uid, role_defaults[i], k_oop)
        core = ap[ap.value_m <= mv].sort_values("base", ascending=False).head(prefs["pool_per_slot"])
        stretch = ap[ap.value_m > mv].sort_values("base", ascending=False).head(prefs["pool_per_slot"] // 4)
        ap = pd.concat([core, stretch]).sort_values("base", ascending=False)
        used_a |= set(ap.head(prefs["per_slot"]).uid.astype(int))
        cands = []
        for _, c in ap.iterrows():
            d = mini_player(c, balance_m, attrs)
            d["match"] = round(float(c.match), 1); d["rest"] = round(float(c.rest), 1); d["base"] = round(float(c.base), 1)
            d["pref"] = is_pref(d)
            cands.append(d)
        mcands, use_stats = [], False
        if stats is not None:
            mp, use_stats = money_candidates(df, t, slot, group, prefs, used_m | xi_uids, club_uid, stats, scored, mprefs)
            core = mp[mp.value_m <= mv].sort_values("mbase", ascending=False).head(prefs["pool_per_slot"])
            stretch = mp[mp.value_m > mv].sort_values("mbase", ascending=False).head(prefs["pool_per_slot"] // 4)
            mp = pd.concat([core, stretch]).sort_values("mbase", ascending=False)
            used_m |= set(mp.head(prefs["per_slot"]).uid.astype(int))
            for _, c in mp.iterrows():
                d = mini_player(c, balance_m)
                u = int(c.uid)
                srow = stats.loc[u] if u in stats.index else None
                d["mins"] = int(c.mins)
                d["prod"] = None if pd.isna(c["prod"]) else round(float(c["prod"]), 1)
                d["rating"] = None if srow is None or pd.isna(srow.get("rating")) else round(float(srow["rating"]), 2)
                d["has"] = bool(c.has_stats); d["mbase"] = round(float(c.mbase), 1); d["star_t"] = round(float(c.star_t), 3)
                d["stats"] = stat_pack(u, scored.get(group), srow, group)
                d["pref"] = is_pref(d)
                mcands.append(d)
        tu = int(t.uid)
        trow = stats.loc[tu] if (stats is not None and tu in stats.index) else None
        player = mini_player(t, balance_m, attrs)
        player["mins"] = int(trow.minutes) if trow is not None else 0
        player["stats"] = stat_pack(tu, scored.get(group), trow, group) if stats is not None else []
        player["prod"] = None
        if trow is not None and group in scored and tu in scored[group].index:
            v = scored[group].loc[tu, "prod"]
            player["prod"] = None if pd.isna(v) else round(float(v), 1)
        out_slots.append({"i": i, "short": short, "label": label, "x": x, "y": y, "gk": is_gk, "group": group,
                          "player": player, "cands": cands, "mcands": mcands, "attr_names": attrs,
                          "roles": role_defaults[i], "use_stats": use_stats,
                          "metrics": [{"k": m[0], "label": m[1], "hib": m[2], "fmt": m[4]} for m in mb.METRICS[group]]})
    bench = [mini_player(p, balance_m) for _, p in
             first[~first.uid.isin(xi_uids)].sort_values("ability_current", ascending=False).iterrows()]

    data = {"mode": start_mode,
            "meta": {"club": managed.club_short_name, "manager": "André Santos", "date": date, "balance": balance_m,
                     "scouting": round(float(managed.scouting_budget_remaining) / 1e3), "formation": prefs["formation"],
                     "generated": datetime.datetime.now().strftime("%d %b %Y %H:%M"), "save": os.path.basename(save),
                     "xi_basis": xi_basis, "money_note": money_note},
            "prefs": {"max_age": prefs["max_age"], "max_value": prefs["max_value_m"], "nation_bonus": prefs["nation_bonus"],
                      "per_slot": prefs["per_slot"], "strict": prefs["strict_nationality"], "oop_weight": k_oop,
                      "pref_nations": sorted(prefs["preferred_nations"].values())},
            "roles": {"ip": roles_lib.IP, "oop": roles_lib.OOP}, "slots": out_slots, "bench": bench}
    last_build_info.update({"date": date})
    html = open(os.path.join(APP, "board_template.html"), encoding="utf-8").read()
    html = html.replace("__DATA__", json.dumps(data, ensure_ascii=False, default=clean))
    out = out or os.path.join(OUT, "recruitment_board.html")
    open(out, "w", encoding="utf-8").write(html)
    print(f"Board written: {out} ({os.path.getsize(out) / 1e3:.0f} KB)")
    print(f"  XI basis: {xi_basis}")
    print(f"  Moneyball: {money_note}")
    if open_after:
        webbrowser.open("file:///" + out.replace("\\", "/"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--save"); ap.add_argument("--no-export", action="store_true")
    ap.add_argument("--open", action="store_true"); ap.add_argument("-o", "--out")
    ap.add_argument("--mode", choices=["attributes", "moneyball"], default="attributes", help="tab shown first")
    ap.add_argument("--prefs", default=os.path.join(ROOT, "prefs.json"))
    a = ap.parse_args()
    build(a.save, not a.no_export, a.prefs, a.out, a.open, a.mode)
