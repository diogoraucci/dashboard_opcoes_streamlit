# ============================================================
# Detector de Expansão / Contração de Volatilidade
# (Lógica de entradas INVERTIDA em relação à versão original)
# Versão Jupyter + Yahoo Finance
# ============================================================
# Nesta versão o monitoramento só começa quando os indicadores
# de volatilidade (VOL_21, BB_WIDTH e ADX) estão em suas MÁXIMAS
# (regime de expansão / trend forte). O sinal de "explosão"
# passa a marcar a CONTRAÇÃO que ocorre em seguida (range
# recuando abaixo do ATR), ou seja, o movimento oposto ao
# rompimento (breakout) da versão original.
# ============================================================

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import yfinance as yf
import MetaTrader5 as mt5

# ============================================================
# COLETA DE DADOS YFINANCE
# ============================================================
def carregar_dados(
    ticker="PETR4.SA",
    start="2018-01-01",
    end=None):

    print(f"Baixando {ticker}...")

    df = yf.download(
        ticker,
        start=start,
        end=end,
        auto_adjust=True,
        progress=False
    )

    # corrige MultiIndex do Yahoo
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df[
        [
            "Open",
            "High",
            "Low",
            "Close",
            "Volume"
        ]
    ]

    df.dropna(inplace=True)

    #print(
     #   f"{len(df)} pregões carregados"
    #)
    return df

# ============================================================
# COLETA DE DADOS MetaTrader5
# ============================================================
def cotacoes_mt5_OHLC(
    ticker,
    timeframe=mt5.TIMEFRAME_D1,
    n_barras=1000):

    
    """
    Coleta OHLCV do MetaTrader 5.

    Parâmetros
    ----------
    ticker : str
        Ex.: 'PETR4', 'WIN$', 'DOL$', 'EURUSD'

    timeframe :
        mt5.TIMEFRAME_M1
        mt5.TIMEFRAME_M5
        mt5.TIMEFRAME_M15
        mt5.TIMEFRAME_M30
        mt5.TIMEFRAME_H1
        mt5.TIMEFRAME_H4
        mt5.TIMEFRAME_D1
        mt5.TIMEFRAME_W1
        mt5.TIMEFRAME_MN1

    n_barras : int
        Quantidade de candles

    Retorna
    -------
    DataFrame
    """

    if not mt5.initialize():
        raise RuntimeError(
            f"Erro ao conectar no MT5:\n{mt5.last_error()}"
        )

    if not mt5.symbol_select(ticker, True):
        mt5.shutdown()
        raise ValueError(f"Ticker '{ticker}' não encontrado.")

    rates = mt5.copy_rates_from_pos(
        ticker,
        timeframe,
        0,
        n_barras
    )

    mt5.shutdown()

    if rates is None:
        raise ValueError("Nenhum dado retornado.")

    df = pd.DataFrame(rates)

    df["time"] = pd.to_datetime(
        df["time"],
        unit="s"
    )

    df.rename(
        columns={
            "time":"Data",
            "open":"Open",
            "high":"High",
            "low":"Low",
            "close":"Close",
            "tick_volume":"Volume",
            "real_volume":"RealVolume",
            "spread":"Spread"
        },
        inplace=True
    )

    df.set_index("Data", inplace=True)

    return df
    
# ============================================================
# INDICADORES
# ============================================================
atr = 14 #14
bolinger = 14 # 14
bolinger_std = 1 #2
adx = 14 # 14

'''keltner_ = 20 # 20
keltener_mult = 0.5 # 1.5
rsi = 14 # 14'''

# ============================================================
# NÍVEIS QUE DEFINEM AS ENTRADAS (SQUEEZE / EXPLOSÃO)
# ------------------------------------------------------------
# Variáveis externas à função detectar_contracao() para permitir
# testar diferentes configurações sem alterar o código interno.
# Todas são usadas como parâmetros default de detectar_contracao(),
# ou seja, também podem ser sobrescritas na própria chamada da
# função, ex.: detectar_contracao(df, adx_minimo=20)
# ============================================================

# --- VOL_21 (volatilidade realizada) -------------------------
VOL21_PERCENTIL = 0.80   # percentil mínimo de VOL_21 para squeeze (máxima)
VOL21_JANELA    = 252    # janela (em candles) do rolling do percentil

# --- BOLLINGER WIDTH ------------------------------------------
BB_WIDTH_PERCENTIL = 0.80   # percentil mínimo de BB Width para squeeze (máxima)
BB_WIDTH_JANELA    = 252    # janela (em candles) do rolling do percentil

# --- ADX --------------------------------------------------------
ADX_MINIMO = 25   # ADX mínimo para squeeze (trend forte / máxima)

# --- CONTRAÇÃO (sinal de "explosão", lógica invertida) ---------
# explosão = squeeze anterior & range < ATR / ATR_CONTRACAO_MULT
ATR_CONTRACAO_MULT = 1.5


def true_range(df):

    
    prev_close = df["Close"].shift(1)

    tr = pd.concat(
        [
            df["High"] - df["Low"],
            abs(df["High"] - prev_close),
            abs(df["Low"] - prev_close)
        ],
        axis=1
    ).max(axis=1)

    return tr

def ATR(df, period=atr):

    atr = (
        true_range(df)
        .ewm(
            alpha=1/period,
            adjust=False
        )
        .mean()
    )

    return atr



def bollinger(df, period=bolinger, std= bolinger_std):

    mid = (
        df["Close"]
        .rolling(period)
        .mean()
    )

    desvio = (
        df["Close"]
        .rolling(period)
        .std()
    )

    upper = mid + std * desvio
    lower = mid - std * desvio


    width = (
        upper - lower
    ) / mid


    return mid, upper, lower, width


'''def keltner(df, period=keltner_, mult=keltener_mult):

    mid = (
        df["Close"]
        .ewm(
            span=period,
            adjust=False
        )
        .mean()
    )


    atr = ATR(df,period)


    upper = mid + mult * atr
    lower = mid - mult * atr


    return mid, upper, lower'''




def ADX(df,period=adx):

    up = df["High"].diff()
    down = -df["Low"].diff()


    plus = np.where(
        (up>down)&(up>0),
        up,
        0
    )

    minus = np.where(
        (down>up)&(down>0),
        down,
        0
    )

    atr = ATR(df,period)

    plus_di = (
        pd.Series(plus,index=df.index)
        .ewm(alpha=1/period)
        .mean()
        /
        atr
        *
        100
    )

    minus_di = (
        pd.Series(minus,index=df.index)
        .ewm(alpha=1/period)
        .mean()
        /
        atr
        *
        100
    )

    dx = (
        abs(plus_di-minus_di)
        /
        (plus_di+minus_di)
    )*100

    return (
        dx
        .ewm(alpha=1/period)
        .mean()
    )

def percentil(series,window=252):

    return (
        series
        .rolling(window)
        .apply(
            lambda x:
            pd.Series(x)
            .rank(pct=True)
            .iloc[-1]*100
        )
    )

'''def RSI(df, period=rsi):

    delta = df["Close"].diff()

    ganho = delta.clip(lower=0)

    perda = -delta.clip(upper=0)

    media_ganho = ganho.ewm(
        alpha=1/period,
        adjust=False
    ).mean()

    media_perda = perda.ewm(
        alpha=1/period,
        adjust=False
    ).mean()

    rs = media_ganho / media_perda

    rsi = 100 - (100 / (1 + rs))

    return rsi'''
    
# ============================================================
# CÁLCULO DO SQUEEZE
# ============================================================
def detectar_contracao(
    df,
    vol21_percentil=VOL21_PERCENTIL,
    vol21_janela=VOL21_JANELA,
    bb_width_percentil=BB_WIDTH_PERCENTIL,
    bb_width_janela=BB_WIDTH_JANELA,
    adx_minimo=ADX_MINIMO,
    atr_contracao_mult=ATR_CONTRACAO_MULT):
    out=df.copy()

    (
        out["bb_mid"],
        out["bb_up"],
        out["bb_low"],
        out["bb_width"]
    ) = bollinger(out)

    '''(
        out["kc_mid"],
        out["kc_up"],
        out["kc_low"]
    ) = keltner(out)'''

    out["ATR"] = ATR(out)

    out["ATR_P80"] = (
        out["ATR"]
        .rolling(252)
        .quantile(0.80)
    )
    
    out["ATR_P20"] = (
        out["ATR"]
        .rolling(252)
        .quantile(0.20)
    )


    out["BB_WIDTH_P80"] = (
        out["bb_width"]
        .rolling(bb_width_janela)
        .quantile(bb_width_percentil)
    )
    
    out["BB_WIDTH_P20"] = (
        out["bb_width"]
        .rolling(252)
        .quantile(0.20)
    )

    
    out["ADX"] = ADX(out)

    out["bb_pct"] = percentil(out["bb_width"])
    out["atr_pct"] = percentil(out["ATR"])

    # Volatilidade realizada 21 dias anualizada
    retorno_log = np.log(
        out["Close"] /
        out["Close"].shift(1)
    )

    out["VOL_21"] = (
        retorno_log
        .rolling(21)
        .std()
        *
        np.sqrt(252) # ++++++++++................
    )

    out["VOL21_P80"] = (
        out["VOL_21"]
        .rolling(vol21_janela)
        .quantile(vol21_percentil)
    )
    
    out["VOL21_P20"] = (
        out["VOL_21"]
        .rolling(252)
        .quantile(0.20)
    )
    
    out["VOL_MEDIA"] = (
        out["VOL_21"]
        .rolling(252)
        .mean()
    )

    # squeeze clássico
    '''out["squeeze"] = (
        (out["bb_up"] < out["kc_up"])
        &
        (out["bb_low"] > out["kc_low"])
    )'''

    # ==========================================================
    # NOVA REGRA DE SQUEEZE (LÓGICA INVERTIDA)
    # ------------------------------------------------------------
    # Em vez de aguardar a COMPRESSÃO (indicadores nas mínimas),
    # o monitoramento agora só é iniciado quando os indicadores
    # de volatilidade estão em suas MÁXIMAS (expansão / trend
    # forte). Isso substitui os percentis P20 por P80 e inverte
    # o filtro do ADX (de <=25 para >=25).
    # ==========================================================
    out["squeeze"] = (
    
        (out["VOL_21"] >= out["VOL21_P80"])
        &
        (out["bb_width"] >= out["BB_WIDTH_P80"])
        &
        (out["ADX"] >= adx_minimo)
    
    )


    out["range"] = (
        out["High"] -
        out["Low"]
    )

    out["vol_media_volume"] = (
        out["Volume"]
        .rolling(20)
        .mean()
    )

    # ------------------------------------------------------------
    # "Explosão" agora marca a CONTRAÇÃO que segue o regime de
    # máxima volatilidade: o range do candle recua para menos de
    # 1/1.5 do ATR (movimento oposto ao rompimento da versão
    # original, que buscava range > 1.5 * ATR).
    # ------------------------------------------------------------
    out["explosao"] = (
        out["squeeze"].shift(1)
        &
        (out["range"] < out["ATR"] / atr_contracao_mult)
        #&
        #(out["Volume"] < 1.5 * out["vol_media_volume"])
    )

    '''out["RSI"] = RSI(out)
    
    out["RSI_P80"] = (
        out["RSI"]
        .rolling(21) #.rolling(252)  ###########################################################>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
        .quantile(0.80)
    )
    
    out["RSI_P20"] = (
        out["RSI"]
        .rolling(252)
        .quantile(0.20)
    )'''

    # ==========================================================
    # HL CUMSUM - ACUMULAÇÃO DA VARIAÇÃO INTRADIÁRIA
    # ==========================================================

    out["HL"] = (
        out["High"] -
        out["Low"]
    ).abs()


    out["HLpct"] = np.log(
        out["HL"] /
        out["HL"].shift(1)
    )


    out["HLcumsum"] = (
        out["HLpct"]
        .cumsum()
        .abs()
    )


    out["HLcumMM"] = (
        out["HLcumsum"]
        .rolling(60)
        .mean()
    )


    out["HL_P20"] = (
        out["HLcumsum"]
        .rolling(
            window=252,
            min_periods=50
        )
        .quantile(0.20)
    )


    out["HL_P80"] = (
        out["HLcumsum"]
        .rolling(
            window=252,
            min_periods=50
        )
        .quantile(0.80)
    )

    
    return out
    
# ============================================================
# RELATÓRIO
# ============================================================
def relatorio(df):
    print("\n===== SQUEEZES =====")
    eventos = df[df["squeeze"]]

    print(
        eventos[
            [
            "Close",
            "bb_pct",
            "atr_pct",
            "ADX"
            ]
        ]
        .tail(20)
    )

    print("\n===== EXPLOSÕES =====")

    print(
        df[df["explosao"]]
        [
        ["Close","Volume"]
        ]
    )

# ============================================================
# SINAL DE ENTRADA (Squeeze / Explosão)
# ============================================================
def verificar_sinal_entrada(df, ticker="", n_candles=1):
    """
    Verifica se há sinal de entrada nos últimos `n_candles` candles,
    considerando como sinal os eventos 'squeeze' e 'explosao'
    (os mesmos exibidos como marcadores no gráfico).

    Prioridade: Explosão > Squeeze > Sem sinal.
    (Explosão é o gatilho de entrada; Squeeze é o alerta de que o
    ativo está comprimido e pode gerar uma explosão em breve.)

    Retorna um dicionário com o resultado, para uso programático.
    """

    recorte = df.tail(n_candles)

    houve_explosao = bool(recorte["explosao"].any())
    houve_squeeze = bool(recorte["squeeze"].any())

    ultimo = df.iloc[-1]
    data_ultimo = df.index[-1]

    print("\n" + "=" * 60)
    print(f"SINAL DE ENTRADA{' - ' + ticker if ticker else ''}")
    print("=" * 60)
    print(f"Data do último candle: {data_ultimo}")
    print(f"Close.................: {ultimo['Close']:.2f}")
    print(f"ADX...................: {ultimo['ADX']:.2f}")
    print(f"Squeeze (último candle): {bool(ultimo['squeeze'])}")
    print(f"Explosão (último candle): {bool(ultimo['explosao'])}")

    if houve_explosao:
        status = "EXPLOSAO"
        print("\n>>> SINAL DE ENTRADA: EXPLOSÃO <<<")
        print("Compressão anterior rompida com expansão de range/volatilidade.")
    elif houve_squeeze:
        status = "SQUEEZE"
        print("\n>>> SINAL DE ATENÇÃO: SQUEEZE ATIVO <<<")
        print("Volatilidade comprimida — possível movimento (explosão) se aproximando.")
        print("Ainda NÃO é o gatilho de entrada, é um alerta de monitoramento.")
    else:
        status = "SEM_SINAL"
        print("\n>>> SEM SINAL DE ENTRADA no momento <<<")

    print("=" * 60 + "\n")

    return {
        "ticker": ticker,
        "data": data_ultimo,
        "status": status,
        "squeeze": bool(ultimo["squeeze"]),
        "explosao": bool(ultimo["explosao"]),
    }


# ============================================================
# GRÁFICO
# ============================================================
import plotly.graph_objects as go
from plotly.subplots import make_subplots


from plotly.subplots import make_subplots
import plotly.graph_objects as go


def plotar_interativo(df, ticker):
    fig = make_subplots(
        rows=6,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.02,
        row_heights=[
            0.38,
            0.14,
            0.12,
            0.12,
            0.12,
            0.12
        ],
        subplot_titles=[
            "Preço + Bollinger + Squeeze",
            "Volatilidade Realizada",
            "Bollinger Width",
            "ATR",
            "ADX",
            "HLcumsum - Compressão/Expansão"
        ]
    )

    # ==========================================================
    # CANDLESTICK
    # ==========================================================
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="Candlestick"
        ),
        row=1,
        col=1
    )
    # ==========================================================
    # BOLLINGER
    # ==========================================================
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["bb_up"],
            mode="lines",
            line=dict(width=1),
            name="BB Superior"
        ),
        row=1,
        col=1
    )
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["bb_mid"],
            mode="lines",
            line=dict(width=1),
            name="BB Média"
        ),
        row=1,
        col=1
    )

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["bb_low"],
            mode="lines",
            line=dict(width=1),
            name="BB Inferior"
        ),
        row=1,
        col=1
    )

    # ==========================================================
    # KELTNER
    # ==========================================================
    '''fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["kc_up"],
            mode="lines",
            line=dict(dash="dot"),
            name="KC Superior"
        ),
        row=1,
        col=1
    )
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["kc_low"],
            mode="lines",
            line=dict(dash="dot"),
            name="KC Inferior"
        ),
        row=1,
        col=1
    )'''

    # ==========================================================
    # SQUEEZE
    # ==========================================================
    sq = df[df["squeeze"]]
    fig.add_trace(
        go.Scatter(
            x=sq.index,
            y=sq["Close"],
            mode="markers",
            marker=dict(
                size=8,
                symbol="circle",
                color="black"
            ),
            name="Squeeze"
        ),
        row=1,
        col=1
    )

    # ==========================================================
    # EXPLOSÃO
    # ==========================================================
    ex = df[df["explosao"]]
    fig.add_trace(
        go.Scatter(
            x=ex.index,
            y=ex["Close"],
            mode="markers",
            marker=dict(
                size=13,
                symbol="triangle-up"
            ),
            name="Explosão"
        ),
        row=1,
        col=1
    )

    # ==========================================================
    # VOLATILIDADE
    # ==========================================================
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["VOL_21"] * 100,
            mode="lines",
            name="Vol 21"
        ),
        row=2,
        col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["VOL21_P80"] * 100,
            mode="lines",
            name="P80"
        ),
        row=2,
        col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["VOL21_P20"] * 100,
            mode="lines",
            name="P20"
        ),
        row=2,
        col=1
    )

    # ==========================================================
    # BOLLINGER WIDTH
    # ==========================================================
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["bb_width"],
            mode="lines",
            name="BB Width"
        ),
        row=3,
        col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["BB_WIDTH_P80"],
            mode="lines",
            name="P80"
        ),
        row=3,
        col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["BB_WIDTH_P20"],
            mode="lines",
            name="P20"
        ),
        row=3,
        col=1
    )
    # ==========================================================
    # ATR
    # ==========================================================
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["ATR"],
            mode="lines",
            name="ATR"
        ),
        row=4,
        col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["ATR_P80"],
            mode="lines",
            name="P80"
        ),
        row=4,
        col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["ATR_P20"],
            mode="lines",
            name="P20"
        ),
        row=4,
        col=1
    )

    '''fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["atr_pct"],
            mode="lines",
            name="ATR Percentil"
        ),
        row=4,
        col=1
    )'''

    # ==========================================================
    # ADX
    # ==========================================================
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["ADX"],
            mode="lines",
            name="ADX"
        ),
        row=5,
        col=1
    )
    fig.add_hline(
        y=25,
        line_dash="dash",
        row=5,
        col=1
    )
    # ==========================================================
    # HL CUMSUM
    # ==========================================================

    # ==========================================================
    # HL CUMSUM - BARRAS COLORIDAS POR REGIME
    # ==========================================================
    
    cores_hl = []
    
    for hl, mm in zip(
        df["HLcumsum"],
        df["HLcumMM"]
    ):
        
        if hl <= mm * 0.5:
            cores_hl.append("red")       # Compressão extrema
        
        elif hl >= mm * 2.0:
            cores_hl.append("green")     # Expansão / explosão
        
        else:
            cores_hl.append("gray")      # Normal
    
    
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df["HLcumsum"],
            name="HLcumsum",
            marker=dict(
                color=cores_hl
            ),
            opacity=1.0
        ),
        row=6,
        col=1
    )


    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["HLcumMM"],
            mode="lines",
            name="HLcumMM"
        ),
        row=6,
        col=1
    )


    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["HL_P20"],
            mode="lines",
            name="HL Percentil 20%",
            line=dict(
                dash="dash"
            )
        ),
        row=6,
        col=1
    )


    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["HL_P80"],
            mode="lines",
            name="HL Percentil 80%",
            line=dict(
                dash="dash"
            )
        ),
        row=6,
        col=1
    )
    # ==========================================================
    # VOLUME
    # ==========================================================
    '''fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["RSI"],
            mode="lines",
            name="RSI"
        ),
        row=6,
        col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["RSI_P80"],
            mode="lines",
            name="P80"
        ),
        row=6,
        col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["RSI_P20"],
            mode="lines",
            name="P20"
        ),
        row=6,
        col=1
    )
    
    fig.add_hline(
        y=70,
        line_dash="dash",
        row=6,
        col=1
    )
    
    fig.add_hline(
        y=30,
        line_dash="dash",
        row=6,
        col=1
    )'''
    # ==========================================================
    # MARCAR EXPLOSÕES NO VOLUME
    # ==========================================================
    '''fig.add_trace(
        go.Scatter(
            x=ex.index,
            y=ex["Volume"],
            mode="markers",
            marker=dict(
                size=10,
                symbol="triangle-up"
            ),
            name="Explosão"
        ),
        row=6,
        col=1
    )'''

    # ==========================================================
    # FORMATAÇÃO DOS EIXOS
    # ==========================================================
    fig.update_yaxes(
        title="Preço",
        row=1,
        col=1
    )

    fig.update_yaxes(
        title="HV 21 (%)",
        row=2,
        col=1
    )

    fig.update_yaxes(
        title="BB Width",
        row=3,
        col=1
    )

    fig.update_yaxes(
        title="ATR",
        row=4,
        col=1
    )
    fig.update_yaxes(
        title="ADX",
        row=5,
        col=1
    )

    fig.update_yaxes(
        title="HLcumsum",
        row=6,
        col=1
    )
    
    '''fig.update_yaxes(
        title="RSI",
        row=6,
        col=1
    )'''

    # ==========================================================
    # LAYOUT
    # ==========================================================
    fig.update_layout(
        title=f"{ticker} - Detector de Compressão e Explosão de Volatilidade",
        height=1600,
        hovermode="x unified",
        template="plotly_white",
        #legend=dict(
         #   orientation="h",
         #   y=1.02,
         #   x=0
        #),
        xaxis_rangeslider_visible=False
    )

    # ==========================================================
    # GRID
    # ==========================================================
    fig.update_xaxes(
        showgrid=True,
        gridwidth=0.5
    )

    fig.update_yaxes(
        showgrid=True,
        gridwidth=0.5
    )

    # ==========================================================
    # HOVER
    # ==========================================================

    fig.update_traces(
        hovertemplate="<b>%{x}</b><br>Valor: %{y:.2f}<extra></extra>",
        selector=dict(type="scatter")
    )
    fig.show()
# ============================================================
# EXECUÇÃO
# ============================================================




def backtest_squeeze(
    df,
    holding_period=20):
    """
    Backtest dos sinais de Squeeze.

    Para cada candle onde squeeze == True,
    calcula o retorno do fechamento após N períodos.
    """

    bt = (
        df[df["squeeze"]]
        .copy()
    )

    # preço de entrada
    bt["Entrada"] = bt["Close"]

    # índice da posição no dataframe original
    posicoes = df.index.get_indexer(bt.index)

    saida = []
    datas_saida = []
    retorno = []

    for pos in posicoes:

        pos_saida = pos + holding_period

        if pos_saida >= len(df):
            saida.append(np.nan)
            datas_saida.append(pd.NaT)
            retorno.append(np.nan)
            continue

        preco_saida = df["Close"].iloc[pos_saida]

        saida.append(preco_saida)
        datas_saida.append(df.index[pos_saida])

        retorno.append(
            (preco_saida / df["Close"].iloc[pos] - 1) * 100
        )

    bt["Data Saída"] = datas_saida
    bt["Saída"] = saida
    bt["Retorno %"] = retorno

    bt["Resultado"] = np.where(
        bt["Retorno %"] > 0,
        "Gain",
        "Loss"
    )

    return bt[
        [
            "Open",
            "High",
            "Low",
            "Close",
            "VOL_21",
            "ADX",
            "squeeze",
            "Data Saída",
            "Saída",
            "Retorno %",
            "Resultado"
        ]
    ]