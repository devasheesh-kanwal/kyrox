# Backend/Services/translation_service.py
"""
Translation Service for KyroX Marine Safety AI
Supports translation to all 22 official languages of India using open-source translation APIs
"""

import logging
import requests
from typing import Optional, Dict, Any
import json

logger = logging.getLogger(__name__)

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
    "urdu": "ur"
}

# Reverse mapping for code to name
LANGUAGE_CODE_TO_NAME = {v: k for k, v in INDIAN_LANGUAGES.items()}


class TranslationService:
    """
    Translation service using LibreTranslate (open-source translation API)
    Falls back to MyMemory Translation API if LibreTranslate is unavailable
    """
    
    def __init__(self):
        # Public LibreTranslate instances
        self.libretranslate_endpoints = [
            "https://libretranslate.com/translate",
            "https://translate.argosopentech.com/translate"
        ]
        self.mymemory_endpoint = "https://api.mymemory.translated.net/get"
        
    def translate_text(
        self, 
        text: str, 
        target_lang: str = "hi", 
        source_lang: str = "en"
    ) -> Dict[str, Any]:
        """
        Translate text to target language
        
        Args:
            text: Text to translate
            target_lang: Target language code (e.g., 'hi' for Hindi)
            source_lang: Source language code (default: 'en' for English)
            
        Returns:
            Dict with 'translated_text', 'source_language', 'target_language', 'success'
        """
        if not text or not text.strip():
            return {
                "translated_text": text,
                "source_language": source_lang,
                "target_language": target_lang,
                "success": False,
                "error": "Empty text provided"
            }
        
        # Normalize language codes
        target_lang = target_lang.lower()
        source_lang = source_lang.lower()
        
        # Try LibreTranslate first
        result = self._translate_libre(text, source_lang, target_lang)
        if result["success"]:
            return result
            
        # Fallback to MyMemory API
        result = self._translate_mymemory(text, source_lang, target_lang)
        return result
    
    def _translate_libre(
        self, 
        text: str, 
        source_lang: str, 
        target_lang: str
    ) -> Dict[str, Any]:
        """Try translation using LibreTranslate endpoints"""
        for endpoint in self.libretranslate_endpoints:
            try:
                response = requests.post(
                    endpoint,
                    data={
                        "q": text,
                        "source": source_lang,
                        "target": target_lang,
                        "format": "text"
                    },
                    timeout=5
                )
                
                if response.status_code == 200:
                    data = response.json()
                    translated_text = data.get("translatedText", text)
                    return {
                        "translated_text": translated_text,
                        "source_language": source_lang,
                        "target_language": target_lang,
                        "success": True,
                        "service": "libretranslate"
                    }
            except Exception as e:
                logger.warning(f"LibreTranslate endpoint {endpoint} failed: {e}")
                continue
                
        return {
            "translated_text": text,
            "source_language": source_lang,
            "target_language": target_lang,
            "success": False,
            "error": "LibreTranslate unavailable"
        }
    
    def _translate_mymemory(
        self, 
        text: str, 
        source_lang: str, 
        target_lang: str
    ) -> Dict[str, Any]:
        """Fallback translation using MyMemory API"""
        try:
            # MyMemory uses language pair format like "en|hi"
            lang_pair = f"{source_lang}|{target_lang}"
            
            response = requests.get(
                self.mymemory_endpoint,
                params={
                    "q": text,
                    "langpair": lang_pair
                },
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                translated_text = data.get("responseData", {}).get("translatedText", text)
                return {
                    "translated_text": translated_text,
                    "source_language": source_lang,
                    "target_language": target_lang,
                    "success": True,
                    "service": "mymemory"
                }
        except Exception as e:
            logger.warning(f"MyMemory translation failed: {e}")
            
        return {
            "translated_text": text,
            "source_language": source_lang,
            "target_language": target_lang,
            "success": False,
            "error": "Translation service unavailable"
        }
    
    def translate_to_all_indian_languages(
        self, 
        text: str, 
        source_lang: str = "en"
    ) -> Dict[str, Any]:
        """
        Translate text to all 22 official Indian languages
        
        Args:
            text: Text to translate
            source_lang: Source language code (default: 'en')
            
        Returns:
            Dict with translations for all Indian languages
        """
        translations = {}
        
        for lang_name, lang_code in INDIAN_LANGUAGES.items():
            if lang_code == source_lang:
                translations[lang_name] = {
                    "text": text,
                    "language": lang_name,
                    "code": lang_code,
                    "success": True
                }
                continue
                
            result = self.translate_text(text, lang_code, source_lang)
            translations[lang_name] = {
                "text": result["translated_text"],
                "language": lang_name,
                "code": lang_code,
                "success": result["success"]
            }
        
        return {
            "source_text": text,
            "source_language": source_lang,
            "translations": translations,
            "total_languages": len(translations)
        }
    
    def get_supported_languages(self) -> Dict[str, str]:
        """Get dictionary of supported Indian languages"""
        return INDIAN_LANGUAGES.copy()


# Global translation service instance
translation_service = TranslationService()


def translate_text(text: str, target_lang: str = "hi", source_lang: str = "en") -> Dict[str, Any]:
    """
    Convenience function to translate text
    
    Args:
        text: Text to translate
        target_lang: Target language code
        source_lang: Source language code
        
    Returns:
        Translation result dictionary
    """
    return translation_service.translate_text(text, target_lang, source_lang)


def translate_to_all_indian_languages(text: str, source_lang: str = "en") -> Dict[str, Any]:
    """
    Convenience function to translate text to all Indian languages
    
    Args:
        text: Text to translate
        source_lang: Source language code
        
    Returns:
        Dictionary with all translations
    """
    return translation_service.translate_to_all_indian_languages(text, source_lang)