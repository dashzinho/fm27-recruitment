# FM27 Recruitment Board

Reads your Football Manager 27 save and builds an interactive, offline HTML board: your starting XI on a pitch with 5 replacement targets per position, in two modes.

- **Attributes**: profile similarity to the player being replaced, in-possession / out-of-possession role fit, CA/PA, age and nationality preference.
- **Moneyball**: no attributes. Ranks on season stats (per-90 percentiles vs position peers, shrunk for small samples), stars, age and price.

Save parsing is done by [fmsave](https://github.com/rhiever/fmsave) (read-only, never modifies the save).

## Run

```
python fm27.py --open
```

First run sets itself up (folders, `pip install fmsave pandas numpy scipy`, default `prefs.json`), parses the newest save in `Documents\Sports Interactive\Football Manager 27\games` (about 90 s) and builds `output/recruitment_board.html`. Later runs are update mode: if the save, the code and `prefs.json` are unchanged it prints "Up to date" instantly; a new save re-parses; a change to only prefs/code rebuilds from the cached data.

Flags: `--force`, `--mode moneyball` (tab shown first), `--save <path>`, `--open`.

## Preferences (`prefs.json`)

| Key | Meaning |
|---|---|
| `formation` | 4-2-3-1, 4-3-3, 4-4-2 or 3-5-2 |
| `max_age`, `max_value_m` | candidate filters (age, value in EUR millions) |
| `preferred_nations`, `nation_bonus`, `strict_nationality` | nationality preference (ids -> names), ranking bonus or hard filter |
| `oop_weight` | how much out-of-possession role fit counts (0-1) |
| `roles` | per-slot role override, e.g. `{"1": {"ip": "Inverted Wing Back", "oop": "Track Back"}}` |
| `xi_override` | pin players to slots, e.g. `{"0": "Diogo Costa"}` |
| `moneyball` | minutes thresholds for the stats-based ranking |

## How it works

- **Starting XI**: the save has no stored lineup before matches are played, so the XI is inferred: best player per formation slot by CA (natural position first), plus recent form once the save has 900+ minutes of match history. Pin real players with `xi_override`.
- **Roles**: in-possession roles and out-of-possession behaviours (Press, Track Back, Screen, Cover, ...) are attribute profiles in `app/fm27_roles.py`. They are approximations of the in-game roles (exact definitions aren't in the save) and are meant to be edited.
- **Moneyball** needs played minutes. A fresh pre-season save has almost none, so the board shows a banner and ranks by stars, age and price until players pass 300+ minutes. Stars are derived from CA/PA (CA / 40, half steps).

## Layout

```
fm27.py        entry point (setup + update logic)
prefs.json     preferences
app/           fm27_report.py (builder), fm27_recruit.py (data + CLI), fm27_moneyball.py, fm27_roles.py, board_template.html
data/          cached parsed data + state.json (git-ignored)
output/        recruitment_board.html (git-ignored, data embedded)
```

## CLI (no HTML)

```
python app/fm27_recruit.py similar "Gabri Veiga" --max-age 26 --max-value 40
python app/fm27_recruit.py search --pos MC --min-ca 120
python app/fm27_recruit.py squad --club "FC Porto"
```

## Caveats

- fmsave reports newer FM27 builds as "unverified (partial coverage)". Attributes, age, contract and value were checked against the in-game profile for one player (36/36 attributes matched); wages can differ slightly from the in-game screen.
- Nation ids are mapped for about 70 countries (`NATIONS` in `app/fm27_report.py`); others show a dash.
- Claude Code skill: `/fm27-recruit`.

## License

Copyright (c) 2026 André Santos. All rights reserved. The code is public for viewing only; see [LICENSE](LICENSE). Contact me for permission to use it.
