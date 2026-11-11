from fastapi import FastAPI, Query, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import pandas as pd
import unicodedata
import glob
import os
import re
import shutil

app = FastAPI(title="CDHEQROO - Asistente Histórico de Transparencia")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("data", exist_ok=True)

def normalizar(texto):
    if not isinstance(texto, str):
        texto = str(texto)
    nfd = unicodedata.normalize('NFD', texto)
    return "".join([c for c in nfd if unicodedata.category(c) != 'Mn']).lower()

def formatear_moneda(valor):
    try:
        return f"{float(valor):,.2f}"
    except:
        return str(valor)

def cargar_base_de_datos_historica():
    archivos = glob.glob("data/**/*.xlsx", recursive=True)
    dfs = []
    for archivo in archivos:
        partes = archivo.replace("\\", "/").split("/")
        fraccion = partes[1].upper() if len(partes) > 1 else "FRACCION_VII"
        anio = partes[2] if len(partes) > 2 else "2026"
        trimestre = partes[3].replace(".xlsx", "").upper() if len(partes) > 3 else "TRIMESTRE_1"
        try:
            df = pd.read_excel(archivo, sheet_name=0)
            df['META_FRACCION'] = fraccion
            df['META_ANIO'] = anio
            df['META_TRIMESTRE'] = trimestre
            dfs.append(df)
        except:
            pass
    if dfs:
        return pd.concat(dfs, ignore_index=True)
    return pd.DataFrame()

@app.get("/", response_class=HTMLResponse)
def interfaz_usuario():
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>CDHEQROO - Repositorio Histórico de Transparencia</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #f4f6f9; margin: 0; padding: 20px; color: #333; }
            .container { max-width: 950px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); }
            h1 { color: #003366; font-size: 24px; margin-bottom: 5px; }
            p.subtitle { color: #666; font-size: 14px; margin-bottom: 20px; border-bottom: 2px solid #e1e8ed; padding-bottom: 15px; }
            
            .tabs { display: flex; gap: 10px; margin-bottom: 20px; }
            .tab-btn { background: #e1e8ed; border: none; padding: 10px 20px; font-size: 15px; font-weight: bold; color: #444; cursor: pointer; border-radius: 6px; transition: 0.3s; }
            .tab-btn.active { background-color: #003366; color: white; }
            .tab-content { display: none; }
            .tab-content.active { display: block; }

            .chat-container { border: 1px solid #ddd; border-radius: 8px; background: #fafafa; display: flex; flex-direction: column; height: 480px; }
            .chat-messages { flex: 1; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; }
            .message { max-width: 85%; padding: 12px 16px; border-radius: 10px; font-size: 14px; line-height: 1.4; }
            .message.bot { background: #e8f4fd; color: #003366; align-self: flex-start; border-left: 4px solid #003366; }
            .message.user { background: #003366; color: white; align-self: flex-end; }
            .chat-input-box { display: flex; padding: 15px; border-top: 1px solid #ddd; background: white; border-radius: 0 0 8px 8px; gap: 10px; }
            
            .admin-form { display: flex; flex-direction: column; gap: 15px; background: #fafafa; padding: 25px; border-radius: 8px; border: 1px solid #ddd; }
            .form-group { display: flex; flex-direction: column; gap: 5px; }
            label { font-weight: bold; font-size: 14px; color: #333; }
            select, input[type="file"] { padding: 10px; border: 2px solid #ddd; border-radius: 6px; font-size: 15px; background: white; outline: none; }
            
            input[type="text"] { flex: 1; padding: 12px; border: 2px solid #ddd; border-radius: 8px; font-size: 16px; outline: none; }
            button.action-btn { background-color: #003366; color: white; border: none; padding: 12px 24px; border-radius: 8px; font-size: 16px; cursor: pointer; font-weight: bold; }
            button.action-btn:hover { background-color: #002244; }
            .alert { padding: 12px; border-radius: 6px; margin-top: 10px; font-size: 14px; display: none; }
            .alert.success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
            .alert.error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Comisión de los Derechos Humanos del Estado de Quintana Roo</h1>
            <p class="subtitle">Repositorio e Histórico Inteligente de Transparencia (Artículo 75)</p>
            
            <div class="tabs">
                <button class="tab-btn active" onclick="cambiarTab('chatTab', event)">🤖 Asistente Conversacional</button>
                <button class="tab-btn" onclick="cambiarTab('adminTab', event)">📁 Carga Histórica (Admin)</button>
            </div>

            <div id="chatTab" class="tab-content active">
                <div class="chat-container">
                    <div class="chat-messages" id="chatMessages">
                        <div class="message bot">¡Hola! Soy tu asistente de transparencia. Pregúntame sobre sueldos, puestos, áreas o estadísticas (ej. "Erick", "¿Quién gana más?", "Sueldos entre 20000 y 40000").</div>
                    </div>
                    <div class="chat-input-box">
                        <input type="text" id="chatInput" placeholder="Escribe tu consulta aquí...">
                        <button class="action-btn" onclick="enviar()">Enviar</button>
                    </div>
                </div>
            </div>

            <div id="adminTab" class="tab-content">
                <div class="admin-form">
                    <h3>Subir Nuevo Formato al Histórico</h3>
                    <p style="font-size:13px; color:#666; margin-top:-5px;">Selecciona la fracción, el año y el trimestre para organizar el archivo en carpetas automáticamente.</p>
                    
                    <div class="form-group">
                        <label>Fracción del Artículo 75:</label>
                        <select id="fraccionSelect">
                            <option value="fraccion_vii">Fracción VII - Remuneraciones</option>
                            <option value="fraccion_viii">Fracción VIII - Viáticos y Gastos</option>
                            <option value="fraccion_xiv">Fracción XIV - Contrataciones</option>
                        </select>
                    </div>

                    <div class="form-group">
                        <label>Año:</label>
                        <select id="anioSelect">
                            <option value="2026">2026</option>
                            <option value="2025">2025</option>
                            <option value="2024">2024</option>
                        </select>
                    </div>

                    <div class="form-group">
                        <label>Trimestre:</label>
                        <select id="trimestreSelect">
                            <option value="trimestre_1">Trimestre 1 (Ene-Mar)</option>
                            <option value="trimestre_2">Trimestre 2 (Abr-Jun)</option>
                            <option value="trimestre_3">Trimestre 3 (Jul-Sep)</option>
                            <option value="trimestre_4">Trimestre 4 (Oct-Dic)</option>
                        </select>
                    </div>

                    <div class="form-group">
                        <label>Archivo Excel (.xlsx):</label>
                        <input type="file" id="fileInput" accept=".xlsx">
                    </div>

                    <button class="action-btn" onclick="subirArchivo()">Subir y Registrar en el Histórico</button>
                    <div class="alert" id="adminAlert"></div>
                </div>
            </div>
        </div>

        <script>
            function cambiarTab(tabId, event) {
                document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
                document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
                document.getElementById(tabId).classList.add('active');
                event.currentTarget.classList.add('active');
            }

            async function enviar() {
                const input = document.getElementById('chatInput');
                const chat = document.getElementById('chatMessages');
                const text = input.value.trim();
                if (!text) return;
                
                chat.innerHTML += `<div class="message user">${text}</div>`;
                input.value = '';
                chat.scrollTop = chat.scrollHeight;

                try {
                    const res = await fetch(`/buscar?q=${encodeURIComponent(text)}`);
                    const data = await res.json();
                    let html = `<div class="message bot">`;
                    if (data.estatus === 'Exito' && data.resultados.length > 0) {
                        html += `Encontré <strong>${data.resultados.length}</strong> registro(s):<br><br>`;
                        data.resultados.forEach(r => {
                            html += `• <strong>${r.servidor_publico}</strong><br>Puesto: ${r.puesto}<br>Área: ${r.area}<br>Sueldo Neto: <strong>$${r.sueldo_neto}</strong><br><span style="font-size:11px; background:#e2e8f0; padding:2px 6px; border-radius:4px;">[${r.fraccion.replace('_',' ').toUpperCase()} - ${r.anio} ${r.trimestre.replace('_',' ')}]</span><br><br>`;
                        });
                    } else {
                        html += `No encontré resultados para "${text}".`;
                    }
                    html += `</div>`;
                    chat.innerHTML += html;
                    chat.scrollTop = chat.scrollHeight;
                } catch(e) {
                    chat.innerHTML += `<div class="message bot">Error al consultar el servidor.</div>`;
                }
            }

            async function subirArchivo() {
                const fraccion = document.getElementById('fraccionSelect').value;
                const anio = document.getElementById('anioSelect').value;
                const trimestre = document.getElementById('trimestreSelect').value;
                const fileInput = document.getElementById('fileInput');
                const alertBox = document.getElementById('adminAlert');

                if (fileInput.files.length === 0) {
                    alertBox.className = 'alert error';
                    alertBox.textContent = 'Selecciona un archivo Excel (.xlsx).';
                    alertBox.style.display = 'block';
                    return;
                }

                const formData = new FormData();
                formData.append('file', fileInput.files[0]);
                formData.append('fraccion', fraccion);
                formData.append('anio', anio);
                formData.append('trimestre', trimestre);

                alertBox.className = 'alert';
                alertBox.textContent = 'Subiendo archivo...';
                alertBox.style.display = 'block';

                try {
                    const res = await fetch('/upload', { method: 'POST', body: formData });
                    const result = await res.json();
                    if (result.estatus === 'Exito') {
                        alertBox.className = 'alert success';
                        alertBox.textContent = result.mensaje;
                        fileInput.value = '';
                    } else {
                        alertBox.className = 'alert error';
                        alertBox.textContent = 'Error: ' + result.detalle;
                    }
                } catch(e) {
                    alertBox.className = 'alert error';
                    alertBox.textContent = 'Error al comunicarse con el servidor.';
                }
            }

            document.getElementById('chatInput').addEventListener('keypress', e => { if(e.key === 'Enter') enviar(); });
        </script>
    </body>
    </html>
    """)

@app.post("/upload")
def subir(file: UploadFile = File(...), fraccion: str = Form(...), anio: str = Form(...), trimestre: str = Form(...)):
    try:
        dir_destino = os.path.join("data", fraccion, anio)
        os.makedirs(dir_destino, exist_ok=True)
        ruta = os.path.join(dir_destino, f"{trimestre}.xlsx")
        with open(ruta, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {"estatus": "Exito", "mensaje": f"Guardado correctamente en histórico: [{fraccion.upper()} | {anio} | {trimestre.upper()}]"}
    except Exception as e:
        return {"estatus": "Error", "detalle": str(e)}

@app.get("/buscar")
def buscar(q: str = Query(...)):
    try:
        df = cargar_base_de_datos_historica()
        if df.empty:
            return {"estatus": "Error", "resultados": []}
        
        texto_global = df.fillna("").astype(str).agg(lambda x: ' '.join(x), axis=1).map(normalizar)
        termino = normalizar(q)
        
        if "mas" in termino or "mayor" in termino:
            cols_num = [c for c in df.columns if pd.to_numeric(df[c], errors='coerce').notnull().sum() > 5]
            if cols_num:
                df['val_num'] = pd.to_numeric(df[cols_num[-1]], errors='coerce').fillna(0)
                df = df.sort_values(by='val_num', ascending=False)
        else:
            palabras = termino.split()
            mask = True
            for p in palabras:
                mask = mask & texto_global.str.contains(p, na=False)
            df = df[mask]

        resultados = []
        for _, row in df.head(5).iterrows():
            row_str = [str(val) for val in row.values]
            resultados.append({
                "servidor_publico": row_str[8] if len(row_str) > 8 else "SERVIDOR PÚBLICO",
                "puesto": row_str[5] if len(row_str) > 5 else "N/D",
                "area": row_str[7] if len(row_str) > 7 else "N/D",
                "sueldo_neto": formatear_moneda(row_str[14]) if len(row_str) > 14 else "0.00",
                "fraccion": str(row.get('META_FRACCION', '')),
                "anio": str(row.get('META_ANIO', '')),
                "trimestre": str(row.get('META_TRIMESTRE', ''))
            })
            
        return {"estatus": "Exito", "resultados": resultados}
    except Exception as e:
        return {"estatus": "Error", "detalle": str(e)}
