"""Pillow motion-graphics fallback for the structured lesson scene language."""

import math
import os
import textwrap
from typing import Any, Dict, List

from PIL import Image, ImageDraw, ImageFont


SIZE = (960, 540)
ACCENTS = {"teal": "#2dd4bf", "blue": "#60a5fa", "violet": "#a78bfa", "amber": "#fbbf24"}


def font(size: int, bold: bool = False):
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def wrapped(draw, value, xy, width, size=18, color="#e2e8f0", bold=False):
    lines = textwrap.wrap(str(value), max(12, int(width / (size * .56)))) or [""]
    draw.multiline_text(xy, "\n".join(lines), font=font(size, bold), fill=color, spacing=4)


def arrow(draw, start, end, color, width=3):
    draw.line((*start, *end), fill=color, width=width)
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    points = [(end[0], end[1])]
    for offset in (.55, -.55):
        points.append((end[0] - 12 * math.cos(angle + offset), end[1] - 12 * math.sin(angle + offset)))
    draw.polygon(points, fill=color)


def sort_states(values, algorithm):
    values = [int(value) for value in values]
    states = [values.copy()]
    if algorithm == "bubble_sort":
        for end in range(len(values) - 1, 0, -1):
            for index in range(end):
                if values[index] > values[index + 1]:
                    values[index], values[index + 1] = values[index + 1], values[index]
                    states.append(values.copy())
    elif algorithm == "selection_sort":
        for index in range(len(values) - 1):
            smallest = min(range(index, len(values)), key=values.__getitem__)
            if index != smallest:
                values[index], values[smallest] = values[smallest], values[index]
                states.append(values.copy())
    else:
        for index in range(1, len(values)):
            key, cursor = values[index], index - 1
            while cursor >= 0 and values[cursor] > key:
                values[cursor + 1] = values[cursor]
                cursor -= 1
            values[cursor + 1] = key
            states.append(values.copy())
    return states[:12]


def cells(draw, values, y, accent, inactive=None):
    width = min(76, int(675 / max(1, len(values))))
    gap = 8
    left = 472 - (len(values) * width + (len(values) - 1) * gap) // 2
    for index, value in enumerate(values):
        x = left + index * (width + gap)
        active = inactive is None or index not in inactive
        draw.rounded_rectangle((x, y, x + width, y + 64), radius=9, fill="#173047" if active else "#101827", outline=accent if active else "#334155", width=3)
        draw.text((x + width / 2, y + 20), str(value), anchor="ma", font=font(21, True), fill="#f8fafc" if active else "#64748b")
        draw.text((x + width / 2, y + 76), str(index), anchor="ma", font=font(12), fill="#64748b")


def draw_visual(draw, scene, reveal, accent):
    visual = scene.get("visual") or {}
    kind = visual.get("type", "none")
    if kind == "array_sort":
        states = sort_states(visual.get("values") or [7, 3, 5, 2, 6, 1], visual.get("algorithm") or "insertion_sort")
        cells(draw, states[min(reveal - 1, len(states) - 1)], 300, accent)
        draw.text((82, 414), (visual.get("algorithm") or "sort").replace("_", " ").title(), font=font(16, True), fill=accent)
    elif kind == "binary_search":
        values = visual.get("values") or [2, 5, 8, 12, 16, 23, 38]
        target, low, high = visual.get("target", values[-2]), 0, len(values) - 1
        for _ in range(reveal - 1):
            middle = (low + high) // 2
            if values[middle] < target: low = middle + 1
            elif values[middle] > target: high = middle - 1
            else: break
        middle = (low + high) // 2
        cells(draw, values, 300, "#fbbf24", {i for i in range(len(values)) if not low <= i <= high})
        draw.text((82, 414), f"Target {target} • inspect index {middle}", font=font(16, True), fill=accent)
    elif kind in {"tree", "graph", "nodes", "network"}:
        names = [str(node) for node in (visual.get("nodes") or ["A", "B", "C", "D", "E"])][:8]
        if kind == "tree":
            positions = [(472, 275), (330, 340), (614, 340), (250, 410), (390, 410), (550, 410), (690, 410)]
        elif kind == "network":
            positions = [(235 + index * (474 // max(1, len(names) - 1)), 340 + 38 * (index % 2)) for index in range(len(names))]
        else:
            positions = [(472 + int(185 * math.cos(index * math.tau / len(names))), 350 + int(72 * math.sin(index * math.tau / len(names)))) for index in range(len(names))]
        lookup = dict(zip(names, positions))
        for edge in visual.get("edges", []):
            if len(edge) > 1 and str(edge[0]) in lookup and str(edge[1]) in lookup:
                draw.line((*lookup[str(edge[0])], *lookup[str(edge[1])]), fill="#475569", width=4)
        active = set(map(str, (visual.get("traversal") or names)[:reveal]))
        for name, (x, y) in lookup.items():
            color = "#34d399" if name in active else accent
            draw.ellipse((x - 25, y - 25, x + 25, y + 25), fill="#173047", outline=color, width=4)
            draw.text((x, y - 9), name, anchor="ma", font=font(17, True), fill="#f8fafc")
    elif kind in {"stack", "queue", "linked_list", "memory"}:
        values = [str(value) for value in (visual.get("values") or ["A", "B", "C", "D"])][:7]
        if kind == "stack":
            for index, value in enumerate(values[:reveal]):
                y = 408 - index * 42
                draw.rounded_rectangle((382, y, 562, y + 36), radius=7, fill="#173047", outline=accent, width=2)
                draw.text((472, y + 7), value, anchor="ma", font=font(18, True), fill="#f8fafc")
            draw.text((582, 300), "TOP", font=font(14, True), fill=accent)
        else:
            width, gap = min(105, int(630 / max(1, len(values)))), 24
            left = 472 - (len(values) * width + (len(values) - 1) * gap) // 2
            for index, value in enumerate(values):
                x = left + index * (width + gap)
                draw.rounded_rectangle((x, 315, x + width, 372), radius=8, fill="#173047", outline=accent, width=2)
                draw.text((x + width / 2, 334), value, anchor="ma", font=font(17, True), fill="#f8fafc")
                if kind == "memory" and index < len(visual.get("labels", [])):
                    draw.text((x, 383), str(visual["labels"][index]), font=font(11), fill="#94a3b8")
                if index + 1 < len(values): arrow(draw, (x + width + 2, 344), (x + width + 21, 344), accent)
            if kind == "queue":
                draw.text((left, 287), "FRONT", font=font(13, True), fill=accent)
                draw.text((left + (len(values) - 1) * (width + gap), 287), "REAR", font=font(13, True), fill=accent)
    elif kind in {"code_trace", "recursion"}:
        code = [str(line) for line in (visual.get("code") or ["for item in values:", "    total += item", "return total"])][:8]
        trace = visual.get("trace") or [{"line": min(reveal, len(code)), "variables": {}}]
        step = trace[min(reveal - 1, len(trace) - 1)]
        active_line = max(1, min(len(code), int(step.get("line", 1))))
        draw.rounded_rectangle((95, 260, 570, 438), radius=14, fill="#091525", outline="#334155", width=2)
        for index, line in enumerate(code, 1):
            y = 278 + (index - 1) * 19
            if index == active_line:
                draw.rounded_rectangle((108, y - 3, 555, y + 18), radius=4, fill="#3d3215")
            draw.text((116, y), f"{index:>2}  {line}", font=font(14), fill="#fef3c7" if index == active_line else "#bfdbfe")
        draw.rounded_rectangle((600, 260, 842, 438), radius=14, fill="#101d2d", outline=accent, width=2)
        draw.text((622, 282), "VARIABLES", font=font(15, True), fill=accent)
        variables = step.get("variables") if isinstance(step, dict) else {}
        for index, (name, value) in enumerate((variables or {}).items()):
            draw.text((622, 320 + index * 29), f"{name} = {value}", font=font(16), fill="#e2e8f0")
    elif kind == "number_line":
        values = visual.get("values") or [0, 2, 5, 3, 7]
        low, high = min(values), max(values)
        draw.line((140, 355, 800, 355), fill="#64748b", width=4)
        for value in range(int(low), int(high) + 1):
            x = 140 + int(660 * (value - low) / max(1, high - low))
            draw.line((x, 345, x, 365), fill="#94a3b8", width=2)
            draw.text((x, 378), str(value), anchor="ma", font=font(12), fill="#94a3b8")
        current = values[min(reveal - 1, len(values) - 1)]
        x = 140 + int(660 * (current - low) / max(1, high - low))
        draw.ellipse((x - 13, 328, x + 13, 354), fill=accent, outline="#f8fafc", width=2)
    elif kind in {"process", "state_machine"}:
        steps = (visual.get("steps") or scene.get("points") or ["Observe", "Understand", "Apply"])[:5]
        width, gap = min(132, int(625 / max(1, len(steps)))), 27
        left = 472 - (len(steps) * width + (len(steps) - 1) * gap) // 2
        for index, step in enumerate(steps):
            x = left + index * (width + gap)
            draw.rounded_rectangle((x, 310, x + width, 382), radius=12, fill="#173047", outline=accent if index < reveal else "#475569", width=3)
            wrapped(draw, step, (x + 8, 328), width - 16, 14, bold=True)
            if index + 1 < len(steps): arrow(draw, (x + width + 3, 346), (x + width + 24, 346), accent)
    elif kind == "engine_cycle":
        phases = visual.get("phases") or ["Intake", "Compression", "Power", "Exhaust"]
        phase = phases[(reveal - 1) % len(phases)]
        draw.rounded_rectangle((350, 266, 585, 424), radius=16, fill="#101d2d", outline="#64748b", width=4)
        piston_y = 360 if phase.lower() in {"intake", "power"} else 300
        if phase.lower() == "power": draw.ellipse((403, 278, 532, 356), fill="#f59e0b", outline="#fef3c7", width=3)
        draw.rectangle((375, piston_y, 560, piston_y + 35), fill=accent, outline="#f8fafc", width=2)
        draw.line((467, piston_y + 35, 467, 456), fill="#94a3b8", width=7)
        draw.ellipse((429, 416, 505, 492), outline="#94a3b8", width=6)
        draw.polygon([(382, 255), (417, 255), (400, 292)], fill="#60a5fa" if phase.lower() == "intake" else "#334155")
        draw.polygon([(518, 255), (553, 255), (536, 292)], fill="#fb7185" if phase.lower() == "exhaust" else "#334155")
        draw.text((625, 328), phase.upper(), font=font(24, True), fill=accent)
    elif kind in {"particles", "molecule"}:
        for index in range(min(18, max(4, int(visual.get("count", 10))))):
            x, y = 150 + (index * 97 + reveal * 19) % 650, 275 + (index * 53 + reveal * 13) % 145
            radius = 8 + index % 4
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=accent if index % 2 else "#a78bfa")
    elif kind == "bar":
        values = visual.get("values") or [2, 5, 3, 7]
        maximum, width = max(max(values), 1), min(78, int(620 / len(values)))
        left = 472 - (len(values) * width + (len(values) - 1) * 20) // 2
        for index, value in enumerate(values):
            height, x = int(120 * value / maximum), left + index * (width + 20)
            draw.rounded_rectangle((x, 414 - height, x + width, 414), radius=6, fill=accent, outline="#bae6fd", width=2)
            draw.text((x + width / 2, 390 - height), str(value), anchor="ma", font=font(14, True), fill="#f8fafc")
    else:
        for index, point in enumerate(scene.get("points", [])[:reveal]):
            y = 285 + index * 48
            draw.ellipse((90, y + 7, 100, y + 17), fill=accent)
            wrapped(draw, point, (118, y), 680, 19)


def reveal_count(scene):
    visual = scene.get("visual") or {}
    kind = visual.get("type", "none")
    if kind == "array_sort": return len(sort_states(visual.get("values") or [7, 3, 5, 2, 6, 1], visual.get("algorithm") or "insertion_sort"))
    if kind == "engine_cycle": return len(visual.get("phases") or [1, 2, 3, 4])
    if kind in {"tree", "graph", "nodes", "network"}: return max(2, len(visual.get("traversal") or []))
    if kind in {"stack", "queue", "linked_list", "memory"}: return max(2, len(visual.get("values") or []))
    if kind in {"process", "state_machine"}: return max(2, len(visual.get("steps") or scene.get("points") or []))
    if kind in {"code_trace", "recursion"}: return max(2, len(visual.get("trace") or []))
    if kind == "number_line": return max(2, len(visual.get("values") or []))
    return max(2, len(scene.get("points") or []))


def frame(storyboard: Dict[str, Any], scene_index: int, reveal: int):
    image = Image.new("RGB", SIZE, "#07101d")
    draw = ImageDraw.Draw(image)
    scene = storyboard["scenes"][scene_index]
    accent = ACCENTS.get(scene.get("accent"), ACCENTS["teal"])
    draw.ellipse((680, -190, 1100, 230), fill="#0d2634")
    draw.rounded_rectangle((54, 44, 906, 496), radius=24, fill="#0e1b2c", outline="#26384d", width=2)
    draw.rounded_rectangle((80, 72, 128, 120), radius=12, fill=accent)
    draw.text((104, 78), str(scene_index + 1), anchor="ma", font=font(24, True), fill="#07101d")
    draw.text((148, 75), "EDUNEXUS · VISUAL LESSON", font=font(15, True), fill="#8291a6")
    wrapped(draw, scene.get("title", "Concept"), (80, 136), 780, 33, "#f1f5f9", True)
    wrapped(draw, scene.get("caption", ""), (82, 192), 750, 18, "#9eacc0")
    draw_visual(draw, scene, reveal, accent)
    progress = int(780 * (scene_index + 1) / len(storyboard["scenes"]))
    draw.rounded_rectangle((82, 464, 862, 470), radius=3, fill="#223247")
    draw.rounded_rectangle((82, 464, 82 + progress, 470), radius=3, fill=accent)
    return image


def render_frames(storyboard: Dict[str, Any]) -> List[Image.Image]:
    frames = []
    for index, scene in enumerate(storyboard["scenes"]):
        count = reveal_count(scene)
        frames.extend(frame(storyboard, index, reveal) for reveal in range(1, count + 1))
        frames.append(frame(storyboard, index, count))
    return frames
