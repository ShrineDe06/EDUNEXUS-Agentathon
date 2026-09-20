import json
import os
import shutil
import subprocess
import tempfile
import textwrap
import uuid
from pathlib import Path
from typing import Any, Dict, List

from PIL import Image, ImageDraw, ImageFont

from backend.media.fallback_runtime import render_frames


CANVAS_SIZE = (960, 540)


def parse_json_response(raw: str) -> Dict[str, Any]:
    cleaned = (raw or "").strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        cleaned = cleaned.rsplit("```", 1)[0]
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("The model did not return a JSON object")
    return json.loads(cleaned[start:end + 1])


def normalize_flashcards(data: Dict[str, Any], topic: str) -> Dict[str, Any]:
    cards = []
    raw_cards = data.get("cards") if isinstance(data.get("cards"), list) else []
    for index, card in enumerate(raw_cards[:8]):
        if not isinstance(card, dict):
            continue
        raw_points = card.get("points") if isinstance(card.get("points"), list) else []
        points = [str(point).strip() for point in raw_points if str(point).strip()][:5]
        visual = card.get("visual") if isinstance(card.get("visual"), dict) else {"type": "none"}
        visual_type = visual.get("type", "none")
        if visual_type not in {"none", "bar", "line", "process"}:
            visual_type = "none"
        raw_blocks = card.get("blocks") if isinstance(card.get("blocks"), list) else []
        blocks = []
        for block in raw_blocks[:4]:
            if not isinstance(block, dict):
                continue
            kind = block.get("kind") if block.get("kind") in {"fact", "example", "tip", "formula"} else "fact"
            blocks.append({
                "label": str(block.get("label") or kind.title())[:45],
                "content": str(block.get("content") or "")[:180],
                "kind": kind,
            })
        accent = card.get("accent") if card.get("accent") in {"cyan", "violet", "orange", "pink", "green"} else ["cyan", "violet", "orange", "pink", "green"][index % 5]
        cards.append({
            "id": f"card-{index + 1}",
            "title": str(card.get("title") or f"{topic} — Part {index + 1}")[:100],
            "summary": str(card.get("summary") or "Key idea")[:280],
            "points": points,
            "prompt": str(card.get("prompt") or "Tap to reveal the key points")[:160],
            "accent": accent,
            "blocks": blocks,
            "visual": {
                "type": visual_type,
                "title": str(visual.get("title") or "")[:80],
                "labels": [str(value)[:30] for value in (visual.get("labels") if isinstance(visual.get("labels"), list) else [])[:7]],
                "values": [float(value) for value in (visual.get("values") if isinstance(visual.get("values"), list) else [])[:7] if isinstance(value, (int, float))],
                "steps": [str(value)[:50] for value in (visual.get("steps") if isinstance(visual.get("steps"), list) else [])[:6]],
            },
        })
    if not cards:
        cards = [{
            "id": "card-1", "title": topic, "summary": "Core concept",
            "points": ["Review the concept", "Connect it to an example", "Check your understanding"],
            "prompt": "Tap to reveal", "visual": {"type": "none", "title": "", "labels": [], "values": [], "steps": []},
            "accent": "cyan", "blocks": [{"label": "Try it", "content": "Connect this idea to a concrete example.", "kind": "example"}],
        }]
    return {"title": str(data.get("title") or topic)[:120], "cards": cards}


def _inferred_visual(topic: str) -> Dict[str, Any]:
    query = topic.lower()
    base = {"algorithm": "", "values": [], "labels": [], "steps": [], "nodes": [], "edges": [], "operations": [], "traversal": [], "code": [], "trace": [], "phases": [], "target": None, "count": 10}
    if "insertion sort" in query:
        return {**base, "type": "array_sort", "algorithm": "insertion_sort", "values": [7, 3, 5, 2, 6, 1]}
    if "bubble sort" in query:
        return {**base, "type": "array_sort", "algorithm": "bubble_sort", "values": [6, 2, 7, 3, 5, 1]}
    if "selection sort" in query:
        return {**base, "type": "array_sort", "algorithm": "selection_sort", "values": [8, 4, 6, 2, 7, 1]}
    if "binary search" in query:
        return {**base, "type": "binary_search", "values": [2, 5, 8, 12, 16, 23, 38], "target": 23}
    if "linked list" in query:
        return {**base, "type": "linked_list", "values": ["10", "20", "30", "40"]}
    if "stack" in query:
        return {**base, "type": "stack", "values": ["A", "B", "C"], "operations": ["push D", "pop"]}
    if "queue" in query:
        return {**base, "type": "queue", "values": ["A", "B", "C"], "operations": ["enqueue D", "dequeue"]}
    if any(term in query for term in ["binary tree", "bst", "tree traversal", "heap"]):
        return {**base, "type": "tree", "nodes": ["10", "5", "15", "3", "7", "12", "18"], "edges": [["10", "5"], ["10", "15"], ["5", "3"], ["5", "7"], ["15", "12"], ["15", "18"]], "traversal": ["3", "5", "7", "10", "12", "15", "18"]}
    if any(term in query for term in ["graph", "bfs", "dfs", "dijkstra"]):
        return {**base, "type": "graph", "nodes": ["A", "B", "C", "D", "E"], "edges": [["A", "B"], ["A", "C"], ["B", "D"], ["C", "D"], ["D", "E"]], "traversal": ["A", "B", "C", "D", "E"]}
    if any(term in query for term in ["network", "packet", "tcp", "routing"]):
        return {**base, "type": "network", "nodes": ["Client", "Router", "Server"], "edges": [["Client", "Router"], ["Router", "Server"]], "traversal": ["Client", "Router", "Server"]}
    if any(term in query for term in ["recursion", "call stack", "code trace", "loop"]):
        return {**base, "type": "code_trace", "code": ["result = 1", "for i in range(1, n + 1):", "    result *= i", "return result"], "trace": [{"line": 1, "variables": {"result": 1}}, {"line": 2, "variables": {"i": 1}}, {"line": 3, "variables": {"result": 1}}, {"line": 2, "variables": {"i": 2}}, {"line": 3, "variables": {"result": 2}}]}
    if any(term in query for term in ["memory", "array layout", "pointer", "cache"]):
        return {**base, "type": "memory", "values": ["A", "B", "C", "D", "E"], "labels": ["0x1000", "0x1004", "0x1008", "0x100C", "0x1010"]}
    if any(term in query for term in ["four stroke", "4 stroke", "combustion engine", "engine working"]):
        return {**base, "type": "engine_cycle", "phases": ["Intake", "Compression", "Power", "Exhaust"]}
    if any(term in query for term in ["atom", "molecule", "gas", "particle"]):
        return {**base, "type": "particles", "count": 12}
    return {**base, "type": "process", "steps": ["Introduce", "Visualize", "Connect", "Apply"]}


def normalize_storyboard(data: Dict[str, Any], topic: str) -> Dict[str, Any]:
    scenes = []
    raw_scenes = data.get("scenes") if isinstance(data.get("scenes"), list) else []
    for scene in raw_scenes[:7]:
        if not isinstance(scene, dict):
            continue
        raw_points = scene.get("points") if isinstance(scene.get("points"), list) else []
        points = [str(point).strip() for point in raw_points if str(point).strip()][:4]
        raw_visual = scene.get("visual") if isinstance(scene.get("visual"), dict) else {}
        visual_type = raw_visual.get("type", "none")
        allowed_visuals = {"none", "array_sort", "binary_search", "stack", "queue", "tree", "graph", "nodes", "linked_list", "code_trace", "recursion", "memory", "state_machine", "network", "bar", "process", "number_line", "engine_cycle", "particles", "molecule"}
        if visual_type not in allowed_visuals:
            visual_type = "none"
        raw_values = raw_visual.get("values") if isinstance(raw_visual.get("values"), list) else []
        if visual_type in {"array_sort", "binary_search", "bar", "number_line"}:
            values = [float(value) for value in raw_values[:10] if isinstance(value, (int, float))]
            if visual_type == "array_sort":
                values = [int(value) for value in values]
        else:
            values = [str(value)[:24] for value in raw_values[:10] if isinstance(value, (str, int, float))]
        raw_labels = raw_visual.get("labels") if isinstance(raw_visual.get("labels"), list) else []
        raw_steps = raw_visual.get("steps") if isinstance(raw_visual.get("steps"), list) else []
        raw_nodes = raw_visual.get("nodes") if isinstance(raw_visual.get("nodes"), list) else []
        raw_edges = raw_visual.get("edges") if isinstance(raw_visual.get("edges"), list) else []
        raw_operations = raw_visual.get("operations") if isinstance(raw_visual.get("operations"), list) else []
        raw_traversal = raw_visual.get("traversal") if isinstance(raw_visual.get("traversal"), list) else []
        raw_code = raw_visual.get("code") if isinstance(raw_visual.get("code"), list) else []
        raw_trace = raw_visual.get("trace") if isinstance(raw_visual.get("trace"), list) else []
        raw_phases = raw_visual.get("phases") if isinstance(raw_visual.get("phases"), list) else []
        algorithm = raw_visual.get("algorithm") if raw_visual.get("algorithm") in {"insertion_sort", "bubble_sort", "selection_sort"} else ""
        target = raw_visual.get("target") if isinstance(raw_visual.get("target"), (int, float)) else None
        scenes.append({
            "title": str(scene.get("title") or topic)[:80],
            "caption": str(scene.get("caption") or "")[:220],
            "points": points,
            "accent": str(scene.get("accent") or "teal") if scene.get("accent") in {"teal", "blue", "violet", "amber"} else "teal",
            "visual": {
                "type": visual_type,
                "algorithm": algorithm,
                "values": values,
                "labels": [str(label)[:24] for label in raw_labels[:10]],
                "steps": [str(step)[:45] for step in raw_steps[:6]],
                "nodes": [str(node)[:24] for node in raw_nodes[:8]],
                "edges": [edge[:2] for edge in raw_edges[:10] if isinstance(edge, list) and len(edge) >= 2],
                "operations": [str(operation)[:45] for operation in raw_operations[:8]],
                "traversal": [str(node)[:24] for node in raw_traversal[:10]],
                "code": [str(line)[:100] for line in raw_code[:12]],
                "trace": [step for step in raw_trace[:14] if isinstance(step, dict)],
                "phases": [str(phase)[:30] for phase in raw_phases[:6]],
                "target": target,
                "count": int(raw_visual.get("count", 10)) if isinstance(raw_visual.get("count", 10), (int, float)) else 10,
            },
        })
    if not scenes:
        scenes = [
            {"title": topic, "caption": "A concise visual introduction", "points": ["Core idea", "How it works"], "accent": "teal", "visual": _inferred_visual(topic)},
            {"title": "Put it together", "caption": "Connect the idea to a practical example", "points": ["Observe", "Apply", "Reflect"], "accent": "blue", "visual": {**_inferred_visual("general process"), "steps": ["Observe", "Apply", "Reflect"]}},
        ]
    if "insertion sort" in topic.lower():
        array_scenes = [scene for scene in scenes if scene["visual"]["type"] == "array_sort"]
        if array_scenes:
            for scene in array_scenes:
                scene["visual"]["algorithm"] = "insertion_sort"
                if len(scene["visual"]["values"]) < 2:
                    scene["visual"]["values"] = [7, 3, 5, 2, 6, 1]
        else:
            scenes.insert(0, {
                "title": "Insertion sort in motion",
                "caption": "Grow a sorted prefix by inserting one value at a time.",
                "points": ["Pick the next key", "Shift larger values", "Insert the key"],
                "accent": "amber",
                "visual": {"type": "array_sort", "algorithm": "insertion_sort", "values": [7, 3, 5, 2, 6, 1], "labels": [], "steps": [], "nodes": [], "edges": []},
            })
    if scenes and all(scene["visual"]["type"] == "none" for scene in scenes):
        scenes[0]["visual"] = _inferred_visual(topic)
    dynamic_types = {"array_sort", "binary_search", "stack", "queue", "tree", "graph", "linked_list", "code_trace", "recursion", "memory", "network", "engine_cycle", "particles", "molecule", "number_line"}
    requested_style = data.get("render_style") if data.get("render_style") in {"manim", "motion_graphics", "auto"} else "auto"
    if any(scene["visual"]["type"] in dynamic_types for scene in scenes):
        requested_style = "manim"
    return {"title": str(data.get("title") or topic)[:120], "render_style": requested_style, "scenes": scenes}


def _font(size: int, bold: bool = False):
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def _wrapped(draw: ImageDraw.ImageDraw, text: str, box, font, fill, spacing=8):
    x, y, width = box
    approximate_chars = max(18, int(width / max(8, getattr(font, "size", 18) * .56)))
    lines = textwrap.wrap(text, width=approximate_chars) or [""]
    draw.multiline_text((x, y), "\n".join(lines), font=font, fill=fill, spacing=spacing)
    return len(lines)


def _draw_frame(storyboard: Dict[str, Any], scene_index: int, reveal: int) -> Image.Image:
    image = Image.new("RGB", CANVAS_SIZE, "#07101d")
    draw = ImageDraw.Draw(image)
    accent_map = {"teal": "#2dd4bf", "blue": "#60a5fa", "violet": "#a78bfa", "amber": "#fbbf24"}
    scene = storyboard["scenes"][scene_index]
    accent = accent_map[scene["accent"]]
    draw.ellipse((680, -190, 1100, 230), fill="#0d2634")
    draw.rounded_rectangle((54, 44, 906, 496), radius=24, fill="#0e1b2c", outline="#26384d", width=2)
    draw.rounded_rectangle((80, 72, 128, 120), radius=12, fill=accent)
    draw.text((95, 77), str(scene_index + 1), font=_font(25, True), fill="#07101d")
    draw.text((148, 74), "EDUNEXUS · ANIMATED LESSON", font=_font(16, True), fill="#8291a6")
    _wrapped(draw, scene["title"], (80, 145, 780), _font(39, True), "#f1f5f9", 6)
    _wrapped(draw, scene["caption"], (82, 214, 750), _font(22), "#9eacc0", 6)
    y = 310
    for point_index, point in enumerate(scene["points"][:reveal]):
        draw.ellipse((84, y + 7, 94, y + 17), fill=accent)
        _wrapped(draw, point, (112, y, 700), _font(21), "#dbe5f1", 5)
        y += 55
    progress_width = int(780 * ((scene_index + 1) / len(storyboard["scenes"])))
    draw.rounded_rectangle((82, 464, 862, 470), radius=3, fill="#223247")
    draw.rounded_rectangle((82, 464, 82 + progress_width, 470), radius=3, fill=accent)
    return image


def _frames(storyboard: Dict[str, Any]) -> List[Image.Image]:
    return render_frames(storyboard)


def _safe_manim_script(storyboard: Dict[str, Any]) -> str:
    payload = json.dumps(storyboard, ensure_ascii=True)
    template = '''from manim import *
import json

STORYBOARD = json.loads(__PAYLOAD__)
ACCENTS = {"teal": "#2dd4bf", "blue": "#60a5fa", "violet": "#a78bfa", "amber": "#fbbf24"}

class LessonScene(Scene):
    def fitted_text(self, value, size=28, color=WHITE, width=11):
        text = Text(str(value), font_size=size, color=color)
        if text.width > width:
            text.scale_to_fit_width(width)
        return text

    def make_cell(self, value, color="#60a5fa"):
        box = RoundedRectangle(width=.9, height=.9, corner_radius=.12, stroke_color=color, stroke_width=3)
        box.set_fill(color, opacity=.12)
        number = Text(str(value), font_size=28, color=WHITE).move_to(box)
        return VGroup(box, number)

    def animate_array_sort(self, visual, accent):
        values = [int(value) for value in visual.get("values", [7, 3, 5, 2, 6, 1])][:8]
        if len(values) < 2:
            values = [7, 3, 5, 2, 6, 1]
        cells = VGroup(*[self.make_cell(value, accent) for value in values]).arrange(RIGHT, buff=.12).move_to(DOWN * .25)
        indices = VGroup(*[Text(str(i), font_size=16, color="#64748b") for i in range(len(values))])
        for index, label in enumerate(indices):
            label.next_to(cells[index], DOWN, buff=.14)
        status = Text("Start with the second value", font_size=22, color="#cbd5e1").to_edge(DOWN, buff=.55)
        self.play(LaggedStart(*[FadeIn(cell, shift=UP * .15) for cell in cells], lag_ratio=.09), FadeIn(indices), FadeIn(status))
        for i in range(1, len(values)):
            key = values[i]
            next_status = Text(f"Insert key {key} into the sorted prefix", font_size=22, color=accent).to_edge(DOWN, buff=.55)
            self.play(Transform(status, next_status), cells[i][0].animate.set_fill("#fbbf24", opacity=.55), run_time=.45)
            j = i - 1
            while j >= 0 and values[j] > key:
                self.play(Indicate(cells[j], color="#fb7185"), Indicate(cells[j + 1], color="#fbbf24"), run_time=.35)
                values[j + 1] = values[j]
                replacement = Text(str(values[j]), font_size=28, color=WHITE).move_to(cells[j + 1][1])
                self.play(Transform(cells[j + 1][1], replacement), run_time=.35)
                j -= 1
            values[j + 1] = key
            replacement = Text(str(key), font_size=28, color=WHITE).move_to(cells[j + 1][1])
            self.play(Transform(cells[j + 1][1], replacement), run_time=.35)
            self.play(*[cells[k][0].animate.set_fill("#34d399", opacity=.28) for k in range(i + 1)], run_time=.35)
        final_status = Text("Sorted array", font_size=24, color="#34d399").to_edge(DOWN, buff=.55)
        self.play(Transform(status, final_status), Circumscribe(cells, color="#34d399"), run_time=.7)
        self.wait(.7)

    def animate_process(self, visual, points, accent):
        steps = (visual.get("steps") or points or ["Observe", "Understand", "Apply"])[:5]
        blocks = VGroup()
        for step in steps:
            box = RoundedRectangle(width=2.15, height=1.0, corner_radius=.16, stroke_color=accent).set_fill(accent, opacity=.1)
            label = self.fitted_text(step, 20, WHITE, 1.8).move_to(box)
            blocks.add(VGroup(box, label))
        blocks.arrange(RIGHT, buff=.45).scale_to_fit_width(min(11.5, blocks.width)).move_to(DOWN * .2)
        for index, block in enumerate(blocks):
            self.play(FadeIn(block, scale=.85), run_time=.4)
            if index:
                arrow = Arrow(blocks[index - 1].get_right(), block.get_left(), buff=.08, color=accent, stroke_width=3)
                self.play(GrowArrow(arrow), run_time=.3)
        self.wait(.7)

    def animate_bars(self, visual, accent):
        values = visual.get("values") or [2, 5, 3, 7]
        labels = visual.get("labels") or [str(i + 1) for i in range(len(values))]
        maximum = max(max(values), 1)
        bars = VGroup()
        for index, value in enumerate(values[:8]):
            height = .45 + 3.0 * float(value) / maximum
            bar = Rectangle(width=.7, height=height, stroke_color=accent).set_fill(accent, opacity=.55)
            value_text = Text(str(value), font_size=18, color=WHITE).next_to(bar, UP, buff=.1)
            label = Text(str(labels[index] if index < len(labels) else index + 1), font_size=16, color="#94a3b8").next_to(bar, DOWN, buff=.12)
            bars.add(VGroup(bar, value_text, label))
        bars.arrange(RIGHT, buff=.45, aligned_edge=DOWN).move_to(DOWN * .25)
        self.play(LaggedStart(*[GrowFromEdge(group[0], DOWN) for group in bars], lag_ratio=.14))
        self.play(LaggedStart(*[FadeIn(VGroup(group[1], group[2])) for group in bars], lag_ratio=.1))
        self.wait(.8)

    def animate_nodes(self, visual, accent):
        names = (visual.get("nodes") or ["A", "B", "C", "D"])[:8]
        node_map, nodes = {}, VGroup()
        for index, name in enumerate(names):
            angle = PI / 2 + TAU * index / len(names)
            circle = Circle(radius=.42, stroke_color=accent, stroke_width=3).set_fill(accent, opacity=.15)
            circle.move_to([2.15 * np.cos(angle), 2.15 * np.sin(angle) - .25, 0])
            label = self.fitted_text(name, 22, WHITE, .62).move_to(circle)
            group = VGroup(circle, label)
            node_map[str(name)] = group
            nodes.add(group)
        edges = VGroup()
        for edge in visual.get("edges", []):
            if len(edge) >= 2 and str(edge[0]) in node_map and str(edge[1]) in node_map:
                edges.add(Line(node_map[str(edge[0])].get_center(), node_map[str(edge[1])].get_center(), color="#475569", stroke_width=3))
        if len(edges):
            self.play(LaggedStart(*[Create(edge) for edge in edges], lag_ratio=.1))
        self.play(LaggedStart(*[FadeIn(node, scale=.5) for node in nodes], lag_ratio=.12))
        self.play(LaggedStart(*[Indicate(node, color=accent) for node in nodes], lag_ratio=.12))
        self.wait(.7)

    def animate_number_line(self, visual, accent):
        values = visual.get("values") or [0, 2, 5, 3, 7]
        low, high = int(min(values)) - 1, int(max(values)) + 1
        line = NumberLine(x_range=[low, high, 1], length=10, include_numbers=True, color="#64748b").move_to(DOWN * .25)
        dot = Dot(line.n2p(values[0]), color=accent, radius=.12)
        self.play(Create(line), FadeIn(dot, scale=.5))
        for value in values[1:]:
            self.play(dot.animate.move_to(line.n2p(value)), run_time=.55)
        self.wait(.7)

    def animate_bullets(self, points, accent):
        items = VGroup(*[self.fitted_text("- " + point, 24, WHITE, 10) for point in (points or ["Explore the idea", "Apply it"])])
        items.arrange(DOWN, aligned_edge=LEFT, buff=.35).move_to(DOWN * .1)
        self.play(LaggedStart(*[FadeIn(item, shift=RIGHT * .2) for item in items], lag_ratio=.16))
        self.wait(.8)

    def construct(self):
        self.camera.background_color = "#07101d"
        for index, scene in enumerate(STORYBOARD["scenes"]):
            accent = ACCENTS.get(scene.get("accent", "teal"), "#2dd4bf")
            title = self.fitted_text(scene["title"], 40, accent, 12).to_edge(UP, buff=.35)
            caption = self.fitted_text(scene["caption"], 21, "#cbd5e1", 11).next_to(title, DOWN, buff=.18)
            self.play(FadeIn(title, shift=UP * .2), FadeIn(caption), run_time=.65)
            visual = scene.get("visual") or {"type": "none"}
            visual_type = visual.get("type", "none")
            if visual_type == "array_sort" and visual.get("algorithm") == "insertion_sort":
                self.animate_array_sort(visual, accent)
            elif visual_type == "bar":
                self.animate_bars(visual, accent)
            elif visual_type == "process":
                self.animate_process(visual, scene.get("points", []), accent)
            elif visual_type == "nodes":
                self.animate_nodes(visual, accent)
            elif visual_type == "number_line":
                self.animate_number_line(visual, accent)
            else:
                self.animate_bullets(scene.get("points", []), accent)
            self.play(*[FadeOut(mob) for mob in self.mobjects], run_time=.45)
'''
    return template.replace("__PAYLOAD__", json.dumps(payload))


def _find_manim_executable() -> str | None:
    configured = os.getenv("MANIM_EXECUTABLE")
    candidates = [
        configured,
        shutil.which("manim"),
        str(Path(__file__).resolve().parents[2] / ".venv-manim" / "Scripts" / "manim.exe"),
        str(Path(__file__).resolve().parents[2] / ".venv-manim" / "bin" / "manim"),
    ]
    return next((candidate for candidate in candidates if candidate and os.path.isfile(candidate)), None)


def _render_manim(storyboard: Dict[str, Any], output_dir: Path, stem: str) -> Path | None:
    executable = _find_manim_executable()
    if not executable:
        return None
    with tempfile.TemporaryDirectory() as temp_dir:
        storyboard_file = Path(temp_dir) / "storyboard.json"
        storyboard_file.write_text(json.dumps(storyboard, ensure_ascii=False), encoding="utf-8")
        runtime = Path(__file__).with_name("manim_runtime.py")
        environment = os.environ.copy()
        environment["EDUNEXUS_STORYBOARD_FILE"] = str(storyboard_file)
        try:
            subprocess.run(
                [executable, "-ql", str(runtime), "LessonScene", "--media_dir", str(output_dir), "-o", f"{stem}.mp4"],
                check=True, capture_output=True, text=True, timeout=240, env=environment,
            )
        except (subprocess.SubprocessError, OSError):
            return None
    matches = list(output_dir.rglob(f"{stem}.mp4"))
    if not matches:
        return None
    destination = output_dir / f"{stem}.mp4"
    if matches[0] != destination:
        shutil.copy2(matches[0], destination)
    return destination


def _render_ffmpeg(storyboard: Dict[str, Any], output_dir: Path, stem: str) -> Path | None:
    executable = shutil.which("ffmpeg")
    if not executable:
        try:
            import imageio_ffmpeg
            executable = imageio_ffmpeg.get_ffmpeg_exe()
        except (ImportError, RuntimeError, OSError):
            executable = None
    if not executable:
        return None
    frames = _frames(storyboard)
    with tempfile.TemporaryDirectory() as temp_dir:
        for index, frame in enumerate(frames):
            frame.save(Path(temp_dir) / f"frame_{index:03d}.png")
        destination = output_dir / f"{stem}.mp4"
        try:
            subprocess.run(
                [executable, "-y", "-framerate", "1", "-i", str(Path(temp_dir) / "frame_%03d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p", str(destination)],
                check=True, capture_output=True, text=True, timeout=120,
            )
            return destination
        except (subprocess.SubprocessError, OSError):
            return None


def _render_gif(storyboard: Dict[str, Any], output_dir: Path, stem: str) -> Path:
    frames = _frames(storyboard)
    destination = output_dir / f"{stem}.gif"
    durations = [900] * len(frames)
    durations[-1] = 1800
    frames[0].save(destination, save_all=True, append_images=frames[1:], duration=durations, loop=0, optimize=True)
    return destination


def render_animated_lesson(storyboard: Dict[str, Any], output_dir: str) -> Dict[str, Any]:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    stem = f"lesson_{uuid.uuid4().hex}"
    style = storyboard.get("render_style", "auto")
    attempts = [
        ("ffmpeg", _render_ffmpeg),
        ("manim", _render_manim),
    ] if style == "motion_graphics" else [
        ("manim", _render_manim),
        ("ffmpeg", _render_ffmpeg),
    ]
    rendered, renderer = None, "pillow"
    for candidate_name, candidate in attempts:
        rendered = candidate(storyboard, directory, stem)
        if rendered is not None:
            renderer = candidate_name
            break
    if rendered is None:
        rendered = _render_gif(storyboard, directory, stem)
    mime_type = "video/mp4" if rendered.suffix == ".mp4" else "image/gif"
    return {
        "title": storyboard["title"],
        "media_url": f"/api/learn/media/{rendered.name}",
        "mime_type": mime_type,
        "renderer": renderer,
        "storyboard": storyboard,
    }
