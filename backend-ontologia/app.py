import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from rdflib import Graph, Namespace, RDF, RDFS, Literal

# --- CONFIGURACIÓN ---
app = FastAPI(title="API Ontología Procesadores", version="2.0")

# Configuración CORS (Para que tu frontend pueda conectarse sin bloqueos)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, cambia esto por la URL de tu frontend
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 1. DEFINICIÓN EXACTA DEL NAMESPACE ---
# Extraído directamente de tu archivo ontologia.rdf
URI_BASE = "http://www.semanticweb.org/usuario/ontologies/2025/9/untitled-ontology-26#"
ONTO = Namespace(URI_BASE)

# --- 2. CARGA DE LA ONTOLOGÍA ---
g = Graph()
ARCHIVO_RDF = "ontologia.rdf"

print("⏳ Iniciando carga de la ontología...")
try:
    # Intentamos parsear el archivo
    g.parse(ARCHIVO_RDF, format="xml")
    print(f"✅ ¡Éxito! Ontología cargada. Se encontraron {len(g)} tripletas.")
except FileNotFoundError:
    print(f"❌ ERROR: No se encontró el archivo '{ARCHIVO_RDF}'. Asegúrate de que esté en la misma carpeta que app.py")
except Exception as e:
    print(f"❌ ERROR CRÍTICO cargando el RDF: {e}")

# --- 3. FUNCIONES DE AYUDA ---
def limpiar_valor(valor):
    """
    Convierte una URI larga en un texto simple y limpio.
    Ejemplo: '...#Apple_A16_Bionic' -> 'Apple_A16_Bionic'
    """
    texto = str(valor)
    # Eliminar la base de nuestra ontología
    texto = texto.replace(URI_BASE, "")
    # Eliminar tipos de datos de XML Schema (ej: enteros, strings)
    texto = texto.replace("http://www.w3.org/2001/XMLSchema#", "")
    # Eliminar otras URIs comunes de OWL/RDF
    texto = texto.replace("http://www.w3.org/2002/07/owl#", "")
    return texto

# --- 4. RUTAS (ENDPOINTS) ---

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
    for s in g.subjects(RDF.type, None):
        # Buscamos cosas que sean de tipo 'Class' (owl:Class o rdfs:Class)
        # O simplemente listamos todos los tipos únicos que existen
        for _, _, o in g.triples((s, RDF.type, None)):
            clases.add(limpiar_valor(o))
    return {"clases_encontradas": list(clases)}

@app.get("/procesadores")
def listar_procesadores():
    """
    Busca específicamente individuos que sean de tipo 'Procesador'.
    """
    procesadores = []
    # Buscamos (Sujeto) que tenga (Predicado: es un) (Objeto: Procesador)
    # Usamos ONTO.Procesador porque así se llama tu clase en el RDF
    for s in g.subjects(RDF.type, ONTO.Procesador):
        procesadores.append(limpiar_valor(s))
    
    # Si la lista está vacía, hacemos un diagnóstico rápido
    if not procesadores:
        # Intento de búsqueda "laxa" por si el namespace falló
        debug_list = []
        for s, _, o in g.triples((None, RDF.type, None)):
            if "Procesador" in str(o):
                debug_list.append(limpiar_valor(s))
        
        if debug_list:
            return {
                "mensaje": "No se encontraron con coincidencia exacta, pero encontré estos similares (revisa el namespace):",
                "sugerencias": debug_list
            }
            
    return {"cantidad": len(procesadores), "resultados": procesadores}

@app.get("/procesador/{nombre_procesador}")
def detalle_procesador(nombre_procesador: str):
    """
    Obtiene todas las propiedades de un procesador específico.
    Ejemplo: /procesador/Apple_A16_Bionic
    """
    # Reconstruimos la URI completa
    uri_sujeto = ONTO[nombre_procesador]
    
    # Verificamos si existe al menos una propiedad para este sujeto
    if (uri_sujeto, None, None) not in g:
        raise HTTPException(status_code=404, detail=f"El procesador '{nombre_procesador}' no fue encontrado en la base de datos.")

    info = {}
    # Recorremos todas las propiedades (predicado) y valores (objeto) de este sujeto
    for predicado, objeto in g.predicate_objects(uri_sujeto):
        propiedad_limpia = limpiar_valor(predicado)
        valor_limpio = limpiar_valor(objeto)
        
        # Excluir metadatos internos aburridos (opcional)
        if propiedad_limpia in ["type", "NamedIndividual"]:
            continue

        # Si la propiedad ya existe (ej: tiene multiple nucleos), la convertimos en lista
        if propiedad_limpia in info:
            if not isinstance(info[propiedad_limpia], list):
                info[propiedad_limpia] = [info[propiedad_limpia]]
            info[propiedad_limpia].append(valor_limpio)
        else:
            info[propiedad_limpia] = valor_limpio

    return {
        "id": nombre_procesador,
        "datos": info
    }

# --- EJECUCIÓN ---
if __name__ == "__main__":
    # Esto permite correrlo con "python app.py"
    uvicorn.run(app, host="127.0.0.1", port=8000)