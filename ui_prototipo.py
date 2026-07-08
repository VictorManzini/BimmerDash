import math
import pygame
import pygame.gfxdraw
from models import engine, vehicle_state, engine_lock, vehicle_state_lock, stop_event
from config import SENSORS, GAUGE_TYPES, MAX_SENSORS, DEFAULT_GAUGE, DEFAULT_SENSORS

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
    x, y, w, _ = rect
    blit_text(screen, fonts["label"], meta["label"].upper(), LABEL, (x + w // 2, y + 15))


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

    # label + digital readout
    draw_label(screen, rect, meta, fonts)
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
    draw_label(screen, rect, meta, fonts)
    draw_value(screen, cx, cy - 4, value, meta, fonts, danger, "value")


def draw_bar(screen, rect, meta, value, fonts):
    x, y, w, h = rect
    bw = 34
    bx = x + w // 2 - bw // 2
    top, bottom = y + 40, y + h - 34
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
    draw_label(screen, rect, meta, fonts)
    draw_value(screen, x + w // 2, y + h - 16, value, meta, fonts, danger, "value")


def draw_digital(screen, rect, meta, value, fonts):
    x, y, w, h = rect
    f = frac(value, meta)
    danger = in_danger(value, meta)
    col = DANGER if danger else WHITE
    draw_label(screen, rect, meta, fonts)
    draw_value(screen, x + w // 2, y + h // 2 - 4, value, meta, fonts, danger, "big")
    if meta["unit"]:
        blit_text(screen, fonts["unit"], meta["unit"], MUTED, (x + w // 2, y + h - 40))
    # thin rounded progress underline
    uw = int(w * 0.5)
    ux, uy, uh = x + (w - uw) // 2, y + h - 24, 6
    fill_round_rect(screen, pygame.Rect(ux, uy, uw, uh), TRACK, uh // 2)
    fw = int(uw * f)
    if fw > 0:
        pygame.draw.rect(screen, col, (ux, uy, fw, uh), border_radius=uh // 2)


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


# --- config screen ---------------------------------------------------------

def config_layout():
    rows = []
    for i, key in enumerate(SENSORS):
        y = 56 + i * 52
        enable = pygame.Rect(12, y, 232, 46)
        cells = [(t, pygame.Rect(262 + j * 130, y + 1, 124, 44)) for j, t in enumerate(GAUGE_TYPES)]
        rows.append((key, enable, cells))
    done = pygame.Rect(694, 8, 96, 28)
    return rows, done


def draw_config(screen, fonts, gauge_types, selected):
    screen.fill((18, 18, 20))
    rows, done = config_layout()
    blit_text(screen, fonts["value"], "Configuration", WHITE, (16, 20), shadow=False, left=16)
    blit_text(screen, fonts["label"], f"{len(selected)}/{MAX_SENSORS} sensores  \u00b7  toque para escolher o gauge",
              MUTED, (0, 20), shadow=False, left=180)
    # column headers over the gauge grid
    for j, t in enumerate(GAUGE_TYPES):
        blit_text(screen, fonts["small"], t.upper(), MUTED, (262 + j * 130 + 62, 44), shadow=False)

    for key, enable, cells in rows:
        meta = SENSORS[key]
        sel = key in selected
        fill_round_rect(screen, enable, (34, 116, 88) if sel else (40, 40, 46), 12)
        ind_x, ind_y = enable.x + 20, enable.centery
        pygame.gfxdraw.aacircle(screen, ind_x, ind_y, 8, WHITE)
        if sel:
            pygame.gfxdraw.filled_circle(screen, ind_x, ind_y, 5, WHITE)
        blit_text(screen, fonts["value"], meta["label"],
                  WHITE if sel else MUTED, (0, enable.centery), shadow=False, left=enable.x + 40)
        for t, cell in cells:
            chosen = gauge_types.get(key) == t
            fill_round_rect(screen, cell, (32, 34, 40) if not chosen else (30, 66, 104), 10)
            if chosen:
                pygame.draw.rect(screen, (0, 132, 236), cell, 2, border_radius=10)
            draw_preview(screen, cell, t, sel, fonts)

    fill_round_rect(screen, done, (70, 70, 78), 8)
    blit_text(screen, fonts["value"], "Done", WHITE, done.center, shadow=False)


def draw_gear(screen, rect):
    cx, cy = rect.center
    for i in range(8):
        a = math.radians(i * 45)
        pygame.draw.line(screen, WHITE,
                         (cx + math.cos(a) * 8, cy + math.sin(a) * 8),
                         (cx + math.cos(a) * 12, cy + math.sin(a) * 12), 2)
    pygame.gfxdraw.aacircle(screen, cx, cy, 8, WHITE)
    pygame.gfxdraw.filled_circle(screen, cx, cy, 3, WHITE)


# --- dashboard -------------------------------------------------------------

def read_values():
    with engine_lock:
        e = dict(vars(engine))
    with vehicle_state_lock:
        v = dict(vars(vehicle_state))
    src = {"engine": e, "vehicle": v}
    values = {k: src[m["src"]][m["attr"]] for k, m in SENSORS.items()}
    return values, v.get("drive_mode", "Comfort")


def draw_dashboard(screen, fonts, gauge_types, selected, values):
    top = 46
    n = len(selected)
    if n == 0:
        t = fonts["value"].render("No sensors selected - open config (gear)", True, WHITE)
        screen.blit(t, t.get_rect(center=(400, 260)))
        return
    cols = min(n, 3)
    rows = math.ceil(n / cols)
    gw, gh = 800 // cols, (480 - top) // rows
    for i, key in enumerate(selected):
        c, r = i % cols, i // cols
        cell = (c * gw, top + r * gh, gw, gh)
        func = GAUGE_FUNCS[gauge_types.get(key, DEFAULT_GAUGE)]
        func(screen, cell, SENSORS[key], values[key], fonts)


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
    gauge_types = {k: DEFAULT_GAUGE for k in SENSORS}
    selected = [k for k in DEFAULT_SENSORS if k in SENSORS][:MAX_SENSORS]
    config_open = False
    gear_rect = pygame.Rect(754, 8, 38, 30)
    running = True

    try:
        while running:
            values, mode = read_values()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key in mode_keys:
                        with vehicle_state_lock:
                            vehicle_state.drive_mode = mode_keys[event.key]
                    elif event.key == pygame.K_c:
                        config_open = not config_open
                    elif event.key == pygame.K_ESCAPE:
                        config_open = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if config_open:
                        rows, done = config_layout()
                        for key, enable, cells in rows:
                            if enable.collidepoint(event.pos):
                                if key in selected:
                                    selected.remove(key)
                                elif len(selected) < MAX_SENSORS:
                                    selected.append(key)
                            for t, cell in cells:
                                if cell.collidepoint(event.pos):
                                    gauge_types[key] = t
                        if done.collidepoint(event.pos):
                            config_open = False
                    elif gear_rect.collidepoint(event.pos):
                        config_open = True

            if config_open:
                draw_config(screen, fonts, gauge_types, selected)
            else:
                back_color = mode_colors.get(mode)
                if back_color is None:
                    print(f"[AVISO] drive_mode desconhecido: '{mode}'")
                    back_color = (34, 35, 38)
                screen.fill(back_color)
                screen.blit(fonts["value"].render(f"Mode: {mode}", True, (255, 255, 255)), (16, 10))
                draw_gear(screen, gear_rect)
                draw_dashboard(screen, fonts, gauge_types, selected, values)

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
    assert grad_color(0.0) == (0, 200, 0) and grad_color(1.0) == (255, 0, 0)
    assert set(GAUGE_FUNCS) == set(GAUGE_TYPES)
    print("ui self-check ok")
