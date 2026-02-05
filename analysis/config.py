"""
Configuração do pipeline de análise: stopwords (PT/EN), parâmetros da nuvem e clustering.
"""
import os

# NLTK data path (evitar conflitos em alguns ambientes)
NLTK_DATA = os.environ.get("NLTK_DATA")

# Idiomas de stopwords
STOPWORDS_LANGUAGES = ("english", "portuguese")

# Mínimo de caracteres por token
MIN_TOKEN_LENGTH = 2

# Máximo de palavras na nuvem (mais relevantes)
MAX_WORDS_CLOUD = 150

# Número de clusters (K-means)
N_CLUSTERS_DEFAULT = 6

# Sugestão automática de k: intervalo testado e método padrão
CLUSTER_K_RANGE = (2, 15)
CLUSTER_SUGGEST_METHOD = "silhouette"

# Parâmetros TF-IDF
MAX_DF = 0.95  # ignorar termos em mais de 95% dos docs
MIN_DF = 1     # termo deve aparecer em pelo menos 1 doc
