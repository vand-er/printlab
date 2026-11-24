# Phone route: start a print later from Bambu Handy

For a part whose `print.md` has a ```` ```slice ```` block (ADR 0004). Every step after the first is yours: agents never send anything to the printer, sign in or use a LAN access code.

1. Ask an agent for `printlab build <part> --slice`. It writes `parts/<part>/out/<part>.gcode.3mf` (gitignored) only once every check has passed.
2. Open that file in Bambu Studio and check the toolpath preview: orientation, supports, first layer.
3. Click **Send** and send it to the printer's microSD card. The X1C stays in normal cloud mode (Handy needs it; LAN-only and Developer mode won't work).
4. On the phone, when you want it to start: Handy → the printer → **Files** → the file → **Print**.

Fallback if Send fails: copy the file to the microSD card by hand, put the card back, then start it from the printer's screen (Print Files → SD Card), or from Handy as in step 4.

The sliced file holds only the part's PETG STL. A part with a second-filament STL (the Pin strip's labels) loses it, so slice that part in Bambu Studio by hand.
