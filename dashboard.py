import pandas as pd
import math
from datetime import datetime
import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import os

df = pd.DataFrame()
produtos_portfolio = []

import os

df = None
caminho_base = None


def formatar_moeda(valor):

    if pd.isna(valor):
        return "R$ 0,00"

    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

caminho_base = None

def carregar_portfolio():

    pasta = os.path.dirname(os.path.abspath(__file__))
    caminho = os.path.join(pasta, "Portifolio.xlsx")

    if os.path.exists(caminho):

        df_port = pd.read_excel(caminho)

        df_port.columns = df_port.columns.str.strip()

        produtos = (
            df_port.iloc[:,0]
            .dropna()
            .astype(str)
            .str.strip()
            .str.upper()
        )

        return list(produtos)

    else:

        print("Arquivo Portifolio.xlsx não encontrado")
        return []

def carregar_automatico():

    global df
    global caminho_base

    pasta_sistema = os.path.dirname(os.path.abspath(__file__))

    caminho = os.path.join(
        pasta_sistema,
        "Vendas_mensais.xlsx"
    )

    caminho_base = caminho

    if os.path.exists(caminho):

        try:
            df = calcular_previsao(caminho)

            global produtos_portfolio

            produtos_portfolio = carregar_portfolio()

            produtos_portfolio = [
                str(p).strip().upper()
                for p in produtos_portfolio
            ]

            atualizar_tabela(df)
            atualizar_kpi(df)
            atualizar_filtro_familia()
            atualizar_filtro_fornecedor()

        except Exception as e:
            print("Erro ao carregar arquivo:", e)

    else:
        print("Arquivo não encontrado:", caminho)
        
def atualizar_filtro_familia():

    familias = sorted(
        df["Família"]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
    )

    filtro_familia["values"] = ["Todas"] + list(familias)
    filtro_familia.set("Todas")

def carregar_custo():

    pasta = os.path.dirname(os.path.abspath(__file__))

    caminho_custo = os.path.join(pasta, "Custo.xlsx")

    if os.path.exists(caminho_custo):

        df_custo = pd.read_excel(
            caminho_custo,
            skiprows=0
        )

        df_custo.columns = df_custo.columns.str.strip()

        return df_custo

    else:

        print("Arquivo Custo.xlsx não encontrado")
        return None




def arredondar(valor):

    if pd.isna(valor):
        return 0

    return int(math.ceil(valor))

def atualizar_kpi(df):

    global produtos_portfolio

    if len(produtos_portfolio) == 0:
        produtos_portfolio = []

    df_port = df[
        df["Produto"].isin(produtos_portfolio)
    ]

    # =========================
    # PORTFOLIO
    # =========================

    ruptura_port = len(
        df_port[df_port["Estoque"] <= 0]
    )

    iminente_port = len(
        df_port[
            (df_port["Cobertura_Meses"] < 1) &
            (df_port["Estoque"] > 0)
        ]
    )

    atencao_port = len(
        df_port[
            (df_port["Cobertura_Meses"] >= 1) &
            (df_port["Cobertura_Meses"] < 2)
        ]
    )

    excesso_port = len(
        df_port[
            df_port["Estoque"] >
            (df_port["Media_3_Meses"] * 2)
        ]
    )

    label_kpi_ruptura_port.config(
        text=f"🔴 Ruptura Portfólio ({ruptura_port})"
    )

    label_kpi_iminente_port.config(
        text=f"🟠 Iminente Portfólio ({iminente_port})"
    )

    label_kpi_atencao_port.config(
        text=f"🟡 Atenção Portfólio ({atencao_port})"
    )

    label_kpi_excesso_port.config(
        text=f"🔵 Excesso Portfólio ({excesso_port})"
    )

    # =========================
    # FINANCEIRO
    # =========================

    impacto = df["Valor_Compra"].sum()

    label_kpi_financeiro.config(
        text=f"💰 Impacto: {formatar_moeda(impacto)}"
    )

    
def atualizar_filtro_fornecedor():

    global lista_fornecedores

    lista_fornecedores = sorted(
        df["Fornecedor  Fantasia"]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
    )

    filtro_fornecedor["values"] = ["Todos"] + lista_fornecedores
    filtro_fornecedor.set("Todos")

def filtrar_fornecedor(event):

    texto = filtro_fornecedor.get().lower()

    lista = [
        fornecedor for fornecedor in lista_fornecedores
        if texto in fornecedor.lower()
    ]

    filtro_fornecedor["values"] = ["Todos"] + lista

def filtrar_ruptura_port(event=None):

    filtrado = df[
        (df["Estoque"] <= 0) &
        (df["Produto"].isin(produtos_portfolio))
    ]

    atualizar_tabela(filtrado)


def filtrar_iminente_port(event=None):

    filtrado = df[
        (df["Cobertura_Meses"] < 1) &
        (df["Estoque"] > 0) &
        (df["Produto"].isin(produtos_portfolio))
    ]

    atualizar_tabela(filtrado)


def filtrar_atencao_port(event=None):

    filtrado = df[
        (df["Cobertura_Meses"] >= 1) &
        (df["Cobertura_Meses"] < 2) &
        (df["Produto"].isin(produtos_portfolio))
    ]

    atualizar_tabela(filtrado)


def filtrar_excesso_port(event=None):

    filtrado = df[
        (df["Estoque"] > df["Media_3_Meses"] * 2) &
        (df["Produto"].isin(produtos_portfolio))
    ]

    atualizar_tabela(filtrado)

def selecionar_compra():

    for item in tabela.get_children():

        valores = list(tabela.item(item, "values"))

        try:
            sugestao = int(valores[7])
        except:
            sugestao = 0

        if sugestao > 0:
            valores[0] = "☑"
        else:
            valores[0] = "☐"

        tabela.item(item, values=valores)

def formatar_cobertura(meses):

    if meses <= 0:
        return "0 dias"

    dias_total = int(meses * 26)

    meses_int = dias_total // 26
    dias = dias_total % 26

    if meses_int == 0:
        return f"{dias} dias"

    if dias == 0:
        if meses_int == 1:
            return "1 mês"
        return f"{meses_int} meses"

    if meses_int == 1:
        return f"1 mês e {dias} dias"

    return f"{meses_int} meses e {dias} dias"


def calcular_previsao(caminho_arquivo):

    df = pd.read_excel(caminho_arquivo, skiprows=3)

    df.columns = df.columns.str.strip()
    df = df.loc[:, ~df.columns.duplicated()]
    df = df.copy()

    

    # =========================
    # CARREGAR CUSTO
    # =========================

    df_custo = carregar_custo()
    

    if df_custo is not None:

        df["Produto"] = df["Produto"].astype(str).str.strip()
        df_custo["Descricao Produto"] = df_custo["Descricao Produto"].astype(str).str.strip()
        df["Fornecedor  Fantasia"] = df["Fornecedor  Fantasia"].astype(str).str.strip()

        df_custo = df_custo.drop_duplicates(subset="Descricao Produto")

        df = df.merge(
            df_custo[
                ["Descricao Produto", "Preco Custo"]
            ],
            left_on="Produto",
            right_on="Descricao Produto",
            how="left"
        )

        df.drop(columns=["Descricao Produto"], inplace=True)

    # =========================
    # AJUSTAR NOMES DAS COLUNAS
    # =========================

    mapa_meses = {
        "Jan":"Jan","Fev":"Fev","Mar":"Mar","Abr":"Abr",
        "Mai":"Mai","Jun":"Jun","Jul":"Jul","Ago":"Ago",
        "Set":"Set","Out":"Out","Nov":"Nov","Dez":"Dez"
    }

    novas_colunas = {}

    for col in df.columns:
        if "Qtde" in col:
            mes = col[:3]
            if mes in mapa_meses:
                novas_colunas[col] = mapa_meses[mes]

    df = df.rename(columns=novas_colunas)
    df = df.fillna(0)

    meses = ["Jan","Fev","Mar","Abr","Mai","Jun",
             "Jul","Ago","Set","Out","Nov","Dez"]

    mes_atual = datetime.now().month - 1

    mes1 = meses[(mes_atual-3) % 12]
    mes2 = meses[(mes_atual-2) % 12]
    mes3 = meses[(mes_atual-1) % 12]

    sugestoes = []
    medias = []

    for _, row in df.iterrows():

        def pegar_valor(row, coluna):
            valor = row[coluna] if coluna in df.columns else 0

            if isinstance(valor, pd.Series):
                valor = valor.iloc[0]

            valor = pd.to_numeric(valor, errors="coerce")

            return 0 if pd.isna(valor) else valor


        v1 = pegar_valor(row, mes1)
        v2 = pegar_valor(row, mes2)
        v3 = pegar_valor(row, mes3)

        media = (v1 + v2 + v3) / 3
        medias.append(arredondar(media))

        if v1 == 0:
            tendencia = 0
        else:
            tendencia = (v3 - v1) / v1

        tendencia = max(min(tendencia, 0.20), -0.20)

        # previsão usando média + tendência
        previsao = media * (1 + tendencia)

        # cobertura desejada = 45 dias
        fator_cobertura = cobertura_dias.get() / 26

        # compra planejada para 45 dias
        compra_planejada = previsao * fator_cobertura

        estoque_atual = row.get("Estoque",0)

        sugestao = max(compra_planejada - estoque_atual, 0)

        sugestoes.append(arredondar(sugestao))

    df["Media_3_Meses"] = medias
    df["Sugestao_Compra"] = sugestoes

    df["Cobertura_Meses"] = df.apply(
        lambda x: x["Estoque"] / x["Media_3_Meses"]
        if x["Media_3_Meses"] > 0 else 0,
        axis=1
    )

    df = df.sort_values(by="Media_3_Meses", ascending=False)
    df["Ranking"] = range(1, len(df)+1)

    df["Valor_Compra"] = (
        df["Sugestao_Compra"] *
        df["Preco Custo"]
    ).fillna(0)

    df["Valor_Compra"] = df["Valor_Compra"].round(2)

    # =========================
    # CURVA ABC
    # =========================

    df["Venda_Anual"] = df[meses].sum(axis=1)

    df = df.sort_values(by="Venda_Anual", ascending=False)

    total_venda = df["Venda_Anual"].sum()

    if total_venda == 0:
        df["Perc_Venda"] = 0
    else:
        df["Perc_Venda"] = df["Venda_Anual"] / total_venda

    df["Perc_Acumulado"] = df["Perc_Venda"].cumsum()

    def classificar_abc(p):

        if p <= 0.80:
            return "A"
        elif p <= 0.95:
            return "B"
        else:
            return "C"

    df["Curva_ABC"] = df["Perc_Acumulado"].apply(classificar_abc)

    df["Família"] = df["Família"].astype(str).str.strip()

    df["Produto"] = (
        df["Produto"]
        .astype(str)
        .str.strip()
        .str.upper()
    )
    

    return df

def recalcular_previsao():

    global df
    global caminho_base

    if caminho_base is None:
        return

    df = calcular_previsao(caminho_base)

    atualizar_tabela(df)


def atualizar_tabela(dados):

    for item in tabela.get_children():
        tabela.delete(item)

    for i, row in dados.iterrows():

        if row["Estoque"] <= 0:
            tag = "ruptura"

        elif row["Cobertura_Meses"] < 1:
            tag = "ruptura_iminente"

        elif row["Cobertura_Meses"] < 2:
            tag = "atencao"

        elif row["Estoque"] > row["Media_3_Meses"] * 2:
            tag = "excesso"

        else:
            tag = "normal"

        tabela.insert(
            "",
            "end",
            values=(
                "☐",
                row["Ranking"],
                row["Código"],
                row["Produto"],
                row["Media_3_Meses"],
                row["Estoque"],
                formatar_cobertura(row["Cobertura_Meses"]),
                row["Sugestao_Compra"],
                formatar_moeda(row["Valor_Compra"]),
                row["Curva_ABC"]
            ),
            tags=(tag,)
        )
        


def toggle_checkbox(event):

    item = tabela.identify_row(event.y)
    coluna = tabela.identify_column(event.x)

    if coluna != "#1":
        return

    valores = list(tabela.item(item,"values"))

    valores[0] = "☑" if valores[0] == "☐" else "☐"

    tabela.item(item,values=valores)

    calcular_impacto_selecionado()


def pesquisar(event=None):

    texto = campo_pesquisa.get().lower()

    df_filtrado = df[
        df["Produto"]
        .astype(str)
        .str.lower()
        .str.contains(texto, na=False)
    ]

    filtro = filtro_situacao.get()

    if filtro == "Ruptura":
        df_filtrado = df_filtrado[df_filtrado["Estoque"] <= 0]

    elif filtro == "Ruptura Iminente":
        df_filtrado = df_filtrado[
            (df_filtrado["Cobertura_Meses"] < 1) &
            (df_filtrado["Estoque"] > 0)
        ]

    elif filtro == "Atenção":
        df_filtrado = df_filtrado[
            (df_filtrado["Cobertura_Meses"] >= 1) &
            (df_filtrado["Cobertura_Meses"] < 2)
        ]

    elif filtro == "Excesso":
        df_filtrado = df_filtrado[
            df_filtrado["Estoque"] >
            (df_filtrado["Media_3_Meses"] * 2)
        ]

    atualizar_tabela(df_filtrado)

def aplicar_filtro():

    filtro = filtro_situacao.get()
    familia = filtro_familia.get()
    fornecedor = filtro_fornecedor.get()

    df_filtrado = df.copy()

    # Situação
    if filtro == "Ruptura":
        df_filtrado = df_filtrado[df_filtrado["Estoque"] <= 0]

    elif filtro == "Ruptura Iminente":
        df_filtrado = df_filtrado[
            (df_filtrado["Cobertura_Meses"] < 1) &
            (df_filtrado["Estoque"] > 0)
        ]

    elif filtro == "Atenção":
        df_filtrado = df_filtrado[
            (df_filtrado["Cobertura_Meses"] >= 1) &
            (df_filtrado["Cobertura_Meses"] < 2)
        ]

    elif filtro == "Excesso":
        df_filtrado = df_filtrado[
            df_filtrado["Estoque"] >
            (df_filtrado["Media_3_Meses"] * 2)
        ]

    # Família
    if familia != "Todas":
        df_filtrado = df_filtrado[
            df_filtrado["Família"] == familia
        ]

    # Fornecedor
    if fornecedor != "Todos":
        df_filtrado = df_filtrado[
            df_filtrado["Fornecedor  Fantasia"] == fornecedor
        ]

    atualizar_tabela(df_filtrado)


def mostrar_grafico(event):

    item = tabela.selection()

    if not item:
        return

    produto = tabela.item(item)["values"][3]

    dados = df[df["Produto"] == produto].iloc[0]

    meses = ["Jan","Fev","Mar","Abr","Mai","Jun",
             "Jul","Ago","Set","Out","Nov","Dez"]

    vendas = [dados.get(m,0) for m in meses]

    fig = Figure(figsize=(5,3))
    ax = fig.add_subplot(111)

    ax.plot(meses, vendas, marker="o")
    ax.set_title(produto)
    ax.set_ylabel("Vendas")

    for widget in frame_grafico.winfo_children():
        widget.destroy()

    canvas = FigureCanvasTkAgg(fig, master=frame_grafico)
    canvas.draw()
    canvas.get_tk_widget().pack()


def gerar_pedido():

    produtos = []

    for item in tabela.get_children():

        valores = tabela.item(item)["values"]

        if valores[0] == "☑":

            produtos.append({
                "Produto": valores[3],
                "Estoque": valores[5],
                "Media_3_Meses": valores[4],
                "Sugestao_Compra": valores[7],
                "Cobertura" : valores[6],
                "Valor_Compra": valores[8],
                "Curva_ABC": valores[9]
            })

    if not produtos:
        return

    pedido_df = pd.DataFrame(produtos)

    caminho = filedialog.asksaveasfilename(
        defaultextension=".xlsx",
        filetypes=[("Excel files","*.xlsx")]
    )

    if caminho:
        pedido_df.to_excel(caminho,index=False)
    

def calcular_impacto_selecionado():

    total = 0

    for item in tabela.get_children():

        valores = tabela.item(item)["values"]

        if valores[0] == "☑":

            valor = valores[7]

            if isinstance(valor, str):
                valor = valor.replace("R$", "").replace(".", "").replace(",", ".")
                valor = float(valor)

            total += float(valor)

    label_impacto_selecionado.config(
        text=f"💰 Impacto Selecionados: {formatar_moeda(total)}"
    )
def selecionar_todos():

    for item in tabela.get_children():

        valores = list(tabela.item(item, "values"))

        valores[0] = "☑"

        tabela.item(item, values=valores)

def desmarcar_todos():

    for item in tabela.get_children():

        valores = list(tabela.item(item, "values"))

        valores[0] = "☐"

        tabela.item(item, values=valores)


# =========================
# INTERFACE
# =========================

janela = tk.Tk()
cobertura_dias = tk.IntVar(value=45)
janela.title("Sistema Inteligente de Planejamento de Compras")
janela.geometry("1200x700")
janela.configure(bg="#f4f6f9")




titulo = tk.Label(
    janela,
    text="Sistema Inteligente de Planejamento de Compras",
    font=("Arial",20,"bold"),
    bg="#f4f6f9"
)

titulo.pack(pady=10)
# =========================
# KPI ALERTAS AVANÇADO
# =========================

frame_kpi = tk.Frame(janela, bg="#f4f6f9")
frame_kpi.pack(pady=5)


botao_pedido = tk.Button(
    janela,
    text="Gerar Pedido de Compra",
    font=("Arial",12,"bold"),
    bg="#2196F3",
    fg="white",
    padx=25,
    pady=8,
    command=gerar_pedido
)



label_impacto_selecionado = tk.Label(
    janela,
    text="💰 Impacto Selecionados: R$ 0,00",
    font=("Arial",12,"bold"),
    fg="#2e7d32",
    bg="#f4f6f9"
)

label_impacto_selecionado.pack(pady=5)

botao_pedido.pack(pady=5)

label_kpi_financeiro = tk.Label(
    frame_kpi,
    text="💰 Impacto Financeiro",
    font=("Arial",12,"bold"),
    fg="#2e7d32",
    bg="#f4f6f9"
)

label_kpi_financeiro.pack(side="left", padx=15)

# =========================
# KPI PORTFOLIO
# =========================

frame_kpi_port = tk.Frame(janela, bg="#f4f6f9")
frame_kpi_port.pack(pady=3)

label_kpi_ruptura_port = tk.Label(
    frame_kpi_port,
    text="🔴 Ruptura Portfólio",
    font=("Arial",11,"bold"),
    fg="red",
    cursor="hand2",
    bg="#f4f6f9"
)

label_kpi_ruptura_port.pack(side="left", padx=8)
label_kpi_ruptura_port.bind("<Button-1>", filtrar_ruptura_port)


label_kpi_iminente_port = tk.Label(
    frame_kpi_port,
    text="🟠 Iminente Portfólio",
    font=("Arial",11,"bold"),
    fg="#ff8c00",
    cursor="hand2",
    bg="#f4f6f9"
)

label_kpi_iminente_port.pack(side="left", padx=8)
label_kpi_iminente_port.bind("<Button-1>", filtrar_iminente_port)


label_kpi_atencao_port = tk.Label(
    frame_kpi_port,
    text="🟡 Atenção Portfólio",
    font=("Arial",11,"bold"),
    fg="#b8860b",
    cursor="hand2",
    bg="#f4f6f9"
)

label_kpi_atencao_port.pack(side="left", padx=8)
label_kpi_atencao_port.bind("<Button-1>", filtrar_atencao_port)


label_kpi_excesso_port = tk.Label(
    frame_kpi_port,
    text="🔵 Excesso Portfólio",
    font=("Arial",11,"bold"),
    fg="#1e90ff",
    cursor="hand2",
    bg="#f4f6f9"
)

label_kpi_excesso_port.pack(side="left", padx=8)
label_kpi_excesso_port.bind("<Button-1>", filtrar_excesso_port)

frame_selecao = tk.Frame(janela, bg="#f4f6f9")
frame_selecao.pack(pady=5)

btn_sel_todos = tk.Button(
    frame_selecao,
    text="Selecionar Todos (Filtrados)",
    font=("Arial",10,"bold"),
    bg="#4CAF50",
    fg="white",
    command=selecionar_todos
)

btn_sel_todos.pack(side="left", padx=5)

btn_sel_compra = tk.Button(
    frame_selecao,
    text="Selecionar Sugestão > 0",
    font=("Arial",10,"bold"),
    bg="#ff9800",
    fg="white",
    command=selecionar_compra
)

btn_sel_compra.pack(side="left", padx=5)


btn_desmarcar = tk.Button(
    frame_selecao,
    text="Desmarcar Todos",
    font=("Arial",10,"bold"),
    bg="#f44336",
    fg="white",
    command=desmarcar_todos
)

btn_desmarcar.pack(side="left", padx=5)


# =========================
# PESQUISA
# =========================

frame_pesquisa = tk.Frame(janela,bg="#f4f6f9")
frame_pesquisa.pack(pady=10)

tk.Label(
    frame_pesquisa,
    text="Pesquisar Produto:",
    font=("Arial",12),
    bg="#f4f6f9"
).pack(side="left")

campo_pesquisa = tk.Entry(frame_pesquisa,font=("Arial",12),width=30)
campo_pesquisa.pack(side="left",padx=10)

campo_pesquisa.bind("<KeyRelease>", pesquisar)

frame_cobertura = tk.Frame(janela, bg="#f4f6f9")
frame_cobertura.pack(pady=5)

tk.Label(
    frame_cobertura,
    text="Cobertura:",
    font=("Arial",11,"bold"),
    bg="#f4f6f9"
).pack(side="left", padx=5)

combo_cobertura = ttk.Combobox(
    frame_cobertura,
    textvariable=cobertura_dias,
    values=[30,45,60,90],
    width=10,
    state="readonly"
)

combo_cobertura.pack(side="left")
combo_cobertura.bind(
    "<<ComboboxSelected>>",
    lambda e: recalcular_previsao()
)

tk.Label(
    frame_cobertura,
    text="dias",
    font=("Arial",11),
    bg="#f4f6f9"
).pack(side="left", padx=5)

# =========================
# FILTROS
# =========================

frame_filtros = tk.Frame(janela, bg="#f4f6f9")
frame_filtros.pack(pady=5)

tk.Label(
    frame_filtros,
    text="Filtro Situação:",
    font=("Arial",11),
    bg="#f4f6f9"
).pack(side="left", padx=5)

filtro_situacao = ttk.Combobox(
    frame_filtros,
    values=[
        "Todos",
        "Ruptura",
        "Ruptura Iminente",
        "Atenção",
        "Excesso"
    ],
    state="readonly",
    width=18
)

tk.Label(
    frame_filtros,
    text="Família:",
    font=("Arial",11),
    bg="#f4f6f9"
).pack(side="left", padx=5)

filtro_familia = ttk.Combobox(
    frame_filtros,
    state="readonly",
    width=25
)

filtro_familia.set("Todas")
filtro_familia.pack(side="left", padx=5)

filtro_familia.bind(
    "<<ComboboxSelected>>",
    lambda e: aplicar_filtro()
)

tk.Label(
    frame_filtros,
    text="Fornecedor:",
    font=("Arial",11),
    bg="#f4f6f9"
).pack(side="left", padx=5)


filtro_fornecedor = ttk.Combobox(
    frame_filtros,
    state="normal",
    width=30
)

filtro_fornecedor.set("Todos")
filtro_fornecedor.pack(side="left", padx=5)
filtro_fornecedor.bind("<KeyRelease>", filtrar_fornecedor)

filtro_fornecedor.bind(
    "<<ComboboxSelected>>",
    lambda e: aplicar_filtro()
)

filtro_situacao.set("Todos")
filtro_situacao.pack(side="left", padx=5)

filtro_situacao.bind("<<ComboboxSelected>>", lambda e: aplicar_filtro())

# =========================
# TABELA
# =========================

frame_tabela = tk.Frame(janela)
frame_tabela.pack(fill="both",expand=True,padx=20,pady=10)

colunas = (
"Sel",
"Ranking",
"Código",
"Produto",
"Média 3 Meses",
"Estoque",
"Cobertura",
"Sugestão compra",
"Valor Compra",
"Curva ABC"
)

scroll = ttk.Scrollbar(frame_tabela)
scroll.pack(side="right",fill="y")

tabela = ttk.Treeview(
    frame_tabela,
    columns=colunas,
    show="headings",
    yscrollcommand=scroll.set
)

scroll.config(command=tabela.yview)

for col in colunas:

    tabela.heading(col,text=col)

    if col == "Sel":
        tabela.column(col,width=60,anchor="center")

    elif col == "Código":
        tabela.column(col,width=100,anchor="center")

    elif col == "Produto":
        tabela.column(col,width=320,anchor="w")

    else:
        tabela.column(col,width=130,anchor="center")

tabela.pack(fill="both",expand=True)

tabela.bind("<<TreeviewSelect>>", mostrar_grafico)
tabela.bind("<Button-1>", toggle_checkbox)


# =========================
# GRAFICO
# =========================

frame_grafico = tk.Frame(janela,bg="#f4f6f9")
frame_grafico.pack(fill="x",padx=20,pady=10)


# =========================
# ESTILO
# =========================

tabela.tag_configure("ruptura", background="#ff4d4d")
tabela.tag_configure("ruptura_iminente", background="#ffb3b3")
tabela.tag_configure("atencao", background="#fff3cd")
tabela.tag_configure("excesso", background="#cce5ff")
tabela.tag_configure("normal", background="white")

style = ttk.Style()
style.configure("Treeview",font=("Arial",11),rowheight=28)
style.configure("Treeview.Heading",font=("Arial",12,"bold"))

carregar_automatico()

janela.mainloop()
