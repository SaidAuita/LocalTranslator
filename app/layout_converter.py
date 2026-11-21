"""
Bidirectional Keyboard Layout Converter (QWERTY <-> ЙЦУКЕН)
Provides Punto Switcher style layout switching and auto-detection of mistyped layout.
"""
import re
from typing import Tuple

EN_LOWER = "`1234567890-=\\qwertyuiop[]asdfghjkl;'zxcvbnm,./"
RU_LOWER = "ё1234567890-=\\йцукенгшщзхъфывапролджэячсмитьбю."

EN_UPPER = "~!@#$%^&*()_+|QWERTYUIOP{}ASDFGHJKL:\"ZXCVBNM<>?"
RU_UPPER = "Ё!\"№;%:?*()_+/ЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮ,"

EN_TO_RU = {}
RU_TO_EN = {}

for e, r in zip(EN_LOWER, RU_LOWER):
    EN_TO_RU[e] = r
    RU_TO_EN[r] = e

for e, r in zip(EN_UPPER, RU_UPPER):
    EN_TO_RU[e] = r
    RU_TO_EN[r] = e

# Common Russian frequent words/roots (in lower case)
COMMON_RU_WORDS = {
    "привет", "как", "дела", "что", "это", "для", "на", "по", "не", "от", "из",
    "до", "со", "же", "ли", "бы", "мы", "вы", "он", "она", "они", "все", "всё",
    "был", "была", "были", "быть", "если", "тоже", "также", "очень", "когда",
    "может", "время", "день", "человек", "работа", "слово", "место", "друг",
    "дело", "жизнь", "мир", "тест", "проверка", "файл", "текст", "перевод",
    "компьютер", "программа", "окно", "настройки", "сообщение", "кнопка",
    "папка", "документ", "поиск", "страница", "пользователь", "сервер", "код"
}

# Common English frequent words (in lower case)
COMMON_EN_WORDS = {
    "the", "be", "to", "of", "and", "a", "in", "that", "have", "i", "it", "for",
    "not", "on", "with", "he", "as", "you", "do", "at", "this", "but", "his",
    "by", "from", "they", "we", "say", "her", "she", "or", "an", "will", "my",
    "one", "all", "would", "there", "their", "what", "so", "up", "out", "if",
    "about", "who", "get", "which", "go", "me", "when", "make", "can", "like",
    "time", "no", "just", "him", "know", "take", "people", "into", "year",
    "your", "good", "some", "could", "them", "see", "other", "than", "then",
    "now", "look", "only", "come", "its", "over", "think", "also", "back",
    "after", "use", "two", "how", "our", "work", "first", "well", "way", "even",
    "new", "want", "because", "any", "these", "give", "day", "most", "us",
    "hello", "world", "test", "file", "text", "translate", "computer", "code",
    "settings", "window", "message", "button", "folder", "search", "page"
}

RE_LATIN = re.compile(r'[a-zA-Z]')
RE_CYRILLIC = re.compile(r'[а-яА-ЯёЁ]')
RE_EN_VOWELS = re.compile(r'[aeiouyAEIOUY]')
RE_RU_VOWELS = re.compile(r'[аеёиоуыэюяАЕЁИОУЫЭЮЯ]')


def convert_en_to_ru(text: str) -> str:
    """Convert string from English QWERTY layout to Russian ЙЦУКЕН layout."""
    if not text:
        return ""
    return "".join(EN_TO_RU.get(c, c) for c in text)


def convert_ru_to_en(text: str) -> str:
    """Convert string from Russian ЙЦУКЕН layout to English QWERTY layout."""
    if not text:
        return ""
    return "".join(RU_TO_EN.get(c, c) for c in text)


def toggle_layout(text: str) -> str:
    """
    Unconditionally flip layout of every character.
    Latin characters turn into Cyrillic, Cyrillic turn into Latin.
    """
    if not text:
        return ""
    res = []
    for c in text:
        if c in EN_TO_RU and RE_LATIN.match(c):
            res.append(EN_TO_RU[c])
        elif c in RU_TO_EN and RE_CYRILLIC.match(c):
            res.append(RU_TO_EN[c])
        elif c in EN_TO_RU:
            # Punctuation / symbol
            res.append(EN_TO_RU[c])
        else:
            res.append(c)
    return "".join(res)


def convert_layout(text: str, direction: str = "auto") -> str:
    """
    Convert layout with automatic or explicit direction.
    direction: "auto" | "en_to_ru" | "ru_to_en"
    """
    if not text:
        return ""

    if direction == "en_to_ru":
        return convert_en_to_ru(text)
    if direction == "ru_to_en":
        return convert_ru_to_en(text)

    # Auto: determine by character frequency
    lat_count = len(RE_LATIN.findall(text))
    cyr_count = len(RE_CYRILLIC.findall(text))

    if lat_count >= cyr_count and lat_count > 0:
        return convert_en_to_ru(text)
    elif cyr_count > 0:
        return convert_ru_to_en(text)

    return toggle_layout(text)


def is_probably_wrong_layout(
    text: str,
    src_lang: str = "auto",
    tgt_lang: str = "auto"
) -> Tuple[bool, str, str]:
    """
    Intelligently detect if text was typed in the wrong keyboard layout.
    Returns:
        (is_wrong: bool, fixed_text: str, direction: str)
        direction is "en_to_ru" or "ru_to_en" or ""
    """
    if not text or len(text.strip()) == 0:
        return False, text, ""

    stripped = text.strip()
    words = re.findall(r'\b[^\s]+\b', stripped)
    if not words:
        return False, text, ""

    lat_count = len(RE_LATIN.findall(stripped))
    cyr_count = len(RE_CYRILLIC.findall(stripped))

    # Case 1: Explicit source language hint
    if src_lang == "ru" and lat_count > 0 and cyr_count == 0:
        # User specified source as Russian, but typed Latin characters -> 100% wrong layout
        return True, convert_en_to_ru(text), "en_to_ru"

    if src_lang == "en" and cyr_count > 0 and lat_count == 0:
        # User specified source as English, but typed Cyrillic characters -> 100% wrong layout
        return True, convert_ru_to_en(text), "ru_to_en"

    # Case 2: Latin text that is actually Russian (e.g. "ghbdtn", "rfr ltkf")
    if lat_count >= 3 and cyr_count == 0:
        conv = convert_en_to_ru(text)
        conv_words = [w.lower() for w in re.findall(r'[а-яА-ЯёЁ]+', conv)]

        # Check if any converted word is in common Russian vocabulary
        if any(w in COMMON_RU_WORDS for w in conv_words):
            return True, conv, "en_to_ru"

        # Check English vowel distribution
        # Normal English words have ~35-45% vowels. Mistyped Russian has near 0% or low English vowels
        vowels = len(RE_EN_VOWELS.findall(stripped))
        vowel_ratio = vowels / lat_count if lat_count > 0 else 0

        # Converted Russian vowel ratio
        ru_vowels = len(RE_RU_VOWELS.findall(conv))
        ru_vowel_ratio = ru_vowels / len(conv) if len(conv) > 0 else 0

        # If English has < 15% vowels and converted Russian has healthy vowel ratio (> 25%)
        if vowel_ratio < 0.16 and ru_vowel_ratio >= 0.22:
            return True, conv, "en_to_ru"

        # Specific impossible English consonant sequences (e.g., ghbd, xnj, ltk, cjp, dbl)
        impossible_en = ["ghb", "xnj", "ltk", "cjp", "dbl", "ghb", "ds", "bp", "rf", "gj", "jly", "vye"]
        if any(pat in stripped.lower() for pat in impossible_en) and ru_vowel_ratio >= 0.20:
            return True, conv, "en_to_ru"

    # Case 3: Cyrillic text that is actually English (e.g. "руддщ" -> "hello", "цщкдв" -> "world")
    if cyr_count >= 3 and lat_count == 0:
        conv = convert_ru_to_en(text)
        conv_words = [w.lower() for w in re.findall(r'[a-zA-Z]+', conv)]

        # Check if any converted word is in common English vocabulary
        if any(w in COMMON_EN_WORDS for w in conv_words):
            return True, conv, "ru_to_en"

        # Check Russian vowel distribution vs English vowel distribution
        ru_vowels = len(RE_RU_VOWELS.findall(stripped))
        ru_vowel_ratio = ru_vowels / cyr_count if cyr_count > 0 else 0

        en_vowels = len(RE_EN_VOWELS.findall(conv))
        en_vowel_ratio = en_vowels / len(conv) if len(conv) > 0 else 0

        if ru_vowel_ratio < 0.16 and en_vowel_ratio >= 0.25:
            return True, conv, "ru_to_en"

    return False, text, ""
