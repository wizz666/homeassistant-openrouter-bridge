# Home Assistant OpenRouter Bridge

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![HA Version](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue)](https://www.home-assistant.io)
[![Version](https://img.shields.io/badge/Version-1.1.0-green)](https://github.com/wizz666/homeassistant-openrouter-bridge/releases)
[![Ko-fi](https://img.shields.io/badge/Ko--fi-Stöd_projektet-F16061?logo=ko-fi&logoColor=white)](https://ko-fi.com/wizz666)

**[🇬🇧 English → README.md](README.md)**

En Anthropic-kompatibel API-proxy byggd direkt i Home Assistant. Peka **Claude Code CLI** (eller valfri Anthropic SDK-klient) mot din HA-instans och använd vilken som helst av OpenRouters 300+ modeller — inklusive gratis sådana. Nu med en **inbyggd webbläsarterminal** så du kan köra Claude Code direkt från din HA-dashboard.

---

## Vad det gör

Claude Code CLI talar Anthropics API-protokoll. OpenRouter talar OpenAIs protokoll. Den här integrationen översätter dem emellan — körs helt inuti Home Assistant, ingen extra server behövs.

```
Claude Code CLI  (eller inbyggd terminal)
    │  POST /api/openrouter_bridge/v1/messages  (Anthropic-format)
    ▼
Home Assistant – OpenRouter Bridge
    • Anthropic tool use  →  OpenAI function calling
    • system-parameter    →  messages[0].role=system
    • Streaming SSE       →  översätts i realtid
    │  POST https://openrouter.ai/api/v1/chat/completions
    ▼
OpenRouter (valfri av 300+ modeller)
    │  svar översatt tillbaka till Anthropic-format
    ▼
Claude Code CLI
```

---

## Funktioner

- **Anthropic-kompatibelt endpoint** i HA:s egna HTTP-server — inga extra containrar eller portar
- **Inbyggd webbläsarterminal** — komplett xterm.js-terminal som kör Claude Code direkt i webbläsaren
- **Modellbyte med ett klick** — byt modell från HA-dashboarden utan att starta om någonting
- **Full tool use-stöd** — Claude Codes bash-exekvering, filredigering och alla inbyggda verktyg fungerar
- **Streaming** — token-för-token svar i realtid
- **Modellistning** — `GET /v1/models` returnerar alla tillgängliga OpenRouter-modeller
- **300+ modeller** — Claude, Gemini, GPT-4o, Llama, Mistral, DeepSeek med mera
- **Gratis modeller** — flera kapabla modeller utan kostnad
- **Användningssensorer** — antal requests, senast använd modell, tillgängliga modeller
- **Fungerar externt** — åtkomst via din HA externa URL (Nabu Casa eller omvänd proxy)

---

## Krav

- Home Assistant 2024.1+
- En OpenRouter API-nyckel — gratis på [openrouter.ai/keys](https://openrouter.ai/keys)
- **Enbart för inbyggd terminal:** Claude Code CLI-binären kopierad till `/config/claude_bin` (se [Terminalsetup](#terminalsetup))

---

## Installation

### Alternativ A – Manuell

1. Kopiera `custom_components/openrouter_bridge/` till din HA:s `custom_components/`-mapp
2. Starta om Home Assistant
3. Gå till **Inställningar → Enheter och tjänster → Lägg till integration → OpenRouter Bridge**
4. Fyll i din OpenRouter API-nyckel

### Alternativ B – HACS (anpassad repo)

1. I HACS → **Anpassade repositorier** → lägg till `https://github.com/wizz666/homeassistant-openrouter-bridge` som typ **Integration**
2. Sök efter **OpenRouter Bridge** och installera
3. Starta om Home Assistant
4. Lägg till integrationen via **Inställningar → Enheter och tjänster**

---

## Konfiguration

Under installationen (eller via **Konfigurera** på integrationskortet) anger du:

| Fält | Beskrivning |
|------|-------------|
| **OpenRouter API-nyckel** | Din `sk-or-v1-...`-nyckel från openrouter.ai/keys |

Det är allt. Modellen styrs från dashboarden (se nedan), inte från konfigurationen.

---

## Dashboard & Modellväljare (valfritt men rekommenderat)

Mappen `extras/` innehåller två filer som lägger till en komplett dashboard med modellväljare och terminalknapp.

### 1 – Lägg till paketet (input-helpers)

Kopiera `extras/package_openrouter_bridge.yaml` till din HA:s `packages/`-mapp (skapa den om den saknas), lägg sedan till i `configuration.yaml`:

```yaml
homeassistant:
  packages: !include_dir_named packages
```

Detta skapar:
- `input_select.openrouter_bridge_model` — dropdown för att välja aktiv modell
- `input_text.openrouter_bridge_workspace` — arbetsmappen för terminalsessioner

### 2 – Lägg till dashboarden

Kopiera `extras/dashboard_openrouter_bridge.yaml` till din HA:s `dashboards/`-mapp, lägg sedan till i `configuration.yaml`:

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

Starta om Home Assistant. En ny **OpenRouter Bridge**-post dyker upp i sidomenyn.

### Dashboardöversikt

Dashboarden innehåller:
- **Statusrad** — live-sensorer: proxystatus, antal requests, tillgängliga modeller, senast använd modell
- **Modellväljare** — `input_select`-dropdown för att välja bland de förkonfigurerade modellerna
- **Workspace-fält** — mappen Claude Code använder som arbetsmapp (standard: `/config/claude_workspace`)
- **Öppna Terminal**-knapp — öppnar den inbyggda Claude-terminalen i en ny flik
- **Snabblänkar** — OpenRouter Activity, Credits, Keys, Models
- **API-endpoint-referens**

---

## Välja modell

Den aktiva modellen styrs av `input_select.openrouter_bridge_model`. Ändra den i dashboarden och nästa request använder automatiskt den nya modellen — ingen omstart behövs.

Bryggan skickar `--model <vald>` till Claude Code i terminalen och vidarebefordrar modell-ID:t i API-request-headern till OpenRouter.

### Förkonfigurerade modeller (redigera `package_openrouter_bridge.yaml` för att lägga till fler)

**Gratis modeller** (inga OpenRouter-credits behövs):

| Modell-ID | Noteringar |
|-----------|-----------|
| `meta-llama/llama-3.3-70b-instruct:free` | Bästa gratisalternativet — snabb och kapabel |
| `google/gemma-3-27b-it:free` | Googles öppna modell |
| `deepseek/deepseek-r1:free` | Stark resonemangsförmåga, bra för komplexa uppgifter |
| `mistralai/mistral-7b-instruct:free` | Lättviktig och mycket snabb |

**Betalmodeller** (bästa Claude Code-upplevelsen):

| Modell-ID | Noteringar |
|-----------|-----------|
| `anthropic/claude-3.5-sonnet` | Bäst totalt för Claude Code |
| `anthropic/claude-3.5-haiku` | Snabb och prisvärd |
| `anthropic/claude-opus-4` | Mest kapabel, högre kostnad |
| `google/gemini-2.0-flash-001` | Snabb och billig |
| `openai/gpt-4o` | OpenAIs flaggskepp |
| `openai/gpt-4o-mini` | Prisvärd GPT-4-klass |
| `deepseek/deepseek-r1` | Utmärkt resonemangsförmåga, mycket prisvärd |

För att lägga till valfri modell från OpenRouters katalog — hitta dess ID på [openrouter.ai/models](https://openrouter.ai/models) och lägg till det i `options:`-listan i `package_openrouter_bridge.yaml`.

---

## Inbyggd terminal

Integrationen inkluderar en komplett webbläsarbaserad terminal med [xterm.js](https://xtermjs.org/). Klicka på **Öppna Terminal** i dashboarden och Claude Code startar omedelbart — rätt modell skickas automatiskt, ingen shell-konfiguration behövs.

### Hur det fungerar

```
Webbläsare (xterm.js) ←──WebSocket──→ HA WebSocket-hanterare ←──PTY──→ claude_bin
```

- Webbläsaren ansluter via WebSocket till `/api/openrouter_bridge/terminal/ws`
- HA startar `claude_bin` i en PTY (pseudo-terminal) med rätt miljövariabler
- Alla tangenttryckningar går via WebSocket till PTY:n; all output kommer tillbaka på samma väg
- Terminalstorlek (inklusive fönsterstorleksändringar) vidarebefordras till PTY:n i realtid
- Aktiv modell från `input_select.openrouter_bridge_model` skickas som `--model <id>`
- Workspace från `input_text.openrouter_bridge_workspace` är arbetsmappen

### Terminalsetup

Terminalen kräver att Claude Code-binären finns tillgänglig inuti HA core-containern. Eftersom Claude Code körs i en separat add-on-container behöver du kopiera binären till den delade `/config/`-volymen en gång:

**Steg 1 — Hitta binären i Claude Code-add-onen:**

Öppna en terminal i Claude Code-add-onen (VS Code Server, SSH, etc.) och kör:

```bash
which claude
# typiskt: /root/.local/share/claude/versions/<version>/claude
# eller: /usr/local/bin/claude
```

**Steg 2 — Kopiera den till den delade volymen:**

```bash
cp $(which claude) /config/claude_bin
chmod +x /config/claude_bin
```

**Steg 3 — Verifiera:**

```bash
/config/claude_bin --version
```

Terminalen hittar den automatiskt på `/config/claude_bin`.

> **OBS:** När du uppdaterar Claude Code, upprepa steg 2 för att hålla binären aktuell.

### Miljövariabler som sätts av terminalen

Terminalen sätter automatiskt dessa när Claude Code startas:

| Variabel | Värde | Syfte |
|----------|-------|-------|
| `ANTHROPIC_BASE_URL` | `http(s)://<din-ha-host>/api/openrouter_bridge` | Pekar Claude mot proxyn |
| `ANTHROPIC_AUTH_TOKEN` | Din OpenRouter API-nyckel från config entry | Autentisering mot OpenRouter |
| `ANTHROPIC_API_KEY` | `""` (tom) | Måste vara tom per OpenRouter-docs |
| `TERM` | `xterm-256color` | Fullt färgstöd i terminalen |

Ingen manuell miljöinställning behövs — allt konfigureras automatiskt.

### Workspace

Arbetsmappen för terminalsessioner ställs in via `input_text.openrouter_bridge_workspace` (standard: `/config/claude_workspace`). Skapa valfri mapp och ange den här. Varje session startar i den mappen.

En `CLAUDE.md`-fil i workspace-mappen plockas upp av Claude Code som projektinstruktioner. Standard-workspace inkluderar en minimal `CLAUDE.md` för att förhindra att HA:s rot-`/config/CLAUDE.md` laddas.

---

## Claude Code-setup (extern maskin)

För att använda proxyn från en annan maskin i nätverket (inte via den inbyggda terminalen):

```bash
export ANTHROPIC_BASE_URL=http://<din-ha-ip>:8123/api/openrouter_bridge
export ANTHROPIC_AUTH_TOKEN=sk-or-v1-din-openrouter-nyckel
export ANTHROPIC_API_KEY=
claude
```

Lägg till i din shell-profil (`~/.bashrc`, `~/.zshrc`) för permanent setup:

```bash
# Claude Code via Home Assistant OpenRouter Bridge
export ANTHROPIC_BASE_URL=http://192.168.1.100:8123/api/openrouter_bridge
export ANTHROPIC_AUTH_TOKEN=sk-or-v1-din-openrouter-nyckel
export ANTHROPIC_API_KEY=
```

> **OBS:** Använd `ANTHROPIC_AUTH_TOKEN` (inte `ANTHROPIC_API_KEY`) för OpenRouter per deras [dokumentation](https://openrouter.ai/docs).

**Verifiera att proxyn körs:**
```bash
curl http://<ha-ip>:8123/api/openrouter_bridge
```
Förväntat svar:
```json
{"status": "ok", "model": "meta-llama/llama-3.3-70b-instruct:free", "requests": 0}
```

---

## API-endpoints

| Endpoint | Metod | Auth krävs | Beskrivning |
|----------|-------|------------|-------------|
| `/api/openrouter_bridge` | GET | Nej | Status, aktuell modell, antal requests |
| `/api/openrouter_bridge/v1/messages` | POST | Nej | Anthropic Messages API-proxy |
| `/api/openrouter_bridge/v1/models` | GET | Nej | Alla tillgängliga OpenRouter-modeller |
| `/api/openrouter_bridge/terminal` | GET | Nej | Inbyggd terminal HTML-sida |
| `/api/openrouter_bridge/terminal/ws` | WS | Nej | Terminal WebSocket-backend |

Alla endpoints är icke-autentiserade av design — de ligger bakom ditt HA-nätverksperimeter. Om du exponerar externt, använd VPN eller se till att Nabu Casa/omvänd proxy hanterar åtkomstkontroll.

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

**Terminalen visar "❌ Kunde inte starta claude"**
→ Binären saknas. Följ [Terminalsetup](#terminalsetup) för att kopiera den till `/config/claude_bin`.

**Terminalen ansluter men Claude visar fel modell**
→ Kontrollera `input_select.openrouter_bridge_model` i dashboarden. Den visade modellen ska matcha vad du valt.

**"Ogiltig API-nyckel" vid integration-setup**
→ Kontrollera att du använder en OpenRouter-nyckel (`sk-or-v1-...`), inte en Anthropic-nyckel.

**Requests lyckas men jag får generiska/oväntade svar**
→ Vissa gratismodeller har begränsade kontextfönster eller instruktionsföljning. Prova en annan modell, eller byt till en betalmodell som `anthropic/claude-3.5-sonnet`.

**Proxystatussensorn visar `invalid_key` efter setup**
→ Ange om din nyckel via **Inställningar → Enheter och tjänster → OpenRouter Bridge → Konfigurera**.

---

## Stöd projektet

Gillar du det här projektet? En kopp kaffe uppskattas ☕

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/wizz666)

---

## Licens

MIT — se [LICENSE](LICENSE)
