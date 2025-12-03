import streamlit as st
import pandas as pd
import numpy as np
import gspread
from google.oauth2.service_account import Credentials
import os
import re
import unicodedata
from datetime import datetime
import plotly.express as px
import base64
from fpdf import FPDF
import statsmodels.api as sm

# ==============================================================================
# 0. CONFIGURAÇÃO DA PÁGINA E ESTILOS (CSS)
# ==============================================================================
st.set_page_config(
    page_title="CAfe.Lab | Dashboard Educacional",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Profissional
st.markdown("""
<style>
    /* Container dos cards */
    .card-container {
        display: flex;
        flex-wrap: nowrap;
        gap: 20px;
        overflow-x: auto;
        padding: 20px 5px;
        padding-bottom: 30px;
    }
    
    /* Card Boletim */
    .card-boletim {
        background-color: #ffffff;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        padding: 20px;
        min-width: 280px;
        border-left: 8px solid #ccc;
        transition: transform 0.2s;
    }
    .card-boletim:hover { transform: translateY(-5px); }
    
    .card-header {
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 700;
        font-size: 1.2rem;
        color: #444;
        text-transform: uppercase;
        border-bottom: 2px solid #f0f0f0;
        padding-bottom: 10px;
        margin-bottom: 15px;
    }
    
    .main-score-container { text-align: center; margin-bottom: 15px; }
    .main-score-label { font-size: 0.75rem; color: #888; text-transform: uppercase; letter-spacing: 1px; }
    .main-score { font-size: 2.8rem; font-weight: 800; color: #2c3e50; line-height: 1.1; }
    
    .sub-scores {
        display: flex;
        justify-content: space-between;
        background-color: #f8f9fa;
        padding: 10px;
        border-radius: 8px;
    }
    .sub-item { text-align: center; flex: 1; }
    .sub-item span { display: block; font-size: 1.1rem; font-weight: 700; color: #333; }
    .sub-item label { font-size: 0.7rem; color: #666; text-transform: uppercase; }
    
    /* Status Colors */
    .status-aprovado { border-left-color: #28a745 !important; }
    .status-atencao { border-left-color: #ffc107 !important; }
    .status-critico { border-left-color: #dc3545 !important; }
    .status-neutro { border-left-color: #6c757d !important; }

    /* Scrollbar */
    .card-container::-webkit-scrollbar { height: 8px; }
    .card-container::-webkit-scrollbar-track { background: #f1f1f1; border-radius: 4px; }
    .card-container::-webkit-scrollbar-thumb { background: #ccc; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 1. CONSTANTES E MAPEAMENTOS
# ==============================================================================

IDS_PLANILHAS = {
    "621": "16s2R-poDNNnd2SMwuq5HIsRmD8ax1J4nI2AABi-bCs4",
    "624": "1Q0yiIRIgsnLAytPVRtwe8_-RbRILRb2-HUEsztc89Rk",
    "711": "1HMjzbAKyDCvJh9CO8T2isGA04EjVoHlCgnzgu-s1mh0",
    "712": "1b_39FjRINpB6ybTrHZ1-j41CBzHqYIOozx_4RtUY9bY",
    "713": "17u8yE9tIieA7VsojilEJXANirXjKceF80y3AXzBXORo"
}

URLS_CONTEXTO = {
    "SDQ_621": "1fycU1axN4cWEVkHB8NPJ2mt27XXbSOmoLw6E5lhxbmQ",
    "SDQ_624": "1aji4nLBc1dbEkFJVWUeMbG3LgNa-dQi_xjA_epwxxYw",
    "SDQ_711": "1YFZPfPw7sT6J4W7_kYIoKWf4Xo484SkputcLFicO7YA",
    "SDQ_712": "1P6Ghbdnyx4tpRa6Df-g7lOZtuGpnEgNNmA4cHZuAYMg",
    "SDQ_713": "16H47jOIqqrJXKIQ3UMa5maVlEpJjJ-_4URiGOI3fZA8",
    "NSE_621": "1OjdXbcQvyP-aWhhPI9ejjgEWSizs-FcObjY0e1Zz23Y",
    "NSE_624": "1w3TEHcQtDuFHpEqyutolyALl1QvhnMjMqFFWIFrpKvw",
    "NSE_711": "1UNpAdfUZDVrQ8xnoW911reclkO7spaE_lQRDxbBtDg4",
    "NSE_712": "1SWm8QRZ3Y3ydhEmp6y-Dti_o8ei9ufZe2aDFmOx2CFs",
    "NSE_713": "1JBMKRv1jtmcQ9zq8-yl3ti3d0oWZ0OKPHT1RDLJfM00",
    "GAD7_621": "1HZMAqD5_5OcPkbTbaa1STtrP_dJHWGh0d-lm1i_gWg4",
    "GAD7_624": "1QuTfi7g0x_uZz5BAeJEyM2yATexOMTBJxdg6d8MeMgA",
    "GAD7_711": "16ap1E52_9VFkSz83-yKgokGlUmFcK0V1NYB06564Mmo",
    "GAD7_713": "1m38s5mEUDm-tzfp9op-EKD-qmjGZbrPb8TWADfx5bz4"
}

ARQUIVO_CREDENCIAIS = "credentials.json"

MAPA_INDICADORES = {
    "av1_nota_final": "AV1",
    "av2_nota_final": "AV2",
    "av3_nota_final": "AV3",
    "nota_global": "Nota Global",
    "nota_global_acumulada": "Nota Global Acumulada",
    "percentual_presencas": "Percentual de Presenças",
    "av1_percentual_de_atividades_feitas": "AV1 %",
    "av2_percentual_de_atividades_feitas": "AV2 %",
    "av3_percentual_de_atividades_feitas": "AV3 %",
    "av1_media_percentual": "AV1 Média %",
    "av2_media_percentual": "AV2 Média %",
    "av3_media_percentual": "AV3 Média %"
}

NIVEL_BIMESTRE = ["1º Bimestre", "2º Bimestre", "3º Bimestre", "4º Bimestre"]
INDICADORES_DESEJADOS = list(MAPA_INDICADORES.values())

MAXIMOS = {
    "1º Bimestre": {"AV1": 5, "AV2": 5, "AV3": 10, "Nota Global": 20, "Nota Global Acumulada": 20},
    "2º Bimestre": {"AV1": 5, "AV2": 5, "AV3": 10, "Nota Global": 20, "Nota Global Acumulada": 40},
    "3º Bimestre": {"AV1": 5, "AV2": 10, "AV3": 15, "Nota Global": 30, "Nota Global Acumulada": 70},
    "4º Bimestre": {"AV1": 5, "AV2": 10, "AV3": 15, "Nota Global": 30, "Nota Global Acumulada": 100},
}

# ==============================================================================
# 2. FUNÇÕES UTILITÁRIAS
# ==============================================================================

def normalizar_nome_coluna(col):
    if not isinstance(col, str): return str(col)
    col = col.lower()
    col = unicodedata.normalize('NFKD', col).encode('ascii', 'ignore').decode('utf-8')
    col = re.sub(r'\s+', '_', col)
    col = re.sub(r'[^a-z0-9_]', '', col)
    return col

def normalizar_nome_aluno(nome):
    if not isinstance(nome, str): return ""
    return normalizar_nome_coluna(nome).strip()

def clean_number(x):
    if isinstance(x, str): return x.replace(',', '.')
    return x

def safe_float(val):
    try: return float(val)
    except: return None

def get_status_class(valor, indicador, bimestre):
    try:
        if valor is None or pd.isna(valor): return "status-neutro"
        v = float(valor)
        if "Presença" in indicador:
            return "status-aprovado" if v >= 75 else "status-critico"
        chave = "Nota Global" if "Global" in indicador else "AV3" if "AV3" in indicador else "AV1" if "AV1" in indicador else "AV2"
        maximo = MAXIMOS.get(bimestre, {}).get(chave, 10)
        if v >= (maximo * 0.6): return "status-aprovado"
        if v >= (maximo * 0.4): return "status-atencao"
        return "status-critico"
    except: return "status-neutro"

def get_color_hex(status_class):
    if status_class == "status-aprovado": return "#16a34a"
    if status_class == "status-atencao": return "#ea580c"
    if status_class == "status-critico": return "#dc2626"
    return "#6c757d"

# ==============================================================================
# 3. GERAÇÃO DE RELATÓRIOS (HTML & PDF)
# ==============================================================================

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Relatório de Desempenho do Estudante', 0, 1, 'C')
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
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, clean_text("Resumo dos Bimestres"), 0, 1)
    pdf.set_font("Arial", "", 10)
    for bim in NIVEL_BIMESTRE:
        row = df_aluno[df_aluno["bimestre"] == bim]
        if not row.empty:
            data = row.iloc[0]
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 10, clean_text(bim), 0, 1)
            pdf.set_font("Arial", "", 10)
            for k in ["AV1", "AV2", "AV3", "Nota Global", "Percentual de Presenças"]:
                if k in data and pd.notna(data[k]):
                    v = data[k]
                    val_str = f"{float(v):.1f}" if isinstance(v, (int, float)) else str(v)
                    pdf.cell(0, 6, f"{clean_text(k)}: {clean_text(val_str)}", 0, 1)
            pdf.ln(2)
    return bytes(pdf.output())

def gerar_html_relatorio(nome_aluno, turma, df_aluno, df_contexto_aluno):
    """Gera HTML no estilo solicitado pelo usuário."""
    
    # Extração de Dados
    def get_val(bim, col):
        row = df_aluno[df_aluno["bimestre"] == bim]
        if row.empty or col not in row.columns or pd.isna(row[col].values[0]): return 0.0
        return float(row[col].values[0])

    av1 = [get_val(b, "AV1") for b in NIVEL_BIMESTRE]
    av2 = [get_val(b, "AV2") for b in NIVEL_BIMESTRE]
    av3 = [get_val(b, "AV3") for b in NIVEL_BIMESTRE]
    glob = [get_val(b, "Nota Global") for b in NIVEL_BIMESTRE]
    acum = [get_val(b, "Nota Global Acumulada") for b in NIVEL_BIMESTRE]
    freq = [get_val(b, "Percentual de Presenças") for b in NIVEL_BIMESTRE]
    
    final_score = acum[-1] if acum else 0.0
    status_text = "Aprovado" if final_score >= 50 else "Recuperação"
    status_class = "status-aprovado" if final_score >= 50 else "status-recuperacao"
    badge_class = "bg-aprovado" if final_score >= 50 else "bg-recuperacao"
    
    # Contexto
    gad = int(df_contexto_aluno.get("gad7_total", 0)) if not pd.isna(df_contexto_aluno.get("gad7_total")) else 0
    sdq = int(df_contexto_aluno.get("sdq_total", 0)) if not pd.isna(df_contexto_aluno.get("sdq_total")) else 0
    
    # Template HTML
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
            body {{ font-family: 'Inter', sans-serif; background-color: #3f3f46; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
            .report-page {{ width: 210mm; min-height: 297mm; margin: 0 auto 30px auto; background: white; padding: 10mm; position: relative; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5); overflow: hidden; }}
            .watermark {{ position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%) rotate(-45deg); font-size: 6rem; font-weight: 900; z-index: 0; pointer-events: none; padding: 1rem 2rem; border-radius: 1rem; text-transform: uppercase; white-space: nowrap; opacity: 0.1; border: 8px solid currentColor; }}
            .status-aprovado {{ color: #16a34a; }}
            .status-recuperacao {{ color: #ea580c; }}
            .bg-aprovado {{ background-color: #dcfce7; color: #166534; }}
            .bg-recuperacao {{ background-color: #ffedd5; color: #9a3412; }}
            @media print {{ body {{ background: white; margin: 0; }} .no-print {{ display: none !important; }} .report-page {{ margin: 0; box-shadow: none; page-break-after: always; width: 100%; height: 100vh; }} }}
        </style>
    </head>
    <body>
        <div class="no-print fixed top-0 left-0 w-full bg-gray-900 text-white p-4 shadow-xl z-50 flex justify-between items-center">
            <h1 class="text-xl font-bold">Relatório Individual</h1>
            <button onclick="window.print()" class="bg-blue-600 hover:bg-blue-500 text-white font-bold py-2 px-6 rounded shadow flex items-center gap-2 transition"><i class="fas fa-print"></i> IMPRIMIR</button>
        </div>
        <div style="height: 80px;" class="no-print"></div>

        <div class="report-page">
            <div class="watermark {status_class}">{status_text}</div>
            <header class="flex justify-between items-end border-b-4 border-slate-800 pb-4 mb-6 relative z-10">
                <div>
                    <h1 class="text-3xl font-black text-slate-800 uppercase tracking-tight">Relatório de Desempenho Analítico</h1>
                    <p class="text-slate-500 font-medium mt-1">Detalhamento por Avaliação e Métricas Globais • 2024</p>
                </div>
                <div class="text-right">
                    <div class="{badge_class} font-bold px-4 py-1 rounded text-sm mb-1 inline-block border">SITUAÇÃO FINAL</div>
                    <div class="text-4xl font-black uppercase {status_class}">{status_text}</div>
                </div>
            </header>

            <section class="bg-slate-50 rounded-xl p-4 mb-6 border border-slate-200 relative z-10">
                <div class="flex justify-between items-center">
                    <div>
                        <h2 class="text-2xl font-bold text-slate-800">{nome_aluno}</h2>
                        <p class="text-sm text-slate-600">Turma {turma} • 6º Ano</p>
                    </div>
                    <div class="text-center px-4">
                        <span class="block text-xs font-bold text-slate-400 uppercase">Nota Global Final</span>
                        <span class="text-xl font-black {status_class}">{final_score:.1f}</span>
                    </div>
                </div>
            </section>

            <section class="mb-8 relative z-10">
                <div class="bg-white p-2 rounded-lg border border-slate-100 shadow-sm">
                    <h3 class="text-sm font-bold text-slate-700 mb-2 border-l-4 border-indigo-500 pl-2 uppercase">Evolução Anual</h3>
                    <div class="h-64 relative"><canvas id="chart-evolution"></canvas></div>
                </div>
            </section>

            <section class="mb-8 relative z-10">
                <h3 class="text-sm font-bold text-slate-700 mb-4 border-l-4 border-slate-500 pl-2 uppercase">Quadro de Notas</h3>
                <div class="overflow-hidden rounded-lg border border-slate-200 shadow-sm">
                    <table class="min-w-full text-sm text-center">
                        <thead class="bg-slate-800 text-white font-bold uppercase text-xs">
                            <tr>
                                <th class="px-2 py-2 text-left">Bimestre</th>
                                <th class="px-2 py-2 bg-blue-900">AV1</th>
                                <th class="px-2 py-2 bg-blue-800">AV2</th>
                                <th class="px-2 py-2 bg-blue-900">AV3</th>
                                <th class="px-2 py-2 bg-indigo-900 text-yellow-300">Global</th>
                                <th class="px-2 py-2 bg-purple-900 text-white">Acum.</th>
                                <th class="px-2 py-2 bg-slate-100 text-slate-600">Freq.</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-200 bg-white">
    """
    
    for i, bim in enumerate(NIVEL_BIMESTRE):
        html += f"""
        <tr class="hover:bg-slate-50">
            <td class="px-2 py-2 text-left font-bold text-slate-700">{bim}</td>
            <td class="px-2 py-2">{av1[i]:.1f}</td>
            <td class="px-2 py-2">{av2[i]:.1f}</td>
            <td class="px-2 py-2">{av3[i]:.1f}</td>
            <td class="px-2 py-2 font-bold text-indigo-700 bg-indigo-50">{glob[i]:.1f}</td>
            <td class="px-2 py-2 font-black text-purple-700 bg-purple-50">{acum[i]:.1f}</td>
            <td class="px-2 py-2">{freq[i]:.0f}%</td>
        </tr>
        """
        
    html += f"""
                        </tbody>
                    </table>
                </div>
            </section>

            <section class="grid grid-cols-2 gap-8 relative z-10">
                <div class="bg-orange-50 p-4 rounded-lg border border-orange-200">
                    <h3 class="text-xs font-bold text-orange-800 uppercase mb-2">Painel Socioemocional</h3>
                    <div class="flex justify-between items-center mb-2">
                        <span class="text-sm text-orange-900">Ansiedade (GAD-7)</span>
                        <span class="bg-white border border-orange-200 text-orange-800 text-xs font-bold px-2 py-1 rounded">{gad} pts</span>
                    </div>
                    <div class="flex justify-between items-center">
                        <span class="text-sm text-orange-900">Comportamento (SDQ)</span>
                        <span class="bg-white border border-orange-200 text-orange-800 text-xs font-bold px-2 py-1 rounded">{sdq} pts</span>
                    </div>
                </div>
                 <div class="bg-slate-50 p-4 rounded-lg border border-slate-200 flex items-center justify-center text-center">
                    <div>
                         <p class="text-xs font-bold text-slate-500 uppercase mb-1">Status Final</p>
                         <p class="text-sm text-slate-700">O estudante atingiu <strong>{final_score:.1f}</strong> pontos acumulados.</p>
                    </div>
                </div>
            </section>

            <footer class="absolute bottom-10 left-10 right-10 pt-4 border-t border-slate-200">
                 <div class="flex justify-between text-[10px] text-slate-400 uppercase">
                    <span>CAfe.Lab - Análise Pedagógica Turma {turma}</span>
                    <span>Documento Processado Digitalmente</span>
                </div>
            </footer>
        </div>

        <script>
            const ctx = document.getElementById('chart-evolution').getContext('2d');
            Chart.register(ChartDataLabels);
            new Chart(ctx, {{
                type: 'bar',
                data: {{
                    labels: {NIVEL_BIMESTRE},
                    datasets: [
                        {{
                            type: 'line',
                            label: 'Acumulado',
                            data: {acum},
                            borderColor: '#7e22ce',
                            backgroundColor: '#7e22ce',
                            borderWidth: 2,
                            yAxisID: 'y1',
                            datalabels: {{ align: 'top', anchor: 'start', color: '#7e22ce', font: {{ weight: 'bold', size: 10 }}, formatter: (v) => v }}
                        }},
                        {{
                            label: 'Global Bimestre',
                            data: {glob},
                            backgroundColor: '#4f46e5',
                            yAxisID: 'y',
                            datalabels: {{ color: 'white', font: {{ size: 9 }}, anchor: 'end', align: 'bottom' }}
                        }}
                    ]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{ legend: {{ position: 'bottom' }}, datalabels: {{ display: true }} }},
                    scales: {{
                        x: {{ grid: {{ display: false }} }},
                        y: {{ type: 'linear', position: 'left', max: 30, beginAtZero: true }},
                        y1: {{ type: 'linear', position: 'right', max: 100, beginAtZero: true, grid: {{ display: false }} }}
                    }}
                }}
            }});
        </script>
    </body>
    </html>
    """
    return html

# ==============================================================================
# 4. ETL (CARREGAMENTO E PROCESSAMENTO)
# ==============================================================================

def processar_contexto_dinamico(client):
    """
    Implementação fiel ao script R para SDQ, NSE e GAD-7.
    """
    dfs = []
    
    # Mapeamentos do R
    map_nse = {"a": 0, "b": 1, "c": 2, "d": 3, "e": 4} # R usa A=0, B=1...
    map_sdq = {"a": 0, "b": 1, "c": 2}
    map_gad = {"a": 0, "b": 1, "c": 2, "d": 3}
    
    for k, url in URLS_CONTEXTO.items():
        try:
            sh = client.open_by_key(url)
            vals = sh.get_worksheet(0).get_all_values()
            if not vals: continue
            
            headers = [normalizar_nome_coluna(h) for h in vals[0]]
            df = pd.DataFrame(vals[1:], columns=headers)
            df["turma"] = k.split("_")[1]
            
            # --- PROCESSAMENTO SDQ ---
            if "SDQ" in k:
                # Renomear colunas (Mapeamento R)
                rename_sdq = {
                    "eu_tento_ser_legal": "sconsid", "no_consigo": "srestles", "muitas_vezes": "ssomatic",
                    "tenho_boa_vontade": "sshares", "fico_muito_bravo": "stantrum", "eu_quase_sempre": "sloner",
                    "geralmente_sou_obediente": "sobeys", "tenho_muitas_preocupa": "sworries", "tento_ajudar": "scaring",
                    "estou_sempre_agitado": "sfidgety", "tenho_pelo_menos_uma": "sfriend", "eu_brigo_muito": "sfights",
                    "frequentemente_estou_infeliz": "sunhappy", "em_geral_sou_querido": "spopular", "perco_a_concentr": "sdistrac",
                    "fico_nervoso": "sclingy", "sou_legal_com_crianas": "skind", "frequentemente_sou_acusado": "slies",
                    "os_outros_jovens": "sbullied", "frequentemente_me_ofereo": "shelpout", "eu_penso": "sreflect",
                    "pego_coisas": "ssteals", "doume_melhor": "soldbest", "tenho_muitos_medos": "safraid",
                    "consigo_terminar": "sattends"
                }
                
                # Aplica rename parcial (startswith logic do R simulada)
                cols_new = {}
                for col in df.columns:
                    for key, val in rename_sdq.items():
                        if col.startswith(key):
                            cols_new[col] = val
                            break
                df.rename(columns=cols_new, inplace=True)
                
                # Converter valores A, B, C
                cols_sdq = list(rename_sdq.values())
                for c in cols_sdq:
                    if c in df.columns:
                        df[c] = df[c].astype(str).str.lower().map(map_sdq).fillna(np.nan)
                
                # Inverter itens (2 - x)
                for c in ["sobeys", "sfriend", "spopular", "sreflect", "sattends"]:
                    if c in df.columns: df[c] = 2 - df[c]
                
                # Calcular Subescalas
                def calc_sub(row, itens):
                    vals = [row[i] for i in itens if i in row and not pd.isna(row[i])]
                    return sum(vals) if len(vals) >= 3 else np.nan

                df["sdq_emocional"] = df.apply(lambda r: calc_sub(r, ["ssomatic", "sworries", "sunhappy", "sclingy", "safraid"]), axis=1)
                df["sdq_conduta"] = df.apply(lambda r: calc_sub(r, ["stantrum", "sobeys", "sfights", "slies", "ssteals"]), axis=1)
                df["sdq_hiperatividade"] = df.apply(lambda r: calc_sub(r, ["srestles", "sfidgety", "sdistrac", "sreflect", "sattends"]), axis=1)
                df["sdq_pares"] = df.apply(lambda r: calc_sub(r, ["sloner", "sfriend", "spopular", "sbullied", "soldbest"]), axis=1)
                df["sdq_prosocial"] = df.apply(lambda r: calc_sub(r, ["sconsid", "sshares", "scaring", "skind", "shelpout"]), axis=1)
                
                df["sdq_total"] = df[["sdq_emocional", "sdq_conduta", "sdq_hiperatividade", "sdq_pares"]].sum(axis=1, min_count=3)

            # --- PROCESSAMENTO NSE ---
            elif "NSE" in k:
                # Renomear
                rename_nse = {
                    "qual__a_maior_escolaridade_da_sua_me": "escolaridade_mae",
                    "qual__a_maior_escolaridade_do_seu_pai": "escolaridade_pai",
                    "quantas_geladeiras": "qtd_geladeiras", "quantos_computadores": "qtd_computadores",
                    "quantos_quartos": "qtd_quartos", "quantas_televises": "qtd_televisoes",
                    "quantos_banheiros": "qtd_banheiros", "quantos_carros": "qtd_carros",
                    "quantos_celulares": "qtd_celulares", "na_sua_casa_tem_tv": "tv_internet",
                    "na_sua_casa_tem_rede_wifi": "wifi", "na_sua_casa_tem_mesa": "mesa_estudo",
                    "na_sua_casa_tem_garagem": "garagem", "na_sua_casa_tem_forno": "microondas",
                    "na_sua_casa_tem_aspirador": "aspirador", "na_sua_casa_tem_mquina": "maquina_lavar",
                    "na_sua_casa_tem_freezer": "freezer", "qual__o_seu_gnero": "genero",
                    "qual__a_sua_cor_ou_raa": "cor_raca"
                }
                cols_new = {}
                for col in df.columns:
                    for key, val in rename_nse.items():
                        if key in col:
                            cols_new[col] = val
                            break
                df.rename(columns=cols_new, inplace=True)
                
                # Converter A-E
                cols_calc_inse = ["escolaridade_mae", "escolaridade_pai", "qtd_geladeiras", "qtd_computadores", 
                                  "qtd_quartos", "qtd_televisoes", "qtd_banheiros", "qtd_carros", "qtd_celulares",
                                  "tv_internet", "wifi", "mesa_estudo", "garagem", "microondas", "aspirador", 
                                  "maquina_lavar", "freezer"]
                
                for c in cols_calc_inse:
                    if c in df.columns:
                        df[c] = df[c].astype(str).str.lower().map(map_nse).fillna(np.nan)
                
                # Calcular INSE (Média)
                cols_present = [c for c in cols_calc_inse if c in df.columns]
                if cols_present:
                    df["inse"] = df[cols_present].mean(axis=1, skipna=True)

            # --- PROCESSAMENTO GAD-7 ---
            elif "GAD" in k:
                rename_gad = {
                    "nas_ltimas_2_semanas": "gad1", "no_conseguir_parar": "gad2", "preocuparse_demais": "gad3",
                    "ter_dificuldade_para_relaxar": "gad4", "sentirse_to_inquietoa": "gad5", 
                    "ficar_facilmente_irritadoa": "gad6", "sentir_medo_como": "gad7"
                }
                cols_new = {}
                for col in df.columns:
                    for key, val in rename_gad.items():
                        if key in col:
                            cols_new[col] = val
                            break
                df.rename(columns=cols_new, inplace=True)
                
                cols_gad = list(rename_gad.values())
                for c in cols_gad:
                    if c in df.columns:
                        df[c] = df[c].astype(str).str.lower().map(map_gad).fillna(np.nan)
                
                cols_present = [c for c in cols_gad if c in df.columns]
                if cols_present:
                    df["gad7_total"] = df[cols_present].sum(axis=1, min_count=3)

            dfs.append(df)
        except Exception as e:
            print(f"Erro processando {k}: {e}")
            continue
            
    if not dfs: return pd.DataFrame()
    
    df_full = pd.concat(dfs, ignore_index=True)
    df_full["chave"] = df_full["nome_estudante"].apply(normalizar_nome_aluno)
    
    # Agrupar por aluno para juntar colunas de diferentes planilhas (SDQ, NSE, GAD)
    # 'first' funciona bem pq as colunas são disjuntas entre os tipos de contexto
    return df_full.groupby(["chave", "turma"], as_index=False).first()

@st.cache_data(ttl=600)
def carregar_dados_completos():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    credentials = None
    try:
        if hasattr(st, "secrets") and "gsheets" in st.secrets:
            credentials = Credentials.from_service_account_info(st.secrets["gsheets"], scopes=scopes)
    except: pass
    if not credentials and os.path.exists(ARQUIVO_CREDENCIAIS):
        credentials = Credentials.from_service_account_file(ARQUIVO_CREDENCIAIS, scopes=scopes)
    if not credentials: st.error("Credenciais não encontradas."); st.stop()
    client = gspread.authorize(credentials)
    
    # 1. Notas
    lista_notas = []
    for turma, sheet_id in IDS_PLANILHAS.items():
        try:
            sh = client.open_by_key(sheet_id)
            vals = sh.get_worksheet(0).get_all_values()
            if vals:
                headers = [normalizar_nome_coluna(h) for h in vals[0]]
                df = pd.DataFrame(vals[1:], columns=headers)
                df = df.loc[:, ~df.columns.duplicated()]
                if 'turma' in df.columns: df = df.drop(columns=['turma'])
                df['turma'] = str(turma)
                lista_notas.append(df)
        except: pass
    if not lista_notas: return pd.DataFrame()
    df_notas_bruto = pd.concat(lista_notas, ignore_index=True)
    
    # Melt Notas
    sufixos = {"_primeirobi": "1º Bimestre", "_segundobi": "2º Bimestre", "_terceirobi": "3º Bimestre", "_quartobi": "4º Bimestre"}
    cols_fixas = [c for c in ["nome_estudante", "turma"] if c in df_notas_bruto.columns]
    cols_melt = [c for c in df_notas_bruto.columns if any(c.endswith(s) for s in sufixos) and not c.startswith("av1_c")]
    
    df_long = df_notas_bruto.melt(id_vars=cols_fixas, value_vars=cols_melt, var_name="indicador_cru", value_name="Valor")
    
    def parse_ind(r):
        ic = r["indicador_cru"]
        for s, b in sufixos.items():
            if ic.endswith(s): return pd.Series([b, MAPA_INDICADORES.get(ic.replace(s, ""), ic.replace(s, ""))])
        return pd.Series([None, None])
        
    df_long[["bimestre", "tipoindicador"]] = df_long.apply(parse_ind, axis=1)
    df_long = df_long.dropna(subset=["tipoindicador"]) 
    df_long["Valor"] = pd.to_numeric(df_long["Valor"].apply(clean_number), errors="coerce")
    df_long["chave"] = df_long["nome_estudante"].apply(normalizar_nome_aluno)
    
    # 2. Contexto
    df_ctx = processar_contexto_dinamico(client)
    
    # 3. Merge
    if not df_ctx.empty:
        # Remove colunas comuns que não sejam chave
        cols_drop = [c for c in df_ctx.columns if c in df_long.columns and c not in ["chave", "turma"]]
        df_final = pd.merge(df_long, df_ctx.drop(columns=cols_drop), on=["chave", "turma"], how="left")
    else:
        df_final = df_long
        
    return df_final

def get_base_larga_analitica(df):
    """Pivota indicadores para colunas (AV1, AV2...) mantendo contexto."""
    df_pivot = df.pivot_table(index=["chave", "turma", "bimestre", "nome_estudante"], 
                              columns="tipoindicador", values="Valor", aggfunc='first').reset_index()
    
    # Recuperar contexto (que foi perdido no pivot pois não varia por indicador)
    # Pega contexto do primeiro registro de cada aluno/turma
    cols_ctx = [c for c in df.columns if c not in ["tipoindicador", "Valor", "indicador_cru", "bimestre"]]
    df_ctx = df[cols_ctx].drop_duplicates(subset=["chave", "turma"])
    
    df_final = pd.merge(df_pivot, df_ctx, on=["chave", "turma", "nome_estudante"], how="left")
    return df_final

# ==============================================================================
# 5. DASHBOARD PRINCIPAL
# ==============================================================================

def main():
    try:
        with st.spinner("Carregando dados..."):
            df = carregar_dados_completos()
            if df.empty: st.warning("Sem dados."); st.stop()
            df_larga = get_base_larga_analitica(df)
    except Exception as e:
        st.error(f"Erro crítico: {e}"); st.stop()

    with st.sidebar:
        st.title("CAfe.Lab v9.0")
        st.markdown("**Dr. William Melo**")
        page = st.radio("Menu", ["Agregado & Correlações", "Boletim Individual", "Estudantes em Atenção", "Base Completa"])
        if st.button("Recarregar Dados"): st.cache_data.clear(); st.rerun()

    # --- AGREGADO ---
    if page == "Agregado & Correlações":
        st.header("📊 Análise Agregada")
        c1, c2, c3 = st.columns(3)
        turmas = ["Todas"] + sorted(df["turma"].unique().astype(str).tolist())
        t_sel = c1.selectbox("Turma", turmas)
        
        inds = sorted([c for c in df["tipoindicador"].unique() if c])
        i_sel = c2.selectbox("Indicador", inds, index=inds.index("Nota Global") if "Nota Global" in inds else 0)
        
        cols_cat = [c for c in df_larga.columns if df_larga[c].nunique() < 15 and df_larga[c].nunique() > 1 
                   and c not in ['nome_estudante', 'chave', 'turma', 'bimestre']]
        d_sel = c3.selectbox("Agrupar por", ["Nenhum"] + sorted(cols_cat))
        
        df_chart = df_larga.copy()
        if t_sel != "Todas": df_chart = df_chart[df_chart["turma"] == t_sel]
        
        # Gráfico de Barras
        if i_sel in df_chart.columns:
            grp = ["bimestre", "turma"] + ([d_sel] if d_sel != "Nenhum" else [])
            df_grp = df_chart.groupby(grp)[i_sel].mean().reset_index()
            
            fig = px.bar(df_grp, x="bimestre", y=i_sel, color=d_sel if d_sel != "Nenhum" else None,
                         barmode="group", facet_col="turma" if t_sel == "Todas" else None,
                         text_auto='.1f', title=f"Média de {i_sel}")
            st.plotly_chart(fig, use_container_width=True)
            
        st.markdown("---")
        st.subheader("🔗 Mapa de Correlações")
        
        cols_num = df_larga.select_dtypes(include=[np.number]).columns.tolist()
        vars_corr = st.multiselect("Selecione Variáveis para Cruzamento", cols_num, default=["inse", "Nota Global", "Percentual de Presenças"])
        
        if len(vars_corr) > 1:
            corr = df_chart[vars_corr].corr()
            fig_h = px.imshow(corr, text_auto=True, color_continuous_scale="RdBu_r", aspect="auto", title="Matriz de Correlação")
            st.plotly_chart(fig_h, use_container_width=True)
            
            c_sc1, c_sc2 = st.columns(2)
            vx = c_sc1.selectbox("Eixo X (Scatter)", vars_corr, index=0)
            vy = c_sc2.selectbox("Eixo Y (Scatter)", vars_corr, index=1)
            fig_s = px.scatter(df_chart, x=vx, y=vy, color="turma", trendline="ols", hover_data=["nome_estudante"])
            st.plotly_chart(fig_s, use_container_width=True)

    # --- INDIVIDUAL ---
    elif page == "Boletim Individual":
        st.header("👤 Boletim Individual")
        c1, c2 = st.columns([1, 3])
        t_ind = c1.selectbox("Turma", ["Todas"] + sorted(df["turma"].unique().astype(str).tolist()))
        lista = df["nome_estudante"].unique() if t_ind == "Todas" else df[df["turma"]==t_ind]["nome_estudante"].unique()
        aluno_sel = c2.selectbox("Estudante", sorted(lista))
        
        d_aluno = df_larga[df_larga["nome_estudante"] == aluno_sel]
        
        # Contexto & Downloads
        if not d_aluno.empty:
            row_ctx = d_aluno.iloc[0]
            
            # Downloads
            c_dl1, c_dl2, c_dl3 = st.columns(3)
            html_rep = gerar_html_relatorio(aluno_sel, row_ctx["turma"], d_aluno, row_ctx)
            c_dl1.download_button("📄 Relatório Web (HTML)", html_rep, f"Relatorio_{normalizar_nome_aluno(aluno_sel)}.html", "text/html")
            pdf_bytes = gerar_pdf_aluno(aluno_sel, row_ctx["turma"], d_aluno)
            c_dl2.download_button("📄 Relatório Simples (PDF)", pdf_bytes, f"Relatorio_{normalizar_nome_aluno(aluno_sel)}.pdf", "application/pdf")
            c_dl3.download_button("💾 Dados CSV", d_aluno.to_csv(index=False).encode('utf-8'), f"Dados_{normalizar_nome_aluno(aluno_sel)}.csv", "text/csv")
            
            st.markdown("---")
            
            # Cards de Bimestre
            st.subheader("Desempenho por Bimestre")
            html_cards = '<div class="card-container">'
            for bim in NIVEL_BIMESTRE:
                row = d_aluno[d_aluno["bimestre"] == bim]
                
                # Extrair valores com segurança
                def get_v(c): return row[c].values[0] if (c in row.columns and not pd.isna(row[c].values[0])) else None
                
                av1, av2, av3 = get_v("AV1"), get_v("AV2"), get_v("AV3")
                glob, glob_ac = get_v("Nota Global"), get_v("Nota Global Acumulada")
                
                # Formatação
                s_av1 = f"{av1:.1f}" if av1 is not None else "-"
                s_av2 = f"{av2:.1f}" if av2 is not None else "-"
                s_av3 = f"{av3:.1f}" if av3 is not None else "-"
                s_glob = f"{glob:.1f}" if glob is not None else "-"
                s_ac = f"{glob_ac:.1f}" if glob_ac is not None else "-"
                
                status_cls = get_status_class(glob, "Nota Global", bim)
                
                html_cards += f"""
                <div class="card-boletim {status_cls}">
                    <div class="card-header">{bim}</div>
                    <div class="main-score-container">
                        <div class="main-score-label">Global</div>
                        <div class="main-score">{s_glob}</div>
                        <div style="font-size:0.8em; color:#666;">Acumulada: {s_ac}</div>
                    </div>
                    <div class="sub-scores">
                        <div class="sub-item"><label>AV1</label><span>{s_av1}</span></div>
                        <div class="sub-item"><label>AV2</label><span>{s_av2}</span></div>
                        <div class="sub-item"><label>AV3</label><span>{s_av3}</span></div>
                    </div>
                </div>
                """
            html_cards += "</div>"
            st.markdown(html_cards, unsafe_allow_html=True)
            
            # Seção Socioemocional e INSE
            st.markdown("### 🧠 Contexto Socioemocional & INSE")
            c_se1, c_se2, c_se3 = st.columns(3)
            
            # INSE Z-Score
            inse = row_ctx.get("inse", np.nan)
            if not pd.isna(inse):
                turma_inse = df_larga[df_larga["turma"] == row_ctx["turma"]]["inse"]
                media_t, std_t = turma_inse.mean(), turma_inse.std()
                z_score = (inse - media_t) / std_t if std_t > 0 else 0
                c_se1.metric("INSE (Nível Socioeconômico)", f"{inse:.2f}", f"{z_score:+.2f} desvios (vs Turma)")
            else:
                c_se1.metric("INSE", "N/A")
                
            # GAD-7
            gad = row_ctx.get("gad7_total", np.nan)
            cat_gad = "Normal"
            if gad >= 15: cat_gad = "Grave"
            elif gad >= 10: cat_gad = "Moderado"
            elif gad >= 5: cat_gad = "Leve"
            c_se2.metric("Ansiedade (GAD-7)", f"{gad:.0f}" if not pd.isna(gad) else "N/A", cat_gad, delta_color="inverse")
            
            # SDQ
            sdq = row_ctx.get("sdq_total", np.nan)
            cat_sdq = "Normal"
            if sdq >= 17: cat_sdq = "Anormal"
            elif sdq >= 14: cat_sdq = "Limítrofe"
            c_se3.metric("Comportamento (SDQ)", f"{sdq:.0f}" if not pd.isna(sdq) else "N/A", cat_sdq, delta_color="inverse")

            # Gráficos
            st.subheader("Evolução de Indicadores")
            cols_g = st.columns(2)
            inds_plot = ["AV1", "AV2", "AV3", "Nota Global", "Percentual de Presenças"]
            for i, ind in enumerate(inds_plot):
                if ind in d_aluno.columns:
                    fig = px.bar(d_aluno, x="bimestre", y=ind, title=ind, text_auto='.1f')
                    cols_g[i%2].plotly_chart(fig, use_container_width=True)

    # --- ATENÇÃO ---
    elif page == "Estudantes em Atenção":
        st.header("⚠️ Estudantes em Atenção")
        c1, c2 = st.columns(2)
        crit = c1.selectbox("Critério", ["Nota Global Baixa (< 6.0)", "Presença Baixa (< 75%)", "SDQ Alto (>= 17)", "GAD-7 Alto (>= 15)"])
        bim_at = c2.selectbox("Bimestre", NIVEL_BIMESTRE)
        
        df_at = df_larga[df_larga["bimestre"] == bim_at].copy()
        
        if "Nota Global" in crit and "Nota Global" in df_at.columns:
            df_at = df_at[df_at["Nota Global"] < 6.0]
        elif "Presença" in crit and "Percentual de Presenças" in df_at.columns:
            df_at = df_at[df_at["Percentual de Presenças"] < 75]
        elif "SDQ" in crit and "sdq_total" in df_at.columns:
            df_at = df_at[df_at["sdq_total"] >= 17]
        elif "GAD" in crit and "gad7_total" in df_at.columns:
            df_at = df_at[df_at["gad7_total"] >= 15]
            
        st.dataframe(df_at)
        st.download_button("💾 Baixar Lista", df_at.to_csv(index=False).encode('utf-8'), "atencao.csv", "text/csv")

    # --- BASE ---
    elif page == "Base Completa":
        st.header("📂 Base de Dados")
        st.dataframe(df_larga)
        st.download_button("💾 Baixar Base Completa", df_larga.to_csv(index=False).encode('utf-8'), "base_completa.csv", "text/csv")

if __name__ == "__main__":
    main()