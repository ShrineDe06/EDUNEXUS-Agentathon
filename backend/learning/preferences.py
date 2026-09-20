"""Prompt guidance derived from locally stored Learn-section preferences."""

from typing import Any, Optional


def build_learn_preference_prompt(preferences: Optional[Any], response_mode: str) -> str:
    if not preferences:
        return ""

    lines = []
    if response_mode == "text":
        style = preferences.chat_style.lower().strip()
        if style == "crisp":
            lines.append("Use a crisp, direct answer with short paragraphs and only essential detail.")
        elif style == "detailed":
            lines.append("Give a detailed, step-by-step explanation with useful examples and connections.")
        custom = preferences.chat_custom_instruction.strip()[:2000]
    elif response_mode == "video":
        style = preferences.animation_style.lower().strip()
        content = preferences.animation_content.lower().strip()
        if style == "simple":
            lines.append("Use a clean, simple visual language with restrained color and minimal transitions.")
        elif style == "vibrant":
            lines.append("Use vibrant colors, strong visual contrast, energetic transitions, and interactive-looking objects while preserving clarity.")
        if content == "less":
            lines.append("Keep the animation compact: prefer 2 to 3 focused scenes and omit secondary details.")
        elif content == "more":
            lines.append("Make the animation comprehensive: prefer 5 to 7 scenes with intermediate states, examples, and a recap.")
        engine = preferences.animation_engine.lower().strip()
        if engine == "manim":
            lines.append("Set render_style to manim.")
        elif engine == "motion_graphics":
            lines.append("Set render_style to motion_graphics.")
        custom = preferences.animation_custom_instruction.strip()[:2000]
    elif response_mode == "flashcards":
        style = preferences.flashcard_style.lower().strip()
        content = preferences.flashcard_content.lower().strip()
        if style == "simple":
            lines.append("Use a simple, calm card design with minimal decorative blocks and visuals only when essential.")
        elif style == "vibrant":
            lines.append("Use vibrant accents, varied interactive blocks, and engaging visuals across the deck.")
        if content == "crisp":
            lines.append("Keep each card especially crisp: one key idea and no more than three short points.")
        elif content == "detailed":
            lines.append("Make the deck detailed with explanations, examples, and formulas where relevant while keeping each card focused.")
        custom = preferences.flashcard_custom_instruction.strip()[:2000]
    else:
        return ""

    if custom:
        lines.append(f"Additional learner instruction for this response format: {custom}")
    if not lines:
        return ""
    return (
        "\nLearn-section response preferences:\n- " + "\n- ".join(lines) +
        "\nApply these preferences only to presentation and depth. They must not override chat-session isolation, "
        "document relevance rules, safety requirements, or the required output schema.\n"
    )
