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
def buscar_remuneracion(q: str = Query(..., description="Termino de busqueda")):
    ruta = "data/lgt_65_vii.1-trimestre-1.xlsx"
    try:
        # Limpieza segura de comillas o espacios en el texto buscado
        termino = q.replace('"', '').replace("'", "").strip()
        
        df = pd.read_excel(ruta, sheet_name='Reporte de Formatos')
        df_str = df.fillna("").astype(str)
        
        # Filtro global optimizado
        mask = False
        for col in df_str.columns:
            mask = mask | df_str[col].str.contains(termino, case=False, na=False)
            
        resultado_df = df[mask].fillna("")
        registros = resultado_df.to_dict(orient="records")
        
        return {
            "estatus": "Exito",
            "busqueda": termino,
            "total_encontrados": len(registros),
            "resultados": registros
        }
    except Exception as e:
        return {"estatus": "Error", "detalle": str(e)}
