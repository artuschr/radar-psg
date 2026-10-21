"""Génère alertes.ics à partir de data.json (Radar PSG)."""
import json, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

here = Path(__file__).parent
data = json.loads((here / "data.json").read_text(encoding="utf-8"))
now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def utc(iso):
    return datetime.fromisoformat(iso).astimezone(timezone.utc)


def fmt(dt):
    return dt.strftime("%Y%m%dT%H%M%SZ")


def esc(s):
    return s.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")


lines = [
    "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Radar PSG//FR", "CALSCALE:GREGORIAN",
    "METHOD:PUBLISH", "X-WR-CALNAME:Radar PSG", "X-WR-TIMEZONE:Europe/Paris",
    "REFRESH-INTERVAL;VALUE=DURATION:PT6H", "X-PUBLISHED-TTL:PT6H",
]


def event(uid, start, minutes, title, desc, url, alarm_min):
    ev = [
        "BEGIN:VEVENT", f"UID:{uid}@radar-psg", f"DTSTAMP:{now}",
        f"DTSTART:{fmt(start)}", f"DTEND:{fmt(start + timedelta(minutes=minutes))}",
        f"SUMMARY:{esc(title)}", f"DESCRIPTION:{esc(desc)}", f"URL:{url}",
    ]
    if alarm_min is not None:
        ev += ["BEGIN:VALARM", "ACTION:DISPLAY", f"DESCRIPTION:{esc(title)}",
               f"TRIGGER:-PT{alarm_min}M", "END:VALARM"]
    ev.append("END:VEVENT")
    lines.extend(ev)


for m in data["matches"]:
    if not m.get("opponent") or not m.get("date"):
        continue
    name = f"PSG – {m['opponent']}"
    url = m.get("buy_url", "https://billetterie.psg.fr/")
    event(f"{m['id']}-match", utc(m["date"]), 120, f"⚽ {name} (Parc des Princes)",
          f"{m['round']}. Billetterie : {url}", url, 180)
    sale = m.get("sale", {})
    for key, label in (("members_open", "membres MyParis"), ("public_open", "grand public")):
        if sale.get(key):
            event(f"{m['id']}-{key}", utc(sale[key]), 30, f"🎟️ Vente {label} : {name}",
                  f"La vente {label} ouvre maintenant. Acheter : {url}", url, 15)
    if not sale.get("members_open") and not sale.get("public_open") and m.get("check_date"):
        event(f"{m['id']}-check", utc(m["check_date"]), 15, f"🔎 Vérifier les billets : {name}",
              f"Date d'ouverture pas encore connue. Ouvre l'app Radar PSG ou la billetterie : {url}", url, 0)

lines.append("END:VCALENDAR")
out = "\r\n".join(lines) + "\r\n"
(here / "alertes.ics").write_text(out, encoding="utf-8")
print(f"alertes.ics : {out.count('BEGIN:VEVENT')} événements")
