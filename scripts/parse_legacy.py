"""One-shot: converte o ICS original (jpgcc/calendario-mundial-2026) em data/matches.json.

Uso: python scripts/parse_legacy.py path/para/original.ics

Apenas necessário para popular/refrescar matches.json a partir do calendário base.
A geração do ICS final é feita por scripts/generate.py.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from zoneinfo import ZoneInfo
from datetime import datetime

LX = ZoneInfo("Europe/Lisbon")

SUMMARY_GROUP = re.compile(r"^Mundial 2026: (.+?) vs (.+?) \(Grupo ([A-L])\)$")
SUMMARY_KO = re.compile(r"^Mundial 2026: (.+?) \((.+?)\)$")
SUMMARY_FINAL = re.compile(r"^Mundial 2026: FINAL — (.+?) vs (.+?)$")


def parse_events(text: str) -> list[dict]:
    events = []
    cur: dict | None = None
    for raw in text.splitlines():
        line = raw.rstrip("\r")
        if line == "BEGIN:VEVENT":
            cur = {}
        elif line == "END:VEVENT":
            if cur:
                events.append(cur)
            cur = None
        elif cur is not None:
            if ":" in line:
                k, _, v = line.partition(":")
                cur[k] = v
    return events


def to_match(evt: dict, idx: int) -> dict:
    uid = evt["UID"]
    summary = evt["SUMMARY"]
    desc = evt.get("DESCRIPTION", "")
    location = evt.get("LOCATION", "").replace("\\,", ",")
    categories = [c for c in evt.get("CATEGORIES", "").split(",") if c]

    # canais
    channels: list[str] = []
    m = re.search(r"Transmiss[ãa]o:\s*(.+?)(?:\.|$)", desc)
    if m:
        raw = m.group(1).replace("\\,", ",")
        channels = [c.strip() for c in raw.split(",") if c.strip()]

    simultaneous = "jornada simultânea" in desc

    # data
    has_time = False
    for key in evt:
        if key.startswith("DTSTART"):
            dt_key, dt_val = key, evt[key]
            break
    if "VALUE=DATE" in dt_key:
        # all-day
        kickoff_local = datetime.strptime(dt_val, "%Y%m%d").replace(tzinfo=LX)
        kickoff_iso = kickoff_local.date().isoformat()
        all_day = True
    else:
        kickoff_local = datetime.strptime(dt_val, "%Y%m%dT%H%M%S").replace(tzinfo=LX)
        kickoff_iso = kickoff_local.isoformat()
        all_day = False

    # equipas / fase
    home = away = None
    group = None
    stage = None
    sub = None
    if (m := SUMMARY_GROUP.match(summary)):
        home, away, group = m.group(1), m.group(2), m.group(3)
        stage = "group"
    elif (m := SUMMARY_FINAL.match(summary)):
        home, away = m.group(1), m.group(2)
        stage = "final"
        sub = "Final"
    elif (m := SUMMARY_KO.match(summary)):
        rest, sub = m.group(1), m.group(2)
        if " vs " in rest:
            home, away = rest.split(" vs ", 1)
        else:
            home, away = rest, ""
        stage_map = {
            "16-avos": "r32",
            "Oitavos": "r16",
            "Quartos de Final": "qf",
            "Meia-Final": "sf",
            "3.º/4.º Lugar": "third",
        }
        stage = stage_map.get(sub, "ko")
    else:
        raise ValueError(f"summary não reconhecido: {summary}")

    return {
        "id": idx,
        "uid_legacy": uid,
        "stage": stage,
        "stage_label_pt": sub or {"group": f"Grupo {group}"}.get(stage),
        "group": group,
        "home": home,
        "away": away,
        "kickoff_local": kickoff_iso,
        "all_day": all_day,
        "simultaneous": simultaneous,
        "location": location,
        "channels_pt": channels,
        "categories": categories,
    }


def main() -> None:
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/orig.ics")
    out = Path(__file__).resolve().parent.parent / "data" / "matches.json"
    events = parse_events(src.read_text(encoding="utf-8"))
    matches = [to_match(e, i + 1) for i, e in enumerate(events)]
    payload = {
        "source": "https://github.com/jpgcc/calendario-mundial-2026",
        "official_source": "https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/schedule",
        "tz": "Europe/Lisbon",
        "generated_from_legacy_at": datetime.now(LX).isoformat(),
        "matches": matches,
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"escrito {out} ({len(matches)} jogos)")


if __name__ == "__main__":
    main()
