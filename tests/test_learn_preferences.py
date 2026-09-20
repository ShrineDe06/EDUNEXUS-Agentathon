from types import SimpleNamespace

from backend.learning.preferences import build_learn_preference_prompt


def preferences(**overrides):
    defaults = {
        "chat_style": "auto", "chat_custom_instruction": "",
        "animation_style": "auto", "animation_content": "auto",
        "animation_engine": "auto", "animation_custom_instruction": "",
        "flashcard_style": "auto", "flashcard_content": "auto",
        "flashcard_custom_instruction": "",
    }
    return SimpleNamespace(**{**defaults, **overrides})


def test_auto_preferences_preserve_existing_prompts():
    value = preferences()
    assert build_learn_preference_prompt(value, "text") == ""
    assert build_learn_preference_prompt(value, "video") == ""
    assert build_learn_preference_prompt(value, "flashcards") == ""


def test_preferences_are_scoped_to_the_selected_response_mode():
    value = preferences(
        chat_style="crisp",
        animation_style="vibrant",
        animation_content="more",
        animation_engine="manim",
        animation_custom_instruction="Show every comparison.",
        flashcard_content="detailed",
    )
    assert "crisp, direct" in build_learn_preference_prompt(value, "text")
    video = build_learn_preference_prompt(value, "video")
    assert "vibrant colors" in video
    assert "5 to 7 scenes" in video
    assert "render_style to manim" in video
    assert "Show every comparison" in video
    assert "detailed" in build_learn_preference_prompt(value, "flashcards")


def test_custom_instructions_are_bounded():
    prompt = build_learn_preference_prompt(preferences(chat_custom_instruction="x" * 3000), "text")
    assert prompt.count("x") == 2000
    assert "must not override chat-session isolation" in prompt
