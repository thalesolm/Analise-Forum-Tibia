"""
Orquestra o pipeline de análise: carrega JSON do scraper, processa, gera scores,
clustering e índice palavra->posts; salva artefatos em data/analysis_<thread_id>.json.
"""
import argparse
import json
from pathlib import Path

from analysis.config import MAX_WORDS_CLOUD, N_CLUSTERS_DEFAULT
from analysis.text_processing import get_stopwords
from analysis.frequency import tfidf_scores, top_words_for_cloud
from analysis.clustering import cluster_posts
from analysis.word_to_posts import build_word_to_posts_index


def run_analysis(thread_data: dict, n_clusters: int = N_CLUSTERS_DEFAULT) -> dict:
    """
    Recebe o dict do thread (thread_id, posts, ...) e retorna o dict de análise
    com word_scores, word_cloud, clusters, cluster_labels, word_to_posts.
    """
    posts = thread_data.get("posts", [])
    texts = [p.get("body") or "" for p in posts]
    thread_id = thread_data.get("thread_id", "unknown")

    stopwords = get_stopwords()
    word_scores = tfidf_scores(texts)
    word_cloud = top_words_for_cloud(word_scores, max_words=MAX_WORDS_CLOUD)
    labels, top_terms_per_cluster, _ = cluster_posts(texts, n_clusters=n_clusters)
    word_to_posts = build_word_to_posts_index(posts, stopwords=stopwords)

    # Serializar: word_to_posts com chaves string; word_cloud como lista de [word, score]
    word_cloud_serializable = [[w, float(s)] for w, s in word_cloud]
    word_scores_serializable = {k: float(v) for k, v in word_scores.items()}

    return {
        "thread_id": thread_id,
        "title": thread_data.get("title"),
        "total_posts": len(posts),
        "word_scores": word_scores_serializable,
        "word_cloud": word_cloud_serializable,
        "cluster_labels": labels,
        "top_terms_per_cluster": top_terms_per_cluster,
        "word_to_posts": word_to_posts,
        "posts": posts,
    }


def main():
    parser = argparse.ArgumentParser(description="Análise NLP de um tópico já baixado")
    parser.add_argument("input", help="Caminho do JSON do thread (ex: data/thread_4992269.json)")
    parser.add_argument("-o", "--output-dir", default="data", help="Diretório de saída")
    parser.add_argument("--clusters", type=int, default=N_CLUSTERS_DEFAULT, help="Número de clusters")
    args = parser.parse_args()

    path = Path(args.input)
    if not path.exists():
        raise SystemExit(f"Arquivo não encontrado: {path}")

    with open(path, encoding="utf-8") as f:
        thread_data = json.load(f)

    result = run_analysis(thread_data, n_clusters=args.clusters)
    thread_id = result["thread_id"]
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"analysis_{thread_id}.json"

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Análise salva: {out_path}")
    print(f"  Palavras na nuvem: {len(result['word_cloud'])}")
    print(f"  Clusters: {len(result['top_terms_per_cluster'])}")


if __name__ == "__main__":
    main()
