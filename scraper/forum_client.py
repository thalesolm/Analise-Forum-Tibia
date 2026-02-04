"""
Cliente HTTP para fetch de páginas do fórum Tibia.
Tratamento de erros, timeout e rate limiting.
"""
import time
import re
from urllib.parse import urljoin, urlparse, parse_qs

import requests

DEFAULT_TIMEOUT = 30
DEFAULT_DELAY_BETWEEN_REQUESTS = 1.5  # segundos
BASE_URL = "https://www.tibia.com/forum/"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def fetch_page(url: str, timeout: int = DEFAULT_TIMEOUT) -> requests.Response:
    """
    Faz o fetch de uma URL do fórum com headers adequados.
    Levanta requests.RequestException em caso de erro.
    """
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response


def fetch_page_with_delay(
    url: str,
    timeout: int = DEFAULT_TIMEOUT,
    delay: float = DEFAULT_DELAY_BETWEEN_REQUESTS,
) -> str:
    """
    Faz o fetch e retorna o texto HTML. Aplica delay após a requisição
    para respeitar o servidor (rate limiting).
    """
    resp = fetch_page(url, timeout=timeout)
    time.sleep(delay)
    return resp.text


def parse_thread_url(url: str) -> tuple[str, str]:
    """
    Extrai thread_id e URL base do tópico a partir da URL.
    Retorna (thread_id, url_base_sem_pagenumber).
    """
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    thread_id = qs.get("threadid", [""])[0]
    if not thread_id:
        raise ValueError(f"URL inválida: não contém threadid: {url}")
    # URL base: action=thread&threadid=X (sem pagenumber)
    base = f"{parsed.scheme}://{parsed.netloc}{parsed.path}?action=thread&threadid={thread_id}"
    return thread_id, base


def page_url(base_url: str, page_number: int) -> str:
    """Monta a URL da página N do tópico (1-based)."""
    sep = "&" if "?" in base_url else "?"
    return f"{base_url}{sep}pagenumber={page_number}"
