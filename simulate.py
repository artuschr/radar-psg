"""Radar PSG : simule la fin de la Ligue des champions (Monte Carlo) et écrit les pronostics dans data.json.

Entrée : teams.json (classement, forces, tirages connus). Sortie : clé "forecast" de data.json.
Usage : python3 simulate.py [nombre_de_simulations]
"""
import json, random, sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent
T = json.loads((HERE / "teams.json").read_text(encoding="utf-8"))
N = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
random.seed(42)

teams = T["teams"]
R = {t["name"]: t["rating"] for t in teams}
BIG = {t["name"] for t in teams if t.get("big")}
AVG = T.get("league_avg_rating", 1800)
draws = T.get("draws", {})
OUT = set(draws.get("eliminated_teams", []))  # équipes réellement éliminées en phase finale
PSG = "PSG"
HOME_ADV = 60


def expect(a, b):
    return 1 / (1 + 10 ** ((b - a) / 400))


def play(ra, rb):
    """Un match : renvoie (points, écart de buts) pour l'équipe a."""
    e = expect(ra, rb)
    pd = 0.26 * (1 - abs(2 * e - 1)) + 0.12
    pw = (1 - pd) * e
    x = random.random()
    if x < pw:
        return 3, random.choice((1, 1, 1, 2, 2, 3))
    if x < pw + pd:
        return 1, 0
    return 0, -random.choice((1, 1, 1, 2, 2, 3))


def tie(a, b):
    """Double confrontation : renvoie le qualifié."""
    if a in OUT:
        return b
    if b in OUT:
        return a
    p = 1 / (1 + 10 ** (-(R[a] - R[b]) * 1.15 / 400))
    return a if random.random() < p else b


def league():
    table = []
    for t in teams:
        pts, gd = t["pts"], t["gd"]
        left = 8 - t["played"]
        if t["name"] == PSG and left == len(T.get("psg_remaining", [])):
            for f in T["psg_remaining"]:
                ra = R[PSG] + (HOME_ADV if f["home"] else -HOME_ADV)
                p, g = play(ra, R.get(f["opp"], AVG))
                pts, gd = pts + p, gd + g
        else:
            for _ in range(left):
                p, g = play(t["rating"], AVG)
                pts, gd = pts + p, gd + g
        table.append((pts, gd, random.random(), t["name"]))
    table.sort(reverse=True)
    return [x[3] for x in table]


def pick(pair_a, pair_b):
    """Tirage dans un couple de positions : (a1,a2) contre (b1,b2), au hasard."""
    b = list(pair_b)
    random.shuffle(b)
    return [(pair_a[0], b[0]), (pair_a[1], b[1])]


def force(pairs, known):
    """Si l'adversaire réel du PSG est connu, on l'impose dans ce tour."""
    if not known:
        return pairs
    flat = [x for p in pairs for x in p]
    if PSG not in flat:
        return pairs
    new = []
    for a, b in pairs:
        if PSG in (a, b):
            other = b if a == PSG else a
            new.append((PSG, known, other))
        else:
            new.append((a, b, None))
    # l'ancien adversaire du PSG prend la place de l'adversaire réel ailleurs
    out = []
    swap = next(x[2] for x in new if x[2] is not None)
    for a, b, _ in new:
        if a == PSG:
            out.append((PSG, known))
        else:
            out.append((swap if a == known else a, swap if b == known else b))
    return out


rounds = ["playoff", "r16", "qf", "sf"]
reach = Counter()
opp = defaultdict(Counter)
pos_bucket = Counter()
team_top8 = Counter()
team_ko = Counter()
team_r16 = Counter()

for _ in range(N):
    order = league()
    pos = {name: i + 1 for i, name in enumerate(order)}
    for name in order[:8]:
        team_top8[name] += 1
    for name in order[:24]:
        team_ko[name] += 1
    P = lambda i: order[i - 1]
    pp = pos[PSG]
    pos_bucket["top8" if pp <= 8 else "barrages" if pp <= 24 else "out"] += 1

    # Barrages : (9,10)v(23,24), (11,12)v(21,22), (13,14)v(19,20), (15,16)v(17,18)
    po_groups = {}
    for (s1, s2), (u1, u2) in (((9, 10), (23, 24)), ((11, 12), (21, 22)), ((13, 14), (19, 20)), ((15, 16), (17, 18))):
        pairs = pick((P(s1), P(s2)), (P(u1), P(u2)))
        pairs = force(pairs, draws.get("playoff"))
        po_groups[(s1, s2)] = [tie(a, b) for a, b in pairs]
        for a, b in pairs:
            if PSG in (a, b):
                reach["playoff"] += 1
                opp["playoff"][b if a == PSG else a] += 1
    winners_po_psg = PSG in [w for g in po_groups.values() for w in g]
    if pp > 24 or (8 < pp <= 24 and not winners_po_psg):
        pass

    # Huitièmes : (1,2) v vainqueurs (15/16-17/18) ; (3,4) v (13/14-19/20) ; (5,6) v (11/12-21/22) ; (7,8) v (9/10-23/24)
    r16 = {}
    for seeds, grp in (((1, 2), (15, 16)), ((3, 4), (13, 14)), ((5, 6), (11, 12)), ((7, 8), (9, 10))):
        pairs = pick((P(seeds[0]), P(seeds[1])), tuple(po_groups[grp]))
        pairs = force(pairs, draws.get("r16"))
        r16[seeds] = pairs
        for a, b in pairs:
            if PSG in (a, b):
                reach["r16"] += 1
                opp["r16"][b if a == PSG else a] += 1

    # Tableau : chaque moitié = (1|2) + (7|8) + (3|4) + (5|6), têtes de série réparties au hasard
    halves = [[], []]
    for seeds in ((1, 2), (7, 8), (3, 4), (5, 6)):
        ties = r16[seeds][:]
        random.shuffle(ties)
        halves[0].append(ties[0])
        halves[1].append(ties[1])
    finalists = []
    for h in halves:
        w = [tie(a, b) for a, b in h]  # [1|2, 7|8, 3|4, 5|6]
        qf = [(w[0], w[1]), (w[2], w[3])]
        qf = force(qf, draws.get("qf"))
        for a, b in qf:
            if PSG in (a, b):
                reach["qf"] += 1
                opp["qf"][b if a == PSG else a] += 1
        sfp = [(tie(*qf[0]), tie(*qf[1]))]
        sfp = force(sfp, draws.get("sf"))
        for a, b in sfp:
            if PSG in (a, b):
                reach["sf"] += 1
                opp["sf"][b if a == PSG else a] += 1
        finalists.append(tie(*sfp[0]))
    if PSG in finalists:
        reach["final"] += 1
    for name in [x for p in r16.values() for t in p for x in t]:
        team_r16[name] += 1

if draws.get("eliminated"):
    reach = Counter()

out_rounds = {}
for r in rounds:
    n = reach[r]
    lst = []
    if n:
        for name, c in opp[r].most_common():
            if c / n < 0.01:
                continue
            lst.append({"name": name, "p": round(c / n, 4), "big": name in BIG})
    big_p = round(sum(c for name, c in opp[r].items() if name in BIG) / n, 4) if n else 0
    out_rounds[r] = {"p": round(n / N, 4), "opponents": lst, "p_big": big_p, "known": draws.get(r)}

std = sorted(teams, key=lambda t: (-t["pts"], -t["gd"]))
data_path = HERE / "data.json"
data = json.loads(data_path.read_text(encoding="utf-8"))
data["forecast"] = {
    "updated": datetime.now(timezone.utc).isoformat(timespec="minutes"),
    "standings_date": T.get("standings_date"),
    "sims": N,
    "psg": {
        "top8": round(pos_bucket["top8"] / N, 4),
        "barrages": round(pos_bucket["barrages"] / N, 4),
        "out": round(pos_bucket["out"] / N, 4),
        "final": round(reach["final"] / N, 4),
        "rounds": out_rounds,
    },
    "table": [
        {"name": t["name"], "played": t["played"], "pts": t["pts"], "gd": t["gd"],
         "p_top8": round(team_top8[t["name"]] / N, 3), "p_ko": round(team_ko[t["name"]] / N, 3),
         "big": t.get("big", False)}
        for t in std
    ],
}
data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print(f"{N} simulations · PSG top 8 {pos_bucket['top8']/N:.0%} · barrages {pos_bucket['barrages']/N:.0%}")
for r in rounds:
    o = out_rounds[r]
    top = ", ".join(f"{x['name']} {x['p']:.0%}" for x in o["opponents"][:5])
    print(f"  {r:8s} {o['p']:.0%}  (gros club {o['p_big']:.0%})  {top}")
print(f"  finale   {reach['final']/N:.0%}")
