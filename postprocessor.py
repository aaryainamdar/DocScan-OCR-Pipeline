"""
pipeline/postprocessor.py
--------------------------
NLP-based post-processing of raw OCR output.
Cleans common OCR artefacts, normalises whitespace, detects structure
(paragraphs, headings, tables, dates, emails, phone numbers, amounts).
"""

import re
import unicodedata
from datetime import datetime


# ──────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────

def clean_and_format(raw_text: str) -> dict:
    """
    Full NLP post-processing pipeline.

    Returns a structured dict with:
      - cleaned_text
      - word_count
      - char_count
      - paragraphs
      - entities  (dates, emails, phones, amounts, urls)
      - headings
      - summary   (first 200 chars of meaningful text)
    """
    text = _normalize_unicode(raw_text)
    text = _fix_common_ocr_errors(text)
    text = _normalize_whitespace(text)

    paragraphs = _split_paragraphs(text)
    headings = _detect_headings(paragraphs)
    entities = _extract_entities(text)
    word_count = len(text.split())
    char_count = len(text)

    # Simple extractive summary
    sentences = _split_sentences(text)
    summary = ' '.join(sentences[:3]) if sentences else text[:200]

    return {
        'cleaned_text': text,
        'word_count': word_count,
        'char_count': char_count,
        'line_count': text.count('\n') + 1,
        'paragraphs': paragraphs,
        'headings': headings,
        'entities': entities,
        'summary': summary,
        'processed_at': datetime.utcnow().isoformat() + 'Z'
    }


# ──────────────────────────────────────────────
# Cleaning helpers
# ──────────────────────────────────────────────

def _normalize_unicode(text: str) -> str:
    """Normalize unicode characters (e.g. ligatures, smart quotes)."""
    text = unicodedata.normalize('NFKC', text)
    # Replace curly quotes
    text = text.replace('\u2018', "'").replace('\u2019', "'")
    text = text.replace('\u201c', '"').replace('\u201d', '"')
    # Replace em/en dashes
    text = text.replace('\u2013', '-').replace('\u2014', '-')
    return text


_OCR_CORRECTIONS = [
    # Common single-character OCR mistakes
    (r'\b0(?=[a-zA-Z])', 'O'),   # 0 before letter → O
    (r'(?<=[a-zA-Z])0\b', 'O'),  # 0 after letter → O
    (r'\bl(?=\d)', '1'),          # l before digit → 1
    (r'(?<=\d)l\b', '1'),         # l after digit → 1
    (r'\|', 'I'),                 # pipe → I
    (r'(?<!\S)rn(?=\S)', 'm'),   # rn → m (common OCR artifact)
    # Repeated punctuation from noise
    (r'[.,]{3,}', '...'),
    (r'-{3,}', '---'),
    # Fix "I" confused with "l" in words
    (r'\bI(?=[a-z]{2,})', 'l'),  # Isolated I before lowercase → l
]


def _fix_common_ocr_errors(text: str) -> str:
    for pattern, replacement in _OCR_CORRECTIONS:
        text = re.sub(pattern, replacement, text)
    return text


def _normalize_whitespace(text: str) -> str:
    """Collapse multiple spaces, fix line endings, remove trailing spaces."""
    # Normalize line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # Collapse multiple blank lines → max 2
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Remove trailing spaces per line
    text = '\n'.join(line.rstrip() for line in text.split('\n'))
    # Collapse multiple spaces (but not newlines)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    return text.strip()


# ──────────────────────────────────────────────
# Structure detection
# ──────────────────────────────────────────────

def _split_paragraphs(text: str) -> list:
    """Split text into paragraphs by double newlines."""
    raw = re.split(r'\n{2,}', text)
    return [p.strip() for p in raw if p.strip() and len(p.strip()) > 5]


def _detect_headings(paragraphs: list) -> list:
    """
    Heuristic heading detection:
    - Short paragraph (< 80 chars)
    - Ends without punctuation or ends with ':'
    - Is mostly uppercase OR title-cased
    """
    headings = []
    for i, p in enumerate(paragraphs):
        first_line = p.split('\n')[0].strip()
        if len(first_line) < 80 and not first_line.endswith(('.', ',', ';')):
            if (first_line.isupper() or
                    first_line.istitle() or
                    first_line.endswith(':') or
                    re.match(r'^\d+[\.\)]\s+\w', first_line)):
                headings.append({'index': i, 'text': first_line})
    return headings


def _split_sentences(text: str) -> list:
    """Naive sentence splitter."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if len(s.strip()) > 20]


# ──────────────────────────────────────────────
# Entity extraction (regex-based NER)
# ──────────────────────────────────────────────

_ENTITY_PATTERNS = {
    'emails': r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}',
    'urls': r'https?://[^\s]+|www\.[^\s]+',
    'phone_numbers': (
        r'(?:\+\d{1,3}[\s\-]?)?'
        r'(?:\(?\d{1,4}\)?[\s\-]?)?'
        r'\d{3,4}[\s\-]?\d{3,4}[\s\-]?\d{0,4}'
    ),
    'dates': (
        r'\b(?:\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}'
        r'|\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2}'
        r'|(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?'
        r'|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
        r'[\s\.\,]+\d{1,2}[\s\.\,]+\d{4})\b'
    ),
    'monetary_amounts': r'\$\s?\d+(?:[,\d]*)?(?:\.\d{2})?|\d+(?:[,\d]*)?\s?(?:USD|EUR|GBP|INR)',
}


def _extract_entities(text: str) -> dict:
    entities = {}
    for entity_type, pattern in _ENTITY_PATTERNS.items():
        matches = list(set(re.findall(pattern, text, re.IGNORECASE)))
        # Filter noise (too short, all digits for phone etc.)
        if entity_type == 'phone_numbers':
            matches = [m for m in matches if len(re.sub(r'\D', '', m)) >= 7]
        entities[entity_type] = [m.strip() for m in matches if m.strip()]
    return entities
