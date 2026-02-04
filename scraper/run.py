"""
CLI para rodar o scraper: recebe URL do tópico e salva JSON em data/.
"""
import argparse
import json
from pathlib import Path

from scraper.pagination import scrape_thread


def main():
    parser = argparse.ArgumentParser(description="Scraper do fórum Tibia - baixa um tópico completo")
    parser.add_argument("url", help="URL do tópico (ex: https://www.tibia.com/forum/?action=thread&threadid=4992269)")
    parser.add_argument("-o", "--output-dir", default="data", help="Diretório de saída para o JSON")
    parser.add_argument("--delay", type=float, default=1.5, help="Delay entre requisições (segundos)")
    parser.add_argument("--max-pages", type=int, default=None, help="Máximo de páginas a baixar (útil para testes)")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Baixando tópico: {args.url}")
    data = scrape_thread(args.url, delay=args.delay, max_pages=args.max_pages)
    thread_id = data["thread_id"]
    out_path = output_dir / f"thread_{thread_id}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Salvo: {out_path} ({len(data['posts'])} posts)")


if __name__ == "__main__":
    main()
