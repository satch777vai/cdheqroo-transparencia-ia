from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd

app = FastAPI(title="CDHEQROO - API Transparencia Accesible RAG-Ready")

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
        termino = q.replace('"', '').replace("'", "").strip()
        
        df = pd.read_excel(ruta, sheet_name='Reporte de Formatos')
        df_str = df.fillna("").astype(str)
        
        # Filtro global optimizado
        mask = False
        for col in df_str.columns:
            mask = mask | df_str[col].str.contains(termino, case=False, na=False)
            
        resultado_df = df[mask].fillna("")
        
        # Formateamos los registros para extraer un resumen limpio RAG-Ready
        registros_limpios = []
        for _, row in resultado_df.iterrows():
            # Intentamos extraer columnas clave de manera segura según la estructura del formato
            # Mapeo basado en las posiciones habituales de la Fracción VII
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
                "remuneracion_neta_mensual": sueldo_neto,
                "datos_completos": row.to_dict()
            })
        
        return {
            "estatus": "Exito",
            "busqueda": termino,
            "total_encontrados": len(registros_limpios),
            "resultados": registros_limpios
        }
    except Exception as e:
        return {"estatus": "Error", "detalle": str(e)}
