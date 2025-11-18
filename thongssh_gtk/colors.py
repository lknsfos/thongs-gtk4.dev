# Placeholder for future internationalization (i18n)
_ = lambda s: s

# --- Color Schemes ---

# Solarized Dark
SOLARIZED_DARK = {
    "background": "#002b36", "foreground": "#839496", "palette": [
    "#073642", "#dc322f", "#859900", "#b58900", "#268bd2", "#d33682", "#2aa198", "#eee8d5",
    "#002b36", "#cb4b16", "#586e75", "#657b83", "#839496", "#6c71c4", "#93a1a1", "#fdf6e3"
]}
# Solarized Light
SOLARIZED_LIGHT = {
    "background": "#fdf6e3", "foreground": "#657b83", "palette": [
    "#eee8d5", "#dc322f", "#859900", "#b58900", "#268bd2", "#d33682", "#2aa198", "#073642",
    "#fdf6e3", "#cb4b16", "#93a1a1", "#839496", "#657b83", "#6c71c4", "#586e75", "#002b36"
]}
# Gruvbox Dark
GRUVBOX_DARK = {
    "background": "#282828", "foreground": "#ebdbb2", "palette": [
    "#282828", "#cc241d", "#98971a", "#d79921", "#458588", "#b16286", "#689d6a", "#a89984",
    "#928374", "#fb4934", "#b8bb26", "#fabd2f", "#83a598", "#d3869b", "#8ec07c", "#ebdbb2"
]}
# ✨ Atom One Light
ATOM_ONE_LIGHT = {
    "background": "#fafafa", "foreground": "#383a42", "palette": [
    "#000000", "#e45649", "#50a14f", "#c18401", "#0184bc", "#a626a4", "#0997b3", "#fafafa",
    "#5c5e64", "#e45649", "#50a14f", "#c18401", "#0184bc", "#a626a4", "#0997b3", "#ffffff"
]}
# ✨ Tango Light
TANGO_LIGHT = {
    "background": "#ffffff", "foreground": "#000000", "palette": [
    "#000000", "#cc0000", "#4e9a06", "#c4a000", "#3465a4", "#75507b", "#06989a", "#d3d7cf",
    "#555753", "#ef2929", "#8ae234", "#fce94f", "#729fcf", "#ad7fa8", "#34e2e2", "#eeeeec"
]}

COLOR_SCHEMES = {
    "default": {"name": _("Default")},
    "solarized-dark": {"name": "Solarized Dark", "colors": SOLARIZED_DARK},
    "solarized-light": {"name": "Solarized Light", "colors": SOLARIZED_LIGHT},
    "gruvbox-dark": {"name": "Gruvbox Dark", "colors": GRUVBOX_DARK},
    "atom-one-light": {"name": "Atom One Light", "colors": ATOM_ONE_LIGHT},
    "tango-light": {"name": "Tango Light", "colors": TANGO_LIGHT},
}