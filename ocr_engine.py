"""
pipeline/ocr_engine.py
----------------------
Abstraction layer over Tesseract OCR and EasyOCR.
Selects the engine at runtime and returns raw text + confidence score.
"""

import os
import pytesseract

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

# ──────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────

def extract_text(image_path: str, engine: str = 'tesseract', lang: str = 'eng'):
    """
    Run OCR on a preprocessed image.

    Parameters
    ----------
    image_path : str
        Path to the preprocessed image.
    engine : str
        'tesseract' or 'easyocr'
    lang : str
        Language code ('eng', 'fra', 'deu', etc.)

    Returns
    -------
    text : str
        Extracted raw text.
    confidence : float
        Average confidence (0–100).
    """
    if engine == 'easyocr':
        return _run_easyocr(image_path, lang)
    else:
        return _run_tesseract(image_path, lang)


# ──────────────────────────────────────────────
# Tesseract backend
# ──────────────────────────────────────────────

def _run_tesseract(image_path: str, lang: str):
    try:
        import pytesseract
        from PIL import Image
        import pandas as pd

        img = Image.open(image_path)

        # OEM 3 = LSTM + legacy, PSM 6 = assume uniform block of text
        config = f'--oem 3 --psm 6 -l {lang}'

        # Get detailed data for confidence scoring
        data = pytesseract.image_to_data(img, config=config, output_type=pytesseract.Output.DICT)

        # Filter valid words
        words = []
        confidences = []
        for i, word in enumerate(data['text']):
            conf = int(data['conf'][i])
            if conf > 0 and word.strip():
                words.append(word)
                confidences.append(conf)

        raw_text = pytesseract.image_to_string(img, config=config)
        avg_conf = round(sum(confidences) / len(confidences), 1) if confidences else 0.0

        return raw_text.strip(), avg_conf

    except ImportError:
        raise RuntimeError(
            "pytesseract is not installed. Run: pip install pytesseract\n"
            "Also install Tesseract binary: https://github.com/tesseract-ocr/tesseract"
        )
    except Exception as e:
        raise RuntimeError(f"Tesseract OCR failed: {e}")


# ──────────────────────────────────────────────
# EasyOCR backend
# ──────────────────────────────────────────────

def _run_easyocr(image_path: str, lang: str):
    try:
        import easyocr

        # EasyOCR uses different language codes
        lang_map = {'eng': 'en', 'fra': 'fr', 'deu': 'de', 'spa': 'es', 'chi_sim': 'ch_sim'}
        easy_lang = lang_map.get(lang, 'en')

        reader = easyocr.Reader([easy_lang], gpu=False, verbose=False)
        results = reader.readtext(image_path, detail=1)

        lines = []
        confidences = []
        for (bbox, text, confidence) in results:
            if text.strip():
                lines.append(text)
                confidences.append(confidence * 100)

        raw_text = '\n'.join(lines)
        avg_conf = round(sum(confidences) / len(confidences), 1) if confidences else 0.0

        return raw_text.strip(), avg_conf

    except ImportError:
        raise RuntimeError("easyocr is not installed. Run: pip install easyocr")
    except Exception as e:
        raise RuntimeError(f"EasyOCR failed: {e}")
