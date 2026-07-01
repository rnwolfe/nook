# nook demo — "vacancy board" theme (warm espresso / cream / terracotta / amber).
# Functionality-first: REAL Airbnb output (search → the availability-calendar wedge → listing),
# then a one-line contract nod. Commands are real, so re-render on a residential connection
# (Airbnb blocks datacenter IPs): `uv tool install . --reinstall && vhs demo/nook.tape`.
# One listing id (27079874, an Alfama flat from the search) threads the last two beats together.

Output demo/nook.gif

Set Shell      "bash"
Set FontSize   16
Set Width      1500
Set Height     680
Set Padding    26
Set TypingSpeed 24ms
Set Theme { "name": "nook-vacancy-board", "background": "#17110d", "foreground": "#e4d7c5", "cursor": "#eeb15a", "selection": "#30241b", "black": "#17110d", "red": "#d96a6a", "green": "#9fb089", "yellow": "#eeb15a", "blue": "#b39d86", "magenta": "#ef9d7f", "cyan": "#f2cf95", "white": "#e4d7c5", "brightBlack": "#6b5a4a", "brightRed": "#ef9d7f", "brightGreen": "#b6c7a0", "brightYellow": "#f2cf95", "brightBlue": "#c9b8a3", "brightMagenta": "#f4b79f", "brightCyan": "#f7e0b3", "brightWhite": "#f7efe2" }

Hide
Type "export NO_COLOR=1 PS1='\033[38;5;209m⌂ \033[0m'"  Enter
Type "clear"  Enter
Show

Sleep 700ms
# 1) DISCOVER — search Lisbon for 4 nights, bounded + field-projected for an agent
Type "nook search Lisbon --checkin 2026-08-10 --checkout 2026-08-14 --no-wrap --limit 4 --select name,price.amount,rating 2>/dev/null"  Enter
Sleep 5.5s

Type "clear"  Enter
# 2) THE WEDGE — a real forward availability calendar: which nights are open + min-nights
Type "nook availability 27079874 --json 2>/dev/null | jq -c '.data[:6][] | {date, available, availableForCheckin, minNights}'"  Enter
Sleep 5.5s

Type "clear"  Enter
# 3) DETAILS — the full listing, projected to the fields you asked for
Type "nook listing get 27079874 --no-wrap --select name,roomType,capacity.guests,rating.overall,location.city 2>/dev/null"  Enter
Sleep 5.0s

Type "clear"  Enter
# …and it's read-only, no-auth, conformant — self-described for agents (offline)
Type "nook schema | jq '{readOnly, conformance: .conformance.version, auth: .scope.auth}'"  Enter
Sleep 4.0s

Sleep 1.2s
