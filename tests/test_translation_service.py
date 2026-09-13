"""Regression tests for the translation service (no network required).

Run with:  Backend\\.venv\\Scripts\\python.exe -m pytest tests -q
or without pytest:  Backend\\.venv\\Scripts\\python.exe tests/test_translation_service.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Backend"))

from Services.translation_service import (  # noqa: E402
    INDIAN_LANGUAGES,
    TranslationService,
    _normalize_language_code,
    is_supported_language,
)


class RecordingTranslator:
    """Stands in for googletrans and records the batches it receives."""

    def __init__(self, failing: bool = False, short: bool = False):
        self.batches = []
        self.failing = failing
        self.short = short

    async def translate(self, texts, src="auto", dest="en"):
        self.batches.append({"texts": texts, "src": src, "dest": dest})
        if self.failing:
            raise RuntimeError("network down")
        # googletrans accepts either one destination for many texts, or many
        # destinations for a single text. Mirror both shapes.
        if isinstance(dest, (list, tuple)):
            payload = [f"{code}:{texts[0]}" for code in dest]
        else:
            payload = [f"{dest}:{text}" for text in texts]
        if self.short:
            payload = payload[:-1]
        return [type("Result", (), {"text": value})() for value in payload]


def service_with(translator):
    service = TranslationService()
    service.translator = translator
    return service


def test_language_code_normalization():
    assert _normalize_language_code("HI-in", "en") == "hi"
    assert _normalize_language_code("", "en") == "en"
    assert _normalize_language_code(None, "en") == "en"
    assert is_supported_language("ta")
    assert not is_supported_language("zz")
    print("ok: language code normalization")


def test_single_translation_success():
    translator = RecordingTranslator()
    result = asyncio.run(service_with(translator).translate_text("Storm warning", "hi"))
    assert result["success"] is True
    assert result["translated_text"] == "hi:Storm warning"
    assert result["target_language"] == "hi"
    assert len(translator.batches) == 1
    print("ok: single translation")


def test_failure_does_not_return_english():
    """A failed translation must not masquerade as a translated string."""
    result = asyncio.run(service_with(RecordingTranslator(failing=True)).translate_text("Storm warning", "hi"))
    assert result["success"] is False
    assert result["translated_text"] == ""
    assert result["error"]
    print("ok: failure returns empty text, not the source text")


def test_unsupported_language_is_not_translated():
    translator = RecordingTranslator()
    result = asyncio.run(service_with(translator).translate_text("Storm warning", "zz"))
    assert result["success"] is False
    assert "Unsupported" in result["error"]
    assert translator.batches == []
    print("ok: unsupported language rejected without a network call")


def test_batch_skips_empty_and_same_language():
    translator = RecordingTranslator()
    results = asyncio.run(
        service_with(translator).translate_batch(["One", "", "Two"], "hi", "en")
    )
    assert [r["success"] for r in results] == [True, False, True]
    assert results[1]["translated_text"] == ""
    assert translator.batches[0]["texts"] == ["One", "Two"]
    print("ok: batch skips empty strings")


def test_batch_is_single_request_for_all_languages():
    translator = RecordingTranslator()
    result = asyncio.run(service_with(translator).translate_to_all_indian_languages("Return to port.", "en"))
    # 22 Indian languages plus the English source entry.
    assert result["total_languages"] == len(INDIAN_LANGUAGES) + 1
    assert result["translations"]["english"]["text"] == "Return to port."
    assert list(result["translations"])[0] == "english"
    # All 21 non-English targets ship in a single request instead of 21 calls.
    assert len(translator.batches) == 1
    assert translator.batches[0]["texts"] == ["Return to port."]
    assert len(translator.batches[0]["dest"]) == len(INDIAN_LANGUAGES)
    assert result["translations"]["hindi"]["success"] is True
    print("ok: all-language bundle uses one batched request")


def test_batch_pads_short_responses():
    translator = RecordingTranslator(short=True)
    results = asyncio.run(service_with(translator).translate_batch(["One", "Two"], "hi"))
    assert [r["success"] for r in results] == [True, False]
    print("ok: short translator response is padded, not misaligned")


def main():
    test_language_code_normalization()
    test_single_translation_success()
    test_failure_does_not_return_english()
    test_unsupported_language_is_not_translated()
    test_batch_skips_empty_and_same_language()
    test_batch_is_single_request_for_all_languages()
    test_batch_pads_short_responses()
    print("\nall translation tests passed")


if __name__ == "__main__":
    main()
