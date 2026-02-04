# Análise Fórum Tibia

Ferramenta para scraping e análise de feedback em tópicos do fórum do Tibia. Gera nuvem de palavras (relevância por TF-IDF), clustering de temas e permite explorar os comentários por palavra.

## Requisitos

- Python 3.10+
- Dependências em `requirements.txt`

## Instalação

```bash
pip install -r requirements.txt
```

Na primeira execução do pipeline de análise, o NLTK baixará stopwords e tokenizers (inglês e português).

## Uso

### 1. Baixar um tópico (scraping)

Forneça a URL do tópico. O scraper descobre o número de páginas e baixa todas.

```bash
python -m scraper.run "https://www.tibia.com/forum/?action=thread&threadid=4992269"
```

O JSON é salvo em `data/thread_<thread_id>.json`.

Opções:

- `-o DIR` — diretório de saída (padrão: `data`)
- `--delay N` — intervalo em segundos entre requisições (padrão: 1.5)
- `--max-pages N` — limitar páginas (útil para testes)

### 2. Rodar a análise NLP

Gera TF-IDF, nuvem de palavras, clustering e índice palavra → comentários.

```bash
python -m analysis.run data/thread_4992269.json
```

Saída: `data/analysis_4992269.json`.

Opções:

- `-o DIR` — diretório de saída
- `--clusters N` — número de clusters (padrão: 6)

### 3. Interface Streamlit

```bash
streamlit run app/streamlit_app.py
```

Na interface você pode:

- Escolher um tópico já analisado (lista em `data/analysis_*.json`)
- Ver a nuvem de palavras
- Selecionar uma palavra e ver a tabela de comentários que a contêm
- Ver os temas (clusters) na barra lateral

## Estrutura do projeto

```
Analise-Forum-Tibia/
├── data/                 # JSONs do scraper e da análise
├── scraper/               # Scraping paginado do fórum
├── analysis/              # NLP: stopwords, TF-IDF, clustering, índice
├── app/                   # Streamlit: nuvem + tabela
├── requirements.txt
└── README.md
```

## Observações

- Respeite os termos de uso do Tibia/CipSoft ao fazer scraping; use delay entre requisições.
- Se o fórum exigir JavaScript para carregar os posts, pode ser necessário usar Playwright (não incluído por padrão).
