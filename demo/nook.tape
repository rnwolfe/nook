# nook demo — "vacancy board" theme (warm espresso / cream / terracotta / amber).
# All commands are OFFLINE/deterministic (help, schema, did-you-mean, agent) so the GIF never
# hangs on a live Airbnb connection — and so CI can regenerate it (datacenter IPs are blocked
# upstream anyway). Regenerate: `vhs demo/nook.tape`.

Output demo/nook.gif

Set Shell      "bash"
Set FontSize   18
Set Width      1200
Set Height     820
Set Padding    24
Set TypingSpeed 26ms
Set Theme { "name": "nook-vacancy-board", "background": "#17110d", "foreground": "#e4d7c5", "cursor": "#eeb15a", "selection": "#30241b", "black": "#17110d", "red": "#d96a6a", "green": "#9fb089", "yellow": "#eeb15a", "blue": "#b39d86", "magenta": "#ef9d7f", "cyan": "#f2cf95", "white": "#e4d7c5", "brightBlack": "#6b5a4a", "brightRed": "#ef9d7f", "brightGreen": "#b6c7a0", "brightYellow": "#f2cf95", "brightBlue": "#c9b8a3", "brightMagenta": "#f4b79f", "brightCyan": "#f7e0b3", "brightWhite": "#f7efe2" }

Hide
Type "export NO_COLOR=1 PS1='\033[38;5;209m⌂ \033[0m'"  Enter
Type "clear"  Enter
Show

Sleep 700ms
# the surface: read-only, no auth, booking excluded — with runnable examples
Type "nook --help"  Enter
Sleep 3.0s

Type "clear"  Enter
# the wedge: a forward availability calendar an agent can read
Type "nook availability --help"  Enter
Sleep 3.0s

Type "clear"  Enter
# machine-readable self-description: read-only, conformance, and the full exit-code contract
Type "nook schema | jq '{readOnly, conformance: .conformance.version, exit_codes}'"  Enter
Sleep 4.0s

Type "clear"  Enter
# self-correcting, fail-fast — a usage error with a suggestion, not a wasted upstream call
Type "nook serch 'Lisbon'; echo exit=$?"  Enter
Sleep 3.0s

Type "clear"  Enter
# the full contract (incl. the legitimacy boundary) is embedded in the binary
Type "nook agent | head -9"  Enter
Sleep 3.2s

Sleep 1.2s
