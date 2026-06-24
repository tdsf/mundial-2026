"""Gera docs/mundial-2026.ics e docs/index.html a partir de data/matches.json + data/teams.json.

Sem dependências externas — usa apenas stdlib.
"""
from __future__ import annotations

import html
import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DOCS = ROOT / "docs"

LX = ZoneInfo("Europe/Lisbon")
SUB_URL = "https://tdsf.github.io/mundial-2026/mundial-2026.ics"
REPO_URL = "https://github.com/tdsf/mundial-2026"

GENERIC_FLAG = "🏳️"


def load() -> tuple[dict, list[dict], dict]:
    teams = json.loads((DATA / "teams.json").read_text(encoding="utf-8"))
    teams.pop("_comment", None)
    payload = json.loads((DATA / "matches.json").read_text(encoding="utf-8"))
    channels = json.loads((DATA / "channels_pt.json").read_text(encoding="utf-8"))["channels"]
    return teams, payload["matches"], channels


def flag_for(team: str, teams: dict) -> str:
    return teams.get(team, {}).get("flag", GENERIC_FLAG)


def score_segment(m: dict) -> str:
    """'x' por defeito, 'sh-sa' quando o jogo já jogou ou está live."""
    if m.get("status") in ("live", "final") and m.get("score_home") is not None and m.get("score_away") is not None:
        return f"{m['score_home']}-{m['score_away']}"
    return "x"


def event_title(m: dict, teams: dict) -> str:
    """Formato: 🇵🇹 2-1 🇧🇷 - Portugal vs Brasil (Grupo K) [🔴 LIVE]"""
    fh, fa = flag_for(m["home"], teams), flag_for(m["away"], teams)
    sep = score_segment(m)
    base = f"{fh} {sep} {fa} - {m['home']} vs {m['away']}"
    if m["stage"] == "group":
        title = f"{base} (Grupo {m['group']})"
    elif m["stage"] == "final":
        title = f"🏆 FINAL — {fh} {sep} {fa} - {m['home']} vs {m['away']}"
    else:
        title = f"{base} ({m['stage_label_pt']})"
    if m.get("status") == "live":
        title += " 🔴 LIVE"
    return title


def parse_kickoff(m: dict) -> datetime:
    kickoff = m["kickoff_local"]
    if "T" not in kickoff:
        kickoff = kickoff + "T00:00:00+01:00"
    return datetime.fromisoformat(kickoff)


# ---------- ICS ----------

ICS_HEADER = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//tdsf//mundial-2026//PT
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-CALNAME:Mundial 2026
X-WR-CALDESC:Calendário do Mundial FIFA 2026 (fonte: FIFA). Horas em Lisboa\\, com canais portugueses.
X-WR-TIMEZONE:Europe/Lisbon
REFRESH-INTERVAL;VALUE=DURATION:PT12H
X-PUBLISHED-TTL:PT12H
BEGIN:VTIMEZONE
TZID:Europe/Lisbon
BEGIN:STANDARD
DTSTART:19701025T020000
RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU
TZOFFSETFROM:+0100
TZOFFSETTO:+0000
TZNAME:WET
END:STANDARD
BEGIN:DAYLIGHT
DTSTART:19700329T010000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU
TZOFFSETFROM:+0000
TZOFFSETTO:+0100
TZNAME:WEST
END:DAYLIGHT
END:VTIMEZONE
"""


def ics_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")


def fold(line: str) -> str:
    """RFC5545: linhas máximas de 75 octetos. Para simplicidade dividimos em 73 chars."""
    raw = line.encode("utf-8")
    if len(raw) <= 75:
        return line
    out = []
    chunk = bytearray()
    for b in raw:
        chunk.append(b)
        if len(chunk) >= 73:
            # garantir que não cortamos no meio de um char UTF-8
            while chunk and (chunk[-1] & 0xC0) == 0x80:
                chunk.pop()
            out.append(chunk.decode("utf-8", errors="ignore"))
            chunk = bytearray()
    if chunk:
        out.append(chunk.decode("utf-8", errors="ignore"))
    return out[0] + "".join("\r\n " + c for c in out[1:])


def emit_event(m: dict, teams: dict, channels: dict) -> str:
    uid = f"mundial2026-{m['id']:03d}@tdsf.github.io"
    dtstamp = datetime.now(tz=ZoneInfo("UTC")).strftime("%Y%m%dT%H%M%SZ")
    summary = event_title(m, teams)
    desc_lines: list[str] = []
    if m["stage"] == "group":
        desc_lines.append(f"Mundial FIFA 2026 — Fase de Grupos, Grupo {m['group']}.")
    elif m["stage"] == "final":
        desc_lines.append("Mundial FIFA 2026 — FINAL.")
    else:
        desc_lines.append(f"Mundial FIFA 2026 — {m['stage_label_pt']} (jogo {m['id']}).")
    if m["simultaneous"]:
        desc_lines[-1] = desc_lines[-1][:-1] + " (jornada simultânea)."
    if m["all_day"]:
        desc_lines.append("Hora a confirmar.")
    if m.get("status") in ("live", "final") and m.get("score_home") is not None:
        label = "Resultado" if m["status"] == "final" else "Em jogo"
        desc_lines.append(f"{label}: {m['home']} {m['score_home']}–{m['score_away']} {m['away']}.")
    chs = channels.get(str(m["id"]), [])
    if chs:
        desc_lines.append("Transmissão: " + ", ".join(chs) + ".")
    desc_lines.append(f"Fonte: ESPN/FIFA — {REPO_URL}")
    description = "\n".join(desc_lines)

    location = m["location"]
    cats = list(m["categories"])
    if "Portugal" in (m["home"], m["away"]) and "Portugal" not in cats:
        cats.append("Portugal")

    lines = [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{dtstamp}",
    ]
    start = parse_kickoff(m)
    end = start + timedelta(hours=2)
    lines.append(f"DTSTART;TZID=Europe/Lisbon:{start.strftime('%Y%m%dT%H%M%S')}")
    lines.append(f"DTEND;TZID=Europe/Lisbon:{end.strftime('%Y%m%dT%H%M%S')}")
    lines.append(f"SUMMARY:{ics_escape(summary)}")
    lines.append(f"DESCRIPTION:{ics_escape(description)}")
    lines.append(f"LOCATION:{ics_escape(location)}")
    lines.append(f"CATEGORIES:{','.join(ics_escape(c) for c in cats)}")
    lines.append("END:VEVENT")
    return "\r\n".join(fold(l) for l in lines) + "\r\n"


def write_ics(matches: list[dict], teams: dict, channels: dict) -> None:
    out = DOCS / "mundial-2026.ics"
    parts = [ICS_HEADER.replace("\n", "\r\n")]
    for m in matches:
        parts.append(emit_event(m, teams, channels))
    parts.append("END:VCALENDAR\r\n")
    out.write_text("".join(parts), encoding="utf-8")
    print(f"escrito {out.relative_to(ROOT)} ({len(matches)} eventos)")


# ---------- HTML ----------

PAGE_TMPL = """<!doctype html>
<html lang="pt-PT">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Calendário Mundial FIFA 2026 — subscrever</title>
<meta name="description" content="Calendário oficial do Mundial FIFA 2026 para subscrever no Google Calendar, Apple Calendar ou Outlook. Horas em Lisboa, canais portugueses.">
<link rel="stylesheet" href="style.css">
</head>
<body>
<header>
  <h1>🏆 Mundial FIFA 2026</h1>
  <p class="lede">Calendário completo dos 104 jogos, com horas em Lisboa e canais portugueses, para subscrever no teu calendário.</p>
  <div class="sub-box">
    <code id="sub-url">{sub_url}</code>
    <button type="button" id="copy-btn" data-url="{sub_url}">Copiar URL</button>
  </div>
  <div class="quick">
    <a class="btn" href="webcal://tdsf.github.io/mundial-2026/mundial-2026.ics">Apple Calendar</a>
    <a class="btn" href="https://calendar.google.com/calendar/r?cid={sub_url}">Google Calendar</a>
    <a class="btn" href="https://outlook.live.com/calendar/0/addcalendar?url={sub_url}&name=Mundial%202026">Outlook</a>
  </div>
</header>

<section>
  <h2>Como subscrever</h2>
  <details open>
    <summary>Google Calendar</summary>
    <ol><li>Em "Outros calendários" carrega no <strong>+</strong>.</li><li>Escolhe <em>De URL</em> e cola o link acima.</li></ol>
  </details>
  <details>
    <summary>Apple Calendar (iPhone/iPad)</summary>
    <ol><li>Definições → Calendário → Contas → <em>Adicionar conta</em>.</li><li>Outra → <em>Adicionar calendário subscrito</em> e cola o URL.</li></ol>
  </details>
  <details>
    <summary>Apple Calendar (Mac)</summary>
    <ol><li>Menu Ficheiro → <em>Nova subscrição de calendário</em>.</li><li>Cola o URL.</li></ol>
  </details>
  <details>
    <summary>Outlook (Web)</summary>
    <ol><li>"Adicionar calendário" → <em>Subscrever da Web</em>.</li><li>Cola o URL e dá um nome.</li></ol>
  </details>
</section>

<section>
  <h2>Todos os jogos ({n})</h2>
  <p class="note">Hora local de Lisboa. Jogos de Portugal destacados.</p>
  {tables}
</section>

<footer>
  <p><strong>Fontes:</strong> calendário, equipas e resultados via <a href="https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard">ESPN</a>; estádios oficiais da <a href="h[...]
  <p>Licença CC0 · <a href="{repo}">código no GitHub</a> · gerado em {gen}</p>
</footer>

<script>
document.getElementById('copy-btn').addEventListener('click', async (e) => {{
  const url = e.target.dataset.url;
  try {{ await navigator.clipboard.writeText(url); e.target.textContent = '✓ Copiado'; setTimeout(() => e.target.textContent = 'Copiar URL', 1500); }}
  catch {{ window.prompt('Copia o URL:', url); }}
}});
</script>
</body>
</html>
"""


def render_match_row(m: dict, teams: dict, channels: dict) -> str:
    is_pt = "Portugal" in (m["home"], m["away"])
    fh, fa = flag_for(m["home"], teams), flag_for(m["away"], teams)
    if m["all_day"]:
        hora = "—"
    else:
        hora = parse_kickoff(m).strftime("%H:%M")
    stage = m["stage_label_pt"] or ""
    if m["stage"] == "final":
        stage = "FINAL 🏆"
    if m.get("status") in ("live", "final") and m.get("score_home") is not None:
        sep = f'<strong class="score">{m["score_home"]}–{m["score_away"]}</strong>'
        if m["status"] == "live":
            sep += ' <span class="live">🔴 LIVE</span>'
    else:
        sep = '<span class="vs">vs</span>'
    teams_html = f'<span class="flag">{html.escape(fh)}</span> {html.escape(m["home"])} {sep} <span class="flag">{html.escape(fa)}</span> {html.escape(m["away"])}'
    chs = channels.get(str(m["id"]), [])
    channels_html = ", ".join(html.escape(c) for c in chs) or "—"
    cls = "match pt" if is_pt else "match"
    return (
        f'<tr class="{cls}">'
        f'<td class="hora">{hora}</td>'
        f'<td class="teams">{teams_html}</td>'
        f'<td class="stage">{html.escape(stage)}</td>'
        f'<td class="loc">{html.escape(m["location"])}</td>'
        f'<td class="ch">{channels_html}</td>'
        f'</tr>'
    )


WEEKDAYS_PT = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
MONTHS_PT = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def fmt_date(d) -> str:
    return f"{WEEKDAYS_PT[d.weekday()]}, {d.day} {MONTHS_PT[d.month - 1]} {d.year}"


def render_tables(matches: list[dict], teams: dict, channels: dict) -> str:
    # agrupar por data Lisboa
    groups: dict = {}
    for m in matches:
        dt = parse_kickoff(m)
        key = dt.date()
        groups.setdefault(key, []).append(m)

    parts = []
    for day in sorted(groups):
        rows = "\n".join(render_match_row(m, teams, channels) for m in groups[day])
        parts.append(
            f"<h3>{fmt_date(day)}</h3>"
            f'<table class="matches"><thead><tr>'
            f'<th>Hora</th><th>Jogo</th><th>Fase</th><th>Local</th><th>Canais PT</th>'
            f'</tr></thead><tbody>{rows}</tbody></table>'
        )
    return "\n".join(parts)


def write_html(matches: list[dict], teams: dict, channels: dict) -> None:
    out = DOCS / "index.html"
    page = PAGE_TMPL.format(
        sub_url=SUB_URL,
        repo=REPO_URL,
        n=len(matches),
        tables=render_tables(matches, teams, channels),
        gen=datetime.now(LX).strftime("%Y-%m-%d %H:%M %Z"),
    )
    out.write_text(page, encoding="utf-8")
    print(f"escrito {out.relative_to(ROOT)}")


def main() -> None:
    DOCS.mkdir(exist_ok=True)
    teams, matches, channels = load()
    write_ics(matches, teams, channels)
    write_html(matches, teams, channels)


if __name__ == "__main__":
    main()
