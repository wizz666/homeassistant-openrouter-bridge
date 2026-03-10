# Home Assistant OpenRouter Bridge

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![HA Version](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue)](https://www.home-assistant.io)
[![Ko-fi](https://img.shields.io/badge/Ko--fi-Stöd_projektet-F16061?logo=ko-fi&logoColor=white)](https://ko-fi.com/wizz666)

En Anthropic-kompatibel API-proxy byggd direkt i Home Assistant. Peka **Claude Code CLI** (eller valfri Anthropic SDK-klient) mot din HA-instans och använd valfri av OpenRouters 300+ modeller — inklusive gratis sådana.

---

## Vad det gör

Claude Code CLI talar Anthropics API-protokoll. OpenRouter talar OpenAIs protokoll. Den här integrationen översätter dem emellan — körs helt inuti Home Assistant, ingen extra server behövs.

```
Claude Code CLI
    │  POST /api/openrouter_bridge/v1/messages  (Anthropic-format)
    ▼
Home Assistant – OpenRouter Bridge
    • Anthropic tool use  →  OpenAI function calling
    • system-parameter    →  messages[0].role=system
    • Streaming SSE       →  översätts i realtid
    │  POST https://openrouter.ai/api/v1/chat/completions
    ▼
OpenRouter (valfri modell)
    │  svar översatt tillbaka till Anthropic-format
    ▼
Claude Code CLI
```

---

## Funktioner

- **Anthropic-kompatibelt endpoint** i HA:s egna HTTP-server
- **Full tool use-stöd** — Claude Codes bash, filredigering och alla verktyg fungerar
- **Streaming** — token-för-token svar i realtid
- **Modellistning** — `GET /v1/models` returnerar alla OpenRouter-modeller
- **300+ modeller** — Claude, Gemini, GPT-4o, Llama, Mistral, DeepSeek med mera
- **Gratis modeller** — `meta-llama/llama-3.3-70b-instruct:free` och andra utan kostnad
- **AI Hub-integration** — fungerar även som provider i [AI Hub](https://github.com/wizz666/homeassistant-ai-hub)
- **Användningssensorer** — antal requests, senast använd modell, tillgängliga modeller

---

## Krav

- Home Assistant 2024.1+
- En OpenRouter API-nyckel — gratis på [openrouter.ai/keys](https://openrouter.ai/keys)
- Claude Code CLI — gratis på [claude.ai/code](https://claude.ai/code) (kräver gratis Anthropic-konto)

---

## Installation

### Alternativ A – Manuell

1. Kopiera `custom_components/openrouter_bridge/` till din HA:s `custom_components/`-mapp
2. Starta om Home Assistant
3. Gå till **Inställningar → Enheter och tjänster → Lägg till integration → OpenRouter Bridge**
4. Fyll i din OpenRouter API-nyckel och standardmodell

### Alternativ B – HACS (anpassad repo)

1. I HACS → **Anpassade repositorier** → lägg till `https://github.com/wizz666/homeassistant-openrouter-bridge` som typ **Integration**
2. Sök efter **OpenRouter Bridge** och installera
3. Starta om Home Assistant
4. Lägg till integrationen via **Inställningar → Enheter och tjänster**

---

## Konfiguration

| Fält | Beskrivning | Standard |
|------|-------------|---------|
| **OpenRouter API-nyckel** | Din `sk-or-v1-...`-nyckel från openrouter.ai/keys | Obligatorisk |
| **Standardmodell** | OpenRouter modell-ID att använda | `meta-llama/llama-3.3-70b-instruct:free` |
| **Tillåt modellval** | Låt Claude Code välja modell istället | Av |

**Rekommenderade gratismodeller för onboarding:**

| Modell-ID | Noteringar |
|----------|-------|
| `meta-llama/llama-3.3-70b-instruct:free` | Bästa gratisalternativet — snabb och kapabel |
| `google/gemma-3-27b-it:free` | Googles öppna modell |
| `deepseek/deepseek-r1:free` | Stark resonemangsmodell |
| `mistralai/mistral-7b-instruct:free` | Lättviktig och snabb |

---

## Claude Code-setup

När integrationen körs, konfigurera Claude Code på valfri maskin:

```bash
export ANTHROPIC_BASE_URL=http://<din-ha-ip>:8123/api/openrouter_bridge
export ANTHROPIC_API_KEY=sk-or-v1-din-openrouter-nyckel
claude
```

Lägg till i din shell-profil (`~/.bashrc`, `~/.zshrc`) för permanent setup:

```bash
# AI via Home Assistant OpenRouter Bridge
export ANTHROPIC_BASE_URL=http://192.168.1.100:8123/api/openrouter_bridge
export ANTHROPIC_API_KEY=sk-or-v1-din-openrouter-nyckel
```

**Verifiera att proxyn körs:**
```bash
curl http://<ha-ip>:8123/api/openrouter_bridge
```

Du borde se ett JSON-svar med `"status": "ok"` och aktuell modell.

---

## Introduktionsflöde

Den här integrationen är designad för att introducera folk till AI-assisterad utveckling innan de förbinder sig till ett abonnemang:

1. **Prova** — använd Claude Code med en gratis OpenRouter-modell, noll kostnad
2. **Utvärdera** — upplev hela arbetsflödet (kodning, felsökning, förklaring)
3. **Uppgradera** — om det är användbart, skaffa Claude Pro för den riktiga upplevelsen

---

## Stöd projektet

Gillar du det här projektet? En kopp kaffe uppskattas ☕

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/wizz666)

---

## Licens

MIT — se [LICENSE](LICENSE)
