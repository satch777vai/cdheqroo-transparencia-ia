from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import pandas as pd
import unicodedata
import glob
import re

app = FastAPI(title="CDHEQROO - Asistente Inteligente de Transparencia")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

def cargar_base_de_datos_unificada():
    """Carga y unifica automáticamente todos los archivos Excel en la carpeta data/"""
    archivos = glob.glob("data/*.xlsx")
    dfs = []
    for archivo in archivos:
        try:
            df = pd.read_excel(archivo, sheet_name='Reporte de Formatos')
            dfs.append(df)
        except Exception:
            try:
                df = pd.read_excel(archivo, sheet_name=0)
                dfs.append(df)
            except Exception:
                pass
    
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
        <title>CDHEQROO - Asistente Inteligente de Transparencia</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f6f9; margin: 0; padding: 20px; color: #333; }
            .container { max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); }
            h1 { color: #003366; font-size: 24px; margin-bottom: 8px; }
            p.subtitle { color: #666; font-size: 14px; margin-bottom: 25px; border-bottom: 2px solid #e1e8ed; padding-bottom: 15px; }

            .chat-container { border: 1px solid #ddd; border-radius: 8px; background: #fafafa; display: flex; flex-direction: column; height: 550px; box-shadow: inset 0 2px 5px rgba(0,0,0,0.02); }
            .chat-messages { flex: 1; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 15px; }
            .message { max-width: 85%; padding: 14px 18px; border-radius: 10px; font-size: 14px; line-height: 1.5; }
            .message.bot { background: #e8f4fd; color: #003366; align-self: flex-start; border-left: 4px solid #003366; box-shadow: 0 2px 5px rgba(0,0,0,0.03); }
            .message.user { background: #003366; color: white; align-self: flex-end; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
            .chat-input-box { display: flex; padding: 15px; border-top: 1px solid #ddd; background: white; border-radius: 0 0 8px 8px; gap: 10px; }
            input[type="text"] { flex: 1; padding: 12px 16px; border: 2px solid #ddd; border-radius: 8px; font-size: 16px; outline: none; transition: 0.3s; }
            input[type="text"]:focus { border-color: #003366; }
            button.action-btn { background-color: #003366; color: white; border: none; padding: 12px 24px; border-radius: 8px; font-size: 16px; cursor: pointer; font-weight: bold; transition: 0.3s; }
            button.action-btn:hover { background-color: #002244; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Comisión de los Derechos Humanos del Estado de Quintana Roo</h1>
            <p class="subtitle">Asistente Inteligente de Transparencia (Art. 75, Fracción VII y Múltiples Formatos)</p>
            
            <div class="chat-container">
                <div class="chat-messages" id="chatMessages">
                    <div class="message bot">¡Hola! Soy tu asistente virtual de transparencia. Pregúntame sobre nombres, puestos, áreas, sueldos máximos/mínimos, rangos o estadísticas (ej. <i>"Erick Armando Poot Alcocer"</i>, <i>"¿Quién gana más?"</i>, <i>"Sueldos entre 20000 y 40000"</i>, <i>"Promedio de sueldos"</i> o <i>"Informática"</i>).</div>
                </div>
                <div class="chat-input-box">
                    <input type="text" id="chatInput" placeholder="Escribe tu consulta aquí...">
                    <button class="action-btn" onclick="enviarMensajeChat()">Enviar</button>
                </div>
            </div>
        </div>

        <script>
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
                            botDiv.innerHTML = `📊 <strong>Reporte Estadístico:</strong><br><br>${data.mensaje}`;
                        } else if (data.total_encontrados > 0) {
                            let respuestaTexto = `Encontré <strong>${data.total_encontrados}</strong> registro(s):<br><br>`;
                            data.resultados.forEach(item => {
                                respuestaTexto += `• <strong>${item.servidor_publico || 'VACANTE'}</strong><br>`;
                                respuestaTexto += `&nbsp;&nbsp;Puesto: ${item.puesto}<br>`;
                                respuestaTexto += `&nbsp;&nbsp;Área: ${item.area}<br>`;
                                respuestaTexto += `&nbsp;&nbsp;Sueldo Neto: <strong>$${item.remuneracion_neta_mensual}</strong><br><br>`;
                            });
                            botDiv.innerHTML = respuestaTexto;
                        } else {
                            botDiv.textContent = `No encontré registros que coincidan con "${text}". Prueba buscando por nombre completo, puesto, área o rangos salariales.`;
                        }
                    } else {
                        botDiv.textContent = `Ocurrió un error al procesar tu consulta con el servidor.`;
                    }

                    chatMessages.appendChild(botDiv);
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                } catch (error) {
                    const errDiv = document.createElement('div');
                    errDiv.className = 'message bot';
                    errDiv.textContent = 'Ocurrió un error de conexión con el servidor.';
                    chatMessages.appendChild(errDiv);
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

@app.get("/buscar")
def buscar_remuneracion(q: str = Query(..., description="Termino de busqueda")):
    try:
        termino_crudo = q.replace('"', '').replace("'", "").strip()
        termino_norm = normalizar(termino_crudo)
        
        df = cargar_base_de_datos_unificada()
        if df.empty:
            return {"estatus": "Error", "detalle": "No se encontraron archivos de datos en el servidor."}
        
        # Limpieza y preparación de columnas numéricas
        try:
            df['sueldo_bruto_num'] = pd.to_numeric(df['Unnamed: 12'], errors='coerce').fillna(0)
        except Exception:
            df['sueldo_bruto_num'] = 0.0

        try:
            df['sueldo_neto_num'] = pd.to_numeric(df['Unnamed: 14'], errors='coerce').fillna(0)
        except Exception:
            df['sueldo_neto_num'] = 0.0

        # FILTRO DE CALIDAD: Eliminamos filas que sean encabezados o datos basura (donde no haya nombres reales o sueldos válidos)
        # Identificamos el nombre concatenando celdas de nombres
        df['nombre_temp'] = df.apply(lambda r: f"{r.get('Unnamed: 8', '')} {r.get('Unnamed: 9', '')} {r.get('Unnamed: 10', '')}".strip(), axis=1)
        
        # Descartamos filas donde el nombre contenga puros números, la palabra "ejercicio", "denominación", etc.
        df = df[df['sueldo_neto_num'] > 1000].copy() # Sueldos reales mínimos en administración pública
        df = df[~df['nombre_temp'].str.contains(r'^\d+(\s+\d+)*$', na=False)] # Elimina filas con puros números como "132 133 134"

        # Texto unificado global por fila
        df['texto_completo'] = df.fillna("").astype(str).agg(lambda x: ' '.join(x), axis=1).map(normalizar)
        
        numeros_en_texto = re.findall(r'\d+', termino_crudo.replace(',', ''))
        
        # 1. Intención Estadística / Promedios / Totales
        if any(p in termino_norm for p in ["promedio", "media", "total", "suma", "cuantos registros", "cuantos empleados"]):
            total_pers = len(df)
            prom_neto = df['sueldo_neto_num'].mean()
            prom_bruto = df['sueldo_bruto_num'].mean()
            suma_neto = df['sueldo_neto_num'].sum()
            
            mensaje_est = (
                f"• Total de registros analizados: <strong>{total_pers}</strong><br>"
                f"• Sueldo Neto Promedio: <strong>${formatear_moneda(prom_neto)}</strong><br>"
                f"• Sueldo Bruto Promedio: <strong>${formatear_moneda(prom_bruto)}</strong><br>"
                f"• Suma Total Nómina Neta: <strong>${formatear_moneda(suma_neto)}</strong>"
            )
            return {
                "estatus": "Exito",
                "tipo_respuesta": "estadistica",
                "mensaje": mensaje_est
            }

        # 2. Detección de rangos numéricos ("entre X y Y")
        elif ("entre" in termino_norm or " a " in termino_norm or " y " in termino_norm) and len(numeros_en_texto) >= 2:
            min_val = float(numeros_en_texto[0])
            max_val = float(numeros_en_texto[1])
            if min_val < 1000 and max_val < 1000:
                min_val *= 1000
                max_val *= 1000
            resultado_df = df[(df['sueldo_neto_num'] >= min_val) & (df['sueldo_neto_num'] <= max_val)].sort_values(by='sueldo_neto_num', ascending=False).fillna("")
        
        # 3. Sueldos máximos ("quién gana más")
        elif any(p in termino_norm for p in ["mas", "mayor", "altos", "maximo"]) and any(p in termino_norm for p in ["sueldo", "gana", "salario", "dinero", "paga"]):
            resultado_df = df.sort_values(by='sueldo_neto_num', ascending=False).head(5).fillna("")
        
        # 4. Sueldos mínimos ("quién gana menos")
        elif any(p in termino_norm for p in ["menos", "menor", "bajos", "minimo"]) and any(p in termino_norm for p in ["sueldo", "gana", "salario", "dinero", "paga"]):
            resultado_df = df.sort_values(by='sueldo_neto_num', ascending=True).head(5).fillna("")
        
        # 5. Búsqueda multi-palabra inteligente (Nombres, puestos, áreas)
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
                "remuneracion_neta_mensual": sueldo_neto
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
