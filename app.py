import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
from google.auth.exceptions import RefreshError, TransportError
import os
import json
import unicodedata

# ==============================================================================
# 0. CONFIGURAÇÃO DE CAMINHOS
# ==============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_CREDENCIAIS = os.path.join(BASE_DIR, "service_account.json")
ARQUIVO_CONTEXTO = os.path.join(BASE_DIR, "dados_turmas_2025.csv")

# ==============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ==============================================================================
st.set_page_config(
    page_title="CAfe.Lab | Analisar & Acolher",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo Visual (CSS)
st.markdown("""
<style>
    .main { background-color: #fcfcfc; }
    h1, h2, h3 { color: #e95420; font-family: 'Segoe UI', sans-serif; }
    .stButton>button { background-color: #e95420; color: white; border-radius: 6px; border: none; }
    .stButton>button:hover { background-color: #d04312; color: white; }
    
    /* Carousel Styles */
    .carousel-container {
        display: flex;
        overflow-x: auto;
        gap: 20px;
        padding: 20px 5px;
        scroll-behavior: smooth;
        -webkit-overflow-scrolling: touch;
        margin-bottom: 20px;
    }
    .carousel-card {
        min-width: 300px;
        max-width: 320px;
        flex: 0 0 auto;
        background-color: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        border-left: 6px solid #ccc;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .carousel-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 16px rgba(0,0,0,0.12);
    }
    .carousel-card h4 {
        margin: 0 0 10px 0;
        color: #444;
        font-size: 1.1rem;
        border-bottom: 1px solid #eee;
        padding-bottom: 5px;
    }
    
    /* Status Colors */
    .status-success { border-left-color: #28a745 !important; } 
    .status-warning { border-left-color: #ffc107 !important; } 
    .status-danger { border-left-color: #dc3545 !important; }  
    .status-info { border-left-color: #17a2b8 !important; }    
    .status-secondary { border-left-color: #ccc !important; }
    
    /* Scrollbar */
    .carousel-container::-webkit-scrollbar { height: 8px; }
    .carousel-container::-webkit-scrollbar-track { background: #f0f0f0; border-radius: 4px; }
    .carousel-container::-webkit-scrollbar-thumb { background: #ccc; border-radius: 4px; }
    .carousel-container::-webkit-scrollbar-thumb:hover { background: #bbb; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. CONSTANTES (REGRAS DE NEGÓCIO)
# ==============================================================================
IDS_PLANILHAS = {
  "711": "1HMjzbAKyDCvJh9CO8T2isGA04EjVoHlCgnzgu-s1mh0",
  "712": "1b_39FjRINpB6ybTrHZ1-j41CBzHqYIOozx_4RtUY9bY",
  "713": "17u8yE9tIieA7VsojilEJXANirXjKceF80y3AXzBXORo",
  "621": "16s2R-poDNNnd2SMwuq5HIsRmD8ax1J4nI2AABi-bCs4",
  "624": "1Q0yiIRIgsnLAytPVRtwe8_-RbRILRb2-HUEsztc89Rk"
}

NIVEL_BIMESTRE = ["1º Bimestre", "2º Bimestre", "3º Bimestre", "4º Bimestre"]

MAXIMOS = {
    "1º Bimestre": {"AV1": 5, "AV2": 5, "AV3": 10, "Nota Global": 20, "Nota Global Acumulada": 20},
    "2º Bimestre": {"AV1": 5, "AV2": 5, "AV3": 10, "Nota Global": 20, "Nota Global Acumulada": 40},
    "3º Bimestre": {"AV1": 5, "AV2": 10, "AV3": 15, "Nota Global": 30, "Nota Global Acumulada": 70},
    "4º Bimestre": {"AV1": 5, "AV2": 10, "AV3": 15, "Nota Global": 30, "Nota Global Acumulada": 100},
}

LIMITES_RUINS = {
    "1º Bimestre": {"AV1": 2.5, "AV2": 2.5, "AV3": 5},
    "2º Bimestre": {"AV1": 2.5, "AV2": 2.5, "AV3": 5},
    "3º Bimestre": {"AV1": 2.5, "AV2": 5,   "AV3": 7.5},
    "4º Bimestre": {"AV1": 2.5, "AV2": 5,   "AV3": 7.5},
}

MAPA_INDICADORES = {
    "numero_aulas": "Número de Aulas", "numero_faltas": "Número de Faltas",
    "percentual_presencas": "Percentual de Presenças", "atencao_abandono": "Atenção / Abandono",
    "nota_maxima_av1": "AV1 – Nota Máxima", "notaav1_media_percentual": "AV1 – Média Percentual",
    "notaav1": "AV1 – Nota Final", 
    "quizz1": "Quizz 1", "quizz2": "Quizz 2", "quizz3": "Quizz 3",
    "quizz": "Quizz – Total",
    "atividade_ucs": "Atividade UCs", "atividade_folha": "Atividade (Folha)",

    "memorias_quilombo": "Memórias do Quilombo", "maquete": "Maquete",
    "atividade_passeio": "Atividade do Passeio",
    "fez_quizz1": "Fez Quizz 1", "fez_quizz2": "Fez Quizz 2",
    "fez_quizz3": "Fez Quizz 3", "fez_uc": "Fez UCs",
    "fez_folha": "Fez Folha", "fez_memorias": "Fez Memórias",
    "fez_maquete": "Fez Maquete", "fez_atividade_passeio": "Fez Atividade do Passeio",
    "percentual_atividades_feitas_av2": "AV2 – % de Atividades Feitas",
    "nota_maxima_av2": "AV2 – Nota Máxima", "notaav2_media_percentual": "AV2 – Média Percentual",
    "notaav2": "AV2 – Nota Final", "nota_maxima_av3": "AV3 – Nota Máxima",
    "notaav3": "AV3 – Nota Final", "percentual_acertos_saem": "SAEM – % Acertos",
    "nota_global": "Nota Global", "nota_global_acumulada": "Nota Global Acumulada",
}

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================
def status_cor(valor, indicador, bimestre):
    if pd.isna(valor): return "secondary"
    
    chave = "Nota Global" if "Nota Global" in indicador else \
            "AV1" if "AV1" in indicador else \
            "AV2" if "AV2" in indicador else \
            "AV3" if "AV3" in indicador else None
            
    if not chave: return "secondary"
    
    mx = MAXIMOS.get(bimestre, {}).get(chave, 10)
    
    if valor < (mx * 0.5): return "danger"
    if valor >= (mx * 0.8): return "success"
    return "warning"

def get_base_larga(df):
    cols_ignorar = ["tipoindicador", "Valor"]
    index_cols = [c for c in df.columns if c not in cols_ignorar]
    
    # Preencher NaNs em colunas de índice para evitar perda de linhas no pivot
    for c in index_cols:
        if pd.api.types.is_numeric_dtype(df[c]):
            df[c] = df[c].fillna(0)
        else:
            df[c] = df[c].fillna("")
            
    df_pivot = df.pivot_table(index=index_cols, columns="tipoindicador", values="Valor", aggfunc='first').reset_index()
    return df_pivot

def normalizar_nome(x):
    if not isinstance(x, str): return ""
    text = x.lower().strip()
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8')
    return "".join(c for c in text if c.isalnum() or c.isspace()).strip()

# ==============================================================================
# 3. CARREGAMENTO DE DADOS
# ==============================================================================
@st.cache_data(ttl=600)
def carregar_dados_v5():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    credentials = None
    
    try:
        if "gsheets" in st.secrets:
            credentials = Credentials.from_service_account_info(st.secrets["gsheets"], scopes=scopes)
    except: pass
        
    if not credentials and os.path.exists(ARQUIVO_CREDENCIAIS):
        try:
            credentials = Credentials.from_service_account_file(ARQUIVO_CREDENCIAIS, scopes=scopes)
        except Exception as e:
            st.error(f"Erro credenciais locais: {e}")
            st.stop()
    
    if not credentials:
        st.error("Credenciais não encontradas.")
        st.stop()

    client = gspread.authorize(credentials)
    lista_dfs = []
    prog_bar = st.progress(0)

    for i, (turma, sheet_id) in enumerate(IDS_PLANILHAS.items()):
        try:
            sh = client.open_by_key(sheet_id)
            ws = sh.get_worksheet(0)
            all_values = ws.get_all_values()
            
            if not all_values: continue

            headers = [str(c).lower().strip() for c in all_values[0]]
            rows = all_values[1:]
            df_temp = pd.DataFrame(rows, columns=headers)
            df_temp = df_temp.loc[:, ~df_temp.columns.duplicated()]
            
            if 'turma' in df_temp.columns: df_temp = df_temp.drop(columns=['turma'])
            df_temp["turma"] = str(turma)
            lista_dfs.append(df_temp)
        except Exception as e:
            st.warning(f"Erro turma {turma}: {e}")
            
        prog_bar.progress((i + 1) / len(IDS_PLANILHAS))

    if not lista_dfs:
        st.error("Nenhuma planilha carregada.")
        st.stop()
        
    df_bruto = pd.concat(lista_dfs, ignore_index=True)
    prog_bar.empty()
    
    # DEBUG: Verificar colunas carregadas
    # st.write("Colunas encontradas:", df_bruto.columns.tolist())
    
    sufixos = {"_primeirobi": "1º Bimestre", "_segundobi": "2º Bimestre", "_terceirobi": "3º Bimestre", "_quartobi": "4º Bimestre"}
    cols_fixas = [c for c in ["nome_estudante", "turma"] if c in df_bruto.columns]
    if "turma" not in cols_fixas and "turma" in df_bruto.columns: cols_fixas.append("turma")
    
    cols_para_melt = []
    for col in df_bruto.columns:
        for suf in sufixos.keys():
            if col.endswith(suf):
                cols_para_melt.append(col)
                break
    
    # DEBUG: Verificar colunas para melt
    # st.write("Colunas para melt:", cols_para_melt)
    
    cols_para_melt = [c for c in cols_para_melt if not c.startswith("av1_c.") and "xpclassmana" not in c]

    df_long = df_bruto.melt(id_vars=cols_fixas, value_vars=cols_para_melt, var_name="indicador_cru", value_name="Valor")
    
    def processar_linha(row):
        cru = row["indicador_cru"]
        for suf, nome_bim in sufixos.items():
            if cru.endswith(suf):
                ind_limpo = cru.replace(suf, "")
                nome_final = MAPA_INDICADORES.get(ind_limpo, ind_limpo.replace("_", " ").title())
                return pd.Series([nome_final, nome_bim])
        return pd.Series([cru, None])

    result = df_long.apply(processar_linha, axis=1)
    df_long["tipoindicador"] = result[0]
    df_long["bimestre"] = result[1]
    df_long = df_long.drop(columns=["indicador_cru"])
    
    df_final = df_long
    df_final["turma"] = df_final["turma"].astype(str)
    
    ID_CONTEXTO = "1iR5M6PKHGDyoKUMEXFSWHxKCSUPBamREQ7J1es"
    df_ctx = pd.DataFrame()

    try:
        sh_ctx = client.open_by_key(ID_CONTEXTO)
        ws_ctx = sh_ctx.get_worksheet(0)
        df_ctx = pd.DataFrame(ws_ctx.get_all_records())
    except:
        if os.path.exists(ARQUIVO_CONTEXTO):
            try: df_ctx = pd.read_csv(ARQUIVO_CONTEXTO, encoding='utf-8')
            except: pass
    
    if not df_ctx.empty:
        df_ctx.columns = [str(c).lower().strip() for c in df_ctx.columns]
        df_ctx["chave_estudante"] = df_ctx["nome_estudante"].apply(normalizar_nome)
        df_ctx["turma"] = df_ctx["turma"].astype(str)
        df_final["chave_estudante"] = df_final["nome_estudante"].apply(normalizar_nome)
        
        cols_drop = [c for c in ["nome_estudante", "tipoindicador", "bimestre"] if c in df_ctx.columns]
        df_ctx_clean = df_ctx.drop(columns=cols_drop)
        df_merged = pd.merge(df_final, df_ctx_clean, on=["chave_estudante", "turma"], how="left")
        
        if "turma" in df_merged.columns: df_final = df_merged
        elif "turma_x" in df_merged.columns: df_final = df_merged.rename(columns={"turma_x": "turma"})
        if "tipoindicador" not in df_final.columns and "tipoindicador_x" in df_final.columns:
            df_final = df_final.rename(columns={"tipoindicador_x": "tipoindicador"})
        df_final = df_final.drop(columns=["chave_estudante"], errors='ignore')

    def clean_number(x):
        if isinstance(x, str): return x.replace(',', '.')
        return x

    df_final["Valor"] = df_final["Valor"].apply(clean_number)
    df_final["Valor"] = pd.to_numeric(df_final["Valor"], errors="coerce")
    
    if "tipoindicador" in df_final.columns:
        mask_av3 = df_final["tipoindicador"] == "AV3 – Nota Final"
        df_av3 = df_final[mask_av3].copy()
        def calc_pct(row):
            mx = MAXIMOS.get(row["bimestre"], {}).get("AV3", 10)
            val = row["Valor"]
            return (val / mx) * 100 if pd.notna(val) and mx > 0 else 0
        df_av3["Valor"] = df_av3.apply(calc_pct, axis=1)
        df_av3["tipoindicador"] = "AV3 – Média Percentual"
        df_final = pd.concat([df_final, df_av3], ignore_index=True)

    INDICADORES_PERCENTUAIS = ["Percentual de Presenças", "AV2 – % de Atividades Feitas", "AV1 – Média Percentual", "AV2 – Média Percentual", "AV3 – Média Percentual"]
    if "tipoindicador" in df_final.columns:
        mask_pct = df_final["tipoindicador"].isin(INDICADORES_PERCENTUAIS)
        df_final.loc[mask_pct, "Valor"] = df_final.loc[mask_pct, "Valor"].apply(lambda x: x*100 if pd.notna(x) and x <= 1.05 else x)

    for col in ["sdq_total", "gad7_total"]:
        if col in df_final.columns: df_final[col] = pd.to_numeric(df_final[col], errors='coerce')

    if "sdq_total" in df_final.columns:
        conditions = [df_final["sdq_total"] <= 14, df_final["sdq_total"] <= 16, df_final["sdq_total"] >= 17]
        df_final["sdq_total_cat"] = np.select(conditions, ["Normal (≤14)", "Limítrofe (15–16)", "Anormal (≥17)"], default=None)

    if "gad7_total" in df_final.columns:
        conditions = [df_final["gad7_total"] <= 4, df_final["gad7_total"] <= 9, df_final["gad7_total"] <= 14, df_final["gad7_total"] >= 15]
        df_final["gad7_total_cat"] = np.select(conditions, ["Mínima (0–4)", "Leve (5–9)", "Moderada (10–14)", "Grave (15–21)"], default=None)
    
    def corrigir_escala_row(row):
        val = row["Valor"]
        if pd.isna(val): return val
        bim, ind = row["bimestre"], row["tipoindicador"]
        chave_max = "Nota Global Acumulada" if "Nota Global Acumulada" in ind else "Nota Global" if "Nota Global" in ind else "AV1" if "AV1" in ind and "Nota Final" in ind else "AV2" if "AV2" in ind and "Nota Final" in ind else "AV3" if "AV3" in ind and "Nota Final" in ind else "AV3" if "AV3" in ind and "Nota Final" in ind else None
        if not chave_max: return val
        max_permitido = MAXIMOS.get(bim, {}).get(chave_max)
        if not max_permitido: return val
        if val > max_permitido * 1.1:
            if (val / 10) <= max_permitido * 1.1: return val / 10
            elif (val / 100) <= max_permitido * 1.1: return val / 100
        return val
    
    df_final["Valor"] = df_final.apply(corrigir_escala_row, axis=1)
    return df_final

# ==============================================================================
# 4. EXECUÇÃO PRINCIPAL
# ==============================================================================
df_larga = pd.DataFrame()
try:
    with st.spinner("Processando dados..."):
        df = carregar_dados_v5()
        if df is not None and not df.empty:
            df_larga = get_base_larga(df)
        else:
            st.warning("Nenhum dado retornado.")
            st.stop()
except Exception as e:
    st.error(f"Erro no carregamento: {e}")
    st.stop()

if df.empty: st.stop()

# --- BARRA LATERAL ---
with st.sidebar:
    st.title("CAfe.Lab")
    st.markdown("**Dr. William Melo** | `v5.0 Python`")
    page = st.radio("Navegação", ["Agregado", "Individual", "Estudantes em Atenção", "Base Completa"])
    if st.button("Atualizar Dados"):
        st.cache_data.clear()
        st.rerun()

# --- AGREGADO ---
if page == "Agregado":
    st.header("📊 Análise Agregada")
    
    # Filtros
    c1, c2, c3, c4 = st.columns(4)
    
    lista_turmas = sorted(list(IDS_PLANILHAS.keys()))
    try:
        if "turma" in df.columns: lista_turmas = sorted(df["turma"].unique().astype(str).tolist())
    except: pass
        
    turmas = ["Todas"] + lista_turmas
    with c1: turma_sel = st.selectbox("Turma", turmas)
    
    inds = sorted(df["tipoindicador"].unique().tolist())
    idx = inds.index("Nota Global") if "Nota Global" in inds else 0
    with c2: ind_sel = st.selectbox("Indicador", inds, index=idx)
    
    bims = ["Todos"] + NIVEL_BIMESTRE
    with c3: bim_sel = st.selectbox("Bimestre", bims)
    
    # Identificar colunas de contexto (que não são as padrão)
    cols_padrao = ["nome_estudante", "turma", "bimestre", "tipoindicador", "Valor", "chave_estudante", "indicador_cru", "sdq_total", "gad7_total", "sdq_total_cat", "gad7_total_cat"]
    cols_contexto = [c for c in df.columns if c not in cols_padrao]
    # Filtra colunas que parecem ser metadados úteis (ex: genero, raca, etc)
    cols_contexto = sorted([c for c in cols_contexto if df[c].nunique() < 20]) # Heurística: poucas categorias
    
    with c4: desagregar_por = st.selectbox("Desagregar por", ["Nenhum"] + cols_contexto)
    
    # Filtragem
    df_filt = df[df["tipoindicador"] == ind_sel].copy()
    if turma_sel != "Todas": df_filt = df_filt[df_filt["turma"] == turma_sel]
    if bim_sel != "Todos": df_filt = df_filt[df_filt["bimestre"] == bim_sel]
    
    if not df_filt.empty:
        # Lógica de Plotagem Unificada
        st.subheader(f"Análise de {ind_sel}")
        
        # Se "Todas" as turmas, fazemos facet_col="turma"
        facet_col = "turma" if turma_sel == "Todas" else None
        
        if desagregar_por == "Nenhum":
            # --- MODO 1: SEM DESAGREGAÇÃO (PONTOS + LINHA MÉDIA NEON) ---
            
            # 1. Gráfico de Dispersão (Pontos)
            fig = px.strip(
                df_filt, 
                x="bimestre", 
                y="Valor", 
                facet_col=facet_col, 
                facet_col_wrap=3, 
                stripmode="overlay", 
                hover_data=["nome_estudante"]
            )
            
            # 2. Adicionar Linha de Média (Neon Pink)
            grp_cols = ["bimestre"]
            if turma_sel == "Todas": grp_cols.append("turma")
            
            df_media = df_filt.groupby(grp_cols)["Valor"].mean().reset_index()
            
            fig_lines = px.line(
                df_media, 
                x="bimestre", 
                y="Valor", 
                facet_col=facet_col, 
                facet_col_wrap=3,
                markers=True
            )
            
            # Estilo Neon Pink chamativo
            fig_lines.update_traces(line_color="#FF10F0", line_width=4, opacity=1)
            
            for trace in fig_lines.data:
                fig.add_trace(trace)
                
            st.plotly_chart(fig, use_container_width=True)
            
        else:
            # --- MODO 2: COM DESAGREGAÇÃO (BARRAS + TABELA) ---
            
            # Agrupamento para média por grupo
            grp_cols = ["bimestre", desagregar_por]
            if turma_sel == "Todas": grp_cols.append("turma")
            
            df_media = df_filt.groupby(grp_cols)["Valor"].mean().reset_index()
            
            # Gráfico de Barras Agrupadas
            fig = px.bar(
                df_media,
                x="bimestre",
                y="Valor",
                color=desagregar_por,
                barmode="group",
                facet_col=facet_col,
                facet_col_wrap=3,
                text_auto='.1f' # Rótulos numéricos visíveis
            )
            
            fig.update_traces(textposition='outside', textfont_size=12)
            fig.update_layout(yaxis_title="Valor Médio")
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Tabela de Diferença de Médias
            st.markdown("### 📋 Tabela de Médias por Grupo")
            
            # Pivotar para facilitar leitura (Linhas: Turma/Bimestre, Colunas: Grupos)
            idx_cols = ["bimestre"]
            if turma_sel == "Todas": idx_cols.insert(0, "turma")
            
            df_pivot = df_media.pivot_table(
                index=idx_cols, 
                columns=desagregar_por, 
                values="Valor"
            )
            
            # Formatar números
            st.dataframe(df_pivot.style.format("{:.2f}"), use_container_width=True)
    else:
        st.info("Sem dados para o filtro selecionado.")

# --- INDIVIDUAL ---
elif page == "Individual":
    st.header("👤 Análise Individual")
    c1, c2 = st.columns([1,3])
    
    lista_turmas = sorted(list(IDS_PLANILHAS.keys()))
    try:
        if "turma" in df.columns: lista_turmas = sorted(df["turma"].unique().astype(str).tolist())
    except: pass

    with c1: turma_ind = st.selectbox("Turma", ["Todas"] + lista_turmas, key="t_ind")
    
    alunos_list = df["nome_estudante"].unique()
    if turma_ind != "Todas":
        alunos_list = df[df["turma"] == turma_ind]["nome_estudante"].unique()
        
    with c2: aluno_sel = st.selectbox("Estudante", sorted(alunos_list))
    
    st.subheader("Boletim (Carrossel)")
    df_al = df_larga[df_larga["nome_estudante"] == aluno_sel]
    
    with st.expander("🔍 Ver dados brutos do estudante"):
        st.dataframe(df_al, use_container_width=True)
    
    def fmt_val(v):
        if pd.isna(v): return "-"
        try:
            return f"{float(v):.1f}"
        except:
            return str(v)

    INDICADORES_DESEJADOS = [
        "AV1 – Nota Final", "AV1 – Média Percentual",
        "AV2 – Nota Final", "AV2 – Média Percentual",
        "AV3 – Nota Final", "AV3 – Média Percentual",
        "Percentual de Presenças",
        "Nota Global", "Nota Global Acumulada"
    ]

    cards_html = '<div class="carousel-container">'

    for bim in NIVEL_BIMESTRE:
        row = df_al[df_al["bimestre"] == bim]
        
        if not row.empty:
            data = row.iloc[0]
            main_val = np.nan
            main_label = "N/A"
            
            if "Nota Global" in data and pd.notna(data["Nota Global"]):
                main_val = data["Nota Global"]
                main_label = "Nota Global"
            elif "AV3 – Nota Final" in data and pd.notna(data["AV3 – Nota Final"]):
                main_val = data["AV3 – Nota Final"]
                main_label = "AV3"
            
            cor_card = status_cor(main_val, main_label, bim)
            
            summary_html = ""
            # Filtrar indicadores para o carrossel
            display_keys = [k for k in INDICADORES_DESEJADOS if k in data.index and pd.notna(data[k])]
            
            for k in display_keys:
                summary_html += f"<div><b>{k}:</b> {fmt_val(data[k])}</div>"

            cards_html += f"""<div class="carousel-card status-{cor_card}">
                <h4>{bim}</h4>
                <div style="font-size: 1.4rem; font-weight: bold; color: #333; margin-bottom: 10px;">
                    {main_label}: {fmt_val(main_val)}
                </div>
                <div style="font-size: 0.9rem; color: #666;">
                    {summary_html}
                </div>
            </div>"""
        else:
            cards_html += f"""<div class="carousel-card status-secondary">
                <h4>{bim}</h4>
                <p style="color: #999;">Sem dados lançados.</p>
            </div>"""
            
    cards_html += '</div>'
    st.markdown(cards_html, unsafe_allow_html=True)
    
    # Gráfico Comparativo do Aluno (Um por indicador)
    st.subheader("Desempenho por Indicador")
    
    # Filtrar apenas indicadores desejados para os gráficos
    indicadores_chart = [c for c in INDICADORES_DESEJADOS if c in df_al.columns]
    
    if indicadores_chart:
        # Criar layout de colunas para os gráficos
        cols = st.columns(2) # 2 gráficos por linha
        for i, ind in enumerate(indicadores_chart):
            df_ind = df_al[["bimestre", ind]].dropna()
            if not df_ind.empty:
                # Tentar converter para numérico se não for
                try:
                    df_ind[ind] = pd.to_numeric(df_ind[ind])
                except:
                    continue # Pula se não for numérico
                
                fig = px.bar(df_ind, x="bimestre", y=ind, title=ind, text_auto=True)
                fig.update_layout(height=300)
                cols[i % 2].plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem dados numéricos para gerar gráficos.")

# --- ESTUDANTES EM ATENÇÃO ---
elif page == "Estudantes em Atenção":
    st.header("⚠️ Estudantes em Atenção")
    
    filtro_risco = st.multiselect("Critérios de Risco", 
                                  ["Nota Global Baixa", "Muitas Faltas", "SDQ Anormal", "GAD-7 Grave"],
                                  default=["Nota Global Baixa"])
    
    # Lógica de identificação de risco (simplificada)
    # Aqui você pode expandir com regras mais complexas
    
    st.info("Funcionalidade em desenvolvimento. Exibindo tabela completa por enquanto.")
    st.dataframe(df_larga)

# --- BASE COMPLETA ---
elif page == "Base Completa":
    st.header("📂 Base de Dados Completa")
    st.dataframe(df)