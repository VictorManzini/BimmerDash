import math
import pygame
import pygame.gfxdraw
from models import engine, vehicle_state, engine_lock, vehicle_state_lock, stop_event
from config import (SENSORS, GAUGE_TYPES, MAX_SENSORS, DEFAULT_GAUGE,
                    load_layout, save_layout, boot_mode,
                    load_thresholds, save_thresholds)

WHITE = (240, 240, 240)
RED = (255, 0, 0)
DANGER = (255, 74, 60)          # warning color that reads on any mode background
TRACK = (255, 255, 255, 55)     # translucent unfilled arc / bar track
LABEL = (222, 222, 226)
MUTED = (170, 170, 176)

mode_keys = {
    pygame.K_1: "Comfort",
    pygame.K_2: "Sport",
    pygame.K_3: "Sport+",
    pygame.K_4: "ECO PRO",
}

mode_colors = {
    "Comfort": (34, 35, 38),
    "Sport": (72, 12, 14),
    "Sport+": (92, 14, 16),
    "ECO PRO": (12, 38, 78)
}


# --- helpers ---------------------------------------------------------------

def frac(value, meta):
    lo, hi = meta["gmin"], meta["gmax"]
    if hi == lo:
        return 0.0
    return max(0.0, min(1.0, (value - lo) / (hi - lo)))


def in_danger(value, meta):
    return (meta["low"] is not None and value <= meta["low"]) or \
           (meta["high"] is not None and value >= meta["high"])


def threshold_field(meta):
    """Which bound is this sensor's redline? None if it has neither."""
    if meta["high"] is not None:
        return "high"
    if meta["low"] is not None:
        return "low"
    return None


def threshold_step(meta):
    step = round((meta["gmax"] - meta["gmin"]) / 40, meta["dec"])
    return step or 10 ** -meta["dec"]


def adjust_threshold(meta, field, direction):
    val = meta[field] + direction * threshold_step(meta)
    meta[field] = round(max(meta["gmin"], min(meta["gmax"], val)), meta["dec"])


def grad_color(f):
    # green -> yellow -> red
    f = max(0.0, min(1.0, f))
    if f < 0.5:
        return (int(255 * f / 0.5), 200, 0)
    return (255, int(200 * (1 - (f - 0.5) / 0.5)), 0)


def temp_color(value, meta):
    # temperature sensors: blue (cold) -> green (ideal band just below the limit).
    # Past the limit, in_danger() turns the whole gauge red elsewhere.
    lo = meta["gmin"]
    hi = meta["high"] if meta["high"] is not None else meta["gmax"]
    if hi <= lo:
        return (0, 200, 70)
    g = max(0.0, min(1.0, (value - lo) / (hi - lo)))
    t = min(1.0, g / 0.7)          # fully green by 70% of the way to the limit
    blue, green = (0, 130, 235), (0, 200, 70)
    return tuple(int(blue[i] + (green[i] - blue[i]) * t) for i in range(3))


def level_color(meta, lf):
    # fill color at a level fraction lf (0..1 across gmin..gmax)
    if meta.get("unit") == "C":
        return temp_color(meta["gmin"] + lf * (meta["gmax"] - meta["gmin"]), meta)
    return grad_color(lf)


def load_font(size, bold=False):
    """A clean system sans (DIN/Helvetica-like) instead of the pixely default."""
    for name in ("Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans", "FreeSans"):
        try:
            f = pygame.font.SysFont(name, size, bold=bold)
            if f is not None:
                return f
        except Exception:
            pass
    return pygame.font.Font(None, int(size * 1.4))


def blit_text(surf, font, text, color, center, shadow=True, left=None):
    """Render text with a soft drop shadow so it stays legible on any background."""
    if shadow:
        s = font.render(text, True, (0, 0, 0))
        s.set_alpha(95)
        if left is not None:
            surf.blit(s, (left + 1, center[1] - s.get_height() // 2 + 2))
        else:
            surf.blit(s, s.get_rect(center=(center[0] + 1, center[1] + 2)))
    t = font.render(text, True, color)
    if left is not None:
        surf.blit(t, (left, center[1] - t.get_height() // 2))
    else:
        surf.blit(t, t.get_rect(center=center))


def fill_round_rect(surf, rect, color, radius):
    """Rounded rect that honors an alpha channel even on an opaque target."""
    tmp = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    pygame.draw.rect(tmp, color, (0, 0, rect.w, rect.h), border_radius=radius)
    surf.blit(tmp, (rect.x, rect.y))


def _arc_pts(cx, cy, r, a0, a1, steps):
    pts = []
    for i in range(steps + 1):
        a = math.radians(a0 + (a1 - a0) * i / steps)
        pts.append((cx + math.cos(a) * r, cy - math.sin(a) * r))
    return pts


def draw_ring_arc(surf, cx, cy, r, width, start_deg, end_deg, color, cap=True):
    """Smooth anti-aliased thick arc drawn as a filled ring segment (degrees, CCW+)."""
    span = abs(end_deg - start_deg)
    if span < 0.4:
        return
    ro, ri = r + width / 2.0, r - width / 2.0
    steps = max(2, int(span / 3))
    outer = _arc_pts(cx, cy, ro, start_deg, end_deg, steps)
    inner = _arc_pts(cx, cy, ri, end_deg, start_deg, steps)
    poly = [(int(round(x)), int(round(y))) for x, y in outer + inner]
    if len(poly) >= 3:
        pygame.gfxdraw.filled_polygon(surf, poly, color)
        pygame.gfxdraw.aapolygon(surf, poly, color)
    if cap:
        rr = max(1, int(round(width / 2.0)))
        for a in (start_deg, end_deg):
            ar = math.radians(a)
            capx = int(round(cx + math.cos(ar) * r))
            capy = int(round(cy - math.sin(ar) * r))
            pygame.gfxdraw.filled_circle(surf, capx, capy, rr, color)
            pygame.gfxdraw.aacircle(surf, capx, capy, rr, color)


def draw_label(screen, rect, meta, fonts):
    x, y, w, h = rect
    blit_text(screen, fonts["label"], meta["label"].upper(), LABEL, (x + w // 2, y + h - 15))


def draw_value(screen, cx, cy, value, meta, fonts, danger, font_key="value"):
    txt = f"{value:.{meta['dec']}f}"
    blit_text(screen, fonts[font_key], txt, DANGER if danger else WHITE, (cx, cy))


# --- the four gauges (screen, cell rect, meta, value, fonts) ---------------

def _nice_ticks(lo, hi, target=6):
    """Round tick values across a range, plus the chosen step (racing-dial scale)."""
    span = hi - lo
    if span <= 0:
        return [lo], 1
    raw = span / target
    mag = 10 ** math.floor(math.log10(raw))
    step = 10 * mag
    for mm in (1, 2, 2.5, 5, 10):
        if raw <= mm * mag:
            step = mm * mag
            break
    ticks = []
    t = math.ceil(lo / step - 1e-9) * step
    while t <= hi + step * 1e-6:
        ticks.append(round(t, 6))
        t += step
    return ticks, step


def draw_circular(screen, rect, meta, value, fonts):
    x, y, w, h = rect
    cx, cy = x + w // 2, y + h // 2 + 2
    r = min(w, h) // 2 - 20
    f = frac(value, meta)
    danger = in_danger(value, meta)

    # dial ring + redline zone
    draw_ring_arc(screen, cx, cy, r, 3, 225, -45, (255, 255, 255, 70), cap=False)
    if meta["high"] is not None:
        hf = frac(meta["high"], meta)
        if hf < 1.0:
            draw_ring_arc(screen, cx, cy, r, 6, 225 - hf * 270, -45, (216, 40, 30), cap=False)

    # major ticks + numbers along the arc
    ticks, step = _nice_ticks(meta["gmin"], meta["gmax"])
    dec = 0 if step == int(step) else (1 if round(step * 10) == step * 10 else 2)
    for t in ticks:
        a = math.radians(225 - frac(t, meta) * 270)
        ca, sa = math.cos(a), math.sin(a)
        pygame.draw.line(screen, (235, 235, 240),
                         (cx + ca * r, cy - sa * r), (cx + ca * (r - 11), cy - sa * (r - 11)), 2)
        blit_text(screen, fonts["small"], f"{t:.{dec}f}", (206, 206, 212),
                  (cx + ca * (r - 22), cy - sa * (r - 22)))
    # minor ticks
    for i in range(len(ticks) - 1):
        for k in range(1, 5):
            a = math.radians(225 - frac(ticks[i] + (ticks[i + 1] - ticks[i]) * k / 5, meta) * 270)
            ca, sa = math.cos(a), math.sin(a)
            pygame.draw.line(screen, (150, 150, 156),
                             (cx + ca * r, cy - sa * r), (cx + ca * (r - 6), cy - sa * (r - 6)), 1)

    # red needle + hub
    a = math.radians(225 - f * 270)
    ca, sa = math.cos(a), math.sin(a)
    perp = a + math.pi / 2
    bw = 5
    needle = [
        (int(cx + ca * (r - 14)), int(cy - sa * (r - 14))),
        (int(cx + math.cos(perp) * bw), int(cy - math.sin(perp) * bw)),
        (int(cx - ca * 16), int(cy + sa * 16)),
        (int(cx - math.cos(perp) * bw), int(cy + math.sin(perp) * bw)),
    ]
    pygame.gfxdraw.filled_polygon(screen, needle, (226, 30, 30))
    pygame.gfxdraw.aapolygon(screen, needle, (226, 30, 30))
    pygame.gfxdraw.filled_circle(screen, cx, cy, 9, (28, 28, 32))
    pygame.gfxdraw.aacircle(screen, cx, cy, 9, (210, 210, 215))
    pygame.gfxdraw.filled_circle(screen, cx, cy, 4, (226, 30, 30))

    # label printed on the dial face (the sweep gap at the bottom is free), like a real gauge
    blit_text(screen, fonts["label"], meta["label"].upper(), LABEL, (cx, cy + int(r * 0.38)))
    draw_value(screen, cx, y + h - 15, value, meta, fonts, danger, "value")


def draw_arc(screen, rect, meta, value, fonts):
    x, y, w, h = rect
    cx, cy = x + w // 2, y + h // 2 + 16
    r = min(w, h) // 2 - 16
    f = frac(value, meta)
    danger = in_danger(value, meta)
    col = DANGER if danger else level_color(meta, f)
    draw_ring_arc(screen, cx, cy, r, 9, 180, 0, TRACK, cap=False)
    draw_ring_arc(screen, cx, cy, r, 9, 180, 180 - f * 180, col, cap=True)
    draw_value(screen, cx, cy - 4, value, meta, fonts, danger, "value")
    draw_label(screen, rect, meta, fonts)


def draw_bar(screen, rect, meta, value, fonts):
    x, y, w, h = rect
    bw = 34
    bx = x + w // 2 - bw // 2
    top, bottom = y + 20, y + h - 54
    bh = bottom - top
    f = frac(value, meta)
    danger = in_danger(value, meta)
    surf = pygame.Surface((bw, bh), pygame.SRCALPHA)
    pygame.draw.rect(surf, TRACK, (0, 0, bw, bh), border_radius=bw // 2)          # track
    fill_h = int(bh * f)
    if fill_h > 0:
        fill = pygame.Surface((bw, bh), pygame.SRCALPHA)
        for i in range(fill_h):
            col = DANGER if danger else level_color(meta, i / bh if bh else 0)
            yy = bh - 1 - i
            pygame.draw.line(fill, col, (0, yy), (bw, yy))
        mask = pygame.Surface((bw, bh), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, bw, bh), border_radius=bw // 2)
        fill.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        surf.blit(fill, (0, 0))
    screen.blit(surf, (bx, top))
    draw_value(screen, x + w // 2, y + h - 40, value, meta, fonts, danger, "value")
    draw_label(screen, rect, meta, fonts)


def draw_digital(screen, rect, meta, value, fonts):
    x, y, w, h = rect
    f = frac(value, meta)
    danger = in_danger(value, meta)
    col = DANGER if danger else WHITE
    draw_value(screen, x + w // 2, y + h // 2 - 4, value, meta, fonts, danger, "big")
    if meta["unit"]:
        blit_text(screen, fonts["unit"], meta["unit"], MUTED, (x + w // 2, y + h - 58))
    # thin rounded progress underline
    uw = int(w * 0.5)
    ux, uy, uh = x + (w - uw) // 2, y + h - 42, 6
    fill_round_rect(screen, pygame.Rect(ux, uy, uw, uh), TRACK, uh // 2)
    fw = int(uw * f)
    if fw > 0:
        pygame.draw.rect(screen, col, (ux, uy, fw, uh), border_radius=uh // 2)
    draw_label(screen, rect, meta, fonts)


GAUGE_FUNCS = {
    "Circular": draw_circular,
    "Arc": draw_arc,
    "Bar": draw_bar,
    "Digital": draw_digital,
}


# --- gauge-type mini previews (config screen) ------------------------------

def draw_preview(screen, rect, type_name, active, fonts):
    cx, cy = rect.centerx, rect.centery
    f = 0.66
    accent = WHITE if active else (110, 110, 116)
    track = (255, 255, 255, 50) if active else (255, 255, 255, 22)
    if type_name == "Circular":
        r = min(rect.w, rect.h) // 2 - 5
        draw_ring_arc(screen, cx, cy + 2, r, 4, 225, -45, track, cap=False)
        draw_ring_arc(screen, cx, cy + 2, r, 4, 225, 225 - f * 270, accent, cap=True)
    elif type_name == "Arc":
        r = min(rect.w, rect.h) // 2 - 3
        draw_ring_arc(screen, cx, cy + 7, r, 4, 180, 0, track, cap=False)
        draw_ring_arc(screen, cx, cy + 7, r, 4, 180, 180 - f * 180,
                      accent if not active else grad_color(f), cap=True)
    elif type_name == "Bar":
        bw, bh = 12, rect.h - 12
        bx, by = cx - bw // 2, cy - bh // 2
        surf = pygame.Surface((bw, bh), pygame.SRCALPHA)
        pygame.draw.rect(surf, track, (0, 0, bw, bh), border_radius=bw // 2)
        fh = int(bh * f)
        for i in range(fh):
            col = grad_color(i / bh) if active else (110, 110, 116)
            pygame.draw.line(surf, col, (0, bh - 1 - i), (bw, bh - 1 - i))
        mask = pygame.Surface((bw, bh), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, bw, bh), border_radius=bw // 2)
        surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        screen.blit(surf, (bx, by))
    else:  # Digital
        blit_text(screen, fonts["prevnum"], "42", accent, (cx, cy - 1), shadow=False)


# --- slot editor -----------------------------------------------------------
# Tapping a gauge on the dashboard edits that one slot: which sensor it shows,
# which gauge type draws it, where it sits, or drop it entirely.

def slot_editor_layout():
    sensors = [(k, pygame.Rect(12 + (i % 4) * 196, 62 + (i // 4) * 58, 184, 50))
               for i, k in enumerate(SENSORS)]
    gauges = [(t, pygame.Rect(12 + j * 196, 206, 184, 110)) for j, t in enumerate(GAUGE_TYPES)]
    prev, nxt = pygame.Rect(12, 340, 56, 50), pygame.Rect(140, 340, 56, 50)
    back = pygame.Rect(216, 340, 160, 50)
    remove, done = pygame.Rect(400, 340, 180, 50), pygame.Rect(600, 340, 188, 50)
    thr_minus, thr_plus = pygame.Rect(12, 400, 60, 50), pygame.Rect(160, 400, 60, 50)
    return sensors, gauges, prev, nxt, back, remove, done, thr_minus, thr_plus


def move_slot(selected, i, delta):
    """Shift a slot within the dashboard order. Returns its new index."""
    j = i + delta
    if not 0 <= j < len(selected):
        return i
    selected[i], selected[j] = selected[j], selected[i]
    return j


def assign_slot(selected, i, key):
    """Put a sensor in slot i. Already shown elsewhere -> the two slots swap."""
    if key in selected:
        j = selected.index(key)
        selected[i], selected[j] = selected[j], selected[i]
    else:
        selected[i] = key


def first_unused(selected):
    return next(k for k in SENSORS if k not in selected)


def draw_arrow_button(screen, rect, left, active):
    fill_round_rect(screen, rect, (40, 40, 46) if active else (26, 26, 30), 8)
    cx, cy = rect.center
    tip = -9 if left else 9
    pts = [(cx + tip, cy), (cx - tip, cy - 9), (cx - tip, cy + 9)]
    col = WHITE if active else (62, 62, 70)
    pygame.gfxdraw.filled_polygon(screen, pts, col)
    pygame.gfxdraw.aapolygon(screen, pts, col)


def draw_slot_editor(screen, fonts, gauge_types, selected, i):
    key = selected[i]
    sensors, gauges, prev, nxt, back, remove, done, thr_minus, thr_plus = slot_editor_layout()
    screen.fill((18, 18, 20))
    blit_text(screen, fonts["value"], f"Slot {i + 1}", WHITE, (0, 20), shadow=False, left=16)
    blit_text(screen, fonts["label"], "escolha o sensor e o tipo de gauge deste slot",
              MUTED, (0, 20), shadow=False, left=110)

    blit_text(screen, fonts["small"], "SENSOR", MUTED, (0, 48), shadow=False, left=12)
    for k, cell in sensors:
        chosen = k == key
        fill_round_rect(screen, cell, (34, 116, 88) if chosen else (32, 34, 40), 10)
        blit_text(screen, fonts["value"], SENSORS[k]["label"], WHITE if chosen else LABEL,
                  cell.center, shadow=False)
        if not chosen and k in selected:      # already on the dash: its slot number
            blit_text(screen, fonts["small"], str(selected.index(k) + 1), MUTED,
                      (cell.right - 16, cell.centery), shadow=False)

    blit_text(screen, fonts["small"], "GAUGE", MUTED, (0, 192), shadow=False, left=12)
    for t, cell in gauges:
        chosen = gauge_types.get(key) == t
        fill_round_rect(screen, cell, (30, 66, 104) if chosen else (32, 34, 40), 10)
        if chosen:
            pygame.draw.rect(screen, (0, 132, 236), cell, 2, border_radius=10)
        draw_preview(screen, cell.inflate(0, -34).move(0, -8), t, True, fonts)
        blit_text(screen, fonts["small"], t.upper(), WHITE if chosen else MUTED,
                  (cell.centerx, cell.bottom - 14), shadow=False)

    draw_arrow_button(screen, prev, True, i > 0)
    draw_arrow_button(screen, nxt, False, i < len(selected) - 1)
    blit_text(screen, fonts["value"], f"{i + 1}/{len(selected)}", WHITE,
              ((prev.right + nxt.x) // 2, prev.centery), shadow=False)
    fill_round_rect(screen, back, (58, 58, 66), 9)
    blit_text(screen, fonts["value"], "Voltar", WHITE, back.center, shadow=False)
    fill_round_rect(screen, remove, (116, 44, 40), 9)
    blit_text(screen, fonts["value"], "Remover", WHITE, remove.center, shadow=False)
    fill_round_rect(screen, done, (34, 116, 88), 9)
    blit_text(screen, fonts["value"], "OK", WHITE, done.center, shadow=False)

    meta = SENSORS[key]
    field = threshold_field(meta)
    blit_text(screen, fonts["small"], "REDLINE", MUTED, (0, 384), shadow=False, left=12)
    if field:
        fill_round_rect(screen, thr_minus, (40, 40, 46), 9)
        blit_text(screen, fonts["value"], "-", WHITE, thr_minus.center, shadow=False)
        fill_round_rect(screen, thr_plus, (40, 40, 46), 9)
        blit_text(screen, fonts["value"], "+", WHITE, thr_plus.center, shadow=False)
        txt = f"{meta[field]:.{meta['dec']}f} {meta['unit']}".strip()
        blit_text(screen, fonts["value"], txt, WHITE,
                  ((thr_minus.right + thr_plus.x) // 2, thr_minus.centery), shadow=False)
    else:
        blit_text(screen, fonts["label"], "sem limite definido", MUTED,
                  (0, thr_minus.centery), shadow=False, left=thr_minus.x)


# --- save/discard confirmation --------------------------------------------

CONFIRM_BOX = pygame.Rect(230, 170, 340, 140)
CONFIRM_BUTTONS = [  # (rect, label, color)
    (pygame.Rect(242, 258, 100, 38), "Salvar", (34, 116, 88)),
    (pygame.Rect(350, 258, 100, 38), "Descartar", (116, 44, 40)),
    (pygame.Rect(458, 258, 100, 38), "Cancelar", (58, 58, 66)),
]


def draw_confirm(screen, fonts, mode):
    dim = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    dim.fill((0, 0, 0, 155))
    screen.blit(dim, (0, 0))
    fill_round_rect(screen, CONFIRM_BOX, (32, 33, 38), 14)
    pygame.draw.rect(screen, (76, 76, 84), CONFIRM_BOX, 1, border_radius=14)
    blit_text(screen, fonts["value"], "Salvar alterações?", WHITE,
              (CONFIRM_BOX.centerx, CONFIRM_BOX.y + 40), shadow=False)
    blit_text(screen, fonts["label"], f"Layout do modo {mode}", MUTED,
              (CONFIRM_BOX.centerx, CONFIRM_BOX.y + 68), shadow=False)
    for rect, text, col in CONFIRM_BUTTONS:
        fill_round_rect(screen, rect, col, 9)
        blit_text(screen, fonts["label"], text, WHITE, rect.center, shadow=False)


# --- dashboard -------------------------------------------------------------

def read_values():
    with engine_lock:
        e = dict(vars(engine))
    with vehicle_state_lock:
        v = dict(vars(vehicle_state))
    src = {"engine": e, "vehicle": v}
    values = {k: src[m["src"]][m["attr"]] for k, m in SENSORS.items()}
    return values, v.get("drive_mode", "Comfort")


def dashboard_cells(selected):
    """Cell rects for the shown gauges, plus a trailing empty slot when there's room."""
    n = max(1, len(selected) + (len(selected) < MAX_SENSORS))
    cols = min(n, 3)
    rows = math.ceil(n / cols)
    gw, gh = 800 // cols, (480 - 46) // rows
    return [pygame.Rect((i % cols) * gw, 46 + (i // cols) * gh, gw, gh) for i in range(n)]


def draw_empty_slot(screen, rect):
    box = rect.inflate(-rect.w // 3, -rect.h // 3)
    pygame.draw.rect(screen, (255, 255, 255, 40), box, 1, border_radius=12)
    cx, cy = rect.center
    pygame.draw.line(screen, (150, 150, 156), (cx - 14, cy), (cx + 14, cy), 3)
    pygame.draw.line(screen, (150, 150, 156), (cx, cy - 14), (cx, cy + 14), 3)


def draw_dashboard(screen, fonts, gauge_types, selected, values):
    for i, cell in enumerate(dashboard_cells(selected)):
        if i >= len(selected):
            draw_empty_slot(screen, cell)
            continue
        key = selected[i]
        GAUGE_FUNCS[gauge_types.get(key, DEFAULT_GAUGE)](
            screen, tuple(cell), SENSORS[key], values[key], fonts)


def show_data():
    pygame.init()
    screen = pygame.display.set_mode((800, 480))
    clock = pygame.time.Clock()
    fonts = {
        "label": load_font(14),
        "value": load_font(20, bold=True),
        "big": load_font(42, bold=True),
        "small": load_font(12),
        "unit": load_font(15),
        "prevnum": load_font(19, bold=True),
    }
    load_thresholds()
    layout_mode = boot_mode()
    with vehicle_state_lock:
        vehicle_state.drive_mode = layout_mode
    selected, gauge_types = load_layout(layout_mode)
    editing = None                  # index of the slot being edited, if any
    confirm_open = False
    snapshot = None                 # layout as it was when the editor opened
    running = True

    try:
        while running:
            values, mode = read_values()

            # a drive-mode change swaps in that mode's saved dashboard
            if editing is None and not confirm_open and mode != layout_mode:
                layout_mode = mode
                selected, gauge_types = load_layout(mode)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif confirm_open:
                    # popup swallows everything else until answered
                    hit = None
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        hit = next((t for r, t, _ in CONFIRM_BUTTONS
                                    if r.collidepoint(event.pos)), None)
                    elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        hit = "Cancelar"
                    if hit == "Salvar":
                        save_layout(layout_mode, selected, gauge_types)
                        confirm_open, editing = False, None
                    elif hit == "Descartar":
                        selected, gauge_types = list(snapshot[0]), dict(snapshot[1])
                        confirm_open, editing = False, None
                    elif hit == "Cancelar":
                        confirm_open = False

                elif event.type == pygame.KEYDOWN:
                    if event.key in mode_keys and editing is None:
                        with vehicle_state_lock:
                            vehicle_state.drive_mode = mode_keys[event.key]
                    elif event.key == pygame.K_ESCAPE and editing is not None:
                        confirm_open = (selected, gauge_types) != snapshot
                        editing = editing if confirm_open else None

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if editing is not None:
                        sensors, gauges, prev, nxt, back, remove, done, thr_minus, thr_plus = slot_editor_layout()
                        for k, cell in sensors:
                            if cell.collidepoint(event.pos):
                                assign_slot(selected, editing, k)
                        for t, cell in gauges:
                            if cell.collidepoint(event.pos):
                                gauge_types[selected[editing]] = t
                        field = threshold_field(SENSORS[selected[editing]])
                        if field and thr_minus.collidepoint(event.pos):
                            adjust_threshold(SENSORS[selected[editing]], field, -1)
                            save_thresholds()
                        elif field and thr_plus.collidepoint(event.pos):
                            adjust_threshold(SENSORS[selected[editing]], field, 1)
                            save_thresholds()
                        if prev.collidepoint(event.pos):
                            editing = move_slot(selected, editing, -1)
                        elif nxt.collidepoint(event.pos):
                            editing = move_slot(selected, editing, 1)
                        elif back.collidepoint(event.pos):
                            confirm_open = (selected, gauge_types) != snapshot
                            editing = editing if confirm_open else None
                        elif remove.collidepoint(event.pos):
                            selected.pop(editing)
                            confirm_open, editing = True, None
                        elif done.collidepoint(event.pos):
                            # only ask when something actually changed
                            confirm_open = (selected, gauge_types) != snapshot
                            editing = editing if confirm_open else None
                    else:
                        for i, cell in enumerate(dashboard_cells(selected)):
                            if cell.collidepoint(event.pos):
                                snapshot = (list(selected), dict(gauge_types))
                                if i == len(selected):          # the empty "+" slot
                                    selected.append(first_unused(selected))
                                editing = i
                                break

            if editing is not None:
                draw_slot_editor(screen, fonts, gauge_types, selected, editing)
            else:
                back_color = mode_colors.get(mode)
                if back_color is None:
                    print(f"[AVISO] drive_mode desconhecido: '{mode}'")
                    back_color = (34, 35, 38)
                screen.fill(back_color)
                screen.blit(fonts["value"].render(f"Mode: {mode}", True, (255, 255, 255)), (16, 10))
                draw_dashboard(screen, fonts, gauge_types, selected, values)
            if confirm_open:
                draw_confirm(screen, fonts, layout_mode)

            clock.tick(30)
            pygame.display.flip()
    except KeyboardInterrupt:
        print("\n BimmerDash encerrado pelo usuário...")
    finally:
        stop_event.set()
        pygame.quit()


if __name__ == "__main__":  # ponytail: pure-logic self-check, no window
    m = {"gmin": 0, "gmax": 100, "low": None, "high": 90, "dec": 0}
    assert frac(0, m) == 0.0 and frac(50, m) == 0.5 and frac(100, m) == 1.0
    assert frac(-5, m) == 0.0 and frac(150, m) == 1.0
    assert in_danger(95, m) and not in_danger(50, m)
    assert threshold_field(m) == "high"
    assert threshold_field({**m, "high": None}) is None
    m2 = dict(m)
    adjust_threshold(m2, "high", 1)
    assert m2["high"] > 90
    adjust_threshold(m2, "high", -100)
    assert m2["gmin"] <= m2["high"] <= m2["gmax"]           # clamped, never runs off the dial
    assert grad_color(0.0) == (0, 200, 0) and grad_color(1.0) == (255, 0, 0)
    assert set(GAUGE_FUNCS) == set(GAUGE_TYPES)

    s = ["rpm", "speed", "oil"]
    assert move_slot(s, 0, -1) == 0 and s == ["rpm", "speed", "oil"]   # already first
    assert move_slot(s, 2, 1) == 2 and s == ["rpm", "speed", "oil"]    # already last
    assert move_slot(s, 0, 1) == 1 and s == ["speed", "rpm", "oil"]
    assert move_slot(s, 2, -1) == 1 and s == ["speed", "oil", "rpm"]

    assign_slot(s, 0, "turbo"); assert s == ["turbo", "oil", "rpm"]    # unused -> replace
    assign_slot(s, 0, "rpm");   assert s == ["rpm", "oil", "turbo"]    # in use -> swap
    assign_slot(s, 1, "oil");   assert s == ["rpm", "oil", "turbo"]    # itself -> no-op
    assert first_unused(s) not in s

    sensors, gauges, *buttons = slot_editor_layout()
    assert len(buttons) == 7, "prev, nxt, back, remove, done, thr_minus, thr_plus"
    rects = [r for _, r in sensors] + [r for _, r in gauges] + buttons
    assert all(r.right <= 800 and r.bottom <= 480 for r in rects), "editor overflows screen"
    for n in range(0, MAX_SENSORS + 1):
        cells = dashboard_cells(["x"] * n)
        assert len(cells) == (n + 1 if n < MAX_SENSORS else n)   # trailing "+" until full
        assert all(c.right <= 800 and c.bottom <= 480 for c in cells), n
    print("ui self-check ok")
