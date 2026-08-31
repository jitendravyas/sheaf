# Depth Charge

A 40-second sonar reflex game. Contacts surface on the grid — strike them before
they sink, grab the aqua salvage, and keep off the mines.

| Target  | Worth |
| ------- | ----- |
| Contact | +1    |
| Salvage | +3    |
| Mine    | −2    |

There are 66 targets in a run and 71 points on the board. The sweep is the same
every time, so the only thing that improves is you.

Open `index.html` in any browser. Nothing to install, nothing to build.

## No JavaScript

The whole game is one HTML file and one stylesheet. There is no script tag.

- **Targets** are `<label>`s tied to hidden checkboxes, parked below their well
  and clipped by `overflow: hidden`. A keyframe animation with a per-target
  `--d` delay and `--u` duration raises each one; while it is down it cannot be
  clicked. Striking one checks its box, which swaps in the burst animation and
  sets `pointer-events: none` so it can never be un-struck.
- **The score** is four CSS counters. `input:checked + .tgt` increments `score`
  by 1, salvage by 3, mines by −2, and the readout below prints them with
  `content: counter(score)` — counters read the document in order, so the panel
  has to sit after the board in the markup.
- **The clock** is a column of 41 numbers inside a 1em window, translated with
  `steps(40)`.
- **Round state** is the `#armed` checkbox. Nothing animates until it is
  checked, the start plate hides itself when it is, and the report card is an
  animation with a 40s delay and `fill-mode: forwards`. "Run it back" is a plain
  `<button type="reset">`, which clears every checkbox in the form at once.

Built and verified in Chromium; uses `aspect-ratio`, `clip-path`, and CSS
counters, all of which are broadly supported.
