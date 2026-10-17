// Arnés de las pruebas de comportamiento de la página: ejecuta el script real de index.html con
// un navegador simulado (DOM mínimo, sessionStorage, EventSource y fetch) y escribe el resultado
// como JSON. Uso: node harness_pagina.js <escenario>
"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const html = fs.readFileSync(path.join(__dirname, "..", "static", "index.html"), "utf8");
const script = /<script>([\s\S]*?)<\/script>/.exec(html)[1];

const ID_VIEJO = "a".repeat(32);
const ID_NUEVO = "b".repeat(32);

class Nodo {
  constructor(etiqueta) {
    this.etiqueta = etiqueta; this.hijos = []; this.className = ""; this.textContent = "";
    this.value = ""; this.disabled = false; this.escuchas = {}; this.id = "";
  }
  appendChild(hijo) { this.hijos.push(hijo); registro.alta(hijo); return hijo; }
  remove() {}
  focus() { this.enfocado = true; }
  addEventListener(tipo, f) { (this.escuchas[tipo] = this.escuchas[tipo] || []).push(f); }
}

const registro = {
  porId: {},
  alta(n) { if (n && n.id) this.porId[n.id] = n; },
};

function construir(escenario) {
  const almacen = {};
  if (escenario !== "sin_guardada") almacen.cid = ID_VIEJO;
  const flujos = [];
  const llamadas = [];

  class FuenteDeEventos {
    constructor(url) { this.url = url; this.readyState = 1; this.cerrado = false; flujos.push(this); }
    close() { this.cerrado = true; this.readyState = 2; }
  }
  FuenteDeEventos.CLOSED = 2;

  const ventana = { escuchas: {}, scrollTo() {} };
  ventana.addEventListener = (tipo, f) => { (ventana.escuchas[tipo] = ventana.escuchas[tipo] || []).push(f); };

  for (const id of ["conversacion", "trabajando", "aviso", "mensaje", "enviar", "formulario"]) {
    const n = new Nodo("x"); n.id = id; registro.alta(n);
  }
  const documento = {
    body: { scrollHeight: 0 },
    getElementById: (id) => registro.porId[id] || null,
    createElement: (e) => new Nodo(e),
    createTextNode: (t) => { const n = new Nodo("#texto"); n.textContent = t; return n; },
  };
  const fetchFalso = (url, opciones) => {
    llamadas.push({ url: String(url), metodo: (opciones && opciones.method) || "GET" });
    return Promise.resolve({ status: 201, json: () => Promise.resolve({ id: ID_NUEVO }) });
  };
  const contexto = {
    window: ventana, document: documento, EventSource: FuenteDeEventos, fetch: fetchFalso,
    sessionStorage: {
      getItem: (k) => (k in almacen ? almacen[k] : null),
      setItem: (k, v) => { almacen[k] = String(v); },
      removeItem: (k) => { delete almacen[k]; },
    },
    console, Date, Math, Number, String, Array, JSON, isNaN,
  };
  return { almacen, flujos, llamadas, ventana, contexto };
}

const vacio = () => new Promise((r) => setTimeout(r, 0));
const creaciones = (llamadas) =>
  llamadas.filter((l) => l.metodo === "POST" && l.url === "/api/conversaciones").length;

async function main() {
  const escenario = process.argv[2];
  const mundo = construir(escenario);
  vm.runInNewContext(script, mundo.contexto);
  await vacio();
  const salida = {
    cidAlCargar: mundo.almacen.cid || null,
    flujosAlCargar: mundo.flujos.map((f) => f.url),
    creacionesAlCargar: creaciones(mundo.llamadas),
  };

  if (escenario === "descarga") {
    // La página se descarga: el navegador cierra el flujo y avisa con un error.
    for (const tipo of ["beforeunload", "pagehide", "unload"]) {
      for (const f of mundo.ventana.escuchas[tipo] || []) f({});
    }
    const flujo = mundo.flujos[0];
    flujo.readyState = 2;
    if (flujo.onerror) flujo.onerror({});
    await vacio();
  } else if (escenario === "restaurada") {
    // Se descarga y el navegador la restaura desde su caché de navegación (atrás/adelante).
    for (const tipo of ["pagehide", "beforeunload"]) {
      for (const f of mundo.ventana.escuchas[tipo] || []) f({});
    }
    for (const f of mundo.ventana.escuchas.pageshow || []) f({ persisted: true });
    await vacio();
  } else if (escenario === "desconocida") {
    // El servidor ya no conoce la conversación (HTTP 404): el flujo se cierra con error.
    const flujo = mundo.flujos[0];
    flujo.readyState = 2;
    if (flujo.onerror) flujo.onerror({});
    await vacio();
    await vacio();
  }
  salida.cidAlFinal = mundo.almacen.cid || null;
  salida.creacionesAlFinal = creaciones(mundo.llamadas);
  salida.flujosAlFinal = mundo.flujos.map((f) => f.url);
  process.stdout.write(JSON.stringify(salida));
}

main().catch((e) => { process.stderr.write(String(e && e.stack || e)); process.exit(1); });
