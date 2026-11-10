#!/usr/bin/env python
"""FM27 Recruitment Board - one command.

    python fm27.py            first run: sets everything up and builds the board.
                              later runs: update mode (only does work if the save changed).
    python fm27.py --open     also open the board in your browser
    python fm27.py --force    re-read the save even if it hasn't changed
    python fm27.py --mode moneyball     which tab opens first (attributes | moneyball)
    python fm27.py --save "path\\to\\x.fm"   use a specific save instead of the newest one

Layout (created on first run):
    prefs.json        your preferences (formation, age, budget, nationalities, roles, XI pins)
    app/              the code + HTML template
    data/             cached parsed data (CSV) + state.json (what was built and from which save)
    output/           recruitment_board.html (data is embedded; opens offline)
"""
import argparse, hashlib, json, os, subprocess, sys, time, webbrowser

ROOT = os.path.dirname(os.path.abspath(__file__))
APP, DATA, OUT = (os.path.join(ROOT, d) for d in ("app", "data", "output"))
STATE = os.path.join(DATA, "state.json")
HTML = os.path.join(OUT, "recruitment_board.html")
SAVES = os.path.expanduser(r"~\Documents\Sports Interactive\Football Manager 27\games")
DEPS = {"fmsave": "fmsave", "pandas": "pandas", "numpy": "numpy", "scipy": "scipy"}

DEFAULT_PREFS = {
    "formation": "4-2-3-1", "max_age": 26, "max_value_m": 45, "min_pos_rating": 15, "per_slot": 5, "pool_per_slot": 40,
    "nation_bonus": 8, "strict_nationality": False, "max_ca_drop": 12, "oop_weight": 0.5,
    "preferred_nations": {"162": "Portugal", "189": "Brazil", "1": "Angola", "7": "Cape Verde", "18": "Guinea-Bissau",
                          "30": "Mozambique", "187": "Argentina", "188": "Bolivia", "190": "Chile", "191": "Colombia",
                          "192": "Ecuador", "193": "Paraguay", "194": "Peru", "195": "Uruguay", "196": "Venezuela",
                          "109": "Mexico", "99": "Costa Rica", "112": "Panama"},
    "roles": {}, "xi_override": {},
    "moneyball": {"min_minutes": 900, "min_minutes_small": 300, "shrink_k": 900, "min_candidates_with_stats": 8},
}


def log(msg): print(msg, flush=True)


def newest_save(path=None):
    if path: return path
    import glob
    files = [f for f in glob.glob(os.path.join(SAVES, "*.fm")) if "overwrite backup" not in f.lower()]
    if not files: sys.exit(f"No .fm saves found in {SAVES}")
    return max(files, key=os.path.getmtime)


def sig_save(path):
    st = os.stat(path); return f"{os.path.abspath(path)}|{st.st_size}|{int(st.st_mtime)}"


def sig_code():
    h = hashlib.md5()
    for base, _, files in os.walk(APP):
        for f in sorted(files):
            if f.endswith((".py", ".html")):
                h.update(open(os.path.join(base, f), "rb").read())
    return h.hexdigest()[:12]


def sig_prefs():
    p = os.path.join(ROOT, "prefs.json")
    return hashlib.md5(open(p, "rb").read()).hexdigest()[:12] if os.path.exists(p) else ""


def load_state():
    try: return json.load(open(STATE, encoding="utf-8"))
    except Exception: return {}


def setup():
    """First run: folders, dependencies, default prefs."""
    log("First run: setting up the FM27 recruitment folder...")
    for d in (APP, DATA, OUT): os.makedirs(d, exist_ok=True)
    missing = []
    for mod, pkg in DEPS.items():
        try: __import__(mod)
        except ImportError: missing.append(pkg)
    if missing:
        log(f"  installing: {', '.join(missing)}")
        r = subprocess.run([sys.executable, "-m", "pip", "install", "-q", *missing, "--disable-pip-version-check"])
        if r.returncode: sys.exit("pip install failed; install manually: pip install " + " ".join(missing))
    if not os.path.exists(os.path.join(ROOT, "prefs.json")):
        json.dump(DEFAULT_PREFS, open(os.path.join(ROOT, "prefs.json"), "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        log("  wrote default prefs.json")
    log("  setup complete")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--open", action="store_true"); ap.add_argument("--force", action="store_true")
    ap.add_argument("--mode", choices=["attributes", "moneyball"], default="attributes")
    ap.add_argument("--save")
    a = ap.parse_args()

    state = load_state()
    first_run = not state.get("setup_done") or not os.path.isdir(APP) or not os.path.exists(os.path.join(ROOT, "prefs.json"))
    if first_run:
        setup()
    save = newest_save(a.save)
    s_save, s_code, s_prefs = sig_save(save), sig_code(), sig_prefs()
    save_changed = a.force or first_run or state.get("save") != s_save or not os.path.exists(os.path.join(DATA, "players.csv"))
    rebuild = save_changed or state.get("code") != s_code or state.get("prefs") != s_prefs or not os.path.exists(HTML) \
        or state.get("mode") != a.mode

    if not rebuild:
        log(f"Up to date: nothing changed since {state.get('built_at')} (save: {os.path.basename(save)}, in-game {state.get('game_date')}).")
        log(f"Board: {HTML}")
        if a.open: webbrowser.open("file:///" + HTML.replace("\\", "/"))
        return

    sys.path.insert(0, APP)
    import fm27_report
    why = "new/changed save" if save_changed else "code, prefs or mode changed (re-using cached save data)"
    log(("Setup run" if first_run else "Update mode") + f": rebuilding ({why})...")
    t0 = time.time()
    fm27_report.build(save, save_changed, os.path.join(ROOT, "prefs.json"), HTML, a.open, a.mode)
    info = {}
    try:
        info = fm27_report.last_build_info
    except Exception: pass
    state.update({"setup_done": True, "save": s_save, "code": s_code, "prefs": s_prefs, "mode": a.mode,
                  "built_at": time.strftime("%Y-%m-%d %H:%M"), "game_date": info.get("date", state.get("game_date", "")),
                  "seconds": round(time.time() - t0)})
    json.dump(state, open(STATE, "w", encoding="utf-8"), indent=2)
    log(f"Done in {round(time.time() - t0)}s -> {HTML}")


if __name__ == "__main__":
    main()
