import React, { useState } from "react";
import "../styles/buscador.css";
import { FaSearch, FaArrowRight } from "react-icons/fa";

const CPU_IMAGE_URL = "https://www.shutterstock.com/image-vector/cpu-phone-microchip-smd-electronic-600nw-1949173120.jpg";
const API_BASE_URL = "http://127.0.0.1:8000";

export default function Buscador() {
  const [search, setSearch] = useState("");
  const [results, setResults] = useState([]);
  const [status, setStatus] = useState(null);

  const handleSearch = async () => {
    if (!search || search.length < 1) {
      alert("Ingrese un texto para buscar.");
      return;
    }

    try {
      const encodedQuery = encodeURIComponent(search);
      const clase = "Procesador";

      const response = await fetch(
        `${API_BASE_URL}/buscar?q=${encodedQuery}&clase=${clase}`
      );

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Error en la API");
      }

      const data = await response.json();
      setResults(data.resultados);
    } catch (e) {
      alert(`Error al buscar: ${e.message}`);
      setResults([]);
    }
  };

  const checkApiStatus = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/`);
      const data = await res.json();
      setStatus(data);
    } catch {
      setStatus({ estado: "offline" });
    }
  };

  React.useEffect(() => {
    checkApiStatus();
  }, []);

  // TARJETA DEL RESULTADO 
  const ResultCard = ({ processor }) => (
    <div className="result-card full-detail">
      <h3 className="card-title">{processor.name}</h3>

      <p className="description-text">
        Es un <strong>{processor.clase}</strong> fabricado por{" "}
        <strong>{processor.fabricante}</strong>.
      </p>

      <div className="chip-info-columns">
        {/* PROPIEDADES */}
        <div className="data-properties">
          <h5 className="details-title">Propiedades de Datos</h5>

          {Object.entries(processor.detalles_completos).map(
            ([propiedad, valor]) => (
              <p key={propiedad} className="detail-item">
                <strong>{propiedad.replace("_", " ")}:</strong>{" "}
                {Array.isArray(valor) ? valor.join(", ") : valor}
              </p>
            )
          )}
        </div>

        {/* RELACIONES */}
        {processor.relaciones_completas?.length > 0 && (
          <div className="semantic-relations">
            <h5 className="details-title">Relaciones Semánticas</h5>
            {processor.relaciones_completas.map((rel, idx) => (
              <p key={idx} className="detail-item">
                <strong>{rel.tipo.replace("_", " ")}:</strong> {rel.nombre}
              </p>
            ))}
          </div>
        )}
      </div>

      <div className="card-footer">
        <span className="source-tag">{processor.fuente}</span>
      </div>
    </div>
  );

  return (
    <div className="buscador-content">
      
      {/* LOGO */}
      <div className="logo-container">
        <img src={CPU_IMAGE_URL} alt="CPU" className="logo" />
        <h1 className="logo-text">PROCESADORES</h1>
      </div>

     {/* BARRA DE BÚSQUEDA */}
<div className="search-wrapper">
  <div className="search-box">
    <FaSearch className="search-icon" />

    <input
      className="search-input"
      placeholder="Buscar procesador..."
      value={search}
      onChange={(e) => setSearch(e.target.value)}
      onKeyDown={(e) => e.key === "Enter" && handleSearch()}
    />

    <button className="search-btn" onClick={handleSearch}>
      <FaArrowRight size={18} />
    </button>
  </div>

  {/* FUENTE */}
  <div className="ontology-source">
    <span>Fuente de la Ontología:</span>
    <button className="ontology-btn">OWL Local</button>
  </div>
</div>


      {/* LISTA DE RESULTADOS */}
      <div className="search-results-container">
        <div className="search-results-list">
          {results.length === 0 ? (
            <p className="no-results-message">
              Escribe un término como <strong>Apple</strong> o{" "}
              <strong>Snapdragon</strong>.
            </p>
          ) : (
            results.map((processor) => (
              <ResultCard key={processor.id} processor={processor} />
            ))
          )}
        </div>
      </div>
    </div>
  );
}
