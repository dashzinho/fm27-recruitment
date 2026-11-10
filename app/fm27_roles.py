"""Approximate attribute profiles for FM roles / defensive behaviours.

These are NOT Sports Interactive's exact role definitions (those aren't exposed in the save);
they are sensible key (weight 3) + secondary (weight 1.5) attribute sets per role. Edit freely.
"""

def _r(key, sec):
    w = {a: 3.0 for a in key}
    for a in sec:
        w.setdefault(a, 1.5)
    return w

# ---- In possession roles ----
IP = {
    # goalkeepers
    "Goalkeeper": _r(["reflexes", "handling", "one_on_ones", "command_of_area", "aerial_reach"],
                     ["positioning", "concentration", "decisions", "communication", "agility", "kicking"]),
    "Sweeper Keeper": _r(["reflexes", "one_on_ones", "rushing_out", "passing", "first_touch", "anticipation", "decisions"],
                         ["command_of_area", "kicking", "composure", "agility", "positioning", "throwing", "handling"]),
    # full / wing backs
    "Full Back": _r(["marking", "tackling", "positioning", "acceleration", "stamina"],
                    ["anticipation", "concentration", "work_rate", "crossing", "passing", "pace"]),
    "Wing Back": _r(["crossing", "dribbling", "acceleration", "pace", "stamina", "work_rate", "off_the_ball"],
                    ["tackling", "marking", "technique", "passing", "agility", "teamwork"]),
    "Inverted Wing Back": _r(["passing", "tackling", "positioning", "decisions", "technique", "teamwork"],
                             ["marking", "anticipation", "first_touch", "vision", "composure", "stamina"]),
    # centre backs
    "Central Defender": _r(["heading", "marking", "tackling", "positioning", "jumping_reach", "strength", "anticipation"],
                           ["concentration", "bravery", "decisions", "aggression", "pace"]),
    "Ball Playing Defender": _r(["passing", "composure", "technique", "heading", "marking", "tackling", "positioning"],
                                ["first_touch", "vision", "decisions", "anticipation", "jumping_reach", "strength"]),
    "No-Nonsense CB": _r(["heading", "marking", "tackling", "jumping_reach", "strength", "bravery", "aggression"],
                         ["positioning", "anticipation", "concentration", "pace"]),
    # defensive / central midfield
    "Anchor": _r(["marking", "tackling", "positioning", "anticipation", "concentration", "decisions", "teamwork"],
                 ["strength", "composure", "passing", "heading"]),
    "Deep Lying Playmaker": _r(["passing", "vision", "technique", "composure", "decisions", "first_touch", "teamwork"],
                               ["anticipation", "positioning", "flair", "off_the_ball", "stamina"]),
    "Ball Winning Midfielder": _r(["tackling", "aggression", "work_rate", "teamwork", "stamina", "anticipation", "bravery"],
                                  ["marking", "determination", "acceleration", "pace", "strength", "positioning"]),
    "Central Midfielder": _r(["passing", "tackling", "teamwork", "decisions", "work_rate", "first_touch", "concentration"],
                             ["stamina", "anticipation", "positioning", "vision", "composure", "technique"]),
    "Box To Box": _r(["work_rate", "stamina", "passing", "off_the_ball", "tackling", "teamwork", "determination"],
                     ["dribbling", "first_touch", "anticipation", "decisions", "composure", "long_shots", "strength", "acceleration"]),
    "Advanced Playmaker": _r(["passing", "vision", "technique", "off_the_ball", "decisions", "first_touch", "composure", "flair"],
                             ["dribbling", "anticipation", "teamwork", "acceleration", "long_shots", "agility"]),
    "Mezzala": _r(["passing", "dribbling", "off_the_ball", "vision", "technique", "decisions", "acceleration"],
                  ["flair", "first_touch", "long_shots", "work_rate", "teamwork", "composure", "stamina"]),
    # attacking midfield / wide
    "Attacking Midfielder": _r(["first_touch", "passing", "technique", "off_the_ball", "flair", "vision", "decisions", "dribbling"],
                               ["composure", "anticipation", "long_shots", "finishing", "acceleration", "agility"]),
    "Shadow Striker": _r(["finishing", "off_the_ball", "anticipation", "composure", "acceleration", "dribbling", "first_touch"],
                         ["pace", "work_rate", "technique", "decisions", "flair", "agility"]),
    "Trequartista": _r(["dribbling", "flair", "vision", "passing", "technique", "first_touch", "composure", "off_the_ball"],
                       ["decisions", "finishing", "long_shots", "agility", "acceleration"]),
    "Winger": _r(["crossing", "dribbling", "acceleration", "pace", "technique", "agility", "stamina"],
                 ["first_touch", "off_the_ball", "balance", "work_rate", "flair"]),
    "Inside Forward": _r(["dribbling", "acceleration", "pace", "finishing", "off_the_ball", "first_touch", "technique", "composure"],
                         ["agility", "balance", "flair", "long_shots", "anticipation", "decisions"]),
    "Inverted Winger": _r(["dribbling", "passing", "vision", "technique", "acceleration", "first_touch", "agility", "decisions"],
                          ["crossing", "flair", "off_the_ball", "pace", "balance", "teamwork"]),
    "Wide Playmaker": _r(["passing", "vision", "technique", "first_touch", "decisions", "dribbling", "off_the_ball", "teamwork"],
                         ["crossing", "flair", "acceleration", "agility", "composure"]),
    # strikers
    "Advanced Forward": _r(["finishing", "off_the_ball", "acceleration", "pace", "anticipation", "composure", "dribbling", "first_touch"],
                           ["technique", "agility", "balance", "decisions", "stamina"]),
    "Pressing Forward": _r(["work_rate", "aggression", "stamina", "anticipation", "acceleration", "teamwork", "determination", "finishing"],
                           ["pace", "first_touch", "off_the_ball", "bravery", "composure"]),
    "Complete Forward": _r(["finishing", "dribbling", "first_touch", "technique", "off_the_ball", "passing", "acceleration", "strength", "heading"],
                           ["anticipation", "composure", "decisions", "vision", "agility", "balance", "jumping_reach", "pace"]),
    "Target Forward": _r(["heading", "strength", "jumping_reach", "balance", "bravery", "finishing", "aggression"],
                         ["first_touch", "off_the_ball", "composure", "anticipation", "teamwork"]),
    "Poacher": _r(["finishing", "off_the_ball", "anticipation", "composure", "acceleration", "decisions"],
                  ["first_touch", "concentration", "balance", "determination"]),
    "False Nine": _r(["passing", "vision", "technique", "first_touch", "dribbling", "off_the_ball", "composure", "decisions"],
                     ["finishing", "flair", "teamwork", "anticipation", "acceleration", "agility"]),
}

# ---- Out of possession behaviours ----
OOP = {
    "Goalkeeper": IP["Goalkeeper"],
    "Sweeper Keeper": IP["Sweeper Keeper"],
    "Press": _r(["work_rate", "aggression", "stamina", "anticipation", "teamwork", "acceleration"],
                ["determination", "tackling", "pace", "bravery"]),
    "Track Back": _r(["work_rate", "stamina", "tackling", "positioning", "teamwork", "marking"],
                     ["anticipation", "concentration", "determination", "acceleration", "pace"]),
    "Screen": _r(["positioning", "anticipation", "marking", "concentration", "decisions", "tackling", "teamwork"],
                 ["strength", "composure", "work_rate", "stamina"]),
    "Mark": _r(["marking", "tackling", "positioning", "anticipation", "concentration", "strength"],
               ["jumping_reach", "bravery", "decisions", "aggression", "heading"]),
    "Cover": _r(["positioning", "anticipation", "concentration", "pace", "acceleration", "marking", "tackling"],
                ["decisions", "composure", "heading", "teamwork"]),
    "Aerial Defend": _r(["heading", "jumping_reach", "strength", "marking", "positioning", "bravery"],
                        ["aggression", "tackling", "anticipation", "concentration"]),
    "Counter Outlet": _r(["pace", "acceleration", "off_the_ball", "finishing", "anticipation", "dribbling"],
                         ["first_touch", "composure", "stamina", "decisions", "agility"]),
}

# defaults per formation slot label -> (IP role, OOP behaviour). Edit prefs.json "roles" to override per slot.
DEFAULT_BY_LABEL = {
    "GK": ("Sweeper Keeper", "Goalkeeper"),
    "LB": ("Wing Back", "Track Back"), "RB": ("Wing Back", "Track Back"),
    "LWB": ("Wing Back", "Track Back"), "RWB": ("Wing Back", "Track Back"),
    "CB": ("Ball Playing Defender", "Cover"),
    "DM": ("Deep Lying Playmaker", "Screen"),
    "CM": ("Box To Box", "Press"), "LM": ("Winger", "Track Back"), "RM": ("Winger", "Track Back"),
    "LW": ("Inside Forward", "Track Back"), "RW": ("Inside Forward", "Track Back"),
    "AM": ("Advanced Playmaker", "Press"),
    "ST": ("Advanced Forward", "Press"),
}
# second occurrence of the same label (e.g. 2nd CB / 2nd DM) gets a complementary role
SECOND_BY_LABEL = {
    "CB": ("Central Defender", "Aerial Defend"),
    "DM": ("Ball Winning Midfielder", "Press"),
    "CM": ("Central Midfielder", "Screen"),
    "ST": ("Pressing Forward", "Press"),
}


def default_roles(slots):
    seen, out = {}, []
    for short, label, *_ in slots:
        n = seen.get(label, 0); seen[label] = n + 1
        ip, oop = (SECOND_BY_LABEL.get(label) if n and label in SECOND_BY_LABEL else DEFAULT_BY_LABEL.get(label, ("Central Midfielder", "Press")))
        out.append({"ip": ip, "oop": oop})
    return out
