"""
Gera 3 CSVs de EXEMPLO com a estrutura exata que o dashboard_opcoes.py espera.
Os valores são sintéticos, mas internamente consistentes: a cadeia de opções
é construída com Black-Scholes de verdade (preço, gamma, IV coerentes entre si).

Quando você tiver dados reais (export de corretora, OpLab, om-qs etc.), é só
substituir estes 3 arquivos MANTENDO OS MESMOS NOMES DE COLUNA — o dashboard
não precisa de nenhuma alteração de código.

Gera:
    precos_historicos_<TICKER>.csv   -> série histórica diária do ativo-objeto
    cadeia_opcoes_<TICKER>.csv       -> snapshot da cadeia de opções (todos os strikes)
    parametros.csv                   -> taxa livre de risco e dividend yield assumidos

Uso:
    python gerar_dados_exemplo.py PETR4
"""

import argparse
import math
import numpy as np
import pandas as pd
import bs


def gerar_precos(ticker: str, dias: int = 500, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    # buffer de +2 e corte para os últimos `dias`: garante exatamente `dias`
    # elementos mesmo quando hoje cai em fim de semana (bdate_range com
    # `end` fora de dia útil retorna `dias-1` elementos, não `dias`)
    datas = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=dias + 2)[-dias:]

    # regime de retornos variável no tempo, pra HV e RSI terem "vida" (como no exemplo)
    retornos = rng.normal(0.0003, 0.014, dias)
    # injeta alguns regimes de vol/tendência distintos, tipo o gráfico de exemplo
    retornos[int(dias*0.55):int(dias*0.62)] += rng.normal(0, 0.02, int(dias*0.62)-int(dias*0.55))
    retornos[int(dias*0.80):] += 0.0015  # alta consistente no final, como no print

    close = 28.0 * np.exp(np.cumsum(retornos))
    high = close * (1 + np.abs(rng.normal(0, 0.007, dias)))
    low = close * (1 - np.abs(rng.normal(0, 0.007, dias)))
    open_ = close * (1 + rng.normal(0, 0.004, dias))
    volume = rng.integers(15_000_000, 60_000_000, dias)

    df = pd.DataFrame({
        "data": datas,
        "abertura": open_.round(2),
        "maxima": high.round(2),
        "minima": low.round(2),
        "fechamento": close.round(2),
        "volume": volume,
    })
    return df


def gerar_cadeia_opcoes(ticker: str, spot: float, data_snapshot: pd.Timestamp,
                         seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    # dois vencimentos: um bem próximo (semanal, como no exemplo D.U.=4) e um mensal
    venc_curto = data_snapshot + pd.Timedelta(days=4)
    venc_longo = data_snapshot + pd.Timedelta(days=32)

    passo = 0.50 if spot < 60 else 1.0
    strike_min = round((spot * 0.80) / passo) * passo
    strike_max = round((spot * 1.20) / passo) * passo
    strikes = np.arange(strike_min, strike_max + passo, passo)

    r = 0.1075   # taxa livre de risco assumida (ex: Selic) — ver parametros.csv
    q = 0.00     # dividend yield assumido

    linhas = []
    for venc, T_dias in [(venc_curto, (venc_curto - data_snapshot).days),
                          (venc_longo, (venc_longo - data_snapshot).days)]:
        T = T_dias / 365.0
        for k in strikes:
            moneyness = (k - spot) / spot

            # smile de IV: ATM ~ base, calls OTM um pouco mais baratas, puts OTM mais caras (skew)
            iv_base = 0.34 if T_dias <= 10 else 0.30
            skew = -0.55 * moneyness + 0.9 * moneyness ** 2
            iv = max(0.08, iv_base + skew + rng.normal(0, 0.01))

            # OI: decai com distância do spot; leve viés de puts OTM (proteção) e calls levemente OTM (especulação)
            dist_norm = moneyness / 0.10
            oi_base = 4000 * math.exp(-0.5 * dist_norm ** 2)
            oi_call = max(0, int(oi_base * rng.uniform(0.5, 1.3) * (1.15 if moneyness > 0 else 0.85)))
            oi_put = max(0, int(oi_base * rng.uniform(0.5, 1.3) * (1.35 if moneyness < 0 else 0.75)))

            for tipo, oi in [("CALL", oi_call), ("PUT", oi_put)]:
                iv_tipo = iv + (0.01 if tipo == "PUT" else 0.0)
                preco = bs.preco_teorico(spot, k, T, r, iv_tipo, tipo, q)
                preco = max(0.01, preco * rng.uniform(0.97, 1.03))
                gm = bs.gamma(spot, k, T, r, iv_tipo, q)
                dl = bs.delta(spot, k, T, r, iv_tipo, tipo, q)

                codigo = f"{ticker}{'G' if tipo=='CALL' else 'T'}{int(k*10):04d}"

                linhas.append({
                    "data_snapshot": data_snapshot.date(),
                    "ticker_ativo": ticker,
                    "codigo_opcao": codigo,
                    "tipo": tipo,
                    "strike": round(k, 2),
                    "vencimento": venc.date(),
                    "oi_contratos": oi,
                    "gamma": round(gm, 6),
                    "delta": round(dl, 4),
                    "iv": round(iv_tipo, 4),
                    "preco_mercado": round(preco, 2),
                    "multiplicador": 100,
                })

    return pd.DataFrame(linhas)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ticker", nargs="?", default="PETR4")
    args = ap.parse_args()
    ticker = args.ticker.upper()

    precos = gerar_precos(ticker)
    spot = precos["fechamento"].iloc[-1]
    hoje = precos["data"].iloc[-1]

    cadeia = gerar_cadeia_opcoes(ticker, spot, hoje)

    params = pd.DataFrame([
        {"parametro": "taxa_livre_risco", "valor": 0.1075, "descricao": "Ex: taxa Selic/CDI anualizada, em decimal"},
        {"parametro": "dividend_yield", "valor": 0.00, "descricao": "Dividend yield anualizado assumido, em decimal"},
    ])

    precos.to_csv(f"precos_historicos_{ticker}.csv", index=False)
    cadeia.to_csv(f"cadeia_opcoes_{ticker}.csv", index=False)
    params.to_csv("parametros.csv", index=False)

    print(f"Spot simulado: {spot:.2f}")
    print(f"precos_historicos_{ticker}.csv -> {len(precos)} linhas")
    print(f"cadeia_opcoes_{ticker}.csv -> {len(cadeia)} linhas ({cadeia['vencimento'].nunique()} vencimentos, "
          f"{cadeia['strike'].nunique()} strikes)")
    print("parametros.csv -> taxa_livre_risco, dividend_yield")


if __name__ == "__main__":
    main()
