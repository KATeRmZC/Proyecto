import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from rdflib import Graph, Namespace, RDF, RDFS, Literal
from rdflib import URIRef 
from typing import List, Dict, Any

# --- CONFIGURACIÓN Y CARGA DE ONTOLOGÍA ---

# Inicializa el grafo
g = Graph()

ONTOLOGY_FILE = "ontologia.rdf" 

try:
    g.parse(ONTOLOGY_FILE)
    print(f"Ontología cargada con éxito. Tripletas: {len(g)}")
except Exception as e:
    print(f"Error al cargar la ontología '{ONTOLOGY_FILE}': {e}")
    # Si la carga falla, el programa continuará, pero las búsquedas fallarán.

# 1. DEFINICIÓN EXACTA DEL NAMESPACE
URI_BASE = "http://www.semanticweb.org/usuario/ontologies/2025/9/untitled-ontology-26#"
ONTO = Namespace(URI_BASE)

# Namespaces estándar
RDF = RDF
RDFS = RDFS

# Inicialización de FastAPI
app = FastAPI(title="API Ontología Procesadores", version="3.0 - Full Detail", description="Carga todos los detalles en la búsqueda inicial.")

# Configuración CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- FUNCIONES AUXILIARES ---

def limpiar_valor(uri_o_literal):
    """Limpia una URI o Literal para obtener un nombre legible."""
    if isinstance(uri_o_literal, Literal):
        return str(uri_o_literal.toPython())
    
    if str(uri_o_literal).startswith(URI_BASE):
        return str(uri_o_literal).replace(URI_BASE, "")
    
    return str(uri_o_literal).split('#')[-1]


def obtener_detalles_contexto(nombre_entidad: str) -> Dict[str, Any]:
    """
    Función auxiliar que obtiene todas las DataProperties y ObjectProperties
    de un individuo específico (usada por /buscar y /procesador/{id}).
    """
    uri_sujeto = ONTO[nombre_entidad]
    
    if (uri_sujeto, None, None) not in g:
        # Se lanza una excepción si se usa directamente, pero en el loop de /buscar simplemente devuelve un dict vacío
        return {"id": nombre_entidad, "datos": {}, "relaciones": []}

    datos = {}
    relaciones = []
    
    for predicado, objeto in g.predicate_objects(uri_sujeto):
        propiedad_limpia = limpiar_valor(predicado)
        
        if propiedad_limpia in ["type", "NamedIndividual"]:
            continue
        
        # Si el Objeto es una URI, es una RELACIÓN (ObjectProperty)
        if isinstance(objeto, URIRef) and str(objeto).startswith(URI_BASE):
            relaciones.append({
                "tipo": propiedad_limpia,
                "nombre": limpiar_valor(objeto).replace('_', ' ')
            })
        # Si es un Literal, es un DATO (DataProperty)
        else:
            valor_limpio = limpiar_valor(objeto)
            
            # Manejo de múltiples valores para la misma DataProperty
            if propiedad_limpia in datos:
                if not isinstance(datos[propiedad_limpia], list):
                    datos[propiedad_limpia] = [datos[propiedad_limpia]]
                datos[propiedad_limpia].append(valor_limpio)
            else:
                datos[propiedad_limpia] = valor_limpio

    return {
        "id": nombre_entidad,
        "datos": datos,
        "relaciones": relaciones
    }


# --- ENDPOINTS (RUTAS) DE LA API ---

@app.get("/")
def inicio():
    """Ruta de prueba para verificar que el servidor respira."""
    return {
        "estado": "online",
        "mensaje": "API de Procesadores funcionando",
        "tripletas_cargadas": len(g),
        "namespace_usado": URI_BASE
    }

@app.get("/clases")
def listar_clases():
    """Devuelve todas las Clases definidas (ej: Procesador, GPU, Fabricante)."""
    clases = set()
    query = """
    SELECT DISTINCT ?clase
    WHERE {
        { ?clase a rdfs:Class }
        UNION
        { ?clase a owl:Class }
    }
    """
    
    # Ejecutar la consulta SPARQL (más robusta)
    for row in g.query(query, initNs={"rdfs": RDFS, "owl": Namespace("http://www.w3.org/2002/07/owl#")}):
        clases.add(limpiar_valor(row.clase))
        
    # Limpieza final de clases no deseadas
    irrelevant_classes = ["Class", "Thing", "NamedIndividual", "AnnotationProperty", "ObjectProperty", "DatatypeProperty", "Ontology"]
    clases_limpias = [c for c in clases if c not in irrelevant_classes]
        
    return {"clases_encontradas": clases_limpias}


@app.get("/buscar")
def buscar_semantico(
    q: str = Query(..., min_length=1), 
    clase: str = Query("Procesador")
):
    """
    Busca entidades por nombre, filtrando por una clase ontológica específica,
    y carga todos los detalles en la respuesta inicial.
    """
    
    clase_uri = ONTO[clase.strip().replace(" ", "_")]
    
    PREFIXES = f"""
        PREFIX rdf: <{RDF}>
        PREFIX onto: <{ONTO}> 
    """
    
    # Consulta SPARQL para obtener los IDs (URIs) de los individuos
    SPARQL_QUERY = PREFIXES + f"""
        SELECT DISTINCT ?entidad
        WHERE {{
            # FILTRO PRINCIPAL: La entidad debe ser de la clase especificada
            ?entidad rdf:type <{clase_uri}> . 
            
            # Busqueda: el filtro permite encontrar coincidencias en la URI
            FILTER (regex(str(?entidad), "{q}", "i"))
        }}
        LIMIT 20
    """
    
    resultados_ids_raw = g.query(SPARQL_QUERY)
    resultados_completos = []
    
    for row in resultados_ids_raw:
        uri_full = str(row.entidad)
        nombre_limpio = limpiar_valor(uri_full)
        
        # *** MODIFICACIÓN CRÍTICA: Llamar a la función de detalles para cada ID ***
        detalles_contexto = obtener_detalles_contexto(nombre_limpio)
        
        # Crear la estructura de la respuesta para el Frontend
        resultado_completo = {
            "id": nombre_limpio,
            "name": nombre_limpio.replace('_', ' '),
            "clase": clase, 
            "fuente": "OWL Local",
            # Datos resumidos que puedes extraer de los detalles completos (opcional, pero ayuda)
            "frecuencia": detalles_contexto['datos'].get('frecuencia_max_GHz', 'N/A'),
            "proceso": detalles_contexto['datos'].get('tecnologia_nm', 'N/A'),
            "fabricante": next((rel['nombre'] for rel in detalles_contexto['relaciones'] if rel['tipo'] == 'esFabricadoPor'), 'N/A'),
            
            # ¡NUEVOS CAMPOS CLAVE PARA EL FRONTEND!
            "detalles_completos": detalles_contexto['datos'],
            "relaciones_completas": detalles_contexto['relaciones']
        }
        resultados_completos.append(resultado_completo)
        
    return {"cantidad": len(resultados_completos), "resultados": resultados_completos}


@app.get("/procesador/{nombre_procesador}")
def detalle_procesador(nombre_procesador: str):
    """
    Obtiene todas las propiedades (datos y relaciones) de un individuo específico.
    Ahora usa la función auxiliar 'obtener_detalles_contexto'.
    """
    detalles_contexto = obtener_detalles_contexto(nombre_procesador)
    
    if not detalles_contexto['datos'] and not detalles_contexto['relaciones']:
        raise HTTPException(status_code=404, detail=f"El procesador '{nombre_procesador}' no fue encontrado en la base de datos.")

    return {
        "id": detalles_contexto['id'],
        "datos": detalles_contexto['datos'],
        "relaciones": detalles_contexto['relaciones']
    }

# Código para iniciar Uvicorn si este script se ejecuta directamente
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)