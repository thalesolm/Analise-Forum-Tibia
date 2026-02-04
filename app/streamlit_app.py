"""
Interface Streamlit: nuvem de palavras e tabela de comentários ao selecionar uma palavra.
"""
import json
from pathlib import Path

import streamlit as st
import pandas as pd
from wordcloud import WordCloud

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_analysis(path: Path) -> dict | None:
    """Carrega JSON de análise."""
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    st.set_page_config(page_title="Análise Fórum Tibia", layout="wide")
    st.title("Análise de feedback do fórum Tibia")

    # Listar análises disponíveis em data/
    data_dir = DATA_DIR
    data_dir.mkdir(parents=True, exist_ok=True)
    analysis_files = list(data_dir.glob("analysis_*.json"))
    if not analysis_files:
        st.warning(
            "Nenhum arquivo de análise encontrado. Execute primeiro:\n"
            "1. `python -m scraper.run \"https://www.tibia.com/forum/?action=thread&threadid=4992269\"`\n"
            "2. `python -m analysis.run data/thread_4992269.json`"
        )
        st.stop()

    # Seletor de análise
    options = {f.stem.replace("analysis_", ""): f for f in sorted(analysis_files, key=lambda p: p.name)}
    selected_id = st.sidebar.selectbox(
        "Tópico (thread)",
        options=list(options.keys()),
        format_func=lambda x: f"Thread {x}",
    )
    analysis_path = options[selected_id]
    data = load_analysis(analysis_path)
    if not data:
        st.error(f"Erro ao carregar {analysis_path}")
        st.stop()

    posts = data.get("posts", [])
    word_cloud = data.get("word_cloud", [])
    word_to_posts = data.get("word_to_posts", {})
    cluster_labels = data.get("cluster_labels", [])
    top_terms_per_cluster = data.get("top_terms_per_cluster", [])

    st.sidebar.metric("Total de posts", len(posts))
    st.sidebar.metric("Palavras na nuvem", len(word_cloud))

    # Nuvem de palavras (imagem)
    st.subheader("Nuvem de palavras (relevância por TF-IDF)")
    if word_cloud:
        try:
            freq = {w: max(1.0, s) for w, s in word_cloud}
            wc = WordCloud(
                width=800,
                height=400,
                background_color="white",
                max_words=150,
                relative_scaling=1.0,
                min_font_size=10,
            ).generate_from_frequencies(freq)
            st.image(wc.to_image(), use_container_width=True)
        except Exception as e:
            st.warning(f"Nuvem não gerada: {e}")
    else:
        st.info("Sem dados para nuvem.")

    # Seleção de palavra (simula "clique" na palavra)
    st.subheader("Ver comentários por palavra")
    words_for_select = [w for w, _ in word_cloud] if word_cloud else list(word_to_posts.keys())[:200]
    selected_word = st.selectbox(
        "Selecione uma palavra para ver os comentários que a contêm:",
        options=[""] + sorted(words_for_select),
        index=0,
    )

    if selected_word:
        entries = word_to_posts.get(selected_word.lower(), [])
        if not entries:
            st.info(f"Nenhum comentário encontrado com a palavra \"{selected_word}\".")
        else:
            st.caption(f"{len(entries)} comentário(s) contendo \"{selected_word}\".")
            df = pd.DataFrame([
                {
                    "Autor": e["author"],
                    "Data": e["date"],
                    "Conteúdo": e["body"],
                }
                for e in entries
            ])
            st.dataframe(df, use_container_width=True, height=400)
            # Expansível com conteúdo completo
            with st.expander("Ver comentários em texto"):
                for e in entries:
                    st.markdown(f"**{e['author']}** ({e['date']})")
                    st.text(e["body"])
                    st.divider()

    # Opcional: temas (clusters)
    if top_terms_per_cluster:
        st.sidebar.subheader("Temas (clusters)")
        for i, terms in enumerate(top_terms_per_cluster[:10]):
            st.sidebar.caption(f"Tema {i+1}: {', '.join(terms[:8])}")


if __name__ == "__main__":
    main()
