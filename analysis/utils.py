"""
Utilitários para o app: divisão de textos em lotes.
"""

CHARS_PER_BATCH = 3500
BATCH_HEADER = "--- Comentário {n} ---\n"


def split_texts_into_batches(
    texts: list[str],
    *,
    max_chars: int = CHARS_PER_BATCH,
    header_template: str = BATCH_HEADER,
) -> list[str]:
    """
    Agrupa textos em lotes que não ultrapassam max_chars.
    Cada texto é precedido por um cabeçalho "--- Comentário N ---".
    Retorna lista de strings (cada string é um lote).
    """
    batches: list[str] = []
    current: list[str] = []
    current_len = 0
    for i, text in enumerate(texts, 1):
        header = header_template.format(n=i)
        block = header + (text or "") + "\n\n"
        block_len = len(block)
        if current_len + block_len > max_chars and current:
            batches.append("".join(current))
            current = []
            current_len = 0
        current.append(block)
        current_len += block_len
    if current:
        batches.append("".join(current))
    return batches
