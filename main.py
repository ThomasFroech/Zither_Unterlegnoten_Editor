import json
import math
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

# ---- Konfiguration ----

CHROMATIC_STEPS = ["c", "c#", "d", "d#", "e", "f", "f#", "g", "g#", "a", "a#", "b"]
ZITHER_NOTE_COUNT = 25

ZITHER_STRINGS = {}
for i in range(ZITHER_NOTE_COUNT):
    semitone = i % 12
    octave = 1 + (i // 12)
    note_name = f"{CHROMATIC_STEPS[semitone]}{octave}"
    ZITHER_STRINGS[note_name] = i + 1

PAGE_WIDTH, PAGE_HEIGHT = A4
TOP_MARGIN = 28
BOTTOM_MARGIN = 40
SIDE_MARGIN = 40
STRING_CENTER_SPACING_MM = 9.0
STRING_REFERENCE_WIDTH_MM = 3.0
STRING_DRAW_WIDTH_MM = 0.4
ALIGNMENT_ERROR_LINES = 1.0
NOTE_SIDE_PADDING = 20
CUT_LEFT_EDGE_MM = 70
CUT_TOP_EDGE_MM = 85
STRING_LABEL_GAP_MM = 2.0
STRING_LABEL_FONT_SIZE = 10
DOT_RADIUS_MM = 0.9
DOT_GAP_MM = 1.2
REST_SYMBOL_WIDTH_MM = 4.0
REST_SYMBOL_HEIGHT_MM = 1.2
VOICE_COLORS = [colors.darkblue, colors.darkred]
ADDITIONAL_VOICE_COLORS = [colors.darkblue, colors.darkred, colors.darkgreen, colors.brown]
CHORD_FONT_SIZE = 9
CHORD_NOTE_OFFSET_MM = 2.0
CHORD_BETWEEN_SPACING_MM = 4.0
NOTE_MASK_PADDING_MM = 0.6
NOTE_ROTATION_DEG = 90
CHORD_WITH_DOT_EXTRA_OFFSET_MM = 3.0

INPUT_MELODY_FILE = Path("melody_input.json")
OUTPUT_PDF_FILE = "unterlegeblatt.pdf"
TITLE_FONT_NAME = "Times-Bold"
TITLE_FONT_SIZE = 22
DATE_FONT_SIZE = 9
C1_NOTICE_FONT_SIZE = 8
RHYTHM_FONT_SIZE = 9

DURATION_OPTIONS = ["whole", "half", "quarter", "eighth", "sixteenth"]
REST_NAME_MAP = {"full": "whole", "whole": "whole", "half": "half", "quarter": "quarter"}
CHORD_OPTIONS = ["none", "1", "2", "3", "4", "5", "6"]
CHORD_STRING_OPTIONS = ["4", "3", "2", "1"]
RHYTHM_OPTIONS = ["2/4", "3/4", "4/4", "6/8", "12/8"]


def draw_note_head(canvas_obj, x, y, radius, fill_fraction):
    # White mask so note heads do not visually intersect underlying lines.
    mask_radius = radius + (NOTE_MASK_PADDING_MM * mm)
    canvas_obj.saveState()
    canvas_obj.setStrokeColor(colors.white)
    canvas_obj.setFillColor(colors.white)
    canvas_obj.circle(x, y, mask_radius, stroke=0, fill=1)
    canvas_obj.restoreState()

    canvas_obj.circle(x, y, radius, stroke=1, fill=0)
    if fill_fraction <= 0:
        return
    if fill_fraction >= 1.0:
        canvas_obj.circle(x, y, radius, stroke=0, fill=1)
        return
    start_angle = 90 + NOTE_ROTATION_DEG
    extent = -360 * fill_fraction
    canvas_obj.wedge(
        x - radius,
        y - radius,
        x + radius,
        y + radius,
        start_angle,
        extent,
        stroke=0,
        fill=1,
    )


def draw_augmentation_dot(canvas_obj, x, y, note_radius):
    dot_radius = DOT_RADIUS_MM * mm
    dot_x = x + note_radius + (DOT_GAP_MM * mm) + dot_radius
    canvas_obj.circle(dot_x, y, dot_radius, stroke=0, fill=1)
    return dot_x, dot_radius


def draw_rest_symbol(canvas_obj, x1, y1, x2, y2, rest_duration):
    mx = (x1 + x2) / 2
    my = (y1 + y2) / 2
    symbol_w = REST_SYMBOL_WIDTH_MM * mm
    symbol_h = REST_SYMBOL_HEIGHT_MM * mm

    if rest_duration == "whole":
        canvas_obj.rect(mx - symbol_w / 2, my - symbol_h - (0.2 * mm), symbol_w, symbol_h, stroke=1, fill=1)
        return

    if rest_duration == "half":
        canvas_obj.rect(mx - symbol_w / 2, my + (0.2 * mm), symbol_w, symbol_h, stroke=1, fill=1)
        return

    if rest_duration == "quarter":
        step = symbol_w / 4
        canvas_obj.line(mx - 1.5 * step, my + 1.2 * symbol_h, mx - 0.5 * step, my + 0.2 * symbol_h)
        canvas_obj.line(mx - 0.5 * step, my + 0.2 * symbol_h, mx + 0.5 * step, my + 1.0 * symbol_h)
        canvas_obj.line(mx + 0.5 * step, my + 1.0 * symbol_h, mx - 0.2 * step, my - 0.2 * symbol_h)
        canvas_obj.line(mx - 0.2 * step, my - 0.2 * symbol_h, mx + 0.8 * step, my - 1.0 * symbol_h)


def draw_connector_line(canvas_obj, x1, y1, x2, y2, endpoint_gap):
    dx = x2 - x1
    dy = y2 - y1
    length = math.hypot(dx, dy)
    if length <= 2 * endpoint_gap:
        return

    ux = dx / length
    uy = dy / length
    sx = x1 + ux * endpoint_gap
    sy = y1 + uy * endpoint_gap
    ex = x2 - ux * endpoint_gap
    ey = y2 - uy * endpoint_gap
    canvas_obj.line(sx, sy, ex, ey)


def draw_cut_label(canvas_obj, x1, y1, x2, y2):
    dx = x2 - x1
    dy = y2 - y1
    length = math.hypot(dx, dy)
    if length == 0:
        return

    ux = dx / length
    uy = dy / length
    nx = -uy
    ny = ux

    # Place the label around the middle of the cut line.
    cx = x1 + 0.55 * dx
    cy = y1 + 0.55 * dy
    offset_into_triangle = 1.8 * mm
    cx += nx * offset_into_triangle
    cy += ny * offset_into_triangle
    angle_deg = math.degrees(math.atan2(dy, dx))
    label = "please cut off"

    canvas_obj.saveState()
    canvas_obj.setFillColor(colors.black)
    canvas_obj.translate(cx, cy)
    canvas_obj.rotate(angle_deg)
    canvas_obj.setFont("Helvetica", 8)
    canvas_obj.drawCentredString(0, 0, label)
    canvas_obj.restoreState()


def draw_chord_on_note(canvas_obj, x, y, note_radius, chord_spec, extra_offset_mm=0.0):
    chord_number, string_count = _parse_chord_spec(chord_spec)
    chord_text = _chord_label(chord_number, string_count)
    x_offset = note_radius + ((CHORD_NOTE_OFFSET_MM + extra_offset_mm) * mm)
    canvas_obj.setFont("Helvetica-Bold", CHORD_FONT_SIZE)
    canvas_obj.saveState()
    canvas_obj.translate(x + x_offset, y)
    canvas_obj.rotate(90)
    canvas_obj.drawString(0, -(CHORD_FONT_SIZE * 0.3), chord_text)
    canvas_obj.restoreState()


def _chord_label(chord_number, string_count):
    if string_count == 4:
        return str(chord_number)
    return f"{chord_number}({string_count})"


def draw_chords_between_notes(canvas_obj, x1, y1, x2, y2, chord_specs):
    if not chord_specs:
        return
    mx = (x1 + x2) / 2
    my = (y1 + y2) / 2
    count = len(chord_specs)
    spacing = CHORD_BETWEEN_SPACING_MM * mm
    start_x = mx - ((count - 1) * spacing / 2)
    canvas_obj.setFont("Helvetica-Bold", CHORD_FONT_SIZE)
    for i, (chord_number, string_count) in enumerate(chord_specs):
        x = start_x + i * spacing
        chord_text = _chord_label(chord_number, string_count)
        text_width = canvas_obj.stringWidth(chord_text, "Helvetica-Bold", CHORD_FONT_SIZE)
        pad = 0.8 * mm
        bg_w = text_width + 2 * pad
        bg_h = CHORD_FONT_SIZE + (1.0 * mm)
        bg_x = x - bg_w / 2
        bg_y = my - (bg_h / 2) + (CHORD_FONT_SIZE * 0.1)

        # White mask so chord labels stay readable over connector lines.
        canvas_obj.saveState()
        canvas_obj.setStrokeColor(colors.white)
        canvas_obj.setFillColor(colors.white)
        canvas_obj.rect(bg_x, bg_y, bg_w, bg_h, stroke=0, fill=1)
        canvas_obj.restoreState()

        canvas_obj.saveState()
        canvas_obj.translate(x, my + (CHORD_FONT_SIZE * 0.1))
        canvas_obj.rotate(90)
        canvas_obj.drawString(0, -(CHORD_FONT_SIZE * 0.3), chord_text)
        canvas_obj.restoreState()


def min_x_outside_cutout(y, base_left_x, note_radius):
    y_from_top = PAGE_HEIGHT - y
    cut_left = CUT_LEFT_EDGE_MM * mm
    cut_top = CUT_TOP_EDGE_MM * mm

    if 0 <= y_from_top <= cut_left:
        cut_boundary_x = cut_top * (1 - (y_from_top / cut_left))
        return max(base_left_x, cut_boundary_x + note_radius)
    return base_left_x


def _voice_sort_key(voice_id):
    text = str(voice_id)
    if text.isdigit():
        return 0, int(text)
    return 1, text


def _parse_chord_spec(chord_value):
    if isinstance(chord_value, (list, tuple)):
        if len(chord_value) == 2:
            chord_number = int(chord_value[0])
            string_count = int(chord_value[1])
        else:
            raise ValueError(f"Invalid chord spec: {chord_value}")
    else:
        chord_number = int(chord_value)
        string_count = 4

    if chord_number not in {1, 2, 3, 4, 5, 6}:
        raise ValueError(f"Invalid chord number: {chord_number}")
    if string_count not in {1, 2, 3, 4}:
        raise ValueError(f"Invalid chord string count: {string_count}")
    return chord_number, string_count


def _serialize_chord_spec(chord_number, string_count):
    if string_count == 4:
        return chord_number
    return (chord_number, string_count)


def parse_melody_entry(entry):
    if len(entry) == 2:
        name_or_rest, duration = entry
        if str(name_or_rest).lower() == "chord":
            chord_number, string_count = _parse_chord_spec(duration)
            return {"kind": "chord_between", "chord_number": chord_number, "chord_string_count": string_count}
        if str(name_or_rest).lower() == "rest":
            return {"kind": "rest", "duration": duration}
        return {"kind": "note", "note_name": name_or_rest, "duration": duration, "dotted": False}
    if len(entry) == 3:
        note_name, duration, third = entry
        if isinstance(third, bool):
            return {
                "kind": "note",
                "note_name": note_name,
                "duration": duration,
                "dotted": bool(third),
                "chord_with_note": None,
            }
        chord_number, string_count = _parse_chord_spec(third)
        return {
            "kind": "note",
            "note_name": note_name,
            "duration": duration,
            "dotted": False,
            "chord_with_note": (chord_number, string_count),
        }
    if len(entry) == 4:
        note_name, duration, dotted, chord_with_note = entry
        if chord_with_note is not None:
            chord_with_note = _parse_chord_spec(chord_with_note)
        return {
            "kind": "note",
            "note_name": note_name,
            "duration": duration,
            "dotted": bool(dotted),
            "chord_with_note": chord_with_note,
        }
    raise ValueError(f"Invalid melody entry format: {entry!r}")


def build_drawable_notes(melody_entries):
    parsed_melody = [parse_melody_entry(entry) for entry in melody_entries]
    drawable_notes = []
    pending_rest = None
    pending_between_chords = []
    for entry in parsed_melody:
        if entry["kind"] == "rest":
            pending_rest = REST_NAME_MAP.get(str(entry["duration"]).lower())
            continue
        if entry["kind"] == "chord_between":
            pending_between_chords.append((entry["chord_number"], entry["chord_string_count"]))
            continue

        note_name = entry["note_name"]
        if note_name in ZITHER_STRINGS:
            drawable_notes.append(
                (
                    note_name,
                    entry["duration"],
                    entry["dotted"],
                    pending_rest,
                    pending_between_chords.copy(),
                    entry.get("chord_with_note"),
                )
            )
        else:
            print(f"Hinweis: Note {note_name} ist außerhalb des Zither-Bereichs und wurde ignoriert.")
        pending_rest = None
        pending_between_chords = []
    return drawable_notes


def render_pdf(voice_melodies, piece_name="", rhythm="", output_pdf=OUTPUT_PDF_FILE):
    available_height = PAGE_HEIGHT - TOP_MARGIN - BOTTOM_MARGIN
    string_count = len(ZITHER_STRINGS)
    string_reference_width = STRING_REFERENCE_WIDTH_MM * mm
    string_intervals = max(string_count - 1, 1)
    base_spacing = STRING_CENTER_SPACING_MM * mm
    spacing_correction = (ALIGNMENT_ERROR_LINES * base_spacing) / string_intervals
    string_spacing = base_spacing + spacing_correction
    required_height = string_reference_width + max(string_count - 1, 0) * string_spacing
    if required_height > available_height:
        raise ValueError(
            "String layout does not fit the page margins with corrected spacing. "
            "Reduce margins or lower ALIGNMENT_ERROR_LINES."
        )

    top_line_center_y = PAGE_HEIGHT - TOP_MARGIN - (string_reference_width / 2)

    c = canvas.Canvas(output_pdf, pagesize=A4)

    c.setLineWidth(STRING_DRAW_WIDTH_MM * mm)
    for i in range(string_count):
        y = top_line_center_y - i * string_spacing
        if i == string_count - 1:
            c.setStrokeColor(colors.black)
        else:
            c.setStrokeColor(colors.lightgrey)
        c.line(SIDE_MARGIN, y, PAGE_WIDTH - SIDE_MARGIN, y)
    c.setStrokeColor(colors.black)
    c.setLineWidth(1)

    label_x = PAGE_WIDTH - SIDE_MARGIN + (STRING_LABEL_GAP_MM * mm)
    c.setFont("Helvetica", STRING_LABEL_FONT_SIZE)
    for note_name, string_number in ZITHER_STRINGS.items():
        y = top_line_center_y - (string_count - string_number) * string_spacing
        c.saveState()
        c.translate(label_x, y)
        c.rotate(90)
        c.drawString(0, -(STRING_LABEL_FONT_SIZE * 0.35), note_name)
        c.restoreState()

    c1_y = top_line_center_y - (string_count - ZITHER_STRINGS["c1"]) * string_spacing
    c1_notice_y = c1_y - (3.2 * mm)
    c.saveState()
    c.translate(PAGE_WIDTH / 2, c1_notice_y)
    c.rotate(180)
    c.setFillColor(colors.black)
    c.setFont("Helvetica", C1_NOTICE_FONT_SIZE)
    c.drawCentredString(0, 0, "This Line must be below the c1 melody string")
    c.restoreState()

    rhythm_text = rhythm.strip() if rhythm else ""
    if rhythm_text:
        c.saveState()
        c.translate(PAGE_WIDTH / 2, c1_notice_y - (4.2 * mm))
        c.rotate(180)
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", RHYTHM_FONT_SIZE)
        c.drawCentredString(0, 0, f"Rhythm: {rhythm_text}")
        c.restoreState()

    note_radius = 5
    duration_fill = {
        "whole": 1.0,
        "half": 0.5,
        "quarter": 0.25,
        "eighth": 0.125,
        "sixteenth": 0.0625,
    }

    drawable_notes_by_voice = {}
    for voice_id, melody_entries in voice_melodies.items():
        voice_drawable = build_drawable_notes(melody_entries)
        if voice_drawable:
            drawable_notes_by_voice[voice_id] = voice_drawable

    if not drawable_notes_by_voice:
        raise ValueError("No drawable notes found.")

    base_left_x = SIDE_MARGIN + NOTE_SIDE_PADDING
    right_x = PAGE_WIDTH - SIDE_MARGIN - NOTE_SIDE_PADDING
    required_left_x = base_left_x

    for voice_notes in drawable_notes_by_voice.values():
        for note_name, _, _, _, _, _ in voice_notes:
            string_number = ZITHER_STRINGS[note_name]
            y = top_line_center_y - (string_count - string_number) * string_spacing
            required_left_x = max(required_left_x, min_x_outside_cutout(y, base_left_x, note_radius))

    left_x = min(required_left_x, right_x)

    voice_count = len(drawable_notes_by_voice)
    for voice_index, voice_id in enumerate(sorted(drawable_notes_by_voice.keys(), key=_voice_sort_key)):
        drawable_notes = drawable_notes_by_voice[voice_id]
        note_count = len(drawable_notes)
        if note_count <= 1:
            note_positions = [(left_x + right_x) / 2]
        else:
            note_spacing = (right_x - left_x) / (note_count - 1)
            note_positions = [left_x + i * note_spacing for i in range(note_count)]

        if voice_index == 0:
            voice_color = colors.black
        else:
            voice_color = ADDITIONAL_VOICE_COLORS[(voice_index - 1) % len(ADDITIONAL_VOICE_COLORS)]
        c.saveState()
        c.setStrokeColor(voice_color)
        c.setFillColor(voice_color)

        prev_x = None
        prev_y = None
        connector_endpoint_gap = note_radius + (NOTE_MASK_PADDING_MM * mm)
        for x_position, (note_name, duration, dotted, rest_before, between_chords, chord_with_note) in zip(
            note_positions, drawable_notes
        ):
            string_number = ZITHER_STRINGS[note_name]
            y = top_line_center_y - (string_count - string_number) * string_spacing
            fill_fraction = duration_fill.get(duration, 1.0)
            draw_note_head(c, x_position, y, note_radius, fill_fraction)
            dot_drawn = False
            if dotted:
                draw_augmentation_dot(c, x_position, y, note_radius)
                dot_drawn = True
            if chord_with_note is not None:
                chord_extra_offset = CHORD_WITH_DOT_EXTRA_OFFSET_MM if dot_drawn else 0.0
                draw_chord_on_note(c, x_position, y, note_radius, chord_with_note, chord_extra_offset)
            if prev_x is not None:
                draw_connector_line(c, prev_x, prev_y, x_position, y, connector_endpoint_gap)
                if rest_before in {"whole", "half", "quarter"}:
                    draw_rest_symbol(c, prev_x, prev_y, x_position, y, rest_before)
                if between_chords:
                    draw_chords_between_notes(c, prev_x, prev_y, x_position, y, between_chords)
            prev_x = x_position
            prev_y = y

        c.restoreState()

    c.setStrokeColor(colors.black)
    cut_x1 = 0
    cut_y1 = PAGE_HEIGHT - (CUT_LEFT_EDGE_MM * mm)
    cut_x2 = CUT_TOP_EDGE_MM * mm
    cut_y2 = PAGE_HEIGHT
    c.line(cut_x1, cut_y1, cut_x2, cut_y2)
    draw_cut_label(c, cut_x1, cut_y1, cut_x2, cut_y2)

    # Piece title + date upside down at the very bottom of the page.
    title_text = piece_name.strip() or "Untitled Piece"
    date_text = date.today().strftime("%d.%m.%Y")
    title_center_y = c1_notice_y / 2
    c.saveState()
    c.translate(PAGE_WIDTH / 2, title_center_y)
    c.rotate(180)
    c.setFillColor(colors.black)
    c.setStrokeColor(colors.black)
    c.setFont(TITLE_FONT_NAME, TITLE_FONT_SIZE)
    c.drawCentredString(0, 0, title_text)
    title_width = c.stringWidth(title_text, TITLE_FONT_NAME, TITLE_FONT_SIZE)
    c.setLineWidth(1.1)
    c.line(-title_width / 2, -1.5 * mm, title_width / 2, -1.5 * mm)
    c.setFont("Helvetica", DATE_FONT_SIZE)
    c.drawCentredString(0, -6 * mm, date_text)
    c.restoreState()

    c.save()


def serialize_project_data(voice_melodies, piece_name, rhythm):
    return {
        "piece_name": piece_name,
        "rhythm": rhythm,
        "voices": {voice_id: [list(event) for event in events] for voice_id, events in voice_melodies.items()}
    }


def save_project_data(voice_melodies, piece_name, rhythm, output_path=INPUT_MELODY_FILE):
    data = serialize_project_data(voice_melodies, piece_name, rhythm)
    output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_project_data(input_path=INPUT_MELODY_FILE):
    if not input_path.exists():
        return {"1": []}, "", ""

    data = json.loads(input_path.read_text(encoding="utf-8"))
    voices = data.get("voices", {})
    piece_name = str(data.get("piece_name", "")).strip()
    rhythm = str(data.get("rhythm", "")).strip()
    parsed = {}
    for voice_id, events in voices.items():
        parsed[str(voice_id)] = [tuple(event) for event in events]
    return (parsed or {"1": []}), piece_name, rhythm


def format_event(event):
    if len(event) == 2 and str(event[0]).lower() == "chord":
        chord_number, string_count = _parse_chord_spec(event[1])
        return f"chord {_chord_label(chord_number, string_count)} (between)"
    if len(event) == 3 and str(event[0]).lower() == "chord":
        chord_number, string_count = _parse_chord_spec(event[1:3])
        return f"chord {_chord_label(chord_number, string_count)} (between)"
    if len(event) == 2 and str(event[0]).lower() == "rest":
        return f"rest {event[1]}"
    if len(event) == 3:
        if isinstance(event[2], bool):
            return f"{event[0]} {event[1]} dotted"
        chord_number, string_count = _parse_chord_spec(event[2])
        return f"{event[0]} {event[1]} chord:{_chord_label(chord_number, string_count)}"
    if len(event) == 4:
        chord_text = ""
        if event[3] is not None:
            chord_number, string_count = _parse_chord_spec(event[3])
            chord_text = f" chord:{_chord_label(chord_number, string_count)}"
        dotted_text = " dotted" if bool(event[2]) else ""
        return f"{event[0]} {event[1]}{dotted_text}{chord_text}"
    return f"{event[0]} {event[1]}"


def run_gui():
    voice_melodies, initial_piece_name, initial_rhythm = load_project_data()

    root = tk.Tk()
    root.title("Zither Melody Editor")
    root.geometry("900x560")

    control_frame = ttk.Frame(root, padding=12)
    control_frame.pack(fill="x")

    ttk.Label(control_frame, text="Piece Name").grid(row=0, column=0, sticky="w")
    piece_name_var = tk.StringVar(value=initial_piece_name)
    piece_name_entry = ttk.Entry(control_frame, textvariable=piece_name_var, width=34)
    piece_name_entry.grid(row=1, column=0, padx=(0, 10), sticky="w")

    ttk.Label(control_frame, text="Rhythm").grid(row=0, column=6, sticky="w")
    rhythm_var = tk.StringVar(value=initial_rhythm or "4/4")
    rhythm_box = ttk.Combobox(
        control_frame,
        textvariable=rhythm_var,
        values=RHYTHM_OPTIONS,
        width=10,
        state="readonly",
    )
    rhythm_box.grid(row=1, column=6, padx=(0, 10), sticky="w")

    ttk.Label(control_frame, text="Output PDF").grid(row=2, column=0, sticky="w")
    output_pdf_var = tk.StringVar(value=OUTPUT_PDF_FILE)
    output_pdf_entry = ttk.Entry(control_frame, textvariable=output_pdf_var, width=34)
    output_pdf_entry.grid(row=3, column=0, padx=(0, 10), sticky="w")

    def choose_output_pdf():
        selected_path = filedialog.asksaveasfilename(
            title="Select PDF Output Path",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
            initialfile=output_pdf_var.get() or OUTPUT_PDF_FILE,
        )
        if selected_path:
            output_pdf_var.set(selected_path)

    ttk.Button(control_frame, text="Browse...", command=choose_output_pdf).grid(row=3, column=1, sticky="w")

    ttk.Label(control_frame, text="Voice").grid(row=0, column=1, sticky="w")
    voice_var = tk.StringVar(value="1")
    voice_spin = ttk.Spinbox(control_frame, from_=1, to=8, textvariable=voice_var, width=8)
    voice_spin.grid(row=1, column=1, padx=(0, 10), sticky="w")

    ttk.Label(control_frame, text="Type").grid(row=0, column=2, sticky="w")
    event_type_var = tk.StringVar(value="note")
    event_type_box = ttk.Combobox(
        control_frame,
        textvariable=event_type_var,
        values=["note", "rest"],
        width=10,
        state="readonly",
    )
    event_type_box.grid(row=1, column=2, padx=(0, 10), sticky="w")

    ttk.Label(control_frame, text="Note").grid(row=0, column=3, sticky="w")
    note_var = tk.StringVar(value=next(iter(ZITHER_STRINGS.keys())))
    note_box = ttk.Combobox(
        control_frame,
        textvariable=note_var,
        values=list(ZITHER_STRINGS.keys()),
        width=10,
        state="readonly",
    )
    note_box.grid(row=1, column=3, padx=(0, 10), sticky="w")

    ttk.Label(control_frame, text="Sim. Chord").grid(row=2, column=3, sticky="w")
    chord_var = tk.StringVar(value="none")
    chord_box = ttk.Combobox(
        control_frame,
        textvariable=chord_var,
        values=CHORD_OPTIONS,
        width=10,
        state="readonly",
    )
    chord_box.grid(row=3, column=3, padx=(0, 10), sticky="w")

    ttk.Label(control_frame, text="Duration").grid(row=0, column=4, sticky="w")
    duration_var = tk.StringVar(value="quarter")
    duration_box = ttk.Combobox(
        control_frame,
        textvariable=duration_var,
        values=DURATION_OPTIONS,
        width=10,
        state="readonly",
    )
    duration_box.grid(row=1, column=4, padx=(0, 10), sticky="w")

    ttk.Label(control_frame, text="Between Chord").grid(row=2, column=4, sticky="w")
    between_chord_var = tk.StringVar(value="none")
    between_chord_box = ttk.Combobox(
        control_frame,
        textvariable=between_chord_var,
        values=CHORD_OPTIONS,
        width=10,
        state="readonly",
    )
    between_chord_box.grid(row=3, column=4, padx=(0, 10), sticky="w")

    ttk.Label(control_frame, text="Chord Strings").grid(row=0, column=5, sticky="w")
    chord_strings_var = tk.StringVar(value="4")
    chord_strings_box = ttk.Combobox(
        control_frame,
        textvariable=chord_strings_var,
        values=CHORD_STRING_OPTIONS,
        width=8,
        state="readonly",
    )
    chord_strings_box.grid(row=1, column=5, padx=(0, 10), sticky="w")

    dotted_var = tk.BooleanVar(value=False)
    dotted_check = ttk.Checkbutton(control_frame, text="Dotted", variable=dotted_var)
    dotted_check.grid(row=3, column=5, padx=(0, 10), sticky="w")

    button_frame = ttk.Frame(root, padding=(12, 0, 12, 12))
    button_frame.pack(fill="x")

    list_frame = ttk.Frame(root, padding=(12, 0, 12, 12))
    list_frame.pack(fill="both", expand=True)

    event_list = tk.Listbox(list_frame, font=("Courier", 11))
    event_list.pack(side="left", fill="both", expand=True)

    scroll = ttk.Scrollbar(list_frame, orient="vertical", command=event_list.yview)
    scroll.pack(side="right", fill="y")
    event_list.configure(yscrollcommand=scroll.set)

    def refresh_event_list():
        event_list.delete(0, tk.END)
        total = 0
        for voice_id in sorted(voice_melodies.keys(), key=_voice_sort_key):
            event_list.insert(tk.END, f"Voice {voice_id}")
            for idx, event in enumerate(voice_melodies[voice_id], start=1):
                event_list.insert(tk.END, f"  {idx:03d}. {format_event(event)}")
                total += 1
        if total == 0:
            event_list.insert(tk.END, "(no events yet)")

    def on_event_type_change(*_):
        event_type = event_type_var.get()
        is_note = event_type == "note"

        note_box.configure(state="readonly" if is_note else "disabled")
        dotted_check.configure(state="normal" if is_note else "disabled")
        duration_box.configure(state="readonly")
        chord_box.configure(state="readonly" if is_note else "disabled")

        if not is_note:
            dotted_var.set(False)
            chord_var.set("none")

    event_type_var.trace_add("write", on_event_type_change)

    def add_event():
        voice_id = voice_var.get().strip() or "1"
        voice_melodies.setdefault(voice_id, [])
        event_type = event_type_var.get()

        duration = duration_var.get().strip().lower()
        if duration not in DURATION_OPTIONS:
            messagebox.showerror("Invalid duration", "Please select a valid duration.")
            return

        if event_type == "rest":
            voice_melodies[voice_id].append(("rest", duration))
        else:
            note = note_var.get().strip().lower()
            if note not in ZITHER_STRINGS:
                messagebox.showerror("Invalid note", "Please select a note from the list.")
                return

            between_chord_text = between_chord_var.get().strip()
            if between_chord_text in {"1", "2", "3", "4", "5", "6"}:
                has_prior_note = any(
                    isinstance(ev, tuple) and len(ev) >= 2 and str(ev[0]).lower() not in {"rest", "chord"}
                    for ev in voice_melodies[voice_id]
                )
                if has_prior_note:
                    chord_strings = int(chord_strings_var.get().strip())
                    chord_spec = _serialize_chord_spec(int(between_chord_text), chord_strings)
                    voice_melodies[voice_id].append(("chord", chord_spec))
                    between_chord_var.set("none")

            chord_with_note = None
            if chord_var.get().strip() in {"1", "2", "3", "4", "5", "6"}:
                chord_with_note = _serialize_chord_spec(int(chord_var.get().strip()), int(chord_strings_var.get().strip()))
            if dotted_var.get():
                voice_melodies[voice_id].append((note, duration, True, chord_with_note))
            else:
                if chord_with_note is not None:
                    voice_melodies[voice_id].append((note, duration, chord_with_note))
                else:
                    voice_melodies[voice_id].append((note, duration))

        refresh_event_list()

    def add_between_chord():
        voice_id = voice_var.get().strip() or "1"
        voice_melodies.setdefault(voice_id, [])
        chord_text = between_chord_var.get().strip()
        if chord_text not in {"1", "2", "3", "4", "5", "6"}:
            messagebox.showerror("Invalid chord", "Please select a between-chord number (1..6).")
            return
        chord_strings = int(chord_strings_var.get().strip())
        chord_spec = _serialize_chord_spec(int(chord_text), chord_strings)
        voice_melodies[voice_id].append(("chord", chord_spec))
        refresh_event_list()

    def undo_last():
        voice_id = voice_var.get().strip() or "1"
        events = voice_melodies.get(voice_id, [])
        if events:
            events.pop()
            refresh_event_list()

    def clear_voice():
        voice_id = voice_var.get().strip() or "1"
        voice_melodies[voice_id] = []
        refresh_event_list()

    def clear_all():
        for voice_id in list(voice_melodies.keys()):
            voice_melodies[voice_id] = []
        refresh_event_list()

    def clear_json_file():
        try:
            save_project_data({"1": []}, "", "", INPUT_MELODY_FILE)
            voice_melodies.clear()
            voice_melodies["1"] = []
            piece_name_var.set("")
            rhythm_var.set("4/4")
            refresh_event_list()
            messagebox.showinfo("Success", f"Cleared {INPUT_MELODY_FILE.name}.")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def write_and_generate_pdf():
        try:
            piece_name = piece_name_var.get().strip()
            rhythm = rhythm_var.get().strip()
            save_project_data(voice_melodies, piece_name, rhythm, INPUT_MELODY_FILE)
            output_pdf = output_pdf_var.get().strip() or OUTPUT_PDF_FILE
            if not output_pdf.lower().endswith(".pdf"):
                output_pdf += ".pdf"
                output_pdf_var.set(output_pdf)
            render_pdf(voice_melodies, piece_name, rhythm, output_pdf)
            messagebox.showinfo(
                "Success",
                f"Saved notes to {INPUT_MELODY_FILE.name} and generated {output_pdf} with today's date.",
            )
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    ttk.Button(button_frame, text="Add Event", command=add_event).pack(side="left", padx=(0, 8))
    ttk.Button(button_frame, text="Undo Last", command=undo_last).pack(side="left", padx=(0, 8))
    ttk.Button(button_frame, text="Clear Voice", command=clear_voice).pack(side="left", padx=(0, 8))
    ttk.Button(button_frame, text="Clear All", command=clear_all).pack(side="left", padx=(0, 8))
    ttk.Button(button_frame, text="Clear JSON", command=clear_json_file).pack(side="left", padx=(0, 8))
    ttk.Button(button_frame, text="Write + Generate PDF", command=write_and_generate_pdf).pack(side="right")

    on_event_type_change()
    refresh_event_list()
    root.mainloop()


if __name__ == "__main__":
    run_gui()
