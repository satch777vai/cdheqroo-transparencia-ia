from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import pandas as pd
import unicodedata

app = FastAPI(title="CDHEQROO - Portal de Transparencia Remuneraciones")

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

@app.get("/", response_class=HTMLResponse)
def interfaz_usuario():
    html_content = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>CDHEQROO - Consulta de Remuneraciones</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f6f9; margin: 0; padding: 20px; color: #333; }
            .container { max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); }
            h1 { color: #003366; font-size: 24px; margin-bottom: 8px; }
            p.subtitle { color: #666; font-size: 14px; margin-bottom: 25px; }
            .search-box { display: flex; gap: 10px; margin-bottom: 25px; }
            input[type="text"] { flex: 1; padding: 12px 16px; border: 2px solid #ddd; border-radius: 8px; font-size: 16px; outline: none; transition: 0.3s; }
            input[type="text"]:focus { border-color: #003366; }
            button { background-color: #003366; color: white; border: none; padding: 12px 24px; border-radius: 8px; font-size: 16px; cursor: pointer; font-weight: bold; transition: 0.3s; }
            button:hover { background-color: #002244; }
            .cards-container { display: flex; flex-direction: column; gap: 15px; }
            .card { border: 1px solid #e1e8ed; border-left: 5px solid #003366; padding: 18px; border-radius: 8px; background: #fafafa; }
            .card h3 { margin: 0 0 6px 0; color: #003366; font-size: 18px; }
            .card p { margin: 4px 0; font-size: 14px; color: #555; }
            .salary-box { margin-top: 10px; padding-top: 10px; border-top: 1px dashed #ddd; display: flex; gap: 20px; }
            .salary-item { font-size: 14px; }
            .salary-item strong { color: #2e7d32; }
            .status { font-size: 14px; color: #777; margin-bottom: 15px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Comisión de los Derechos Humanos del Estado de Quintana Roo</h1>
            <p class="subtitle">Consulta Pública de Remuneraciones (Art. 75, Fracción VII)</p>
            
            <div class="search-box">
                <input type="text" id="searchInput" placeholder="Escribe un nombre, área o puesto (ej. Gabriel, Informatica, Director)...">
                <button onclick="realizarBusqueda()">Buscar</button>
            </div>

            <div class="status" id="statusMessage">Alineado con estándares de transparencia y accesibilidad.</div>
            <div class="cards-container" id="resultsContainer"></div>
        </div>

        <script>
            async function realizarBusqueda() {
                const query = document.getElementById('searchInput').value.trim();
                const container = document.getElementById('resultsContainer');
                const status = document.getElementById('statusMessage');

                if (!query) {
                    status.textContent = 'Por favor ingresa un término de búsqueda.';
                    return;
                }

                status.textContent = 'Buscando registros en la nube...';
                container.innerHTML = '';

                try {
                    const response = await fetch(`/buscar?q=${encodeURIComponent(query)}`);
                    const data = await response.json();

                    if (data.estatus === 'Exito' && data.total_encontrados > 0) {
                        status.textContent = `Se encontraron ${data.total_encontrados} registro(s) para "${data.busqueda}":`;
                        data.resultados.forEach(item => {
                            const card = document.createElement('div');
                            card.className = 'card';
                            card.innerHTML = `
                                <h3>${item.servidor_publico || 'PUESTO VACANTE / SIN NOMBRE'}</h3>
                                <p><strong>Puesto:</strong> ${item.puesto}</p>
                                <p><strong>Área de Adscripción:</strong> ${item.area}</p>
                                <div class="salary-box">
                                    <div class="salary-item">Sueldo Bruto Mensual: <strong>$${item.remuneracion_bruta_mensual}</strong></div>
                                    <div class="salary-item">Sueldo Neto Mensual: <strong>$${item.remuneracion_neta_mensual}</strong></div>
                                </div>
                            `;
                            container.appendChild(card);
                        });
                    } else {
                        status.textContent = `No se encontraron coincidencias para "${query}".`;
                    }
                } catch (error) {
                    status.textContent = 'Ocurrió un error al consultar el servidor.';
                }
            }

            document.getElementById('searchInput').addEventListener('keypress', function (e) {
                if (e.key === 'Enter') realizarBusqueda();
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/probar-excel")
def probar_excel():
    ruta = "data/lgt_65_vii.1-trimestre-1.xlsx"
    try:
        xls = pd.ExcelFile(ruta)
        df = pd.read_excel(ruta, sheet_name='Reporte de Formatos')
        return {
            "estatus": "Exito",
            "archivo": "lgt_65_vii.1-trimestre-1.xlsx",
            "hojas_encontradas": xls.sheet_names,
            "total_filas": len(df)
        }
    except Exception as e:
        return {"estatus": "Error", "detalle": str(e)}

@app.get("/buscar")
def buscar_remuneracion(q: str = Query(..., description="Termino de busqueda: nombre, puesto o area")):
    ruta = "data/lgt_65_vii.1-trimestre-1.xlsx"
    try:
        termino_crudo = q.replace('"', '').replace("'", "").strip()
        termino_busqueda = normalizar(termino_crudo)
        
        df = pd.read_excel(ruta, sheet_name='Reporte de Formatos')
        
        # Creamos una copia auxiliar normalizada de todo el DataFrame para la búsqueda sin importar tildes ni mayúsculas
        df_norm = df.fillna("").astype(str).applymap(normalizar)
        
        mask = False
        for col in df_norm.columns:
            mask = mask | df_norm[col].str.contains(termino_busqueda, na=False)
            
        resultado_df = df[mask].fillna("")
        
        registros_limpios = []
        for _, row in resultado_df.iterrows():
            area = str(row.get('Unnamed: 7', 'N/D'))
            puesto = str(row.get('Unnamed: 5', 'N/D'))
            nombre = f"{row.get('Unnamed: 8', '')} {row.get('Unnamed: 9', '')} {row.get('Unnamed: 10', '')}".strip()
            sueldo_bruto = str(row.get('Unnamed: 12', 'N/D'))
            sueldo_neto = str(row.get('Unnamed: 14', 'N/D'))
            
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
