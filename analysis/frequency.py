"""
Contagem de termos e TF-IDF para relevância na nuvem de palavras.
"""
from collections import Counter
from typing import Optional

from sklearn.feature_extraction.text import TfidfVectorizer

from analysis.config import MIN_DF, MAX_DF, MAX_WORDS_CLOUD
from analysis.text_processing import get_stopwords, tokenize_without_stopwords, normalize_text


def count_terms(texts: list[str], stopwords: Optional[set[str]] = None) -> Counter:
    """
    Contagem bruta de termos em todos os textos (após tokenização e stopwords).
    Retorna Counter palavra -> frequência.
    """
    if stopwords is None:
        stopwords = get_stopwords()
    counter: Counter = Counter()
    for text in texts:
        tokens = tokenize_without_stopwords(text, stopwords=stopwords)
        counter.update(tokens)
    return counter


def tfidf_scores(
    texts: list[str],
    *,
    max_df: float = MAX_DF,
    min_df: int = MIN_DF,
    max_features: int = 5000,
) -> dict[str, float]:
    """
    Calcula relevância por TF-IDF. Cada elemento de `texts` é um documento (ex.: um post).
    Retorna dict palavra -> score (soma dos TF-IDF da palavra em todos os docs).
    """
    # TF-IDF espera strings; usamos texto normalizado por doc
    normalized = [normalize_text(t) for t in texts]
    vectorizer = TfidfVectorizer(
        max_df=max_df,
        min_df=min_df,
        max_features=max_features,
        stop_words=list(get_stopwords()),
        token_pattern=r"(?u)\b\w{2,}\b",
    )
    try:
        X = vectorizer.fit_transform(normalized)
    except ValueError:
        return {}
    vocab = vectorizer.get_feature_names_out()
    # Soma dos TF-IDF por termo (coluna)
    sums = X.sum(axis=0).A1
    return dict(zip(vocab, sums))


def top_words_for_cloud(
    word_scores: dict[str, float],
    max_words: int = MAX_WORDS_CLOUD,
) -> list[tuple[str, float]]:
    """
    Retorna as top N palavras por score, ordenadas (palavra, score).
    Útil para gerar a nuvem (tamanho proporcional ao score).
    """
    sorted_items = sorted(word_scores.items(), key=lambda x: -x[1])
    return sorted_items[:max_words]
