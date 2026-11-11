from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd

app = FastAPI(title="CDHEQROO - API Transparencia Accesible")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def estado():
    return {"estatus": "Activo", "mensaje": "El servidor de la CDHEQROO esta operando correctamente."}

@app.get("/probar-excel")
def probar_excel():
    ruta = "data/lgt_65_vii.1-trimestre-1.xlsx"
    try:
        xls = pd.ExcelFile(ruta)
        df = pd.read_excel(ruta, sheet_name='Reporte de Formatos')
        filas = len(df) - 6
        return {
            "estatus": "Exito",
            "archivo": "lgt_65_vii.1-trimestre-1.xlsx",
            "hojas_encontradas": xls.sheet_names,
            "registros_servidores_publicos": filas
        }
    except Exception as e:
        return {"estatus": "Error", "detalle": str(e)}

@app.get("/buscar")
def buscar_remuneracion(q: str = Query(..., description="Termino de busqueda: nombre, puesto o area")):
    ruta = "data/lgt_65_vii.1-trimestre-1.xlsx"
    try:
        # Leemos el excel saltando las cabeceras institucionales para llegar a los datos tabulares
        df = pd.read_excel(ruta, sheet_name='Reporte de Formatos', skiprows=5)
        
        # Limpiamos nombres de columnas por si tienen espacios extra
        df.columns = df.columns.astype(str).str.strip()
        
        # Convertimos todo el DataFrame a texto para hacer una búsqueda global flexible
        df_str = df.astype(str)
        mask = df_str.apply(lambda row: row.str.contains(q, case=False, na=False).any(), axis=1)
        resultado_df = df[mask]
        
        registros = resultado_df.to_dict(orient="records")
        
        return {
            "estatus": "Exito",
            "busqueda": q,
            "total_encontrados": len(registros),
            "resultados": registros
        }
    except Exception as e:
        return {"estatus": "Error", "detalle": str(e)}
