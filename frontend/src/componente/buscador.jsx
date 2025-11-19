import React from "react";
import "../styles/buscador.css";
import { useState } from "react";

export default function Buscador() {
  //  búsqueda
  const [search, setSearch] = useState("");

  return (
    <div className="buscador-content">

      {/* BARRA DE BÚSQUEDA */}
      <div className="search-header">
        <input
          className="search-input"
          placeholder="Buscar..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />

        <div className="search-buttons">
          <button className="btn-help">Buscar</button>
          <button className="btn-new">Ayuda</button>
        </div>
      </div>

    </div>
  );
}