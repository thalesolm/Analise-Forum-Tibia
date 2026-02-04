"""
Parse de páginas do fórum Tibia: extração de posts e informação de paginação.
"""
import re
from dataclasses import dataclass
from typing import Optional

from bs4 import BeautifulSoup


@dataclass
class Post:
    """Um único post do fórum."""
    post_id: Optional[str]
    author: str
    date: str
    body: str


# Padrão para data do fórum: 22.01.2026 11:04:19
DATE_PATTERN = re.compile(r"\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2}:\d{2}")

# Padrão para "Post #39563969" ou similar
POST_ID_PATTERN = re.compile(r"Post\s*#(\d+)", re.I)

# Resultados totais: "Results: 206"
RESULTS_PATTERN = re.compile(r"Results:\s*(\d+)", re.I)

# Páginas: "Pages: 1 2 3 ... 11" - pegar último número
PAGES_PATTERN = re.compile(r"pagenumber=(\d+)")
# Ou texto "» Pages: 1 2 3 ... 11"
PAGES_TEXT_PATTERN = re.compile(r"Pages:\s*([\d\s]+)", re.I)

POSTS_PER_PAGE = 20  # valor típico do fórum Tibia


def _normalize_whitespace(text: str) -> str:
    """Colapsa espaços e newlines em espaço único e strip."""
    if not text:
        return ""
    return " ".join(text.split()).strip()


def _extract_author_from_link(soup: BeautifulSoup, container) -> Optional[str]:
    """Extrai nome do autor a partir de link para character (subtopic=characters&name=)."""
    for a in container.find_all("a", href=True):
        href = a.get("href", "")
        if "subtopic=characters" in href and "name=" in href:
            # name= pode ser encoded (e.g. name=Lata+Ogon)
            name = a.get_text(strip=True)
            if name and len(name) < 50:  # nome de personagem razoável
                return name
    return None


def _find_post_containers(soup: BeautifulSoup):
    """
    Encontra blocos que representam cada post.
    Usa a imagem logo_oldpost/logo_newpost como marcador de fim de post,
    ou divide por "Post #" para isolar o corpo de cada post.
    """
    # Estratégia: encontrar imagens que marcam fim do post (logo_oldpost.gif / logo_newpost.gif)
    # e pegar o container pai que contém todo o post (autor, data, corpo).
    end_markers = soup.find_all("img", src=lambda s: s and ("logo_oldpost" in str(s) or "logo_newpost" in str(s)))
    if not end_markers:
        # Fallback: procurar por "Post #" e extrair blocos de texto
        return _find_posts_by_post_id(soup)

    posts_data = []
    for img in end_markers:
        # Subir até um container que tenha autor + data (ex.: tr ou div grande)
        block = img.parent
        for _ in range(20):
            if block is None:
                break
            text = block.get_text()
            if not DATE_PATTERN.search(text):
                block = block.parent
                continue
            author_link = block.find("a", href=lambda h: h and "subtopic=characters" in str(h) and "name=" in str(h))
            if not author_link:
                block = block.parent
                continue
            author = author_link.get_text(strip=True)
            if not author or len(author) > 50:
                block = block.parent
                continue
            date_match = DATE_PATTERN.search(text)
            date_str = date_match.group(0)
            # Corpo: texto do block; remover cabeçalho (até a data) e assinaturas
            body = text
            body = DATE_PATTERN.sub("", body, count=1)
            body = re.sub(r"Edited by [^\n]+ on \d{2}\.\d{2}\.\d{4}[^\n]*", "", body, flags=re.I)
            body = re.sub(r"_+", "", body)
            body = _normalize_whitespace(body)
            post_id = None
            pid_match = POST_ID_PATTERN.search(text)
            if pid_match:
                post_id = pid_match.group(1)
            posts_data.append(
                {"post_id": post_id, "author": author, "date": date_str, "body": body}
            )
            break
            block = block.parent

    return posts_data if posts_data else _find_posts_by_post_id(soup)


def _find_posts_by_post_id(soup: BeautifulSoup):
    """Fallback: extrair posts por links de character no contexto de 'Post #'."""
    author_links = soup.find_all("a", href=lambda h: h and "subtopic=characters" in str(h) and "name=" in str(h))
    if not author_links:
        return []
    posts_data = []
    for link in author_links:
        author = link.get_text(strip=True)
        if not author or len(author) > 50:
            continue
        if author.lower() in ("community", "tibia", "forum", "board jump", "thread jump", "post jump", "page jump"):
            continue
        parent = link.parent
        for _ in range(15):
            if parent is None:
                break
            text = parent.get_text()
            date_match = DATE_PATTERN.search(text)
            if date_match:
                date_str = date_match.group(0)
                body = DATE_PATTERN.sub("", text, count=1)
                body = re.sub(r"Edited by [^\n]+ on \d{2}\.\d{2}\.\d{4}[^\n]*", "", body, flags=re.I)
                body = re.sub(r"_+", "", body)
                body = _normalize_whitespace(body)
                post_id = None
                pid_match = POST_ID_PATTERN.search(text)
                if pid_match:
                    post_id = pid_match.group(1)
                posts_data.append(
                    {"post_id": post_id, "author": author, "date": date_str, "body": body}
                )
                break
            parent = parent.parent
    return posts_data


def parse_thread_page(html: str) -> tuple[list[dict], Optional[int], Optional[int]]:
    """
    Parse uma página HTML do tópico.
    Retorna:
      - lista de dicts com keys: post_id, author, date, body
      - total de resultados (Results: N) ou None
      - número total de páginas ou None
    """
    soup = BeautifulSoup(html, "lxml")
    posts_data = _find_post_containers(soup)
    # Deduplicar por (author, date) para evitar repetir o mesmo post
    seen = set()
    unique = []
    for p in posts_data:
        key = (p["author"], p["date"])
        if key not in seen:
            seen.add(key)
            unique.append(p)

    total_results = None
    text = soup.get_text()
    res_match = RESULTS_PATTERN.search(text)
    if res_match:
        total_results = int(res_match.group(1))

    total_pages = None
    # Links de paginação: pagenumber=2, pagenumber=3, ...
    page_links = soup.find_all("a", href=lambda h: h and "pagenumber=" in str(h))
    if page_links:
        numbers = []
        for a in page_links:
            href = a.get("href", "")
            m = PAGES_PATTERN.search(href)
            if m:
                numbers.append(int(m.group(1)))
        if numbers:
            total_pages = max(numbers)
    if total_pages is None and total_results is not None:
        total_pages = max(1, (total_results + POSTS_PER_PAGE - 1) // POSTS_PER_PAGE)

    return unique, total_results, total_pages


def posts_to_objects(posts_data: list[dict]) -> list[Post]:
    """Converte lista de dicts em lista de Post."""
    return [
        Post(
            post_id=p.get("post_id"),
            author=p.get("author", ""),
            date=p.get("date", ""),
            body=p.get("body", ""),
        )
        for p in posts_data
    ]
