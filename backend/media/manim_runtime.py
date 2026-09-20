"""Trusted Manim runtime for structured EduNexus storyboards.

The model never writes or executes Python. It emits JSON consumed by this fixed
runtime, which keeps video generation expressive without arbitrary code execution.
"""

import json
import os

from manim import *


ACCENTS = {"teal": "#2dd4bf", "blue": "#60a5fa", "violet": "#a78bfa", "amber": "#fbbf24"}


def load_storyboard():
    path = os.environ["EDUNEXUS_STORYBOARD_FILE"]
    with open(path, "r", encoding="utf-8") as source:
        return json.load(source)


class LessonScene(Scene):
    def fitted_text(self, value, size=28, color=WHITE, width=11):
        text = Text(str(value), font_size=size, color=color)
        if text.width > width:
            text.scale_to_fit_width(width)
        return text

    def scene_header(self, scene, accent):
        title = self.fitted_text(scene.get("title", "Concept"), 38, accent, 12).to_edge(UP, buff=.28)
        caption = self.fitted_text(scene.get("caption", ""), 20, "#cbd5e1", 11).next_to(title, DOWN, buff=.13)
        self.play(FadeIn(title, shift=UP * .15), FadeIn(caption), run_time=.55)
        return VGroup(title, caption)

    def make_cell(self, value, color="#60a5fa", width=.9):
        box = RoundedRectangle(width=width, height=.9, corner_radius=.12, stroke_color=color, stroke_width=3)
        box.set_fill(color, opacity=.12)
        number = Text(str(value), font_size=27, color=WHITE).move_to(box)
        return VGroup(box, number)

    def make_array(self, values, accent):
        cells = VGroup(*[self.make_cell(value, accent) for value in values]).arrange(RIGHT, buff=.12)
        if cells.width > 11:
            cells.scale_to_fit_width(11)
        cells.move_to(DOWN * .2)
        indices = VGroup(*[Text(str(i), font_size=15, color="#64748b") for i in range(len(values))])
        for index, label in enumerate(indices):
            label.next_to(cells[index], DOWN, buff=.12)
        return cells, indices

    def set_cell_value(self, cell, value):
        replacement = Text(str(value), font_size=27, color=WHITE).move_to(cell[1])
        return Transform(cell[1], replacement)

    def animate_insertion_sort(self, values, accent):
        cells, indices = self.make_array(values, accent)
        status = Text("Start with a sorted prefix of one", font_size=20, color="#cbd5e1").to_edge(DOWN, buff=.42)
        self.play(LaggedStart(*[FadeIn(cell, shift=UP * .15) for cell in cells], lag_ratio=.08), FadeIn(indices), FadeIn(status))
        for i in range(1, len(values)):
            key = values[i]
            message = Text(f"Key {key}: compare and shift", font_size=20, color=accent).to_edge(DOWN, buff=.42)
            self.play(Transform(status, message), cells[i][0].animate.set_fill("#fbbf24", opacity=.55), run_time=.35)
            j = i - 1
            while j >= 0 and values[j] > key:
                self.play(Indicate(cells[j], color="#fb7185"), Indicate(cells[j + 1], color="#fbbf24"), run_time=.28)
                values[j + 1] = values[j]
                self.play(self.set_cell_value(cells[j + 1], values[j]), run_time=.28)
                j -= 1
            values[j + 1] = key
            self.play(self.set_cell_value(cells[j + 1], key), run_time=.28)
            self.play(*[cells[k][0].animate.set_fill("#34d399", opacity=.28) for k in range(i + 1)], run_time=.28)
        self.play(Transform(status, Text("Sorted array", font_size=22, color="#34d399").to_edge(DOWN, buff=.42)), Circumscribe(cells, color="#34d399"))
        self.wait(.5)

    def animate_bubble_sort(self, values, accent):
        cells, indices = self.make_array(values, accent)
        status = Text("Compare adjacent values", font_size=20, color="#cbd5e1").to_edge(DOWN, buff=.42)
        self.play(FadeIn(cells), FadeIn(indices), FadeIn(status))
        n = len(values)
        for end in range(n - 1, 0, -1):
            for index in range(end):
                self.play(Indicate(cells[index], color="#fbbf24"), Indicate(cells[index + 1], color="#fbbf24"), run_time=.22)
                if values[index] > values[index + 1]:
                    values[index], values[index + 1] = values[index + 1], values[index]
                    self.play(self.set_cell_value(cells[index], values[index]), self.set_cell_value(cells[index + 1], values[index + 1]), run_time=.3)
            self.play(cells[end][0].animate.set_fill("#34d399", opacity=.3), run_time=.2)
        self.play(cells[0][0].animate.set_fill("#34d399", opacity=.3), Transform(status, Text("Sorted array", font_size=22, color="#34d399").to_edge(DOWN, buff=.42)))
        self.wait(.5)

    def animate_selection_sort(self, values, accent):
        cells, indices = self.make_array(values, accent)
        status = Text("Find the minimum in the unsorted region", font_size=20, color="#cbd5e1").to_edge(DOWN, buff=.42)
        self.play(FadeIn(cells), FadeIn(indices), FadeIn(status))
        for start in range(len(values) - 1):
            minimum = start
            self.play(cells[start][0].animate.set_fill("#fbbf24", opacity=.4), run_time=.2)
            for cursor in range(start + 1, len(values)):
                self.play(Indicate(cells[cursor], color="#60a5fa"), run_time=.18)
                if values[cursor] < values[minimum]:
                    minimum = cursor
            if minimum != start:
                values[start], values[minimum] = values[minimum], values[start]
                self.play(self.set_cell_value(cells[start], values[start]), self.set_cell_value(cells[minimum], values[minimum]), run_time=.32)
            self.play(cells[start][0].animate.set_fill("#34d399", opacity=.3), run_time=.2)
        self.play(cells[-1][0].animate.set_fill("#34d399", opacity=.3), Transform(status, Text("Sorted array", font_size=22, color="#34d399").to_edge(DOWN, buff=.42)))
        self.wait(.5)

    def animate_array_sort(self, visual, accent):
        values = [int(value) for value in visual.get("values", [7, 3, 5, 2, 6, 1])][:9]
        if len(values) < 2:
            values = [7, 3, 5, 2, 6, 1]
        algorithm = visual.get("algorithm", "insertion_sort")
        if algorithm == "bubble_sort":
            self.animate_bubble_sort(values, accent)
        elif algorithm == "selection_sort":
            self.animate_selection_sort(values, accent)
        else:
            self.animate_insertion_sort(values, accent)

    def animate_binary_search(self, visual, accent):
        values = sorted([int(value) for value in visual.get("values", [2, 5, 8, 12, 16, 23, 38])])[:10]
        target = int(visual.get("target", values[len(values) // 2]))
        cells, indices = self.make_array(values, accent)
        status = Text(f"Find {target}", font_size=22, color=accent).to_edge(DOWN, buff=.42)
        self.play(FadeIn(cells), FadeIn(indices), FadeIn(status))
        low, high = 0, len(values) - 1
        while low <= high:
            mid = (low + high) // 2
            animations = []
            for index, cell in enumerate(cells):
                color = "#fbbf24" if index == mid else (accent if low <= index <= high else "#334155")
                opacity = .5 if index == mid else (.16 if low <= index <= high else .04)
                animations.append(cell[0].animate.set_stroke(color).set_fill(color, opacity=opacity))
            self.play(*animations, run_time=.4)
            self.play(Indicate(cells[mid], color="#fbbf24"), run_time=.35)
            if values[mid] == target:
                self.play(cells[mid][0].animate.set_fill("#34d399", opacity=.55), Transform(status, Text(f"Found {target} at index {mid}", font_size=22, color="#34d399").to_edge(DOWN, buff=.42)))
                break
            if values[mid] < target:
                low = mid + 1
            else:
                high = mid - 1
        self.wait(.6)

    def animate_stack_queue(self, visual, accent, mode):
        values = [str(value) for value in visual.get("values", ["A", "B", "C"])][:6]
        operations = visual.get("operations") or (["push D", "pop"] if mode == "stack" else ["enqueue D", "dequeue"])
        if mode == "stack":
            items = VGroup(*[self.make_cell(value, accent, 2.2) for value in values]).arrange(UP, buff=.1).move_to(DOWN * .2)
        else:
            items = VGroup(*[self.make_cell(value, accent, 1.4) for value in values]).arrange(RIGHT, buff=.12).move_to(DOWN * .2)
        self.play(LaggedStart(*[FadeIn(item, scale=.8) for item in items], lag_ratio=.12))
        label = Text("LIFO: top" if mode == "stack" else "FIFO: front to rear", font_size=20, color=accent).to_edge(DOWN, buff=.42)
        self.play(FadeIn(label))
        for operation in operations[:4]:
            message = Text(str(operation), font_size=22, color="#fbbf24").to_edge(DOWN, buff=.42)
            self.play(Transform(label, message), run_time=.3)
            lower = str(operation).lower()
            if ("pop" in lower or "dequeue" in lower) and len(items):
                target = items[-1] if mode == "stack" else items[0]
                self.play(FadeOut(target, shift=UP * .4 if mode == "stack" else LEFT * .4), run_time=.45)
            elif "push" in lower or "enqueue" in lower:
                value = str(operation).split()[-1]
                new_item = self.make_cell(value, "#fbbf24", 2.2 if mode == "stack" else 1.4)
                new_item.next_to(items[-1], UP if mode == "stack" else RIGHT, buff=.1)
                self.play(FadeIn(new_item, shift=DOWN * .25 if mode == "stack" else LEFT * .25), run_time=.45)
        self.wait(.5)

    def node_layout(self, names, layout="circle"):
        positions = {}
        if layout == "tree":
            presets = [[0, 1.7, 0], [-2.4, .3, 0], [2.4, .3, 0], [-3.5, -1.4, 0], [-1.2, -1.4, 0], [1.2, -1.4, 0], [3.5, -1.4, 0]]
            for index, name in enumerate(names):
                positions[str(name)] = presets[index] if index < len(presets) else [0, -2, 0]
        else:
            for index, name in enumerate(names):
                angle = PI / 2 + TAU * index / max(1, len(names))
                positions[str(name)] = [2.5 * np.cos(angle), 2.05 * np.sin(angle) - .15, 0]
        return positions

    def animate_graph(self, visual, accent, layout="circle"):
        names = [str(name) for name in (visual.get("nodes") or ["A", "B", "C", "D", "E"])[:9]]
        positions = self.node_layout(names, layout)
        node_map, nodes = {}, VGroup()
        for name in names:
            circle = Circle(radius=.38, stroke_color=accent, stroke_width=3).set_fill(accent, opacity=.13).move_to(positions[name])
            label = self.fitted_text(name, 20, WHITE, .58).move_to(circle)
            node_map[name] = VGroup(circle, label)
            nodes.add(node_map[name])
        edges = VGroup()
        raw_edges = visual.get("edges") or [[names[index], names[index + 1]] for index in range(len(names) - 1)]
        for edge in raw_edges:
            if len(edge) >= 2 and str(edge[0]) in node_map and str(edge[1]) in node_map:
                edges.add(Line(node_map[str(edge[0])].get_center(), node_map[str(edge[1])].get_center(), color="#475569", stroke_width=3))
        if len(edges):
            self.play(LaggedStart(*[Create(edge) for edge in edges], lag_ratio=.08))
        self.play(LaggedStart(*[FadeIn(node, scale=.5) for node in nodes], lag_ratio=.1))
        order = [str(name) for name in visual.get("traversal", names) if str(name) in node_map]
        trail = Text("Traversal: ", font_size=19, color="#94a3b8").to_edge(DOWN, buff=.4)
        self.play(FadeIn(trail))
        visited = []
        for name in order:
            visited.append(name)
            self.play(node_map[name][0].animate.set_fill("#34d399", opacity=.5), Indicate(node_map[name], color="#34d399"), Transform(trail, Text("Traversal: " + " -> ".join(visited), font_size=19, color="#34d399").to_edge(DOWN, buff=.4)), run_time=.38)
        self.wait(.5)

    def animate_linked_list(self, visual, accent):
        values = [str(value) for value in visual.get("values", ["10", "20", "30", "40"])][:7]
        nodes = VGroup()
        for value in values:
            value_box = Rectangle(width=1.15, height=.85, stroke_color=accent).set_fill(accent, opacity=.12)
            pointer_box = Rectangle(width=.45, height=.85, stroke_color=accent).next_to(value_box, RIGHT, buff=0)
            label = Text(value, font_size=22).move_to(value_box)
            nodes.add(VGroup(value_box, pointer_box, label))
        nodes.arrange(RIGHT, buff=.55).scale_to_fit_width(min(11, nodes.width)).move_to(DOWN * .15)
        self.play(LaggedStart(*[FadeIn(node, shift=RIGHT * .2) for node in nodes], lag_ratio=.12))
        arrows = VGroup(*[Arrow(nodes[i][1].get_right(), nodes[i + 1][0].get_left(), buff=.05, color="#94a3b8", stroke_width=3) for i in range(len(nodes) - 1)])
        if len(arrows):
            self.play(LaggedStart(*[GrowArrow(arrow) for arrow in arrows], lag_ratio=.1))
        null = Text("NULL", font_size=18, color="#fb7185").next_to(nodes[-1], RIGHT, buff=.35)
        self.play(FadeIn(null), Indicate(nodes[0], color="#34d399"))
        self.wait(.6)

    def animate_code_trace(self, visual, accent):
        lines = [str(line) for line in visual.get("code", ["for i in range(n):", "    total += values[i]"])][:10]
        code_lines = VGroup(*[Text(f"{index + 1:>2}  {line}", font="Consolas", font_size=18, color="#dbeafe") for index, line in enumerate(lines)])
        code_lines.arrange(DOWN, aligned_edge=LEFT, buff=.18).to_edge(LEFT, buff=.55).shift(DOWN * .15)
        panel = RoundedRectangle(width=4.2, height=4.1, corner_radius=.18, stroke_color="#334155").set_fill("#0b1626", opacity=.8).to_edge(RIGHT, buff=.55).shift(DOWN * .15)
        variables_title = Text("Variables", font_size=22, color=accent).next_to(panel.get_top(), DOWN, buff=.3)
        variable_text = Text("Ready", font="Consolas", font_size=19, color="#cbd5e1").next_to(variables_title, DOWN, buff=.35)
        self.play(FadeIn(code_lines), FadeIn(panel), FadeIn(variables_title), FadeIn(variable_text))
        highlight = None
        for step in visual.get("trace", [])[:12]:
            line_index = max(0, min(len(code_lines) - 1, int(step.get("line", 1)) - 1))
            new_highlight = SurroundingRectangle(code_lines[line_index], color="#fbbf24", buff=.08, corner_radius=.06)
            variables = step.get("variables", {})
            variable_value = "\n".join(f"{key} = {value}" for key, value in variables.items()) or str(step.get("note", "Step"))
            updated = Text(variable_value, font="Consolas", font_size=18, color="#cbd5e1", line_spacing=.8).next_to(variables_title, DOWN, buff=.35)
            if highlight is None:
                self.play(Create(new_highlight), Transform(variable_text, updated), run_time=.4)
            else:
                self.play(Transform(highlight, new_highlight), Transform(variable_text, updated), run_time=.4)
            highlight = new_highlight if highlight is None else highlight
        self.wait(.6)

    def animate_memory(self, visual, accent):
        values = [str(value) for value in visual.get("values", ["A", "B", "C", "D", "E"])][:9]
        addresses = visual.get("labels") or [hex(4096 + 4 * index) for index in range(len(values))]
        cells = VGroup(*[self.make_cell(value, accent, 1.05) for value in values]).arrange(RIGHT, buff=.04).move_to(DOWN * .1)
        labels = VGroup(*[Text(str(addresses[index]), font_size=13, color="#64748b").next_to(cells[index], DOWN, buff=.12) for index in range(len(cells))])
        self.play(LaggedStart(*[FadeIn(cell, shift=UP * .15) for cell in cells], lag_ratio=.1), FadeIn(labels))
        for cell in cells:
            self.play(Indicate(cell, color=accent), run_time=.18)
        self.wait(.5)

    def animate_process(self, visual, points, accent):
        steps = (visual.get("steps") or points or ["Observe", "Understand", "Apply"])[:5]
        blocks = VGroup()
        for step in steps:
            box = RoundedRectangle(width=2.15, height=1.0, corner_radius=.16, stroke_color=accent).set_fill(accent, opacity=.1)
            label = self.fitted_text(step, 20, WHITE, 1.8).move_to(box)
            blocks.add(VGroup(box, label))
        blocks.arrange(RIGHT, buff=.45).scale_to_fit_width(min(11.5, blocks.width)).move_to(DOWN * .15)
        arrows = []
        for index, block in enumerate(blocks):
            self.play(FadeIn(block, scale=.85), run_time=.35)
            if index:
                arrow = Arrow(blocks[index - 1].get_right(), block.get_left(), buff=.08, color=accent, stroke_width=3)
                arrows.append(arrow)
                self.play(GrowArrow(arrow), run_time=.25)
        self.wait(.6)

    def animate_bars(self, visual, accent):
        values = visual.get("values") or [2, 5, 3, 7]
        labels = visual.get("labels") or [str(i + 1) for i in range(len(values))]
        maximum = max(max(values), 1)
        bars = VGroup()
        for index, value in enumerate(values[:8]):
            height = .45 + 3.0 * float(value) / maximum
            bar = Rectangle(width=.7, height=height, stroke_color=accent).set_fill(accent, opacity=.55)
            value_text = Text(str(value), font_size=18).next_to(bar, UP, buff=.1)
            label = Text(str(labels[index] if index < len(labels) else index + 1), font_size=16, color="#94a3b8").next_to(bar, DOWN, buff=.12)
            bars.add(VGroup(bar, value_text, label))
        bars.arrange(RIGHT, buff=.45, aligned_edge=DOWN).move_to(DOWN * .2)
        self.play(LaggedStart(*[GrowFromEdge(group[0], DOWN) for group in bars], lag_ratio=.12))
        self.play(LaggedStart(*[FadeIn(VGroup(group[1], group[2])) for group in bars], lag_ratio=.08))
        self.wait(.6)

    def animate_number_line(self, visual, accent):
        values = visual.get("values") or [0, 2, 5, 3, 7]
        low, high = int(min(values)) - 1, int(max(values)) + 1
        line = NumberLine(x_range=[low, high, 1], length=10, include_numbers=True, color="#64748b").move_to(DOWN * .15)
        dot = Dot(line.n2p(values[0]), color=accent, radius=.12)
        self.play(Create(line), FadeIn(dot, scale=.5))
        for value in values[1:]:
            self.play(dot.animate.move_to(line.n2p(value)), run_time=.5)
        self.wait(.5)

    def animate_engine_cycle(self, visual, accent):
        phases = visual.get("phases") or ["Intake", "Compression", "Power", "Exhaust"]
        cylinder = RoundedRectangle(width=3.1, height=4.0, corner_radius=.18, stroke_color="#94a3b8", stroke_width=4).move_to(DOWN * .15)
        piston = Rectangle(width=2.65, height=.65, stroke_color=accent).set_fill(accent, opacity=.5).move_to(cylinder.get_bottom() + UP * .75)
        crank = Circle(radius=.42, stroke_color="#cbd5e1", stroke_width=4).next_to(cylinder, DOWN, buff=.15)
        rod = always_redraw(lambda: Line(piston.get_bottom(), crank.get_center(), color="#cbd5e1", stroke_width=6))
        intake_valve = Line(cylinder.get_top() + LEFT * .75, cylinder.get_top() + LEFT * .75 + DOWN * .45, color="#60a5fa", stroke_width=7)
        exhaust_valve = Line(cylinder.get_top() + RIGHT * .75, cylinder.get_top() + RIGHT * .75 + DOWN * .45, color="#fb7185", stroke_width=7)
        label = Text("Four-stroke cycle", font_size=21, color=accent).to_edge(DOWN, buff=.22)
        self.play(Create(cylinder), FadeIn(piston), Create(rod), Create(crank), Create(intake_valve), Create(exhaust_valve), FadeIn(label))
        top = cylinder.get_top() + DOWN * .85
        bottom = cylinder.get_bottom() + UP * .75
        for phase in phases[:4]:
            name = str(phase).lower()
            phase_label = Text(str(phase), font_size=23, color=accent).to_edge(DOWN, buff=.22)
            if "intake" in name:
                arrows = VGroup(*[Arrow(LEFT * 5 + UP * offset, cylinder.get_left() + UP * offset, color="#60a5fa", buff=.1) for offset in (.5, .9)])
                self.play(Transform(label, phase_label), intake_valve.animate.shift(DOWN * .22), LaggedStart(*[GrowArrow(arrow) for arrow in arrows]), piston.animate.move_to(bottom), run_time=.85)
                self.play(FadeOut(arrows), intake_valve.animate.shift(UP * .22), run_time=.3)
            elif "compression" in name:
                self.play(Transform(label, phase_label), piston.animate.move_to(top), run_time=.85)
            elif "power" in name or "combust" in name:
                spark = Star(n=8, outer_radius=.45, inner_radius=.16, color="#fbbf24", fill_opacity=.8).move_to(cylinder.get_top() + DOWN * .75)
                self.play(Transform(label, phase_label), Flash(spark.get_center(), color="#fbbf24"), FadeIn(spark, scale=.2), run_time=.35)
                self.play(piston.animate.move_to(bottom), Rotate(crank, angle=PI), FadeOut(spark), run_time=.85)
            else:
                arrows = VGroup(*[Arrow(cylinder.get_right() + UP * offset, RIGHT * 5 + UP * offset, color="#fb7185", buff=.1) for offset in (.5, .9)])
                self.play(Transform(label, phase_label), exhaust_valve.animate.shift(DOWN * .22), piston.animate.move_to(top), LaggedStart(*[GrowArrow(arrow) for arrow in arrows]), run_time=.85)
                self.play(FadeOut(arrows), exhaust_valve.animate.shift(UP * .22), run_time=.3)
        self.wait(.6)

    def animate_particles(self, visual, accent):
        count = max(3, min(18, int(visual.get("count", 10))))
        particles = VGroup(*[Dot(radius=.1, color=accent).move_to([(-4.5 + (index * 1.17) % 9), (-1.7 + (index * .83) % 3.4), 0]) for index in range(count)])
        self.play(LaggedStart(*[FadeIn(particle, scale=.2) for particle in particles], lag_ratio=.05))
        motions = [particle.animate.shift([(-1) ** index * .5, .35 if index % 3 else -.35, 0]) for index, particle in enumerate(particles)]
        self.play(*motions, run_time=1.2, rate_func=there_and_back)
        self.wait(.4)

    def animate_bullets(self, points, accent):
        items = VGroup(*[self.fitted_text("- " + point, 24, WHITE, 10) for point in (points or ["Explore the idea", "Apply it"])])
        items.arrange(DOWN, aligned_edge=LEFT, buff=.35).move_to(DOWN * .05)
        self.play(LaggedStart(*[FadeIn(item, shift=RIGHT * .2) for item in items], lag_ratio=.14))
        self.wait(.6)

    def render_visual(self, scene, accent):
        visual = scene.get("visual") or {"type": "none"}
        kind = visual.get("type", "none")
        if kind == "array_sort": self.animate_array_sort(visual, accent)
        elif kind == "binary_search": self.animate_binary_search(visual, accent)
        elif kind == "stack": self.animate_stack_queue(visual, accent, "stack")
        elif kind == "queue": self.animate_stack_queue(visual, accent, "queue")
        elif kind == "tree": self.animate_graph(visual, accent, "tree")
        elif kind in {"graph", "nodes", "network"}: self.animate_graph(visual, accent)
        elif kind == "linked_list": self.animate_linked_list(visual, accent)
        elif kind in {"code_trace", "recursion"}: self.animate_code_trace(visual, accent)
        elif kind == "memory": self.animate_memory(visual, accent)
        elif kind == "bar": self.animate_bars(visual, accent)
        elif kind in {"process", "state_machine"}: self.animate_process(visual, scene.get("points", []), accent)
        elif kind == "number_line": self.animate_number_line(visual, accent)
        elif kind == "engine_cycle": self.animate_engine_cycle(visual, accent)
        elif kind in {"particles", "molecule"}: self.animate_particles(visual, accent)
        else: self.animate_bullets(scene.get("points", []), accent)

    def construct(self):
        self.camera.background_color = "#07101d"
        storyboard = load_storyboard()
        for scene in storyboard["scenes"]:
            accent = ACCENTS.get(scene.get("accent", "teal"), "#2dd4bf")
            self.scene_header(scene, accent)
            self.render_visual(scene, accent)
            self.play(*[FadeOut(mob) for mob in self.mobjects], run_time=.35)
