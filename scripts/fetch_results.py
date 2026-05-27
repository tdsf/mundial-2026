"""Busca scoreboard da ESPN e actualiza data/matches.json com scores/status/external_id.

Stdlib only.

Estratégia:
- 1 GET ao scoreboard com `dates=20260611-20260720&limit=200` devolve os 104 jogos.
- Para cada evento ESPN: matchar por external_id_espn (se já conhecido) ou por
  (data Lisboa, par de espn_abbr home/away) caso contrário.
- Update apenas: external_id_espn, score_home, score_away, status. Para knockouts,
  substituir home/away pelo nome PT se a ESPN já tiver equipa real (abbr ∈ teams.json).
"""
from __future__ import annotations

import json
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
LX = ZoneInfo("Europe/Lisbon")
UTC = ZoneInfo("UTC")

URL = (
    "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"
    "?dates=20260611-20260720&limit=200"
)

STATUS_MAP = {
    "STATUS_SCHEDULED": "scheduled",
    "STATUS_IN_PROGRESS": "live",
    "STATUS_HALFTIME": "live",
    "STATUS_FIRST_HALF": "live",
    "STATUS_SECOND_HALF": "live",
    "STATUS_END_PERIOD": "live",
    "STATUS_FULL_TIME": "final",
    "STATUS_FINAL": "final",
    "STATUS_POSTPONED": "postponed",
    "STATUS_CANCELED": "canceled",
    "STATUS_DELAYED": "delayed",
}


def fetch() -> dict:
    req = urllib.request.Request(URL, headers={"User-Agent": "mundial-2026/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def normalize_status(name: str) -> str:
    return STATUS_MAP.get(name, "scheduled")


def parse_int(s):
    if s is None or s == "":
        return None
    try:
        return int(s)
    except (TypeError, ValueError):
        return None


def main() -> int:
    teams = json.loads((DATA / "teams.json").read_text(encoding="utf-8"))
    teams.pop("_comment", None)
    abbr_to_pt = {v["espn_abbr"]: name for name, v in teams.items() if "espn_abbr" in v}

    payload = json.loads((DATA / "matches.json").read_text(encoding="utf-8"))
    matches = payload["matches"]

    by_external = {m["external_id_espn"]: m for m in matches if m.get("external_id_espn")}
    # Index por (data Lisboa YYYY-MM-DD, frozenset({abbr1, abbr2}))
    by_date_pair: dict[tuple[str, frozenset[str]], dict] = {}
    for m in matches:
        h_abbr = teams.get(m["home"], {}).get("espn_abbr")
        a_abbr = teams.get(m["away"], {}).get("espn_abbr")
        if not (h_abbr and a_abbr):
            continue
        if m["all_day"]:
            d = m["kickoff_local"][:10]
        else:
            d = datetime.fromisoformat(m["kickoff_local"]).astimezone(LX).date().isoformat()
        by_date_pair[(d, frozenset({h_abbr, a_abbr}))] = m

    data = fetch()
    events = data.get("events", [])
    print(f"ESPN devolveu {len(events)} eventos")

    matched = updated = teams_filled = 0
    for ev in events:
        eid = ev["id"]
        comp = ev["competitions"][0]
        competitors = comp["competitors"]
        home_c = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
        away_c = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])
        h_abbr = home_c["team"].get("abbreviation", "")
        a_abbr = away_c["team"].get("abbreviation", "")
        status = normalize_status(comp["status"]["type"]["name"])
        sh = parse_int(home_c.get("score"))
        sa = parse_int(away_c.get("score"))
        # Para scheduled, scores 0 não significam nada — força None.
        if status == "scheduled":
            sh = sa = None

        # 1. lookup por external_id
        m = by_external.get(eid)
        # 2. lookup por (data Lisboa, par de abbrs)
        if m is None and h_abbr in abbr_to_pt and a_abbr in abbr_to_pt:
            d_lx = datetime.fromisoformat(ev["date"].replace("Z", "+00:00")).astimezone(LX).date().isoformat()
            m = by_date_pair.get((d_lx, frozenset({h_abbr, a_abbr})))
        if m is None:
            # Knockout sem equipas resolvidas ainda → match por ordem ESPN não é fiável,
            # então skip. Os eventos do calendário ficam intactos.
            continue

        matched += 1
        # Para knockouts: se a ESPN já tem nome real, sobrepor
        if m["stage"] != "group" and h_abbr in abbr_to_pt and a_abbr in abbr_to_pt:
            pt_home = abbr_to_pt[h_abbr]
            pt_away = abbr_to_pt[a_abbr]
            if m["home"] != pt_home or m["away"] != pt_away:
                m["home"] = pt_home
                m["away"] = pt_away
                teams_filled += 1

        new_fields = {
            "external_id_espn": eid,
            "score_home": sh,
            "score_away": sa,
            "status": status,
        }
        if any(m.get(k) != v for k, v in new_fields.items()):
            m.update(new_fields)
            updated += 1

    payload["last_fetch"] = datetime.now(UTC).isoformat()
    (DATA / "matches.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"matched={matched} updated={updated} teams_filled={teams_filled}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
