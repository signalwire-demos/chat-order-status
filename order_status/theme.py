"""The SignalWire design system, as tokens.

Locked brand colours, dark-mode-first, with the 60-30-10 discipline: neutral
surfaces carry the page, fuchsia is spent only on the few roles that earn it
(eyebrows, links, the accent on a table header), and headings stay neutral.
Blue is structural: buttons, focus rings, borders. Never invent a hue.
"""

FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
    "family=Instrument+Sans:wght@400;500;600;700&"
    "family=JetBrains+Mono:wght@400;500;700&"
    'family=Lexend:wght@300;400;500;600&display=swap">'
)

CSS = """
/* Dark is the primary theme. Light is the adaptation, not an inversion. */
:root{
  --sw-blue:#044EF4; --sw-fuchsia:#F72A72; --sw-turquoise:#40E0D0; --sw-gold:#FFD700;
  --bg-page:#0e0e18; --bg-surface:#181a28; --bg-raised:#222436;
  --fg-default:#f0f0f4; --fg-secondary:#e8e8ec; --fg-muted:#a0a0aa; --fg-headings:#f0f0f4;
  --border-default:rgba(255,255,255,.12); --border-faint:rgba(255,255,255,.07);
  --link:#40E0D0;
  --cb-bg:#1e1e1f; --cb-fg:#d4d4d8; --cb-comment:#898995;
  --font-heading:'Instrument Sans',system-ui,-apple-system,sans-serif;
  --font-body:'Lexend',system-ui,-apple-system,sans-serif;
  --font-code:'JetBrains Mono',ui-monospace,'SF Mono',Menlo,monospace;
}
@media (prefers-color-scheme:light){
  :root:not([data-theme="dark"]){
    --bg-page:#FAFBFC; --bg-surface:#F3F4F6; --bg-raised:#E8EAF0;
    --fg-default:#1A1A18; --fg-secondary:#3A3A38; --fg-muted:#737371; --fg-headings:#070c2d;
    --border-default:rgba(0,0,0,.10); --border-faint:rgba(0,0,0,.06);
    --link:#044EF4;
  }
}
*{box-sizing:border-box}
body{background:var(--bg-page);color:var(--fg-default);font-family:var(--font-body);
     font-size:16px;font-weight:300;line-height:1.7;margin:0;padding:40px 24px 72px;
     -webkit-font-smoothing:antialiased}
.wrap{max-width:880px;margin:0 auto}
h1,h2,h3{font-family:var(--font-heading);color:var(--fg-headings);font-weight:700;
         line-height:1.2;letter-spacing:-.02em;margin:0;text-wrap:balance}
h1{font-size:clamp(1.6rem,3.4vw,2.1rem);margin-bottom:8px}
h2{font-size:1.05rem;margin:36px 0 12px}
p{margin:0 0 12px;max-width:68ch}
.muted{color:var(--fg-muted);font-size:14px}
/* Eyebrow: the one place a mono uppercase label belongs. */
.eyebrow{font-family:var(--font-code);font-size:11px;font-weight:700;text-transform:uppercase;
         letter-spacing:.14em;color:var(--sw-fuchsia);display:flex;align-items:center;
         gap:10px;margin-bottom:10px}
.eyebrow::before{content:"";width:24px;height:1px;background:var(--sw-fuchsia);flex:none}
a{color:var(--link);text-underline-offset:2px}
a:hover{color:var(--sw-fuchsia)}
a:focus-visible,button:focus-visible,input:focus-visible{outline:2px solid var(--sw-blue);
  outline-offset:3px;border-radius:4px}
/* Panels sit on the raised level. Depth from shadow and level, not colour. */
.panel{background:var(--bg-surface);border:1px solid var(--border-default);border-radius:10px;
       padding:22px 24px;margin-bottom:18px}
table{border-collapse:collapse;width:100%;font-size:14px;margin-bottom:10px}
th{text-align:left;font-family:var(--font-code);font-size:11px;font-weight:700;
   letter-spacing:.12em;text-transform:uppercase;color:var(--fg-muted);
   padding:0 14px 10px 0;border-bottom:2px solid var(--sw-fuchsia)}
td{padding:11px 14px 11px 0;border-bottom:1px solid var(--border-faint);
   color:var(--fg-secondary);vertical-align:top}
tbody tr:last-child td{border-bottom:none}
td:first-child{font-family:var(--font-code);font-size:12.5px;color:var(--fg-default);
  white-space:nowrap}
code{font-family:var(--font-code);font-size:.88em;background:var(--bg-raised);
     border:1px solid var(--border-faint);border-radius:4px;padding:1px 5px;color:var(--fg-default)}
/* Code blocks stay dark in both themes: terminal aesthetic. */
pre{background:var(--cb-bg);color:var(--cb-fg);border:1px solid var(--border-faint);
    border-radius:8px;padding:16px 18px;overflow-x:auto;margin:0 0 14px;
    font-family:var(--font-code);font-size:12.5px;line-height:1.75}
pre .c{color:var(--cb-comment)}
ul{margin:0 0 12px;padding-left:20px}li{margin-bottom:6px;color:var(--fg-secondary)}
li strong{color:var(--fg-default);font-weight:500}
.tag{font-family:var(--font-code);font-size:11px;border:1px solid var(--border-default);
     border-radius:100px;padding:2px 9px;color:var(--fg-muted);white-space:nowrap}
.btn{display:inline-block;background:var(--sw-blue);color:#fff;font-family:var(--font-body);
     font-weight:600;font-size:14px;border:none;border-radius:8px;padding:10px 18px;
     text-decoration:none;cursor:pointer}
.btn:hover{background:#0342cf;color:#fff}
.btn[disabled]{opacity:.5;cursor:default}
.btn-secondary{background:transparent;color:var(--fg-default);
  border:1px solid var(--border-default)}
.btn-secondary:hover{background:var(--bg-raised);color:var(--fg-default)}
input{background:var(--bg-raised);color:var(--fg-default);font-family:var(--font-body);
      font-size:15px;border:1px solid var(--border-default);border-radius:8px;padding:10px 12px}
input::placeholder{color:var(--fg-muted)}
footer{margin-top:44px;padding-top:20px;border-top:1px solid var(--border-default);
       color:var(--fg-muted);font-size:13px}
"""
