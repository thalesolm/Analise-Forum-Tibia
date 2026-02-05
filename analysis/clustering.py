"""
Clustering de posts por TF-IDF + K-means.
Sugestão de número de clusters via silhouette e elbow.
"""
from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import silhouette_score

from analysis.config import (
    CLUSTER_K_RANGE,
    CLUSTER_SUGGEST_METHOD,
    MAX_DF,
    MIN_DF,
    N_CLUSTERS_DEFAULT,
)
from analysis.text_processing import get_stopwords, normalize_text


def suggest_n_clusters(
    X,
    k_range: tuple[int, int] = CLUSTER_K_RANGE,
    method: str = "silhouette",
) -> tuple[int, dict[int, float]]:
    """
    Sugere o número de clusters testando k no intervalo k_range.
    Retorna (best_k, scores) onde scores é um dict k -> score (silhouette ou inertia).
    """
    n = X.shape[0]
    k_min, k_max = k_range
    k_max = min(k_max, n)
    fallback_k = max(2, min(k_min, n))
    if k_min >= k_max or n < 2:
        return fallback_k, {}

    scores: dict[int, float] = {}
    if method == "silhouette":
        for k in range(k_min, k_max + 1):
            if k >= n:
                break
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = kmeans.fit_predict(X)
            if len(set(labels)) < 2:
                continue
            scores[k] = float(silhouette_score(X, labels))
        best_k = max(scores, key=scores.get) if scores else fallback_k
        return best_k, scores

    if method == "elbow":
        inertias = []
        for k in range(k_min, k_max + 1):
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            kmeans.fit(X)
            scores[k] = float(kmeans.inertia_)
            inertias.append((k, kmeans.inertia_))
        if len(inertias) < 2:
            return k_min, scores
        # Elbow: ponto de maior distância à reta (k_min, iner_min) -> (k_max, iner_max)
        ks = [p[0] for p in inertias]
        iners = np.array([p[1] for p in inertias])
        k0, k1 = ks[0], ks[-1]
        i0, i1 = iners[0], iners[-1]
        denom = np.sqrt((k1 - k0) ** 2 + (i1 - i0) ** 2) or 1.0
        dists = np.abs((ks - k0) * (i1 - i0) - (iners - i0) * (k1 - k0)) / denom
        best_k = ks[int(np.argmax(dists))]
        return best_k, scores

    return max(k_min, min(N_CLUSTERS_DEFAULT, k_max)), {}


def suggest_n_clusters_both(
    X,
    k_range: tuple[int, int] = CLUSTER_K_RANGE,
) -> dict[str, dict[str, Any]]:
    """
    Calcula sugestão de k para silhouette e elbow.
    Retorna {"silhouette": {"k": int, "scores": {k: score}}, "elbow": {"k": int, "scores": {k: inertia}}}.
    """
    result: dict[str, dict[str, Any]] = {}
    for method in ("silhouette", "elbow"):
        best_k, scores = suggest_n_clusters(X, k_range=k_range, method=method)
        result[method] = {"k": best_k, "scores": scores}
    return result


def cluster_posts(
    texts: list[str],
    n_clusters: int | None = N_CLUSTERS_DEFAULT,
    *,
    max_df: float = MAX_DF,
    min_df: int = MIN_DF,
    k_range: tuple[int, int] = CLUSTER_K_RANGE,
) -> tuple[list[int], list[list[str]], TfidfVectorizer, dict[str, dict[str, Any]]]:
    """
    Agrupa documentos (corpo dos posts) em clusters.
    Se n_clusters for None, usa o k sugerido pelo método silhouette.
    Retorna:
      - labels: lista de tamanho len(texts) com o cluster de cada post
      - top_terms_per_cluster: lista de n_clusters listas com termos mais representativos
      - vectorizer: o TfidfVectorizer usado
      - suggestions: {"silhouette": {"k", "scores"}, "elbow": {"k", "scores"}}
    """
    empty_suggestions = {"silhouette": {"k": 2, "scores": {}}, "elbow": {"k": 2, "scores": {}}}
    normalized = [normalize_text(t) for t in texts]
    vectorizer = TfidfVectorizer(
        max_df=max_df,
        min_df=min_df,
        stop_words=list(get_stopwords()),
        token_pattern=r"(?u)\b\w{2,}\b",
    )
    try:
        X = vectorizer.fit_transform(normalized)
    except ValueError:
        n = len(texts)
        k_use = n_clusters if n_clusters is not None else N_CLUSTERS_DEFAULT
        return (
            list(range(n)),
            [[] for _ in range(min(k_use, n))],
            vectorizer,
            empty_suggestions,
        )

    n = X.shape[0]
    if n < 2:
        return list(range(n)), [[]] * n, vectorizer, empty_suggestions

    suggestions = suggest_n_clusters_both(X, k_range=k_range)
    if n_clusters is None:
        k_used = suggestions[CLUSTER_SUGGEST_METHOD]["k"]
    else:
        k_used = n_clusters
    actual_k = max(1, min(k_used, n))

    kmeans = KMeans(n_clusters=actual_k, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X)

    vocab = vectorizer.get_feature_names_out()
    top_terms_per_cluster = []
    for c in range(actual_k):
        center = kmeans.cluster_centers_[c]
        top_indices = np.argsort(center)[::-1][:15]
        terms = [vocab[i] for i in top_indices if center[i] > 0]
        top_terms_per_cluster.append(terms)

    return list(labels), top_terms_per_cluster, vectorizer, suggestions
