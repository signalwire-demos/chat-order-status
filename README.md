# Order desk, by text and by voice

One agent definition. It answers in the chat panel on your page, it answers on
a phone call, and a conversation can move between the two without starting
over.

The channel is the SignalWire chat product on your own site. This is not SMS
and not WhatsApp, and it is not a general-purpose assistant: it answers
questions about order status and declines everything else, on purpose.

**Live:** https://ai-chat-demo.signalwire.me/demo/

## Install

Requires Python 3.11 or newer, and `signalwire-sdk` **3.4.1 or newer**.

```bash
git clone https://github.com/signalwire-demos/chat-order-status.git
cd chat-order-status
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env`, then:

```bash
./venv/bin/python app.py
```

Open `http://localhost:8080/demo/` and ask about order **4417**, **5120** or
**6001**. Ask about anything else and it declines.

`http://localhost:8080/` is the index: every route, the orders, and an honest
list of what is and is not proven.

Two things run: this server, and the page it serves. If you expect one
process, the page looks broken.

## Environment

| Variable | Required | What it is |
|---|---|---|
| `SIGNALWIRE_PROJECT_ID` | yes | Project id. Without it the app will not boot |
| `SIGNALWIRE_API_TOKEN` | yes | API token, with the **Chat** scope enabled |
| `SIGNALWIRE_SPACE` | yes | `your-space.signalwire.com` or bare `your-space`, either works |
| `PUBLIC_URL` | yes | Public base URL. The browser derives `/chat`, `/chat/handoff`, `/chat/escalate` and `/chat/say` from it |
| `CHAT_PUBLIC_KEY` | yes | Publishable key the page presents. Safe in the page: it names no credential, and the gateway's caps bound what it can cost |
| `CHAT_HANDLE_SECRET` | prod | HMAC key for signing conversation handles. Omit and handles stop verifying across a restart or a second worker |
| `SWML_BASIC_AUTH_USER` / `_PASSWORD` | prod | Credentials for `/swml`. See below |
| `FROM_NUMBER` | for voice | A number on your space, used as caller id when dialling |
| `DEFAULT_DIAL_TO` | no | Fallback destination if the page does not pass one |
| `ALLOWED_ORIGINS` | no | Extra origins, comma separated. `PUBLIC_URL` is always allowed |

### `SIGNALWIRE_SPACE` takes either form

The SDK reads it two different ways and neither is wrong: the REST client
builds `https://{host}` and wants the full host, while `AIChatClient` builds
`https://{space}.signalwire.com` and wants the bare name. Set the full host
naively and AI Chat resolves `yourspace.signalwire.com.signalwire.com`.
`config.py` normalises either form and derives both.

### `/swml` is behind basic auth

The AI Chat service fetches `config_url` with no credentials of its own, so an
unauthenticated URL comes back 401 and the gateway answers
`Configuration error` with nothing saying why. Set
`SWML_BASIC_AUTH_USER` and `SWML_BASIC_AUTH_PASSWORD` and the app embeds them
in the config URL for you.

## Routes

| Route | What it is |
|---|---|
| `GET /` | Index page |
| `GET /health` | Liveness |
| `GET /demo/` | The chat page. Start here |
| `GET /state/{id}` | What the agent knows, and every leg of the thread |
| `GET /swml` | The agent, for a voice call (basic auth) |
| `POST /chat/` | Text conversation, gateway JSON-RPC (bearer key) |
| `POST /chat` | 307 to `/chat/`, so a mis-derived URL still works |
| `POST /chat/handoff` | Voice call to text (nonce) |
| `POST /chat/escalate` | Text to voice call (handle) |
| `POST /chat/say` | Type into a live call (nonce) |
| `POST /escalate/dial` | Place the call that carries the nonce |

The three handoff routes must be siblings of the gateway, because the browser
derives all of them from one configured URL.

### The trailing slash

Mounting the gateway at prefix `/chat` puts it at **`/chat/`**. A POST to
`/chat` with no trailing slash falls through to the agent's catch-all, which
answers **HTTP 200** with `{"error": "Invalid route"}`. That reads like a
working endpoint returning nonsense rather than a routing mistake, so `app.py`
aliases the bare path with a 307 and a test holds it down.

## How the switch works

1. `POST /chat/escalate {handle}` ends the text leg and **waits for its
   record**. The call must not start before this returns.
2. `POST /escalate/dial {handle, to}` mints a nonce and dials with
   `url={PUBLIC_URL}/swml?handoff_nonce=...`, returning the nonce.
3. The platform fetches that SWML. `on_swml_request` reads the nonce from the
   query string and the `call_id` from the platform's own POST body, and
   registers them together. **Those two meet in exactly one place and neither
   comes from the browser.**
4. `POST /chat/handoff {nonce}` ends the call, captures the voice leg, and
   mints a handle for the next text leg (`c1.1`).
5. `POST /chat/say {nonce, text}` types into the live call.

### Why the nonce

A browser cannot be trusted to name a call, or anyone who guessed a call id
could type into a stranger's live call. The nonce is server-generated, travels
in a URL we control, and the browser only ever presents it back. Redemption is
single use. An unknown nonce answers exactly like an expired one, so it cannot
be used to probe whether a call is live.

### What survives

`ChatGateway` and `HandoffRouter` own the wire contract. What a conversation
*is* lives in `order_status/conversations.py`. One conversation id hosts text
**and then** voice: only the leg after a call gets a new id, so each message
records its medium when written rather than at read time.

## Deploy to Dokku

```bash
# on the Dokku host
dokku apps:create ai-chat-demo

# from your machine
ssh dokku@your-dokku-host config:set --no-restart ai-chat-demo \
  PUBLIC_URL=https://ai-chat-demo.example.com \
  SIGNALWIRE_PROJECT_ID=... \
  SIGNALWIRE_API_TOKEN=... \
  SIGNALWIRE_SPACE=your-space.signalwire.com \
  CHAT_PUBLIC_KEY=demo-key \
  CHAT_HANDLE_SECRET="$(openssl rand -hex 32)" \
  SWML_BASIC_AUTH_USER=agent \
  SWML_BASIC_AUTH_PASSWORD="$(openssl rand -hex 24)" \
  FROM_NUMBER=+1XXXXXXXXXX

git remote add dokku dokku@your-dokku-host:ai-chat-demo
git push dokku main
```

TLS, once DNS points at the host:

```bash
ssh dokku@your-dokku-host config:set --no-restart ai-chat-demo \
  DOKKU_LETSENCRYPT_EMAIL=you@example.com
ssh dokku@your-dokku-host letsencrypt:enable ai-chat-demo
```

Set the credentials **before** the first push. The app fails fast on a missing
project id, so a push without them fails the deploy rather than booting broken.

## Tests

```bash
./venv/bin/pip install -r requirements-dev.txt
./venv/bin/python -m pytest
```

106 tests. `test_mode_switch.py` runs the whole switch with the real
`HandoffRouter`, real handle signing and real store, asserting that after text
to voice to text the third leg still knows what the first was told.
`test_switching.py` covers the nonce, including that a replayed one is refused.
`brandcheck.py` fails the build if a page drifts off the SignalWire palette.

## What this does not do

- **Not SMS, not WhatsApp**, and no other text channel.
- **Not a general-purpose assistant.** It answers order questions and declines
  the rest.
- **No pricing.** Nothing here says what the feature costs.
- **No reference customer.** Nobody runs this in production.
- **No real call has been placed.** The switch is proven in tests with the
  platform faked, not on a live call.
