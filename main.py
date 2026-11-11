from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import pandas as pd
import unicodedata
import re

app = FastAPI(title="CDHEQROO - Portal de Transparencia Remuneraciones e IA")

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

@app.get("/", response_class=HTMLResponse)
def interfaz_usuario():
    html_content = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>CDHEQROO - Asistente y Consulta de Remuneraciones</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f6f9; margin: 0; padding: 20px; color: #333; }
            .container { max-width: 950px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); }
            h1 { color: #003366; font-size: 24px; margin-bottom: 8px; }
            p.subtitle { color: #666; font-size: 14px; margin-bottom: 20px; }
            
            .tabs { display: flex; gap: 10px; margin-bottom: 25px; border-bottom: 2px solid #e1e8ed; padding-bottom: 10px; }
            .tab-btn { background: none; border: none; padding: 10px 20px; font-size: 16px; font-weight: bold; color: #666; cursor: pointer; border-radius: 6px; transition: 0.3s; }
            .tab-btn.active { background-color: #003366; color: white; }

            .tab-content { display: none; }
            .tab-content.active { display: block; }

            .search-box { display: flex; gap: 10px; margin-bottom: 20px; }
            input[type="text"] { flex: 1; padding: 12px 16px; border: 2px solid #ddd; border-radius: 8px; font-size: 16px; outline: none; transition: 0.3s; }
            input[type="text"]:focus { border-color: #003366; }
            button.action-btn { background-color: #003366; color: white; border: none; padding: 12px 24px; border-radius: 8px; font-size: 16px; cursor: pointer; font-weight: bold; transition: 0.3s; }
            button.action-btn:hover { background-color: #002244; }

            .summary-badge { background-color: #e8f4fd; border-left: 5px solid #003366; padding: 12px 18px; border-radius: 6px; margin-bottom: 20px; font-size: 15px; color: #003366; font-weight: 600; display: none; }
            .cards-container { display: flex; flex-direction: column; gap: 15px; }
            .card { border: 1px solid #e1e8ed; border-left: 5px solid #003366; padding: 18px; border-radius: 8px; background: #fafafa; }
            .card h3 { margin: 0 0 6px 0; color: #003366; font-size: 18px; }
            .card p { margin: 4px 0; font-size: 14px; color: #555; }
            .salary-box { margin-top: 10px; padding-top: 10px; border-top: 1px dashed #ddd; display: flex; gap: 20px; }
            .salary-item { font-size: 14px; }
            .salary-item strong { color: #2e7d32; }

            .chat-container { border: 1px solid #ddd; border-radius: 8px; background: #fafafa; display: flex; flex-direction: column; height: 450px; }
            .chat-messages { flex: 1; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; }
            .message { max-width: 80%; padding: 12px 16px; border-radius: 10px; font-size: 14px; line-height: 1.4; }
            .message.bot { background: #e8f4fd; color: #003366; align-self: flex-start; border-left: 4px solid #003366; }
            .message.user { background: #003366; color: white; align-self: flex-end; }
            .chat-input-box { display: flex; padding: 15px; border-top: 1px solid #ddd; background: white; border-radius: 0 0 8px 8px; gap: 10px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Comisión de los Derechos Humanos del Estado de Quintana Roo</h1>
            <p class="subtitle">Portal de Transparencia y Asistente Inteligente (Art. 75, Fracción VII)</p>
            
            <div class="tabs">
                <button class="tab-btn active" onclick="cambiarTab('buscador', event)">🔍 Buscador Tradicional</button>
                <button class="tab-btn" onclick="cambiarTab('chat', event)">🤖 Asistente Conversacional (IA)</button>
            </div>

            <div id="buscador" class="tab-content active">
                <div class="search-box">
                    <input type="text" id="searchInput" placeholder="Escribe un nombre, área o puesto (ej. Gabriel, Informatica, Director)...">
                    <button class="action-btn" onclick="realizarBusqueda()">Buscar</button>
                </div>
                <div class="summary-badge" id="summaryBadge"></div>
                <div class="cards-container" id="resultsContainer"></div>
            </div>

            <div id="chat" class="tab-content">
                <div class="chat-container">
                    <div class="chat-messages" id="chatMessages">
                        <div class="message bot">¡Hola! Soy tu asistente virtual de transparencia. Pregúntame sobre sueldos, rangos o comparativas (ej. <i>"¿Quién gana más?"</i>, <i>"¿Quién gana menos?"</i>, <i>"Sueldos entre 20000 y 40000"</i> o <i>"Busca a Gabriel"</i>).</div>
                    </div>
                    <div class="chat-input-box">
                        <input type="text" id="chatInput" placeholder="Escribe tu pregunta aquí...">
                        <button class="action-btn" onclick="enviarMensajeChat()">Enviar</button>
                    </div>
                </div>
            </div>
        </div>

        <script>
            function cambiarTab(tabName, event) {
                document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
                document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
                document.getElementById(tabName).classList.add('active');
                event.currentTarget.classList.add('active');
            }

            async function realizarBusqueda() {
                const query = document.getElementById('searchInput').value.trim();
                const container = document.getElementById('resultsContainer');
                const summaryBadge = document.getElementById('summaryBadge');

                if (!query) return;
                summaryBadge.style.display = 'none';
                container.innerHTML = '<p style="color:#666;">Buscando registros...</p>';

                try {
                    const response = await fetch(`/buscar?q=${encodeURIComponent(query)}`);
                    const data = await response.json();

                    container.innerHTML = '';
                    if (data.estatus === 'Exito' && data.total_encontrados > 0) {
                        summaryBadge.textContent = `Resumen: Se encontraron ${data.total_encontrados} registro(s) para "${data.busqueda}".`;
                        summaryBadge.style.display = 'block';

                        data.resultados.forEach(item => {
                            const card = document.createElement('div');
                            card.className = 'card';
                            card.innerHTML = `
                                <h3>${item.servidor_publico || 'PUESTO VACANTE / SIN NOMBRE'}</h3>
                                <p><strong>Puesto:</strong> ${item.puesto}</p>
                                <p><strong>Área:</strong> ${item.area}</p>
                                <div class="salary-box">
                                    <div class="salary-item">Bruto Mensual: <strong>$${item.remuneracion_bruta_mensual}</strong></div>
                                    <div class="salary-item">Neto Mensual: <strong>$${item.remuneracion_neta_mensual}</strong></div>
                                </div>
                            `;
                            container.appendChild(card);
                        });
                    } else {
                        summaryBadge.textContent = `Resumen: No se encontraron registros para "${query}".`;
                        summaryBadge.style.display = 'block';
                    }
                } catch (error) {
                    container.innerHTML = '<p style="color:red;">Error al consultar el servidor.</p>';
                }
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

                    if (data.estatus === 'Exito' && data.total_encontrados > 0) {
                        let respuestaTexto = `Análisis de tu consulta ("${data.busqueda}") - ${data.total_encontrados} resultado(s):<br><br>`;
                        data.resultados.forEach(item => {
                            respuestaTexto += `• <strong>${item.servidor_publico || 'VACANTE'}</strong> (${item.puesto} - ${item.area})<br>  Sueldo Neto: <strong>$${item.remuneracion_neta_mensual}</strong><br><br>`;
                        });
                        botDiv.innerHTML = respuestaTexto;
                    } else {
                        botDiv.textContent = `No encontré registros directos para "${text}". Prueba preguntando por rangos de sueldo (ej. "entre 20000 y 40000"), puestos o áreas específicas.`;
                    }

                    chatMessages.appendChild(botDiv);
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                } catch (error) {
                    const errDiv = document.createElement('div');
                    errDiv.className = 'message bot';
                    errDiv.textContent = 'Ocurrió un error al procesar tu consulta.';
                    chatMessages.appendChild(errDiv);
                }
            }

            document.getElementById('searchInput').addEventListener('keypress', function (e) {
                if (e.key === 'Enter') realizarBusqueda();
            });
            document.getElementById('chatInput').addEventListener('keypress', function (e) {
                if (e.key === 'Enter') enviarMensajeChat();
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/areas")
def listar_areas():
    ruta = "data/lgt_65_vii.1-trimestre-1.xlsx"
    try:
        df = pd.read_excel(ruta, sheet_name='Reporte de Formatos')
        if 'Unnamed: 7' in df.columns:
            areas = df['Unnamed: 7'].dropna().unique().tolist()
            areas_limpias = [str(a) for a in areas if "AREA" not in str(a).upper() and len(str(a)) > 3]
            return {"estatus": "Exito", "total_areas": len(areas_limpias), "areas": areas_limpias}
        return {"estatus": "Error", "detalle": "Columna de área no encontrada"}
    except Exception as e:
        return {"estatus": "Error", "detalle": str(e)}

@app.get("/buscar")
def buscar_remuneracion(q: str = Query(..., description="Termino de busqueda")):
    ruta = "data/lgt_65_vii.1-trimestre-1.xlsx"
    try:
        termino_crudo = q.replace('"', '').replace("'", "").strip()
        termino_norm = normalizar(termino_crudo)
        
        df = pd.read_excel(ruta, sheet_name='Reporte de Formatos')
        
        # Preparamos la columna numérica de sueldo bruto
        try:
            df['sueldo_num'] = pd.to_numeric(df['Unnamed: 12'], errors='coerce')
        except Exception:
            df['sueldo_num'] = 0.0

        df_norm = df.fillna("").astype(str).map(normalizar)
        
        # 1. Detección de rangos numéricos (ej. "entre 20000 y 40000", "de 20 mil a 40 mil")
        numeros_en_texto = re.findall(r'\d+', termino_crudo.replace(',', ''))
        es_rango = ("entre" in termino_norm or " a " in termino_norm or " y " in termino_norm) and len(numeros_en_texto) >= 2
        
        if es_rango:
            min_val = float(numeros_en_texto[0])
            max_val = float(numeros_en_texto[1])
            # Si escribieron "20" refiriéndose a miles, ajustamos
            if min_val < 1000 and max_val < 1000:
                min_val *= 1000
                max_val *= 1000
            resultado_df = df[(df['sueldo_num'] >= min_val) & (df['sueldo_num'] <= max_val)].sort_values(by='sueldo_num', ascending=False).fillna("")
        
        # 2. Detección de sueldos máximos ("quién gana más")
        elif any(p in termino_norm for p in ["mas", "mayor", "altos", "maximo"]) and any(p in termino_norm for p in ["sueldo", "gana", "salario", "dinero", "paga"]):
            resultado_df = df.sort_values(by='sueldo_num', ascending=False).head(5).fillna("")
        
        # 3. Detección de sueldos mínimos ("quién gana menos")
        elif any(p in termino_norm for p in ["menos", "menor", "bajos", "minimo"]) and any(p in termino_norm for p in ["sueldo", "gana", "salario", "dinero", "paga"]):
            df_filtrado = df[df['sueldo_num'] > 100]
            resultado_df = df_filtrado.sort_values(by='sueldo_num', ascending=True).head(5).fillna("")
        
        # 4. Búsqueda general por coincidencia de texto
        else:
            mask = False
            for col in df_norm.columns:
                mask = mask | df_norm[col].str.contains(termino_norm, na=False)
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
            "busqueda": termino_crudo,
            "total_encontrados": len(registros_limpios),
            "resultados": registros_limpios
        }
    except Exception as e:
        return {"estatus": "Error", "detalle": str(e)}
