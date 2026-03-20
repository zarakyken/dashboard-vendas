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

    df_frete = pd.read_excel("frete.xlsx", skiprows=3)

    # Renomear colunas novas
    df_frete = df_frete.rename(columns={
        "Vendedor": "vendedor",
        "Valor Frete": "receita_frete"
    })

    

    # Padronizar
    df_frete.columns = [c.lower().strip() for c in df_frete.columns]

    # Garantir tipo numérico
    df_frete["receita_frete"] = pd.to_numeric(df_frete["receita_frete"], errors="coerce").fillna(0)

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

    

   # -------- VENDAS + FRETE + META POR VENDEDOR --------
    st.subheader("👤 Vendas, Frete e Meta por Vendedor")

    # Agrupa vendas
    vendas_vendedor = (
        df.groupby("vendedor")["valor_total"]
        .sum()
        .reset_index()
    )

    # Agrupa frete

    import re

    def limpar_vendedor(nome):
        nome = str(nome)
        nome = re.sub(r"\s*\[.*?\]", "", nome)  # remove [xxx]
        return nome.strip().upper()

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
    meta_individual = META_MENSAL / qtd_vendedores if qtd_vendedores > 0 else 0

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

    # dias úteis decorridos
    dias_passados = len(
        pd.date_range(inicio_ciclo, hoje - pd.Timedelta(days=1), freq="B")
    )

    # dias úteis restantes
    dias_restantes = len(
        pd.date_range(hoje, fim_ciclo, freq="B")
    )

    # média diária
    vendas_vendedor["media_diaria"] = vendas_vendedor["valor_total_ciclo"] / max(dias_passados,1)

    # projeção
    vendas_vendedor["projecao"] = (
        vendas_vendedor["valor_total_ciclo"] +
        vendas_vendedor["media_diaria"] * dias_restantes
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
    df_periodo = df[(df["data"] >= inicio_ciclo) & (df["data"] <= fim_ciclo)]

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

    # -------- VENDAS DIÁRIAS (SELEÇÃO POR DATA) --------
    st.subheader("📅 Vendas do Dia")

    datas_disponiveis = sorted(df["data"].unique())
    hoje = datetime.today().date()

    if hoje in datas_disponiveis:
        indice_padrao = datas_disponiveis.index(hoje)
    else:
        indice_padrao = len(datas_disponiveis) - 1

    dia_sel = st.selectbox(
        "Selecione a data",
        datas_disponiveis,
        index=indice_padrao
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
