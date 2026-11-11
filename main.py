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
        # Limpiamos espacios y comillas accidentales de la consulta
        busqueda_limpia = q.strip('"\\'\' ').strip()
        
        df = pd.read_excel(ruta, sheet_name='Reporte de Formatos', skiprows=5)
        df.columns = df.columns.astype(str).str.strip()
        
        # Filtramos eliminando valores nulos
        df_str = df.fillna("").astype(str)
        
        mask = pd.Series([False] * len(df_str))
        for col in df_str.columns:
            mask = mask | df_str[col].str.contains(busqueda_limpia, case=False, na=False)
            
        resultado_df = df[mask].fillna("")
        registros = resultado_df.to_dict(orient="records")
        
        return {
            "estatus": "Exito",
            "busqueda": busqueda_limpia,
            "total_encontrados": len(registros),
            "resultados": registros
        }
    except Exception as e:
        return {"estatus": "Error", "detalle": str(e)}
