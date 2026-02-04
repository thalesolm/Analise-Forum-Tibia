"""
Índice palavra -> lista de posts (para filtrar comentários ao clicar na nuvem).
"""
from typing import Optional

from analysis.text_processing import get_stopwords, tokenize_without_stopwords


def build_word_to_posts_index(
    posts: list[dict],
    stopwords: Optional[set[str]] = None,
) -> dict[str, list[dict]]:
    """
    Constrói índice: para cada palavra (token sem stopword), lista de posts que a contêm.
    Cada item da lista é um dict com keys: post_index, author, date, body (e opcionalmente excerpt).
    """
    if stopwords is None:
        stopwords = get_stopwords()
    index: dict[str, list[dict]] = {}
    for i, post in enumerate(posts):
        body = post.get("body") or ""
        tokens = set(tokenize_without_stopwords(body, stopwords=stopwords))
        excerpt = (body[:300] + "…") if len(body) > 300 else body
        entry = {
            "post_index": i,
            "post_id": post.get("post_id"),
            "author": post.get("author", ""),
            "date": post.get("date", ""),
            "body": body,
            "excerpt": excerpt,
        }
        for word in tokens:
            word_lower = word.lower()
            if word_lower not in index:
                index[word_lower] = []
            index[word_lower].append(entry)
    return index
