import argparse

import lru
import otimo


def main():
    parser = argparse.ArgumentParser(description="Acessos e faltas de página usando os algoritmos Ótimo e LRU.")

    #Argumentos obrigatórios para rodar
    parser.add_argument("arquivo_acessos", help="Caminho para o arquivo de acessos.")
    parser.add_argument("tamanho_memoria", help="Tamanho da memória física (ex: 8MB).")
    parser.add_argument("tamanho_pagina", help="Tamanho da página (ex: 4KB).")
    
    args = parser.parse_args()


    mem_size = lru.parse_size(args.tamanho_memoria)
    page_size = lru.parse_size(args.tamanho_pagina)

    num_frames = mem_size // page_size

    print(f"Memória : {lru.fmt_bytes(mem_size)}  |  Página: {lru.fmt_bytes(page_size)}  |  Quadros: {num_frames}")
    print("Analisando o arquivo (Passo 1/2)...")
    print("Simulando algoritmos (Passo 2/2)...")

    #Executa o algoritmo ótimo
    m_otimo = otimo.simulate_optimal_low_ram(args.arquivo_acessos, page_size, num_frames)
    
    #Executa o algoritmo LRU com um novo fluxo de leitura, para que não leia de onde o ótimo parou (última linha)
    with lru.open_text_stream(args.arquivo_acessos) as stream:
        m_lru = lru.simulate_lru(stream, page_size, num_frames)

    acessos_distintos = m_otimo["total_acessos"]

    #Páginas distintas = faltas por primeiro acesso
    paginas_distintas = m_otimo["falta_primeiro_acesso"] 
    
    faltas_otimo = m_otimo["falta_total"]
    faltas_lru = m_lru["falta_total"]

    #Cálculo do desempenho relativo
    if faltas_lru > 0:
        razao_desempenho = (faltas_otimo / faltas_lru) * 100
        porcentagem = razao_desempenho
    else:
        porcentagem = 100.0

    print(f"A memória física comporta {num_frames} páginas.")
    print(f"Há {acessos_distintos} acessos distintos no arquivo.")
    print(f"Há {paginas_distintas} páginas distintas no arquivo.")
    print(f"Com o algoritmo Ótimo ocorrem {faltas_otimo} faltas de pagina.")
    print(f"Com o algoritmo LRU ocorrem {faltas_lru} faltas de pagina, atingindo {porcentagem:.2f}% do desempenho do Ótimo.")

if __name__ == "__main__":
    main()