import streamlit as st
import pandas as pd
import numpy as np
import gspread
from google.oauth2.service_account import Credentials
import os
import re
import unicodedata
from datetime import datetime
from fpdf import FPDF
import plotly.express as px
import base64
import io
import zipfile
import matplotlib.pyplot as plt

# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA
# ==============================================================================
st.set_page_config(
    page_title="CAfe.Lab | Analisar & Acolher",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# CONSTANTES E CONFIGURAÇÕES
# ==============================================================================

# IDs das planilhas de Notas/Frequência
IDS_PLANILHAS = {
    "621": "16s2R-poDNNnd2SMwuq5HIsRmD8ax1J4nI2AABi-bCs4",
    "624": "1Q0yiIRIgsnLAytPVRtwe8_-RbRILRb2-HUEsztc89Rk",
    "711": "1HMjzbAKyDCvJh9CO8T2isGA04EjVoHlCgnzgu-s1mh0",
    "712": "1b_39FjRINpB6ybTrHZ1-j41CBzHqYIOozx_4RtUY9bY",
    "713": "17u8yE9tIieA7VsojilEJXANirXjKceF80y3AXzBXORo"
}

# IDs das planilhas de Contexto
URLS_SDQ = {
    "621": "1fycU1axN4cWEVkHB8NPJ2mt27XXbSOmoLw6E5lhxbmQ",
    "624": "1aji4nLBc1dbEkFJVWUeMbG3LgNa-dQi_xjA_epwxxYw",
    "711": "1YFZPfPw7sT6J4W7_kYIoKWf4Xo484SkputcLFicO7YA",
    "712": "1P6Ghbdnyx4tpRa6Df-g7lOZtuGpnEgNNmA4cHZuAYMg",
    "713": "16H47jOIqqrJXKIQ3UMa5maVlEpJjJ-_4URiGOI3fZA8"
}

URLS_NSE = {
    "621": "1OjdXbcQvyP-aWhhPI9ejjgEWSizs-FcObjY0e1Zz23Y",
    "624": "1w3TEHcQtDuFHpEqyutolyALl1QvhnMjMqFFWIFrpKvw",
    "711": "1UNpAdfUZDVrQ8xnoW911reclkO7spaE_lQRDxbBtDg4",
    "712": "1SWm8QRZ3Y3ydhEmp6y-Dti_o8ei9ufZe2aDFmOx2CFs",
    "713": "1JBMKRv1jtmcQ9zq8-yl3ti3d0oWZ0OKPHT1RDLJfM00"
}

URLS_GAD7 = {
    "621": "1HZMAqD5_5OcPkbTbaa1STtrP_dJHWGh0d-lm1i_gWg4",
    "624": "1QuTfi7g0x_uZz5BAeJEyM2yATexOMTBJxdg6d8MeMgA",
    "711": "16ap1E52_9VFkSz83-yKgokGlUmFcK0V1NYB06564Mmo",
    "713": "1m38s5mEUDm-tzfp9op-EKD-qmjGZbrPb8TWADfx5bz4"
}

ARQUIVO_CREDENCIAIS = "credentials.json"

# Mapa ampliado para garantir que pegue as notas independente da variação do nome na coluna
MAPA_INDICADORES = {
    # Variações AV1
    "av1_nota_final": "AV1 – Nota Final",
    "notaav1": "AV1 – Nota Final",
    "nota_av1": "AV1 – Nota Final",
    "av1": "AV1 – Nota Final",
    
    # Variações AV2
    "av2_nota_final": "AV2 – Nota Final",
    "notaav2": "AV2 – Nota Final",
    "nota_av2": "AV2 – Nota Final",
    "av2": "AV2 – Nota Final",
    
    # Variações AV3
    "av3_nota_final": "AV3 – Nota Final",
    "notaav3": "AV3 – Nota Final",
    "nota_av3": "AV3 – Nota Final",
    "av3": "AV3 – Nota Final",
    
    # Globais e Presença
    "nota_global": "Nota Global",
    "nota_global_acumulada": "Nota Global Acumulada",
    "av1_percentual_de_presencas": "Percentual de Presenças",
    "percentual_de_presencas": "Percentual de Presenças",
    "percentual_presencas": "Percentual de Presenças",
    
    # Atividades
    "av1_percentual_de_atividades_feitas": "AV1 – % de Atividades Feitas",
    "av2_percentual_de_atividades_feitas": "AV2 – % de Atividades Feitas",
    "percentual_atividades_feitas_av2": "AV2 – % de Atividades Feitas"
}

NIVEL_BIMESTRE = ["1º Bimestre", "2º Bimestre", "3º Bimestre", "4º Bimestre"]
INDICADORES_DESEJADOS = [
    "AV1 – Nota Final", 
    "AV2 – Nota Final", 
    "AV3 – Nota Final", 
    "Percentual de Presenças", 
    "Nota Global", 
    "Nota Global Acumulada",
    "AV1 – % de Atividades Feitas",
    "AV2 – % de Atividades Feitas"
]

MAXIMOS = {
    "1º Bimestre": {"AV1": 5, "AV2": 5, "AV3": 10, "Nota Global": 20, "Nota Global Acumulada": 20},
    "2º Bimestre": {"AV1": 5, "AV2": 5, "AV3": 10, "Nota Global": 20, "Nota Global Acumulada": 40},
    "3º Bimestre": {"AV1": 5, "AV2": 10, "AV3": 15, "Nota Global": 30, "Nota Global Acumulada": 70},
    "4º Bimestre": {"AV1": 5, "AV2": 10, "AV3": 15, "Nota Global": 30, "Nota Global Acumulada": 100},
}

# ==============================================================================
# FUNÇÕES UTILITÁRIAS
# ==============================================================================

def normalizar_nome_coluna(col):
    if not isinstance(col, str): return str(col)
    col = col.lower()
    col = unicodedata.normalize('NFKD', col).encode('ascii', 'ignore').decode('utf-8')
    col = re.sub(r'\s+', '_', col)
    col = re.sub(r'[^a-z0-9_]', '', col)
    return col

def clean_number(x):
    if isinstance(x, str): return x.replace(',', '.')
    return x

def safe_int(val):
    try: return int(float(val))
    except: return 0

def status_cor(val, lbl, bim):
    try:
        if pd.isna(val) or val == "": return "secondary"
        v = float(val)
        
        # Lógica de Presença
        if "Presença" in lbl:
            return "aprovado" if v >= 75 else "recuperacao"
        
        # Lógica de Nota (Dinâmica por bimestre)
        chave_max = "Nota Global" if "Global" in lbl else "AV3" if "AV3" in lbl else "AV1" if "AV1" in lbl else "AV2"
        max_val = MAXIMOS.get(bim, {}).get(chave_max, 10)
        
        if v >= (max_val * 0.6): return "aprovado"
        return "recuperacao"
    except:
        return "secondary"

# ==============================================================================
# ETL & PROCESSAMENTO
# ==============================================================================

def processar_contexto_online(client):
    """Baixa e processa SDQ, NSE e GAD7 aplicando tratamento estatístico do R."""
    
    def fetch_data(urls_dict):
        lista = []
        for turma, sheet_id in urls_dict.items():
            try:
                sh = client.open_by_key(sheet_id)
                ws = sh.get_worksheet(0)
                vals = ws.get_all_values()
                if vals:
                    headers = [normalizar_nome_coluna(h) for h in vals[0]]
                    df_t = pd.DataFrame(vals[1:], columns=headers)
                    df_t["turma"] = str(turma)
                    lista.append(df_t)
            except: pass
        return pd.concat(lista, ignore_index=True) if lista else pd.DataFrame()

    # --- 1. GAD-7 ---
    df_gad = fetch_data(URLS_GAD7)
    if not df_gad.empty:
        rename_gad = {}
        for c in df_gad.columns:
            if c.startswith('nas_ultimas_2_semanas'): rename_gad[c] = 'gad1'
            elif c.startswith('nao_conseguir_parar'): rename_gad[c] = 'gad2'
            elif c.startswith('preocuparse_demais'): rename_gad[c] = 'gad3'
            elif c.startswith('ter_dificuldade_para_relaxar'): rename_gad[c] = 'gad4'
            elif c.startswith('sentirse_tao_inquietoa'): rename_gad[c] = 'gad5'
            elif c.startswith('ficar_facilmente_irritadoa'): rename_gad[c] = 'gad6'
            elif c.startswith('sentir_medo_como'): rename_gad[c] = 'gad7'
            elif c.startswith('se_voce_marcou'): rename_gad[c] = 'dificuldade'
        df_gad.rename(columns=rename_gad, inplace=True)
        
        score_map = {"a": 0, "b": 1, "c": 2, "d": 3}
        gad_cols = [f'gad{i}' for i in range(1, 8)]
        for c in gad_cols:
            if c in df_gad.columns:
                df_gad[c] = df_gad[c].astype(str).str.lower().map(score_map)
        
        df_gad['gad7_total'] = df_gad[gad_cols].sum(axis=1, min_count=3)
        cols_keep = ['nome_estudante', 'turma', 'gad7_total']
        df_gad = df_gad[[c for c in cols_keep if c in df_gad.columns]]

    # --- 2. SDQ (Com inversão correta) ---
    df_sdq = fetch_data(URLS_SDQ)
    if not df_sdq.empty:
        rename_sdq = {}
        map_keys = {
            'eu_tento_ser_legal': 'sconsid', 'nao_consigo': 'srestles', 'muitas_vezes': 'ssomatic', 
            'tenho_boa_vontade': 'sshares', 'fico_muito_bravo': 'stantrum', 'eu_quase_sempre': 'sloner', 
            'geralmente_sou_obediente': 'sobeys', 'tenho_muitas_preocupa': 'sworries', 'tento_ajudar': 'scaring', 
            'estou_sempre_agitado': 'sfidgety', 'tenho_pelo_menos_uma': 'sfriend', 'eu_brigo_muito': 'sfights', 
            'frequentemente_estou_infeliz': 'sunhappy', 'em_geral_sou_querido': 'spopular', 'perco_a_concentr': 'sdistrac', 
            'fico_nervoso': 'sclingy', 'sou_legal_com_crianas': 'skind', 'frequentemente_sou_acusado': 'slies', 
            'os_outros_jovens': 'sbullied', 'frequentemente_me_ofereo': 'shelpout', 'eu_penso': 'sreflect', 
            'pego_coisas': 'ssteals', 'doume_melhor': 'soldbest', 'tenho_muitos_medos': 'safraid', 'consigo_terminar': 'sattends'
        }
        for c in df_sdq.columns:
            for k, v in map_keys.items():
                if c.startswith(k): rename_sdq[c] = v; break
        df_sdq.rename(columns=rename_sdq, inplace=True)
        
        sdq_val_map = {"a": 0, "b": 1, "c": 2}
        sdq_cols = list(map_keys.values())
        for c in sdq_cols:
            if c in df_sdq.columns:
                df_sdq[c] = df_sdq[c].astype(str).str.lower().map(sdq_val_map)
        
        # Inversão (Reverse Scoring)
        reverse_cols = ['sobeys', 'sfriend', 'spopular', 'sreflect', 'sattends']
        for c in reverse_cols:
            if c in df_sdq.columns:
                df_sdq[c] = 2 - df_sdq[c]

        def calc_sub(row, cols):
            valid = [row[c] for c in cols if c in row and pd.notna(row[c])]
            return sum(valid) if len(valid) >= 3 else None

        df_sdq['sdq_emocional'] = df_sdq.apply(lambda x: calc_sub(x, ['ssomatic', 'sworries', 'sunhappy', 'sclingy', 'safraid']), axis=1)
        df_sdq['sdq_conduta'] = df_sdq.apply(lambda x: calc_sub(x, ['stantrum', 'sobeys', 'sfights', 'slies', 'ssteals']), axis=1)
        df_sdq['sdq_hiperatividade'] = df_sdq.apply(lambda x: calc_sub(x, ['srestles', 'sfidgety', 'sdistrac', 'sreflect', 'sattends']), axis=1)
        df_sdq['sdq_pares'] = df_sdq.apply(lambda x: calc_sub(x, ['sloner', 'sfriend', 'spopular', 'sbullied', 'soldbest']), axis=1)
        df_sdq['sdq_prosocial'] = df_sdq.apply(lambda x: calc_sub(x, ['sconsid', 'sshares', 'scaring', 'skind', 'shelpout']), axis=1)
        df_sdq['sdq_total'] = df_sdq['sdq_emocional'] + df_sdq['sdq_conduta'] + df_sdq['sdq_hiperatividade'] + df_sdq['sdq_pares']
        
        keep = ['nome_estudante', 'turma', 'sdq_total', 'sdq_emocional', 'sdq_conduta', 'sdq_hiperatividade', 'sdq_pares', 'sdq_prosocial']
        df_sdq = df_sdq[[c for c in keep if c in df_sdq.columns]]

    # --- 3. NSE (Cálculo do INSE) ---
    df_nse = fetch_data(URLS_NSE)
    if not df_nse.empty:
        rename_nse = {}
        nse_keys = {
            'qual__a_maior_escolaridade_da_sua_me_ou_mulher': 'escolaridade_mae',
            'qual__a_maior_escolaridade_do_seu_pai_ou_homem': 'escolaridade_pai',
            'quantas_geladeiras_existem': 'qtd_geladeiras',
            'quantos_computadores_ou_notebooks': 'qtd_computadores',
            'quantos_quartos_para_dormir': 'qtd_quartos',
            'quantas_televises_existem': 'qtd_televisoes',
            'quantos_banheiros_existem': 'qtd_banheiros',
            'quantos_carros_de_passeio': 'qtd_carros',
            'quantos_celulares_com_internet': 'qtd_celulares',
            'na_sua_casa_tem_tv_por_internet': 'tv_internet',
            'na_sua_casa_tem_rede_wifi': 'wifi',
            'na_sua_casa_tem_mesa_para_estudar': 'mesa_estudo',
            'na_sua_casa_tem_garagem': 'garagem',
            'na_sua_casa_tem_forno_de_microondas': 'microondas',
            'na_sua_casa_tem_aspirador_de_p': 'aspirador',
            'na_sua_casa_tem_mquina_de_lavar_roupa': 'maquina_lavar',
            'na_sua_casa_tem_freezer_independente': 'freezer',
            'qual__o_seu_gnero': 'genero',
            'qual__a_sua_cor_ou_raa': 'cor_raca'
        }
        for c in df_nse.columns:
            for k, v in nse_keys.items():
                if c.startswith(k): rename_nse[c] = v; break
        df_nse.rename(columns=rename_nse, inplace=True)

        nse_val_map = {"a": 0, "b": 1, "c": 2, "d": 3, "e": 4}
        cols_inse = ['escolaridade_mae', 'escolaridade_pai', 'qtd_geladeiras', 'qtd_computadores', 
                     'qtd_quartos', 'qtd_televisoes', 'qtd_banheiros', 'qtd_carros', 'qtd_celulares',
                     'tv_internet', 'wifi', 'mesa_estudo', 'garagem', 'microondas', 'aspirador', 
                     'maquina_lavar', 'freezer']
        
        for c in cols_inse:
            if c in df_nse.columns:
                 df_nse[c] = df_nse[c].astype(str).str.lower().map(nse_val_map)

        df_nse['inse'] = df_nse[[c for c in cols_inse if c in df_nse.columns]].mean(axis=1)

        if 'genero' in df_nse.columns:
            df_nse['genero'] = df_nse['genero'].astype(str).str.lower().map({'a': 'Masculino', 'b': 'Feminino'}).fillna(df_nse['genero'])
        if 'cor_raca' in df_nse.columns:
            df_nse['cor_raca'] = df_nse['cor_raca'].astype(str).str.lower().map({'a': 'Branca', 'b': 'Preta/Parda', 'c': 'Amarela', 'd': 'Indígena'}).fillna(df_nse['cor_raca'])

        cols_keep_nse = ['nome_estudante', 'turma', 'inse', 'genero', 'cor_raca']
        df_nse = df_nse[[c for c in cols_keep_nse if c in df_nse.columns]]

    # --- MERGE FINAL ---
    df_final = df_sdq if not df_sdq.empty else pd.DataFrame(columns=['nome_estudante', 'turma'])
    
    if not df_gad.empty:
        df_final = pd.merge(df_final, df_gad, on=['nome_estudante', 'turma'], how='outer')
    
    if not df_nse.empty:
        cols_nse = [c for c in df_nse.columns if c not in ['nome_estudante', 'turma']]
        df_final = pd.merge(df_final, df_nse[['nome_estudante', 'turma'] + cols_nse], on=['nome_estudante', 'turma'], how='outer')
        
    return df_final

@st.cache_data(ttl=600)
def carregar_dados_v5():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    credentials = None
    try:
        if "gsheets" in st.secrets: credentials = Credentials.from_service_account_info(st.secrets["gsheets"], scopes=scopes)
    except: pass
    if not credentials and os.path.exists(ARQUIVO_CREDENCIAIS):
        try: credentials = Credentials.from_service_account_file(ARQUIVO_CREDENCIAIS, scopes=scopes)
        except: pass
    
    if not credentials:
        st.error("Credenciais não encontradas."); st.stop()
        
    client = gspread.authorize(credentials)
    
    lista_dfs = []
    for turma, sheet_id in IDS_PLANILHAS.items():
        try:
            sh = client.open_by_key(sheet_id)
            vals = sh.get_worksheet(0).get_all_values()
            if vals:
                headers = [normalizar_nome_coluna(c) for c in vals[0]]
                df_t = pd.DataFrame(vals[1:], columns=headers)
                df_t = df_t.loc[:, ~df_t.columns.duplicated()]
                if 'turma' in df_t.columns: df_t = df_t.drop(columns=['turma'])
                df_t["turma"] = str(turma)
                lista_dfs.append(df_t)
        except: pass

    if not lista_dfs: return pd.DataFrame()
    df_bruto = pd.concat(lista_dfs, ignore_index=True)
    
    # Melt
    sufixos = {"_primeirobi": "1º Bimestre", "_segundobi": "2º Bimestre", "_terceirobi": "3º Bimestre", "_quartobi": "4º Bimestre"}
    cols_fixas = [c for c in ["nome_estudante", "turma"] if c in df_bruto.columns]
    cols_para_melt = [c for c in df_bruto.columns if any(c.endswith(s) for s in sufixos) and not c.startswith("av1_c") and "xpclassmana" not in c]
    
    if not cols_para_melt: return df_bruto
    
    df_long = df_bruto.melt(id_vars=cols_fixas, value_vars=cols_para_melt, var_name="indicador_cru", value_name="Valor")
    
    def proc_ind(r):
        ic = r["indicador_cru"]
        for s, b in sufixos.items():
            if ic.endswith(s): return pd.Series([b, MAPA_INDICADORES.get(ic.replace(s, ""), ic.replace(s, ""))])
        return pd.Series([None, None])
        
    df_long[["bimestre", "tipoindicador"]] = df_long.apply(proc_ind, axis=1)
    df_final = df_long.drop(columns=["indicador_cru"])
    
    # Contexto (Integração)
    df_ctx = processar_contexto_online(client)
    if not df_ctx.empty:
        df_ctx = df_ctx.drop(columns=[c for c in ["tipoindicador", "bimestre"] if c in df_ctx.columns], errors='ignore')
        df_final = pd.merge(df_final, df_ctx, on=["nome_estudante", "turma"], how="left")
        
    # Limpeza final
    df_final["Valor"] = pd.to_numeric(df_final["Valor"].apply(clean_number), errors="coerce")
    
    # Categorias para Filtros
    if "sdq_total" in df_final.columns:
        df_final["sdq_total_cat"] = np.select([df_final["sdq_total"]<=14, df_final["sdq_total"]<=16, df_final["sdq_total"]>=17], ["Normal", "Limítrofe", "Anormal"], default=None)
    if "gad7_total" in df_final.columns:
        df_final["gad7_total_cat"] = np.select([df_final["gad7_total"]<=4, df_final["gad7_total"]<=9, df_final["gad7_total"]<=14, df_final["gad7_total"]>=15], ["Mínima", "Leve", "Moderada", "Grave"], default=None)
        
    return df_final

def get_base_larga(df):
    cols_ignorar = ["tipoindicador", "Valor"]
    index_cols = [c for c in df.columns if c not in cols_ignorar]
    for c in index_cols:
        if pd.api.types.is_numeric_dtype(df[c]): df[c] = df[c].fillna(0)
        else: df[c] = df[c].fillna("")
    return df.pivot_table(index=index_cols, columns="tipoindicador", values="Valor", aggfunc='first').reset_index()

# ==============================================================================
# CLASSES E GERADORES (PDF/HTML)
# ==============================================================================

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Relatório Individual - CAfe.Lab', 0, 1, 'C')
        self.ln(5)
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def gerar_pdf_aluno(nome_aluno, turma, df_aluno, comentarios=""):
    def clean_text(text):
        if not isinstance(text, str): return str(text)
        return unicodedata.normalize('NFKD', text).encode('latin-1', 'ignore').decode('latin-1')

    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"Nome: {clean_text(nome_aluno)}", 0, 1)
    pdf.cell(0, 10, f"Turma: {clean_text(turma)}", 0, 1)
    pdf.ln(5)
    
    pdf.cell(0, 10, clean_text("Resumo dos Bimestres"), 0, 1)
    pdf.set_font("Arial", "", 10)
    for bim in NIVEL_BIMESTRE:
        row = df_aluno[df_aluno["bimestre"] == bim]
        if not row.empty:
            data = row.iloc[0]
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 10, clean_text(bim), 0, 1)
            pdf.set_font("Arial", "", 10)
            for k in INDICADORES_DESEJADOS:
                if k in data and pd.notna(data[k]):
                    val_str = f"{float(data[k]):.1f}"
                    pdf.cell(0, 6, f"{clean_text(k)}: {clean_text(val_str)}", 0, 1)
            pdf.ln(2)
    
    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, clean_text("Avaliação Psicossocial"), 0, 1)
    pdf.set_font("Arial", "", 10)
    
    sdq_val, gad_val, inse_val = "-", "-", "-"
    if not df_aluno.empty:
        row = df_aluno.iloc[0]
        if "sdq_total" in row: sdq_val = str(row.get("sdq_total", "-"))
        if "gad7_total" in row: gad_val = str(row.get("gad7_total", "-"))
        if "inse" in row: inse_val = f"{float(row.get('inse', 0)):.2f}"

    pdf.cell(0, 6, f"SDQ Total: {clean_text(sdq_val)}", 0, 1)
    pdf.cell(0, 6, f"GAD-7 Total: {clean_text(gad_val)}", 0, 1)
    pdf.cell(0, 6, f"INSE (Est.): {clean_text(inse_val)}", 0, 1)
    pdf.ln(5)
    
    if comentarios:
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, clean_text("Comentários"), 0, 1)
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(0, 6, clean_text(comentarios))

    return bytes(pdf.output())

def gerar_html_web(nome_aluno, turma, df_aluno):
    av1, av2, av3, glob, accum, freq = ([0.0]*4 for _ in range(6))
    sdq_val, gad_val = 0, 0
    
    if not df_aluno.empty:
        if "sdq_total" in df_aluno.columns: sdq_val = safe_int(df_aluno.iloc[0].get("sdq_total", 0))
        if "gad7_total" in df_aluno.columns: gad_val = safe_int(df_aluno.iloc[0].get("gad7_total", 0))
            
    for i, bim in enumerate(NIVEL_BIMESTRE):
        row = df_aluno[df_aluno["bimestre"] == bim]
        if not row.empty:
            d = row.iloc[0]
            try: av1[i] = float(d.get("AV1 – Nota Final", 0) or 0)
            except: pass
            try: av2[i] = float(d.get("AV2 – Nota Final", 0) or 0)
            except: pass
            try: av3[i] = float(d.get("AV3 – Nota Final", 0) or 0)
            except: pass
            try: glob[i] = float(d.get("Nota Global", 0) or 0)
            except: pass
            try: accum[i] = float(d.get("Nota Global Acumulada", 0) or 0)
            except: pass
            try: freq[i] = safe_int(d.get("Percentual de Presenças", 0))
            except: pass

    final_score = max(accum) if accum else 0.0
    
    html = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>Relatório - {nome_aluno}</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.0.0"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;900&display=swap');
            body {{ font-family: 'Inter', sans-serif; background-color: #525659; margin: 0; padding: 40px 0; display: flex; justify-content: center; }}
            .report-page {{ width: 210mm; min-height: 297mm; background: white; padding: 10mm; position: relative; box-shadow: 0 0 15px rgba(0,0,0,0.5); }}
            .watermark {{ position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%) rotate(-45deg); font-size: 6rem; font-weight: 900; opacity: 0.1; border: 8px solid currentColor; padding: 1rem 2rem; border-radius: 1rem; text-transform: uppercase; white-space: nowrap; pointer-events: none; }}
            .status-aprovado {{ color: #16a34a; }} .status-recuperacao {{ color: #ea580c; }}
            .bg-aprovado {{ background-color: #dcfce7; color: #166534; }} .bg-recuperacao {{ background-color: #ffedd5; color: #9a3412; }}
            .fab-print {{ position: fixed; bottom: 30px; right: 30px; background-color: #e95420; color: white; width: 60px; height: 60px; border-radius: 50%; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 10px rgba(0,0,0,0.3); cursor: pointer; z-index: 100; font-size: 24px; border: none; }}
            @media print {{ body {{ background: white; padding: 0; display: block; }} .fab-print {{ display: none !important; }} .report-page {{ box-shadow: none; margin: 0; width: 100%; }} }}
        </style>
    </head>
    <body>
        <button onclick="window.print()" class="fab-print"><i class="fas fa-print"></i></button>
        <div id="container"></div>
        <script>
            const data = {{
                name: "{nome_aluno}", turma: "{turma}", score: {final_score},
                socio: {{ gad: {gad_val}, sdq: {sdq_val} }},
                av1: {av1}, av2: {av2}, av3: {av3}, glob: {glob}, acc: {accum}, freq: {freq}
            }};
            
            const isApp = data.score >= 50;
            const stTxt = isApp ? "Aprovado" : "Recuperação";
            const stCls = isApp ? "status-aprovado" : "status-recuperacao";
            const bgCls = isApp ? "bg-aprovado" : "bg-recuperacao";
            const bdCol = isApp ? "border-green-200" : "border-amber-200";
            const fmt = (n) => n !== undefined ? n.toFixed(1) : "--";
            
            document.getElementById('container').innerHTML = `
            <div class="report-page">
                <div class="watermark ${{stCls}}">${{stTxt}}</div>
                <header class="flex justify-between items-end border-b-4 border-slate-800 pb-4 mb-6 relative z-10">
                    <div><h1 class="text-3xl font-black text-slate-800 uppercase">Relatório de Desempenho</h1><p class="text-slate-500 font-medium">Análise Integrada • 2025</p></div>
                    <div class="text-right"><div class="${{bgCls}} font-bold px-4 py-1 rounded text-sm mb-1 inline-block border ${{bdCol}}">SITUAÇÃO FINAL</div><div class="text-4xl font-black uppercase ${{stCls}}">${{stTxt}}</div></div>
                </header>
                <section class="bg-slate-50 rounded-xl p-4 mb-6 border border-slate-200 relative z-10 flex justify-between items-center">
                    <div><h2 class="text-2xl font-bold text-slate-800">${{data.name}}</h2><p class="text-sm text-slate-600">Turma ${{data.turma}}</p></div>
                    <div class="text-center px-4"><span class="block text-xs font-bold text-slate-400 uppercase">Nota Acumulada</span><span class="text-xl font-black ${{stCls}}">${{data.score.toFixed(1)}}</span></div>
                </section>
                <section class="mb-8 relative z-10"><div class="bg-white p-2 rounded-lg border border-slate-100 shadow-sm"><div class="h-64 relative"><canvas id="chart"></canvas></div></div></section>
                <section class="mb-8 relative z-10">
                    <div class="overflow-hidden rounded-lg border border-slate-200 shadow-sm">
                        <table class="min-w-full text-sm text-center">
                            <thead class="bg-slate-800 text-white font-bold uppercase text-xs"><tr><th class="px-2 py-2 text-left">Bim</th><th class="px-2 py-2 bg-blue-900">AV1</th><th class="px-2 py-2 bg-blue-800">AV2</th><th class="px-2 py-2 bg-blue-900">AV3</th><th class="px-2 py-2 bg-indigo-900 text-yellow-300">Global</th><th class="px-2 py-2 bg-purple-900">Acum.</th><th class="px-2 py-2 bg-slate-100 text-slate-600">Freq.</th></tr></thead>
                            <tbody class="divide-y divide-slate-200 bg-white">
                                ${{[0,1,2,3].map(i => `<tr class="hover:bg-slate-50"><td class="px-2 py-2 text-left font-bold text-slate-700">${{i+1}}º</td><td>${{fmt(data.av1[i])}}</td><td>${{fmt(data.av2[i])}}</td><td>${{fmt(data.av3[i])}}</td><td class="font-bold text-indigo-700 bg-indigo-50">${{fmt(data.glob[i])}}</td><td class="font-black text-purple-700 bg-purple-50">${{fmt(data.acc[i])}}</td><td>${{data.freq[i]}}%</td></tr>`).join('')}}
                            </tbody>
                        </table>
                    </div>
                </section>
                <section class="grid grid-cols-2 gap-8 relative z-10">
                    <div class="bg-orange-50 p-4 rounded-lg border border-orange-200">
                        <h3 class="text-xs font-bold text-orange-800 uppercase mb-2">Socioemocional</h3>
                        <div class="flex justify-between items-center mb-1"><span class="text-sm text-orange-900">GAD-7</span><span class="bg-white border border-orange-200 text-orange-800 text-xs font-bold px-2 py-1 rounded">${{data.socio.gad}} pts</span></div>
                        <div class="flex justify-between items-center"><span class="text-sm text-orange-900">SDQ</span><span class="bg-white border border-orange-200 text-orange-800 text-xs font-bold px-2 py-1 rounded">${{data.socio.sdq}} pts</span></div>
                    </div>
                    <div class="bg-slate-50 p-4 rounded-lg border border-slate-200 flex items-center justify-center text-center"><p class="text-sm text-slate-700">Gerado em <strong>{datetime.now().strftime('%d/%m/%Y')}</strong>.</p></div>
                </section>
            </div>`;

            new Chart(document.getElementById('chart').getContext('2d'), {{
                type: 'bar',
                data: {{ labels: ['1º', '2º', '3º', '4º'], datasets: [
                    {{ type: 'line', label: 'Acumulado', data: data.acc, borderColor: '#7e22ce', backgroundColor: '#7e22ce', borderWidth: 2, yAxisID: 'y1', datalabels: {{ align: 'top', anchor: 'start', color: '#7e22ce', font: {{ weight: 'bold' }}, formatter: (v) => v }} }},
                    {{ label: 'Global', data: data.glob, backgroundColor: '#4f46e5', yAxisID: 'y', datalabels: {{ color: 'white', font: {{ size: 9 }}, anchor: 'end', align: 'bottom' }} }}
                ]}},
                options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ position: 'bottom' }}, datalabels: {{ display: true }} }}, scales: {{ x: {{ grid: {{ display: false }} }}, y: {{ type: 'linear', position: 'left', max: 30, beginAtZero: true }}, y1: {{ type: 'linear', position: 'right', max: 100, beginAtZero: true, grid: {{ display: false }} }} }} }}
            }});
        </script>
    </body>
    </html>
    """
    return html

# ==============================================================================
# INTERFACE PRINCIPAL
# ==============================================================================

def main():
    # --- Carregamento de Dados ---
    df_larga = pd.DataFrame()
    df = pd.DataFrame()
    
    try:
        with st.spinner("Conectando ao banco de dados..."):
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
        st.markdown("**Dr. William Melo** | `v6.0 Integrated`")
        page = st.radio("Navegação", ["Agregado", "Individual", "Estudantes em Atenção", "Base Completa"])
        st.divider()
        if st.button("Atualizar Dados"):
            st.cache_data.clear()
            st.rerun()

    # --- PÁGINAS ---
    if page == "Agregado":
        st.header("📊 Análise Agregada")
        c1, c2, c3, c4 = st.columns(4)
        turmas = ["Todas"] + sorted(df["turma"].unique().astype(str).tolist())
        with c1: t_sel = st.selectbox("Turma", turmas)
        
        inds = sorted(df["tipoindicador"].unique().tolist())
        idx_global = inds.index("Nota Global") if "Nota Global" in inds else 0
        with c2: i_sel = st.selectbox("Indicador", inds, index=idx_global)
        
        with c3: b_sel = st.selectbox("Bimestre", ["Todos"] + NIVEL_BIMESTRE)
        
        # Filtro de colunas: Aumentado limite para permitir que INSE (contínuo) apareça
        cols_ctx = sorted([c for c in df.columns if c not in ["nome_estudante","turma","bimestre","tipoindicador","Valor","chave_estudante"] and df[c].nunique() < 100])
        with c4: d_sel = st.selectbox("Desagregar por", ["Nenhum"] + cols_ctx)
        
        df_f = df[df["tipoindicador"] == i_sel].copy()
        if t_sel != "Todas": df_f = df_f[df_f["turma"] == t_sel]
        if b_sel != "Todos": df_f = df_f[df_f["bimestre"] == b_sel]
        
        if not df_f.empty:
            facet = "turma" if t_sel == "Todas" else None
            if d_sel == "Nenhum":
                fig = px.strip(df_f, x="bimestre", y="Valor", facet_col=facet, facet_col_wrap=3, stripmode="overlay", hover_data=["nome_estudante"])
                grp = ["bimestre"] + (["turma"] if t_sel=="Todas" else [])
                df_m = df_f.groupby(grp)["Valor"].mean().reset_index()
                fig2 = px.line(df_m, x="bimestre", y="Valor", facet_col=facet, facet_col_wrap=3, markers=True)
                fig2.update_traces(line_color="#FF10F0", line_width=4)
                for t in fig2.data: fig.add_trace(t)
                st.plotly_chart(fig, use_container_width=True)
            else:
                grp = ["bimestre", d_sel] + (["turma"] if t_sel=="Todas" else [])
                df_m = df_f.groupby(grp)["Valor"].mean().reset_index()
                fig = px.bar(df_m, x="bimestre", y="Valor", color=d_sel, barmode="group", facet_col=facet, facet_col_wrap=3, text_auto='.1f')
                st.plotly_chart(fig, use_container_width=True)
                if not df_m.empty:
                    st.dataframe(df_m.pivot_table(index=["bimestre"]+(["turma"] if t_sel=="Todas" else []), columns=d_sel, values="Valor").style.format("{:.2f}"), use_container_width=True)
        else: st.info("Sem dados para a seleção atual.")

    elif page == "Individual":
        st.header("👤 Análise Individual")
        c1, c2 = st.columns([1,3])
        turmas = sorted(df["turma"].unique().astype(str).tolist())
        with c1: t_ind = st.selectbox("Turma", ["Todas"]+turmas, key="t_ind")
        
        if t_ind == "Todas":
            alunos = df["nome_estudante"].unique()
        else:
            alunos = df[df["turma"]==t_ind]["nome_estudante"].unique()
            
        with c2: a_sel = st.selectbox("Estudante", sorted(alunos))
        
        st.markdown("---")
        st.subheader("📄 Relatórios")
        c_pdf1, c_pdf2 = st.columns([2, 1])
        with c_pdf1: cmts = st.text_area("Comentários (para o PDF)", height=100)
        with c_pdf2:
            df_w = df_larga[df_larga["nome_estudante"] == a_sel]
            
            # Botão de Download HTML (Corrigido)
            html_content = gerar_html_web(a_sel, t_ind, df_w)
            st.download_button(
                label="🌐 Baixar HTML Interativo",
                data=html_content,
                file_name=f"Relatorio_Web_{a_sel}.html",
                mime='text/html'
            )
            
            if st.button("Gerar PDF Simples"):
                pdf_bytes = gerar_pdf_aluno(a_sel, t_ind, df_w, cmts)
                st.download_button("📥 Baixar PDF", pdf_bytes, f"Relatorio_{a_sel}.pdf", "application/pdf")

        st.markdown("---")
        st.subheader("Boletim Interativo")
        
        # Estilo CSS para os Cards
        st.markdown("""
        <style>
        .carousel-container { display: flex; gap: 1rem; overflow-x: auto; padding-bottom: 1rem; }
        .carousel-card { min-width: 250px; border-radius: 10px; padding: 1.5rem; background: white; border: 1px solid #ddd; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .status-aprovado { border-left: 5px solid #16a34a; background-color: #f0fdf4; }
        .status-recuperacao { border-left: 5px solid #ea580c; background-color: #fff7ed; }
        .status-secondary { border-left: 5px solid #9ca3af; background-color: #f9fafb; }
        </style>
        """, unsafe_allow_html=True)
        
        html_cards = '<div class="carousel-container">'
        for bim in NIVEL_BIMESTRE:
            row = df_w[df_w["bimestre"]==bim]
            if not row.empty:
                d = row.iloc[0]
                val = d.get("Nota Global") if pd.notna(d.get("Nota Global")) and d.get("Nota Global") != "" else d.get("AV3 – Nota Final", 0)
                lbl = "Nota Global" if pd.notna(d.get("Nota Global")) and d.get("Nota Global") != "" else "AV3"
                cor = status_cor(val, lbl, bim)
                
                det = ""
                # Loop para garantir que AV1, AV2, AV3 apareçam
                for k in INDICADORES_DESEJADOS:
                    if k in d and pd.notna(d[k]) and d[k] != "":
                        try:
                            v_float = float(d[k])
                            det += f"<div><b>{k}:</b> {v_float:.1f}</div>"
                        except:
                            det += f"<div><b>{k}:</b> {d[k]}</div>"
                            
                html_cards += f'<div class="carousel-card status-{cor}"><h4>{bim}</h4><div style="font-size:1.4rem;font-weight:bold;color:#333;margin-bottom:10px;">{lbl}: {val}</div><div style="font-size:0.9rem;color:#666;">{det}</div></div>'
            else:
                html_cards += f'<div class="carousel-card status-secondary"><h4>{bim}</h4><p style="color:#999;">Sem dados.</p></div>'
        st.markdown(html_cards + '</div>', unsafe_allow_html=True)

        # Gráficos de barra por indicador
        ind_charts = [c for c in INDICADORES_DESEJADOS if c in df_w.columns]
        if ind_charts:
            st.markdown("#### Evolução dos Indicadores")
            cols = st.columns(2)
            for i, ind in enumerate(ind_charts):
                df_i = df_w[["bimestre", ind]].dropna()
                df_i[ind] = pd.to_numeric(df_i[ind], errors='coerce')
                df_i = df_i.dropna()
                
                if not df_i.empty:
                    fig = px.bar(df_i, x="bimestre", y=ind, title=ind, text_auto=True)
                    fig.update_layout(height=300)
                    cols[i%2].plotly_chart(fig, use_container_width=True)

    elif page == "Estudantes em Atenção":
        st.header("⚠️ Estudantes em Atenção")
        st.write("Visão tabular da base unificada (Pivotada).")
        st.dataframe(df_larga)

    elif page == "Base Completa":
        st.header("📂 Base Completa")
        st.write("Dados brutos (Formato Longo).")
        st.dataframe(df)

if __name__ == "__main__":
    main()