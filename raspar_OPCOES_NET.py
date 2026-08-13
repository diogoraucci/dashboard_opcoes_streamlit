# ============================================================
# COLETAR HISTÓRICO SELIC - BANCO CENTRAL
# ============================================================
def selic():
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    
    import pandas as pd
    from bs4 import BeautifulSoup
    import time
    
    # ============================================================
    # SELENIUM
    # ============================================================
    url = "https://www.bcb.gov.br/controleinflacao/historicotaxasjuros"
    
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(options=options)
    driver.get(url)
    time.sleep(5)
    
    # captura HTML puro
    html = driver.find_element(
        By.ID,
        "historicotaxasjuros"
    ).get_attribute("outerHTML")
    
    driver.quit()
    
    # ============================================================
    # HTML -> TEXTO DA TABELA
    # ============================================================
    soup = BeautifulSoup(html, "html.parser")
    linhas = []
    
    for tr in soup.find("tbody").find_all("tr"):
        
        colunas = [
            td.get_text(strip=True)
            for td in tr.find_all("td")
        ]
        
        linhas.append(colunas)
    
    
    # dataframe manual
    df_selic = pd.DataFrame(
        linhas,
        columns=[
            "Reuniao",
            "Data",
            "Vies",
            "Periodo_Vigencia",
            "Meta_Selic",
            "TBAN",
            "Selic_Percentual",
            "Selic_aa"
        ]
    )
    
    
    # ============================================================
    # LIMPEZA
    # ============================================================
    
    df_selic["Data"] = pd.to_datetime(
        df_selic["Data"],
        format="%d/%m/%Y"
    )
    
    
    # conversão brasileira correta
    def converte_numero(valor):
    
        if valor in ["", "n/a", None]:
            return None
    
        return float(
            valor.replace(",", ".")
        )
    
    
    for col in [
        "Meta_Selic",
        "TBAN",
        "Selic_Percentual",
        "Selic_aa"
    ]:
    
        df_selic[col] = df_selic[col].apply(
            converte_numero
        )
    
    # ============================================================
    # FORMATAR EXIBIÇÃO COM 2 CASAS DECIMAIS
    # ============================================================
    
    colunas_numericas = [
        "Meta_Selic",
        "TBAN",
        "Selic_Percentual",
        "Selic_aa"
    ]
    
    for col in colunas_numericas:
        df_selic[col] = df_selic[col].map(
            lambda x: f"{x:.2f}" if pd.notna(x) else None
        )
    
    
    df_selic.head()
    # Exibir Tabela
    df_selic.head()
    
    tx_selic = df_selic['Meta_Selic'][0]
    #print(f'{tx_selic}%')

    return tx_selic, df_selic


# =============================
# Coletar Opcoes Net
# =============================
def opcoes_net():
    import time
    from bs4 import BeautifulSoup
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait
    
    # ============================================================
    # CONFIGURAÇÕES
    # ============================================================
    CPF_USUARIO = "350.422.188-74"
    SENHA_USUARIO = "logoi777"
    acao = "PETR4"
    
    # ============================================================
    # CONFIGURA CHROME
    # ============================================================
    options = uc.ChromeOptions()
    
    # Mantém browser ativo, mas fora da tela
    options.add_argument("--window-position=-2000,0") # remover esse para visualizar browser
    options.add_argument("--window-size=1920,1080")
    
    # Evita congelamento em segundo plano
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-renderer-backgrounding")
    
    driver = uc.Chrome(options=options, version_main=150)
    
    driver.set_page_load_timeout(60)
    wait = WebDriverWait(driver, 20)
    
    # ============================================================
    # LOGIN
    # ============================================================
    try:
        print("1. Acessando página de ações...")
        driver.get("https://opcoes.net.br/acoes")
    
        # --------------------------------------------------------
        # CLICAR LOGIN
        # --------------------------------------------------------
        while True:
            try:
                botao = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'a.btn.btn-primary[href*="/login"]')))
                driver.execute_script("arguments[0].click();", botao)
    
                wait.until(lambda d: "/login" in d.current_url)
                break
    
            except Exception as e:
                print("Esperando botão login...", e)
                time.sleep(2)
    
        # --------------------------------------------------------
        # CPF
        # --------------------------------------------------------
        print("2. Informando CPF...")
    
        campo_cpf = wait.until(EC.visibility_of_element_located((By.ID, "CPF")))
        campo_cpf.clear()
        campo_cpf.send_keys(CPF_USUARIO)
    
        # --------------------------------------------------------
        # SENHA
        # --------------------------------------------------------
        print("3. Informando senha...")
    
        campo_senha = wait.until(EC.visibility_of_element_located((By.ID, "Password")))
        campo_senha.clear()
        campo_senha.send_keys(SENHA_USUARIO)
    
        # --------------------------------------------------------
        # BOTÃO ENTRAR
        # --------------------------------------------------------
        print("4. Efetuando login...")
    
        botao_entrar = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn.btn-default[type='submit']")))
        driver.execute_script("arguments[0].click();", botao_entrar)
        time.sleep(6)
    
        # --------------------------------------------------------
        # IR PARA AÇÕES
        # --------------------------------------------------------
        if "/acoes" not in driver.current_url:
    
            print("Redirecionando para ações...")
            driver.get("https://opcoes.net.br/acoes")
    
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr")))
        time.sleep(3)
    
        # --------------------------------------------------------
        # FECHAR POPUP
        # --------------------------------------------------------
        try:
    
            botao_modal = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(),'Continuar com dados de fechamento')]")))
            driver.execute_script( "arguments[0].click();", botao_modal)
    
        except Exception:
            pass
    
    except Exception as e:
    
        print("Erro no login:", e)
    
    
    # ===========================================================
    # ABRIR ATIVO
    # ===========================================================
    print(f"Buscando ativo {acao}")
    
    while True:
        try:
            xpath_acao = (f"//table//tbody//td"
                f"[normalize-space(text())='{acao}']")
    
    
            elemento_acao = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, xpath_acao)))
    
            driver.execute_script(
                "arguments[0].click();", elemento_acao)
    
            print(            "Ativo aberto com sucesso:", acao)
            break
    
        except Exception as e:
            print(            "Aguardando ativo...", e)
            time.sleep(2)
    
    print("Página carregada com sucesso")

    # ======================================
    # COlETAR TABELA 
    # ======================================

    from selenium.webdriver.common.by import By
    
    # Captura o texto do elemento localizado pelo XPath
    elemento = driver.find_element(By.XPATH, "/html/body/div[1]/div[1]/div[1]")
    dados = elemento.text
    
    #print(dados)
    
    import pandas as pd
    import re
    
    # Definição das colunas
    colunas = [
        "Ativo", "Var. %", "Últ.", "Data",
        "CALLs_IV_Rank", "CALLs_Perc", "CALLs_Vol_Impl",
        "Diff_Vol",
        "PUTs_IV_Rank", "PUTs_Perc", "PUTs_Vol_Impl",
        "HV_Rank", "Perc_Hist", "Vol_Hist",
        "Volume_Financeiro"
    ]
    
    linhas_processadas = []
    
    # Expressão regular ajustada para pegar apenas tickers válidos da B3 (ex: YDUQ3, WEGE3, TAEE11)
    patrao_ativo = re.compile(r'^[A-Z]{4}\d{1,2}\b')
    
    for linha in dados.split('\n'):
        linha = linha.strip()
        partes = linha.split()
        
        # Valida se a linha começa com um ticker E se possui no mínimo 5 elementos
        if partes and patrao_ativo.match(partes[0]) and len(partes) >= 5:
            if len(partes) == 15:
                linhas_processadas.append(partes)
            else:
                # Captura segura dos elementos fixos
                ativo, var, ult, data = partes[0], partes[1], partes[2], partes[3]
                volume = partes[-1]
                meio = partes[4:-1]
                
                # Preenche o meio com None para manter o alinhamento correto em 15 colunas
                meio_com_nulos = meio + [None] * (10 - len(meio))
                linhas_processadas.append([ativo, var, ult, data] + meio_com_nulos + [volume])
    
    # Criando o DataFrame
    df_acoes = pd.DataFrame(linhas_processadas, columns=colunas)
    
    df_ativos_b3_ticker = df_acoes['Ativo'].to_list()
    #display(df_ativos_b3_ticker)
    display(df_acoes)

    # ==============================================================
    # MUDAR PAGINA PARA #https://opcoes.net.br/opcoes/bovespa/{acao}
    driver.get(f"https://opcoes.net.br/opcoes/bovespa/{acao}")

    # CRIAR AQUI LOOPING FOR PARA COLETAR TODAS AS CÇÕES >>>>--------------->
    # ==============================================================
    
    # CLICAR EM TODOS OS VENCIMENTOS DE OPÇOES ===========================
    time.sleep(10)
    from selenium.webdriver.common.by import By
    import time
    
    checkboxes = driver.find_elements(
        By.XPATH,
        "//input[@type='checkbox']"
    )
    
    print(f"{len(checkboxes)} checkboxes encontrados.")
    
    for i, cb in enumerate(checkboxes, start=1):
        try:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", cb)
            time.sleep(0.1)
    
            if not cb.is_selected():
                driver.execute_script("arguments[0].click();", cb)
    
            print(f"{i} - {cb.get_attribute('value')} marcado.")
    
        except Exception as e:
            print(f"Erro no checkbox {i}: {e}")
    
    #####################################################################
    # Abrir Todo o Range de Strikes
    # Executa JavaScript no slider
    script = """
    var slider = $("#strike-range");
    
    var min = slider.slider("option", "min");
    var max = slider.slider("option", "max");
    
    slider.slider("values", [min, max]);
    
    slider.slider("option", "slide").call(
        slider,
        null,
        {
            values: [min, max]
        }
    );
    
    slider.trigger("slidechange");
    """
    
    driver.execute_script(script)
    time.sleep(10)

    # ================================
    # COLETAR TABELA =================
    # ================================

    from bs4 import BeautifulSoup
    import pandas as pd
    
    # UMA chamada só pro Selenium
    html = driver.find_element(By.ID, "tblListaOpc").get_attribute("outerHTML")
    
    soup = BeautifulSoup(html, "lxml")  # ou "html.parser" se não tiver lxml
    
    # Headers (primeira linha do thead)
    headers = [th.get_text(strip=True) for th in soup.select("thead tr:first-child th")]
    
    # Linhas do tbody
    dados = []
    for tr in soup.select("tbody tr"):
        celulas = [td.get_text(strip=True) for td in tr.find_all("td")]
        if celulas:  # ignora linhas vazias
            dados.append(celulas)
    
    df_tabela = pd.DataFrame(dados, columns=headers)

    # reduzir tabela
    df_tabela.loc[:, :'Vega']
    # Remover Colunas
    df_tabela = df_tabela.drop(columns=["F.M."])

    # Exibir Primeira coleta
    #display(df_tabela)
    # =======================================================
    # FORMATAR TABELA
    # =======================================================

    '''colunas_final = (
        list(df_tabela.columns[:2]) +
        list(df_tabela.columns[[3]]) +
        list(df_tabela.columns[6:7]) +
        list(df_tabela.columns[8:11]) +
        list(df_tabela.columns[12:20])
    )'''
    
    colunas_final = ['Ticker', 'Tipo', 'Dias úteis','Mod.', 'Strike', 'A/I/OTM', 'Dist. (%) do Strike', 'Último', 'Var.\xa0(%)', 'Núm. de Neg.',
                     'Vol. Financeiro', 'Vol. Impl. (%)', 'Delta', 'Gamma', 'Theta ($)', 'Theta (%)', 'Vega']
       
    # Colunas que serão convertidas
    '''colunas_converter = (
        list(df_tabela.columns[2:3]) +
        list(df_tabela.columns[6:7]) +
        list(df_tabela.columns[8:11]) +
        list(df_tabela.columns[12:])
    )'''

    colunas_converter = ['Strike',  'Dist. (%) do Strike', 'Último', 'Var.\xa0(%)', 'Núm. de Neg.',
                     'Vol. Financeiro', 'Vol. Impl. (%)', 'Delta', 'Gamma', 'Theta ($)', 'Theta (%)', 'Vega']

    # Converter tipos
    df_tabela[colunas_converter] = (
        df_tabela[colunas_converter]
        .apply(
            lambda col: (
                col.astype(str)
                .str.replace(r'\.(?=\d{3}(?:,|$))', '', regex=True)
                .str.replace(',', '.', regex=False)
                .str.replace('%', '', regex=False)
                .str.strip()
                .replace({'': None, '-': None, 'nan': None})
            )
        )
        .apply(pd.to_numeric, errors='coerce')
    )
    
    # Definir Tabela
    df_tabela = df_tabela[colunas_final]
    
    # Exibir as colunas desejadas no final
    display(df_tabela)
    
    # Conferir tipos somente delas
    df_tabela.dtypes
    driver.quit()

    return df_tabela, df_acoes

# =========================================
# COLETAR CARTEIRAS B3
# =========================================


def carteiras_b3():
    # =========================================
    # COLETAR IDIV B3
    # =========================================
    import time
    from bs4 import BeautifulSoup
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import Select
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait
    
    from io import StringIO
    import pandas as pd

    url = 'https://sistemaswebb3-listados.b3.com.br/indexPage/day/IDIV?language=pt-br'
    
    options = uc.ChromeOptions()
    driver = uc.Chrome(options=options, version_main=150)
    wait = WebDriverWait(driver, 5)
    
    loop = 0
    while loop == 0:
        try:
            
            # 1. Acessa a página inicial
            print("1. Acessando a página Carteira IDIV...")
            driver.get(url)
            
            # Verificar Iframes
            iframes = driver.find_elements(
                By.TAG_NAME,
                "iframe"
            )
            
            print("Quantidade de iframes:", len(iframes))
            
            for i, iframe in enumerate(iframes):
                print(i, iframe.get_attribute("src"))
            
            # Clicar em Exibir 120 Empresas
            driver.find_element(
                By.XPATH,
                '//*[@id="selectPage"]/option[4]'
            ).click()
            
            time.sleep(5)
            
            # Coletar Tabela
            xpath_tabela = "/html/body/app-root/app-day-portfolio/div/div/div[1]/form/div[2]/div/table"
            
            # aguardar tabela
            tabela = WebDriverWait(driver,20).until(
                EC.presence_of_element_located(
                    (By.XPATH, xpath_tabela)
                )
            )
            
            # HTML da tabela renderizada pelo Angular
            html_tabela = tabela.get_attribute("outerHTML")
            
            # converter para dataframe
            df = pd.read_html(
                StringIO(html_tabela))[0]
            
            df_IDIV = df.iloc[:-2]
            display(df_IDIV)
        
            # ===================================
            # COLETAR CARTERA IBSD
            # ===================================
            url = 'https://sistemaswebb3-listados.b3.com.br/indexPage/day/IBSD?language=pt-br'
            
            '''options = uc.ChromeOptions()
            driver = uc.Chrome(options=options, version_main=150)
            wait = WebDriverWait(driver, 5)'''
            
            # 1. Acessa a página inicial
            print("1. Acessando a página Carteira IBSD...")
            driver.get(url)
            
            # Verificar Iframes
            iframes = driver.find_elements(
                By.TAG_NAME,
                "iframe"
            )
            
            print("Quantidade de iframes:", len(iframes))
            
            for i, iframe in enumerate(iframes):
                print(i, iframe.get_attribute("src"))
            
            # Clicar em Exibir 120 Empresas
            driver.find_element(
                By.XPATH,
                '//*[@id="selectPage"]/option[4]'
            ).click()
            
            time.sleep(5)
            
            # Coletar Tabela
            xpath_tabela = "/html/body/app-root/app-day-portfolio/div/div/div[1]/form/div[2]/div/table"
            
            # aguardar tabela
            tabela = WebDriverWait(driver,20).until(
                EC.presence_of_element_located(
                    (By.XPATH, xpath_tabela)
                )
            )
            
            # HTML da tabela renderizada pelo Angular
            html_tabela = tabela.get_attribute("outerHTML")
            
            # converter para dataframe
            df = pd.read_html(
                StringIO(html_tabela))[0]
            
            df_IBSD = df.iloc[:-2]
            display(df_IBSD) 
        
            # ===================================
            # COLETAR CARTERA IBOV
            # ===================================
            url = 'https://sistemaswebb3-listados.b3.com.br/indexPage/day/IBOV?language=pt-br'
            
            '''options = uc.ChromeOptions()
            driver = uc.Chrome(options=options, version_main=150)
            wait = WebDriverWait(driver, 5)'''
            
            # 1. Acessa a página inicial
            print("1. Acessando a página Carteira IBOV...")
            driver.get(url)
            
            # Verificar Iframes
            iframes = driver.find_elements(
                By.TAG_NAME,
                "iframe"
            )
            
            print("Quantidade de iframes:", len(iframes))
            
            for i, iframe in enumerate(iframes):
                print(i, iframe.get_attribute("src"))
            
            time.sleep(5)
            # Clicar em Exibir 120 Empresas
            driver.find_element(
                By.XPATH,
                '//*[@id="selectPage"]/option[4]'
            ).click()
            
            time.sleep(5)
            
            # Coletar Tabela
            xpath_tabela = "/html/body/app-root/app-day-portfolio/div/div/div[1]/form/div[2]/div/table"
            
            # aguardar tabela
            tabela = WebDriverWait(driver,20).until(
                EC.presence_of_element_located(
                    (By.XPATH, xpath_tabela)
                )
            )
            
            # HTML da tabela renderizada pelo Angular
            html_tabela = tabela.get_attribute("outerHTML")
            
            # converter para dataframe
            df = pd.read_html(
                StringIO(html_tabela))[0]
            
            df_IBOV = df.iloc[:-2]
            display(df_IBOV) 
                   
    
            loop = 1
            driver.quit()
                    
        except:
            clear_output()
            print('Falha na Coleta.')
    
    return df_IBOV, df_IBSD, df_IDIV

# =========================================
# COLETAR FUNDAMENTUS.COM.BR
# =========================================
def fundamentos():
    # EMPRESAS TICKERS E RAZÃO SOCIAL
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from io import StringIO
    import pandas as pd
    import numpy as np
    import time
    
    driver = webdriver.Chrome()
    url = "https://www.fundamentus.com.br/detalhes.php?papel="
    driver.get(url)
    
    # Coletar Tabela
    html_tabela = driver.find_element(
        By.TAG_NAME,
        "table"
    ).get_attribute("outerHTML")
    
    df_empresas = pd.read_html(StringIO(html_tabela))[0]
    
    display(df_empresas)

    # ======================================
    # Coletar Indicadores Funcamentalistas
    # ======================================
    url = "https://www.fundamentus.com.br/resultado.php"
    driver.get(url)
    time.sleep(5)
    
    tabela = driver.find_element(By.TAG_NAME, "table")
    html = tabela.get_attribute("outerHTML")
    df_fundamentos = pd.read_html(StringIO(html))[0]
    
    driver.quit()
    # ============================================================
    # Conversão Fundamentus -> FLOAT
    # ============================================================
    def converter_float(valor):
        if pd.isna(valor):
            return np.nan
    
        valor = str(valor).strip()
    
        if valor == "":
            return np.nan
    
        # remove %
        valor = valor.replace("%", "")
    
        # remove separador de milhar brasileiro
        valor = valor.replace(".", "")
    
        # troca decimal brasileiro
        valor = valor.replace(",", ".")
    
        try:
            return float(valor)
    
        except:
            return np.nan
            
    # ============================================================
    # Converter colunas numéricas
    # ============================================================
    for col in df_fundamentos.columns:
        if col != "Papel":
            df_fundamentos[col] = df_fundamentos[col].apply(converter_float)
    
    # ============================================================
    # Garantir float no Patrimônio Líquido
    # ============================================================
    df_fundamentos["Patrim. Líq"] = df_fundamentos["Patrim. Líq"].astype(float)
    
    # ============================================================
    # Remover notação científica SEM FORMATAR COM VÍRGULA
    # ============================================================
    pd.set_option(
        "display.float_format",
        lambda x: f"{x:.1f}"
    )

    # Unir DataFrames
    # ============================================================
    # Incluir Nome Comercial e Razão Social no dataframe df
    # ============================================================
    df_uniao = df_fundamentos.merge(
        df_empresas[
            [
                "Papel",
                "Nome Comercial",
                "Razão Social"
            ]
        ],
        on="Papel",
        how="left"
    )
    
    # ============================================================
    # Renomear colunas
    # ============================================================
    df_uniao = df_uniao.rename(
        columns={
            "Papel": "Ticker",
            "Nome Comercial": "Nome_Comercial",
            "Razão Social": "Razão_Social",
            "Patrim. Líq": "Patrim_Liq"})
    
    # ============================================================
    # Visualizar resultado
    # ============================================================
    #display(df_uniao)

    # Remover Empresas com Valores Zerados
    # Colunas que não podem ser zero
    colunas_filtro = [
        "P/L",
        "P/VP",
        "PSR",
        "Div.Yield",
        "P/Ativo",
        "P/Cap.Giro",
        "P/EBIT",
        "P/Ativ Circ.Liq"
    ]
    
    
    # Remove linhas onde qualquer coluna da lista é igual a zero
    df_uniao = df_uniao[
        ~(df_uniao[colunas_filtro] == 0).any(axis=1)
    ].copy()
    
    # Resetar índice
    
    df_uniao.sort_values('Patrim_Liq', ascending=False, inplace=True)
    df_uniao.reset_index(drop=True, inplace=True)
    display(df_uniao)

    return df_uniao
    
# =============================================
# OHLC
# ==============================================
import MetaTrader5 as mt5
def cotacoes_mt5_OHLC(
    ticker,
    timeframe=mt5.TIMEFRAME_D1,
    n_barras=1000):


    import pandas as pd
    from IPython.display import clear_output
    import time

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

    #mt5.shutdown()

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

    return df.iloc[:,:5]

# COLETA METATRADER
def cotacoes_mt5_lista(
    tickers,
    timeframe=mt5.TIMEFRAME_D1,
    n_barras=1):
    
    """
    Coleta último preço de uma lista de ativos no MetaTrader 5.

    Retorna:
    
        Ticker      Último
        PETRG340    1.25
        PETRH350    0.80
        VALEA100    2.10
    """

    if not mt5.initialize():
        raise RuntimeError(f"Erro ao conectar no MT5:\n{mt5.last_error()}")
    resultados = []

    for ticker in tickers:

        try:
            # Habilita o ativo no MT5
            if not mt5.symbol_select(ticker, True):
                #print(f"Ticker não encontrado: {ticker}")
                resultados.append({"Ticker": ticker, "Último": 0})
                continue


            rates = mt5.copy_rates_from_pos(ticker, timeframe, 0, n_barras)


            if rates is not None and len(rates) > 0:
                df = pd.DataFrame(rates)
                ultimo = df["close"].iloc[-1]

            else:
                ultimo = 0
            resultados.append({"Ticker": ticker, "Último": ultimo})

        except Exception as e:
            print(f"Erro {ticker}: {e}")
            resultados.append({"Ticker": ticker, "Último": 0})

    df_cotacoes = pd.DataFrame(resultados)

    return df_cotacoes

# =================================
# LOOPING FOR OPÇOES NET 
# =================================
def loop_opcoes_net():
    
    import time
    from bs4 import BeautifulSoup
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait
    from IPython.display import clear_output
    # ============================================================
    # CONFIGURAÇÕES
    # ============================================================
    CPF_USUARIO = "350.422.188-74"
    SENHA_USUARIO = "logoi777"
    acao = "PETR4"
    
    # ============================================================
    # CONFIGURA CHROME
    # ============================================================
    options = uc.ChromeOptions()
    
    # Mantém browser ativo, mas fora da tela
    #options.add_argument("--window-position=-2000,0") # remover esse para visualizar browser
    options.add_argument("--window-size=1920,1080")
    
    # Evita congelamento em segundo plano
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-renderer-backgrounding")
    
    driver = uc.Chrome(options=options, version_main=150)
    
    driver.set_page_load_timeout(60)
    wait = WebDriverWait(driver, 20)
    
    # ============================================================
    # LOGIN
    # ============================================================
    try:
        print("1. Acessando página de ações...")
        driver.get("https://opcoes.net.br/acoes")
    
        # --------------------------------------------------------
        # CLICAR LOGIN
        # --------------------------------------------------------
        while True:
            try:
                botao = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'a.btn.btn-primary[href*="/login"]')))
                driver.execute_script("arguments[0].click();", botao)
    
                wait.until(lambda d: "/login" in d.current_url)
                break
    
            except Exception as e:
                print("Esperando botão login...", e)
                time.sleep(2)
    
        # --------------------------------------------------------
        # CPF
        # --------------------------------------------------------
        print("2. Informando CPF...")
    
        campo_cpf = wait.until(EC.visibility_of_element_located((By.ID, "CPF")))
        campo_cpf.clear()
        campo_cpf.send_keys(CPF_USUARIO)
    
        # --------------------------------------------------------
        # SENHA
        # --------------------------------------------------------
        print("3. Informando senha...")
    
        campo_senha = wait.until(EC.visibility_of_element_located((By.ID, "Password")))
        campo_senha.clear()
        campo_senha.send_keys(SENHA_USUARIO)
    
        # --------------------------------------------------------
        # BOTÃO ENTRAR
        # --------------------------------------------------------
        print("4. Efetuando login...")
    
        botao_entrar = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn.btn-default[type='submit']")))
        driver.execute_script("arguments[0].click();", botao_entrar)
        time.sleep(6)
    
        # --------------------------------------------------------
        # IR PARA AÇÕES
        # --------------------------------------------------------
        if "/acoes" not in driver.current_url:
    
            print("Redirecionando para ações...")
            driver.get("https://opcoes.net.br/acoes")
    
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr")))
        time.sleep(3)
    
        # --------------------------------------------------------
        # FECHAR POPUP
        # --------------------------------------------------------
        try:
    
            botao_modal = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(),'Continuar com dados de fechamento')]")))
            driver.execute_script( "arguments[0].click();", botao_modal)
    
        except Exception:
            pass
    
    except Exception as e:
    
        print("Erro no login:", e)
    
    # ===========================================================
    # ABRIR ATIVO
    # ===========================================================
    print(f"Buscando ativo {acao}")
    
    while True:
        try:
            xpath_acao = (f"//table//tbody//td"
                f"[normalize-space(text())='{acao}']")
    
    
            elemento_acao = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, xpath_acao)))
    
            driver.execute_script(
                "arguments[0].click();", elemento_acao)
    
            print(            "Ativo aberto com sucesso:", acao)
            break
    
        except Exception as e:
            print(            "Aguardando ativo...", e)
            time.sleep(2)
    
    print("Página carregada com sucesso")
    
    # ======================================
    # COlETAR TABELA 
    # ======================================
    
    from selenium.webdriver.common.by import By
    
    # Captura o texto do elemento localizado pelo XPath
    elemento = driver.find_element(By.XPATH, "/html/body/div[1]/div[1]/div[1]")
    dados = elemento.text
    
    #print(dados)
    
    import pandas as pd
    import re
    
    # Definição das colunas
    colunas = [
        "Ativo", "Var. %", "Últ.", "Data",
        "CALLs_IV_Rank", "CALLs_Perc", "CALLs_Vol_Impl",
        "Diff_Vol",
        "PUTs_IV_Rank", "PUTs_Perc", "PUTs_Vol_Impl",
        "HV_Rank", "Perc_Hist", "Vol_Hist",
        "Volume_Financeiro"
    ]
    
    linhas_processadas = []
    
    # Expressão regular ajustada para pegar apenas tickers válidos da B3 (ex: YDUQ3, WEGE3, TAEE11)
    patrao_ativo = re.compile(r'^[A-Z]{4}\d{1,2}\b')
    
    for linha in dados.split('\n'):
        linha = linha.strip()
        partes = linha.split()
        
        # Valida se a linha começa com um ticker E se possui no mínimo 5 elementos
        if partes and patrao_ativo.match(partes[0]) and len(partes) >= 5:
            if len(partes) == 15:
                linhas_processadas.append(partes)
            else:
                # Captura segura dos elementos fixos
                ativo, var, ult, data = partes[0], partes[1], partes[2], partes[3]
                volume = partes[-1]
                meio = partes[4:-1]
                
                # Preenche o meio com None para manter o alinhamento correto em 15 colunas
                meio_com_nulos = meio + [None] * (10 - len(meio))
                linhas_processadas.append([ativo, var, ult, data] + meio_com_nulos + [volume])
    
    # Criando o DataFrame
    df_acoes = pd.DataFrame(linhas_processadas, columns=colunas)

    arquivo = "CotacoesAcoesOpcoes/df_tabela.xlsx"
    with pd.ExcelWriter(arquivo, engine="openpyxl") as writer:
        df_acoes.to_excel(writer, sheet_name="Tabela", index=True)
    
    #df_ativos_b3_ticker = df_acoes['Ativo'].to_list()
    #display(df_ativos_b3_ticker)
    display(df_acoes)
    
    # ==============================================================
    # LOOPING DE COLETA
    # ==============================================================
    
    # Selecionar Códigos Das Ações
    df_tickers_acoes = df_acoes['Ativo'].to_list()
    
    # Selecionar Codigos Opçoes
    #df_tickers_opcoes = []
    
    # Loping For ==============================
    for acao in df_tickers_acoes:
    # =========================================
        
        # MUDAR PAGINA PARA #https://opcoes.net.br/opcoes/bovespa/{acao}
        driver.get(f"https://opcoes.net.br/opcoes/bovespa/{acao}")
        # CRIAR AQUI LOOPING FOR PARA COLETAR TODAS AS CÇÕES >>>>--------------->
    
        # CLICAR EM TODOS OS VENCIMENTOS DE OPÇOES ===========================
        time.sleep(10)
        from selenium.webdriver.common.by import By
        import time
        
        checkboxes = driver.find_elements(
            By.XPATH,
            "//input[@type='checkbox']"
        )
        
        print(f"{len(checkboxes)} checkboxes encontrados.")
        
        for i, cb in enumerate(checkboxes, start=1):
            try:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", cb)
                time.sleep(0.1)
        
                if not cb.is_selected():
                    driver.execute_script("arguments[0].click();", cb)
        
                print(f"{i} - {cb.get_attribute('value')} marcado.")
        
            except Exception as e:
                print(f"Erro no checkbox {i}: {e}")
        
        #####################################################################
        # Abrir Todo o Range de Strikes
        # Executa JavaScript no slider
        script = """
        var slider = $("#strike-range");
        
        var min = slider.slider("option", "min");
        var max = slider.slider("option", "max");
        
        slider.slider("values", [min, max]);
        
        slider.slider("option", "slide").call(
            slider,
            null,
            {
                values: [min, max]
            }
        );
        
        slider.trigger("slidechange");
        """
        
        driver.execute_script(script)
        time.sleep(10)
        
        # ================================
        # COLETAR TABELA =================
        # ================================
        
        from bs4 import BeautifulSoup
        import pandas as pd
        
        # UMA chamada só pro Selenium
        html = driver.find_element(By.ID, "tblListaOpc").get_attribute("outerHTML")
        
        soup = BeautifulSoup(html, "lxml")  # ou "html.parser" se não tiver lxml
        
        # Headers (primeira linha do thead)
        headers = [th.get_text(strip=True) for th in soup.select("thead tr:first-child th")]
        
        # Linhas do tbody
        dados = []
        for tr in soup.select("tbody tr"):
            celulas = [td.get_text(strip=True) for td in tr.find_all("td")]
            if celulas:  # ignora linhas vazias
                dados.append(celulas)
    
        # Criar Tabela
        df_tabela = pd.DataFrame(dados, columns=headers)
        
        # reduzir tabela
        df_tabela = df_tabela.loc[:, :'Vega']
        # Remover Colunas
        #df_tabela = df_tabela.drop(columns=["F.M."])
        
        # Exibir Primeira coleta
        #display(df_tabela)
        # =======================================================
        # FORMATAR TABELA
        # =======================================================
        
        '''colunas_final = (
            list(df_tabela.columns[:2]) +
            list(df_tabela.columns[[3]]) +
            list(df_tabela.columns[6:7]) +
            list(df_tabela.columns[8:11]) +
            list(df_tabela.columns[12:20])
        )'''
        
        colunas_final = ['Ticker', 'Tipo', 'F.M.','Dias úteis','Mod.', 'Strike', 'A/I/OTM', 'Dist. (%) do Strike', 'Último', 'Var.\xa0(%)', 'Núm. de Neg.',
                         'Vol. Financeiro', 'Vol. Impl. (%)', 'Delta', 'Gamma', 'Theta ($)', 'Theta (%)', 'Vega']
           
        # Colunas que serão convertidas
        '''colunas_converter = (
            list(df_tabela.columns[2:3]) +
            list(df_tabela.columns[6:7]) +
            list(df_tabela.columns[8:11]) +
            list(df_tabela.columns[12:])
        )'''
        
        colunas_converter = ['Strike',  'Dist. (%) do Strike', 'Último', 'Var.\xa0(%)', 'Núm. de Neg.',
                         'Vol. Financeiro', 'Vol. Impl. (%)', 'Delta', 'Gamma', 'Theta ($)', 'Theta (%)', 'Vega']
        
        # Converter tipos
        df_tabela[colunas_converter] = (
            df_tabela[colunas_converter]
            .apply(
                lambda col: (
                    col.astype(str)
                    .str.replace(r'\.(?=\d{3}(?:,|$))', '', regex=True)
                    .str.replace(',', '.', regex=False)
                    .str.replace('%', '', regex=False)
                    .str.strip()
                    .replace({'': None, '-': None, 'nan': None})
                )
            )
            .apply(pd.to_numeric, errors='coerce')
        )
        
        # Definir Tabela
        df_tabela = df_tabela[colunas_final]
    
        # Altera Index
        df_tabela.index = [acao] * len(df_tabela)
        # Renomear Index
        df_tabela.index.name = acao

        # Exibir as colunas desejadas no final
        display(df_tabela)
        
        # Conferir tipos somente delas
        #df_tabela.dtypes
    
        # Salvar Arquivo Excel ==========================================
        arquivo = f"CotacoesAcoesOpcoes/df_OpcoesAcoes_Cotacoes_{acao}.xlsx"
        with pd.ExcelWriter(arquivo, engine="openpyxl") as writer:
            df_tabela.to_excel(writer, sheet_name="opcoes", index=True)
            
            clear_output()
            print(f"Arquivo salvo: {acao}")

        # Unir Tickers Opções
       # df_tickers_opcoes.extend(df_tabela['Ticker'].to_list())
        
    driver.quit()

import MetaTrader5 as mt5
def cotacoes_acoes_opcoes():
    # Coletar Tickers =================================================================================
    import pandas as pd
    import MetaTrader5 as mt5
    df_tickers_acoes = pd.read_excel("CotacoesAcoesOpcoes/df_tabela.xlsx",  index_col=0)
    df_tickers_acoes = df_tickers_acoes['Ativo'].to_list()
    
    # =================================================
    # LOOP DE COLETA DE COTACOES DE AÇÕES META TRADE 5
    # ===============================================
    for acao in df_tickers_acoes:
        print(acao, f'0=== COLETAR COTAÇÕES DE AÇÃO e OPÇÃO de {acao} =====0')
        
        # Abrir Arquivo Excel
        arquivo = f"CotacoesAcoesOpcoes/df_OpcoesAcoes_Cotacoes_{acao}.xlsx"
    
        # Lê a aba existente
        df_opcoes = pd.read_excel(arquivo, sheet_name="opcoes", index_col=0)
        # Coletar Tickers Opções
        df_tickers_opcoes = df_opcoes['Ticker'].to_list()
        
        # Coleta as cotações
        cotacoes = cotacoes_mt5_OHLC(acao, timeframe=mt5.TIMEFRAME_D1, n_barras=1000)
    
        # Salva em uma nova aba =======================================================================
        with pd.ExcelWriter(arquivo, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
            cotacoes.to_excel(writer, sheet_name=f"cotacoes_{acao}", index=True)
    
    # ==================================================
    # LOOP DE COLETA DE COTACOES DE OPÇOES META TRADE 5
    # ================================================
        #for acao in df_tickers_opcoes:
    
        # Definir Nome Do Arquivo
        #arquivo = f"CotacoesAcoesOpcoes/df_OpcoesAcoes_Cotacoes_{'ASAI3'}.xlsx"
        
        # Ler a aba Opções
        #df_opcoes = pd.read_excel(arquivo, sheet_name="opcoes", index_col=0)
        # Coletar Tickers De Opções
        #tickers_opcoes = df_opcoes['Ticker'].to_list()
        
        df_cotacoes_opcoes = cotacoes_mt5_lista(df_tickers_opcoes, timeframe=mt5.TIMEFRAME_D1, n_barras=1)
        
        # Atualizar Último somente quando o Ticker for igual
        df_opcoes["Último"] = df_opcoes["Ticker"].map(
            df_cotacoes_opcoes.set_index("Ticker")["Último"])
        
        with pd.ExcelWriter(arquivo, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
            df_opcoes.to_excel(writer, sheet_name="opcoes", index=True)
   
    # Encerra Conexao e Fechar Programa
    import MetaTrader5 as mt5
    import subprocess
    # encerra conexão Python
    mt5.shutdown()
    
    # fecha o terminal MT5
    subprocess.run(["taskkill", "/F", "/IM", "terminal64.exe"])







# COLETA METATRADER ======================================================
def cotacoes_mt5_lista(
    tickers,
    timeframe=mt5.TIMEFRAME_D1,
    n_barras=1):
    import pandas as pd
    
    """
    Coleta último preço de uma lista de ativos no MetaTrader 5.

    Retorna:
    
        Ticker      Último
        PETRG340    1.25
        PETRH350    0.80
        VALEA100    2.10
    """

    if not mt5.initialize():
        raise RuntimeError(f"Erro ao conectar no MT5:\n{mt5.last_error()}")
    resultados = []

    for ticker in tickers:

        try:
            # Habilita o ativo no MT5
            if not mt5.symbol_select(ticker, True):
                #print(f"Ticker não encontrado: {ticker}")
                resultados.append({"Ticker": ticker, "Último": 0})
                continue


            rates = mt5.copy_rates_from_pos(ticker, timeframe, 0, n_barras)


            if rates is not None and len(rates) > 0:
                df = pd.DataFrame(rates)
                ultimo = df["close"].iloc[-1]

            else:
                ultimo = 0
            resultados.append({"Ticker": ticker, "Último": ultimo})

        except Exception as e:
            print(f"Erro {ticker}: {e}")
            resultados.append({"Ticker": ticker, "Último": 0})

    df_cotacoes = pd.DataFrame(resultados)

    '''# Apagar historico MT5
    import subprocess
    import time
    
    mt5.shutdown()
    import gc
    import time
    gc.collect()
    time.sleep(10)

    r = subprocess.run(
        ["taskkill", "/F", "/IM", "terminal64.exe"],
        capture_output=True,
        text=True
    )

    print(r.stdout)
    print(r.stderr)
    time.sleep(20)'''
    
    #apagar_historico_mt5()
    time.sleep(10)

    return df_cotacoes



def cotacoes_mt5_lista_2(tickers, timeframe=mt5.TIMEFRAME_D1, n_barras=100):
    import pandas as pd

    if not mt5.initialize():
        raise RuntimeError(f"Erro ao conectar no MT5:\n{mt5.last_error()}")

    resultados = []

    for ticker in tickers:
        try:
            if not mt5.symbol_select(ticker, True):
                print(f"Ticker não encontrado: {ticker}")
                continue

            rates = mt5.copy_rates_from_pos(ticker, timeframe, 0, n_barras)

            if rates is not None and len(rates) > 0:
                df = pd.DataFrame(rates)
                df["time"] = pd.to_datetime(df["time"], unit="s")
                df = df.set_index("time")
                df = df["close"].rename(ticker)
                
                resultados.append(df)

            else:
                print(f"Sem cotações para: {ticker}")

        except Exception as e:
            print(f"Erro {ticker}: {e}")

    if resultados:
        df_cotacoes = pd.concat(resultados, axis=1)
    else:
        df_cotacoes = pd.DataFrame()

    return df_cotacoes








    
import time
def apagar_historico_mt5():
    from pathlib import Path
    import shutil
    
    pasta = Path(r"C:\Users\Usuário\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\bases\XPMT5-DEMO\history")
    
    for item in pasta.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()
    
    print("Conteúdo removido com sucesso.")
    time.sleep(30)




def loog_classificacao_vol(tickers):
    import pandas as pd
    import numpy as np
    
    df_class_vol = pd.DataFrame()
    for i in tickers:
        df = cotacoes_mt5_OHLC(i, timeframe=mt5.TIMEFRAME_D1, n_barras=600)

        #df = cotacoes_yfinance(i, start_data)
        df['ticker'] = i
    
        # ============================================================
        # CONFIGURAÇÕES
        # ============================================================
        JANELA_VOL = 21
        JANELA_IV = 252
        DIAS_ANO = 252
    
        # ============================================================
        # 1. RETORNO LOGARÍTMICO
        # ============================================================
        df["Retorno_Log"] = np.log(df["Close"] / df["Close"].shift(1))
    
        # ============================================================
        # 2. VOLATILIDADE REALIZADA
        # ============================================================
        df["Vol_Realizada"] = df["Retorno_Log"].rolling(JANELA_VOL).std() * np.sqrt(DIAS_ANO) * 100
        df["Vol_20"] = df["Vol_Realizada"].quantile(0.20)
        df["Vol_80"] = df["Vol_Realizada"].quantile(0.80)
    
        # ============================================================
        # 3. RANK DA VOLATILIDADE
        # ============================================================
        vol_min = df["Vol_Realizada"].rolling(JANELA_IV).min()
        vol_max = df["Vol_Realizada"].rolling(JANELA_IV).max()
        denominador = vol_max - vol_min
    
        df["Vol_Rank"] = np.where(denominador != 0, ((df["Vol_Realizada"] - vol_min) / denominador) * 100, np.nan)
        df["Vol_Rank_20"] = df["Vol_Rank"].quantile(0.20)
        df["Vol_Rank_80"] = df["Vol_Rank"].quantile(0.80)
    
        # ============================================================
        # 4. PERCENTIL DA VOLATILIDADE
        # ============================================================
        df["Vol_Percentil"] = df["Vol_Realizada"].rolling(JANELA_IV).rank(pct=True) * 100
        df["Vol_Perc_20"] = df["Vol_Percentil"].quantile(0.20)
        df["Vol_Perc_80"] = df["Vol_Percentil"].quantile(0.80)
    
        # ============================================================
        # CLASSIFICAR VOLATILIDADE
        # ============================================================
        df["Vol_Hist"] = np.select([df["Vol_Realizada"] >= df["Vol_80"], df["Vol_Realizada"] <= df["Vol_20"]], ["Alta", "Baixa"], default="Neutra")
        df["Vol_Perc"] = np.select([df["Vol_Percentil"] >= df["Vol_Perc_80"], df["Vol_Percentil"] <= df["Vol_Perc_20"]], ["Alta", "Baixa"], default="Neutra")
        df["Vol_Rank"] = np.select([df["Vol_Rank"] >= df["Vol_Rank_80"], df["Vol_Rank"] <= df["Vol_Rank_20"]], ["Alta", "Baixa"], default="Neutra")
    
        # ============================================================
        # RESULTADO
        # ============================================================
        df = pd.DataFrame(df[['ticker', 'Vol_Rank', 'Vol_Perc', 'Vol_Hist']].iloc[-1]).T
        df_class_vol = pd.concat([df_class_vol, df], axis=0).reset_index(drop=True)
    
    # ============================================================
    # RENOMEAR ÍNDICE
    # ============================================================
    df_class_vol.columns = df_class_vol.columns.get_level_values(-1) if isinstance(df_class_vol.columns, pd.MultiIndex) else df_class_vol.columns
    df_class_vol = pd.DataFrame(df_class_vol.to_numpy(), columns=df_class_vol.columns)
    df_class_vol.index = range(len(df_class_vol))
    
    return df_class_vol

