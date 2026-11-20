# Agents may write Bambu Studio process presets

Narrows 0001. Agents may write a Bambu Studio **process** preset (`.json`) that inherits a Bambu system process profile and overrides only named settings. The user imports it (File → Import → Import Configs), reviews it, and slices by hand.

Still forbidden: G-code, project files (`.3mf`), and printer or filament presets, since those carry start G-code and temperatures. Presets live in `presets/` and are never written into Bambu Studio's own folders.

Every overridden key must already exist, with the same value type, in the inherited system profiles, so a typo cannot pass as a setting.

Narrowed by 0004: printer and filament settings generated from Bambu's own profiles, used only in a temp folder while slicing.
