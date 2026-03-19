# Home Assistant OpenRouter Bridge

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![HA Version](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue)](https://www.home-assistant.io)
[![Version](https://img.shields.io/badge/Version-1.1.1-green)](https://github.com/wizz666/homeassistant-openrouter-bridge/releases)
[![Ko-fi](https://img.shields.io/badge/Ko--fi-Support_this_project-F16061?logo=ko-fi&logoColor=white)](https://ko-fi.com/wizz666)

**[🇸🇪 Svenska → README.sv.md](README.sv.md)**

An Anthropic-compatible API proxy built into Home Assistant. Point **Claude Code CLI** at your Home Assistant instance and use any of OpenRouter's 300+ models — including free ones — through a **built-in browser terminal** or from any machine on your network.

---

## What this does

Claude Code CLI speaks Anthropic's API protocol. OpenRouter speaks OpenAI's protocol. This integration bridges the two — running entirely inside Home Assistant, no extra server or container needed.

```
Claude Code CLI  (or built-in terminal)
    │  POST /api/openrouter_bridge/v1/messages  (Anthropic format)
    ▼
Home Assistant – OpenRouter Bridge
    • Translates Anthropic → OpenAI format in real time
    • Picks active model from HA dashboard dropdown
    │  POST https://openrouter.ai/api/v1/chat/completions
    ▼
OpenRouter (300+ models, including free ones)
    │  Response translated back to Anthropic format
    ▼
Claude Code CLI
```

---

## Features

- **Anthropic-compatible endpoint** built into HA's own HTTP server — no extra ports or containers
- **Built-in browser terminal** — full xterm.js terminal running Claude Code directly in your browser
- **One-click model switching** — change models from the HA dashboard dropdown, no restart needed
- **`openrouter/free` auto-router** — always picks the best available free model automatically
- **Full tool-use support** — Claude Code's bash executor, file editor, and all built-in tools work
- **Real-time streaming** — token-by-token output
- **Clear error messages** — shows the actual OpenRouter error (rate limit, wrong key, etc.) instead of a generic message
- **Usage sensors** — request count, last used model, available model count
- **Works externally** — accessible via Nabu Casa or any reverse proxy

---

## Requirements

- Home Assistant 2024.1+
- An OpenRouter API key — free at [openrouter.ai/keys](https://openrouter.ai/keys)
- **For the built-in terminal only:** Claude Code binary copied to `/config/claude_bin` (see [Terminal Setup](#terminal-setup))

---

## Installation

### Option A – Manual

1. Copy `custom_components/openrouter_bridge/` to your HA `custom_components/` folder
2. Restart Home Assistant
3. Go to **Settings → Devices & Services → Add integration → OpenRouter Bridge**
4. Enter your OpenRouter API key

### Option B – HACS (custom repository)

1. In HACS → **Custom repositories** → add `https://github.com/wizz666/homeassistant-openrouter-bridge` as type **Integration**
2. Install **OpenRouter Bridge** and restart Home Assistant
3. Add the integration via **Settings → Devices & Services**

---

## Configuration

When adding the integration, enter only your OpenRouter API key (`sk-or-v1-...`). The active model is controlled from the dashboard, not from the config.

---

## Dashboard & Model Selector (Recommended)

The `extras/` folder contains ready-to-use YAML files that add a full dashboard with model selector and terminal button.

### Step 1 — Add the package file

Copy `extras/package_openrouter_bridge.yaml` to your `packages/` folder (create it if needed), then add to `configuration.yaml`:

```yaml
homeassistant:
  packages: !include_dir_named packages
```

This creates two input helpers:
- `input_select.openrouter_bridge_model` — dropdown to select the active model
- `input_text.openrouter_bridge_workspace` — working directory for terminal sessions

### Step 2 — Add the dashboard

Copy `extras/dashboard_openrouter_bridge.yaml` to your `dashboards/` folder, then add to `configuration.yaml`:

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

Restart Home Assistant. **OpenRouter Bridge** appears in the sidebar.

---

## Choosing a Model

The active model is set by the `input_select.openrouter_bridge_model` dropdown in the dashboard. Change it anytime — the next request uses the new model immediately, no restart needed.

> **Always open a new terminal session after switching models** so the `--model` flag passed to Claude Code matches the selected model.

### Free Models

Free models require no OpenRouter credits. They are hosted by OpenRouter on shared infrastructure, so they can occasionally be **temporarily rate-limited** (HTTP 429) during peak hours — this is normal and resolves on its own. The solution is to use `openrouter/free` which automatically picks whichever free model has capacity right now.

| Model ID | Notes |
|----------|-------|
| **`openrouter/free`** | **Recommended — auto-selects the best available free model** |
| `meta-llama/llama-3.3-70b-instruct:free` | Best specific free model for Claude Code |
| `google/gemma-3-27b-it:free` | Good alternative |
| `mistralai/mistral-small-3.1-24b-instruct:free` | Fast and lightweight |
| `nousresearch/hermes-3-llama-3.1-405b:free` | Strong tool-use model |

> ⚠️ **Important:** Claude Code requires **tool-use support** in the model (it uses bash, file editing, etc. via function calling). Reasoning models like DeepSeek R1 and o1 do **not** support tool use and will fail. Always use instruct or chat variants.

### Paid Models

Paid models require OpenRouter credits ([openrouter.ai/credits](https://openrouter.ai/credits)). Even $5 lasts a long time with efficient models.

| Model ID | Notes |
|----------|-------|
| `anthropic/claude-3.5-sonnet` | Best overall for Claude Code |
| `anthropic/claude-3.5-haiku` | Fast and cost-effective |
| `anthropic/claude-3-opus` | Most capable Claude 3 model |
| `google/gemini-2.0-flash-001` | Fast and very affordable |
| `google/gemini-2.5-pro-preview-03-25` | Latest Gemini, high capability |
| `openai/gpt-4o` | OpenAI flagship |
| `openai/gpt-4o-mini` | Affordable GPT-4 class |
| `meta-llama/llama-3.3-70b-instruct` | Best open-source paid option |
| `deepseek/deepseek-chat-v3-0324` | Excellent reasoning, very affordable |

To add any model from OpenRouter's full catalog, find its ID at [openrouter.ai/models](https://openrouter.ai/models) and add it to `extras/package_openrouter_bridge.yaml`.

---

## Free Tier Rate Limits

OpenRouter's free tier has these limits:

| Condition | Requests/day |
|-----------|-------------|
| No credits ever added | ~50 req/day |
| At least some credits added | ~200 req/day |
| Account balance negative | 0 — HTTP 402 even for free models |

Claude Code can generate many requests in a single session (each tool call is a request). If you hit the daily limit, either wait until the next day or add a small credit balance.

The `openrouter/free` router selects from whichever free model **is not currently rate-limited**, so it provides the best chance of getting a response even during peak hours.

---

## Built-in Terminal

Click **Open Terminal** on the dashboard and Claude Code starts immediately in your browser — the selected model is passed automatically, no shell configuration needed.

### How it works

```
Browser (xterm.js) ←── WebSocket ──→ HA PTY handler ←── PTY ──→ /config/claude_bin
```

- A WebSocket connects to `/api/openrouter_bridge/terminal/ws`
- HA spawns the Claude Code binary in a PTY with the correct environment
- All keystrokes and output flow through the WebSocket in real time
- Terminal resize is forwarded to the PTY automatically
- The active model from `input_select.openrouter_bridge_model` is passed as `--model`
- The workspace from `input_text.openrouter_bridge_workspace` is the working directory

### Terminal Setup

The terminal requires the Claude Code binary inside the HA core container. Since Claude Code runs in a separate app container, copy it to the shared `/config/` volume once:

**Step 1 — Find the binary (in the Claude Code app terminal):**

```bash
which claude
# e.g. /root/.local/share/claude/versions/2.x.x/claude
```

**Step 2 — Copy to shared volume:**

```bash
cp $(which claude) /config/claude_bin
chmod +x /config/claude_bin
```

**Step 3 — Verify:**

```bash
/config/claude_bin --version
```

> Repeat step 2 whenever you update Claude Code.

### Environment variables set automatically

| Variable | Value | Purpose |
|----------|-------|---------|
| `ANTHROPIC_BASE_URL` | `http(s)://<your-ha>/api/openrouter_bridge` | Points Claude at the proxy |
| `ANTHROPIC_AUTH_TOKEN` | Your OpenRouter API key | Authentication |
| `ANTHROPIC_API_KEY` | `""` (empty) | Required empty per OpenRouter docs |
| `TERM` | `xterm-256color` | Full color terminal |

### Workspace

The working directory for terminal sessions is set by `input_text.openrouter_bridge_workspace` (default: `/config/claude_workspace`). Create any directory and set it here. A `CLAUDE.md` file in the workspace is loaded as project instructions.

---

## External Machine Setup

To use the proxy from any machine on your network:

```bash
export ANTHROPIC_BASE_URL=http://<your-ha-ip>:8123/api/openrouter_bridge
export ANTHROPIC_AUTH_TOKEN=sk-or-v1-your-openrouter-key
export ANTHROPIC_API_KEY=
claude
```

Add to your shell profile (`~/.bashrc`, `~/.zshrc`) for permanent setup:

```bash
# Claude Code via Home Assistant OpenRouter Bridge
export ANTHROPIC_BASE_URL=http://192.168.1.100:8123/api/openrouter_bridge
export ANTHROPIC_AUTH_TOKEN=sk-or-v1-your-openrouter-key
export ANTHROPIC_API_KEY=
```

> Use `ANTHROPIC_AUTH_TOKEN`, not `ANTHROPIC_API_KEY`, per [OpenRouter docs](https://openrouter.ai/docs).

**Verify:**
```bash
curl http://<ha-ip>:8123/api/openrouter_bridge
# → {"status": "ok", "default_model": "...", "total_requests": 0}
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/openrouter_bridge` | GET | Status, current model, request count |
| `/api/openrouter_bridge/v1/messages` | POST | Anthropic Messages API proxy |
| `/api/openrouter_bridge/v1/models` | GET | All available OpenRouter models |
| `/api/openrouter_bridge/terminal` | GET | Built-in terminal HTML page |
| `/api/openrouter_bridge/terminal/ws` | WS | Terminal WebSocket backend |

All endpoints are unauthenticated — they sit behind your HA network. Use a VPN or ensure your reverse proxy handles access control if exposing externally.

---

## Sensors

| Sensor | Description |
|--------|-------------|
| `sensor.openrouter_bridge_status` | `ok` / `invalid_key` / `unconfigured` |
| `sensor.openrouter_bridge_total_requests` | Requests proxied this session |
| `sensor.openrouter_bridge_available_models` | Number of models on OpenRouter |
| `sensor.openrouter_bridge_last_used_model` | Model used in the last request |

---

## Troubleshooting

**"❌ Kunde inte starta claude" in terminal**
→ Binary missing. Follow [Terminal Setup](#terminal-setup) to copy it to `/config/claude_bin`.

**`[OpenRouter 429] temporarily rate-limited upstream`**
→ The specific free model is overloaded right now. Switch to `openrouter/free` (auto-selects an available one) or try again in a few minutes.

**`[OpenRouter 402] insufficient credits`**
→ Your account balance is negative. Add credits at [openrouter.ai/credits](https://openrouter.ai/credits) or use only free models with a positive balance.

**"API error" or model not responding**
→ Some free models have limited tool-use support. Stick to `openrouter/free` or `meta-llama/llama-3.3-70b-instruct:free` for best results.

**Model switch doesn't seem to take effect**
→ Open a **new terminal session** after changing the dropdown. The model is passed as `--model` at startup.

**Terminal connects but no response from Claude**
→ Run `/status` inside Claude Code to verify `ANTHROPIC_BASE_URL` and auth token. Run `/logout` if you were previously logged in with Anthropic credentials.

**`invalid_key` sensor after setup**
→ Re-enter your key via **Settings → Devices & Services → OpenRouter Bridge → Configure**.

---

## Support

If you find this useful, a coffee is always appreciated ☕

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/wizz666)

---

## License

MIT — see [LICENSE](LICENSE)
