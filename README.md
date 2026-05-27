# 🏆 Calendário Mundial FIFA 2026

Calendário iCal subscritível do Mundial FIFA 2026 (Canadá, México, EUA) com horas em **Europe/Lisbon** e canais de transmissão em Portugal.

📅 **Página oficial:** https://tdsf.github.io/mundial-2026/

🔗 **URL para subscrever:**
```
https://tdsf.github.io/mundial-2026/mundial-2026.ics
```

Eventos no formato `🇵🇹 x 🇧🇷 - Portugal vs Brasil (Grupo K)`.

## Como subscrever

### Google Calendar
1. Em **Outros calendários** clica no `+` → **De URL**
2. Cola o link e adiciona

### Apple Calendar (iPhone/iPad)
1. **Definições → Calendário → Contas → Adicionar conta → Outra**
2. **Adicionar calendário subscrito** → cola o URL

### Apple Calendar (Mac)
1. Menu **Ficheiro → Nova subscrição de calendário**
2. Cola o URL

### Outlook (Web)
1. **Adicionar calendário → Subscrever da Web**
2. Cola o URL e dá um nome

## Conteúdo

- 104 jogos (72 fase de grupos + 32 mata-mata)
- Horas em Lisboa (já com DST)
- Estádios e localização oficial FIFA
- Canais portugueses (Sport TV, RTP, Livemode)
- Jogos com horário ainda por confirmar (knockouts) ficam como evento de dia inteiro

## Atualizações

Os calendários subscritos atualizam automaticamente. Quando os emparelhamentos dos knockouts forem definidos pela FIFA, o ficheiro será atualizado e os eventos vão refletir os jogos reais.

## Para desenvolvedores

```
data/teams.json      mapa nome PT → ISO + emoji bandeira
data/matches.json    104 jogos (fonte da verdade)
scripts/generate.py  lê os JSONs e gera docs/mundial-2026.ics + docs/index.html
scripts/parse_legacy.py  one-shot: converte ICS legacy em matches.json
```

Regerar local:
```bash
python3 scripts/generate.py
```

CI: cada push que toque em `data/` ou `scripts/` corre o generator e committa `docs/`.

## Fontes

- **Calendário e estádios:** [FIFA](https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/schedule)
- **Canais portugueses:** [A Bola](https://www.abola.pt/)
- **Inspiração / dados iniciais:** [jpgcc/calendario-mundial-2026](https://github.com/jpgcc/calendario-mundial-2026) (CC0)

## Licença

[CC0 1.0 Universal](LICENSE) — domínio público, faz o que quiseres.
