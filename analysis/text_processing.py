"""
Normalização, tokenização e remoção de stopwords.
"""
import re
from typing import Optional

from analysis.config import STOPWORDS_LANGUAGES, MIN_TOKEN_LENGTH, NLTK_DATA


def _ensure_nltk_data():
    """Baixa stopwords e punkt se ainda não existirem."""
    import nltk
    if NLTK_DATA:
        nltk.data.path.insert(0, NLTK_DATA)
    try:
        nltk.data.find("corpora/stopwords")
    except LookupError:
        nltk.download("stopwords", quiet=True)
    try:
        nltk.data.find("tokenizers/punkt")
    except LookupError:
        nltk.download("punkt", quiet=True)


def get_stopwords() -> set[str]:
    """Retorna conjunto unificado de stopwords em inglês e português."""
    import nltk
    _ensure_nltk_data()
    stop = set()
    for lang in STOPWORDS_LANGUAGES:
        try:
            stop.update(nltk.corpus.stopwords.words(lang))
        except OSError:
            pass
    return stop


def normalize_text(text: str) -> str:
    """Lowercase e remove caracteres que não são letras (mantém espaços)."""
    if not text:
        return ""
    text = text.lower().strip()
    # Manter apenas letras unicode e espaços
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def tokenize(text: str, min_length: int = MIN_TOKEN_LENGTH) -> list[str]:
    """Tokenização simples por espaços, após normalização; filtra por tamanho mínimo."""
    normalized = normalize_text(text)
    tokens = normalized.split()
    return [t for t in tokens if len(t) >= min_length]


def tokenize_without_stopwords(
    text: str,
    stopwords: Optional[set[str]] = None,
    min_length: int = MIN_TOKEN_LENGTH,
) -> list[str]:
    """Tokeniza e remove stopwords."""
    if stopwords is None:
        stopwords = get_stopwords()
    tokens = tokenize(text, min_length=min_length)
    return [t for t in tokens if t not in stopwords]


def process_corpus(texts: list[str], stopwords: Optional[set[str]] = None) -> list[list[str]]:
    """
    Processa uma lista de documentos (ex.: corpo de cada post).
    Retorna lista de listas de tokens (sem stopwords) por documento.
    """
    if stopwords is None:
        stopwords = get_stopwords()
    return [tokenize_without_stopwords(t, stopwords=stopwords) for t in texts]
