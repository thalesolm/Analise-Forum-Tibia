"""
Clustering de posts por TF-IDF + K-means.
"""
from typing import Optional

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
import numpy as np

from analysis.config import N_CLUSTERS_DEFAULT, MIN_DF, MAX_DF
from analysis.text_processing import get_stopwords, normalize_text


def cluster_posts(
    texts: list[str],
    n_clusters: int = N_CLUSTERS_DEFAULT,
    *,
    max_df: float = MAX_DF,
    min_df: int = MIN_DF,
) -> tuple[list[int], list[str], TfidfVectorizer]:
    """
    Agrupa documentos (corpo dos posts) em clusters.
    Retorna:
      - labels: lista de tamanho len(texts) com o cluster de cada post (0 a n_clusters-1)
      - top_terms_per_cluster: lista de n_clusters listas com termos mais representativos
      - vectorizer: o TfidfVectorizer usado (para reuso se necessário)
    """
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
        return list(range(n)), [[] for _ in range(min(n_clusters, n))], vectorizer

    n = X.shape[0]
    actual_k = min(n_clusters, n)
    if actual_k < 1:
        return [], [], vectorizer

    kmeans = KMeans(n_clusters=actual_k, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X)

    # Termos mais representativos por cluster (centroide)
    vocab = vectorizer.get_feature_names_out()
    top_terms_per_cluster = []
    for c in range(actual_k):
        center = kmeans.cluster_centers_[c]
        top_indices = np.argsort(center)[::-1][:15]
        terms = [vocab[i] for i in top_indices if center[i] > 0]
        top_terms_per_cluster.append(terms)

    return list(labels), top_terms_per_cluster, vectorizer
