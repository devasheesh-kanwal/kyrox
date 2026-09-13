# Backend/Services/translation_service.py
"""Translation service for KyroX Marine Safety AI."""
import asyncio
import logging
from typing import Any, Dict, Iterable, List, Optional

from googletrans import LANGUAGES, Translator

logger = logging.getLogger(__name__)

MAX_TRANSLATE_BATCH = 40
TRANSLATE_TIMEOUT_SECONDS = 15.0


# 22 Official Languages of India with their language codes
INDIAN_LANGUAGES = {
    "assamese": "as",
    "bengali": "bn",
    "bodo": "brx",
    "dogri": "doi",
    "gujarati": "gu",
    "hindi": "hi",
    "kannada": "kn",
    "kashmiri": "ks",
    "konkani": "kok",
    "maithili": "mai",
    "malayalam": "ml",
    "manipuri": "mni",
    "marathi": "mr",
    "nepali": "ne",
    "odia": "or",
    "punjabi": "pa",
    "sanskrit": "sa",
    "santali": "sat",
    "sindhi": "sd",
    "tamil": "ta",
    "telugu": "te",
    "urdu": "ur",
}

# Reverse mapping for code to name
LANGUAGE_CODE_TO_NAME = {v: k for k, v in INDIAN_LANGUAGES.items()}


def _normalize_language_code(lang: Optional[str], default: str) -> str:
    """Trim case and region suffixes (``hi-IN`` -> ``hi``)."""
    if not lang or not str(lang).strip():
        return default
    code = str(lang).strip().lower().replace("_", "-")
    return code.split("-")[0] or default


def is_supported_language(lang: Optional[str]) -> bool:
    """True when Google Translate can target this language code."""
    return _normalize_language_code(lang, "") in LANGUAGES


class TranslationService:
    """Async translation service backed by the googletrans client."""

    def __init__(self) -> None:
        self.translator = Translator()

    async def translate_text(
        self,
        text: str,
        target_lang: str = "hi",
        source_lang: str = "en",
    ) -> Dict[str, Any]:
        """Translate one string.

        Args:
            text: Text to translate.
            target_lang: Target language code (e.g. ``hi`` for Hindi).
            source_lang: Source language code (default ``en``).

        Returns a dict with ``translated_text``, ``source_language``,
        ``target_language`` and ``success``. On failure ``translated_text``
        stays empty instead of echoing the untranslated input, so callers can
        tell a failed translation apart from a genuine result.
        """
        source = _normalize_language_code(source_lang, "en")
        target = _normalize_language_code(target_lang, "hi")

        if not isinstance(text, str) or not text.strip():
            return self._failure(source, target, "Empty text provided")
        if target == source:
            return self._success(text, source, target, "skipped")
        if not is_supported_language(target):
            return self._failure(source, target, self._unsupported(target))

        return (await self._translate_chunk([text], source, target))[0]

    async def translate_batch(
        self,
        texts: Iterable[Any],
        target_lang: str = "hi",
        source_lang: str = "en",
    ) -> List[Dict[str, Any]]:
        """Translate many strings in one request, preserving the input order.

        Empty strings, same-language requests and unsupported language codes
        are resolved locally, so only genuinely translatable text is sent to
        Google.
        """
        source = _normalize_language_code(source_lang, "en")
        target = _normalize_language_code(target_lang, "hi")
        items = [item if isinstance(item, str) else "" for item in texts]

        results: List[Optional[Dict[str, Any]]] = []
        for item in items:
            if not item.strip():
                results.append(self._failure(source, target, "Empty text provided"))
            elif target == source:
                results.append(self._success(item, source, target, "skipped"))
            else:
                results.append(None)

        if not is_supported_language(target):
            reason = self._unsupported(target)
            return [result or self._failure(source, target, reason) for result in results]

        pending = [
            (index, item)
            for index, (item, result) in enumerate(zip(items, results))
            if result is None
        ]
        for offset in range(0, len(pending), MAX_TRANSLATE_BATCH):
            chunk = pending[offset:offset + MAX_TRANSLATE_BATCH]
            translated = await self._translate_chunk(
                [item for _, item in chunk], source, target
            )
            for (index, _), value in zip(chunk, translated):
                results[index] = value

        return [
            result or self._failure(source, target, "Translation skipped")
            for result in results
        ]

    async def _translate_grouped(
        self,
        text: str,
        target_languages: List[str],
        source: str,
    ) -> List[Dict[str, Any]]:
        """Translate one string into many languages with one Google request.

        googletrans accepts a list of destination languages for a single text
        argument, so the whole bundle costs one network round trip while the
        caller's ordering is preserved.
        """
        if not target_languages:
            return []

        try:
            # A one-element list is required: googletrans only pairs one text
            # with many destinations when ``texts`` itself is a list.
            response = await asyncio.wait_for(
                self.translator.translate([text], src=source, dest=target_languages),
                timeout=TRANSLATE_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            logger.warning("Google Translate timed out for %s language group", source)
            return [
                self._failure(source, code, "Google Translate timed out")
                for code in target_languages
            ]
        except Exception as exc:  # network, protocol, quota or client errors
            logger.warning("Google Translate group call failed for %s: %s", source, exc)
            return await self._translate_individually(text, target_languages, source)

        if not isinstance(response, list):
            response = [response]

        results = [
            self._to_result(item, source, lang_code)
            for item, lang_code in zip(response, target_languages)
        ]
        if len(results) != len(target_languages):
            # Unexpected shape; fall back to per-language calls rather than
            # letting missing entries silently stay English.
            logger.warning(
                "Grouped translation returned %s results for %s languages",
                len(results), len(target_languages),
            )
            return await self._translate_individually(text, target_languages, source)
        return results

    async def _translate_individually(
        self,
        text: str,
        target_languages: List[str],
        source: str,
    ) -> List[Dict[str, Any]]:
        """Translate one string per language, used if grouping is unsupported."""
        results: List[Dict[str, Any]] = []
        for lang_code in target_languages:
            (result,) = await self.translate_batch([text], lang_code, source)
            results.append(result)
        return results

    async def _translate_chunk(
        self,
        texts: List[str],
        source: str,
        target: str,
    ) -> List[Dict[str, Any]]:
        """Send one batch to Google Translate and map the reply to results."""
        if not texts:
            return []

        try:
            response = await asyncio.wait_for(
                self.translator.translate(texts, src=source, dest=target),
                timeout=TRANSLATE_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            logger.warning("Google Translate timed out for %s -> %s", source, target)
            return [
                self._failure(source, target, "Google Translate timed out")
                for _ in texts
            ]
        except Exception as exc:  # network, protocol, quota or client errors
            logger.warning(
                "Google Translate failed for %s -> %s: %s", source, target, exc
            )
            return [
                self._failure(source, target, "Google Translate is unavailable")
                for _ in texts
            ]

        if not isinstance(response, list):
            response = [response]

        batch_results = [self._to_result(item, source, target) for item in response]
        if len(batch_results) != len(texts):
            logger.warning(
                "Google Translate returned %s results for %s inputs",
                len(batch_results),
                len(texts),
            )
            batch_results.extend(
                self._failure(source, target, "Google Translate returned no text")
                for _ in range(len(texts) - len(batch_results))
            )
        return batch_results[:len(texts)]

    async def translate_to_all_indian_languages(
        self,
        text: str,
        source_lang: str = "en",
    ) -> Dict[str, Any]:
        """Translate one string into all 22 official Indian languages.

        Every non-source language is fetched in a single batched request
        instead of one request per language.
        """
        source = _normalize_language_code(source_lang, "en")
        source_text = text if isinstance(text, str) else ""

        # Every Indian language except the source one needs a translation.
        entries = [
            (lang_name, lang_code)
            for lang_name, lang_code in INDIAN_LANGUAGES.items()
            if lang_code != source
        ]
        passthrough = {"english": source_text}

        # One request per language group, so the whole bundle costs a single
        # network round trip for the 22 official languages.
        grouped = await self._translate_grouped(source_text, [code for _, code in entries], source)
        results: List[Dict[str, Any]] = grouped

        translations: Dict[str, Any] = {
            lang_name: {
                "text": passthrough_text,
                "language": lang_name,
                "code": "en",
                "success": True,
            }
            for lang_name, passthrough_text in passthrough.items()
        }
        for (lang_name, lang_code), result in zip(entries, results):
            translations[lang_name] = {
                "text": result["translated_text"],
                "language": lang_name,
                "code": lang_code,
                "success": result["success"],
            }

        # Keep the declared language order so clients can rely on it, with the
        # English passthrough first.
        ordered = {
            lang_name: translations[lang_name]
            for lang_name in ["english", *INDIAN_LANGUAGES]
            if lang_name in translations
        }
        return {
            "source_text": source_text,
            "source_language": source,
            "translations": ordered,
            "total_languages": len(ordered),
        }

    def get_supported_languages(self) -> Dict[str, str]:
        """Get dictionary of supported Indian languages."""
        return INDIAN_LANGUAGES.copy()

    def _to_result(self, item: Any, source: str, target: str) -> Dict[str, Any]:
        translated_text = getattr(item, "text", "")
        if translated_text:
            return self._success(translated_text, source, target, "googletrans")
        return self._failure(source, target, "Google Translate returned no text")

    @staticmethod
    def _unsupported(target: str) -> str:
        return f"Unsupported target language: '{target}'"

    @staticmethod
    def _success(
        translated_text: str,
        source_lang: str,
        target_lang: str,
        service: str,
    ) -> Dict[str, Any]:
        return {
            "translated_text": translated_text,
            "source_language": source_lang,
            "target_language": target_lang,
            "success": True,
            "service": service,
        }

    @staticmethod
    def _failure(source_lang: str, target_lang: str, error: str) -> Dict[str, Any]:
        return {
            "translated_text": "",
            "source_language": source_lang,
            "target_language": target_lang,
            "success": False,
            "error": error,
        }


# Global translation service instance
translation_service = TranslationService()


async def translate_text(
    text: str,
    target_lang: str = "hi",
    source_lang: str = "en",
) -> Dict[str, Any]:
    """Async convenience wrapper around the global translation service."""
    return await translation_service.translate_text(text, target_lang, source_lang)


async def translate_batch(
    texts: Iterable[str],
    target_lang: str = "hi",
    source_lang: str = "en",
) -> List[Dict[str, Any]]:
    """Async convenience wrapper for translating a list of strings."""
    return await translation_service.translate_batch(texts, target_lang, source_lang)


async def translate_to_all_indian_languages(
    text: str,
    source_lang: str = "en",
) -> Dict[str, Any]:
    """Async convenience wrapper around the global translation service."""
    return await translation_service.translate_to_all_indian_languages(text, source_lang)
