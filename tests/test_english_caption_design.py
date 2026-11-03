"""English grouped subtitles keep exact word timings and bounded width."""
from __future__ import annotations

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from english_caption_design import grouped_captions


def test_two_to_three_words_per_caption_with_active_word_boundaries():
    source = [
        {"startFrame": i * 9, "endFrame": i * 9 + 8, "text": word}
        for i, word in enumerate(["One", "name.", "One", "death.", "That's", "all", "this", "notebook", "needs."])
    ]
    captions = grouped_captions(source)
    assert len(captions) >= 3
    assert all(1 <= len(c["words"]) <= 3 for c in captions)
    assert [w for group in captions for w in group["words"]] == source
    assert captions[0]["text"] == "One name. One"
    assert all(len(c["text"]) <= 23 for c in captions)


def test_long_pauses_generate_a_new_group():
    source = [
        {"startFrame": 0, "endFrame": 6, "text": "Maybe"},
        {"startFrame": 11, "endFrame": 18, "text": "a"},
        {"startFrame": 38, "endFrame": 45, "text": "coincidence?"},
    ]
    assert len(grouped_captions(source)) == 2


def test_invalid_boundary_lists_fail_closed():
    with pytest.raises(ValueError):
        grouped_captions([])
    with pytest.raises(ValueError):
        grouped_captions([{"startFrame": 4, "endFrame": 2, "text": "foo"}])
