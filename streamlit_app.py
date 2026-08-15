"""
streamlit_app.py — Dashboard de Opções (GEX + métricas de contrato), versão Streamlit.

Reaproveita 100% da engine de cálculo e dos gráficos originais:
  - motor_calculo.py  -> NÃO foi alterado. Continua sendo o motor de cálculo puro
                         (GEX, walls, gamma flip, PCR, IV skew, RSI, HV, Black-Scholes).
  - gerar_dashboard.py -> NÃO foi alterado. Suas funções `_fig_gex_profile`,
                         `_fig_direita`, `_card`, `_card_box`, `_tabela_pin_candidates`
                         e `_tabela_zonas` são importadas e reaproveitadas na íntegra,
                         então cards, tabelas, badges e gráficos mantêm exatamente o
                         mesmo visual (cores, fontes, layout interno) da versão HTML
                         estática. A função `gerar_dashboard()` original continua
                         disponível para exportar o HTML estático como download, se
                         você quiser manter esse uso.

Layout (2 colunas, proporção 2:3 — ver imagem de referência):
  - Coluna ESQUERDA (métricas): seletores (Ativo-objeto / CÓDIGO / Period) +
    todos os boxes/cards/tabelas — tanto os da opção (TIPO, STRIKE, VENCIMENTO,
    D.U., PREÇO, IV RANK/PERCENTIL, VOL...) quanto os do GEX (WALLS, GAMMA FLIP,
    PCR, SPOT, Pin Candidates, Significant GEX Zones) — nessa ordem, um empilhado
    no outro, dentro do MESMO container.
  - Coluna DIREITA (gráficos): os 4 gráficos empilhados — Preço/Volatilidade/RSI
    (subplot único, `_fig_direita`) e, embaixo, o Gamma Exposure Profile
    (`_fig_gex_profile`) — cada um seguido do seu disclaimer.
  Antes desta versão, o app usava 2 colunas 50/50 onde cada painel (GEX /
  Opção) trazia junto suas próprias métricas E seu próprio gráfico; agora as
  métricas de ambos ficam juntas à esquerda e os gráficos de ambos ficam juntos
  à direita — só rearranjo de camada de apresentação, cálculo e conteúdo
  idênticos (ver `_metricas_gex`/`_grafico_gex` e `_metricas_opcao`/`_grafico_opcao`).

O que mudou é só a camada de entrada/saída:
  - argparse (--codigo, --vencimento, --dir)  -> controles na sidebar
  - print() no console                        -> st.html / st.plotly_chart ao vivo
  - salvar um .html                           -> renderização nativa (+ export opcional)

Rodar localmente:
    pip install -r requirements.txt
    streamlit run streamlit_app.py
"""

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

import motor_calculo as m
import gerar_dashboard as gd
import gerar_dados_exemplo as gde

CORES = gd.CORES

st.set_page_config(page_title="Dashboard de Opções", page_icon="📊", layout="wide")


def _fmt_data_br(d) -> str:
    """dd/mm/aaaa. Idempotente: se já vier formatado (string), devolve como
    está em vez de re-parsear — evita ambiguidade dd/mm vs mm/dd ao reprocessar
    uma string já formatada (ex.: harness de teste do Streamlit reaplica o
    format_func em cima do próprio valor exibido)."""
    if isinstance(d, str):
        return d
    return pd.Timestamp(d).strftime("%d/%m/%Y")


# ----------------------------------------------------------------------------
# TEMA — reaproveita a paleta (gd.CORES) e as MESMAS classes CSS que
# gerar_dashboard.py já usa (.card, .box, .tabela, .cards-row...). O fundo/cor
# de texto base do app é resolvido por .streamlit/config.toml (tema nativo do
# Streamlit); aqui só injetamos as classes específicas do dashboard.
# ----------------------------------------------------------------------------

def _injetar_tema():
    # st.html() em vez de st.markdown(unsafe_allow_html=True): o conteúdo vai
    # direto pro DOM (sanitizado via DOMPurify), sem passar pelo parser de
    # markdown. st.markdown() tratava parte deste bloco (a partir de
    # .boxes-row) como texto de parágrafo em vez de CSS — st.html() não tem
    # esse problema porque nunca interpreta o conteúdo como markdown.
    st.html(
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
        'family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap">'
        f"<style>"
        f".titulo-painel {{ font-family:'JetBrains Mono',monospace; font-size:13px; color:{CORES['texto']}; margin-bottom:14px; }}"
        f".subtitulo {{ font-family:'JetBrains Mono',monospace; font-size:12px; color:{CORES['fraco']}; margin:18px 0 8px; text-transform:uppercase; letter-spacing:.05em; }}"
        f".cards-row {{ display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin-bottom:10px; }}"
        f".cards-row-3 {{ grid-template-columns:repeat(3,1fr); }}"
        f".card {{ background:{CORES['fundo']}; border:1px solid {CORES['borda']}; border-radius:8px; padding:10px 12px; text-align:center; }}"
        f".card-label {{ font-family:'JetBrains Mono',monospace; font-size:10px; color:{CORES['fraco']}; text-transform:uppercase; margin-bottom:6px; }}"
        f".card-value {{ font-family:'JetBrains Mono',monospace; font-size:16px; font-weight:600; color:{CORES['texto']}; }}"
        f".boxes-row {{ display:flex; flex-wrap:wrap; gap:8px; margin-bottom:8px; }}"
        f".box {{ border:1px solid {CORES['borda']}; border-radius:8px; padding:8px 14px; flex:1 1 150px; font-family:'JetBrains Mono',monospace; font-size:13px; white-space:nowrap; }}"
        f".box-label {{ color:{CORES['fraco']}; }}"
        f".box-value {{ color:{CORES['texto']}; font-weight:700; }}"
        f".tabela {{ width:100%; border-collapse:collapse; font-family:'JetBrains Mono',monospace; font-size:12px; margin-bottom:6px; color:{CORES['texto']}; }}"
        f".tabela th {{ text-align:left; color:{CORES['fraco']}; font-weight:500; padding:6px 8px; border-bottom:1px solid {CORES['borda']}; text-transform:uppercase; font-size:10px; }}"
        f".tabela td {{ padding:6px 8px; border-bottom:1px solid {CORES['borda']}; }}"
        f".disclaimer {{ margin-top:14px; font-size:11px; color:{CORES['fraco']}; line-height:1.5; }}"
        f".vol-badge {{ display:inline-block; margin-left:6px; padding:1px 7px; border-radius:10px; "
        f"font-size:10px; font-weight:600; text-transform:uppercase; letter-spacing:.03em; "
        f"background:{CORES['fundo']}; border:1px solid {CORES['borda']}; color:{CORES['fraco']}; "
        f"vertical-align:middle; }}"
        f"</style>"
    )


# ----------------------------------------------------------------------------
# WRAPPERS CACHEADOS — envolvem motor_calculo.py (inalterado) com
# @st.cache_data, pra não reprocessar CSV/GEX/BS a cada interação na sidebar.
# ----------------------------------------------------------------------------

@st.cache_data(show_spinner="Lendo CSVs...")
def carregar_dados_cached(ticker: str, diretorio: str):
    return m.carregar_dados(ticker, diretorio)


@st.cache_data(show_spinner="Calculando RSI e volatilidade histórica...")
def indicadores_precos_cached(precos: pd.DataFrame):
    return m.calcular_indicadores_precos(precos)


@st.cache_data(show_spinner="Calculando GEX, walls e gamma flip...")
def gex_cached(cadeia: pd.DataFrame, spot: float, data_ref: pd.Timestamp,
               vencimento_alvo: pd.Timestamp, r: float, q: float):
    return m.calcular_gex(cadeia, spot, data_ref, vencimento_alvo, r, q)


@st.cache_data(show_spinner="Calculando métricas do contrato (Black-Scholes + IV rank)...")
def metricas_opcao_cached(cadeia: pd.DataFrame, precos_ind: pd.DataFrame, spot: float,
                           data_ref: pd.Timestamp, r: float, q: float, ticker: str,
                           codigo, diretorio: str):
    return m.calcular_metricas_opcao(cadeia, precos_ind, spot, data_ref, r, q, ticker,
                                      codigo=codigo, diretorio=diretorio)


CAMINHO_COTACOES = Path(__file__).resolve().parent / "df_cotacoes.xlsx"


@st.cache_data(show_spinner="Carregando universo de ativos (df_cotacoes.xlsx)...")
def carregar_df_cotacoes() -> pd.DataFrame:
    """Lê df_cotacoes.xlsx (aba 'cotacoes') da raiz do repo: colunas = tickers,
    valores = fechamento diário, índice = data (1a coluna do Excel, sem nome)."""
    df = pd.read_excel(CAMINHO_COTACOES, sheet_name="cotacoes", index_col=0)
    df.index = pd.to_datetime(df.index)
    df.index.name = "data"
    return df


@st.cache_data(show_spinner="Calculando RSI e volatilidade histórica do ativo-objeto...")
def indicadores_ativo_cached(df_cotacoes: pd.DataFrame, ativo: str) -> pd.DataFrame:
    """Reaproveita m.calcular_indicadores_precos (RSI, HV) — só remonta a coluna
    do ativo escolhido no formato ('data','fechamento') que a função espera.
    Usado só pelos 3 gráficos (série histórica); os cards de VOL HISTÓRICA/IV
    RANK/IV PERCENTIL vêm de carregar_class_vol(), não daqui."""
    precos_ativo = df_cotacoes[[ativo]].reset_index()
    precos_ativo.columns = ["data", "fechamento"]
    return m.calcular_indicadores_precos(precos_ativo)


@st.cache_data(show_spinner="Carregando classificações de volatilidade (class_vol)...")
def carregar_class_vol() -> pd.DataFrame:
    """Lê df_cotacoes.xlsx (aba 'class_vol'): 1 linha por ticker, com Vol_Realizada/
    Vol_Rank/Vol_Percentil (valores em %) e suas respectivas *_class ('Alta'/'Baixa'/
    'Neutra') já pré-calculados. Indexado por 'ticker' pra lookup direto."""
    df = pd.read_excel(CAMINHO_COTACOES, sheet_name="class_vol")
    df = df.drop(columns=[c for c in df.columns if str(c).startswith("Unnamed")])
    return df.set_index("ticker")


def _localizar_caminho_opcoes() -> Path:
    """Aceita tanto 'df_opcoes.xlsx' quanto 'df_opcoess.xlsx' (nome usado no
    export original da raspagem) — evita quebrar o app por causa de um 's' a
    mais/a menos no nome do arquivo. Se nenhum dos dois existir, devolve o
    nome canônico mesmo assim (o erro de arquivo-não-encontrado aparece só
    quando o pandas tentar ler, com uma mensagem clara)."""
    base = Path(__file__).resolve().parent
    for nome in ("df_opcoes.xlsx", "df_opcoess.xlsx"):
        candidato = base / nome
        if candidato.exists():
            return candidato
    return base / "df_opcoes.xlsx"


CAMINHO_OPCOES = _localizar_caminho_opcoes()


@st.cache_data(show_spinner="Carregando cadeia de opções real (df_opcoes.xlsx)...")
def carregar_df_opcoes(ativo_objeto: str) -> pd.DataFrame:
    """Lê df_opcoes.xlsx (ou df_opcoess.xlsx), aba 'opcoes_{ativo_objeto}' —
    snapshot real da cadeia de opções do ativo-objeto selecionado (raspagem
    OPCOES.NET). Colunas esperadas nessa aba: 'Ticker' (código da opção, ex:
    PETRH834), 'Strike', 'Último' (preço de mercado), 'Dias úteis' (até o
    vencimento) e 'Tipo' (CALL/PUT). Se a aba não existir para o ativo pedido,
    o pandas levanta ValueError — tratado no call site."""
    df = pd.read_excel(CAMINHO_OPCOES, sheet_name=f"opcoes_{ativo_objeto}")
    df = df.drop(columns=[c for c in df.columns if str(c).startswith("Unnamed")])
    return df


def _vencimento_por_dias_uteis(dias_uteis) -> pd.Timestamp:
    """Data de hoje + `dias_uteis` dias ÚTEIS (sem calendário de feriados —
    mesma convenção 'só fins de semana' usada em motor_calculo.dias_uteis_ate,
    que usa np.busday_count puro). dias_uteis<=0 -> hoje."""
    hoje = pd.Timestamp.today().normalize()
    du = int(dias_uteis)
    if du <= 0:
        return hoje
    return hoje + pd.tseries.offsets.BDay(du)


@st.cache_data(show_spinner="Gerando dados sintéticos de exemplo...")
def gerar_dados_exemplo_em_disco(ticker: str, diretorio: str):
    """Gera os 3 CSVs sintéticos (gerar_dados_exemplo.py, inalterado) direto
    no diretório informado, pra reaproveitar o MESMO m.carregar_dados() dos
    outros modos — nenhum caminho de código novo pra dados sintéticos."""
    precos = gde.gerar_precos(ticker)
    spot0 = precos["fechamento"].iloc[-1]
    hoje = precos["data"].iloc[-1]
    cadeia = gde.gerar_cadeia_opcoes(ticker, spot0, hoje)
    params = pd.DataFrame([
        {"parametro": "taxa_livre_risco", "valor": 0.1075},
        {"parametro": "dividend_yield", "valor": 0.00},
    ])
    precos.to_csv(Path(diretorio, f"precos_historicos_{ticker}.csv"), index=False)
    cadeia.to_csv(Path(diretorio, f"cadeia_opcoes_{ticker}.csv"), index=False)
    params.to_csv(Path(diretorio, "parametros.csv"), index=False)


@st.cache_data(show_spinner="Calculando bandas de desvio-padrão...")
def bandas_desvio_padrao_cached(precos_ind_ativo: pd.DataFrame, period: int) -> pd.DataFrame:
    """Porta fielmente a lógica do script OMSF/NoTrend enviado:

      1) Normalização logarítmica do fechamento: log(close / close[0]).
      2) MM_NoTrend = média móvel SIMPLES (rolling), agora com janela = `period`
         (o slider "Period (EMA baseline p/ bandas)" — deixou de ser EMA e
         passou a ser a mesma rolling mean do script original, só que com
         janela ajustável em vez do 90 fixo).
      3) Close_NoTrend = log-close - MM_NoTrend.
      4) STD = desvio-padrão ROLLING (janela 252, como no script original) de
         Close_NoTrend — portanto, como STD é calculado em cima de
         Close_NoTrend, ele muda automaticamente junto com `period`.
      5) Bandas = MM_NoTrend ± N*STD, calculadas em escala log e depois
         projetadas de volta pra escala de preço (R$) via exp(), pra continuar
         sobrepondo corretamente o gráfico de preço existente.
    """
    close = precos_ind_ativo["fechamento"]
    preco_base = close.iloc[0]

    log_close = np.log(close / preco_base)
    mm_no_trend = log_close.rolling(period).mean()
    close_no_trend = log_close - mm_no_trend
    std = close_no_trend.rolling(252).std()

    bandas_log = pd.DataFrame(index=precos_ind_ativo.index)
    bandas_log["banda_0"] = mm_no_trend
    for n in (1, 2, 3):
        bandas_log[f"banda+{n}"] = mm_no_trend + std * n
        bandas_log[f"banda-{n}"] = mm_no_trend - std * n

    # volta pra escala de preço (R$): preco = preco_base * exp(log_normalizado)
    bandas = np.exp(bandas_log) * preco_base
    return bandas


# ----------------------------------------------------------------------------
# PAINÉIS — mesma composição de gd.gerar_dashboard(), só que renderizando
# nativamente (st.plotly_chart) em vez de embutir fig.to_html().
# ----------------------------------------------------------------------------

def _metricas_gex(gex: dict, ticker: str, data_ref: pd.Timestamp):
    """Título + cards + tabelas do painel GEX (SEM o gráfico) — coluna
    ESQUERDA (métricas) do layout novo."""
    venc_str = pd.Timestamp(gex["vencimento_alvo"]).strftime("%d %b %Y")
    hoje_str = pd.Timestamp(data_ref).strftime("%d %b %Y")

    st.html(
        f'<div class="titulo-painel">GEX {ticker}: snapshot {hoje_str} '
        f'&bull; expiry {venc_str}</div>')

    linha1 = "".join([
        gd._card("WALLS (C/P)", f"{gex['call_wall']:.2f} / {gex['put_wall']:.2f}"),
        gd._card("GAMMA FLIP", f"{gex['gamma_flip']:.2f}", CORES["neutro"]),
        gd._card("PCR (GLOBAL)", f"{gex['pcr']:.2f}"),
        gd._card("SPOT", f"{gex['spot']:.2f}"),
    ])
    st.html(f'<div class="cards-row">{linha1}</div>')

    st.html('<div class="subtitulo">Pin Candidates (&plusmn;5% from spot)</div>')
    st.html(gd._tabela_pin_candidates(gex["pin_candidates"]))

    cor_sent = (CORES["baixa"] if gex["sentiment"] == "Bearish"
                else CORES["alta"] if gex["sentiment"] == "Bullish" else CORES["fraco"])
    linha2 = "".join([
        gd._card("PCR (OI)", f"{gex['pcr']:.2f}"),
        gd._card("SENTIMENT", gex["sentiment"], cor_sent),
        gd._card("IV SKEW", f"{gex['iv_skew']:.2f}%"),
        gd._card("REGIME", gex["regime"], CORES["neutro"]),
        gd._card("FLIP DIST.", f"{gex['flip_dist']:.2f}%"),
        gd._card("HEDGING", gex["hedging"]),
    ])
    st.html(f'<div class="cards-row cards-row-3">{linha2}</div>')

    st.html('<div class="subtitulo">Significant GEX Zones</div>')
    st.html(gd._tabela_zonas(gex["zonas_significativas"]))


def _grafico_gex(gex: dict, ticker: str):
    """Gráfico de perfil de GEX (SEM as métricas) — coluna DIREITA (gráficos)
    do layout novo, embaixo do gráfico de Preço/Vol/RSI."""
    st.plotly_chart(gd._fig_gex_profile(gex, ticker), use_container_width=True,
             config={"displayModeBar": False}, key="fig_gex")

    st.html(
        '<div class="disclaimer">Convenção assumida: dealers líquidos COMPRADOS em calls e '
        'VENDIDOS em puts (padrão usado por trackers públicos de GEX). Ajuste o sinal no '
        'código se a sua fonte de dados indicar o oposto para este ativo/mercado.</div>')


CORES_CLASSIFICACAO = {
    "Alta": CORES["alta"],      # verde
    "Baixa": "#e056c8",         # magenta
    "Neutra": "#ffffff",        # branco
}


def _badge(valor_fmt: str, classe: str) -> str:
    cor = CORES_CLASSIFICACAO.get(classe, CORES["fraco"])
    return (f'{valor_fmt}<span class="vol-badge" '
            f'style="background:{cor}; border-color:{cor}; color:{CORES["fundo"]};">'
            f'{classe}</span>')


def _metricas_opcao(opcao: dict, df_cotacoes: pd.DataFrame, class_vol: pd.DataFrame, ticker_atual: str):
    """Seletores (Ativo-objeto / CÓDIGO / Period) + boxes de métricas do
    contrato (SEM o gráfico) — coluna ESQUERDA (métricas) do layout novo.
    Devolve os dados que o gráfico de Preço/Vol/RSI precisa, pra serem
    usados depois na coluna DIREITA (gráficos)."""
    ativos = df_cotacoes.columns.tolist()
    idx_default = ativos.index(ticker_atual) if ticker_atual in ativos else 0

    col_ativo, col_codigo, col_period = st.columns([1.1, 1.3, 0.9])
    with col_ativo:
        ativo_objeto = st.selectbox(
            "Ativo-objeto", ativos, index=idx_default,
            help="Universo de df_cotacoes.xlsx (aba 'cotacoes') — independente do ticker/cadeia "
                 "de opções carregado na sidebar.")

    # -- Cadeia de opções REAL do ativo-objeto (df_opcoes.xlsx, aba
    # 'opcoes_{ativo_objeto}'). O seletor CÓDIGO é montado a partir da
    # coluna 'Ticker' dessa aba, igual ao seletor Ativo-objeto é montado
    # a partir das colunas de df_cotacoes.xlsx.
    linha_opcao = None
    try:
        df_opcoes_ativo = carregar_df_opcoes(ativo_objeto)
    except FileNotFoundError:
        df_opcoes_ativo = None
    except ValueError:
        # aba 'opcoes_{ativo_objeto}' não existe pra esse ativo
        df_opcoes_ativo = None

    with col_codigo:
        if df_opcoes_ativo is not None and "Ticker" in df_opcoes_ativo.columns and len(df_opcoes_ativo):
            codigos_opcao = sorted(df_opcoes_ativo["Ticker"].astype(str).unique())
            codigo_opcao_sel = st.selectbox(
                "CÓDIGO OPÇÃO", codigos_opcao, key=f"codigo_opcao_{ativo_objeto}",
                help=f"Contratos da aba 'opcoes_{ativo_objeto}' em df_opcoes.xlsx.")
            linha_opcao = df_opcoes_ativo.loc[
                df_opcoes_ativo["Ticker"].astype(str) == codigo_opcao_sel].iloc[0]
        else:
            st.selectbox("CÓDIGO", ["— sem aba opcoes_" + ativo_objeto + " —"], disabled=True)

    with col_period:
        period = st.slider("Period (Média Móvel)", min_value=20, max_value=300,
                            value=50, step=5)

    precos_ind_ativo = indicadores_ativo_cached(df_cotacoes, ativo_objeto)
    preco_atual = float(precos_ind_ativo["fechamento"].iloc[-1])
    bandas = bandas_desvio_padrao_cached(precos_ind_ativo, period)

    if ativo_objeto in class_vol.index:
        lv = class_vol.loc[ativo_objeto]
        vol_hist_fmt = _badge(f"{lv['Vol_Realizada']:.2f}%", lv["Vol_Hist_class"])
        iv_rank_fmt = _badge(f"{lv['Vol_Rank']:.2f}%", lv["Vol_Rank_class"])
        iv_pctl_fmt = _badge(f"{lv['Vol_Percentil']:.2f}%", lv["Vol_Perc_class"])
    else:
        vol_hist_fmt = iv_rank_fmt = iv_pctl_fmt = "— (sem linha em class_vol)"

    # Campos preenchidos a partir do contrato REAL selecionado em CÓDIGO
    # (df_opcoes.xlsx). Se a aba não existir para o ativo, cai de volta
    # pro contrato sintético/CSV (`opcao`) selecionado na sidebar, só pra
    # o painel não quebrar.
    if linha_opcao is not None:
        strike_fmt = f"{float(linha_opcao['Strike']):.2f}"
        preco_mkt_fmt = f"{float(linha_opcao['Último']):.2f}"
        du_fmt = f"{int(linha_opcao['Dias úteis'])} DIA(S)"
        vencimento_fmt = _vencimento_por_dias_uteis(linha_opcao["Dias úteis"]).strftime("%d-%m-%Y")
        tipo_fmt = str(linha_opcao["Tipo"]).upper()
    else:
        strike_fmt = f"{opcao['strike']:.2f}"
        preco_mkt_fmt = f"{opcao['preco_mercado']:.2f}"
        du_fmt = f"{opcao['dias_uteis']} DIA(S)"
        vencimento_fmt = pd.Timestamp(opcao["vencimento"]).strftime("%d-%m-%Y")
        tipo_fmt = opcao["tipo"]

    linha1 = "".join([
        gd._card_box("TIPO", tipo_fmt),
        gd._card_box("STRIKE", strike_fmt),
        gd._card_box("VENCIMENTO", vencimento_fmt),
        gd._card_box("DIAS ÚTEIS", du_fmt),
    ])
    st.html(f'<div class="boxes-row">{linha1}</div>')

    linha2 = "".join([
        gd._card_box("PREÇO AÇÃO", f"{preco_atual:.2f}"),
        gd._card_box("PREÇO MKT", preco_mkt_fmt),
        gd._card_box("PREÇO TEÓRICO", f"{opcao['preco_teorico']:.2f}"),
        gd._card_box("IV PERCENTIL", iv_pctl_fmt),
        gd._card_box("IV RANK", iv_rank_fmt),
        gd._card_box("VOL HISTÓRICA", vol_hist_fmt),
        gd._card_box("VOL IMPLÍCITA", f"{opcao['iv_implicita']:.2f}%"),
    ])
    st.html(f'<div class="boxes-row">{linha2}</div>')

    return {"precos_ind_ativo": precos_ind_ativo, "ativo_objeto": ativo_objeto,
            "bandas": bandas, "period": period}


def _grafico_opcao(precos_ind_ativo: pd.DataFrame, ativo_objeto: str, bandas: pd.DataFrame, period: int):
    """Gráfico de Preço/Vol/RSI (SEM as métricas) — coluna DIREITA (gráficos)
    do layout novo, no topo (acima do gráfico de GEX)."""
    st.plotly_chart(gd._fig_direita(precos_ind_ativo, ativo_objeto, bandas=bandas), use_container_width=True,
             config={"displayModeBar": False}, key="fig_direita")

    '''st.html(
        f'<div class="disclaimer">Bandas no gráfico de Preço: baseline (azul) = média móvel '
        f'simples de {period} períodos sobre o log-preço normalizado de {ativo_objeto} '
        f'(equivalente ao MM_NoTrend do script OMSF/NoTrend, só que com janela ajustável em vez '
        f'do rolling(90) fixo); bandas verdes/vermelhas = baseline &plusmn; 1/2/3 desvios-padrão '
        f'ROLLING (janela 252) de (log-preço &minus; baseline), depois convertidas de volta pra '
        f'escala de preço (R$) — replica fielmente o script OMSF/NoTrend que você enviou. '
        f'VOL HISTÓRICA / IV RANK / IV PERCENTIL de {ativo_objeto}: valores e '
        f'classificação (Alta/Baixa/Neutra) pré-calculados na aba <code>class_vol</code> de '
        f'df_cotacoes.xlsx. CÓDIGO / TIPO / STRIKE / VENCIMENTO / D.U. / PREÇO MKT acima vêm do '
        f'contrato selecionado em "CÓDIGO", lido em tempo real da aba '
        f'<code>opcoes_{ativo_objeto}</code> de df_opcoes.xlsx (VENCIMENTO = hoje + D.U. dias '
        f'úteis, sem calendário de feriados). PREÇO TEÓRICO / VOL IMPLÍCITA continuam vindo do '
        f'contrato sintético/CSV selecionado em "Contrato em destaque" na sidebar — ainda não há '
        f'IV na cadeia real pra recalcular esses dois via Black-Scholes.</div>')'''


# ----------------------------------------------------------------------------
# SIDEBAR — substitui o argparse original (ticker, --dir, --codigo, --vencimento)
# ----------------------------------------------------------------------------

def _sidebar_configuracao():
    st.sidebar.markdown("### ⚙️ Configuração")
    ticker = st.sidebar.text_input("Ticker", value="PETR4").strip().upper()

    fonte = st.sidebar.radio(
        "Fonte dos dados",
        ["Dados de exemplo (sintéticos)", "Diretório local", "Upload de CSVs"],
        index=0,
        help="'Dados de exemplo' gera os mesmos CSVs sintéticos de gerar_dados_exemplo.py, "
             "só pra você testar o dashboard sem precisar de dados reais.",
    )

    diretorio_manual = "."
    uploads = {}
    if fonte == "Diretório local":
        diretorio_manual = st.sidebar.text_input(
            "Diretório dos CSVs", value=".",
            help=f"Deve conter precos_historicos_{ticker}.csv, cadeia_opcoes_{ticker}.csv "
                 f"e parametros.csv")
    elif fonte == "Upload de CSVs":
        uploads["precos"] = st.sidebar.file_uploader(f"precos_historicos_{ticker}.csv", type="csv")
        uploads["cadeia"] = st.sidebar.file_uploader(f"cadeia_opcoes_{ticker}.csv", type="csv")
        uploads["params"] = st.sidebar.file_uploader("parametros.csv", type="csv")

    carregar = st.sidebar.button("📥 Carregar dados", type="primary", width='stretch')

    if carregar:
        if fonte == "Upload de CSVs" and not all(uploads.values()):
            st.sidebar.error("Envie os 3 arquivos CSV antes de carregar.")
        else:
            try:
                if fonte == "Dados de exemplo (sintéticos)":
                    diretorio_efetivo = tempfile.mkdtemp()
                    gerar_dados_exemplo_em_disco(ticker, diretorio_efetivo)
                elif fonte == "Diretório local":
                    diretorio_efetivo = diretorio_manual
                else:
                    diretorio_efetivo = tempfile.mkdtemp()
                    Path(diretorio_efetivo, f"precos_historicos_{ticker}.csv").write_bytes(
                        uploads["precos"].getvalue())
                    Path(diretorio_efetivo, f"cadeia_opcoes_{ticker}.csv").write_bytes(
                        uploads["cadeia"].getvalue())
                    Path(diretorio_efetivo, "parametros.csv").write_bytes(
                        uploads["params"].getvalue())

                precos, cadeia, params = carregar_dados_cached(ticker, diretorio_efetivo)
                precos_ind = indicadores_precos_cached(precos)

                st.session_state["dados"] = dict(
                    ticker=ticker, diretorio=diretorio_efetivo, fonte=fonte,
                    precos=precos, cadeia=cadeia, params=params, precos_ind=precos_ind,
                )
            except FileNotFoundError as e:
                st.sidebar.error(f"Arquivo não encontrado: {e}")
            except Exception as e:
                st.sidebar.error(f"Erro ao carregar dados: {e}")


# ----------------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------------

def main():
    _injetar_tema()
    _sidebar_configuracao()

    dados = st.session_state.get("dados")
    if not dados:
        st.info(
            "Configure o ticker e a fonte de dados na barra lateral e clique em "
            "**📥 Carregar dados** para começar. Use \"Dados de exemplo (sintéticos)\" "
            "se só quiser testar o dashboard sem CSVs reais.")
        return

    precos, cadeia, params = dados["precos"], dados["cadeia"], dados["params"]
    precos_ind, ticker, diretorio = dados["precos_ind"], dados["ticker"], dados["diretorio"]

    r = float(params["taxa_livre_risco"])
    q = float(params["dividend_yield"])
    spot = float(precos["fechamento"].iloc[-1])
    data_ref = precos["data"].iloc[-1]

    vencimentos = sorted(cadeia["vencimento"].unique())
    vencimento_alvo = st.sidebar.selectbox(
        "Vencimento (painel GEX)", vencimentos, format_func=_fmt_data_br)

    codigos = sorted(cadeia["codigo_opcao"].unique())
    escolha_codigo = st.sidebar.selectbox(
        "Contrato em destaque", ["Automático (CALL ATM, venc. mais curto)"] + codigos)
    codigo_escolhido = None if escolha_codigo.startswith("Automático") else escolha_codigo

    try:
        gex = gex_cached(cadeia, spot, data_ref, pd.Timestamp(vencimento_alvo), r, q)
        opcao = metricas_opcao_cached(cadeia, precos_ind, spot, data_ref, r, q,
                                       ticker, codigo_escolhido, diretorio)
    except ValueError as e:
        st.error(str(e))
        return

    st.caption(
        f"**{ticker}** · Spot {spot:.2f} · dado de referência "
        f"{pd.Timestamp(data_ref):%d/%m/%Y} · fonte: {dados['fonte']}")

    # Layout replicando a imagem de referência: coluna estreita à esquerda com
    # TODAS as métricas/seletores/tabelas (opção + GEX, nessa ordem) e coluna
    # larga à direita com TODOS os gráficos empilhados (Preço/Vol/RSI + perfil
    # de GEX, nessa ordem) — proporção 2:3 medida na imagem enviada.
    col_esq, col_dir = st.columns([2, 3], gap="large")

    dados_grafico_opcao = None
    with col_esq:
        with st.container(border=True):
            try:
                df_cotacoes = carregar_df_cotacoes()
                class_vol = carregar_class_vol()
                dados_grafico_opcao = _metricas_opcao(opcao, df_cotacoes, class_vol, ticker)
            except FileNotFoundError:
                st.error(
                    f"Não encontrei `df_cotacoes.xlsx` em `{CAMINHO_COTACOES}`. Ele precisa estar "
                    "na raiz do repositório, junto com o streamlit_app.py.")
            except ValueError as e:
                st.error(
                    f"Erro lendo `df_cotacoes.xlsx` — confira se as abas 'cotacoes' e 'class_vol' "
                    f"existem com esses nomes exatos. Detalhe: {e}")

            _metricas_gex(gex, ticker, data_ref)

    with col_dir:
        with st.container(border=True):
            if dados_grafico_opcao is not None:
                _grafico_opcao(**dados_grafico_opcao)
            _grafico_gex(gex, ticker)

    st.sidebar.divider()
    if st.sidebar.button("⬇️ Gerar HTML estático (export)", width='stretch'):
        tmp_out = Path(tempfile.mkdtemp(), f"dashboard_{ticker}.html")
        gd.gerar_dashboard(ticker, precos_ind, gex, opcao, data_ref, str(tmp_out))
        st.sidebar.download_button(
            f"Baixar dashboard_{ticker}.html", data=tmp_out.read_bytes(),
            file_name=f"dashboard_{ticker}.html", mime="text/html", width='stretch')


if __name__ == "__main__":
    main()