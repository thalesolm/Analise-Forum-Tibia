"""
Lógica de paginação: descobre o total de páginas e percorre todas,
agregando os posts de um tópico.
"""
from typing import Callable, Optional

from scraper.forum_client import (
    parse_thread_url,
    page_url,
    fetch_page_with_delay,
)
from scraper.parser import parse_thread_page


def scrape_thread(
    url: str,
    *,
    fetch_fn: Optional[Callable[[str], str]] = None,
    delay: float = 1.5,
    max_pages: Optional[int] = None,
) -> dict:
    """
    Faz o scraping de um tópico completo (todas as páginas).
    Retorna um dict com thread_id, title (se disponível), total_pages, posts.
    fetch_fn: se fornecido, usa essa função para obter HTML (útil para testes com cache).
    """
    thread_id, base_url = parse_thread_url(url)
    if fetch_fn is None:
        def _fetch(u: str) -> str:
            return fetch_page_with_delay(u, delay=delay)
        fetch_fn = _fetch

    all_posts = []
    total_pages = None
    total_results = None
    title = None

    # Primeira página
    page1_url = page_url(base_url, 1)
    html = fetch_fn(page1_url)
    posts, total_results, total_pages = parse_thread_page(html)
    all_posts.extend(posts)

    if total_pages is None:
        total_pages = 1
    if max_pages is not None:
        total_pages = min(total_pages, max_pages)

    for p in range(2, total_pages + 1):
        page_url_n = page_url(base_url, p)
        html_n = fetch_fn(page_url_n)
        posts_n, _, _ = parse_thread_page(html_n)
        all_posts.extend(posts_n)

    # Deduplicar por (author, date, body) para segurança
    seen = set()
    unique_posts = []
    for p in all_posts:
        key = (p.get("author"), p.get("date"), (p.get("body") or "")[:200])
        if key not in seen:
            seen.add(key)
            unique_posts.append(p)

    return {
        "thread_id": thread_id,
        "title": title,
        "total_pages": total_pages,
        "total_results": total_results,
        "posts": unique_posts,
    }
