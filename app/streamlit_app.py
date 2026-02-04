"""
Interface Streamlit: colar URL do tópico, scraping + análise automáticos,
nuvem de palavras e tabela de comentários ao selecionar uma palavra.
"""
import json
import sys
from pathlib import Path

# Garantir imports do projeto (raiz = parent de app/)
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import requests
import streamlit as st
import pandas as pd
from wordcloud import WordCloud

DATA_DIR = ROOT / "data"


def load_analysis(path: Path) -> dict | None:
    """Carrega JSON de análise."""
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def scrape_and_analyze(url: str) -> dict | None:
    """Executa scraping do tópico e análise NLP. Retorna dict de análise ou None em caso de erro."""
    try:
        from scraper.pagination import scrape_thread
        from analysis.run import run_analysis
    except ImportError as e:
        st.error(f"Erro ao importar módulos: {e}. Execute a partir da raiz do projeto.")
        return None
    try:
        with st.spinner("Baixando páginas do fórum…"):
            thread_data = scrape_thread(url, delay=1.2, max_pages=None)
    except requests.HTTPError as e:
        code = e.response.status_code if e.response is not None else "?"
        st.error(
            f"**O site do fórum retornou erro HTTP {code}.** "
            "Sites como o Tibia costumam bloquear requisições de datacenters (ex.: Streamlit Cloud). "
            "**Sugestão:** abra a seção **Alternativa: enviar arquivo JSON** abaixo, baixe o tópico no seu PC com o scraper e envie o arquivo aqui."
        )
        return None
    except requests.RequestException as e:
        st.error(f"**Erro de rede:** {e}. Verifique a URL e se o site está acessível.")
        return None
    if not thread_data.get("posts"):
        st.warning("Nenhum post encontrado. Verifique a URL ou se o fórum está acessível.")
        return None
    try:
        with st.spinner("Analisando textos (TF-IDF e clusters)…"):
            result = run_analysis(thread_data)
    except Exception as e:
        st.error(f"Erro durante a análise: {e}")
        return None
    return result


def main():
    st.set_page_config(page_title="Análise Fórum Tibia", layout="wide")
    st.title("Análise de feedback do fórum Tibia")

    # Inicializar session_state para análise em memória
    if "analysis_result" not in st.session_state:
        st.session_state["analysis_result"] = None
    if "analysis_thread_id" not in st.session_state:
        st.session_state["analysis_thread_id"] = None

    # ---- Entrada por URL (sempre visível no topo) ----
    st.subheader("Analisar um tópico")
    url = st.text_input(
        "URL do tópico do fórum",
        placeholder="https://www.tibia.com/forum/?action=thread&threadid=4992269",
        key="forum_url",
    )
    st.caption("Pode levar alguns minutos se o tópico tiver muitas páginas.")
    col1, _ = st.columns([1, 3])
    with col1:
        analyze_clicked = st.button("Baixar e analisar", type="primary")

    if analyze_clicked and url.strip():
        result = scrape_and_analyze(url.strip())
        if result:
            st.session_state["analysis_result"] = result
            st.session_state["analysis_thread_id"] = result.get("thread_id")
            st.success(f"Tópico analisado: {len(result.get('posts', []))} posts.")
            st.rerun()

    # Alternativa: upload de JSON (quando o site bloqueia, ex.: no Streamlit Cloud)
    with st.expander("Alternativa: enviar arquivo JSON (se o site bloquear)"):
        st.caption("Se o Tibia bloquear o acesso (ex.: no Streamlit Cloud), baixe o tópico no seu PC e envie o JSON aqui.")
        uploaded = st.file_uploader("Enviar thread_*.json ou analysis_*.json", type="json", key="upload_json")
        if uploaded is not None:
            try:
                data = json.load(uploaded)
                if "word_cloud" in data and "posts" in data:
                    # Já é análise pronta
                    st.session_state["analysis_result"] = data
                    st.session_state["analysis_thread_id"] = data.get("thread_id")
                    st.success(f"Análise carregada: {len(data.get('posts', []))} posts.")
                    st.rerun()
                elif "posts" in data and "thread_id" in data:
                    # É thread bruto: rodar análise
                    with st.spinner("Analisando textos…"):
                        from analysis.run import run_analysis
                        result = run_analysis(data)
                    st.session_state["analysis_result"] = result
                    st.session_state["analysis_thread_id"] = result.get("thread_id")
                    st.success(f"Tópico analisado: {len(result.get('posts', []))} posts.")
                    st.rerun()
                else:
                    st.warning("JSON inválido: precisa ter 'posts' e 'thread_id' (thread) ou 'word_cloud' (análise).")
            except json.JSONDecodeError as e:
                st.error(f"Arquivo JSON inválido: {e}")

    # Fonte dos dados: análise em memória ou arquivos em data/
    data = st.session_state["analysis_result"]
    data_dir = DATA_DIR
    data_dir.mkdir(parents=True, exist_ok=True)
    analysis_files = list(data_dir.glob("analysis_*.json"))
    options = {}
    if data:
        options["_current"] = data  # análise feita pela URL
    for f in sorted(analysis_files, key=lambda p: p.name):
        tid = f.stem.replace("analysis_", "")
        options[tid] = load_analysis(f)
    # Remover entradas None (arquivo não carregado)
    options = {k: v for k, v in options.items() if v is not None}

    if not options:
        st.info("Cole a URL de um tópico acima e clique em **Baixar e analisar** para ver a nuvem de palavras e explorar os comentários.")
        st.stop()

    # Seletor de análise (se mais de uma, mostrar no sidebar)
    if len(options) == 1 and "_current" in options:
        data = options["_current"]
    else:
        choice_labels = {"_current": "Último analisado (URL)"}
        choice_labels.update({tid: f"Thread {tid}" for tid in options if tid != "_current"})
        selected_id = st.sidebar.selectbox(
            "Tópico (thread)",
            options=list(options.keys()),
            format_func=lambda x: choice_labels.get(x, f"Thread {x}"),
        )
        data = options[selected_id]

    if not data:
        st.error("Erro ao carregar os dados.")
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
