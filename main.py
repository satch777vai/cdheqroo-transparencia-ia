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

# Asegurar que exista la carpeta base de datos
os.makedirs("data", exist_ok=True)

def normalizar(texto):
    """Elimina acentos/tildes y convierte a minúsculas para una búsqueda robusta"""
    if not isinstance(texto, str):
        texto = str(texto)
    nfd = unicodedata.normalize('NFD', texto)
    sin_tildes = "".join([c for c in nfd if unicodedata.category(c) != 'Mn'])
    return sin_tildes.lower()

def formatear_moneda(valor):
    """Formatea valores numéricos a estilo monetario con comas y 2 decimales"""
    try:
        num = float(valor)
        return f"{num:,.2f}"
    except (ValueError, TypeError):
        return str(valor)

def cargar_base_de_datos_historica():
    """Escanea recursivamente la carpeta data/ y extrae metadatos de Fracción, Año y Trimestre"""
    archivos = glob.glob("data/**/*.xlsx", recursive=True)
    dfs = []
    
    for archivo in archivos:
        # Extraer metadatos de la ruta (ej: data/frac_7/2026/trimestre_1.xlsx)
        partes = archivo.replace("\\", "/").split("/")
        fraccion = partes[1].upper() if len(partes) > 1 else "FRACCION_GENERAL"
        anio = partes[2] if len(partes) > 2 else "S_ANIO"
        trimestre = partes[3].replace(".xlsx", "").upper() if len(partes) > 3 else "S_TRIMESTRE"
        
        try:
            df = pd.read_excel(archivo, sheet_name='Reporte de Formatos')
        except Exception:
            try:
                df = pd.read_excel(archivo, sheet_name=0)
            except Exception:
                continue
        
        # Inyectar metadatos históricos al DataFrame
        df['META_FRACCION'] = fraccion
        df['META_ANIO'] = anio
        df['META_TRIMESTRE'] = trimestre
        dfs.append(df)
        
    if dfs:
        return pd.concat(dfs, ignore_index=True)
    return pd.DataFrame()

@app.get("/", response_class=HTMLResponse)
def interfaz_usuario():
    html_content = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>CDHEQROO - Asistente Histórico de Transparencia</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f6f9; margin: 0; padding: 20px; color: #333; }
            .container { max-width: 950px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); }
            h1 { color: #003366; font-size: 24px; margin-bottom: 8px; }
            p.subtitle { color: #666; font-size: 14px; margin-bottom: 20px; border-bottom: 2px solid #e1e8ed; padding-bottom: 15px; }

            /* Pestañas de navegación */
            .tabs { display: flex; gap: 10px; margin-bottom: 20px; }
            .tab-btn { background: #e1e8ed; border: none; padding: 10px 20px; font-size: 15px; font-weight: bold; color: #444; cursor: pointer; border-radius: 6px; transition: 0.3s; }
            .tab-btn.active { background-color: #003366; color: white; }

            .tab-content { display: none; }
            .tab-content.active { display: block; }

            /* Chat IA */
            .chat-container { border: 1px solid #ddd; border-radius: 8px; background: #fafafa; display: flex; flex-direction: column; height: 500px; }
            .chat-messages { flex: 1; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 15px; }
            .message { max-width: 85%; padding: 14px 18px; border-radius: 10px; font-size: 14px; line-height: 1.5; }
            .message.bot { background: #e8f4fd; color: #003366; align-self: flex-start; border-left: 4px solid #003366; }
            .message.user { background: #003366; color: white; align-self: flex-end; }
            .chat-input-box { display: flex; padding: 15px; border-top: 1px solid #ddd; background: white; border-radius: 0 0 8px 8px; gap: 10px; }

            /* Formulario Admin */
            .admin-form { display: flex; flex-direction: column; gap: 15px; background: #fafafa; padding: 20px; border-radius: 8px; border: 1px solid #ddd; }
            .form-group { display: flex; flex-direction: column; gap: 5px; }
            label { font-weight: bold; font-size: 14px; color: #333; }
            select, input[type="file"] { padding: 10px; border: 2px solid #ddd; border-radius: 6px; font-size: 15px; background: white; outline: none; }
            select:focus, input[type="file"]:focus { border-color: #003366; }
            
            input[type="text"] { flex: 1; padding: 12px 16px; border: 2px solid #ddd; border-radius: 8px; font-size: 16px; outline: none; transition: 0.3s; }
            input[type="text"]:focus { border-color: #003366; }
            button.action-btn { background-color: #003366; color: white; border: none; padding: 12px 24px; border-radius: 8px; font-size: 16px; cursor: pointer; font-weight: bold; transition: 0.3s; }
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

            <!-- PESTAÑA 1: CHAT INTELIGENTE -->
            <div id="chatTab" class="tab-content active">
                <div class="chat-container">
                    <div class="chat-messages" id="chatMessages">
                        <div class="message bot">¡Hola! Soy tu asistente histórico de transparencia. Pregúntame sobre cualquier servidor público, sueldos máximos/mínimos, rangos o estadísticas de los trimestres y años cargados (ej. <i>"¿Quién gana más?"</i>, <i>"Sueldos entre 20000 y 40000"</i> o <i>"Erick Armando"</i>).</div>
                    </div>
                    <div class="chat-input-box">
                        <input type="text" id="chatInput" placeholder="Escribe tu consulta aquí...">
                        <button class="action-btn" onclick="enviarMensajeChat()">Enviar</button>
                    </div>
                </div>
            </div>

            <!-- PESTAÑA 2: PANEL DE CARGA ADMIN -->
            <div id="adminTab" class="tab-content">
                <div class="admin-form">
                    <h3>Subir Nuevo Formato al Histórico</h3>
                    <p style="font-size:13px; color:#666; margin-top:-10px;">Selecciona la fracción, el año y el trimestre correspondientes para organizar el archivo automáticamente en el repositorio.</p>
                    
                    <div class="form-group">
                        <label for="fraccionSelect">Fracción del Artículo 75:</label>
                        <select id="fraccionSelect">
                            <option value="fraccion_vii">Fracción VII - Remuneraciones brutas y netas</option>
                            <option value="fraccion_viii">Fracción VIII - Gastos de representación y viáticos</option>
                            <option value="fraccion_xiv">Fracción XIV - Contrataciones de servicios y obras</option>
                            <option value="fraccion_xxviii">Fracción XXVIII - Informes de resultados de auditorías</option>
                        </select>
                    </div>

                    <div class="form-group">
                        <label for="anioSelect">Año:</label>
                        <select id="anioSelect">
                            <option value="2026">2026</option>
                            <option value="2025">2025</option>
                            <option value="2024">2024</option>
                            <option value="2023">2023</option>
                        </select>
                    </div>

                    <div class="form-group">
                        <label for="trimestreSelect">Trimestre:</label>
                        <select id="trimestreSelect">
                            <option value="trimestre_1">Trimestre 1 (Enero - Marzo)</option>
                            <option value="trimestre_2">Trimestre 2 (Abril - Junio)</option>
                            <option value="trimestre_3">Trimestre 3 (Julio - Septiembre)</option>
                            <option value="trimestre_4">Trimestre 4 (Octubre - Diciembre)</option>
                        </select>
                    </div>

                    <div class="form-group">
                        <label for="fileInput">Archivo Excel (.xlsx):</label>
                        <input type="file" id="fileInput" accept=".xlsx">
                    </div>

                    <button class="action-btn" onclick="subirArchivoExcel()">Subir y Registrar en el Histórico</button>
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

            async function enviarMensajeChat() {
                const input = document.getElementById('chatInput');
                const chatMessages = document.getElementById('chatMessages');
                const text = input.value.trim();
                if (!text) return;

                const userDiv = document.createElement('div');
                userDiv.className = 'message user';
                userDiv.textContent = text;
                chatMessages.appendChild(userDiv);
                input.value = '';
                chatMessages.scrollTop = chatMessages.scrollHeight;

                try {
                    const response = await fetch(`/buscar?q=${encodeURIComponent(text)}`);
                    const data = await response.json();

                    const botDiv = document.createElement('div');
                    botDiv.className = 'message bot';

                    if (data.estatus === 'Exito') {
                        if (data.tipo_respuesta === 'estadistica') {
                            botDiv.innerHTML = `📊 <strong>Reporte Estadístico Histórico:</strong><br><br>${data.mensaje}`;
                        } else if (data.total_encontrados > 0) {
                            let respuestaTexto = `Encontré <strong>${data.total_encontrados}</strong> registro(s) en el histórico:<br><br>`;
                            data.resultados.forEach(item => {
                                respuestaTexto += `• <strong>${item.servidor_publico || 'VACANTE'}</strong><br>`;
                                respuestaTexto += `&nbsp;&nbsp;Puesto: ${item.puesto}<br>`;
                                respuestaTexto += `&nbsp;&nbsp;Área: ${item.area}<br>`;
                                respuestaTexto += `&nbsp;&nbsp;Sueldo Neto: <strong>$${item.remuneracion_neta_mensual}</strong> <span style="font-size:11px; background:#e2e8f0; padding:2px 6px; border-radius:4px;">[${item.fraccion.replace('_',' ').toUpperCase()} - ${item.anio} ${item.trimestre.replace('_',' ')}]</span><br><br>`;
                            });
                            botDiv.innerHTML = respuestaTexto;
                        } else {
                            botDiv.textContent = `No encontré registros históricos para "${text}". Prueba con otro término o rango salarial.`;
                        }
                    } else {
                        botDiv.textContent = `Ocurrió un error al procesar tu consulta.`;
                    }

                    chatMessages.appendChild(botDiv);
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                } catch (error) {
                    const errDiv = document.createElement('div');
                    errDiv.className = 'message bot';
                    errDiv.textContent = 'Error de conexión con el servidor.';
                    chatMessages.appendChild(errDiv);
                }
            }

            async function subirArchivoExcel() {
                const fraccion = document.getElementById('fraccionSelect').value;
                const anio = document.getElementById('anioSelect').value;
                const trimestre = document.getElementById('trimestreSelect').value;
                const fileInput = document.getElementById('fileInput');
                const alertBox = document.getElementById('adminAlert');

                if (fileInput.files.length === 0) {
                    alertBox.className = 'alert error';
                    alertBox.textContent = 'Por favor selecciona un archivo Excel (.xlsx).';
                    alertBox.style.display = 'block';
                    return;
                }

                const formData = new FormData();
                formData.append('file', fileInput.files[0]);
                formData.append('fraccion', fraccion);
                formData.append('anio', anio);
                formData.append('trimestre', trimestre);

                alertBox.className = 'alert';
                alertBox.textContent = 'Subiendo y procesando archivo...';
                alertBox.style.display = 'block';

                try {
                    const response = await fetch('/upload', { method: 'POST', body: formData });
                    const result = await response.json();

                    if (result.estatus === 'Exito') {
                        alertBox.className = 'alert success';
                        alertBox.textContent = result.mensaje;
                        fileInput.value = '';
                    } else {
                        alertBox.className = 'alert error';
                        alertBox.textContent = 'Error: ' + result.detalle;
                    }
                } catch (e) {
                    alertBox.className = 'alert error';
                    alertBox.textContent = 'Error al comunicarse con el servidor.';
                }
            }

            document.getElementById('chatInput').addEventListener('keypress', function (e) {
                if (e.key === 'Enter') enviarMensajeChat();
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.post("/upload")
def subir_archivo(file: UploadFile = File(...), fraccion: str = Form(...), anio: str = Form(...), trimestre: str = Form(...)):
    """Endpoint para que el área encargada suba formatos organizados por Fracción, Año y Trimestre"""
    try:
        # Crear estructura de carpetas: data/fraccion_vii/2026/
        dir_destino = os.path.join("data", fraccion, anio)
        os.makedirs(dir_destino, exist_ok=True)
        
        # Ruta final del archivo (ej: data/fraccion_vii/2026/trimestre_1.xlsx)
        ruta_archivo = os.path.join(dir_destino, f"{trimestre}.xlsx")
        
        with open(ruta_archivo, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        return {
            "estatus": "Exito",
            "mensaje": f"Archivo guardado exitosamente en el histórico: [{fraccion.upper()} | {anio} | {trimestre.upper()}]"
        }
    except Exception as e:
        return {"estatus": "Error", "detalle": str(e)}

@app.get("/buscar")
def buscar_remuneracion(q: str = Query(..., description="Termino de busqueda")):
    try:
        termino_crudo = q.replace('"', '').replace("'", "").strip()
        termino_norm = normalizar(termino_crudo)
        
        df = cargar_base_de_datos_historica()
        if df.empty:
            return {"estatus": "Error", "detalle": "No hay archivos cargados en el repositorio histórico."}
        
        # Limpieza y preparación de columnas numéricas
        try:
            df['sueldo_bruto_num'] = pd.to_numeric(df['Unnamed: 12'], errors='coerce').fillna(0)
        except Exception:
            df['sueldo_bruto_num'] = 0.0

        try:
            df['sueldo_neto_num'] = pd.to_numeric(df['Unnamed: 14'], errors='coerce').fillna(0)
        except Exception:
            df['sueldo_neto_num'] = 0.0

        # Filtro de calidad (descartar basura técnica)
        df['nombre_temp'] = df.apply(lambda r: f"{r.get('Unnamed: 8', '')} {r.get('Unnamed: 9', '')} {r.get('Unnamed: 10', '')}".strip(), axis=1)
        df = df[df['sueldo_neto_num'] > 1000].copy()
        df = df[~df['nombre_temp'].str.contains(r'^\d+(\s+\d+)*$', na=False)]

        df['texto_completo'] = df.fillna("").astype(str).agg(lambda x: ' '.join(x), axis=1).map(normalizar)
        
        numeros_en_texto = re.findall(r'\d+', termino_crudo.replace(',', ''))
        
        # 1. Intención Estadística Histórica
        if any(p in termino_norm for p in ["promedio", "media", "total", "suma", "cuantos registros", "cuantos empleados"]):
            total_pers = len(df)
            prom_neto = df['sueldo_neto_num'].mean()
            prom_bruto = df['sueldo_bruto_num'].mean()
            suma_neto = df['sueldo_neto_num'].sum()
            
            mensaje_est = (
                f"• Total de registros históricos analizados: <strong>{total_pers}</strong><br>"
                f"• Sueldo Neto Promedio Histórico: <strong>${formatear_moneda(prom_neto)}</strong><br>"
                f"• Sueldo Bruto Promedio Histórico: <strong>${formatear_moneda(prom_bruto)}</strong><br>"
                f"• Suma Total Nómina Neta Histórica: <strong>${formatear_moneda(suma_neto)}</strong>"
            )
            return {
                "estatus": "Exito",
                "tipo_respuesta": "estadistica",
                "mensaje": mensaje_est
            }

        # 2. Rangos numéricos
        elif ("entre" in termino_norm or " a " in termino_norm or " y " in termino_norm) and len(numeros_en_texto) >= 2:
            min_val = float(numeros_en_texto[0])
            max_val = float(numeros_en_texto[1])
            if min_val < 1000 and max_val < 1000:
                min_val *= 1000
                max_val *= 1000
            resultado_df = df[(df['sueldo_neto_num'] >= min_val) & (df['sueldo_neto_num'] <= max_val)].sort_values(by='sueldo_neto_num', ascending=False).fillna("")
        
        # 3. Sueldos máximos
        elif any(p in termino_norm for p in ["mas", "mayor", "altos", "maximo"]) and any(p in termino_norm for p in ["sueldo", "gana", "salario", "dinero", "paga"]):
            resultado_df = df.sort_values(by='sueldo_neto_num', ascending=False).head(5).fillna("")
        
        # 4. Sueldos mínimos
        elif any(p in termino_norm for p in ["menos", "menor", "bajos", "minimo"]) and any(p in termino_norm for p in ["sueldo", "gana", "salario", "dinero", "paga"]):
            resultado_df = df.sort_values(by='sueldo_neto_num', ascending=True).head(5).fillna("")
        
        # 5. Búsqueda multi-palabra inteligente en el histórico
        else:
            palabras = termino_norm.split()
            mask = True
            for palabra in palabras:
                mask = mask & df['texto_completo'].str.contains(palabra, na=False)
            resultado_df = df[mask].fillna("")
        
        registros_limpios = []
        for _, row in resultado_df.iterrows():
            area = str(row.get('Unnamed: 7', 'N/D'))
            puesto = str(row.get('Unnamed: 5', 'N/D'))
            nombre = f"{row.get('Unnamed: 8', '')} {row.get('Unnamed: 9', '')} {row.get('Unnamed: 10', '')}".strip()
            
            sueldo_bruto = formatear_moneda(row.get('Unnamed: 12', '0'))
            sueldo_neto = formatear_moneda(row.get('Unnamed: 14', '0'))
            
            registros_limpios.append({
                "area": area,
                "puesto": puesto,
                "servidor_publico": nombre,
                "remuneracion_bruta_mensual": sueldo_bruto,
                "remuneracion_neta_mensual": sueldo_neto,
                "fraccion": str(row.get('META_FRACCION', '')),
                "anio": str(row.get('META_ANIO', '')),
                "trimestre": str(row.get('META_TRIMESTRE', ''))
            })
        
        return {
            "estatus": "Exito",
            "tipo_respuesta": "registros",
            "busqueda": termino_crudo,
            "total_encontrados": len(registros_limpios),
            "resultados": registros_limpios
        }
    except Exception as e:
        return {"estatus": "Error", "detalle": str(e)}
