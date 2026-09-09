"""The page at /.

The gateway's own root answers JSON-RPC, and the agent's catch-all answers
{"error": "Invalid route"} with HTTP 200, so a visitor to / learns nothing
about whether any of this works. This lays out the routes, what each is for,
and what is genuinely not wired up yet.
"""

from __future__ import annotations

import html

ROUTES = [
    ("GET", "/", "This page.", ""),
    ("GET", "/health", "Liveness.", ""),
    ("GET", "/demo/", "The chat page. Start here.", ""),
    ("GET", "/state/{id}", "What the agent knows, and every leg of the thread.", ""),
    ("GET", "/swml", "The agent, for a voice call.", "basic auth"),
    ("POST", "/chat/", "Text conversation. JSON-RPC.", "bearer key"),
    ("POST", "/chat", "Redirects to /chat/ so a mis-derived URL still works.", "307"),
    ("POST", "/chat/handoff", "Voice call to text.", "nonce"),
    ("POST", "/chat/escalate", "Text to voice call.", "handle"),
    ("POST", "/chat/say", "Type into a live call.", "nonce"),
]

from . import theme  # noqa: E402


def render(*, orders, base_url: str, key: str) -> str:
    rows = "\n".join(
        f"<tr><td>{html.escape(m)} {html.escape(p)}</td><td>{html.escape(d)}</td>"
        f"<td>{'<span class=tag>' + html.escape(n) + '</span>' if n else ''}</td></tr>"
        for m, p, d, n in ROUTES
    )
    order_rows = "\n".join(
        f"<tr><td>{html.escape(o.number)}</td><td>{html.escape(o.status)}</td>"
        f"<td>{html.escape(o.eta)}</td><td>{html.escape(o.address)}</td></tr>"
        for o in orders
    )
    base = html.escape(base_url or "")
    k = html.escape(key or "")

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Order desk</title>
{theme.FONTS}<style>{theme.CSS}</style></head><body><div class="wrap">

<div class="eyebrow">SignalWire &middot; AI Chat</div>
<h1>Order desk</h1>
<p class="muted">
One agent definition. It answers in the chat panel on a page, it answers on a
phone call, and a conversation can move between the two without starting over.
The channel is the SignalWire chat product. Not SMS, not WhatsApp, and not a
general-purpose assistant.
</p>

<p><a class="btn" href="/demo/">Open the chat page</a></p>

<h2>Or from a terminal</h2>
<pre>curl -s -X POST {base}/chat/ \\
  -H 'Content-Type: application/json' \\
  -H 'Authorization: Bearer {k}' \\
  -H 'Origin: {base}' \\
  -d '{{"method":"chat","message":"4417"}}'</pre>
<p class="muted">The <code>Origin</code> header matters: the gateway refuses
origins it was not told about, and a missing one is refused too.</p>

<h2>Orders you can ask about</h2>
<table><thead><tr><th>Order</th><th>Status</th><th>Due</th><th>Address</th></tr></thead>
<tbody>{order_rows}</tbody></table>
<p class="muted">Ask about anything else and it declines, on purpose.</p>

<h2>Routes</h2>
<table><thead><tr><th>Route</th><th>What it does</th><th></th></tr></thead>
<tbody>{rows}</tbody></table>

<h2>Honest state of this demo</h2>
<ul>
<li><strong>Text works end to end</strong>, through the gateway to the AI Chat
service and back, including the order lookup tool.</li>
<li><strong>The voice to text switch is not exercised.</strong> The three
handoff routes are mounted and reject correctly, but a real move needs a call
placed with a <code>handoff_nonce</code> in its user variables, which needs a
number pointed at this agent. That is the part worth seeing and it has not run
yet.</li>
<li><strong>The state panel may stay empty.</strong> Facts are recorded only
when the tool call carries a conversation id, and which field the gateway
passes has not been confirmed.</li>
<li>No pricing anywhere, and no reference customer. Nobody runs this in
production.</li>
</ul>

<footer>One agent definition, served as SWML for voice and fronted by a ChatGateway for text.</footer>
</div></body></html>"""
