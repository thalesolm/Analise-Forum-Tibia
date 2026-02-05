"""
Interface Streamlit: colar URL do tópico, scraping + análise automáticos,
nuvem de palavras e tabela de comentários ao selecionar uma palavra.
"""
import base64
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
import altair as alt
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
            "**Sugestão:** abra a seção **Gerar JSON no navegador** abaixo: abra o tópico no Tibia, rode o script no Console e cole o JSON aqui. Não precisa instalar nada no PC."
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
    st.set_page_config(page_title="Análise do Alytreta - Feedbacks do forum do tibia", layout="wide")
    st.title("Análise do Alytreta – Feedbacks do fórum do Tibia")

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

    # Gerar JSON no navegador (sem rodar nada no PC)
    with st.expander("Gerar JSON no navegador (use se o botão acima falhar)"):
        st.markdown("""
        1. **Abra o tópico do Tibia** no navegador (ex.: [este link](https://www.tibia.com/forum/?action=thread&threadid=4992269)).
        2. Pressione **F12** e vá na aba **Console**.
        3. **Copie todo o script** da caixa abaixo (clique no ícone de copiar) e **cole no Console**, depois pressione **Enter**.
        4. Aguarde: o script vai baixar todas as páginas do tópico e **copiar o JSON** para a área de transferência.
        5. **Volte aqui**, cole o JSON na caixa de texto e clique em **Carregar e analisar**.
        """)
        script_path = Path(__file__).resolve().parent / "browser_fetch_script.js"
        browser_script = script_path.read_text(encoding="utf-8") if script_path.exists() else "// Arquivo browser_fetch_script.js não encontrado."
        st.code(browser_script, language="javascript")
        pasted_json = st.text_area("Cole aqui o JSON gerado pelo script (sem limite de tamanho)", height=200, key="pasted_json", placeholder='{"thread_id": "4992269", "posts": [...]}')
        if st.button("Carregar e analisar", key="btn_load_pasted"):
            if not pasted_json.strip():
                st.warning("Cole o JSON na caixa acima.")
            else:
                try:
                    data = json.loads(pasted_json)
                    if "word_cloud" in data and "posts" in data:
                        st.session_state["analysis_result"] = data
                        st.session_state["analysis_thread_id"] = data.get("thread_id")
                        st.success(f"Análise carregada: {len(data.get('posts', []))} posts.")
                        st.rerun()
                    elif "posts" in data and "thread_id" in data:
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
                    st.error(f"JSON inválido: {e}")

    # Alternativa: upload de arquivo JSON
    with st.expander("Ou envie um arquivo JSON"):
        st.caption("Envie um arquivo thread_*.json ou analysis_*.json (se tiver salvo no PC).")
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
        st.info("Use **Baixar e analisar** com a URL do tópico ou, se o site bloquear, abra **Gerar JSON no navegador** e siga os passos (sem instalar nada no PC).")
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

    # Session state: filtro de palavras e palavra selecionada
    if "words_to_hide" not in st.session_state:
        st.session_state["words_to_hide"] = set()
    if "selected_word" not in st.session_state:
        st.session_state["selected_word"] = None

    # ---- Filtro de palavras (sidebar) ----
    st.sidebar.subheader("Filtro de palavras")
    hide_input = st.sidebar.text_area(
        "Palavras a ocultar (vírgula ou uma por linha)",
        value="",
        height=80,
        key="words_to_hide_input",
        placeholder="game, thing, lol",
    )
    if st.sidebar.button("Aplicar filtro", key="apply_filter"):
        parts = [p.strip().lower() for p in hide_input.replace(",", "\n").split() if p.strip()]
        st.session_state["words_to_hide"] = set(parts)
        st.rerun()
    if st.sidebar.button("Limpar filtro", key="clear_filter"):
        st.session_state["words_to_hide"] = set()
        st.rerun()

    words_to_hide = st.session_state["words_to_hide"]
    filtered_cloud = [(w, s) for w, s in word_cloud if w.lower() not in words_to_hide] if word_cloud else []
    n_hidden = len(word_cloud) - len(filtered_cloud) if word_cloud else 0
    if n_hidden > 0:
        st.sidebar.caption(f"{n_hidden} palavra(s) oculta(s)")

    st.sidebar.metric("Total de posts", len(posts))
    st.sidebar.metric("Palavras na nuvem", len(filtered_cloud))

    # Nuvem de palavras (imagem) com dados filtrados
    st.subheader("Nuvem de palavras (relevância por TF-IDF)")
    if filtered_cloud:
        try:
            freq = {w: max(1.0, s) for w, s in filtered_cloud}
            wc = WordCloud(
                width=800,
                height=400,
                background_color="#0e1117",
                max_words=150,
                relative_scaling=1.0,
                min_font_size=10,
                colormap="viridis",
            ).generate_from_frequencies(freq)
            st.image(wc.to_image(), use_container_width=True)
        except Exception as e:
            st.warning(f"Nuvem não gerada: {e}")
    else:
        st.info("Sem dados para nuvem (ou todas as palavras estão ocultas).")

    # Lista de palavras para o selectbox (dados filtrados)
    TOP_SELECT = 70
    words_for_buttons = [w for w, _ in filtered_cloud[:TOP_SELECT]]

    # Seleção por selectbox
    options_sel = [""] + sorted(words_for_buttons) if words_for_buttons else [""]
    cur = st.session_state.get("selected_word") or ""
    idx_sel = options_sel.index(cur) if cur in options_sel else 0
    chosen = st.selectbox("Selecione uma palavra para ver os comentários:", options_sel, index=idx_sel, key="select_word")
    if chosen:
        st.session_state["selected_word"] = chosen
    selected_word = st.session_state.get("selected_word")

    if selected_word:
        entries = word_to_posts.get(selected_word.lower(), [])
        if not entries:
            st.info(f"Nenhum comentário encontrado com a palavra \"{selected_word}\".")
        else:
            st.caption(f"{len(entries)} comentário(s) contendo \"{selected_word}\".")
            df = pd.DataFrame([
                {"Autor": e["author"], "Data": e["date"], "Conteúdo": e["body"]}
                for e in entries
            ])
            st.dataframe(df, use_container_width=True, height=400)
            with st.expander("Ver comentários em texto"):
                for e in entries:
                    st.markdown(f"**{e['author']}** ({e['date']})")
                    st.text(e["body"])
                    st.divider()

            # Interpretar com IA (manual): prompt + lotes
            st.subheader("Interpretar com IA (manual)")
            st.caption("Cole o prompt abaixo no ChatGPT/DeepSeek, depois cole os comentários de um lote. Repita com outros lotes se precisar.")
            prompt_text = f'Estes são comentários de um fórum sobre o jogo Tibia que mencionam a palavra "{selected_word}". O que esses comentários têm em comum? Qual o sentimento ou pedido principal (ex.: buff, nerf, qualidade de vida)? Responde em 1–2 frases.'
            st.text_area("Prompt sugerido (copie e cole na IA)", value=prompt_text, height=80, disabled=True, key="prompt_word")
            bodies = [e["body"] for e in entries]
            from analysis.utils import split_texts_into_batches
            batches = split_texts_into_batches(bodies)
            for i, batch in enumerate(batches, 1):
                st.text_area(f"Lote {i} (Ctrl+A e Ctrl+C para copiar)", value=batch, height=180, disabled=True, key=f"batch_word_{i}")

    # Gráfico de frequência (dados filtrados): maior → menor, esquerda → direita
    st.subheader("Frequência das palavras")
    if filtered_cloud:
        TOP_CHART = 40
        chart_data = filtered_cloud[:TOP_CHART]
        df_chart = pd.DataFrame({"palavra": [w for w, _ in chart_data], "relevância": [s for w, s in chart_data]})
        df_chart = df_chart.sort_values("relevância", ascending=False)
        chart = (
            alt.Chart(df_chart)
            .mark_bar(color="#6eb5e0")
            .encode(
                x=alt.X("palavra", sort=alt.EncodingSortField("relevância", order="descending"), title="Palavra"),
                y=alt.Y("relevância", title="Frequência"),
            )
            .configure_view(background="#0e1117")
            .configure_axis(labelColor="#fafafa", titleColor="#fafafa", domainColor="#444", gridColor="#333")
            .configure_title(color="#fafafa")
        )
        st.altair_chart(chart, use_container_width=True)

    # Temas (clusters) com cópia para IA
    if top_terms_per_cluster:
        st.sidebar.subheader("Temas (clusters)")
        for i, terms in enumerate(top_terms_per_cluster[:10]):
            st.sidebar.caption(f"Tema {i+1}: {', '.join(terms[:8])}")

    st.subheader("Temas (clusters) – copiar para IA")
    if top_terms_per_cluster and cluster_labels and len(cluster_labels) == len(posts):
        from analysis.utils import split_texts_into_batches
        for c in range(len(top_terms_per_cluster)):
            terms = top_terms_per_cluster[c]
            cluster_posts = [posts[i] for i in range(len(posts)) if cluster_labels[i] == c]
            with st.expander(f"Tema {c+1}: {', '.join(terms[:6])}... ({len(cluster_posts)} posts)"):
                prompt_cluster = f"Estes são comentários de um fórum de feedback do jogo Tibia. Os principais termos deste grupo são: {', '.join(terms[:12])}. Abaixo estão trechos dos comentários. O que eles têm em comum? Qual o sentimento ou pedido principal (buff, nerf, QoL)? Responde em 1–2 frases."
                st.text_area("Prompt sugerido (copie e cole na IA)", value=prompt_cluster, height=70, disabled=True, key=f"prompt_cluster_{c}")
                bodies = [p.get("body", "") for p in cluster_posts]
                # Cluster inteiro para copiar de uma vez
                full_text = "\n\n".join(f"--- Post {n} ---\n{b}" for n, b in enumerate(bodies, 1))
                st.text_area("Cluster inteiro", value=full_text, height=min(500, max(200, 100 + len(full_text) // 35)), disabled=True, key=f"full_cluster_{c}")
                # Botão que copia o cluster para a área de transferência (via JS no navegador)
                b64 = base64.b64encode(full_text.encode("utf-8")).decode("ascii")
                copy_html = f"""
                <html><body style="margin:0;">
                <button id="copyBtn" style="padding:8px 16px;cursor:pointer;font-size:14px;border-radius:6px;border:1px solid #4a5568;background:#2d3748;color:#fafafa;">📋 Copiar cluster para área de transferência</button>
                <span id="msg" style="margin-left:8px;color:#68d391;font-size:13px;"></span>
                <script>
                (function() {{
                    var b64 = "{b64}";
                    var binary = atob(b64);
                    var bytes = new Uint8Array(binary.length);
                    for (var i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
                    var text = new TextDecoder("utf-8").decode(bytes);
                    document.getElementById("copyBtn").onclick = function() {{
                        navigator.clipboard.writeText(text).then(function() {{
                            var el = document.getElementById("msg");
                            el.textContent = "Copiado!";
                            setTimeout(function() {{ el.textContent = ""; }}, 2000);
                        }}).catch(function() {{ document.getElementById("msg").textContent = "Erro ao copiar."; }});
                    }};
                }})();
                </script>
                </body></html>
                """
                st.components.v1.html(copy_html, height=50)
                # Lotes menores (opcional)
                batches = split_texts_into_batches(bodies, header_template="--- Post {n} ---\n")
                if len(batches) > 1:
                    st.caption("Se preferir copiar em partes menores, use os lotes abaixo.")
                    for i, batch in enumerate(batches, 1):
                        st.text_area(f"Lote {i} (Ctrl+A e Ctrl+C para copiar)", value=batch, height=160, disabled=True, key=f"batch_cluster_{c}_{i}")


if __name__ == "__main__":
    main()
