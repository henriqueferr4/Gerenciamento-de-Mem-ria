# Ótimo para gerenciamento de memória - Rápido e Econômico em RAM

import io
import sys
import time
from array import array  # Estrutura nativa super compacta para números

try:
    import zstandard as zstd

    _ZSTD_AVAILABLE = True
except ImportError:
    _ZSTD_AVAILABLE = False


def parse_size(s: str) -> int:
    s = s.strip().upper()
    units = {"KB": 1024, "MB": 1024 ** 2, "GB": 1024 ** 3, "TB": 1024 ** 4}
    for suffix, mult in units.items():
        if s.endswith(suffix):
            return int(s[: -len(suffix)]) * mult
    return int(s)


def open_text_stream(filepath: str):
    if filepath.endswith(".zst"):
        if not _ZSTD_AVAILABLE:
            print("Erro: biblioteca 'zstandard' não encontrada.")
            sys.exit(1)

        class _ZstStream:
            def __enter__(self_inner):
                self_inner._fh = open(filepath, "rb")
                dctx = zstd.ZstdDecompressor(max_window_size=2 ** 31)
                self_inner._reader = dctx.stream_reader(self_inner._fh)
                self_inner._text = io.TextIOWrapper(self_inner._reader, encoding="utf-8")
                return self_inner._text

            def __exit__(self_inner, *_):
                self_inner._text.detach()
                self_inner._reader.close()
                self_inner._fh.close()

        return _ZstStream()
    else:
        return open(filepath, "r", encoding="utf-8")


# ---- Implementação do ÓTIMO OTIMIZADO ---- #

def simulate_optimal_fast_low_ram(filepath: str, page_size: int, num_frames: int) -> dict:
    # Usamos 'Q' (unsigned long long - 8 bytes) para suportar endereços/páginas gigantescos de 64-bits
    acessos = array('Q')
    seen_pages = set()

    print("1. Carregando e compactando dados na RAM...")
    with open_text_stream(filepath) as stream:
        for line in stream:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                address = int(line, 0)
            except ValueError:
                continue
            if address < 0:
                continue

            page = address // page_size
            acessos.append(page)

    total_acessos = len(acessos)
    if total_acessos == 0:
        return {
            "total_acessos": 0, "falta_total": 0, "falta_primeiro_acesso": 0,
            "falta_por_capacidade": 0, "porcent_faltas": 0.0,
        }

    print("2. Mapeando posições futuras...")
    # Cria o mapa de posições futuras
    futuro_indices = {}
    for idx, page in enumerate(acessos):
        if page not in futuro_indices:
            futuro_indices[page] = []
        futuro_indices[page].append(idx)

    # Ponteiro de controle para saber qual a próxima aparição da página
    ponteiros_futuro = {pag: 0 for pag in futuro_indices}

    frames = set()
    falta_total = 0
    falta_primeiro_acesso = 0
    falta_por_capacidade = 0

    print("3. Executando simulação do Algoritmo Ótimo...")
    for i, page in enumerate(acessos):
        ponteiros_futuro[page] += 1

        is_first_time = page not in seen_pages
        if is_first_time:
            seen_pages.add(page)

        # Hit
        if page in frames:
            continue

        # Miss
        falta_total += 1
        if is_first_time:
            falta_primeiro_acesso += 1
        else:
            falta_por_capacidade += 1

        # Espaço disponível nos quadros físicos
        if len(frames) < num_frames:
            frames.add(page)
        else:
            # Algoritmo Ótimo Real: Encontra quem vai demorar MAIS tempo para aparecer
            pag_substituir = None
            maior_distancia = -1

            for pag_memoria in frames:
                historico = futuro_indices[pag_memoria]
                ptr = ponteiros_futuro[pag_memoria]

                if ptr >= len(historico):
                    # Essa página NUNCA mais será usada. É a candidata perfeita.
                    pag_substituir = pag_memoria
                    break
                else:
                    proximo_uso = historico[ptr]
                    if proximo_uso > maior_distancia:
                        maior_distancia = proximo_uso
                        pag_substituir = pag_memoria

            frames.remove(pag_substituir)
            frames.add(page)

    porcent_faltas = (total_acessos - falta_total) / total_acessos if total_acessos else 0.0

    return {
        "total_acessos": total_acessos,
        "falta_total": falta_total,
        "falta_primeiro_acesso": falta_primeiro_acesso,
        "falta_por_capacidade": falta_por_capacidade,
        "porcent_faltas": porcent_faltas,
    }


# --- Formatação da saída ---- #

def fmt_bytes(b: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if b < 1024 or unit == "TB":
            return f"{b:.0f} {unit}" if b == int(b) else f"{b:.2f} {unit}"
        b /= 1024


def print_results(
        filepath: str,
        mem_size: int,
        page_size: int,
        num_frames: int,
        metrics: dict,
        elapsed: float,
) -> None:
    W = 52

    def row(label, value):
        print(f"║  {label:<21}: {str(value):<26}║")

    print()
    print("╔" + "═" * W + "╗")
    print("║     ÓTIMO OTIMIZADO       ║")
    print("╠" + "═" * W + "╣")
    row("Arquivo de acessos", filepath)
    row("Memória física", fmt_bytes(mem_size))
    row("Tamanho da página", fmt_bytes(page_size))
    row("Quadros disponíveis", num_frames)
    print("╠" + "═" * W + "╣")
    row("Endereços acessados", f"{metrics['total_acessos']:,}")
    print("╠" + "═" * W + "╣")
    row("Faltas de página", f"{metrics['falta_total']:,}")
    row("  ↳ Falta por 1º acesso", f"{metrics['falta_primeiro_acesso']:,}")
    row("  ↳ Por capacidade", f"{metrics['falta_por_capacidade']:,}")
    row("Porcentagem", f"{metrics['porcent_faltas'] * 100:.2f} %")
    print("╠" + "═" * W + "╣")
    row("Tempo de execução", f"{elapsed:.2f} s")
    if elapsed > 0:
        taxa = metrics['total_acessos'] / elapsed
        row("Taxa de leitura", f"{taxa:,.0f} acessos/s")
    print("╚" + "═" * W + "╝")
    print()


# ---- main ---- #

def main():
    if len(sys.argv) != 4:
        print("Uso: python otimo-rapido.py <arquivo_acessos> <tamanho_memoria> <tamanho_pagina>")
        sys.exit(1)

    filepath = sys.argv[1]
    mem_size = parse_size(sys.argv[2])
    page_size = parse_size(sys.argv[3])

    if page_size == 0:
        print("Tamanho de página inválido")
        sys.exit(1)

    num_frames = mem_size // page_size

    print(f"\nArquivo : {filepath} ")
    print(f"Memória : {fmt_bytes(mem_size)}  |  Página: {fmt_bytes(page_size)}  |  Quadros: {num_frames}")

    inicio = time.perf_counter()

    metrics = simulate_optimal_fast_low_ram(filepath, page_size, num_frames)

    elapsed = time.perf_counter() - inicio

    if metrics["total_acessos"] == 0:
        print("Nenhum acesso válido encontrado no arquivo.")
        sys.exit(1)

    print_results(filepath, mem_size, page_size, num_frames, metrics, elapsed)


if __name__ == "__main__":
    main()