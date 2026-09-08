# Order desk, by text and by voice

One agent definition. It answers in the chat panel on your page, it answers on
a phone call, and a conversation can move between the two without starting
over.

The channel here is the SignalWire chat product on your own site. This is not
SMS and not WhatsApp, and it is not a general-purpose assistant: it answers
questions about order status and declines everything else, on purpose.

## Run it

```bash
python -m venv venv && ./venv/bin/pip install -r requirements.txt
cp .env.example .env          # fill in your SignalWire credentials and PUBLIC_URL
./venv/bin/python app.py
```

Then open `http://localhost:8080/demo/`. Ask for order 4417, 5120 or 6001.

Two things run: this server, and the page it serves. If you expect one
process, the page looks broken.

## What to watch

The right-hand panel shows what the agent has established. That panel is the
demo. A switch that fires proves plumbing; a switch that *remembers* proves the
product. Establish an order in text, move the conversation to voice, and the
address is already known on the other side.

## The routes

| Route | What it is |
|---|---|
| `GET /swml` | the agent, for a voice call |
| `POST /chat/` | text conversation, gateway JSON-RPC |
| `POST /chat/handoff` | voice call to text |
| `POST /chat/escalate` | text to voice call |
| `POST /chat/say` | type into a live call |
| `GET /state/{id}` | what the agent knows, for the panel |

The three handoff routes have to be siblings of the gateway, because the
browser derives all of them from one configured URL.

### The trailing slash

Mounting the gateway at prefix `/chat` puts it at **`/chat/`**. A POST to
`/chat` with no trailing slash falls through to the agent's catch-all, which
answers **HTTP 200** with `{"error": "Invalid route"}`. That reads like a
working endpoint returning nonsense rather than a routing mistake, so `app.py`
aliases the bare path with a 307 and a test holds the behaviour down.

## How the switch keeps its context

`ChatGateway` and `HandoffRouter` own the wire contract: the routes, the nonce,
the ordering guarantee. They own nothing about what a conversation *is*, which
is `order_status/conversations.py`.

The ordering guarantee runs through `capture_leg`. A new medium never starts
until the one it replaces has finished and its record is durable, and
`capture_leg` returns truthy only once that write has happened. Return early
and the new leg's config fetch races a record that has not landed, so it opens
knowing nothing.

A new leg gets `.N` appended to the conversation id. Facts belong to the whole
thread, so they are keyed on the root id.

## The nonce

A browser cannot be trusted to name a call, or anyone who guessed a call id
could type into a stranger's live call. The application puts a random
`handoff_nonce` in the user variables of the dial, registers it against that
call, and the browser presents it later. An unknown nonce answers exactly like
an expired one, so it cannot be used to probe whether a call is live.

## Tests

```bash
./venv/bin/pip install -r requirements-dev.txt
./venv/bin/python -m pytest
```

46 tests. `test_conversations.py` covers the state that has to survive the
switch, including facts accumulating across legs and legs sorting numerically
rather than alphabetically (`c1.10` after `c1.2`). `test_app.py` runs against
the real SDK and asserts the routes answer as themselves rather than being
swallowed by the catch-all.

## What this does not do

- **Not SMS, not WhatsApp**, and no other text channel.
- **Not a general-purpose assistant.** It answers order questions and declines
  the rest.
- **No pricing.** Nothing here says what the feature costs.
- **No reference customer.** Nobody is running this in production yet.

Requires `signalwire-sdk>=3.4.1`.
