# Home Assistant OpenRouter Bridge

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![HA Version](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue)](https://www.home-assistant.io)
[![Ko-fi](https://img.shields.io/badge/Ko--fi-Support_this_project-F16061?logo=ko-fi&logoColor=white)](https://ko-fi.com/wizz666)

**[🇸🇪 Svenska → README.sv.md](README.sv.md)**

An Anthropic-compatible API proxy built into Home Assistant. Point **Claude Code CLI** (or any Anthropic SDK client) at your Home Assistant instance and use any of OpenRouter's 300+ models — including free ones.

---

## What this does

Claude Code CLI talks Anthropic's API protocol. OpenRouter speaks OpenAI's protocol. This integration bridges the two — running entirely inside Home Assistant, no extra server needed.

```
Claude Code CLI
    │  POST /api/openrouter_bridge/v1/messages  (Anthropic format)
    ▼
Home Assistant – OpenRouter Bridge
    • Anthropic tools    →  OpenAI function calling
    • system parameter   →  messages[0].role=system
    • Streaming SSE      →  translated in real-time
    │  POST https://openrouter.ai/api/v1/chat/completions
    ▼
OpenRouter (any model)
    │  response translated back to Anthropic format
    ▼
Claude Code CLI
```

---

## Features

- **Anthropic-compatible endpoint** built into HA's own HTTP server
- **Full tool use support** — Claude Code's bash, file editor, and all tools work
- **Streaming** — real-time token-by-token responses
- **Model listing** — `GET /v1/models` returns all OpenRouter models
- **300+ models** — Claude, Gemini, GPT-4o, Llama, Mistral, DeepSeek, and more
- **Free models available** — `meta-llama/llama-3.3-70b-instruct:free` and others at no cost
- **AI Hub integration** — also works as a provider for [AI Hub](https://github.com/wizz666/homeassistant-ai-hub)
- **Usage sensors** — requests count, last model used, available model count

---

## Use cases

### Introduce others to AI coding assistance
Let someone try Claude Code with a free OpenRouter model before committing to a subscription. They experience the full Claude Code workflow without any upfront cost.

### Use any model with Claude Code
Claude Code normally only works with Anthropic's models. With this bridge, you can use Gemini 2.0 Flash, Llama 3.3, DeepSeek R1, or any other OpenRouter model — through the same Claude Code interface.

### Shared team setup
One OpenRouter API key on your HA instance, multiple team members using it via Claude Code.

---

## Requirements

- Home Assistant 2024.1+
- An OpenRouter API key — free at [openrouter.ai/keys](https://openrouter.ai/keys)
- Claude Code CLI — free at [claude.ai/code](https://claude.ai/code) (requires free Anthropic account)

---

## Installation

### Option A – Manual

1. Copy `custom_components/openrouter_bridge/` to your HA `custom_components/` folder
2. Restart Home Assistant
3. Go to **Settings → Devices & Services → Add integration → OpenRouter Bridge**
4. Enter your OpenRouter API key and default model

### Option B – HACS (custom repository)

1. In HACS → **Custom repositories** → add `https://github.com/wizz666/homeassistant-openrouter-bridge` as type **Integration**
2. Search for **OpenRouter Bridge** and install
3. Restart Home Assistant
4. Add the integration via **Settings → Devices & Services**

---

## Configuration

| Field | Description | Default |
|-------|-------------|---------|
| **OpenRouter API Key** | Your `sk-or-v1-...` key from openrouter.ai/keys | Required |
| **Default Model** | OpenRouter model ID to use | `meta-llama/llama-3.3-70b-instruct:free` |
| **Allow model override** | Let Claude Code choose the model instead | Off |

**Recommended free models for onboarding:**

| Model ID | Notes |
|----------|-------|
| `meta-llama/llama-3.3-70b-instruct:free` | Best free option — fast, capable |
| `google/gemma-3-27b-it:free` | Google's open model |
| `deepseek/deepseek-r1:free` | Strong reasoning model |
| `mistralai/mistral-7b-instruct:free` | Lightweight and fast |

**Recommended paid models (best Claude Code experience):**

| Model ID | Notes |
|----------|-------|
| `anthropic/claude-3.5-sonnet` | Best overall for Claude Code |
| `anthropic/claude-3.5-haiku` | Fast and affordable |
| `google/gemini-2.0-flash-001` | Fast and cheap |

---

## Claude Code setup

Once the integration is running, configure Claude Code on any machine:

```bash
export ANTHROPIC_BASE_URL=http://<your-ha-ip>:8123/api/openrouter_bridge
export ANTHROPIC_API_KEY=sk-or-v1-your-openrouter-key
claude
```

Or add to your shell profile (`~/.bashrc`, `~/.zshrc`):

```bash
# AI via Home Assistant OpenRouter Bridge
export ANTHROPIC_BASE_URL=http://192.168.1.100:8123/api/openrouter_bridge
export ANTHROPIC_API_KEY=sk-or-v1-your-openrouter-key
```

**Verify the proxy is running:**
```bash
curl http://<ha-ip>:8123/api/openrouter_bridge
```

You should see a JSON response with `"status": "ok"` and the current model.

---

## API endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/openrouter_bridge` | GET | Status, current model, request count |
| `/api/openrouter_bridge/v1/messages` | POST | Main proxy — Anthropic Messages API |
| `/api/openrouter_bridge/v1/models` | GET | List all available OpenRouter models |

---

## Sensors

| Sensor | Description |
|--------|-------------|
| `sensor.openrouter_bridge_status` | `ok` / `invalid_key` / `unconfigured` |
| `sensor.openrouter_bridge_total_requests` | Requests proxied this session |
| `sensor.openrouter_bridge_available_models` | Number of models on OpenRouter |
| `sensor.openrouter_bridge_last_used_model` | Last model used via the proxy |

---

## AI Hub integration

If you have [AI Hub](https://github.com/wizz666/homeassistant-ai-hub) installed, add your OpenRouter key there:

```
AI Hub → Keys → OpenRouter API Key
AI Hub → Keys → OpenRouter Model
```

All AI Hub integrations can then use OpenRouter via `provider: openrouter`.

---

## How the protocol translation works

**Anthropic → OpenAI (request):**
- `system` parameter → first message with `role: "system"`
- `tools[].input_schema` → `tools[].function.parameters`
- `tool_use` content blocks → `tool_calls` array
- `tool_result` blocks → separate messages with `role: "tool"`
- `tool_choice: "any"` → `"required"`

**OpenAI → Anthropic (response):**
- `choices[0].message.content` → `content[{type: "text"}]`
- `tool_calls` → `content[{type: "tool_use"}]`
- `finish_reason: "stop"` → `stop_reason: "end_turn"`
- `finish_reason: "tool_calls"` → `stop_reason: "tool_use"`
- `usage.prompt_tokens` → `usage.input_tokens`

Streaming responses are translated event-by-event from OpenAI SSE format to Anthropic SSE format.

---

## Onboarding flow

This integration was designed to introduce people to AI-assisted development before they commit to a subscription:

1. **Try** — use Claude Code with a free OpenRouter model, zero cost
2. **Evaluate** — experience the full workflow (coding, debugging, explanation)
3. **Upgrade** — if it's useful, get a Claude Pro subscription for the real thing

---

## Support

If you find this useful, a coffee is always appreciated ☕

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/wizz666)

---

## License

MIT — see [LICENSE](LICENSE)
