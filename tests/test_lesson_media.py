from backend.media.lesson_media import normalize_flashcards, normalize_storyboard, render_animated_lesson


def test_flashcard_normalization_keeps_graph_data():
    deck = normalize_flashcards({
        "title": "Complexity",
        "cards": [{
            "title": "Growth", "summary": "Compare rates", "points": ["Linear", "Quadratic"],
            "accent": "orange",
            "blocks": [{"label": "Example", "content": "n = 4", "kind": "example"}],
            "visual": {"type": "line", "labels": ["1", "2"], "values": [1, 4]},
        }],
    }, "Complexity")
    assert deck["cards"][0]["visual"]["type"] == "line"
    assert deck["cards"][0]["visual"]["values"] == [1.0, 4.0]
    assert deck["cards"][0]["accent"] == "orange"
    assert deck["cards"][0]["blocks"][0]["kind"] == "example"


def test_insertion_sort_storyboard_always_contains_an_array_animation():
    storyboard = normalize_storyboard({}, "Explain insertion sort")
    visual = storyboard["scenes"][0]["visual"]
    assert visual["type"] == "array_sort"
    assert visual["algorithm"] == "insertion_sort"
    assert visual["values"] != sorted(visual["values"])

    model_storyboard = normalize_storyboard({
        "scenes": [{"title": "Sort", "caption": "Insert values", "visual": {"type": "array_sort"}}],
    }, "Insertion sort")
    model_visual = model_storyboard["scenes"][0]["visual"]
    assert model_visual["algorithm"] == "insertion_sort"
    assert len(model_visual["values"]) >= 2


def test_storyboard_infers_specialized_visuals_and_manim_for_motion():
    expectations = {
        "Explain binary search": "binary_search",
        "Animate BFS graph traversal": "graph",
        "How does a four stroke engine work?": "engine_cycle",
        "Show a linked list": "linked_list",
    }
    for topic, expected in expectations.items():
        storyboard = normalize_storyboard({}, topic)
        assert storyboard["scenes"][0]["visual"]["type"] == expected
        assert storyboard["render_style"] == "manim"


def test_storyboard_keeps_string_values_for_data_structures():
    storyboard = normalize_storyboard({
        "render_style": "manim",
        "scenes": [{"title": "Queue", "visual": {"type": "queue", "values": ["Ada", "Linus", "Grace"]}}],
    }, "Queue")
    assert storyboard["scenes"][0]["visual"]["values"] == ["Ada", "Linus", "Grace"]


def test_animated_lesson_has_a_local_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.media.lesson_media._find_manim_executable", lambda: None)
    monkeypatch.setattr("backend.media.lesson_media.shutil.which", lambda _: None)
    monkeypatch.setitem(__import__('sys').modules, "imageio_ffmpeg", None)
    storyboard = normalize_storyboard({
        "title": "Vectors",
        "scenes": [{"title": "Direction", "caption": "A vector points somewhere", "points": ["Magnitude", "Direction"], "accent": "teal"}],
    }, "Vectors")

    result = render_animated_lesson(storyboard, str(tmp_path))

    assert result["renderer"] == "pillow"
    assert result["mime_type"] == "image/gif"
    assert (tmp_path / result["media_url"].split("/")[-1]).is_file()
