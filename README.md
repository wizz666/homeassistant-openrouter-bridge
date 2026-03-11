# Home Assistant OpenRouter Bridge

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![HA Version](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue)](https://www.home-assistant.io)
[![Version](https://img.shields.io/badge/Version-1.1.0-green)](https://github.com/wizz666/homeassistant-openrouter-bridge/releases)
[![Ko-fi](https://img.shields.io/badge/Ko--fi-Support_this_project-F16061?logo=ko-fi&logoColor=white)](https://ko-fi.com/wizz666)

**[🇸🇪 Svenska → README.sv.md](README.sv.md)**

An Anthropic-compatible API proxy built into Home Assistant. Point **Claude Code CLI** (or any Anthropic SDK client) at your Home Assistant instance and use any of OpenRouter's 300+ models — including free ones. Now includes a **built-in browser terminal** so you can run Claude Code directly from your HA dashboard.

---

## What this does

Claude Code CLI talks Anthropic's API protocol. OpenRouter speaks OpenAI's protocol. This integration bridges the two — running entirely inside Home Assistant, no extra server needed.

```
Claude Code CLI  (or built-in terminal)
    │  POST /api/openrouter_bridge/v1/messages  (Anthropic format)
    ▼
Home Assistant – OpenRouter Bridge
    • Anthropic tools    →  OpenAI function calling
    • system parameter   →  messages[0].role=system
    • Streaming SSE      →  translated in real-time
    │  POST https://openrouter.ai/api/v1/chat/completions
    ▼
OpenRouter (any of 300+ models)
    │  response translated back to Anthropic format
    ▼
Claude Code CLI
```

---

## Features

- **Anthropic-compatible endpoint** built into HA's own HTTP server — no extra containers or ports
- **Built-in browser terminal** — full xterm.js terminal running Claude Code directly in your browser
- **One-click model switching** — change models from the HA dashboard without restarting anything
- **Full tool use support** — Claude Code's bash executor, file editor, and all built-in tools work
- **Streaming** — real-time token-by-token responses
- **Model listing** — `GET /v1/models` returns all available OpenRouter models
- **300+ models** — Claude, Gemini, GPT-4o, Llama, Mistral, DeepSeek, and many more
- **Free models available** — several capable models at zero cost
- **Usage sensors** — requests count, last model used, available model count
- **Works externally** — accessible via your HA external URL (Nabu Casa or reverse proxy)

---

## Requirements

- Home Assistant 2024.1+
- An OpenRouter API key — free at [openrouter.ai/keys](https://openrouter.ai/keys)
- **For the built-in terminal only:** Claude Code CLI binary copied to `/config/claude_bin` (see [Terminal Setup](#terminal-setup))

---

## Installation

### Option A – Manual

1. Copy `custom_components/openrouter_bridge/` to your HA `custom_components/` folder
2. Restart Home Assistant
3. Go to **Settings → Devices & Services → Add integration → OpenRouter Bridge**
4. Enter your OpenRouter API key

### Option B – HACS (custom repository)

1. In HACS → **Custom repositories** → add `https://github.com/wizz666/homeassistant-openrouter-bridge` as type **Integration**
2. Search for **OpenRouter Bridge** and install
3. Restart Home Assistant
4. Add the integration via **Settings → Devices & Services**

---

## Configuration

During setup (or via **Configure** in the integration card) you set:

| Field | Description |
|-------|-------------|
| **OpenRouter API Key** | Your `sk-or-v1-...` key from openrouter.ai/keys |

That's it. The model is controlled from the dashboard (see below), not baked into the config.

---

## Dashboard & Model Selector (Optional but Recommended)

The `extras/` folder contains two files that add a proper dashboard with model selector and terminal button.

### 1 – Add the package (input helpers)

Copy `extras/package_openrouter_bridge.yaml` to your HA `packages/` folder (create it if it doesn't exist), then add to `configuration.yaml`:

```yaml
homeassistant:
  packages: !include_dir_named packages
```

This creates:
- `input_select.openrouter_bridge_model` — dropdown to pick the active model
- `input_text.openrouter_bridge_workspace` — the working directory for terminal sessions

### 2 – Add the dashboard

Copy `extras/dashboard_openrouter_bridge.yaml` to your HA `dashboards/` folder, then add to `configuration.yaml`:

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

Restart Home Assistant. A new **OpenRouter Bridge** entry appears in the sidebar.

### Dashboard overview

The dashboard contains:
- **Status row** — live sensors: proxy status, request count, available models, last used model
- **Model selector** — `input_select` dropdown to pick any of the pre-configured models
- **Workspace field** — directory Claude Code uses as its working folder (default: `/config/claude_workspace`)
- **Open Terminal** button — opens the built-in Claude terminal in a new tab
- **Quick links** — OpenRouter Activity, Credits, Keys, Models
- **API endpoint reference**

---

## Choosing a Model

The active model is controlled by `input_select.openrouter_bridge_model`. Change it in the dashboard and the next request automatically uses the new model — no restart needed.

The bridge sends `--model <selected>` to Claude Code in the terminal and forwards the model ID in the API request header to OpenRouter.

### Pre-configured models (edit `package_openrouter_bridge.yaml` to add more)

**Free models** (no OpenRouter credits needed):

| Model ID | Notes |
|----------|-------|
| `meta-llama/llama-3.3-70b-instruct:free` | Best free option — fast and highly capable |
| `google/gemma-3-27b-it:free` | Google's open model |
| `deepseek/deepseek-r1:free` | Strong reasoning, good for complex tasks |
| `mistralai/mistral-7b-instruct:free` | Lightweight and very fast |

**Paid models** (best Claude Code experience):

| Model ID | Notes |
|----------|-------|
| `anthropic/claude-3.5-sonnet` | Best overall for Claude Code |
| `anthropic/claude-3.5-haiku` | Fast and affordable |
| `anthropic/claude-opus-4` | Most capable, higher cost |
| `google/gemini-2.0-flash-001` | Fast and cheap |
| `openai/gpt-4o` | OpenAI flagship |
| `openai/gpt-4o-mini` | Affordable GPT-4 class |
| `deepseek/deepseek-r1` | Excellent reasoning, very affordable |

To add any model from OpenRouter's catalog, find its ID at [openrouter.ai/models](https://openrouter.ai/models) and add it to the `options:` list in `package_openrouter_bridge.yaml`.

---

## Built-in Terminal

The integration includes a full browser-based terminal powered by [xterm.js](https://xtermjs.org/). Click **Open Terminal** on the dashboard and Claude Code starts immediately — the correct model is passed automatically, no shell configuration needed.

### How it works

```
Browser (xterm.js) ←──WebSocket──→ HA WebSocket handler ←──PTY──→ claude_bin
```

- The browser connects via WebSocket to `/api/openrouter_bridge/terminal/ws`
- HA spawns `claude_bin` in a PTY (pseudo-terminal) with the correct environment
- All keystrokes go through the WebSocket to the PTY; all output comes back the same way
- Terminal resize events (including window resize) are forwarded to the PTY in real time
- The active model from `input_select.openrouter_bridge_model` is passed as `--model <id>`
- The workspace from `input_text.openrouter_bridge_workspace` is the working directory

### Terminal Setup

The terminal requires the Claude Code binary to be available inside the HA core container. Since Claude Code runs in a separate add-on container, you need to copy the binary to the shared `/config/` volume once:

**Step 1 — Find the binary in the Claude Code add-on:**

Open a terminal in the Claude Code add-on (VS Code Server, SSH, etc.) and run:

```bash
which claude
# typically: /root/.local/share/claude/versions/<version>/claude
# or: /usr/local/bin/claude
```

**Step 2 — Copy it to the shared volume:**

```bash
cp $(which claude) /config/claude_bin
chmod +x /config/claude_bin
```

**Step 3 — Verify:**

```bash
/config/claude_bin --version
```

The terminal will then find it automatically at `/config/claude_bin`.

> **Note:** When you update Claude Code, repeat step 2 to keep the binary current.

### Environment variables set by the terminal

The terminal automatically sets these when launching Claude Code:

| Variable | Value | Purpose |
|----------|-------|---------|
| `ANTHROPIC_BASE_URL` | `http(s)://<your-ha-host>/api/openrouter_bridge` | Points Claude at the proxy |
| `ANTHROPIC_AUTH_TOKEN` | Your OpenRouter API key from the config entry | Authentication to OpenRouter |
| `ANTHROPIC_API_KEY` | `""` (empty) | Required to be empty per OpenRouter docs |
| `TERM` | `xterm-256color` | Full color terminal support |

No manual environment setup needed — everything is configured automatically.

### Workspace

The working directory for terminal sessions is set by `input_text.openrouter_bridge_workspace` (default: `/config/claude_workspace`). Create any directory you like and set it here. Each session starts in that directory.

A `CLAUDE.md` file in the workspace directory will be picked up by Claude Code as project instructions. The default workspace includes a minimal `CLAUDE.md` to prevent HA's root `/config/CLAUDE.md` from being loaded.

---

## Claude Code Setup (External Machine)

To use the proxy from any machine on your network (not via the built-in terminal):

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

> **Note:** Use `ANTHROPIC_AUTH_TOKEN` (not `ANTHROPIC_API_KEY`) for OpenRouter per their [documentation](https://openrouter.ai/docs).

**Verify the proxy is running:**
```bash
curl http://<ha-ip>:8123/api/openrouter_bridge
```
Expected response:
```json
{"status": "ok", "model": "meta-llama/llama-3.3-70b-instruct:free", "requests": 0}
```

---

## API Endpoints

| Endpoint | Method | Auth required | Description |
|----------|--------|---------------|-------------|
| `/api/openrouter_bridge` | GET | No | Status, current model, request count |
| `/api/openrouter_bridge/v1/messages` | POST | No | Anthropic Messages API proxy |
| `/api/openrouter_bridge/v1/models` | GET | No | All available OpenRouter models |
| `/api/openrouter_bridge/terminal` | GET | No | Built-in terminal HTML page |
| `/api/openrouter_bridge/terminal/ws` | WS | No | Terminal WebSocket backend |

All endpoints are unauthenticated by design — they sit behind your HA network perimeter. If exposing externally, use a VPN or ensure Nabu Casa/reverse proxy handles access control.

---

## Sensors

| Sensor | Description |
|--------|-------------|
| `sensor.openrouter_bridge_status` | `ok` / `invalid_key` / `unconfigured` |
| `sensor.openrouter_bridge_total_requests` | Requests proxied this session |
| `sensor.openrouter_bridge_available_models` | Number of models available on OpenRouter |
| `sensor.openrouter_bridge_last_used_model` | Model ID used in the last request |

---

## How the Protocol Translation Works

**Anthropic → OpenAI (request):**
- `system` parameter → first message with `role: "system"`
- `tools[].input_schema` → `tools[].function.parameters`
- `tool_use` content blocks → `tool_calls` array
- `tool_result` blocks → messages with `role: "tool"`
- `tool_choice: "any"` → `"required"`

**OpenAI → Anthropic (response):**
- `choices[0].message.content` → `content[{type: "text"}]`
- `tool_calls` → `content[{type: "tool_use"}]`
- `finish_reason: "stop"` → `stop_reason: "end_turn"`
- `finish_reason: "tool_calls"` → `stop_reason: "tool_use"`
- `usage.prompt_tokens` → `usage.input_tokens`

Streaming responses are translated event-by-event from OpenAI SSE format to Anthropic SSE format.

---

## Troubleshooting

**Terminal shows "❌ Kunde inte starta claude"**
→ The binary is missing. Follow [Terminal Setup](#terminal-setup) to copy it to `/config/claude_bin`.

**Terminal connects but Claude shows wrong model**
→ Check `input_select.openrouter_bridge_model` in the dashboard. The displayed model should match what you selected.

**"Invalid API key" on integration setup**
→ Make sure you're using an OpenRouter key (`sk-or-v1-...`), not an Anthropic key.

**Requests succeed but I get generic/unexpected responses**
→ Some free models have limited context windows or instruction-following. Try a different model, or switch to a paid one like `anthropic/claude-3.5-sonnet`.

**The proxy status sensor shows `invalid_key` after setup**
→ Re-enter your key via **Settings → Devices & Services → OpenRouter Bridge → Configure**.

---

## Support

If you find this useful, a coffee is always appreciated ☕

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/wizz666)

---

## License

MIT — see [LICENSE](LICENSE)
