import streamlit as st
import pandas as pd
from datetime import datetime


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
        "NF-e  Emissão": "data",
        "Vendedor": "vendedor",
        "Produto": "produto",
        "Quantidade": "quantidade",
        "Valor  Unitário": "valor_unitario"
    })

    df.columns = [c.lower().strip() for c in df.columns]

    df["data"] = pd.to_datetime(df["data"]).dt.date
    df["quantidade"] = df["quantidade"].astype(float)
    df["valor_unitario"] = df["valor_unitario"].astype(float)
    df["valor_total"] = df["quantidade"] * df["valor_unitario"]

    return df

# =====================================================
# SIDEBAR
# =====================================================
st.sidebar.title("📊 Relatórios")

if perfil == "admin":
    tipo_dashboard = st.sidebar.radio(
        "Selecione o Dashboard",
        ["Dashboard Mensal", "Orçamentos em Aberto"]
    )
else:
    tipo_dashboard = "Dashboard Mensal"
    st.sidebar.info("Acesso restrito ao Dashboard Mensal")

# =====================================================
# DASHBOARD MENSAL (ATUALIZADO)
# =====================================================
if tipo_dashboard == "Dashboard Mensal":
    st.title("📊 Dashboard Mensal de Vendas")

    df = preparar_base(pd.read_excel("vendas.xlsx"))

    df_frete = pd.read_excel("frete.xlsx")
    df_frete.columns = [c.lower().strip() for c in df_frete.columns]
    df_frete["receita_frete"] = df_frete["receita_frete"].astype(float)

    frete_por_vendedor = (
        df_frete.groupby("vendedor")["receita_frete"].sum().reset_index()
    )

    c1, c2 = st.columns(2)
    data_inicio = c1.date_input("Data inicial", min(df["data"]))
    data_fim = c2.date_input("Data final", max(df["data"]))

    df = df[(df["data"] >= data_inicio) & (df["data"] <= data_fim)]

    total_vendas = df["valor_total"].sum()
    total_frete = frete_por_vendedor["receita_frete"].sum()

    k1, k2, k3 = st.columns(3)
    k1.metric("💰 Total de Vendas", formato_real(total_vendas))
    k2.metric("🚚 Frete Total", formato_real(total_frete))
    k3.metric("🎯 Meta Mensal", formato_real(META_MENSAL))

    # -------- VENDAS POR VENDEDOR --------
    st.subheader("👤 Vendas por Vendedor")

    vendas_vendedor = (
        df.groupby("vendedor")["valor_total"]
        .sum()
        .reset_index()
    )

    vendas_vendedor = vendas_vendedor.merge(
        frete_por_vendedor, on="vendedor", how="left"
    ).fillna(0)

    vendas_vendedor["% Frete / Vendas"] = (
        vendas_vendedor["receita_frete"] / vendas_vendedor["valor_total"] * 100
    ).fillna(0)

    vendas_vendedor["Vendas"] = vendas_vendedor["valor_total"].apply(formato_real)
    vendas_vendedor["Frete Cobrado"] = vendas_vendedor["receita_frete"].apply(formato_real)
    vendas_vendedor["% Frete / Vendas"] = vendas_vendedor["% Frete / Vendas"].apply(
        lambda x: f"{x:.2f}%"
    )

    st.dataframe(
        vendas_vendedor[
            ["vendedor", "Vendas", "Frete Cobrado", "% Frete / Vendas"]
        ],
        use_container_width=True
    )

    # -------- VENDAS DIÁRIAS (SELEÇÃO POR DATA) --------
    st.subheader("📅 Vendas do Dia")

    dia_sel = st.selectbox(
        "Selecione a data",
        sorted(df["data"].unique())
    )

    df_dia = df[df["data"] == dia_sel]

    titulo_dia = pd.to_datetime(dia_sel).strftime("%A").capitalize()
    st.markdown(f"### 🗓️ {titulo_dia} ({formato_data_br(dia_sel)})")

    vendas_dia = (
        df_dia.groupby("vendedor")["valor_total"]
        .sum()
        .reset_index()
    )

    vendas_dia["valor_total"] = vendas_dia["valor_total"].apply(formato_real)

    st.dataframe(vendas_dia, use_container_width=True)


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

    # --------------------------
    # TOTAIS
    # --------------------------
    total_geral_orcamentos = df_orc["valor_orcado"].sum()

    dia_sel = st.selectbox(
        "Selecione o dia",
        sorted(df_orc["data"].unique())
    )

    df_dia = df_orc[df_orc["data"] == dia_sel]
    total_dia_orcamentos = df_dia["valor_orcado"].sum()

    k1, k2 = st.columns(2)
    k1.metric("💰 Total Geral de Orçamentos", formato_real(total_geral_orcamentos))
    k2.metric("📅 Total do Dia", formato_real(total_dia_orcamentos))

    # --------------------------
    # VISÃO DIÁRIA POR VENDEDOR
    # --------------------------
    titulo_dia = pd.to_datetime(dia_sel).strftime("%A").capitalize()
    st.subheader(f"🗓️ {titulo_dia} ({formato_data_br(dia_sel)})")

    calendario = (
        df_dia.groupby("vendedor")["valor_orcado"]
        .sum()
        .reset_index()
    )

    calendario["valor_orcado"] = calendario["valor_orcado"].apply(formato_real)

    st.dataframe(calendario, use_container_width=True)
