from fastapi import FastAPI, Query, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import pandas as pd
import unicodedata
import glob
import os
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
        <title>CDHEQROO - Asistente de Transparencia</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #f4f6f9; margin: 0; padding: 20px; color: #333; }
            .container { max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); }
            h1 { color: #003366; font-size: 24px; margin-bottom: 5px; }
            p.subtitle { color: #666; font-size: 14px; margin-bottom: 20px; border-bottom: 2px solid #e1e8ed; padding-bottom: 10px; }
            .chat-container { border: 1px solid #ddd; border-radius: 8px; background: #fafafa; display: flex; flex-direction: column; height: 450px; }
            .chat-messages { flex: 1; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; }
            .message { max-width: 85%; padding: 12px 16px; border-radius: 10px; font-size: 14px; line-height: 1.4; }
            .message.bot { background: #e8f4fd; color: #003366; align-self: flex-start; border-left: 4px solid #003366; }
            .message.user { background: #003366; color: white; align-self: flex-end; }
            .chat-input-box { display: flex; padding: 15px; border-top: 1px solid #ddd; background: white; border-radius: 0 0 8px 8px; gap: 10px; }
            input[type="text"] { flex: 1; padding: 12px; border: 2px solid #ddd; border-radius: 8px; font-size: 16px; outline: none; }
            button { background-color: #003366; color: white; border: none; padding: 12px 20px; border-radius: 8px; font-size: 16px; cursor: pointer; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Comisión de los Derechos Humanos del Estado de Quintana Roo</h1>
            <p class="subtitle">Asistente Inteligente de Transparencia</p>
            <div class="chat-container">
                <div class="chat-messages" id="chatMessages">
                    <div class="message bot">¡Hola! Pregúntame sobre sueldos, puestos o áreas (ej. "Erick", "Director", "quién gana más").</div>
                </div>
                <div class="chat-input-box">
                    <input type="text" id="chatInput" placeholder="Escribe tu consulta aquí...">
                    <button onclick="enviar()">Enviar</button>
                </div>
            </div>
        </div>
        <script>
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
                        html += `Encontré ${data.resultados.length} registro(s):<br><br>`;
                        data.resultados.forEach(r => {
                            html += `• <strong>${r.servidor_publico}</strong><br>Puesto: ${r.puesto}<br>Área: ${r.area}<br>Sueldo Neto: <strong>$${r.sueldo_neto}</strong><br><br>`;
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
            document.getElementById('chatInput').addEventListener('keypress', e => { if(e.key === 'Enter') enviar(); });
        </script>
    </body>
    </html>
    """)

@app.get("/buscar")
def buscar(q: str = Query(...)):
    try:
        df = cargar_base_de_datos_historica()
        if df.empty:
            return {"estatus": "Error", "resultados": []}
        
        # Convertir todo el dataframe a texto normalizado para búsqueda flexible
        texto_global = df.fillna("").astype(str).agg(lambda x: ' '.join(x), axis=1).map(normalizar)
        termino = normalizar(q)
        
        # Si preguntan por sueldos máximos
        if "mas" in termino or "mayor" in termino:
            # Buscar columnas numéricas de sueldo de manera flexible
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
            # Intentar extraer datos comunes de manera segura
            row_str = [str(val) for val in row.values]
            resultados.append({
                "servidor_publico": row_str[8] if len(row_str) > 8 else "SERVIDOR PÚBLICO",
                "puesto": row_str[5] if len(row_str) > 5 else "N/D",
                "area": row_str[7] if len(row_str) > 7 else "N/D",
                "sueldo_neto": formatear_moneda(row_str[14]) if len(row_str) > 14 else "0.00"
            })
            
        return {"estatus": "Exito", "resultados": resultados}
    except Exception as e:
        return {"estatus": "Error", "detalle": str(e)}
