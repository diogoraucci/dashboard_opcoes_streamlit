"""Motor de cálculo do dashboard: lê os CSVs e produz todas as métricas
derivadas (GEX por strike, perfil de gamma, walls, gamma flip, PCR, IV skew,
regime, zonas significativas, RSI, HV com bandas de percentil, Black-Scholes)
"""

import os
import numpy as np
import pandas as pd
import bs


# ----------------------------------------------------------------------------
# LEITURA
# ----------------------------------------------------------------------------

def carregar_dados(ticker: str, diretorio: str = "."):
    precos = pd.read_csv(os.path.join(diretorio, f"precos_historicos_{ticker}.csv"),
                          parse_dates=["data"]).sort_values("data").reset_index(drop=True)
    cadeia = pd.read_csv(os.path.join(diretorio, f"cadeia_opcoes_{ticker}.csv"),
                          parse_dates=["data_snapshot", "vencimento"])
    params = pd.read_csv(os.path.join(diretorio, "parametros.csv")).set_index("parametro")["valor"]
    return precos, cadeia, params


# ----------------------------------------------------------------------------
# INDICADORES DE PREÇO (RSI + HV com bandas de percentil móvel)
# ----------------------------------------------------------------------------

def rsi(close: pd.Series, periodo: int = 14) -> pd.Series:
    delta = close.diff()
    ganho = delta.clip(lower=0)
    perda = -delta.clip(upper=0)
    avg_g = ganho.ewm(alpha=1 / periodo, adjust=False).mean()
    avg_p = perda.ewm(alpha=1 / periodo, adjust=False).mean()
    rs = avg_g / avg_p.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def volatilidade_historica(close: pd.Series, janela: int = 21) -> pd.Series:
    log_ret = np.log(close / close.shift(1))
    return log_ret.rolling(janela).std() * np.sqrt(252) * 100


def calcular_indicadores_precos(precos: pd.DataFrame, janela_rank: int = 252) -> pd.DataFrame:
    d = precos.copy().set_index("data")
    d["RSI"] = rsi(d["fechamento"])
    d["HV"] = volatilidade_historica(d["fechamento"])
    min_p = min(60, janela_rank // 4)
    d["HV_P20"] = d["HV"].rolling(janela_rank, min_periods=min_p).quantile(0.2)
    d["HV_P80"] = d["HV"].rolling(janela_rank, min_periods=min_p).quantile(0.8)
    d["HV_PCTL"] = d["HV"].rolling(janela_rank, min_periods=min_p).apply(
        lambda s: s.rank(pct=True).iloc[-1] * 100, raw=False)
    return d


# ----------------------------------------------------------------------------
# GEX: por strike (no spot atual) + perfil (spot hipotético) + walls + flip
# ----------------------------------------------------------------------------

def _gex_total_num_spot(sub: pd.DataFrame, spot_hipotetico: float, r: float, q: float) -> float:
    """Soma o GEX de toda a cadeia (sub-dataframe) recalculando a gamma de cada
    opção como se o ativo estivesse em spot_hipotetico. Usado tanto para o
    valor por strike (no spot real) quanto para a curva de perfil (spot variando)."""
    total = 0.0
    for row in sub.itertuples():
        T = row.T_anos
        if T <= 0:
            continue
        g = bs.gamma(spot_hipotetico, row.strike, T, r, row.iv, q)
        sinal = 1.0 if row.tipo == "CALL" else -1.0
        total += sinal * g * row.oi_contratos * row.multiplicador * spot_hipotetico ** 2 * 0.01
    return total


def calcular_gex(cadeia: pd.DataFrame, spot: float, data_ref: pd.Timestamp,
                  vencimento_alvo, r: float, q: float = 0.0) -> dict:
    sub = cadeia[cadeia["vencimento"] == vencimento_alvo].copy()
    sub["T_anos"] = (sub["vencimento"] - data_ref).dt.days.clip(lower=0) / 365.0

    strikes = sorted(sub["strike"].unique())

    # GEX por strike, avaliado no SPOT ATUAL (para as barras e as tabelas)
    linhas = []
    for k in strikes:
        grupo = sub[sub["strike"] == k]
        gex_k = _gex_total_num_spot(grupo, spot, r, q)
        oi_call = grupo.loc[grupo["tipo"] == "CALL", "oi_contratos"].sum()
        oi_put = grupo.loc[grupo["tipo"] == "PUT", "oi_contratos"].sum()
        linhas.append({"strike": k, "gex": gex_k, "gex_m": gex_k / 1e6,
                        "oi_call": oi_call, "oi_put": oi_put})
    gdf = pd.DataFrame(linhas).sort_values("strike").reset_index(drop=True)

    call_wall = float(gdf.loc[gdf["gex"].idxmax(), "strike"])
    put_wall = float(gdf.loc[gdf["gex"].idxmin(), "strike"])

    # Perfil de GEX total variando o SPOT HIPOTÉTICO (para a curva "Agg Gamma (Smooth)"
    # e para localizar o Gamma Flip com precisão)
    grade_spot = np.linspace(strikes[0], strikes[-1], 120)
    perfil = np.array([_gex_total_num_spot(sub, s, r, q) for s in grade_spot])

    flip = None
    for i in range(1, len(perfil)):
        if (perfil[i - 1] < 0 <= perfil[i]) or (perfil[i - 1] <= 0 < perfil[i]):
            x0, x1 = grade_spot[i - 1], grade_spot[i]
            y0, y1 = perfil[i - 1], perfil[i]
            flip = x0 if y1 == y0 else x0 + (0 - y0) * (x1 - x0) / (y1 - y0)
            break
    if flip is None:
        flip = float(grade_spot[np.argmin(np.abs(perfil))])

    oi_call_tot = sub.loc[sub["tipo"] == "CALL", "oi_contratos"].sum()
    oi_put_tot = sub.loc[sub["tipo"] == "PUT", "oi_contratos"].sum()
    pcr = oi_put_tot / oi_call_tot if oi_call_tot else np.nan

    iv_call_media = sub.loc[sub["tipo"] == "CALL", "iv"].mean()
    iv_put_media = sub.loc[sub["tipo"] == "PUT", "iv"].mean()
    iv_skew = (iv_put_media - iv_call_media) * 100

    flip_dist = (spot - flip) / spot * 100
    if abs(flip_dist) < 1.5:
        regime, hedging = "TRANSITION ZONE", "MIXED"
    elif flip_dist > 0:
        regime, hedging = "POSITIVE GAMMA (PINNING)", "DAMPEN"
    else:
        regime, hedging = "NEGATIVE GAMMA (AMPLIFICADO)", "AMPLIFY"

    sentiment = "Bearish" if pcr > 1.05 else ("Bullish" if pcr < 0.95 else "Neutral")

    # Pin candidates: strikes dentro de +-5% do spot, ordenados por |GEX|
    faixa = gdf[(gdf["strike"] >= spot * 0.95) & (gdf["strike"] <= spot * 1.05)]
    pin_candidates = faixa.reindex(faixa["gex"].abs().sort_values(ascending=False).index).head(5)

    # Zonas significativas: resistência (GEX+ acima do spot) / suporte (GEX- abaixo do spot)
    # Força calibrada pelos PRÓPRIOS percentis de |GEX| do ativo (não por valor fixo em R$,
    # que variaria demais entre um ativo de R$30 e um de R$65.000 como o BTC do exemplo).
    magnitudes = gdf["gex_m"].abs()
    p33, p66 = magnitudes.quantile([0.33, 0.66])

    def forca(gex_m):
        a = abs(gex_m)
        return "Strong" if a >= p66 else ("Mod" if a >= p33 else "Weak")

    resistencias = gdf[(gdf["strike"] > spot) & (gdf["gex"] > 0)].sort_values("gex", ascending=False).head(4)
    suportes = gdf[(gdf["strike"] < spot) & (gdf["gex"] < 0)].sort_values("gex").head(4)

    zonas = []
    for _, row in resistencias.iterrows():
        zonas.append({"zona": "Resistance", "strike": row["strike"], "gex_m": row["gex_m"],
                      "forca": forca(row["gex_m"])})
    for _, row in suportes.iterrows():
        zonas.append({"zona": "Support", "strike": row["strike"], "gex_m": row["gex_m"],
                      "forca": forca(row["gex_m"])})

    return {
        "gdf": gdf, "grade_spot": grade_spot, "perfil": perfil,
        "call_wall": call_wall, "put_wall": put_wall, "gamma_flip": flip,
        "spot": spot, "pcr": pcr, "sentiment": sentiment, "iv_skew": iv_skew,
        "regime": regime, "hedging": hedging, "flip_dist": flip_dist,
        "pin_candidates": pin_candidates, "zonas_significativas": pd.DataFrame(zonas),
        "vencimento_alvo": vencimento_alvo,
    }


# ----------------------------------------------------------------------------
# PAINEL DE OPÇÃO ESPECÍFICA: seleção de contrato + Black-Scholes + IV Rank/Percentil
# ----------------------------------------------------------------------------

def selecionar_contrato(cadeia: pd.DataFrame, spot: float, codigo: str = None) -> pd.Series:
    """Seleciona a linha do contrato a destacar no painel direito. Se `codigo`
    for informado, busca por ele; senão pega a CALL mais próxima do dinheiro
    (ATM) do vencimento mais curto disponível."""
    if codigo:
        achado = cadeia[cadeia["codigo_opcao"] == codigo]
        if achado.empty:
            raise ValueError(f"Código de opção '{codigo}' não encontrado na cadeia.")
        return achado.iloc[0]

    venc_curto = cadeia["vencimento"].min()
    sub = cadeia[(cadeia["vencimento"] == venc_curto) & (cadeia["tipo"] == "CALL")].copy()
    sub["dist"] = (sub["strike"] - spot).abs()
    return sub.loc[sub["dist"].idxmin()]


def dias_uteis_ate(data_ref: pd.Timestamp, vencimento: pd.Timestamp) -> int:
    if vencimento <= data_ref:
        return 0
    return int(np.busday_count(data_ref.date(), vencimento.date()))


def atualizar_log_iv(ticker: str, codigo: str, iv_hoje: float, diretorio: str = ".") -> pd.DataFrame:
    """Mantém um CSV local com a IV observada do contrato a cada execução,
    para que IV Rank / IV Percentile deixem de ser proxy assim que houver
    massa suficiente (>= 30 pregões logados)."""
    arquivo = os.path.join(diretorio, f"iv_log_{ticker}_{codigo}.csv")
    hoje = pd.Timestamp.now().normalize()

    if os.path.exists(arquivo):
        log = pd.read_csv(arquivo, parse_dates=["data"])
    else:
        log = pd.DataFrame(columns=["data", "iv"])

    if not (log["data"] == hoje).any():
        log = pd.concat([log, pd.DataFrame([{"data": hoje, "iv": iv_hoje}])], ignore_index=True)
        log.to_csv(arquivo, index=False)
    return log


def iv_rank_percentile(log: pd.DataFrame, minimo_obs: int = 30):
    if log is None or len(log) < minimo_obs:
        return None, None
    serie = log["iv"].dropna()
    atual = serie.iloc[-1]
    rank = 50.0 if serie.max() == serie.min() else (atual - serie.min()) / (serie.max() - serie.min()) * 100
    pctl = serie.rank(pct=True).iloc[-1] * 100
    return rank, pctl


def calcular_metricas_opcao(cadeia: pd.DataFrame, precos_ind: pd.DataFrame, spot: float,
                             data_ref: pd.Timestamp, r: float, q: float,
                             ticker: str, codigo: str = None, diretorio: str = ".") -> dict:
    contrato = selecionar_contrato(cadeia, spot, codigo)
    du = dias_uteis_ate(data_ref, contrato["vencimento"])
    T = max((contrato["vencimento"] - data_ref).days, 0) / 365.0

    preco_teorico = bs.preco_teorico(spot, contrato["strike"], T, r, contrato["iv"],
                                      contrato["tipo"], q)

    log_iv = atualizar_log_iv(ticker, contrato["codigo_opcao"], contrato["iv"], diretorio)
    rank_real, pctl_real = iv_rank_percentile(log_iv)

    ultimo_preco = precos_ind.iloc[-1]
    if rank_real is None:
        iv_rank, iv_pctl, fonte_iv = ultimo_preco["HV_PCTL"], ultimo_preco["HV_PCTL"], "HV Percentile (proxy)"
    else:
        iv_rank, iv_pctl, fonte_iv = rank_real, pctl_real, "IV real (log local)"

    return {
        "ticker": ticker, "codigo": contrato["codigo_opcao"], "tipo": contrato["tipo"],
        "strike": contrato["strike"], "vencimento": contrato["vencimento"],
        "preco_mercado": contrato["preco_mercado"], "preco_teorico": preco_teorico,
        "spot": spot, "dias_uteis": du, "iv_implicita": contrato["iv"] * 100,
        "iv_rank": iv_rank, "iv_percentil": iv_pctl, "fonte_iv_rank": fonte_iv,
        "vol_historica": ultimo_preco["HV"], "n_obs_log_iv": len(log_iv),
    }
