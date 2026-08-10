"""Gera o dashboard HTML final, replicando o layout de dois painéis da imagem
de referência: GEX (esquerda) + métricas de opção específica (direita)."""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

CORES = {
    "fundo": "#0b0e14", "painel": "#12161f", "borda": "#232838",
    "texto": "#e6e9f0", "fraco": "#8a91a3",
    "alta": "#2fd48b", "baixa": "#ef5b5b", "neutro": "#f2b632", "accent": "#5b8def",
    "roxo": "#c25bef", "rosa": "#e0568c",
}


# ----------------------------------------------------------------------------
# GRÁFICO 1: Perfil de GEX (painel esquerdo)
# ----------------------------------------------------------------------------

def _fig_gex_profile(gex: dict, ticker: str):
    gdf = gex["gdf"]
    cores_barra = [CORES["alta"] if v >= 0 else CORES["baixa"] for v in gdf["gex_m"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(x=gdf["strike"], y=gdf["gex_m"], name="GEX $M", marker_color=cores_barra))
    fig.add_trace(go.Scatter(x=gex["grade_spot"], y=gex["perfil"] / 1e6, name="Agg Gamma (Smooth)",
                              line=dict(color=CORES["accent"], width=2)))

    for nome, x, cor, dash in [
        ("Spot Price", gex["spot"], CORES["texto"], "solid"),
        ("Gamma Flip", gex["gamma_flip"], CORES["neutro"], "dash"),
        ("Call Wall", gex["call_wall"], CORES["accent"], "dot"),
        ("Put Wall", gex["put_wall"], CORES["baixa"], "dot"),
    ]:
        fig.add_vline(x=x, line=dict(color=cor, width=1.4, dash=dash))
        fig.add_annotation(x=x, y=1.0, yref="paper", text=nome, showarrow=False,
                            font=dict(size=9, color=cor), yshift=10)

    fig.update_layout(
        template="plotly_dark", paper_bgcolor=CORES["painel"], plot_bgcolor=CORES["painel"],
        font=dict(color=CORES["texto"], family="JetBrains Mono, monospace", size=11),
        height=420, margin=dict(l=50, r=20, t=40, b=40),
        title=dict(text=f"{ticker} Gamma Exposure Profile", font=dict(size=14)),
        xaxis_title="Strike Price", yaxis_title="GEX ($ Millions)",
        legend=dict(orientation="h", y=-0.18, x=0, bgcolor="rgba(0,0,0,0)"),
    )
    fig.update_xaxes(gridcolor=CORES["borda"])
    fig.update_yaxes(gridcolor=CORES["borda"], zerolinecolor=CORES["fraco"])
    return fig


# ----------------------------------------------------------------------------
# GRÁFICOS 2-4: Preço / Volatilidade / RSI (painel direito)
# ----------------------------------------------------------------------------

def _fig_direita(precos_ind: pd.DataFrame, ticker: str, fonte_vol_nome: str = "Volatilidade Histórica (21 dias)",
                  bandas: pd.DataFrame = None):
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05,
        row_heights=[0.42, 0.28, 0.30],
        subplot_titles=(f"{ticker} — Preço", fonte_vol_nome + " - Baseada em Retornos", "RSI (14) calculado sobre os Retornos"),
    )

    if bandas is not None:
        # bandas verdes/vermelhas (± 1/2/3 desvios-padrão), sem entrada própria na legenda
        for n in (3, 2, 1):
            fig.add_trace(go.Scatter(x=bandas.index, y=bandas[f"banda-{n}"], name=f"Banda -{n}",
                                      line=dict(color=CORES["baixa"], width=1, dash="dot"),
                                      opacity=0.35 + 0.15 * (3 - n), showlegend=False), row=1, col=1)
        for n in (1, 2, 3):
            fig.add_trace(go.Scatter(x=bandas.index, y=bandas[f"banda+{n}"], name=f"Banda +{n}",
                                      line=dict(color=CORES["alta"], width=1, dash="dot"),
                                      opacity=0.35 + 0.15 * (3 - n), showlegend=False), row=1, col=1)
        # baseline (azul) por cima das bandas
        fig.add_trace(go.Scatter(x=bandas.index, y=bandas["banda_0"], name="Baseline (EMA)",
                                  line=dict(color=CORES["accent"], width=1.4, dash="dash"),
                                  showlegend=False), row=1, col=1)

    fig.add_trace(go.Scatter(x=precos_ind.index, y=precos_ind["fechamento"], name="Preço",
                              line=dict(color=CORES["neutro"], width=1.6)), row=1, col=1)

    if bandas is not None:
        close = precos_ind["fechamento"].reindex(bandas.index)
        std = bandas["banda+1"] - bandas["banda_0"]
        desvio = (close - bandas["banda_0"]) / std

        # Prioridade roxo > azul > rosa (faixas se sobrepõem; cada ponto recebe só a cor mais extrema)
        mask_roxo = (desvio >= 3) | (desvio <= -3)
        mask_azul = ~mask_roxo & ((desvio >= 1) | (desvio <= -2))
        mask_rosa = ~mask_roxo & ~mask_azul & ((desvio >= 1) | (desvio <= -1))

        for mask, cor, nome in (
            (mask_roxo, CORES["roxo"], "≥3σ / ≤-3σ"),
            (mask_azul, CORES["accent"], "≥2σ / ≤-2σ"),
            (mask_rosa, CORES["rosa"], "≥1σ / ≤-1σ"),
        ):
            if mask.any():
                fig.add_trace(go.Scatter(
                    x=close.index[mask], y=close[mask], mode="markers", name=nome,
                    marker=dict(color=cor, size=6, line=dict(color=CORES["fundo"], width=0.5)),
                    showlegend=False,
                ), row=1, col=1)

    fig.add_trace(go.Scatter(x=precos_ind.index, y=precos_ind["HV"], name="Vol. Histórica",
                              line=dict(color=CORES["accent"], width=1.6)), row=2, col=1)

    fig.add_trace(go.Scatter(x=precos_ind.index, y=precos_ind["RSI"], name="RSI",
                              line=dict(color="#e0568c", width=1.6)), row=3, col=1)
    fig.add_hline(y=70, line=dict(color=CORES["accent"], width=1, dash="dot"), row=3, col=1)
    fig.add_hline(y=30, line=dict(color=CORES["roxo"], width=1, dash="dot"), row=3, col=1)

    fig.update_layout(
        template="plotly_dark", paper_bgcolor=CORES["fundo"], plot_bgcolor=CORES["painel"],
        font=dict(color=CORES["texto"], family="Inter, Segoe UI, sans-serif"),
        height=780, margin=dict(l=55, r=30, t=60, b=30), showlegend=False,
    )
    fig.update_yaxes(title_text="R$", row=1, col=1)
    fig.update_yaxes(title_text="% Anualizada", row=2, col=1)
    for i in range(1, 4):
        fig.update_xaxes(gridcolor=CORES["borda"], row=i, col=1)
        fig.update_yaxes(gridcolor=CORES["borda"], row=i, col=1)
    return fig


# ----------------------------------------------------------------------------
# BLOCOS HTML (cards + tabelas)
# ----------------------------------------------------------------------------

def _card(rotulo, valor, cor=None):
    estilo = f"color:{cor};" if cor else ""
    return f'<div class="card"><div class="card-label">{rotulo}</div><div class="card-value" style="{estilo}">{valor}</div></div>'


def _card_box(rotulo, valor):
    return f'<div class="box"><span class="box-label">{rotulo}:</span> <span class="box-value">{valor}</span></div>'


def _tabela_pin_candidates(df: pd.DataFrame) -> str:
    linhas = ""
    for _, r in df.iterrows():
        cor = CORES["alta"] if r["gex"] >= 0 else CORES["baixa"]
        linhas += (f"<tr><td>{r['strike']:.2f}</td>"
                   f"<td style='color:{cor}'>{r['gex']/1e6:.2f}M</td>"
                   f"<td>{int(r['oi_call'])}</td><td>{int(r['oi_put'])}</td></tr>")
    return f"""<table class="tabela">
      <thead><tr><th>Strike</th><th>Dealer GEX</th><th>Calls OI</th><th>Puts OI</th></tr></thead>
      <tbody>{linhas}</tbody></table>"""


def _tabela_zonas(df: pd.DataFrame) -> str:
    linhas = ""
    for _, r in df.iterrows():
        cor = CORES["baixa"] if r["zona"] == "Resistance" else CORES["alta"]
        linhas += (f"<tr><td style='color:{cor}'>{r['zona']}</td><td>{r['strike']:.2f}</td>"
                   f"<td>{r['gex_m']:.2f}M</td><td>{r['forca']}</td></tr>")
    return f"""<table class="tabela">
      <thead><tr><th>Zone</th><th>Strike</th><th>GEX $M</th><th>Strength</th></tr></thead>
      <tbody>{linhas}</tbody></table>"""


# ----------------------------------------------------------------------------
# MONTAGEM FINAL
# ----------------------------------------------------------------------------

def gerar_dashboard(ticker: str, precos_ind: pd.DataFrame, gex: dict, opcao: dict,
                     data_ref: pd.Timestamp, saida: str):

    fig_gex = _fig_gex_profile(gex, ticker)
    fig_direita = _fig_direita(precos_ind, ticker)

    html_fig_gex = fig_gex.to_html(full_html=False, include_plotlyjs="cdn")
    html_fig_direita = fig_direita.to_html(full_html=False, include_plotlyjs=False)

    venc_str = gex["vencimento_alvo"].strftime("%d %b %Y")
    hoje_str = data_ref.strftime("%d %b %Y")

    # ---- painel esquerdo: GEX ----
    painel_esq = f"""
    <div class="painel">
      <div class="titulo-painel">GEX {ticker}: snapshot: {hoje_str} &bull; expiry: {venc_str}</div>
      <div class="cards-row">
        {_card("WALLS (C/P)", f"{gex['call_wall']:.2f} / {gex['put_wall']:.2f}")}
        {_card("GAMMA FLIP", f"{gex['gamma_flip']:.2f}", CORES["neutro"])}
        {_card("PCR (GLOBAL)", f"{gex['pcr']:.2f}")}
        {_card("SPOT", f"{gex['spot']:.2f}")}
      </div>

      <div class="subtitulo">Pin Candidates (&plusmn;5% from spot)</div>
      {_tabela_pin_candidates(gex["pin_candidates"])}

      <div class="cards-row cards-row-3">
        {_card("PCR (OI)", f"{gex['pcr']:.2f}")}
        {_card("SENTIMENT", gex["sentiment"], CORES["baixa"] if gex["sentiment"]=="Bearish" else CORES["alta"] if gex["sentiment"]=="Bullish" else CORES["fraco"])}
        {_card("IV SKEW", f"{gex['iv_skew']:.2f}%")}
        {_card("REGIME", gex["regime"], CORES["neutro"])}
        {_card("FLIP DIST.", f"{gex['flip_dist']:.2f}%")}
        {_card("HEDGING", gex["hedging"])}
      </div>

      <div class="subtitulo">Significant GEX Zones</div>
      {_tabela_zonas(gex["zonas_significativas"])}

      {html_fig_gex}

      <div class="disclaimer">
        Convenção assumida: dealers líquidos COMPRADOS em calls e VENDIDOS em puts
        (padrão usado por trackers públicos de GEX). Ajuste o sinal no código se a
        sua fonte de dados indicar o oposto para este ativo/mercado.
      </div>
    </div>
    """

    # ---- painel direito: métricas da opção ----
    painel_dir = f"""
    <div class="painel">
      <div class="boxes-row">
        {_card_box("TICKER", opcao['ticker'])}
        {_card_box("STRIKE", f"{opcao['strike']:.2f}")}
        {_card_box("VENCIMENTO", opcao['vencimento'].strftime('%d-%m-%Y'))}
        {_card_box("PREÇO MKT", f"{opcao['preco_mercado']:.2f}")}
        {_card_box("IV PERCENTIL", f"{opcao['iv_percentil']:.2f}%")}
        {_card_box("VOL HISTÓRICA", f"{opcao['vol_historica']:.2f}%")}
      </div>
      <div class="boxes-row">
        {_card_box("PREÇO", f"{opcao['spot']:.2f}")}
        {_card_box("CÓDIGO", opcao['codigo'])}
        {_card_box("D.U.", f"{opcao['dias_uteis']} DIA(S)")}
        {_card_box("PREÇO TEÓRICO", f"{opcao['preco_teorico']:.2f}")}
        {_card_box("IV RANK", f"{opcao['iv_rank']:.2f}%")}
        {_card_box("VOL IMPLÍCITA", f"{opcao['iv_implicita']:.2f}%")}
      </div>

      {html_fig_direita}

      <div class="disclaimer">
        IV Rank / IV Percentil: {opcao['fonte_iv_rank']} &mdash; log local com {opcao['n_obs_log_iv']}
        observação(ões) para o contrato {opcao['codigo']}. Passa a usar IV real do
        contrato assim que o log acumular 30+ execuções.
      </div>
    </div>
    """

    html = f"""<!DOCTYPE html>
<html lang="pt-br"><head><meta charset="utf-8"><title>Dashboard de Opções — {ticker}</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ background:{CORES['fundo']}; color:{CORES['texto']}; margin:0; padding:20px;
          font-family: Inter, 'Segoe UI', sans-serif; }}
  .container {{ display:flex; gap:20px; align-items:flex-start; }}
  .painel {{ flex:1; min-width:0; background:{CORES['painel']}; border:1px solid {CORES['borda']};
             border-radius:10px; padding:18px; }}
  .titulo-painel {{ font-family:'JetBrains Mono',monospace; font-size:13px; color:{CORES['texto']};
                     margin-bottom:14px; }}
  .subtitulo {{ font-family:'JetBrains Mono',monospace; font-size:12px; color:{CORES['fraco']};
                margin:18px 0 8px; text-transform:uppercase; letter-spacing:.05em; }}

  .cards-row {{ display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin-bottom:10px; }}
  .cards-row-3 {{ grid-template-columns:repeat(3,1fr); }}
  .card {{ background:{CORES['fundo']}; border:1px solid {CORES['borda']}; border-radius:8px;
           padding:10px 12px; text-align:center; }}
  .card-label {{ font-family:'JetBrains Mono',monospace; font-size:10px; color:{CORES['fraco']};
                 text-transform:uppercase; margin-bottom:6px; }}
  .card-value {{ font-family:'JetBrains Mono',monospace; font-size:16px; font-weight:600; }}

  .boxes-row {{ display:flex; flex-wrap:wrap; gap:8px; margin-bottom:8px; }}
  .box {{ border:1px solid {CORES['borda']}; border-radius:8px; padding:8px 14px; flex:1 1 150px;
          font-family:'JetBrains Mono',monospace; font-size:13px; white-space:nowrap; }}
  .box-label {{ color:{CORES['fraco']}; }}
  .box-value {{ color:{CORES['texto']}; font-weight:700; }}

  .tabela {{ width:100%; border-collapse:collapse; font-family:'JetBrains Mono',monospace; font-size:12px; margin-bottom:6px; }}
  .tabela th {{ text-align:left; color:{CORES['fraco']}; font-weight:500; padding:6px 8px;
                border-bottom:1px solid {CORES['borda']}; text-transform:uppercase; font-size:10px; }}
  .tabela td {{ padding:6px 8px; border-bottom:1px solid {CORES['borda']}; }}

  .disclaimer {{ margin-top:14px; font-size:11px; color:{CORES['fraco']}; line-height:1.5; }}
  .rodape {{ margin-top:18px; font-size:11px; color:{CORES['fraco']}; text-align:center; }}
</style></head>
<body>
  <div class="container">
    {painel_esq}
    {painel_dir}
  </div>
  <div class="rodape">Dashboard gerado a partir de CSVs locais (dados sintéticos de exemplo) · {pd.Timestamp.now():%d/%m/%Y %H:%M}</div>
</body></html>"""

    with open(saida, "w", encoding="utf-8") as f:
        f.write(html)