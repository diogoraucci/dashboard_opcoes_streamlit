"""
DASHBOARD DE OPÇÕES — GEX + Métricas de Contrato
===================================================
Lê os 3 CSVs (preços históricos, cadeia de opções, parâmetros), calcula todas
as métricas (GEX por strike, gamma flip, walls, PCR, IV skew, regime, RSI,
volatilidade histórica com bandas de percentil, Black-Scholes) e gera um
dashboard HTML com dois painéis, replicando a referência enviada.

Arquitetura 100% orientada a CSV: para usar dados reais, basta substituir os
3 arquivos de entrada mantendo os mesmos nomes de coluna — nenhuma alteração
de código é necessária. Veja o cabeçalho de gerar_dados_exemplo.py para o
schema exato de cada CSV.

Uso:
    python gerar_dados_exemplo.py PETR4        # gera os 3 CSVs de exemplo
    python dashboard_opcoes.py PETR4            # gera o dashboard HTML

Opcional:
    python dashboard_opcoes.py PETR4 --codigo PETR4G0360   # destaca um contrato específico
    python dashboard_opcoes.py PETR4 --vencimento 2026-07-31  # GEX de um vencimento específico
"""

import argparse
import pandas as pd

import motor_calculo as m
import gerar_dashboard as gd


def main():
    ap = argparse.ArgumentParser(description="Dashboard de opções (GEX + métricas de contrato)")
    ap.add_argument("ticker", help="Ticker do ativo-objeto, ex: PETR4")
    ap.add_argument("--dir", default=".", help="Diretório onde estão os CSVs de entrada")
    ap.add_argument("--codigo", default=None, help="Código da opção a destacar no painel direito")
    ap.add_argument("--vencimento", default=None, help="Vencimento (AAAA-MM-DD) a usar no painel de GEX")
    ap.add_argument("--saida", default=None, help="Nome do arquivo HTML de saída")
    args = ap.parse_args()

    ticker = args.ticker.upper()
    saida = args.saida or f"dashboard_{ticker}.html"

    print(f"Carregando CSVs de {ticker}...")
    precos, cadeia, params = m.carregar_dados(ticker, args.dir)

    r = float(params["taxa_livre_risco"])
    q = float(params["dividend_yield"])

    precos_ind = m.calcular_indicadores_precos(precos)
    spot = precos["fechamento"].iloc[-1]
    data_ref = precos["data"].iloc[-1]

    vencimento_alvo = pd.Timestamp(args.vencimento) if args.vencimento else cadeia["vencimento"].min()

    print(f"Spot: {spot:.2f} | Data ref.: {data_ref.date()} | Vencimento GEX: {vencimento_alvo.date()}")
    print("Calculando GEX, walls, gamma flip...")
    gex = m.calcular_gex(cadeia, spot, data_ref, vencimento_alvo, r, q)

    print("Calculando métricas do contrato em destaque...")
    opcao = m.calcular_metricas_opcao(cadeia, precos_ind, spot, data_ref, r, q,
                                       ticker, codigo=args.codigo, diretorio=args.dir)

    print("\n" + "=" * 70)
    print(f"GEX {ticker} — vencimento {vencimento_alvo.date()}")
    print("=" * 70)
    print(f"Spot            : {gex['spot']:.2f}")
    print(f"Call Wall       : {gex['call_wall']:.2f}   |  Put Wall: {gex['put_wall']:.2f}")
    print(f"Gamma Flip      : {gex['gamma_flip']:.2f}   |  Flip dist: {gex['flip_dist']:.2f}%")
    print(f"PCR             : {gex['pcr']:.2f}   |  Sentiment: {gex['sentiment']}")
    print(f"IV Skew         : {gex['iv_skew']:.2f}%   |  Regime: {gex['regime']}  ({gex['hedging']})")
    print("-" * 70)
    print(f"Contrato em destaque : {opcao['codigo']} ({opcao['tipo']}, strike {opcao['strike']:.2f})")
    print(f"Preço mercado        : {opcao['preco_mercado']:.2f}  |  Teórico (BS): {opcao['preco_teorico']:.2f}")
    print(f"IV implícita         : {opcao['iv_implicita']:.2f}%")
    print(f"IV Rank / Percentil  : {opcao['iv_rank']:.2f}% / {opcao['iv_percentil']:.2f}%  [{opcao['fonte_iv_rank']}]")
    print("=" * 70 + "\n")

    gd.gerar_dashboard(ticker, precos_ind, gex, opcao, data_ref, saida)
    print(f"Dashboard salvo em: {saida}")


if __name__ == "__main__":
    main()
