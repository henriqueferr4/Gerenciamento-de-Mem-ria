# LRU para gerenciamento de memória - Falta de páginas

import io
import sys
import time
from collections import OrderedDict

# Solução ara ler direto os arquivos .zst de entrada
try:
    import zstandard as zstd
    _ZSTD_AVAILABLE = True
except ImportError:
    _ZSTD_AVAILABLE = False


# ---- Funções Auxiliares ---- #

# Converte strings do parametro de entrada em equivalente em bytes
def parse_size(s: str) -> int:
    s = s.strip().upper()
    units = {"KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}
    for suffix, mult in units.items():
        if s.endswith(suffix):
            return int(s[: -len(suffix)]) * mult
    return int(s)

# Abre arquivo de entrada . zst sem descomprimir
def open_text_stream(filepath: str):
    if filepath.endswith(".zst"):
        if not _ZSTD_AVAILABLE:
            print("Erro: biblioteca 'zstandard' não encontrada.")
            sys.exit(1)

        class _ZstStream:
            def __enter__(self_inner):
                self_inner._fh = open(filepath, "rb")
                dctx = zstd.ZstdDecompressor(max_window_size=2**31)
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


# ---- Implementação do LRU ---- #


def simulate_lru(text_stream, page_size: int, num_frames: int) -> dict:
    frames: OrderedDict[int, None] = OrderedDict()
    seen_pages: set[int] = set()

    total_acessos  = 0
    falta_total     = 0
    falta_primeiro_acesso = 0
    falta_por_capacidade   = 0

    for lineno, line in enumerate(text_stream, 1):
        line = line.strip()

        # Ignora linhas em branco 
        if not line or line.startswith("#"):
            continue

        # Converter endereço em número de página
        try:
            address = int(line, 0)        
        except ValueError:
            continue

        if address < 0:
            continue

        page = address // page_size
        total_acessos += 1

        is_first_time = page not in seen_pages
        if is_first_time:
            seen_pages.add(page)

        # Se tem pag disponivel 
        if page in frames: 
            frames.move_to_end(page)
        
        # Casos de falta de página
        else: 
            falta_total += 1

            # Falta por falta_primeiro_acesso acesso
            if is_first_time:
                falta_primeiro_acesso += 1
            
            # Falta por capacidade
            else:
                falta_por_capacidade += 1

            if len(frames) >= num_frames:
                # Expulsa a página menos recentemente usada (início do dict)
                frames.popitem(last=False)

            frames[page] = None             # insere no fim (MRU)


    porcent_faltas   = (total_acessos - falta_total) / total_acessos if total_acessos else 0.0

    return {
        "total_acessos":   total_acessos,
        "falta_total":      falta_total,
        "falta_primeiro_acesso": falta_primeiro_acesso,
        "falta_por_capacidade":  falta_por_capacidade,
        "porcent_faltas":       porcent_faltas,
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
    print("║        LRU        ║")
    print("╠" + "═" * W + "╣")
    row("Arquivo de acessos",            filepath)
    row("Memória física",     fmt_bytes(mem_size))
    row("Tamanho da página",  fmt_bytes(page_size))
    row("Quadros disponíveis", num_frames)
    print("╠" + "═" * W + "╣")
    row("Endereços acessados", f"{metrics['total_acessos']:,}")
    print("╠" + "═" * W + "╣")
    row("Faltas de página",    f"{metrics['falta_total']:,}")
    row("  ↳ Falta por falta_primeiro_acesso acesso",   f"{metrics['falta_primeiro_acesso']:,}")
    row("  ↳ Por capacidade", f"{metrics['falta_por_capacidade']:,}")
    row("Porcentagem",   f"{metrics['porcent_faltas']*100:.2f} %")
    print("╠" + "═" * W + "╣")
    row("Tempo de execução",  f"{elapsed:.2f} s")
    if elapsed > 0:
        taxa = metrics['total_acessos'] / elapsed
        row("Taxa de leitura",   f"{taxa:,.0f} acessos/s")
    print("╚" + "═" * W + "╝")
    print()


# ---- main ---- #

def main():
    if len(sys.argv) != 4:
        print("Uso: python lru.py <arquivo_acessos> <tamanho_memoria> <tamanho_pagina>")
        sys.exit(1)

    filepath  = sys.argv[1]
    mem_size  = parse_size(sys.argv[2])
    page_size = parse_size(sys.argv[3])

    if page_size == 0:
        print("Tamanho de página inválido")
        sys.exit(1)

    num_frames = mem_size // page_size


    print(f"\nArquivo : {filepath} ")
    print(f"Memória : {fmt_bytes(mem_size)}  |  Página: {fmt_bytes(page_size)}  |  Quadros: {num_frames}")
    print("Simulando LRU...\n")

    inicio = time.perf_counter()

    with open_text_stream(filepath) as stream:
        metrics = simulate_lru(stream, page_size, num_frames)

    elapsed = time.perf_counter() - inicio

    if metrics["total_acessos"] == 0:
        print("Nenhum acesso válido encontrado no arquivo.")
        sys.exit(1)

    print_results(filepath, mem_size, page_size, num_frames, metrics, elapsed)


if __name__ == "__main__":
    main()