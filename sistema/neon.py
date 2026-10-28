"""Base de datos de Clinicas Odontologicas en Neon (PostgreSQL en la nube).

Crea las mismas tablas que usa el sistema, pero en PostgreSQL, y siembra las
cuentas de ejemplo. Sirve para tener la base en linea (varias computadoras
conectadas a la misma base) en lugar del archivo local dientecito.db.

Preparacion (una sola vez):
  1. Cree una cuenta en https://neon.tech y un proyecto.
  2. Copie la cadena de conexion que le da Neon. Se ve asi:
     postgresql://usuario:clave@ep-algo-123.us-east-2.aws.neon.tech/neondb?sslmode=require
  3. Guardela en la variable de entorno NEON_URL (o DATABASE_URL):
       PowerShell:  $env:NEON_URL = "postgresql://..."
       CMD:         set NEON_URL=postgresql://...
     O escribala en un archivo .neon_url junto a este archivo (git lo ignora).
  4. pip install "psycopg[binary]"

Uso:
  python neon.py              crea las tablas que falten y las cuentas de ejemplo
  python neon.py --probar     solo prueba la conexion y lista las tablas
  python neon.py --sql        imprime el SQL, para pegarlo en el editor de Neon
  python neon.py --importar   copia a Neon lo que ya haya en dientecito.db
"""
import argparse
import os
import sqlite3
import sys
from pathlib import Path

RAIZ = Path(__file__).parent
SQLITE = RAIZ / "dientecito.db"

# Mismo modelo de datos que app.py, escrito para PostgreSQL:
# SERIAL en lugar de INTEGER PRIMARY KEY, y DOUBLE PRECISION en lugar de REAL.
ESQUEMA = """
CREATE TABLE IF NOT EXISTS usuarios(
    id SERIAL PRIMARY KEY, usuario TEXT UNIQUE NOT NULL, nombre TEXT NOT NULL,
    rol TEXT NOT NULL, clave TEXT NOT NULL, activo INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS pacientes(
    id SERIAL PRIMARY KEY, nombre TEXT NOT NULL, cedula TEXT UNIQUE NOT NULL,
    telefono TEXT, correo TEXT, nacimiento TEXT, sexo TEXT, direccion TEXT,
    contacto_emergencia TEXT, contacto_emergencia_nombre TEXT, contacto_emergencia_telefono TEXT,
    alergias TEXT, motivo_consulta TEXT, antecedentes TEXT, medicamentos TEXT,
    examen_clinico TEXT, plan TEXT, docente TEXT, aprobado INTEGER DEFAULT 0,
    firma TEXT, firma_fecha TEXT, archivado INTEGER DEFAULT 0,
    estudiante_id INTEGER REFERENCES usuarios(id));
CREATE TABLE IF NOT EXISTS salas(id SERIAL PRIMARY KEY, nombre TEXT UNIQUE NOT NULL);
CREATE TABLE IF NOT EXISTS citas(
    id SERIAL PRIMARY KEY,
    paciente_id INTEGER NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,
    fecha TEXT NOT NULL, hora TEXT NOT NULL, motivo TEXT, estudiante TEXT,
    estado TEXT DEFAULT 'Pendiente', sala_id INTEGER REFERENCES salas(id), token TEXT);
CREATE TABLE IF NOT EXISTS odontograma(
    paciente_id INTEGER REFERENCES pacientes(id) ON DELETE CASCADE,
    diente INTEGER, estado TEXT, PRIMARY KEY(paciente_id, diente));
CREATE TABLE IF NOT EXISTS odonto_sesiones(
    id SERIAL PRIMARY KEY,
    paciente_id INTEGER NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,
    foto TEXT NOT NULL, nota TEXT, fecha TEXT NOT NULL, usuario_id INTEGER REFERENCES usuarios(id),
    estado TEXT DEFAULT 'Abierta', enviado TEXT, observacion TEXT,
    revisado_por INTEGER REFERENCES usuarios(id), revisado TEXT);
CREATE TABLE IF NOT EXISTS odonto_registros(
    id SERIAL PRIMARY KEY,
    paciente_id INTEGER NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,
    diente INTEGER NOT NULL, estado TEXT NOT NULL, descripcion TEXT, foto TEXT NOT NULL,
    fecha TEXT NOT NULL, usuario_id INTEGER REFERENCES usuarios(id),
    revision TEXT DEFAULT 'Pendiente', observacion TEXT, revisado_por INTEGER REFERENCES usuarios(id),
    sesion_id INTEGER REFERENCES odonto_sesiones(id));
CREATE TABLE IF NOT EXISTS asignaciones(
    id SERIAL PRIMARY KEY,
    paciente_id INTEGER NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,
    estudiante_id INTEGER REFERENCES usuarios(id),
    desde TEXT NOT NULL, hasta TEXT, resumen TEXT);
CREATE TABLE IF NOT EXISTS tratamientos(
    id SERIAL PRIMARY KEY,
    paciente_id INTEGER NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,
    procedimiento TEXT NOT NULL, diente TEXT, costo DOUBLE PRECISION DEFAULT 0,
    pagado DOUBLE PRECISION DEFAULT 0, estado TEXT DEFAULT 'Pendiente', fecha TEXT);
CREATE TABLE IF NOT EXISTS tarifario(
    id SERIAL PRIMARY KEY, procedimiento TEXT UNIQUE NOT NULL, precio DOUBLE PRECISION DEFAULT 0);
CREATE TABLE IF NOT EXISTS inventario(
    id SERIAL PRIMARY KEY, material TEXT UNIQUE NOT NULL, unidad TEXT,
    cantidad INTEGER DEFAULT 0, minimo INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS reportes(
    id SERIAL PRIMARY KEY, sala_id INTEGER NOT NULL REFERENCES salas(id) ON DELETE CASCADE,
    tipo TEXT NOT NULL, descripcion TEXT, estado TEXT DEFAULT 'Pendiente',
    reportado_por INTEGER REFERENCES usuarios(id), fecha TEXT NOT NULL,
    atendido_por INTEGER REFERENCES usuarios(id), actualizado TEXT);
CREATE TABLE IF NOT EXISTS bitacora(
    id SERIAL PRIMARY KEY, fecha TEXT NOT NULL, usuario_id INTEGER, accion TEXT NOT NULL,
    detalle TEXT, paciente_id INTEGER);
CREATE INDEX IF NOT EXISTS bitacora_paciente ON bitacora(paciente_id);
CREATE INDEX IF NOT EXISTS asignaciones_paciente ON asignaciones(paciente_id);
"""
# Orden de copiado: una tabla nunca va antes de aquella a la que apunta
TABLAS = ["usuarios", "salas", "pacientes", "citas", "odontograma", "odonto_sesiones",
          "odonto_registros", "asignaciones", "tratamientos", "tarifario", "inventario",
          "reportes", "bitacora"]


def cadena():
    """Cadena de conexion de Neon: variable de entorno o archivo .neon_url."""
    archivo = RAIZ / ".neon_url"
    url = os.environ.get("NEON_URL") or os.environ.get("DATABASE_URL") or (
        archivo.read_text(encoding="utf-8").strip() if archivo.exists() else "")
    if not url:
        sys.exit("Falta la cadena de conexion. Guardela en NEON_URL o en el archivo .neon_url "
                 "(vea las instrucciones al inicio de este archivo).")
    return url


def conectar():
    try:
        import psycopg
    except ModuleNotFoundError:
        sys.exit('Falta el conector de PostgreSQL. Instalelo con:  pip install "psycopg[binary]"')
    return psycopg.connect(cadena(), autocommit=True)


def crear(con):
    con.execute(ESQUEMA)
    print("Tablas creadas (las que ya existian quedaron igual).")


def sembrar(con):
    """Cuentas de ejemplo y salas, solo si la base esta vacia."""
    from app import CLAVE_INICIAL, CUENTAS_EJEMPLO  # mismas cuentas que usa el sistema
    from werkzeug.security import generate_password_hash
    if con.execute("SELECT 1 FROM usuarios LIMIT 1").fetchone():
        print("Ya hay usuarios: no se siembra nada.")
        return
    for cif, nombre, rol in CUENTAS_EJEMPLO:
        con.execute("INSERT INTO usuarios(usuario, nombre, rol, clave) VALUES (%s, %s, %s, %s)",
                    (cif, nombre, rol, generate_password_hash(CLAVE_INICIAL)))
    for nombre in ("Sala 1", "Sala 2", "Sala 3"):
        con.execute("INSERT INTO salas(nombre) VALUES (%s) ON CONFLICT (nombre) DO NOTHING", (nombre,))
    print(f"Sembradas {len(CUENTAS_EJEMPLO)} cuentas de ejemplo (clave {CLAVE_INICIAL}) y 3 salas.")


def columnas(con, tabla):
    return [f[0] for f in con.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name = %s", (tabla,)).fetchall()]


def importar(con):
    """Copia a Neon lo que haya en dientecito.db (solo las filas que faltan)."""
    if not SQLITE.exists():
        sys.exit(f"No existe {SQLITE.name}: no hay nada que copiar.")
    local = sqlite3.connect(SQLITE)
    local.row_factory = sqlite3.Row
    existentes = {f[0] for f in local.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()}
    for tabla in TABLAS:
        if tabla not in existentes:
            continue
        destino = columnas(con, tabla)
        filas = local.execute(f"SELECT * FROM {tabla}").fetchall()
        comunes = [c for c in filas[0].keys() if c in destino] if filas else []
        copiadas = 0
        for fila in filas:
            marcas = ", ".join(["%s"] * len(comunes))
            con.execute(f"INSERT INTO {tabla} ({', '.join(comunes)}) VALUES ({marcas}) "
                        "ON CONFLICT DO NOTHING", tuple(fila[c] for c in comunes))
            copiadas += 1
        if "id" in destino:  # el contador de ids debe quedar despues del ultimo copiado
            con.execute(f"SELECT setval(pg_get_serial_sequence('{tabla}', 'id'), "
                        f"GREATEST((SELECT COALESCE(MAX(id), 1) FROM {tabla}), 1))")
        print(f"  {tabla}: {copiadas} filas")
    local.close()
    print("Copia terminada.")


def probar(con):
    version = con.execute("SELECT version()").fetchone()[0]
    print("Conectado a:", version.split(",")[0])
    tablas = con.execute("SELECT table_name, (SELECT COUNT(*) FROM information_schema.columns c "
                         "WHERE c.table_name = t.table_name) FROM information_schema.tables t "
                         "WHERE table_schema = 'public' ORDER BY table_name").fetchall()
    if not tablas:
        print("La base esta vacia: ejecute  python neon.py  para crear las tablas.")
    for nombre, cuantas in tablas:
        filas = con.execute(f"SELECT COUNT(*) FROM {nombre}").fetchone()[0]
        print(f"  {nombre:18} {cuantas:2} columnas, {filas} filas")


if __name__ == "__main__":
    opciones = argparse.ArgumentParser(description="Base de datos de Clinicas Odontologicas en Neon")
    opciones.add_argument("--probar", action="store_true", help="solo probar la conexion")
    opciones.add_argument("--sql", action="store_true", help="imprimir el SQL y salir")
    opciones.add_argument("--importar", action="store_true", help="copiar los datos de dientecito.db")
    args = opciones.parse_args()

    if args.sql:
        print(ESQUEMA)
        sys.exit()
    con = conectar()
    if args.probar:
        probar(con)
    elif args.importar:
        crear(con)
        importar(con)
    else:
        crear(con)
        sembrar(con)
        probar(con)
    con.close()
