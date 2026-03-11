"""Inbyggd webberminal för OpenRouter Bridge – kör Claude CLI i en PTY."""
from __future__ import annotations

import asyncio
import logging
import os
import subprocess

import aiohttp
from aiohttp import web

# PTY-moduler är Linux-specifika – skyddad import så resten av integrationen laddas
try:
    import fcntl
    import struct
    import termios
    import pty as _pty_mod
    _PTY_AVAILABLE = True
except ImportError:
    _PTY_AVAILABLE = False

from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# claude_bin kopieras till /config/ – delad volym tillgänglig från HA core-containern
_CLAUDE_BIN = "/config/claude_bin"

# ---------------------------------------------------------------------------
# xterm.js HTML – serveras vid /api/openrouter_bridge/terminal
# ---------------------------------------------------------------------------
_HTML = r"""<!DOCTYPE html>
<html lang="sv">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Claude – OpenRouter Bridge</title>
  <link rel="stylesheet" href="https://unpkg.com/@xterm/xterm@5.5.0/css/xterm.css">
  <style>
    /* Force-hide xterm measurement helpers (guard against CDN CSS race condition) */
    .xterm-char-measure-element { visibility: hidden !important; left: -9999em !important; }
    .xterm-helper-textarea { opacity: 0 !important; left: -9999em !important; }
    * { margin: 0; padding: 0; box-sizing: border-box; }
    html, body { height: 100%; background: #1e1e1e; overflow: hidden; }
    #terminal { width: 100%; height: 100%; padding: 6px; }
    #terminal .xterm { height: 100%; }
    #status { position: fixed; top: 6px; right: 10px; font: 12px monospace;
              color: #888; pointer-events: none; z-index: 10; }
  </style>
</head>
<body>
  <div id="terminal"></div>
  <div id="status">__MODEL__ · Ansluter...</div>
  <script src="https://unpkg.com/@xterm/xterm@5.5.0/lib/xterm.js"></script>
  <script src="https://unpkg.com/@xterm/addon-fit@0.10.0/lib/addon-fit.js"></script>
  <script>
    const term = new Terminal({
      cursorBlink: true,
      fontFamily: '"DejaVu Sans Mono", "Ubuntu Mono", "Cascadia Code", Menlo, "Courier New", monospace',
      fontSize: 14,
      scrollback: 5000,
      theme: {
        background: '#1e1e1e', foreground: '#d4d4d4', cursor: '#d4d4d4',
        black: '#1e1e1e', brightBlack: '#808080',
        red: '#f44747', brightRed: '#f44747',
        green: '#4ec9b0', brightGreen: '#4ec9b0',
        yellow: '#dcdcaa', brightYellow: '#dcdcaa',
        blue: '#569cd6', brightBlue: '#569cd6',
        magenta: '#c678dd', brightMagenta: '#c678dd',
        cyan: '#4fc1ff', brightCyan: '#4fc1ff',
        white: '#d4d4d4', brightWhite: '#ffffff',
      }
    });
    const fit = new FitAddon.FitAddon();
    term.loadAddon(fit);
    term.open(document.getElementById('terminal'));
    // Delay first fit until DOM is fully laid out (prevents measurement element artifact)
    requestAnimationFrame(() => fit.fit());

    const status = document.getElementById('status');
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    const ws = new WebSocket(`${proto}://${location.host}/api/openrouter_bridge/terminal/ws`);
    ws.binaryType = 'arraybuffer';
    const _dec = new TextDecoder('utf-8', {fatal: false});

    function sendResize() {
      if (ws.readyState !== WebSocket.OPEN) return;
      const b = new Uint8Array(5);
      b[0] = 0x01;
      b[1] = (term.cols >> 8) & 0xff; b[2] = term.cols & 0xff;
      b[3] = (term.rows >> 8) & 0xff; b[4] = term.rows & 0xff;
      ws.send(b);
    }

    const modelLabel = status.textContent.replace(' · Ansluter...', '');
    ws.onopen = () => { fit.fit(); status.textContent = modelLabel + ' · OpenRouter · Ansluten'; sendResize(); };
    ws.onmessage = e => {
      let text = _dec.decode(new Uint8Array(e.data));
      if (text.includes('API Usage Billing')) text = text.replaceAll('API Usage Billing', 'OpenRouter       ');
      term.write(text);
    };
    ws.onclose = () => {
      status.textContent = modelLabel + ' · Stängd';
      term.write('\r\n\x1b[31m── Session avslutad ──\x1b[0m\r\n');
    };
    ws.onerror = () => { status.textContent = 'Fel'; };

    term.onData(d => { if (ws.readyState === WebSocket.OPEN) ws.send(new TextEncoder().encode(d)); });
    term.onResize(sendResize);
    window.addEventListener('resize', () => { fit.fit(); sendResize(); });
  </script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

class OpenRouterTerminalView(HomeAssistantView):
    """Servar xterm.js-sidan med aktuell modell inbakad."""

    url = "/api/openrouter_bridge/terminal"
    name = "api:openrouter_bridge:terminal"
    requires_auth = False

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass

    async def get(self, request: web.Request) -> web.Response:
        model_state = self._hass.states.get("input_select.openrouter_bridge_model")
        model = model_state.state if model_state and model_state.state not in ("unknown", "unavailable") else "openrouter"
        html = _HTML.replace("__MODEL__", model)
        return web.Response(text=html, content_type="text/html")


class OpenRouterTerminalWSView(HomeAssistantView):
    """WebSocket-backend: skapar PTY och kör Claude CLI."""

    url = "/api/openrouter_bridge/terminal/ws"
    name = "api:openrouter_bridge:terminal:ws"
    requires_auth = False

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass

    def _get_proxy_url(self, request: web.Request) -> str:
        """Bygg proxy-URL från request-host (fungerar både lokalt och externt)."""
        scheme = request.headers.get("X-Forwarded-Proto", request.scheme)
        host = request.headers.get("X-Forwarded-Host", request.host)
        return f"{scheme}://{host}/api/openrouter_bridge"

    async def get(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        proxy_url = self._get_proxy_url(request)

        # Läs workspace från HA-state, fallback till /config/claude_workspace
        workspace = "/config/claude_workspace"
        ws_state = self._hass.states.get("input_text.openrouter_bridge_workspace")
        if ws_state and ws_state.state not in ("unknown", "unavailable", ""):
            workspace = ws_state.state.strip()
        # Skapa mappen om den inte finns
        os.makedirs(workspace, exist_ok=True)

        _LOGGER.debug("Terminal: proxy=%s workspace=%s", proxy_url, workspace)

        # Hämta OpenRouter-nyckeln från integration config
        from .api import _get_entry_data
        entry_data = _get_entry_data(self._hass)
        or_key = (entry_data or {}).get("api_key", "")

        env = os.environ.copy()
        env["ANTHROPIC_BASE_URL"] = proxy_url
        # Per OpenRouter-docs: ANTHROPIC_AUTH_TOKEN = OR-nyckeln, ANTHROPIC_API_KEY = tom
        env["ANTHROPIC_AUTH_TOKEN"] = or_key if or_key else "placeholder"
        env["ANTHROPIC_API_KEY"] = ""
        env["TERM"] = "xterm-256color"
        env["HOME"] = "/root"
        env["LANG"] = "en_US.UTF-8"

        # Skapa PTY
        if not _PTY_AVAILABLE:
            await ws.send_bytes(b"\r\n\xe2\x9d\x8c PTY ej tillg\xc3\xa4nglig i denna milj\xc3\xb6\r\n")
            await ws.close()
            return ws

        master_fd, slave_fd = _pty_mod.openpty()
        try:
            fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 120, 0, 0))
        except OSError:
            pass

        # Läs aktiv modell för --model flaggan
        model_state = self._hass.states.get("input_select.openrouter_bridge_model")
        active_model = (
            model_state.state
            if model_state and model_state.state not in ("unknown", "unavailable", "")
            else None
        )
        cmd = [_CLAUDE_BIN]
        if active_model:
            cmd += ["--model", active_model]

        # Starta Claude
        try:
            proc = subprocess.Popen(
                cmd,
                stdin=slave_fd, stdout=slave_fd, stderr=slave_fd,
                close_fds=True, env=env, cwd=workspace,
                preexec_fn=os.setsid,
            )
        except Exception as exc:
            os.close(master_fd)
            os.close(slave_fd)
            await ws.send_bytes(f"\r\n❌ Kunde inte starta claude: {exc}\r\n".encode())
            await ws.close()
            return ws

        os.close(slave_fd)
        loop = asyncio.get_event_loop()
        pty_task = asyncio.ensure_future(_pty_reader(master_fd, ws, loop))

        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.BINARY:
                    data: bytes = msg.data
                    if len(data) == 5 and data[0] == 0x01:
                        cols = (data[1] << 8) | data[2]
                        rows = (data[3] << 8) | data[4]
                        try:
                            fcntl.ioctl(master_fd, termios.TIOCSWINSZ,
                                        struct.pack("HHHH", rows, cols, 0, 0))
                        except OSError:
                            pass
                    else:
                        try:
                            os.write(master_fd, data)
                        except OSError:
                            break
                elif msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        os.write(master_fd, msg.data.encode())
                    except OSError:
                        break
                elif msg.type in (aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSE):
                    break
        finally:
            pty_task.cancel()
            try:
                proc.terminate()
            except ProcessLookupError:
                pass
            try:
                os.close(master_fd)
            except OSError:
                pass

        return ws


async def _pty_reader(
    master_fd: int,
    ws: web.WebSocketResponse,
    loop: asyncio.AbstractEventLoop,
) -> None:
    """Läser från PTY och skickar till WebSocket."""
    while True:
        try:
            data = await loop.run_in_executor(None, _read_pty, master_fd)
        except Exception:
            break
        if data is None:
            break
        if ws.closed:
            break
        if not data:  # tom buffer-spillover, vänta på nästa chunk
            continue
        try:
            await ws.send_bytes(data)
        except Exception:
            break


_REPLACE_FROM = b"API Usage Billing"
_REPLACE_TO   = b"OpenRouter       "  # samma längd = bevarar layout
_OVERLAP      = len(_REPLACE_FROM) - 1  # 16 bytes överlapp
_pty_buf: dict[int, bytes] = {}  # per fd-buffer


def _read_pty(fd: int) -> bytes | None:
    """Blocking PTY-läsning med rullande buffer för text-ersättning."""
    try:
        raw = os.read(fd, 4096)
    except OSError:
        _pty_buf.pop(fd, None)
        return None

    # Kombinera med eventuell spillover från föregående läsning
    combined = _pty_buf.get(fd, b"") + raw
    replaced = combined.replace(_REPLACE_FROM, _REPLACE_TO)

    # Behåll sista (overlap) bytes för nästa läsning
    if len(replaced) > _OVERLAP:
        _pty_buf[fd] = replaced[-_OVERLAP:]
        return replaced[:-_OVERLAP]
    else:
        _pty_buf[fd] = replaced
        return b""
