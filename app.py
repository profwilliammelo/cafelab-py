import streamlit as st  # Biblioteca principal para criar o Web App
import pandas as pd     # A 'Excel' do Python: manipula tabelas e dados
import numpy as np      # Biblioteca matemática (cálculos numéricos rápidos)
import plotly.express as px  # Cria gráficos interativos de forma fácil
import gspread          # Conecta especificamente com o Google Sheets
from google.oauth2.service_account import Credentials # Gerencia a segurança/login do Google
from google.auth.exceptions import RefreshError, TransportError # Tratamento de erros de autenticação
import os               # Permite interagir com o sistema operacional (pastas, arquivos)
import json             # Para ler e corrigir o arquivo de senha se necessário

# ==============================================================================
# 0. CONFIGURAÇÃO DE CAMINHOS (IMPORTANTE!)
# ==============================================================================
# Define o diretório base como a pasta onde este arquivo app.py está salvo
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Montamos o caminho completo para os arquivos
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
    .cafe-card {
        background-color: white; padding: 15px; border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1); border-left: 5px solid #777; margin-bottom: 10px;
    }
    .status-success { border-left-color: #28a745 !important; } 
    .status-warning { border-left-color: #ffc107 !important; } 
    .status-danger { border-left-color: #dc3545 !important; }  
    .status-info { border-left-color: #17a2b8 !important; }    
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

# REGRAS DE NEGÓCIO: Notas máximas por bimestre
# Nota Global Acumulada soma os bimestres anteriores
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

def normalizar_nome(x):
    import unicodedata
    if not isinstance(x, str): return ""
    text = x.lower().strip()
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8')
    return "".join(c for c in text if c.isalnum() or c.isspace()).strip()


@st.cache_data(ttl=600)
def carregar_dados_v5():
    # Configuração da Autenticação do Google Sheets
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    # Autenticação: Secrets (Cloud) ou Arquivo Local (Dev)
    credentials = None
    
    try:
        if "gsheets" in st.secrets:
            credentials = Credentials.from_service_account_info(
                st.secrets["gsheets"], scopes=scopes
            )
    except:
        pass # Ignora erro de secrets se não existir (ambiente local)
        
    if not credentials:
        if os.path.exists(ARQUIVO_CREDENCIAIS):
            credentials = Credentials.from_service_account_file(
                ARQUIVO_CREDENCIAIS, scopes=scopes
            )
        else:
            st.error("❌ Credenciais não encontradas! Configure 'st.secrets' (Cloud) ou 'service_account.json' (Local).")
            st.stop()
            
    client = gspread.authorize(credentials)
    lista_dfs = []
    prog_bar = st.progress(0)

    # 3. Loop de Leitura das Planilhas
    for i, (turma, sheet_id) in enumerate(IDS_PLANILHAS.items()):
        try:
            sh = client.open_by_key(sheet_id)
            ws = sh.get_worksheet(0)
            data = ws.get_all_records()
            
            df_temp = pd.DataFrame(data)
            df_temp.columns = [str(c).lower().strip() for c in df_temp.columns]
            
            # Remove coluna turma se vier da planilha para não duplicar
            if 'turma' in df_temp.columns:
                df_temp = df_temp.drop(columns=['turma'])
                
            # Adiciona a turma explicitamente
            df_temp["turma"] = str(turma)
            
            lista_dfs.append(df_temp)
        
        except RefreshError:
            st.error(f"❌ Erro de Token (Data/Hora ou Chave) na turma {turma}.")
            st.stop()
        except Exception as e:
            st.warning(f"Aviso: Não consegui ler a turma {turma}. Erro: {e}")
            
        prog_bar.progress((i + 1) / len(IDS_PLANILHAS))
            
    if not lista_dfs:
        st.error("Nenhuma planilha carregada.")
        st.stop()
        
    df_bruto = pd.concat(lista_dfs, ignore_index=True)
    prog_bar.empty()
    
    # 4. Melt (Transformação Longa)
    sufixos = {"_primeirobi": "1º Bimestre", "_segundobi": "2º Bimestre", 
               "_terceirobi": "3º Bimestre", "_quartobi": "4º Bimestre"}
    
    cols_fixas = [c for c in ["nome_estudante", "turma"] if c in df_bruto.columns]
    
    # Garante coluna turma
    if "turma" not in cols_fixas:
        if "turma" in df_bruto.columns:
            cols_fixas.append("turma")
    
    cols_para_melt = []
    for col in df_bruto.columns:
        for suf in sufixos.keys():
            if col.endswith(suf):
                cols_para_melt.append(col)
                break
    
    if not cols_para_melt:
        st.error("Erro Crítico: Nenhuma coluna de bimestre encontrada.")
        st.stop()

    cols_para_melt = [c for c in cols_para_melt if not c.startswith("av1_c.") and "xpclassmana" not in c]

    df_long = df_bruto.melt(
        id_vars=cols_fixas,       
        value_vars=cols_para_melt,
        var_name="indicador_cru", 
        value_name="Valor"        
    )
    
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
    
    # 5. Merge com Contexto
    df_final = df_long
    df_final["turma"] = df_final["turma"].astype(str)
    
    # Leitura do Contexto (Google Sheets ou CSV Local)
    ID_CONTEXTO = "1iR5M6PKHGDyoKUMEXFSWHxKCSUPBamREQ7J1es"
    df_ctx = pd.DataFrame()

    try:
        # Tenta ler do Google Sheets
        sh_ctx = client.open_by_key(ID_CONTEXTO)
        ws_ctx = sh_ctx.get_worksheet(0)
        data_ctx = ws_ctx.get_all_records()
        df_ctx = pd.DataFrame(data_ctx)
    except Exception as e:
        # Se falhar, tenta local
        if os.path.exists(ARQUIVO_CONTEXTO):
            try:
                df_ctx = pd.read_csv(ARQUIVO_CONTEXTO, encoding='utf-8')
            except:
                try:
                    df_ctx = pd.read_csv(ARQUIVO_CONTEXTO, encoding='latin-1')
                except:
                    pass
    
    if not df_ctx.empty:
        df_ctx.columns = [str(c).lower().strip() for c in df_ctx.columns]
        
        df_ctx["chave_estudante"] = df_ctx["nome_estudante"].apply(normalizar_nome)
        df_ctx["turma"] = df_ctx["turma"].astype(str)
        
        df_final["chave_estudante"] = df_final["nome_estudante"].apply(normalizar_nome)
        
        cols_drop = [c for c in ["nome_estudante", "tipoindicador", "bimestre"] if c in df_ctx.columns]
        df_ctx_clean = df_ctx.drop(columns=cols_drop)
        
        df_merged = pd.merge(df_final, df_ctx_clean, on=["chave_estudante", "turma"], how="left")
        
        # Recuperação de Colunas Perdidas
        if "turma" in df_merged.columns:
            df_final = df_merged
        elif "turma_x" in df_merged.columns:
            df_merged = df_merged.rename(columns={"turma_x": "turma"})
            df_final = df_merged
        
        if "tipoindicador" not in df_final.columns and "tipoindicador_x" in df_final.columns:
            df_final = df_final.rename(columns={"tipoindicador_x": "tipoindicador"})

        df_final = df_final.drop(columns=["chave_estudante"], errors='ignore')
            
    # 6. Cálculos Finais (COM CORREÇÃO DE PONTO/VÍRGULA)
    def clean_number(x):
        if isinstance(x, str):
            return x.replace(',', '.')
        return x

    df_final["Valor"] = df_final["Valor"].apply(clean_number)
    df_final["Valor"] = pd.to_numeric(df_final["Valor"], errors="coerce")
    
    # AV3 %
    if "tipoindicador" in df_final.columns:
        mask_av3 = df_final["tipoindicador"] == "AV3 – Nota Final"
        df_av3 = df_final[mask_av3].copy()
        
        def calc_pct(row):
            mx = MAXIMOS.get(row["bimestre"], {}).get("AV3", 10)
            val = row["Valor"]
            if pd.isna(val): return np.nan
            return (val / mx) * 100 if mx > 0 else 0
            
        df_av3["Valor"] = df_av3.apply(calc_pct, axis=1)
        df_av3["tipoindicador"] = "AV3 – Média Percentual"
        df_final = pd.concat([df_final, df_av3], ignore_index=True)

    # Normalização de Percentuais
    INDICADORES_PERCENTUAIS = [
        "Percentual de Presenças", "AV2 – % de Atividades Feitas",
        "AV1 – Média Percentual", "AV2 – Média Percentual", "AV3 – Média Percentual"
    ]
    
    if "tipoindicador" in df_final.columns:
        mask_pct = df_final["tipoindicador"].isin(INDICADORES_PERCENTUAIS)
        def normalize_pct(val):
            if pd.isna(val): return val
            if val <= 1.05: return val * 100
            return val
        df_final.loc[mask_pct, "Valor"] = df_final.loc[mask_pct, "Valor"].apply(normalize_pct)

    # 7. Categorização SDQ / GAD
    for col in ["sdq_total", "gad7_total"]:
        if col in df_final.columns:
            df_final[col] = pd.to_numeric(df_final[col], errors='coerce')

    if "sdq_total" in df_final.columns:
        conditions = [
            df_final["sdq_total"] <= 14,
            df_final["sdq_total"] <= 16,
            df_final["sdq_total"] >= 17
        ]
        choices = ["Normal (≤14)", "Limítrofe (15–16)", "Anormal (≥17)"]
        df_final["sdq_total_cat"] = np.select(conditions, choices, default=None)

    if "gad7_total" in df_final.columns:
        conditions = [
            df_final["gad7_total"] <= 4,
            df_final["gad7_total"] <= 9,
            df_final["gad7_total"] <= 14,
            df_final["gad7_total"] >= 15
        ]
        choices = ["Mínima (0–4)", "Leve (5–9)", "Moderada (10–14)", "Grave (15–21)"]
        df_final["gad7_total_cat"] = np.select(conditions, choices, default=None)
    
    # 8. Sanitização de Outliers (Correção de Escala por Bimestre)
    def corrigir_escala_row(row):
        val = row["Valor"]
        if pd.isna(val): return val
        
        bim = row["bimestre"]
        ind = row["tipoindicador"]
        
        # Identifica qual regra de máximo usar (Ordem importa!)
        chave_max = None
        if "Nota Global Acumulada" in ind: chave_max = "Nota Global Acumulada"
        elif "Nota Global" in ind: chave_max = "Nota Global"
        elif "AV1" in ind and "Nota Final" in ind: chave_max = "AV1"
        elif "AV2" in ind and "Nota Final" in ind: chave_max = "AV2"
        elif "AV3" in ind and "Nota Final" in ind: chave_max = "AV3"
        
        # Se não achou chave específica, retorna original
        if not chave_max: return val
        
        # Busca máximo no dicionário de regras
        max_permitido = MAXIMOS.get(bim, {}).get(chave_max)
        
        if not max_permitido: return val
        
        # Lógica de correção: se for maior que o teto + 10% de tolerância
        if val > max_permitido * 1.1:
            # Tenta dividir por 10 (ex: 14.1 virou 141)
            if (val / 10) <= max_permitido * 1.1:
                return val / 10
            # Tenta dividir por 100 (ex: 14.1 virou 1410)
            elif (val / 100) <= max_permitido * 1.1:
                return val / 100
        
        return val
    
    if not df_final.empty and "Valor" in df_final.columns:
        df_final["Valor"] = df_final.apply(corrigir_escala_row, axis=1)

    return df_final

def get_base_larga(df_long):
    cols_fixas = ["nome_estudante", "turma", "bimestre"]
    cols_fixas = [c for c in cols_fixas if c in df_long.columns]
    cols_dados = ["tipoindicador", "Valor"]
    cols_ctx = [c for c in df_long.columns if c not in cols_fixas + cols_dados]
    
    if "tipoindicador" not in df_long.columns:
        return pd.DataFrame()

    df_pivot = df_long.pivot_table(
        index=cols_fixas + cols_ctx,
        columns="tipoindicador",
        values="Valor",
        aggfunc="mean" 
    ).reset_index()
    return df_pivot

def status_cor(valor, indicador, bimestre):
    if pd.isna(valor): return "secondary"
    
    # Identifica qual é o indicador para buscar o máximo correto
    chave = "Nota Global" if "Nota Global" in indicador else \
            "AV1" if "AV1" in indicador else \
            "AV2" if "AV2" in indicador else \
            "AV3" if "AV3" in indicador else None
            
    if not chave: return "secondary" # Se não for nota de avaliação, não colore
    
    mx = MAXIMOS.get(bimestre, {}).get(chave, 10)
    
    if valor < (mx * 0.5): return "danger"
    if valor >= (mx * 0.8): return "success"
    return "warning"

# ==============================================================================
# 4. EXECUÇÃO PRINCIPAL
# ==============================================================================

df = pd.DataFrame()
df_larga = pd.DataFrame()

try:
    with st.spinner("Processando dados..."):
        df = carregar_dados_v5()
        
        if df is not None and not df.empty:
            required_cols = ['turma', 'tipoindicador']
            missing = [c for c in required_cols if c not in df.columns]
            
            if missing:
                st.error(f"Erro Crítico: Colunas obrigatórias ausentes: {missing}")
                st.stop()
                
            df_larga = get_base_larga(df)
        else:
            st.warning("Nenhum dado retornado.")
            st.stop()

except Exception as e:
    st.error(f"Erro no carregamento: {e}")
    st.stop()

if df.empty:
    st.stop()

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
    c1, c2, c3 = st.columns(3)
    
    lista_turmas = sorted(list(IDS_PLANILHAS.keys()))
    try:
        if "turma" in df.columns:
            lista_turmas = sorted(df["turma"].unique().astype(str).tolist())
    except:
        pass
        
    turmas = ["Todas"] + lista_turmas
    with c1: turma_sel = st.selectbox("Turma", turmas)
    
    inds = sorted(df["tipoindicador"].unique().tolist())
    idx = inds.index("Nota Global") if "Nota Global" in inds else 0
    with c2: ind_sel = st.selectbox("Indicador", inds, index=idx)
    
    cols_ignorar = ["nome_estudante", "turma", "bimestre"] + inds
    cols_ctx = [c for c in df_larga.columns if c not in cols_ignorar]
    cols_cat = [c for c in cols_ctx if df_larga[c].nunique() < 15]
    with c3: color_sel = st.selectbox("Desagregar por", ["Nenhum"] + cols_cat)
    
    dff = pd.DataFrame()
    if "tipoindicador" in df.columns:
        dff = df[df["tipoindicador"] == ind_sel].copy()
    else:
        st.error("Coluna 'tipoindicador' não existe.")
        st.stop()
    
    if dff.empty:
        st.warning("Sem dados.")
        st.stop()

    if turma_sel != "Todas": 
        dff = dff[dff["turma"] == turma_sel]
    
    # Título Dinâmico
    st.subheader(f"Evolução Bimestral — {ind_sel}")
    grp = ["bimestre"]
    if color_sel != "Nenhum": grp.append(color_sel)
    
    chart_data = dff.groupby(grp)["Valor"].mean().reset_index()
    
    fig = px.bar(chart_data, x="bimestre", y="Valor", 
                 color=color_sel if color_sel != "Nenhum" else None,
                 barmode="group", text_auto='.1f', 
                 category_orders={"bimestre": NIVEL_BIMESTRE})
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("📈 Correlações")
    numeric_cols = df_larga.select_dtypes(include=[np.number]).columns.tolist()
    c_x, c_y = st.columns(2)
    with c_x: 
        idx_x = numeric_cols.index("Número de Faltas") if "Número de Faltas" in numeric_cols else 0
        x_axis = st.selectbox("Eixo X", numeric_cols, index=idx_x)
    with c_y: 
        idx_y = numeric_cols.index("Nota Global") if "Nota Global" in numeric_cols else 0
        y_axis = st.selectbox("Eixo Y", numeric_cols, index=idx_y)
    
    if x_axis and y_axis:
        # Proteção contra ausência de statsmodels para não quebrar o app
        trend_arg = None
        try:
            import statsmodels.api
            trend_arg = "ols"
        except ImportError:
            st.warning("⚠️ Biblioteca 'statsmodels' não encontrada. O gráfico será exibido sem a linha de tendência.")

        fig_s = px.scatter(df_larga, x=x_axis, y=y_axis, color="bimestre", trendline=trend_arg)
        st.plotly_chart(fig_s, use_container_width=True)

# --- INDIVIDUAL ---
elif page == "Individual":
    st.header("👤 Análise Individual")
    c1, c2 = st.columns([1,3])
    
    lista_turmas = sorted(list(IDS_PLANILHAS.keys()))
    try:
        if "turma" in df.columns:
            lista_turmas = sorted(df["turma"].unique().astype(str).tolist())
    except:
        pass

    with c1: turma_ind = st.selectbox("Turma", ["Todas"] + lista_turmas, key="t_ind")
    
    alunos_list = df["nome_estudante"].unique()
    if turma_ind != "Todas":
        alunos_list = df[df["turma"] == turma_ind]["nome_estudante"].unique()
        
    with c2: aluno_sel = st.selectbox("Estudante", sorted(alunos_list))
    
    st.subheader("Boletim")
    df_al = df_larga[df_larga["nome_estudante"] == aluno_sel]
    
    cols = st.columns(4)
    for i, bim in enumerate(NIVEL_BIMESTRE):
        row = df_al[df_al["bimestre"] == bim]
        with cols[i]:
            st.markdown(f"**{bim}**")
            if not row.empty:
                val = lambda c: row.iloc[0].get(c, np.nan)
                av1, av2, av3 = val("AV1 – Nota Final"), val("AV2 – Nota Final"), val("AV3 – Nota Final")
                faltas = val("Número de Faltas")
                st.markdown(f"""
                <div class="cafe-card status-{status_cor(av3, 'AV3', bim)}">
                    <div style="font-size:0.8rem; color:#666;">AV3</div>
                    <div class="valor">{av3:.1f}</div>
                    <div style="font-size:0.8rem; margin-top:5px;">
                        AV1: <b>{av1:.1f}</b> | AV2: <b>{av2:.1f}</b><br>
                        Faltas: {int(faltas) if pd.notna(faltas) else '-'}
                    </div>
                </div>""", unsafe_allow_html=True)
            else: st.info("-")
            
    st.markdown("---")
    st.subheader("Comparativo Aluno vs Turma")
    
    t_aluno = df[df["nome_estudante"] == aluno_sel]["turma"].iloc[0]
    df_turma = df[df["turma"] == t_aluno].groupby(["bimestre", "tipoindicador"])["Valor"].mean().reset_index()
    df_turma["Serie"] = "Média Turma"
    df_single = df[df["nome_estudante"] == aluno_sel].copy()
    df_single["Serie"] = "Aluno"
    
    main_inds = ["Nota Global", "Percentual de Presenças", "AV3 – Média Percentual", "SAEM – % Acertos"]
    df_comp = pd.concat([df_turma, df_single[["bimestre", "tipoindicador", "Valor", "Serie"]]])
    df_comp = df_comp[df_comp["tipoindicador"].isin(main_inds)]
    
    fig_comp = px.line(df_comp, x="bimestre", y="Valor", color="Serie", 
                       facet_col="tipoindicador", facet_col_wrap=2, markers=True)
    fig_comp.update_yaxes(matches=None) 
    st.plotly_chart(fig_comp, use_container_width=True)
    
# --- ATENÇÃO ---
elif page == "Estudantes em Atenção":
    st.header("⚠️ Estudantes em Atenção")
    st.info("Critério: Nota Global < 10 OU Presença < 75%")
    bim = st.selectbox("Bimestre", ["Todos"] + NIVEL_BIMESTRE)
    
    dfr = df_larga.copy()
    if bim != "Todos": dfr = dfr[dfr["bimestre"] == bim]
    
    if "Nota Global" in dfr.columns and "Percentual de Presenças" in dfr.columns:
        mask = (dfr["Nota Global"] < 10) | (dfr["Percentual de Presenças"] < 75)
        st.dataframe(dfr[mask][["nome_estudante", "turma", "bimestre", "Nota Global", "Percentual de Presenças"]], use_container_width=True)
    else:
        st.warning("Colunas necessárias não encontradas.")

# --- BASE COMPLETA ---
elif page == "Base Completa":
    st.header("📚 Base de Dados Completa")
    csv = df_larga.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Baixar Dados (CSV)", csv, 'cafelab_dados_completos.csv', 'text/csv')
    st.dataframe(df_larga, use_container_width=True)