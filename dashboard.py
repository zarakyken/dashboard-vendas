import streamlit as st
import pandas as pd
from datetime import datetime
from datetime import timedelta
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import re

# =====================================================
# CONFIGURAÇÃO INICIAL
# =====================================================
st.set_page_config(page_title="Dashboard de Vendas", layout="wide")


# =====================================================
# CONSTANTES
# =====================================================
META_MENSAL = 2_400_000.00

# =====================================================
# CONTROLE DE PERFIL
# =====================================================
query_params = st.query_params
perfil = query_params.get("perfil", "admin")  # admin | mensal

# =====================================================
# FUNÇÕES AUXILIARES
# =====================================================
def formato_real(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def formato_numero(valor):
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def formato_data_br(data):
    return pd.to_datetime(data).strftime("%d/%m/%Y")

def preparar_base(df):
    df = df.rename(columns={
        "NF-e  Emissão": "data_nfe",
        "CF-e  Emissão": "data_cfe",
        "Vendedor": "vendedor",
        "Produto": "produto",
        "Quantidade": "quantidade",
        "Valor  Unitário": "valor_unitario"
    })

    df.columns = [c.lower().strip() for c in df.columns]
    

    # =====================================================
    # TRATAMENTO DE DATA (NF-e prioridade, CF-e fallback)
    # =====================================================

    df["data"] = df["data_nfe"].fillna(df["data_cfe"])

    # converter para data
    df["data"] = pd.to_datetime(df["data"], errors="coerce").dt.date

    # remover linhas sem data
    df = df.dropna(subset=["data"])

    # =====================================================
    # RESTANTE DO TRATAMENTO
    # =====================================================

    df["quantidade"] = df["quantidade"].astype(float)
    df["valor_unitario"] = df["valor_unitario"].astype(float)

    df["valor_total"] = (
        df["quantidade"].abs() * df["valor_unitario"].abs()
    )

    df.loc[df["quantidade"] < 0, "valor_total"] *= -1

    df["vendedor"] = df["vendedor"].astype(str).str.strip().str.upper()

    # =====================================================
    # CONTROLE DE VISUALIZAÇÃO VENDEDORES RESTRITOS
    # =====================================================

    VENDEDORES_RESTRITOS = ["LIMA", "EDUARDO"]

    if perfil != "admin":
        # Usuário comum não vê esses vendedores
        df = df[
            ~df["vendedor"].isin(VENDEDORES_RESTRITOS)
        ]

    # Base separada para KPIs gerais (mesmo admin não soma)
    df_kpi = df[
        ~df["vendedor"].isin(VENDEDORES_RESTRITOS)
    ].copy()

    # Base exclusiva dos vendedores restritos (somente admin)
    df_restritos = df[
        df["vendedor"].isin(VENDEDORES_RESTRITOS)
    ].copy()
 

    return df, df_kpi, df_restritos

# =====================================================
# SIDEBAR
# =====================================================
st.sidebar.title("📊 Relatórios")

if perfil == "admin":
    tipo_dashboard = st.sidebar.radio(
        "Selecione o Dashboard",
        ["Dashboard Mensal", "Orçamentos em Aberto", "Dashboard de Compras"]
    )
else:
    tipo_dashboard = "Dashboard Mensal"
    st.sidebar.info("Acesso restrito ao Dashboard Mensal")

# =====================================================
# DASHBOARD MENSAL (ATUALIZADO)
# =====================================================
if tipo_dashboard == "Dashboard Mensal":
    st.title("📊 Dashboard Mensal de Vendas")

    df, df_kpi, df_restritos = preparar_base(
        pd.read_excel("vendas.xlsx")
    )

    df_frete = pd.read_excel("frete.xlsx", skiprows=3)

    # Renomear colunas novas
    df_frete = df_frete.rename(columns={
        "Vendedor": "vendedor",
        "Valor Frete": "receita_frete"
    })

    

    import re

    # Padronizar colunas
    df_frete.columns = [c.lower().strip() for c in df_frete.columns]

    # 🔥 LIMPAR VENDEDOR (ANTES DE TUDO)
    def limpar_vendedor(nome):
        nome = str(nome)
        nome = re.sub(r"\s*\[.*?\]", "", nome)
        return nome.strip().upper()

    df_frete["vendedor"] = df_frete["vendedor"].apply(limpar_vendedor)

    # Garantir tipo numérico
    df_frete["receita_frete"] = pd.to_numeric(
        df_frete["receita_frete"], errors="coerce"
    ).fillna(0)

    # Agora sim agrupa corretamente
    frete_por_vendedor = (
        df_frete.groupby("vendedor")["receita_frete"]
        .sum()
        .reset_index()
    )

    frete_por_vendedor["vendedor"] = frete_por_vendedor["vendedor"].str.upper()

    frete_sem_lima = frete_por_vendedor[
        frete_por_vendedor["vendedor"] != "LIMA"
    ]

    total_frete = frete_sem_lima["receita_frete"].sum()

    c1, c2 = st.columns(2)
    data_inicio = c1.date_input("Data inicial", min(df["data"]))
    data_fim = c2.date_input("Data final", max(df["data"]))

    df = df[(df["data"] >= data_inicio) & (df["data"] <= data_fim)]

    # 🔐 Separação de base
    df["vendedor"] = df["vendedor"].astype(str).str.strip().str.upper()

    df_lima = df[df["vendedor"] == "LIMA"]
    df_sem_lima = df[df["vendedor"] != "LIMA"]

    # Controle por perfil
    if perfil != "admin":
        df = df_sem_lima.copy()

    df_kpi_filtrado = df_kpi[
        (df_kpi["data"] >= data_inicio) &
        (df_kpi["data"] <= data_fim)
    ]

    total_vendas = df_kpi_filtrado["valor_total"].sum()
    total_frete = frete_por_vendedor["receita_frete"].sum()

    k1, k2, k3 = st.columns(3)
    k1.metric("💰 Total de Vendas", formato_real(total_vendas))
    k2.metric("🚚 Frete Total", formato_real(total_frete))
    k3.metric("🎯 Meta Mensal", formato_real(META_MENSAL))

    

   # -------- VENDAS + FRETE + META POR VENDEDOR --------
    st.subheader("👤 Vendas, Frete e Meta por Vendedor")

    # Agrupa vendas
    vendas_vendedor = (
        df.groupby("vendedor")["valor_total"]
        .sum()
        .reset_index()
    )

    # Agrupa frete

    df_frete["vendedor"] = df_frete["vendedor"].apply(limpar_vendedor)
    
    frete_por_vendedor = (
        df_frete.groupby("vendedor")["receita_frete"]
        .sum()
        .reset_index()
    )

    # Junta vendas + frete
    vendas_vendedor = vendas_vendedor.merge(
        frete_por_vendedor,
        on="vendedor",
        how="left"
    ).fillna(0)

    # Ordena do maior para o menor
    vendas_vendedor = vendas_vendedor.sort_values(
        "valor_total", ascending=False
    )

    # Calcula meta individual
    qtd_vendedores = vendas_vendedor["vendedor"].nunique()
    meta_individual = META_MENSAL / 7

    vendas_vendedor["Meta Individual"] = meta_individual

    

    # =====================================================
    # PROJEÇÃO DE FATURAMENTO (CICLO 26-25)
    # =====================================================

    hoje = pd.Timestamp.today().date()

    # Determinar início do ciclo
    if hoje.day >= 26:
        inicio_ciclo = hoje.replace(day=26)
    else:
        mes_anterior = (pd.Timestamp(hoje) - pd.DateOffset(months=1)).date()
        inicio_ciclo = mes_anterior.replace(day=26)

    # Determinar fim do ciclo
    if hoje.day >= 26:
        proximo_mes = (pd.Timestamp(hoje) + pd.DateOffset(months=1)).date()
        fim_ciclo = proximo_mes.replace(day=25)
    else:
        fim_ciclo = hoje.replace(day=25)

    # Dados do ciclo
    df_ciclo = df[(df["data"] >= inicio_ciclo) & (df["data"] < hoje)]

    # Remover domingos
    df_ciclo = df_ciclo[pd.to_datetime(df_ciclo["data"]).dt.weekday != 6]

    # vendas por vendedor no ciclo
    vendas_ciclo = (
        df_ciclo.groupby("vendedor")["valor_total"]
        .sum()
        .reset_index()
    )

    # juntar com tabela principal
    vendas_vendedor = vendas_vendedor.merge(
        vendas_ciclo,
        on="vendedor",
        how="left",
        suffixes=("", "_ciclo")
    ).fillna(0)

    # Dias trabalhados (sem domingo)
    datas_passadas = pd.date_range(inicio_ciclo, hoje - pd.Timedelta(days=1))
    dias_passados = len([d for d in datas_passadas if d.weekday() != 6])

    # Total de dias do ciclo (sem domingo)
    datas_total = pd.date_range(inicio_ciclo, fim_ciclo)
    total_dias = len([d for d in datas_total if d.weekday() != 6])

    # média diária
    vendas_vendedor["media_diaria"] = vendas_vendedor["valor_total_ciclo"] / max(dias_passados,1)

    # projeção
    vendas_vendedor["projecao"] = (
        vendas_vendedor["media_diaria"] * total_dias
    )

    # Status da meta
    vendas_vendedor["Status Meta"] = vendas_vendedor["valor_total"].apply(
        lambda x: "🟢 Atingiu a Meta" if x >= meta_individual else "🔴 Não Atingiu"
    )

    # % Frete sobre vendas
    vendas_vendedor["% Frete / Vendas"] = (
        vendas_vendedor["receita_frete"] / vendas_vendedor["valor_total"] * 100
    ).fillna(0)

    # Formatação
    vendas_vendedor["Vendas"] = vendas_vendedor["valor_total"].apply(formato_real)
    vendas_vendedor["Frete Cobrado"] = vendas_vendedor["receita_frete"].apply(formato_real)
    vendas_vendedor["Meta Individual"] = vendas_vendedor["Meta Individual"].apply(formato_real)
    vendas_vendedor["% Frete / Vendas"] = vendas_vendedor["% Frete / Vendas"].apply(
        lambda x: f"{x:.2f}%"
    )
    vendas_vendedor["Projeção"] = vendas_vendedor["projecao"].apply(formato_real)

    # Exibição final
    st.dataframe(
        vendas_vendedor[
            [
                "vendedor",
                "Vendas",
                "Frete Cobrado",
                "% Frete / Vendas",
                "Meta Individual",
                "Projeção",
                "Status Meta",
                
            ]
        ],
        use_container_width=True
    )

    # =====================================================
    # PROGRESSO DA META (BASEADO NO VENDIDO)
    # =====================================================

    progresso_meta = total_vendas / META_MENSAL

    if progresso_meta > 1:
        progresso_meta = 1

    percentual_meta = (total_vendas / META_MENSAL) * 100

    st.markdown("### 🎯 Progresso da Meta (Realizado)")

    st.progress(progresso_meta)

    st.markdown(
        f"**{percentual_meta:,.2f}% da meta atingida**".replace(",", "X").replace(".", ",").replace("X", ".")
    )


    # =====================================================
    # PROJEÇÃO DE FATURAMENTO (CICLO 26 → 25) SEM DOMINGOS
    # =====================================================

    from datetime import datetime, timedelta

    hoje = datetime.today().date()

    # Determinar início e fim do ciclo (26 -> 25)
    if hoje.day >= 26:
        inicio_ciclo = hoje.replace(day=26)
        proximo_mes = (inicio_ciclo + timedelta(days=32)).replace(day=1)
        fim_ciclo = proximo_mes.replace(day=25)
    else:
        mes_anterior = (hoje.replace(day=1) - timedelta(days=1))
        inicio_ciclo = mes_anterior.replace(day=26)
        fim_ciclo = hoje.replace(day=25)

    # Converter data
    df["data"] = pd.to_datetime(df["data"]).dt.date

    # Filtrar período
    df_periodo = df_kpi[
        (df["data"] >= inicio_ciclo) &
        (df["data"] <= fim_ciclo) &
        (df["data"] < hoje)
    ]

    # Remover domingos
    df_periodo = df_periodo[pd.to_datetime(df_periodo["data"]).dt.weekday != 6]

    # Remover dia atual
    df_periodo = df_periodo[df_periodo["data"] < hoje]

    # Faturamento atual
    faturamento_atual = df_periodo["valor_total"].sum()

    # Dias já ocorridos
    dias_ocorridos = df_periodo["data"].nunique()

    # Total de dias úteis no ciclo (sem domingos)
    datas = pd.date_range(inicio_ciclo, fim_ciclo)
    datas = [d.date() for d in datas if d.weekday() != 6]

    total_dias = len(datas)

    # Média diária
    media_diaria = faturamento_atual / dias_ocorridos if dias_ocorridos > 0 else 0

    # Projeção final
    projecao = media_diaria * total_dias

    

    if projecao >= META_MENSAL:
        cor = "green"
        icone = "🟢"
    else:
        cor = "red"
        icone = "🔴"
        
    col1, col2 = st.columns(2)

    with col1:
        st.metric("📊 Média diária", formato_real(media_diaria))    
    with col2:
        st.markdown("📈 Projeção de vendas")    
    col2.markdown(
        f"""
        <h2 style='color:{cor};'>
        {icone} {formato_real(projecao)}
        </h2>
        """,
        unsafe_allow_html=True
    )

    

    # =====================================================
    # 🎯 META DIÁRIA POR VENDEDOR
    # =====================================================

    # Total de dias do ciclo (sem domingo)
    datas_ciclo = pd.date_range(inicio_ciclo, fim_ciclo)
    dias_ciclo = len([d for d in datas_ciclo if d.weekday() != 6])

    # Quantidade de vendedores
    qtd_vendedores = df["vendedor"].nunique()

    

    import plotly.express as px

    # -------- VENDAS DIÁRIAS (SELEÇÃO POR DATA) --------
    st.subheader("📅 Vendas do Dia")

    datas_disponiveis = sorted(df["data"].unique())
    hoje = datetime.today().date()

    indice_padrao = datas_disponiveis.index(hoje) if hoje in datas_disponiveis else len(datas_disponiveis) - 1

    dia_sel = st.selectbox(
        "Selecione a data",
        datas_disponiveis,
        index=indice_padrao
    )

    df_dia = df_kpi[df["data"] == dia_sel]

    titulo_dia = pd.to_datetime(dia_sel).strftime("%A").capitalize()
    st.markdown(f"### 🗓️ {titulo_dia} ({formato_data_br(dia_sel)})")

    # =====================================================
    # 📈 TENDÊNCIA (DIA ANTERIOR)
    # =====================================================

    # 🔥 PRIMEIRO calcula o total do dia
    total_dia = df_dia["valor_total"].sum()

    # Depois calcula dia anterior
    data_anterior = dia_sel - pd.Timedelta(days=1)
    df_dia_anterior = df[df["data"] == data_anterior]

    total_dia_anterior = df_dia_anterior["valor_total"].sum()

    # Variação
    if total_dia_anterior > 0:
        variacao = ((total_dia - total_dia_anterior) / total_dia_anterior) * 100
    else:
        variacao = 0

    # =====================================================
    # KPI
    # =====================================================

    delta_cor = "normal" if variacao >= 0 else "inverse"

    st.metric(
        "💰 Total do Dia",
        formato_real(total_dia),
        f"{variacao:.2f}% vs dia anterior",
        delta_color=delta_cor
    )

    # =====================================================
    # 📈 VENDAS POR DIA (CICLO)
    # =====================================================

    st.markdown("### 📈 Vendas por Dia no Ciclo")

    df_ciclo_total = df_sem_lima[
        (df["data"] >= inicio_ciclo) &
        (df["data"] <= fim_ciclo)
    ].copy()

    # Remover domingos
    df_ciclo_total = df_ciclo_total[
        pd.to_datetime(df_ciclo_total["data"]).dt.weekday != 6
    ]

    # Agrupar por dia
    vendas_por_dia = (
        df_ciclo_total.groupby("data")["valor_total"]
        .sum()
        .reset_index()
        .sort_values("data")
    )

    # =====================================================
    # 🔥 COLUNAS AUXILIARES (ORDEM CORRETA)
    # =====================================================

    # Semana do ciclo
    vendas_por_dia["semana"] = (
        (pd.to_datetime(vendas_por_dia["data"]) - pd.to_datetime(inicio_ciclo))
        .dt.days // 7
    )

    # Nome do dia
    vendas_por_dia["dia_semana_nome"] = pd.to_datetime(
        vendas_por_dia["data"]
    ).dt.strftime("%a")

    mapa_dias = {
        "Mon": "Seg",
        "Tue": "Ter",
        "Wed": "Qua",
        "Thu": "Qui",
        "Fri": "Sex",
        "Sat": "Sáb"
    }

    vendas_por_dia["dia_semana_nome"] = vendas_por_dia["dia_semana_nome"].map(mapa_dias)

    # Média
    media = vendas_por_dia["valor_total"].mean()

    # =====================================================
    # 📊 GRÁFICO
    # =====================================================

    import plotly.express as px

    fig_linha = px.line(
        vendas_por_dia,
        x="data",
        y="valor_total",
        markers=True
    )

    # =====================================================
    # 🎨 FUNDO POR SEMANA
    # =====================================================

    semanas = vendas_por_dia["semana"].unique()

    for i, semana in enumerate(semanas):
        dados_semana = vendas_por_dia[vendas_por_dia["semana"] == semana]

        fig_linha.add_vrect(
            x0=dados_semana["data"].min(),
            x1=dados_semana["data"].max(),
            fillcolor="lightgrey" if i % 2 == 0 else "white",
            opacity=0.2,
            layer="below",
            line_width=0,
        )

    # =====================================================
    # 📈 LINHA DA MÉDIA (UMA SÓ)
    # =====================================================

    fig_linha.add_hline(
        y=media,
        line_dash="dash",
        line_color="green",
        annotation_text="Média diária",
        annotation_position="top left"
    )

    # =====================================================
    # 🎯 TOOLTIP FORMATADO
    # =====================================================

    fig_linha.update_traces(
        customdata=vendas_por_dia["dia_semana_nome"],
        hovertemplate="Data: %{x}<br>Dia: %{customdata}<br>Vendas: R$ %{y:,.2f}<extra></extra>"
    )

    # =====================================================
    # 🧭 EIXO X COM DIA + DATA
    # =====================================================

    fig_linha.update_layout(
        xaxis=dict(
            tickmode='array',
            tickvals=vendas_por_dia["data"],
            ticktext=[
                f"{d.strftime('%d/%m')} ({ds})"
                for d, ds in zip(
                    pd.to_datetime(vendas_por_dia["data"]),
                    vendas_por_dia["dia_semana_nome"]
                )
            ]
        ),
        xaxis_title="Data",
        yaxis_title="Valor Vendido"
    )

    st.plotly_chart(fig_linha, use_container_width=True)

    
    # =====================================================
    # 📊  (GRÁFICO)
    # =====================================================

    ranking = (
        df_dia.groupby("vendedor")["valor_total"]
        .sum()
        .reset_index()
        .sort_values("valor_total", ascending=False)
    )

    st.markdown("### 📊 Vendas por Vendedor")

    if not ranking.empty:
        fig_vendedores = px.bar(
            ranking,
            x="vendedor",
            y="valor_total",
            text="valor_total"
        )

        fig_vendedores.update_traces(
            texttemplate="R$ %{y:,.2f}",
            hovertemplate="<b>%{x}</b><br>Vendas: R$ %{y:,.2f}<extra></extra>"
        )

        fig_vendedores.update_layout(
            xaxis_title="Vendedor",
            yaxis_title="Valor Vendido",
        )

        st.plotly_chart(fig_vendedores, use_container_width=True)
    
    

    # =====================================================
    # 📊 PRODUTOS (GRÁFICO POR VALOR)
    # =====================================================

    produtos = (
        df_dia.groupby("produto")["valor_total"]
        .sum()
        .reset_index()
        .sort_values("valor_total", ascending=False)
    )

    st.markdown("### 📊 Vendas por Produto")

    if not produtos.empty:
        fig_produtos = px.bar(
            produtos.head(10),  # top 10
            x="produto",
            y="valor_total",
            text="valor_total"
        )

        fig_produtos.update_traces(
            texttemplate="R$ %{y:,.2f}",
            hovertemplate="<b>%{x}</b><br>Vendas: R$ %{y:,.2f}<extra></extra>"
        )

        fig_produtos.update_layout(
            xaxis_title="Produto",
            yaxis_title="Valor Vendido",
        )

        st.plotly_chart(fig_produtos, use_container_width=True)

# =====================================================
# ORÇAMENTOS EM ABERTO (INALTERADO)
# =====================================================
elif tipo_dashboard == "Orçamentos em Aberto":
    st.title("📋 Orçamentos em Aberto – Visão Semanal")

    df_orc = pd.read_excel("orcamentos_abertos.xlsx")
    df_orc = df_orc.rename(columns={
        "Dt  Emissão": "data",
        "Vendedor": "vendedor",
        "Vl  Pedido": "valor_orcado"
    })
    df_orc.columns = [c.lower().strip() for c in df_orc.columns]

    df_orc["data"] = pd.to_datetime(df_orc["data"], errors="coerce").dt.date
    df_orc = df_orc.dropna(subset=["data"])
    df_orc["valor_orcado"] = df_orc["valor_orcado"].astype(float)

    # =====================================================
    # CONTROLE DE VENDEDORES RESTRITOS
    # =====================================================

    VENDEDORES_RESTRITOS = ["LIMA", "EDUARDO"]

    # Padronizar vendedor
    df_orc["vendedor"] = (
        df_orc["vendedor"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    # Base exclusiva admin (LIMA + EDUARDO)
    df_orc_restritos = df_orc[
        df_orc["vendedor"].isin(VENDEDORES_RESTRITOS)
    ].copy()

    # Usuário comum não vê esses vendedores
    if perfil != "admin":
        df_orc = df_orc[
            ~df_orc["vendedor"].isin(VENDEDORES_RESTRITOS)
        ]

    # KPIs nunca somam LIMA + EDUARDO
    df_orc_kpi = df_orc[
        ~df_orc["vendedor"].isin(VENDEDORES_RESTRITOS)
    ].copy()

    df_orc["vendedor"] = df_orc["vendedor"].astype(str).str.strip().str.upper()

    df_orc_lima = df_orc[df_orc["vendedor"] == "LIMA"]
    df_orc_sem_lima = df_orc[df_orc["vendedor"] != "LIMA"]

    if perfil != "admin":
        df_orc = df_orc_sem_lima.copy()

    # --------------------------
    # TOTAIS
    # --------------------------

    
    total_geral_orcamentos = df_orc_kpi["valor_orcado"].sum()

    

    datas_disponiveis = sorted(df_orc["data"].unique())
    hoje = datetime.today().date()

    if hoje in datas_disponiveis:
        indice_padrao = datas_disponiveis.index(hoje)
    else:
        indice_padrao = len(datas_disponiveis) - 1

    dia_sel = st.selectbox(
        "Selecione o dia",
        datas_disponiveis,
        index=indice_padrao
    )

    df_dia_total = df_orc[df_orc["data"] == dia_sel]
    df_dia_kpi = df_orc_kpi[
        df_orc_kpi["data"] == dia_sel
    ]

    total_dia_orcamentos = df_dia_kpi["valor_orcado"].sum()

    k1, k2 = st.columns(2)
    k1.metric("💰 Total Geral de Orçamentos", formato_real(total_geral_orcamentos))
    k2.metric("📅 Total do Dia", formato_real(total_dia_orcamentos))

    # --------------------------
    # VISÃO DIÁRIA POR VENDEDOR
    # --------------------------
    titulo_dia = pd.to_datetime(dia_sel).strftime("%A").capitalize()
    st.subheader(f"🗓️ {titulo_dia} ({formato_data_br(dia_sel)})")

    calendario = (
        df_dia_total.groupby("vendedor")["valor_orcado"]
        .sum()
        .reset_index()
    )

    calendario["valor_orcado"] = calendario["valor_orcado"].apply(formato_real)

    st.dataframe(calendario, use_container_width=True)

    

elif tipo_dashboard == "Dashboard de Compras":

    st.title("📦 Dashboard de Compras")

    ORCAMENTO_COMPRAS_MENSAL = 1_000_000.00
    

    # =====================================================
    # CARREGAR BASES
    # =====================================================

    df_compras = pd.read_excel("Compras_mensais.xlsx")
    
    
    df = df_compras.copy()
    # Padronizar colunas
    df.columns = df.columns.str.strip()

    def extrair_observacao(texto):

        pagamento = None
        frete = 0
        tipo = "Regular"

        if pd.isna(texto):
            return pagamento, frete, tipo

        texto = str(texto).lower()

        # Pagamento
        pagamento_match = re.search(
            r'pagamento\s*[:\-]?\s*(\d+(?:\/\d+)*)',
            texto
        )

        if pagamento_match:
            pagamento = pagamento_match.group(1)

        # Frete
        frete_match = re.search(
            r'frete\s*[:\-]?\s*([\d\.,]+)',
            texto
        )

        if frete_match:
            frete = (
                frete_match.group(1)
                .replace(".", "")
                .replace(",", ".")
            )
            frete = float(frete)

        # Tipo
        if "emergencial" in texto:
            tipo = "Emergencial"

        return pagamento, frete, tipo
    df = df.rename(columns={
        "PEDIDO": "pedido",
        "DT PEDIDO": "data",
        "FORNECEDOR": "fornecedor",
        "VL PEDIDO": "valor"
        
    })

    # Corrigir pedido
    df["pedido"] = (
        df["pedido"]
        .astype(str)
        .str.replace(".", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.replace(".0", "", regex=False)
        .str.strip()
    )

    # Converter tipos
    df["data"] = pd.to_datetime(df["data"])

    df["valor"] = pd.to_numeric(
        df["valor"],
        errors="coerce"
    ).fillna(0)

    df[["pagamento_obs","frete_obs","tipo_compra"]] = (
        df["OBSERVAÇÃO"]
        .apply(lambda x: pd.Series(extrair_observacao(x)))
    )

    df["condicao"] = np.where(
        df["pagamento_obs"].notna(),
        df["pagamento_obs"],
        "0"
    )

    

    # =====================================================
    # 💰 CONSOLIDAR PEDIDOS
    # =====================================================

    df_pedidos = (
        df.groupby(
            ["pedido", "fornecedor", "data", "condicao"]
        )["valor"]
        .sum()
        .reset_index()
    )

    

    # =====================================================
    # 💰 EXPLODIR CONDIÇÃO DE PAGAMENTO
    # =====================================================

    registros = []

    for _, row in df_pedidos.iterrows():
    
        pedido = row["pedido"]
        fornecedor = row["fornecedor"]
        data_pedido = pd.to_datetime(row["data"])
        valor_total = row["valor"]

        condicao = str(row["condicao"]).strip().upper()

        # =====================================================
        # IGNORAR PEDIDOS À VISTA
        # =====================================================

        if condicao in [
            "0",
            "0/0",
            "À VISTA",
            "A VISTA",
            "AVISTA",
            "",
            "NONE",
            "NAN"
        ]:
            continue

        parcelas = [
            int(float(p.strip()))
            for p in condicao.split("/")
            if p.strip() != ""
        ]

        if len(parcelas) == 0:
            continue

        qtd_parcelas = len(parcelas)

        if qtd_parcelas == 0:
            parcelas = [30]
            qtd_parcelas = 1

        valor_parcela = valor_total / qtd_parcelas

        for i, dias in enumerate(parcelas):

            vencimento = data_pedido + pd.Timedelta(days=dias)

            registros.append({
                "pedido": pedido,
                "fornecedor": fornecedor,
                "data_pedido": data_pedido,
                "parcela": i + 1,
                "vencimento": vencimento,
                "valor": valor_parcela
            })


    df_pagamentos = pd.DataFrame(registros)

    from datetime import timedelta

    provisao_fornecedor = []

    for _, row in df.iterrows():

        pedido = row["pedido"]
        fornecedor = row["fornecedor"]
        valor = row["valor"]
        condicao = row["condicao"]
        data = row["data"]

        try:
            parcelas = [int(x) for x in str(condicao).split("/") if x.strip()]
        except:
            parcelas = [0]

        valor_parcela = valor / len(parcelas)

        for dias in parcelas:

            data_vencimento = pd.to_datetime(data) + timedelta(days=int(dias))

            provisao_fornecedor.append({
                "pedido": pedido,
                "fornecedor": fornecedor,
                "valor": valor_parcela,
                "data_vencimento": data_vencimento
            })

    


    df_provisao_fornecedor = pd.DataFrame(provisao_fornecedor)

    df_provisao_fornecedor["mes"] = (
        pd.to_datetime(df_provisao_fornecedor["data_vencimento"])
        .dt.to_period("M")
        .astype(str)
    )

    pagamento_fornecedor = (
        df_provisao_fornecedor
        .groupby(["mes","fornecedor"])["valor"]
        .sum()
        .reset_index()
    )

    lista_fornecedores = sorted(
        pagamento_fornecedor["fornecedor"]
        .dropna()
        .unique()
    )

    fornecedores_selecionados = st.multiselect(
        "🏢 Filtrar Fornecedor",
        lista_fornecedores,
        default=lista_fornecedores
    )

    pagamento_fornecedor_filtrado = pagamento_fornecedor[
        pagamento_fornecedor["fornecedor"].isin(fornecedores_selecionados)
    ]

    fig_fornecedor = px.bar(
        pagamento_fornecedor_filtrado,
        x="mes",
        y="valor",
        color="fornecedor",
        title="🏢 Previsão de Pagamento por Fornecedor"
    )

    fig_fornecedor.update_traces(
        hovertemplate=
        "<b>Mês:</b> %{x}<br>" +
        "<b>Fornecedor:</b> %{fullData.name}<br>" +
        "<b>Valor:</b> R$ %{y:,.2f}<extra></extra>"
    )

    st.plotly_chart(
        fig_fornecedor,
        use_container_width=True
    )

    
    # =====================================================
    # CRIAR MÊS PROVISÃO
    # =====================================================

    df_pagamentos["mes"] = (
        df_pagamentos["vencimento"]
        .dt.to_period("M")
        .astype(str)
    )

    # =====================================================
    # PROVISÃO MENSAL
    # =====================================================

    pagamento_mes = (
        df_pagamentos
        .groupby("mes")["valor"]
        .sum()
        .reset_index()
    )

    # =====================================================
    # KPI MÊS ATUAL
    # =====================================================

    mes_atual = str(pd.Timestamp.today().to_period("M"))

    valor_mes_atual = pagamento_mes[
        pagamento_mes["mes"] == mes_atual
    ]["valor"].sum()

    # =====================================================
    # KPI MÊS ATUAL
    # =====================================================

    mes_atual = str(pd.Timestamp.today().to_period("M"))

    valor_mes_atual = pagamento_mes[
        pagamento_mes["mes"] == mes_atual
    ]["valor"].sum()

    saldo_disponivel = ORCAMENTO_COMPRAS_MENSAL - valor_mes_atual

    k1, k2, k3 = st.columns(3)

    k1.metric(
        "💰 Previsão Pagamento Mês",
        formato_real(valor_mes_atual)
    )

    k2.metric(
        "🎯 Orçamento Compras Mês",
        formato_real(ORCAMENTO_COMPRAS_MENSAL)
    )

    cor = "normal" if saldo_disponivel >= 0 else "inverse"

    k3.metric(
        "📉 Saldo Disponível",
        formato_real(saldo_disponivel),
        delta=formato_real(saldo_disponivel),
        delta_color=cor
    )

    # =====================================================
    # GRÁFICO PROVISÃO
    # =====================================================

    import plotly.express as px

    fig = px.bar(
        pagamento_mes,
        x="mes",
        y="valor",
        title="💰 Provisão de Pagamento por Mês"
    )

    fig.update_traces(
        hovertemplate=
        "<b>Mês:</b> %{x}<br>" +
        "<b>Valor:</b> R$ %{y:,.2f}<extra></extra>"
    )

    fig.update_layout(
        yaxis=dict(
            tickprefix="R$ ",
            separatethousands=True
        )
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        key="grafico_pagamento_mensal"
    )


    # =====================================================
    # TRATAMENTO BASE COMPRAS
    # =====================================================

    df_compras = df_compras.rename(columns={
        "PEDIDO": "pedido",
        "DT PEDIDO": "data",
        "FORNECEDOR": "fornecedor",
        "Descrição": "descricao",
        "VL PEDIDO": "valor_total"
    })

    df_compras.columns = [c.lower().strip() for c in df_compras.columns]

    df_compras["data"] = pd.to_datetime(
        df_compras["data"], errors="coerce"
    ).dt.date

    # remover datas inválidas
    df_compras = df_compras.dropna(subset=["data"])

    df_compras["valor_total"] = pd.to_numeric(
        df_compras["valor_total"], errors="coerce"
    ).fillna(0)

    df_compras["fornecedor"] = (
        df_compras["fornecedor"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    print(df_pagamentos.head(10))
    print(
        df_pagamentos[
            df_pagamentos["mes"] == mes_atual
        ]["valor"].sum()
    )
    print(df_pagamentos["valor"].sum())

    
    # =====================================================
    # JUNTAR BASES
    # =====================================================

    df["tipo_compra"] = df["tipo_compra"].fillna("Regular")

    # Limpar nomes das colunas
    df_compras.columns = df_compras.columns.str.strip()
    

    # Renomear corretamente
    df_compras.rename(columns={"Nr Pedido": "pedido"}, inplace=True)

    

    # Padronizar nomes das colunas
    df_compras.columns = (
        df_compras.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )

    

    # limpar colunas
    df_compras.columns = df_compras.columns.str.strip()

    # renomear
    df_compras = df_compras.rename(columns={
        "Nr Pedido": "pedido",
        "Nr  Pedido": "pedido"
    })

    # converter
    df_compras["pedido"] = (
        df_compras["pedido"]
        .astype(str)
        .str.replace(".0", "", regex=False)
        .str.strip()
    )
    

    df_compras["pedido"] = (
        df_compras["pedido"]
        .astype(str)
        .str.replace(".0", "", regex=False)
        .str.strip()
    )

    

    
 

    frete_por_pedido = (
        df.groupby("pedido")["frete_obs"]
        .sum()
    .   reset_index()
    )

    df = df.merge(
        frete_por_pedido,
        on="pedido",
        how="left",
        suffixes=("","_pedido")
    )

    df["valor"] = df["valor"] + df["frete_obs_pedido"].fillna(0)

    
    from datetime import timedelta

    provisao = []

    for _, row in df.iterrows():

        pedido = row["pedido"]
        fornecedor = row["fornecedor"]
        valor = row["valor"]
        condicao = row["condicao"]
        data_emissao = pd.to_datetime(row["data"])  # ← GARANTE USO DA DT PEDIDO
        tipo = row["tipo_compra"]

        try:
            parcelas = [int(x) for x in str(condicao).split("/") if x.strip()]
        except:
            parcelas = [0]

        valor_parcela = valor / len(parcelas)

        for i, dias in enumerate(parcelas):

            data_vencimento = (
            pd.to_datetime(data_emissao)
            + timedelta(days=int(dias))
        )

        provisao.append({
            "pedido": pedido,
            "fornecedor": fornecedor,
            "parcela": i + 1,
            "valor": valor_parcela,
            "tipo": tipo,
            "data_vencimento": data_vencimento
        })

    df_pagamentos = pd.DataFrame(provisao)

    # =====================================================
    # 📅 CONTROLE DE JANELA IDEAL DE VENCIMENTO
    # =====================================================

    #def classificar_vencimento(data):
        #dia = pd.to_datetime(data).day

        #if 5 <= dia <= 20:
            #return "🟢 Ideal (05-20)"
        #else:
            #return "🔴 Fora da Janela (21-04)"

    #df_pagamentos["status_vencimento"] = (
        #df_pagamentos["data_vencimento"]
        #.apply(classificar_vencimento)
    #)

    #valor_ideal = df_pagamentos[
        #df_pagamentos["status_vencimento"]
        #== "🟢 Ideal (05-20)"
    #]["valor"].sum()

    #valor_fora = df_pagamentos[
        #df_pagamentos["status_vencimento"]
        #== "🔴 Fora da Janela (21-04)"
    #]["valor"].sum()

    #percentual_fora = (
        #(valor_fora / (valor_ideal + valor_fora)) * 100
        #if (valor_ideal + valor_fora) > 0 else 0
    #)

    #st.divider()
    #st.header("📅 Controle de Janela Ideal de Vencimentos")

    #k1, k2, k3 = st.columns(3)

    #k1.metric(
        #"🟢 Dentro da Janela",
        #formato_real(valor_ideal)
    #)

    #k2.metric(
        #"🔴 Fora da Janela",
        #formato_real(valor_fora)
    #)

    #k3.metric(
        #"⚠️ % Fora da Política",
        #f"{percentual_fora:.2f}%"
    #)

    #tabela_vencimentos = df_pagamentos.copy()

    #tabela_vencimentos["data_vencimento"] = (
        #pd.to_datetime(tabela_vencimentos["data_vencimento"])
    #.dt.strftime("%d/%m/%Y")
    #)

    #tabela_vencimentos["Valor"] = (
        #tabela_vencimentos["valor"]
        #.apply(formato_real)
    #)

    #st.dataframe(
        #tabela_vencimentos[
            #[
                #"pedido",
                #"fornecedor",
                #"parcela",
                #"data_vencimento",
                #"Valor",
                #"status_vencimento"
            #]
        #],
        #use_container_width=True,
        #hide_index=True
    #)

    

    #df_provisao = pd.DataFrame(provisao)

    #df_provisao["mes"] = (
        #pd.to_datetime(df_provisao["data_vencimento"])
        #.dt.to_period("M")
        #.astype(str)
    #)

    #provisao_mensal = (
        #df_provisao.groupby("mes")["valor"]
        #.sum()
        #.reset_index()
    #)

    # =====================================================
    # 📅 GARANTIR DATA COMO DATETIME
    # =====================================================

    df["data"] = pd.to_datetime(
        df["data"],
        errors="coerce",
        dayfirst=True
    )
    

    # =====================================================
    # 📅 DATAS PADRÃO
    # =====================================================

    from datetime import datetime

    hoje = datetime.today()
    primeiro_dia_mes = hoje.replace(day=1).date()
    data_hoje = hoje.date()

    

    # =====================================================
    # 📈 COMPRAS POR DIA (REGULAR X EMERGENCIAL)
    # =====================================================

    st.divider()
    st.header("📅 Acompanhamento Diário")

    # =====================================================
    # 📅 FILTRO PERÍODO DIÁRIO
    # =====================================================

    col1, col2 = st.columns(2)

    with col1:
        data_inicio = st.date_input(
            "Data Início",
            value=primeiro_dia_mes
        )

    with col2:
        data_fim = st.date_input(
            "Data Fim",
            value=data_hoje
        )

    # =====================================================
    # 📊 FILTRO BASE DIÁRIA
    # =====================================================

    df_diario = df[
        (df["data"] >= pd.to_datetime(data_inicio)) &
        (df["data"] <= pd.to_datetime(data_fim))
    ]

    compras_dia = (
        df_diario.groupby(["data", "tipo_compra"])["valor"]
        .sum()
        .reset_index()
    )

    fig = px.line(
        compras_dia,
        x="data",
        y="valor",
        color="tipo_compra",
        markers=True
    )

    fig.update_traces(
        hovertemplate=
        "<b>Tipo:</b> %{legendgroup}<br>" +
        "<b>Data:</b> %{x}<br>" +
        "<b>Valor:</b> R$ %{y:,.2f}<extra></extra>"
)

    fig.update_layout(
        legend_title="Tipo de Compra",
        xaxis_title="Data",
        yaxis_title="Valor Comprado"
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        key="grafico_compras_dia_1"
    )

    

    # =====================================================
    # 💰 KPI DO DIA
    # =====================================================

    total_dia = df_diario["valor"].sum()

    emergencial_dia = df_diario[
        df_diario["tipo_compra"] == "Emergencial"
        ]["valor"].sum()

    regular_dia = df_diario[
        df_diario["tipo_compra"] == "Regular"
    ]["valor"].sum()

    k1, k2, k3 = st.columns(3)

    k1.metric("💰 Total", formato_real(total_dia))
    k2.metric("🚨 Emergencial", formato_real(emergencial_dia))
    k3.metric("📦 Regular", formato_real(regular_dia))

    

    st.markdown(
        f"📅 Período: {formato_data_br(data_inicio)} até {formato_data_br(data_fim)}"
    )

    # Agrupar fornecedor
    compras_fornecedor = (
        df_diario.groupby("fornecedor")["valor"]
        .sum()
        .reset_index()
        .sort_values("valor", ascending=False)
    )

    # Gráfico
    fig = px.bar(
        compras_fornecedor,
        x="fornecedor",
        y="valor",
        text="valor"
    )

    fig.update_traces(
        texttemplate="R$ %{y:,.2f}",
        hovertemplate=
        "<b>Fornecedor:</b> %{x}<br>" +
        "<b>Valor:</b> R$ %{y:,.2f}<extra></extra>"
    )

    

    
    # =====================================================
    # 🏆 RANKING FORNECEDOR (TABELA)
    # =====================================================

    st.subheader("🏆 Ranking por Fornecedor")

    ranking = (
        df_diario.groupby("fornecedor")["valor"]
        .sum()
        .reset_index()
        .sort_values("valor", ascending=False)
    )

    ranking["Valor Comprado"] = ranking["valor"].apply(formato_real)

    ranking["Ranking"] = range(1, len(ranking) + 1)

    ranking = ranking[
        ["Ranking", "fornecedor", "Valor Comprado"]
    ]

    ranking.columns = [
        "Posição",
        "Fornecedor",
        "Valor Comprado"
    ]

    st.dataframe(
        ranking,
        use_container_width=True,
        hide_index=True
    ) 

    # =====================================================
    # 🚨 REGULAR X EMERGENCIAL
    # =====================================================

    st.subheader("🚨 Compras Regulares vs Emergenciais")

    tipo = (
        df_diario.groupby("tipo_compra")["valor"]
        .sum()
        .reset_index()
    )

    fig = px.pie(
        tipo,
        names="tipo_compra",
        values="valor"
    )

    fig.update_traces(
        hovertemplate=
        "<b>%{label}</b><br>" +
        "Valor: R$ %{value:,.2f}<br>" +
        "Percentual: %{percent}<extra></extra>"
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        key="grafico_emergencial"
    )
