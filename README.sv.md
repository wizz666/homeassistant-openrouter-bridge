# Home Assistant OpenRouter Bridge

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![HA Version](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue)](https://www.home-assistant.io)
[![Version](https://img.shields.io/badge/Version-1.1.1-green)](https://github.com/wizz666/homeassistant-openrouter-bridge/releases)
[![Ko-fi](https://img.shields.io/badge/Ko--fi-Stöd_projektet-F16061?logo=ko-fi&logoColor=white)](https://ko-fi.com/wizz666)

**[🇬🇧 English → README.md](README.md)**

En Anthropic-kompatibel API-proxy byggd direkt i Home Assistant. Peka **Claude Code CLI** mot din HA-instans och använd valfri av OpenRouters 300+ modeller — inklusive gratis sådana — via en **inbyggd webbläsarterminal** eller från valfri maskin i nätverket.

---

## Vad det gör

Claude Code CLI talar Anthropics API-protokoll. OpenRouter talar OpenAIs protokoll. Den här integrationen översätter dem emellan — körs helt inuti Home Assistant, ingen extra server behövs.

```
Claude Code CLI  (eller inbyggd terminal)
    │  POST /api/openrouter_bridge/v1/messages  (Anthropic-format)
    ▼
Home Assistant – OpenRouter Bridge
    • Översätter Anthropic → OpenAI-format i realtid
    • Väljer aktiv modell från HA-dashboardens dropdown
    │  POST https://openrouter.ai/api/v1/chat/completions
    ▼
OpenRouter (300+ modeller, inklusive gratis)
    │  Svar översatt tillbaka till Anthropic-format
    ▼
Claude Code CLI
```

---

## Funktioner

- **Anthropic-kompatibelt endpoint** i HA:s egna HTTP-server — inga extra portar eller containrar
- **Inbyggd webbläsarterminal** — komplett xterm.js-terminal med Claude Code direkt i webbläsaren
- **Modellbyte med ett klick** — byt modell från HA-dashboardens dropdown, ingen omstart behövs
- **`openrouter/free` auto-router** — väljer alltid den bäst tillgängliga fria modellen automatiskt
- **Full tool-use-stöd** — Claude Codes bash-exekvering, filredigering och alla inbyggda verktyg fungerar
- **Realtidsstreaming** — token-för-token output
- **Tydliga felmeddelanden** — visar det faktiska OpenRouter-felet (rate limit, fel nyckel, m.m.)
- **Användningssensorer** — requesträknare, senast använd modell, antal tillgängliga modeller
- **Fungerar externt** — åtkomst via Nabu Casa eller omvänd proxy

---

## Krav

- Home Assistant 2024.1+
- En OpenRouter API-nyckel — gratis på [openrouter.ai/keys](https://openrouter.ai/keys)
- **Enbart för inbyggd terminal:** Claude Code-binären kopierad till `/config/claude_bin` (se [Terminalsetup](#terminalsetup))

---

## Installation

### Alternativ A – Manuell

1. Kopiera `custom_components/openrouter_bridge/` till din HA:s `custom_components/`-mapp
2. Starta om Home Assistant
3. Gå till **Inställningar → Enheter och tjänster → Lägg till integration → OpenRouter Bridge**
4. Fyll i din OpenRouter API-nyckel

### Alternativ B – HACS (anpassad repo)

1. I HACS → **Anpassade repositorier** → lägg till `https://github.com/wizz666/homeassistant-openrouter-bridge` som typ **Integration**
2. Installera **OpenRouter Bridge** och starta om Home Assistant
3. Lägg till integrationen via **Inställningar → Enheter och tjänster**

---

## Konfiguration

Vid installation anger du bara din OpenRouter API-nyckel (`sk-or-v1-...`). Aktiv modell styrs från dashboarden, inte från konfigurationen.

---

## Dashboard & Modellväljare (Rekommenderat)

Mappen `extras/` innehåller färdiga YAML-filer som lägger till en komplett dashboard med modellväljare och terminalknapp.

### Steg 1 — Lägg till paketet

Kopiera `extras/package_openrouter_bridge.yaml` till din `packages/`-mapp (skapa den om den saknas), lägg sedan till i `configuration.yaml`:

```yaml
homeassistant:
  packages: !include_dir_named packages
```

Detta skapar:
- `input_select.openrouter_bridge_model` — dropdown för att välja aktiv modell
- `input_text.openrouter_bridge_workspace` — arbetsmapp för terminalsessioner

### Steg 2 — Lägg till dashboarden

Kopiera `extras/dashboard_openrouter_bridge.yaml` till din `dashboards/`-mapp, lägg sedan till i `configuration.yaml`:

```yaml
lovelace:
  dashboards:
    openrouter-bridge-dashboard:
      mode: yaml
      filename: dashboards/openrouter_bridge.yaml
      title: OpenRouter Bridge
      icon: mdi:robot
      show_in_sidebar: true
      require_admin: false
```

Starta om Home Assistant. **OpenRouter Bridge** syns i sidomenyn.

---

## Välja modell

Aktiv modell styrs av `input_select.openrouter_bridge_model`-dropdownen i dashboarden. Byt när som helst — nästa request använder den nya modellen direkt.

> **Öppna alltid en ny terminal-session efter modellbyte** så att `--model`-flaggan som skickas till Claude Code stämmer.

### Gratismodeller

Gratis modeller kräver inga OpenRouter-credits. De körs på delad infrastruktur, vilket innebär att de kan vara **temporärt rate-limitade** (HTTP 429) under hög belastning — det är normalt och löser sig av sig självt. Lösningen är att använda `openrouter/free` som automatiskt väljer den fria modell som har kapacitet just nu.

| Modell-ID | Noteringar |
|-----------|-----------|
| **`openrouter/free`** | **Rekommenderat — väljer automatiskt bästa tillgängliga fria modell** |
| `meta-llama/llama-3.3-70b-instruct:free` | Bästa specifika gratismodellen för Claude Code |
| `google/gemma-3-27b-it:free` | Bra alternativ |
| `mistralai/mistral-small-3.1-24b-instruct:free` | Snabb och lättviktig |
| `nousresearch/hermes-3-llama-3.1-405b:free` | Stark tool-use-modell |

> ⚠️ **Viktigt:** Claude Code kräver **tool-use-stöd** i modellen (bash, filredigering m.m. körs via function calling). Reasoning-modeller som DeepSeek R1 och o1 stödjer **inte** tool use och kommer att misslyckas. Använd alltid instruct- eller chat-varianter.

### Betalmodeller

Betalmodeller kräver OpenRouter-credits ([openrouter.ai/credits](https://openrouter.ai/credits)). Redan $5 räcker länge med effektiva modeller.

| Modell-ID | Noteringar |
|-----------|-----------|
| `anthropic/claude-3.5-sonnet` | Bäst totalt för Claude Code |
| `anthropic/claude-3.5-haiku` | Snabb och prisvärd |
| `anthropic/claude-3-opus` | Mest kapabel Claude 3-modell |
| `google/gemini-2.0-flash-001` | Snabb och mycket prisvärd |
| `google/gemini-2.5-pro-preview-03-25` | Senaste Gemini, hög kapabilitet |
| `openai/gpt-4o` | OpenAIs flaggskepp |
| `openai/gpt-4o-mini` | Prisvärd GPT-4-klass |
| `meta-llama/llama-3.3-70b-instruct` | Bästa open-source betalmodellen |
| `deepseek/deepseek-chat-v3-0324` | Utmärkt resonemang, mycket prisvärd |

Lägg till valfri modell från OpenRouters katalog på [openrouter.ai/models](https://openrouter.ai/models) i `extras/package_openrouter_bridge.yaml`.

---

## Gratis-tier begränsningar

OpenRouters gratisnivå har dessa gränser:

| Villkor | Requests/dag |
|---------|-------------|
| Inga credits någonsin tillagda | ~50 req/dag |
| Minst lite credits tillagda | ~200 req/dag |
| Negativt saldo | 0 — HTTP 402 även för gratis-modeller |

Claude Code kan generera många requests per session (varje verktygsanrop är en request). Vid limit, vänta till nästa dag eller lägg till ett litet credits-saldo.

`openrouter/free`-routern väljer automatiskt en modell som **inte är rate-limitad just nu**, vilket ger bäst chans att få ett svar även under topptider.

---

## Inbyggd terminal

Klicka på **Öppna Terminal** i dashboarden och Claude Code startar direkt i webbläsaren — vald modell skickas automatiskt, ingen shell-konfiguration behövs.

### Hur det fungerar

```
Webbläsare (xterm.js) ←── WebSocket ──→ HA PTY-hanterare ←── PTY ──→ /config/claude_bin
```

- WebSocket ansluter till `/api/openrouter_bridge/terminal/ws`
- HA startar Claude Code-binären i en PTY med rätt miljövariabler
- Tangenttryckningar och output flödar via WebSocket i realtid
- Terminalstorlek vidarebefordras automatiskt till PTY:n
- Aktiv modell från `input_select.openrouter_bridge_model` skickas som `--model`
- Workspace från `input_text.openrouter_bridge_workspace` är arbetsmappen

### Terminalsetup

Terminalen kräver Claude Code-binären inuti HA core-containern. Kopiera den från Claude Code add-on-containern till den delade `/config/`-volymen:

**Steg 1 — Hitta binären (i Claude Code add-on-terminalen):**

```bash
which claude
# t.ex. /root/.local/share/claude/versions/2.x.x/claude
```

**Steg 2 — Kopiera till delad volym:**

```bash
cp $(which claude) /config/claude_bin
chmod +x /config/claude_bin
```

**Steg 3 — Verifiera:**

```bash
/config/claude_bin --version
```

> Upprepa steg 2 när du uppdaterar Claude Code.

### Miljövariabler som sätts automatiskt

| Variabel | Värde | Syfte |
|----------|-------|-------|
| `ANTHROPIC_BASE_URL` | `http(s)://<din-ha>/api/openrouter_bridge` | Pekar Claude mot proxyn |
| `ANTHROPIC_AUTH_TOKEN` | Din OpenRouter API-nyckel | Autentisering |
| `ANTHROPIC_API_KEY` | `""` (tom) | Måste vara tom per OpenRouter-docs |
| `TERM` | `xterm-256color` | Fullt färgstöd |

---

## Claude Code-setup (extern maskin)

```bash
export ANTHROPIC_BASE_URL=http://<din-ha-ip>:8123/api/openrouter_bridge
export ANTHROPIC_AUTH_TOKEN=sk-or-v1-din-openrouter-nyckel
export ANTHROPIC_API_KEY=
claude
```

Permanent setup i shell-profil (`~/.bashrc`, `~/.zshrc`):

```bash
# Claude Code via Home Assistant OpenRouter Bridge
export ANTHROPIC_BASE_URL=http://192.168.1.100:8123/api/openrouter_bridge
export ANTHROPIC_AUTH_TOKEN=sk-or-v1-din-openrouter-nyckel
export ANTHROPIC_API_KEY=
```

> Använd `ANTHROPIC_AUTH_TOKEN`, inte `ANTHROPIC_API_KEY`, per [OpenRouter-docs](https://openrouter.ai/docs).

**Verifiera:**
```bash
curl http://<ha-ip>:8123/api/openrouter_bridge
# → {"status": "ok", "default_model": "...", "total_requests": 0}
```

---

## API-endpoints

| Endpoint | Metod | Beskrivning |
|----------|-------|-------------|
| `/api/openrouter_bridge` | GET | Status, aktuell modell, antal requests |
| `/api/openrouter_bridge/v1/messages` | POST | Anthropic Messages API-proxy |
| `/api/openrouter_bridge/v1/models` | GET | Alla tillgängliga OpenRouter-modeller |
| `/api/openrouter_bridge/terminal` | GET | Inbyggd terminal HTML-sida |
| `/api/openrouter_bridge/terminal/ws` | WS | Terminal WebSocket-backend |

---

## Sensorer

| Sensor | Beskrivning |
|--------|-------------|
| `sensor.openrouter_bridge_status` | `ok` / `invalid_key` / `unconfigured` |
| `sensor.openrouter_bridge_total_requests` | Requests proxierade denna session |
| `sensor.openrouter_bridge_available_models` | Antal tillgängliga modeller på OpenRouter |
| `sensor.openrouter_bridge_last_used_model` | Modell-ID använt i senaste requesten |

---

## Felsökning

**"❌ Kunde inte starta claude" i terminalen**
→ Binären saknas. Följ [Terminalsetup](#terminalsetup) för att kopiera den till `/config/claude_bin`.

**`[OpenRouter 429] temporarily rate-limited upstream`**
→ Den specifika fria modellen är överbelastad just nu. Byt till `openrouter/free` (väljer automatiskt en tillgänglig) eller försök om några minuter.

**`[OpenRouter 402] insufficient credits`**
→ Ditt kontosaldo är negativt. Lägg till credits på [openrouter.ai/credits](https://openrouter.ai/credits) eller använd bara gratis-modeller med positivt saldo.

**Modell svarar inte eller verkar fel**
→ Se till att du använder en modell med tool-use-stöd. Använd `openrouter/free` eller `meta-llama/llama-3.3-70b-instruct:free` för bäst resultat.

**Modellbyte verkar inte ha effekt**
→ Öppna en **ny terminal-session** efter att ha bytt i dropdownen.

**Terminalen ansluter men Claude svarar inte**
→ Kör `/status` inne i Claude Code för att verifiera `ANTHROPIC_BASE_URL` och auth-token. Kör `/logout` om du tidigare loggat in med Anthropic-credentials.

**Proxystatussensorn visar `invalid_key`**
→ Ange om nyckeln via **Inställningar → Enheter och tjänster → OpenRouter Bridge → Konfigurera**.

---

## Stöd projektet

Gillar du det här projektet? En kopp kaffe uppskattas ☕

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/wizz666)

---

## Licens

MIT — se [LICENSE](LICENSE)
