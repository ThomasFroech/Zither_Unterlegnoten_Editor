# Zither Unterlegeblatt Editor

A desktop tool for creating printable zither underlay sheets (`unterlegeblatt`) as PDF.

You enter notes event-by-event in a GUI, assign voices, rests, dotted notes, and chords, then export directly to PDF.

## Features

- GUI-based note entry (no manual code editing required)
- Multi-voice support (voice 1 always black, additional voices colored)
- Notes, rests, dotted notes
- Simultaneous chords on notes (`1..6`)
- Chords between notes (`1..6`)
- Chord string-count variants (`1..4`)
  - Display style:
    - all 4 strings: `3`
    - partial: `3(2)`
- Automatic JSON project save (`melody_input.json`)
- Custom PDF output path selection
- Optional project metadata:
  - piece title
  - rhythm
  - auto date in PDF
- Print-specific layout helpers:
  - cut-off triangle marker with label
  - c1 reference line note

## Requirements

- Python 3.10+
- `reportlab`
- Tkinter (usually included with standard Python installers)

Install dependency (inside your venv):

```bash
pip install reportlab
```

## Run

From project root:

```bash
python main.py
```

(or your venv Python, e.g. `.venv/bin/python main.py`)

## GUI Workflow

1. Enter **Piece Name**.
2. Select **Rhythm**.
3. Select **Voice**.
4. Choose **Type** (`note` or `rest`).
5. For notes:
   - select note name
   - optional `Dotted`
   - optional **Sim. Chord** (`1..6`)
6. Optional **Between Chord**:
   - set value (`1..6`) before adding the next note
   - it is inserted between previous and next note automatically
7. Click **Add Event**.
8. Click **Write + Generate PDF**.

Useful buttons:

- `Undo Last`
- `Clear Voice`
- `Clear All`
- `Clear JSON` (resets `melody_input.json`)

## Output Files

- Project data: `melody_input.json`
- PDF: configurable path in GUI (`Output PDF`)

## JSON Format

Top-level structure:

```json
{
  "piece_name": "My Piece",
  "rhythm": "4/4",
  "voices": {
    "1": [
      ["c1", "quarter"],
      ["d1", "quarter", true],
      ["e1", "quarter", [3, 2]],
      ["chord", [2, 3]],
      ["rest", "quarter"],
      ["f1", "half", true, 4]
    ]
  }
}
```

Event conventions:

- Note:
  - `[note, duration]`
  - `[note, duration, dotted_bool]`
  - `[note, duration, chord]`
  - `[note, duration, dotted_bool, chord]`
- Rest:
  - `["rest", duration]`
- Between-note chord:
  - `["chord", chord]`

`chord` can be:

- simple number (`1..6`) -> all 4 strings
- pair `[number, string_count]` -> partial chord (`string_count` in `1..4`)

## Visual Rules in PDF

- c1 string line is dark, others are light gray
- Note connectors are trimmed so they do not cross note circles
- Note circles and between-chord labels have white masks for readability
- Between-chord numbers are rotated 90° counterclockwise
- String names on right side are rotated 90° counterclockwise
- Title/date and helper labels are upside down for print alignment

## Troubleshooting

- If GUI changes don’t appear, fully close and restart `main.py`.
- If PDF is misaligned on paper, print with **100% scale / Actual size** (no "fit to page").
- If no notes appear, confirm note names are within zither range (`c1` up chromatically for 25 strings).

## Project Structure

- `main.py` - GUI + rendering logic
- `main_backup.py` - backup copy (not used by runtime)
- `melody_input.json` - saved project input
- `unterlegeblatt.pdf` - generated output (or custom path)
