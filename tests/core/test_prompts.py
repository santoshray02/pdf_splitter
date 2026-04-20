from __future__ import annotations

from pdf_splitter.core.models import FewShotExample, ProfileConfig
from pdf_splitter.core.prompts import DEFAULT_SYSTEM_PROMPT, compose_prompt


def test_default_only():
    prompt = compose_prompt(profile=None, user_prompt=None, examples=[])
    assert prompt == DEFAULT_SYSTEM_PROMPT


def test_profile_appended():
    p = ProfileConfig(name="p", prompt="look for Form P-II")
    prompt = compose_prompt(profile=p, user_prompt=None, examples=[])
    assert DEFAULT_SYSTEM_PROMPT in prompt
    assert "look for Form P-II" in prompt


def test_user_prompt_overrides_after_profile():
    p = ProfileConfig(name="p", prompt="profile text")
    prompt = compose_prompt(profile=p, user_prompt="user override", examples=[])
    # user prompt appears AFTER profile, winning precedence-wise
    assert prompt.index("user override") > prompt.index("profile text")


def test_few_shot_examples_appear_last(tmp_path):
    b = tmp_path / "before.png"
    b.write_bytes(b"\x89PNG\r\n\x1a\n")
    a = tmp_path / "after.png"
    a.write_bytes(b"\x89PNG\r\n\x1a\n")
    ex = [FewShotExample(before=b, after=a, is_boundary=True)]
    prompt = compose_prompt(profile=None, user_prompt="u", examples=ex)
    assert prompt.rindex("Example") > prompt.index("u")
