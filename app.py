"""Dientecito Feliz - Clinica Odontologica UAM
Aplicacion web (Flask + SQLite) para computadora y telefono.
Tres interfaces segun el rol del usuario: estudiante, profesor y servicios.

Ejecutar:   python app.py
Luego abrir la direccion que aparece en consola (el telefono debe estar en la misma red Wi-Fi).
"""
import os
import re
import secrets
import shutil
import socket
import sqlite3
import tempfile
import uuid
import zipfile
from datetime import date, datetime, timedelta, timezone
from functools import wraps
from pathlib import Path
from urllib.parse import quote

from flask import (Flask, abort, flash, g, jsonify, redirect, render_template, request,
                   send_file, send_from_directory, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

RAIZ = Path(__file__).parent
DB = RAIZ / "dientecito.db"
FOTOS = RAIZ / "fotos"
RESPALDOS = RAIZ / "respaldos"  # copia diaria automatica de la base de datos
DIAS_RESPALDO = 14
CLAVE_INICIAL = os.environ.get("DIENTECITO_CLAVE", "uam2026")  # clave de las cuentas de ejemplo
DEMO = bool(os.environ.get("DIENTECITO_DEMO"))  # servidor publico de prueba: muestra aviso de datos ficticios
NICARAGUA = timezone(timedelta(hours=-6))  # el servidor puede estar en UTC

ROLES = {"estudiante": "Estudiante", "profesor": "Profesor", "servicios": "Servicios"}
MENUS = {
    "estudiante": [("inicio", "Inicio"), ("pacientes", "Mis pacientes"), ("citas", "Citas"), ("salas", "Salas")],
    "profesor": [("inicio", "Inicio"), ("pacientes", "Pacientes"), ("citas", "Citas"), ("salas", "Salas"),
                 ("tarifario", "Tarifario"), ("usuarios", "Usuarios"), ("bitacora", "Bitácora")],
    "servicios": [("avisos", "Avisos"), ("salas", "Salas"), ("inventario", "Inventario")],
}
ESTADOS_DIENTE = {"Sano": "#ffffff", "Caries": "#c0504d", "Obturado": "#4f81bd",
                  "Corona": "#c9a94a", "Endodoncia": "#8064a2", "Extraido": "#a5a5a5"}
ESTADOS_CITA = ["Pendiente", "Confirmada", "Atendida", "No asistió", "Cancelada"]
TIPOS_REPORTE = ["Reparación", "Limpieza"]
# Sesion de odontograma: Abierta -> (enviar) Pendiente -> Aprobado | Corregir -> (enviar) Pendiente ...
EDITABLES = ("Abierta", "Corregir")
# Numeracion FDI: arcada superior e inferior, de derecha a izquierda del paciente
SUPERIOR = [18, 17, 16, 15, 14, 13, 12, 11, 21, 22, 23, 24, 25, 26, 27, 28]
INFERIOR = [48, 47, 46, 45, 44, 43, 42, 41, 31, 32, 33, 34, 35, 36, 37, 38]
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

ESQUEMA = """
CREATE TABLE IF NOT EXISTS usuarios(
    id INTEGER PRIMARY KEY, usuario TEXT UNIQUE NOT NULL, nombre TEXT NOT NULL,
    rol TEXT NOT NULL, clave TEXT NOT NULL, activo INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS pacientes(
    id INTEGER PRIMARY KEY, nombre TEXT NOT NULL, cedula TEXT UNIQUE NOT NULL,
    telefono TEXT, nacimiento TEXT, alergias TEXT);
CREATE TABLE IF NOT EXISTS salas(id INTEGER PRIMARY KEY, nombre TEXT UNIQUE NOT NULL);
CREATE TABLE IF NOT EXISTS citas(
    id INTEGER PRIMARY KEY,
    paciente_id INTEGER NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,
    fecha TEXT NOT NULL, hora TEXT NOT NULL, motivo TEXT, estudiante TEXT);
CREATE TABLE IF NOT EXISTS odontograma(
    paciente_id INTEGER REFERENCES pacientes(id) ON DELETE CASCADE,
    diente INTEGER, estado TEXT, PRIMARY KEY(paciente_id, diente));
CREATE TABLE IF NOT EXISTS odonto_sesiones(
    id INTEGER PRIMARY KEY,
    paciente_id INTEGER NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,
    foto TEXT NOT NULL, nota TEXT, fecha TEXT NOT NULL, usuario_id INTEGER REFERENCES usuarios(id),
    estado TEXT DEFAULT 'Abierta', enviado TEXT, observacion TEXT,
    revisado_por INTEGER REFERENCES usuarios(id), revisado TEXT);
CREATE TABLE IF NOT EXISTS odonto_registros(
    id INTEGER PRIMARY KEY,
    paciente_id INTEGER NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,
    diente INTEGER NOT NULL, estado TEXT NOT NULL, descripcion TEXT, foto TEXT NOT NULL,
    fecha TEXT NOT NULL, usuario_id INTEGER REFERENCES usuarios(id),
    revision TEXT DEFAULT 'Pendiente', observacion TEXT, revisado_por INTEGER REFERENCES usuarios(id));
CREATE TABLE IF NOT EXISTS tratamientos(
    id INTEGER PRIMARY KEY,
    paciente_id INTEGER NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,
    procedimiento TEXT NOT NULL, diente TEXT, costo REAL DEFAULT 0, pagado REAL DEFAULT 0,
    estado TEXT DEFAULT 'Pendiente', fecha TEXT);
CREATE TABLE IF NOT EXISTS tarifario(
    id INTEGER PRIMARY KEY, procedimiento TEXT UNIQUE NOT NULL, precio REAL DEFAULT 0);
CREATE TABLE IF NOT EXISTS inventario(
    id INTEGER PRIMARY KEY, material TEXT UNIQUE NOT NULL, unidad TEXT,
    cantidad INTEGER DEFAULT 0, minimo INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS reportes(
    id INTEGER PRIMARY KEY, sala_id INTEGER NOT NULL REFERENCES salas(id) ON DELETE CASCADE,
    tipo TEXT NOT NULL, descripcion TEXT, estado TEXT DEFAULT 'Pendiente',
    reportado_por INTEGER REFERENCES usuarios(id), fecha TEXT NOT NULL,
    atendido_por INTEGER REFERENCES usuarios(id), actualizado TEXT);
CREATE TABLE IF NOT EXISTS bitacora(
    id INTEGER PRIMARY KEY, fecha TEXT NOT NULL, usuario_id INTEGER, accion TEXT NOT NULL,
    detalle TEXT, paciente_id INTEGER);
CREATE INDEX IF NOT EXISTS bitacora_paciente ON bitacora(paciente_id);
"""
# Columnas agregadas despues de las primeras versiones; se anaden a bases ya existentes
COLUMNAS_NUEVAS = {
    "pacientes": ["sexo TEXT", "direccion TEXT", "contacto_emergencia TEXT", "motivo_consulta TEXT",
                  "antecedentes TEXT", "medicamentos TEXT", "examen_clinico TEXT", "plan TEXT",
                  "docente TEXT", "aprobado INTEGER DEFAULT 0", "firma TEXT", "firma_fecha TEXT",
                  "estudiante_id INTEGER REFERENCES usuarios(id)", "archivado INTEGER DEFAULT 0"],
    "citas": ["estado TEXT DEFAULT 'Pendiente'", "sala_id INTEGER REFERENCES salas(id)"],
    "odonto_registros": ["sesion_id INTEGER REFERENCES odonto_sesiones(id)"],
}
CAMPOS_PACIENTE = ["nombre", "cedula", "telefono", "nacimiento", "sexo", "direccion",
                   "contacto_emergencia", "alergias", "motivo_consulta", "antecedentes",
                   "medicamentos", "examen_clinico", "plan"]
ACTIVOS = " AND COALESCE(p.archivado, 0) = 0"  # los pacientes archivados no aparecen en las listas
CITAS_SQL = """SELECT c.*, p.nombre, p.telefono, p.estudiante_id, u.nombre AS estudiante_nombre, s.nombre AS sala
               FROM citas c JOIN pacientes p ON p.id = c.paciente_id
               LEFT JOIN usuarios u ON u.id = p.estudiante_id LEFT JOIN salas s ON s.id = c.sala_id WHERE 1 = 1"""
SESIONES_SQL = """SELECT s.*, p.nombre AS paciente, u.nombre AS autor, v.nombre AS revisor,
                         (SELECT GROUP_CONCAT(r.diente || ': ' || r.estado, ' · ') FROM odonto_registros r
                          WHERE r.sesion_id = s.id) AS cambios
                  FROM odonto_sesiones s JOIN pacientes p ON p.id = s.paciente_id
                  LEFT JOIN usuarios u ON u.id = s.usuario_id LEFT JOIN usuarios v ON v.id = s.revisado_por
                  WHERE 1 = 1"""
BITACORA_SQL = """SELECT b.*, u.nombre AS usuario, p.nombre AS paciente FROM bitacora b
                  LEFT JOIN usuarios u ON u.id = b.usuario_id LEFT JOIN pacientes p ON p.id = b.paciente_id"""
REPORTES_SQL = """SELECT r.*, s.nombre AS sala, u.nombre AS reporta, a.nombre AS atiende
                  FROM reportes r JOIN salas s ON s.id = r.sala_id
                  LEFT JOIN usuarios u ON u.id = r.reportado_por LEFT JOIN usuarios a ON a.id = r.atendido_por"""

app = Flask(__name__)
app.secret_key = os.environ.get("DIENTECITO_SECRETO") or secrets.token_hex(16)
app.config["MAX_CONTENT_LENGTH"] = 15 * 1024 * 1024  # fotos de hasta 15 MB
app.jinja_env.globals.update(ESTADOS_DIENTE=ESTADOS_DIENTE, ESTADOS_CITA=ESTADOS_CITA, SUPERIOR=SUPERIOR,
                             INFERIOR=INFERIOR, DEMO=DEMO, ROLES=ROLES, TIPOS_REPORTE=TIPOS_REPORTE,
                             ESTADO_SESION={"Abierta": "En edición", "Pendiente": "Por revisar",
                                            "Aprobado": "Aprobado", "Corregir": "Corregir"})


# ---------- base de datos ----------
def iniciar_db():
    con = sqlite3.connect(DB)
    con.executescript(ESQUEMA)
    for tabla, columnas in COLUMNAS_NUEVAS.items():
        existentes = {fila[1] for fila in con.execute(f"PRAGMA table_info({tabla})")}
        for col in columnas:
            if col.split()[0] not in existentes:
                con.execute(f"ALTER TABLE {tabla} ADD COLUMN {col}")
    # Registros de la version anterior (una foto por diente): cada uno pasa a ser una sesion con su foto
    viejos = con.execute("SELECT id, paciente_id, foto, descripcion, fecha, usuario_id, revision, observacion, "
                         "revisado_por FROM odonto_registros WHERE sesion_id IS NULL").fetchall()
    for rid, pid, foto, nota, fecha, uid, revision, observacion, revisor in viejos:
        sid = con.execute("INSERT INTO odonto_sesiones(paciente_id, foto, nota, fecha, usuario_id, estado, enviado, "
                          "observacion, revisado_por) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                          (pid, foto, nota, fecha, uid, revision or "Pendiente", fecha, observacion, revisor)).lastrowid
        con.execute("UPDATE odonto_registros SET sesion_id = ? WHERE id = ?", (sid, rid))
    if not con.execute("SELECT 1 FROM usuarios").fetchone():
        for usuario, nombre, rol in [("profesor", "Profesor de prueba", "profesor"),
                                     ("estudiante", "Estudiante de prueba", "estudiante"),
                                     ("servicios", "Servicios generales", "servicios")]:
            con.execute("INSERT INTO usuarios(usuario, nombre, rol, clave) VALUES (?, ?, ?, ?)",
                        (usuario, nombre, rol, generate_password_hash(CLAVE_INICIAL)))
        # Los pacientes de versiones anteriores pasan al estudiante de ejemplo
        con.execute("UPDATE pacientes SET estudiante_id = (SELECT id FROM usuarios WHERE usuario = 'estudiante') "
                    "WHERE estudiante_id IS NULL")
    if not con.execute("SELECT 1 FROM salas").fetchone():
        con.executemany("INSERT INTO salas(nombre) VALUES (?)", [("Sala 1",), ("Sala 2",), ("Sala 3",)])
    con.commit()
    con.close()


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def cerrar_db(_):
    if (con := g.pop("db", None)) is not None:
        con.close()


def q(sql, args=(), uno=False):
    cur = db().execute(sql, args)
    return cur.fetchone() if uno else cur.fetchall()


def ejecutar(sql, args=()):
    with db() as con:
        return con.execute(sql, args).lastrowid


def ahora():
    return datetime.now(NICARAGUA)


def hoy():
    return ahora().date()


def numero(texto):
    try:
        return max(0.0, float(str(texto).replace(",", ".")))
    except ValueError:
        return 0.0


def volver(pid, seccion):
    return redirect(url_for("expediente", pid=pid, _anchor=seccion))


def regresar(defecto):
    destino = request.form.get("volver", "")
    return redirect(destino if destino.startswith("/") and not destino.startswith("//") else defecto)


def anotar(accion, detalle="", paciente_id=None, usuario_id=None):
    """Deja constancia en la bitacora de quien hizo que y cuando."""
    if usuario_id is None and g.get("usuario"):
        usuario_id = g.usuario["id"]
    ejecutar("INSERT INTO bitacora(fecha, usuario_id, accion, detalle, paciente_id) VALUES (?, ?, ?, ?, ?)",
             (ahora().strftime("%Y-%m-%d %H:%M:%S"), usuario_id, accion, detalle, paciente_id))


def copiar_db(destino):
    """Copia consistente de la base de datos aunque este en uso (API de respaldo de SQLite)."""
    origen, copia = sqlite3.connect(DB), sqlite3.connect(destino)
    with copia:
        origen.backup(copia)
    copia.close()
    origen.close()


def respaldo_diario():
    destino = RESPALDOS / f"dientecito-{hoy().isoformat()}.db"
    if destino.exists():
        return
    RESPALDOS.mkdir(exist_ok=True)
    temporal = destino.with_suffix(".tmp")
    copiar_db(temporal)
    temporal.replace(destino)
    for viejo in sorted(RESPALDOS.glob("dientecito-*.db"))[:-DIAS_RESPALDO]:
        viejo.unlink()


def guardar_foto(archivo):
    """Guarda la foto si es una imagen real (JPG, PNG, WEBP o HEIC) y devuelve su nombre."""
    if not archivo or not archivo.filename:
        return None
    cabecera = archivo.stream.read(16)
    archivo.stream.seek(0)
    if cabecera.startswith(b"\xff\xd8\xff"):
        ext = ".jpg"
    elif cabecera.startswith(b"\x89PNG"):
        ext = ".png"
    elif cabecera[:4] == b"RIFF" and cabecera[8:12] == b"WEBP":
        ext = ".webp"
    elif cabecera[4:8] == b"ftyp":  # fotos de iPhone
        ext = ".heic"
    else:
        return None
    FOTOS.mkdir(exist_ok=True)
    nombre = uuid.uuid4().hex + ext
    archivo.save(FOTOS / nombre)
    return nombre


# ---------- usuarios y permisos ----------
def es(rol):
    return g.usuario["rol"] == rol


def solo(*roles):
    def decorador(vista):
        @wraps(vista)
        def envuelta(*args, **kwargs):
            if g.usuario["rol"] not in roles:
                abort(403)
            return vista(*args, **kwargs)
        return envuelta
    return decorador


def alcance(alias="p"):
    """Filtro SQL: cada estudiante solo ve sus propios pacientes."""
    return f" AND {alias}.estudiante_id = {int(g.usuario['id'])}" if es("estudiante") else ""


def paciente_o_404(pid):
    extra = ACTIVOS if es("estudiante") else ""  # el profesor puede abrir archivados para restaurarlos
    return q("SELECT p.* FROM pacientes p WHERE p.id = ?" + alcance() + extra, (pid,), uno=True) or abort(404)


def estudiantes():
    return q("SELECT id, nombre FROM usuarios WHERE rol = 'estudiante' AND activo = 1 ORDER BY nombre")


def salas_con_estado():
    return q("""SELECT s.*, (SELECT GROUP_CONCAT(DISTINCT r.tipo) FROM reportes r
                             WHERE r.sala_id = s.id AND r.estado != 'Resuelto') AS pendiente
                FROM salas s ORDER BY s.nombre""")


@app.before_request
def cargar_usuario():
    respaldo_diario()
    g.usuario = None
    if uid := session.get("uid"):
        g.usuario = q("SELECT * FROM usuarios WHERE id = ? AND activo = 1", (uid,), uno=True)
    if g.usuario is None and request.endpoint not in ("entrar", "static"):
        return redirect(url_for("entrar"))


@app.context_processor
def menu_y_avisos():
    if not g.get("usuario"):
        return {}
    contadores = {}
    if es("servicios"):
        contadores["avisos"] = q("SELECT COUNT(*) FROM reportes WHERE estado != 'Resuelto'", uno=True)[0]
    elif es("profesor"):
        contadores["inicio"] = q("SELECT (SELECT COUNT(*) FROM odonto_sesiones s JOIN pacientes p ON p.id = s.paciente_id "
                                 "WHERE s.estado = 'Pendiente'" + ACTIVOS + ") + (SELECT COUNT(*) FROM pacientes p "
                                 "WHERE COALESCE(p.aprobado, 0) = 0" + ACTIVOS + ")", uno=True)[0]
    else:
        contadores["inicio"] = q("SELECT COUNT(*) FROM odonto_sesiones s JOIN pacientes p ON p.id = s.paciente_id "
                                 "WHERE s.estado = 'Corregir'" + alcance() + ACTIVOS, uno=True)[0]
    return {"menu": MENUS[g.usuario["rol"]], "contadores": contadores}


@app.errorhandler(413)
def foto_muy_grande(_):
    flash("La foto es demasiado grande (máximo 15 MB).", "error")
    return redirect(request.referrer or url_for("inicio"))


# ---------- formato para las plantillas ----------
@app.template_filter("fecha")
def fecha_corta(iso):
    try:
        d = date.fromisoformat(iso)
    except (TypeError, ValueError):
        return iso or ""
    if d == hoy():
        return "Hoy"
    if d == hoy() + timedelta(1):
        return "Mañana"
    return f"{DIAS[d.weekday()][:3]} {d.day:02d}/{d.month:02d}/{d.year}"


@app.template_filter("fecha_larga")
def fecha_larga(iso):
    try:
        d = date.fromisoformat(iso)
    except (TypeError, ValueError):
        return iso or ""
    return f"{DIAS[d.weekday()]} {d.day} de {MESES[d.month - 1]}"


@app.template_filter("dinero")
def dinero(valor):
    return f"C$ {valor or 0:,.2f}"


@app.template_filter("edad")
def edad(nacimiento):
    try:
        n = date.fromisoformat(nacimiento)
    except (TypeError, ValueError):
        return ""
    h = hoy()
    return f"{h.year - n.year - ((h.month, h.day) < (n.month, n.day))} años"


@app.template_global()
def whatsapp(telefono, mensaje=""):
    num = re.sub(r"\D", "", telefono or "")
    if not num:
        return None
    if len(num) == 8:  # numero nicaraguense sin codigo de pais
        num = "505" + num
    return f"https://wa.me/{num}?text={quote(mensaje)}"


@app.template_global()
def recordatorio(cita):
    return whatsapp(cita["telefono"],
                    f"Hola {cita['nombre']}, le saludamos de la Clínica Odontológica UAM. "
                    f"Le recordamos su cita el {fecha_larga(cita['fecha'])} a las {cita['hora']}. "
                    "¿Nos confirma su asistencia?")


# ---------- acceso ----------
@app.route("/entrar", methods=["GET", "POST"])
def entrar():
    if request.method == "POST":
        u = q("SELECT * FROM usuarios WHERE usuario = ? AND activo = 1",
              (request.form.get("usuario", "").strip().lower(),), uno=True)
        if u and check_password_hash(u["clave"], request.form.get("clave", "")):
            session.clear()
            session.permanent = True
            session["uid"] = u["id"]
            anotar("Inicio de sesión", usuario_id=u["id"])
            return redirect(url_for("inicio"))
        anotar("Intento de acceso fallido", f"Usuario: {request.form.get('usuario', '')[:40]}")
        flash("Usuario o clave incorrectos.", "error")
    return render_template("entrar.html")


@app.route("/salir")
def salir():
    session.clear()
    return redirect(url_for("entrar"))


@app.route("/cuenta", methods=["GET", "POST"])
def cuenta():
    if request.method == "POST":
        f = request.form
        if not check_password_hash(g.usuario["clave"], f.get("actual", "")):
            flash("La clave actual no es correcta.", "error")
        elif len(f.get("nueva", "")) < 6:
            flash("La clave nueva debe tener al menos 6 caracteres.", "error")
        elif f["nueva"] != f.get("repetir"):
            flash("Las claves nuevas no coinciden.", "error")
        else:
            ejecutar("UPDATE usuarios SET clave = ? WHERE id = ?", (generate_password_hash(f["nueva"]), g.usuario["id"]))
            anotar("Cambió su clave")
            flash("Clave actualizada.", "ok")
        return redirect(url_for("cuenta"))
    return render_template("cuenta.html")


# ---------- inicio ----------
@app.route("/")
def inicio():
    if es("servicios"):
        return redirect(url_for("avisos"))
    d = hoy().isoformat()
    datos = {"hoy": d, "salas": salas_con_estado(),
             "citas_hoy": q(CITAS_SQL + alcance() + ACTIVOS + " AND c.fecha = ? ORDER BY c.hora", (d,))}
    if es("estudiante"):
        datos["por_recordar"] = q(CITAS_SQL + alcance() + ACTIVOS + " AND c.fecha > ? AND c.fecha <= ? AND c.estado = 'Pendiente'"
                                  " ORDER BY c.fecha, c.hora", (d, (hoy() + timedelta(3)).isoformat()))
        datos["sesiones"] = q(SESIONES_SQL + alcance() + ACTIVOS + " AND s.estado != 'Aprobado' ORDER BY s.fecha DESC")
    else:
        datos["por_aprobar"] = q("SELECT p.*, u.nombre AS estudiante_nombre FROM pacientes p "
                                 "LEFT JOIN usuarios u ON u.id = p.estudiante_id "
                                 "WHERE COALESCE(p.aprobado, 0) = 0" + ACTIVOS + " ORDER BY p.nombre")
        datos["sesiones"] = q(SESIONES_SQL + ACTIVOS + " AND s.estado = 'Pendiente' ORDER BY s.enviado")
    return render_template(f"inicio_{g.usuario['rol']}.html", **datos)


# ---------- pacientes ----------
@app.route("/pacientes")
@solo("estudiante", "profesor")
def pacientes():
    texto = request.args.get("q", "").strip()
    est = request.args.get("estudiante", type=int)
    archivados = es("profesor") and request.args.get("archivados") == "1"
    patron = f"%{texto}%"
    sql = ("SELECT p.*, u.nombre AS estudiante_nombre FROM pacientes p LEFT JOIN usuarios u ON u.id = p.estudiante_id "
           "WHERE (p.nombre LIKE ? OR p.cedula LIKE ? OR p.telefono LIKE ?)" + alcance() +
           " AND COALESCE(p.archivado, 0) = ?")
    args = [patron, patron, patron, int(archivados)]
    if est and es("profesor"):
        sql += " AND p.estudiante_id = ?"
        args.append(est)
    return render_template("pacientes.html", texto=texto, est=est, estudiantes=estudiantes(), archivados=archivados,
                           pacientes=q(sql + " ORDER BY p.nombre", args))


@app.route("/pacientes/nuevo", methods=["GET", "POST"])
@app.route("/pacientes/<int:pid>/editar", methods=["GET", "POST"])
@solo("estudiante", "profesor")
def paciente_form(pid=None):
    p = dict(paciente_o_404(pid)) if pid else {}
    if request.method == "POST":
        antes = p
        p = {c: request.form.get(c, "").strip() for c in CAMPOS_PACIENTE}
        p["estudiante_id"] = request.form.get("estudiante_id", type=int) if es("profesor") else g.usuario["id"]
        if not p["nombre"] or not p["cedula"]:
            flash("El nombre y la cédula son obligatorios.", "error")
        else:
            try:
                if pid:
                    ejecutar(f"UPDATE pacientes SET {', '.join(c + ' = ?' for c in p)} WHERE id = ?",
                             (*p.values(), pid))
                    cambios = [f"{c}: «{(antes.get(c) or '')[:60]}» → «{(v or '')[:60]}»" if c in CAMPOS_PACIENTE
                               else f"{c} cambiado" for c, v in p.items() if (antes.get(c) or "") != (v or "")]
                    if cambios:
                        anotar("Modificó datos del paciente", "; ".join(cambios), pid)
                    flash("Cambios guardados.", "ok")
                else:
                    pid = ejecutar(f"INSERT INTO pacientes({', '.join(p)}) VALUES ({', '.join('?' * len(p))})",
                                   tuple(p.values()))
                    anotar("Registró paciente", f"{p['nombre']} ({p['cedula']})", pid)
                    flash("Paciente registrado.", "ok")
                return redirect(url_for("expediente", pid=pid))
            except sqlite3.IntegrityError:
                flash("Ya existe un paciente con esa cédula.", "error")
    return render_template("paciente_form.html", p=p, pid=pid, estudiantes=estudiantes())


@app.route("/pacientes/<int:pid>")
@solo("estudiante", "profesor")
def expediente(pid):
    p = paciente_o_404(pid)
    abierta = q(SESIONES_SQL + " AND s.paciente_id = ? AND s.estado IN ('Abierta', 'Corregir')", (pid,), uno=True)
    return render_template(
        "expediente.html", p=p,
        estudiante=q("SELECT nombre FROM usuarios WHERE id = ?", (p["estudiante_id"],), uno=True),
        dientes={d: e for d, e in q("SELECT diente, estado FROM odontograma WHERE paciente_id = ?", (pid,))},
        sesiones=q(SESIONES_SQL + " AND s.paciente_id = ? ORDER BY s.id DESC", (pid,)),
        abierta=abierta,
        marcados=[r["diente"] for r in q("SELECT diente FROM odonto_registros WHERE sesion_id = ?",
                                         (abierta["id"],))] if abierta else [],
        citas=q(CITAS_SQL + " AND c.paciente_id = ? ORDER BY c.fecha DESC, c.hora DESC", (pid,)),
        tratamientos=q("SELECT * FROM tratamientos WHERE paciente_id = ? ORDER BY id DESC", (pid,)),
        tarifario=q("SELECT * FROM tarifario ORDER BY procedimiento"),
        historial=q(BITACORA_SQL + " WHERE b.paciente_id = ? ORDER BY b.id DESC", (pid,)) if es("profesor") else [],
        archivo=q(BITACORA_SQL + " WHERE b.paciente_id = ? AND b.accion = 'Archivó paciente' ORDER BY b.id DESC",
                  (pid,), uno=True) if p["archivado"] else None)


@app.post("/pacientes/<int:pid>/archivo")
@solo("profesor")
def paciente_archivar(pid):
    """Los expedientes no se borran: se archivan (y se pueden restaurar)."""
    p = paciente_o_404(pid)
    if request.form.get("restaurar"):
        ejecutar("UPDATE pacientes SET archivado = 0 WHERE id = ?", (pid,))
        anotar("Restauró paciente", "", pid)
        flash("Paciente restaurado.", "ok")
        return redirect(url_for("expediente", pid=pid))
    motivo = request.form.get("motivo", "").strip()
    if not motivo:
        flash("Indique el motivo para archivar al paciente.", "error")
        return redirect(url_for("expediente", pid=pid))
    ejecutar("UPDATE pacientes SET archivado = 1 WHERE id = ?", (pid,))
    anotar("Archivó paciente", motivo, pid)
    flash(f"{p['nombre']} fue archivado. Su expediente se conserva y puede restaurarse.", "ok")
    return redirect(url_for("pacientes"))


def sesion_o_404(sid):
    """Sesion de odontograma de un paciente al que el usuario tiene acceso."""
    return q("SELECT s.* FROM odonto_sesiones s JOIN pacientes p ON p.id = s.paciente_id WHERE s.id = ?" + alcance(),
             (sid,), uno=True) or abort(404)


@app.post("/pacientes/<int:pid>/sesiones")
@solo("estudiante", "profesor")
def sesion_nueva(pid):
    """Paso 1: sin la foto del odontograma presencial no se puede llenar el digital."""
    paciente_o_404(pid)
    if q("SELECT 1 FROM odonto_sesiones WHERE paciente_id = ? AND estado IN ('Abierta', 'Corregir')", (pid,), uno=True):
        flash("Ya hay un odontograma en curso para este paciente. Termínelo y envíelo a revisión.", "error")
    elif not (foto := guardar_foto(request.files.get("foto"))):
        flash("Suba la foto del odontograma presencial (JPG o PNG) para poder llenar el digital.", "error")
    else:
        sid = ejecutar("INSERT INTO odonto_sesiones(paciente_id, foto, nota, fecha, usuario_id) VALUES (?, ?, ?, ?, ?)",
                       (pid, foto, request.form.get("nota", "").strip(), ahora().strftime("%Y-%m-%d %H:%M"),
                        g.usuario["id"]))
        anotar("Subió foto del odontograma presencial", f"Sesión {sid}", pid)
        flash("Foto guardada. Ahora llene el odontograma digital y envíelo a revisión.", "ok")
    return volver(pid, "odontograma")


@app.post("/sesiones/<int:sid>/diente")
@solo("estudiante", "profesor")
def sesion_diente(sid):
    """Paso 2: marcar dientes en el odontograma digital de una sesion con foto."""
    s = sesion_o_404(sid)
    datos = request.get_json(silent=True) or {}
    diente, estado = datos.get("diente"), datos.get("estado")
    if s["estado"] not in EDITABLES:
        return jsonify(error="Este odontograma ya fue enviado a revisión y no se puede modificar."), 409
    if estado not in ESTADOS_DIENTE or diente not in SUPERIOR + INFERIOR:
        abort(400)
    ejecutar("DELETE FROM odonto_registros WHERE sesion_id = ? AND diente = ?", (sid, diente))
    ejecutar("INSERT INTO odonto_registros(paciente_id, diente, estado, foto, fecha, usuario_id, sesion_id) "
             "VALUES (?, ?, ?, ?, ?, ?, ?)",
             (s["paciente_id"], diente, estado, s["foto"], ahora().strftime("%Y-%m-%d %H:%M"), g.usuario["id"], sid))
    ejecutar("INSERT OR REPLACE INTO odontograma VALUES (?, ?, ?)", (s["paciente_id"], diente, estado))
    anotar("Marcó diente en el odontograma digital", f"Sesión {sid}. Diente {diente}: {estado}", s["paciente_id"])
    return jsonify(ok=True)


@app.post("/sesiones/<int:sid>/foto")
@solo("estudiante", "profesor")
def sesion_foto(sid):
    s = sesion_o_404(sid)
    if s["estado"] not in EDITABLES:
        flash("Este odontograma ya fue enviado a revisión.", "error")
    elif not (foto := guardar_foto(request.files.get("foto"))):
        flash("El archivo no es una imagen válida (JPG o PNG).", "error")
    else:
        ejecutar("UPDATE odonto_sesiones SET foto = ? WHERE id = ?", (foto, sid))
        ejecutar("UPDATE odonto_registros SET foto = ? WHERE sesion_id = ?", (foto, sid))
        anotar("Cambió la foto del odontograma presencial", f"Sesión {sid}. Foto anterior: {s['foto']}", s["paciente_id"])
        flash("Foto reemplazada.", "ok")
    return volver(s["paciente_id"], "odontograma")


@app.post("/sesiones/<int:sid>/enviar")
@solo("estudiante", "profesor")
def sesion_enviar(sid):
    """Paso 3: el odontograma queda bloqueado hasta que el docente lo revise."""
    s = sesion_o_404(sid)
    if s["estado"] in EDITABLES:
        ejecutar("UPDATE odonto_sesiones SET estado = 'Pendiente', enviado = ? WHERE id = ?",
                 (ahora().strftime("%Y-%m-%d %H:%M"), sid))
        anotar("Envió odontograma a revisión", f"Sesión {sid}", s["paciente_id"])
        flash("Odontograma enviado al docente para su revisión.", "ok")
    return volver(s["paciente_id"], "odontograma")


@app.route("/sesiones/<int:sid>")
@solo("estudiante", "profesor")
def sesion_ver(sid):
    """Foto presencial junto al odontograma digital: pantalla de revision del docente."""
    s = q(SESIONES_SQL + " AND s.id = ?" + alcance(), (sid,), uno=True) or abort(404)
    return render_template(
        "sesion.html", s=s,
        dientes={d: e for d, e in q("SELECT diente, estado FROM odontograma WHERE paciente_id = ?", (s["paciente_id"],))},
        registros=q("SELECT * FROM odonto_registros WHERE sesion_id = ? ORDER BY diente", (sid,)))


@app.post("/sesiones/<int:sid>/revision")
@solo("profesor")
def sesion_revision(sid):
    s = sesion_o_404(sid)
    revision = request.form.get("revision")
    observacion = request.form.get("observacion", "").strip()
    if s["estado"] not in ("Pendiente", "Aprobado"):
        flash("Solo se revisan odontogramas enviados por el estudiante.", "error")
    elif revision == "Corregir" and not observacion:
        flash("Escriba qué debe corregir el estudiante.", "error")
    elif revision in ("Aprobado", "Corregir"):
        ejecutar("UPDATE odonto_sesiones SET estado = ?, observacion = ?, revisado_por = ?, revisado = ? WHERE id = ?",
                 (revision, observacion, g.usuario["id"], ahora().strftime("%Y-%m-%d %H:%M"), sid))
        anotar(f"Revisó odontograma: {revision}", f"Sesión {sid}. {observacion}".strip(), s["paciente_id"])
        flash("Revisión guardada.", "ok")
    return regresar(url_for("sesion_ver", sid=sid))


@app.route("/fotos/<nombre>")
@solo("estudiante", "profesor")
def foto(nombre):
    # El docente tiene acceso a todas las fotos; el estudiante, solo a las de sus pacientes
    if es("estudiante"):
        q("SELECT s.id FROM odonto_sesiones s JOIN pacientes p ON p.id = s.paciente_id WHERE s.foto = ?" + alcance(),
          (nombre,), uno=True) or abort(404)
    return send_from_directory(FOTOS, nombre)


@app.post("/pacientes/<int:pid>/firma")
@solo("estudiante", "profesor")
def firmar(pid):
    paciente_o_404(pid)
    firma = request.form.get("firma", "")
    if firma.startswith("data:image/png;base64,"):
        ejecutar("UPDATE pacientes SET firma = ?, firma_fecha = ? WHERE id = ?", (firma, hoy().isoformat(), pid))
        anotar("Registró firma del consentimiento", "", pid)
        flash("Consentimiento firmado y guardado.", "ok")
    else:
        flash("Falta la firma del paciente.", "error")
    return volver(pid, "consentimiento")


@app.post("/pacientes/<int:pid>/aprobacion")
@solo("profesor")
def aprobar(pid):
    aprobado = 1 if request.form.get("aprobado") == "1" else 0
    ejecutar("UPDATE pacientes SET aprobado = ?, docente = ? WHERE id = ?",
             (aprobado, g.usuario["nombre"] if aprobado else None, pid))
    anotar("Aprobó paciente" if aprobado else "Retiró aprobación del paciente", "", pid)
    flash("Paciente aprobado." if aprobado else "Aprobación retirada.", "ok")
    return regresar(url_for("expediente", pid=pid))


# ---------- tratamientos ----------
@app.post("/pacientes/<int:pid>/tratamientos")
@solo("estudiante", "profesor")
def tratamiento_nuevo(pid):
    paciente_o_404(pid)
    f = request.form
    if f.get("procedimiento", "").strip():
        ejecutar("INSERT INTO tratamientos(paciente_id, procedimiento, diente, costo, fecha) VALUES (?, ?, ?, ?, ?)",
                 (pid, f["procedimiento"].strip(), f.get("diente", "").strip(), numero(f.get("costo")),
                  hoy().isoformat()))
        anotar("Agregó tratamiento", f"{f['procedimiento'].strip()} ({dinero(numero(f.get('costo')))})", pid)
        flash("Tratamiento agregado.", "ok")
    return volver(pid, "tratamientos")


@app.post("/tratamientos/<int:tid>")
@solo("estudiante", "profesor")
def tratamiento_actualizar(tid):
    t = q("SELECT * FROM tratamientos WHERE id = ?", (tid,), uno=True) or abort(404)
    paciente_o_404(t["paciente_id"])
    f = request.form
    if f.get("eliminar"):
        if t["pagado"] > 0 and not es("profesor"):
            flash("Este tratamiento tiene pagos registrados; solo un profesor puede eliminarlo.", "error")
        else:
            ejecutar("DELETE FROM tratamientos WHERE id = ?", (tid,))
            anotar("Eliminó tratamiento", f"{t['procedimiento']} (costo {dinero(t['costo'])}, pagado {dinero(t['pagado'])})",
                   t["paciente_id"])
    elif f.get("abono"):
        monto = min(numero(f["abono"]), t["costo"] - t["pagado"])
        ejecutar("UPDATE tratamientos SET pagado = pagado + ? WHERE id = ?", (monto, tid))
        anotar("Registró pago", f"{t['procedimiento']}: {dinero(monto)}", t["paciente_id"])
        flash("Pago registrado.", "ok")
    elif f.get("estado") in ("Pendiente", "Realizado"):
        ejecutar("UPDATE tratamientos SET estado = ? WHERE id = ?", (f["estado"], tid))
        anotar(f"Marcó tratamiento como {f['estado'].lower()}", t["procedimiento"], t["paciente_id"])
    return volver(t["paciente_id"], "tratamientos")


@app.route("/tarifario", methods=["GET", "POST"])
@solo("profesor")
def tarifario():
    if request.method == "POST" and request.form.get("procedimiento", "").strip():
        ejecutar("INSERT INTO tarifario(procedimiento, precio) VALUES (?, ?) "
                 "ON CONFLICT(procedimiento) DO UPDATE SET precio = excluded.precio",
                 (request.form["procedimiento"].strip(), numero(request.form.get("precio"))))
        anotar("Actualizó tarifario", f"{request.form['procedimiento'].strip()}: {dinero(numero(request.form.get('precio')))}")
        flash("Tarifario actualizado.", "ok")
        return redirect(url_for("tarifario"))
    return render_template("tarifario.html", tarifario=q("SELECT * FROM tarifario ORDER BY procedimiento"))


@app.post("/tarifario/<int:tid>/eliminar")
@solo("profesor")
def tarifario_eliminar(tid):
    t = q("SELECT * FROM tarifario WHERE id = ?", (tid,), uno=True) or abort(404)
    ejecutar("DELETE FROM tarifario WHERE id = ?", (tid,))
    anotar("Quitó del tarifario", t["procedimiento"])
    return redirect(url_for("tarifario"))


# ---------- citas ----------
@app.route("/citas", methods=["GET", "POST"])
@solo("estudiante", "profesor")
def citas():
    if request.method == "POST":
        f = {k: request.form.get(k, "").strip() for k in ("paciente_id", "fecha", "hora", "sala_id", "motivo")}
        p = q("SELECT p.* FROM pacientes p WHERE p.id = ?" + alcance() + ACTIVOS, (f["paciente_id"],), uno=True)
        activas = " AND c.estado NOT IN ('Cancelada', 'No asistió')"
        if not (p and f["fecha"] and f["hora"]):
            flash("Elige paciente, fecha y hora.", "error")
        elif f["fecha"] < hoy().isoformat():
            flash("No se pueden agendar citas en fechas pasadas.", "error")
        elif q("SELECT 1 FROM citas c WHERE c.paciente_id = ? AND c.fecha = ?" + activas,
               (p["id"], f["fecha"]), uno=True):
            flash("Este paciente ya tiene una cita ese día.", "error")
        elif p["estudiante_id"] and q("SELECT 1 FROM citas c JOIN pacientes p ON p.id = c.paciente_id "
                                      "WHERE p.estudiante_id = ? AND c.fecha = ? AND c.hora = ?" + activas,
                                      (p["estudiante_id"], f["fecha"], f["hora"]), uno=True):
            flash("El estudiante ya tiene otra cita a esa hora.", "error")
        elif f["sala_id"] and q("SELECT 1 FROM citas c WHERE c.sala_id = ? AND c.fecha = ? AND c.hora = ?" + activas,
                                (f["sala_id"], f["fecha"], f["hora"]), uno=True):
            flash("Esa sala ya está ocupada a esa hora.", "error")
        else:
            ejecutar("INSERT INTO citas(paciente_id, fecha, hora, motivo, sala_id) VALUES (?, ?, ?, ?, ?)",
                     (p["id"], f["fecha"], f["hora"], f["motivo"], f["sala_id"] or None))
            anotar("Agendó cita", f"{f['fecha']} {f['hora']} {f['motivo']}".strip(), p["id"])
            flash("Cita agendada.", "ok")
            if f["sala_id"] and (s := q("SELECT GROUP_CONCAT(DISTINCT tipo) FROM reportes WHERE sala_id = ? "
                                        "AND estado != 'Resuelto'", (f["sala_id"],), uno=True)[0]):
                flash(f"Atención: la sala tiene un reporte pendiente ({s.lower()}).", "aviso")
            return redirect(url_for("citas"))
        return redirect(url_for("citas", paciente=f["paciente_id"]))

    ver = request.args.get("ver", "proximas")
    d = hoy().isoformat()
    filas = q(CITAS_SQL + alcance() + ACTIVOS + (" AND c.fecha >= ? ORDER BY c.fecha, c.hora" if ver == "proximas"
                                       else " AND c.fecha < ? ORDER BY c.fecha DESC, c.hora DESC"), (d,))
    return render_template("citas.html", citas=filas, ver=ver, hoy=d, salas=salas_con_estado(),
                           pacientes=q("SELECT p.id, p.nombre, p.cedula FROM pacientes p WHERE 1 = 1" + alcance() + ACTIVOS +
                                       " ORDER BY p.nombre"),
                           elegido=request.args.get("paciente", type=int))


@app.post("/citas/<int:cid>/estado")
@solo("estudiante", "profesor")
def cita_estado(cid):
    c = q("SELECT c.* FROM citas c JOIN pacientes p ON p.id = c.paciente_id WHERE c.id = ?" + alcance(),
          (cid,), uno=True) or abort(404)
    if request.form.get("estado") in ESTADOS_CITA:
        ejecutar("UPDATE citas SET estado = ? WHERE id = ?", (request.form["estado"], cid))
        anotar(f"Cambió cita a «{request.form['estado']}»", f"{c['fecha']} {c['hora']}", c["paciente_id"])
    return regresar(url_for("citas"))


# ---------- salas y avisos a servicios ----------
@app.route("/salas", methods=["GET", "POST"])
def salas():
    if request.method == "POST":
        f = request.form
        if f.get("tipo") in TIPOS_REPORTE and q("SELECT 1 FROM salas WHERE id = ?", (f.get("sala_id"),), uno=True):
            ejecutar("INSERT INTO reportes(sala_id, tipo, descripcion, reportado_por, fecha) VALUES (?, ?, ?, ?, ?)",
                     (f["sala_id"], f["tipo"], f.get("descripcion", "").strip(), g.usuario["id"],
                      ahora().strftime("%Y-%m-%d %H:%M")))
            sala = q("SELECT nombre FROM salas WHERE id = ?", (f["sala_id"],), uno=True)["nombre"]
            anotar("Reportó sala", f"{sala}: {f['tipo']}. {f.get('descripcion', '').strip()}".strip())
            flash("Reporte enviado. Servicios ya recibió el aviso.", "ok")
        else:
            flash("Elige la sala y el tipo de problema.", "error")
        return redirect(url_for("salas"))
    return render_template("salas.html", salas=salas_con_estado(), elegida=request.args.get("sala", type=int),
                           reportes=q(REPORTES_SQL + " ORDER BY r.estado = 'Resuelto', r.fecha DESC LIMIT 40"))


@app.post("/salas/nueva")
@solo("servicios", "profesor")
def sala_nueva():
    nombre = request.form.get("nombre", "").strip()
    if nombre:
        try:
            ejecutar("INSERT INTO salas(nombre) VALUES (?)", (nombre,))
            anotar("Agregó sala", nombre)
            flash("Sala agregada.", "ok")
        except sqlite3.IntegrityError:
            flash("Ya existe una sala con ese nombre.", "error")
    return redirect(url_for("salas"))


@app.post("/salas/<int:sid>/eliminar")
@solo("servicios", "profesor")
def sala_eliminar(sid):
    s = q("SELECT * FROM salas WHERE id = ?", (sid,), uno=True) or abort(404)
    anotar("Eliminó sala", s["nombre"])
    ejecutar("UPDATE citas SET sala_id = NULL WHERE sala_id = ?", (sid,))
    ejecutar("DELETE FROM salas WHERE id = ?", (sid,))
    flash("Sala eliminada.", "ok")
    return redirect(url_for("salas"))


@app.route("/avisos")
@solo("servicios")
def avisos():
    return render_template(
        "avisos.html",
        abiertos=q(REPORTES_SQL + " WHERE r.estado != 'Resuelto' ORDER BY r.estado = 'En proceso', r.fecha"),
        resueltos=q(REPORTES_SQL + " WHERE r.estado = 'Resuelto' ORDER BY r.actualizado DESC LIMIT 20"))


@app.post("/reportes/<int:rid>")
@solo("servicios")
def reporte_estado(rid):
    if request.form.get("estado") in ("En proceso", "Resuelto"):
        ejecutar("UPDATE reportes SET estado = ?, atendido_por = ?, actualizado = ? WHERE id = ?",
                 (request.form["estado"], g.usuario["id"], ahora().strftime("%Y-%m-%d %H:%M"), rid))
        r = q(REPORTES_SQL + " WHERE r.id = ?", (rid,), uno=True)
        anotar(f"Marcó reporte como «{request.form['estado']}»", f"{r['sala']}: {r['tipo']}")
        flash("Reporte actualizado.", "ok")
    return redirect(url_for("avisos"))


# ---------- inventario ----------
@app.route("/inventario", methods=["GET", "POST"])
@solo("servicios", "profesor")
def inventario():
    if request.method == "POST" and request.form.get("material", "").strip():
        f = request.form
        ejecutar("INSERT INTO inventario(material, unidad, cantidad, minimo) VALUES (?, ?, ?, ?) "
                 "ON CONFLICT(material) DO UPDATE SET unidad = excluded.unidad, cantidad = excluded.cantidad, "
                 "minimo = excluded.minimo",
                 (f["material"].strip(), f.get("unidad", "").strip(), int(numero(f.get("cantidad"))),
                  int(numero(f.get("minimo")))))
        anotar("Actualizó inventario", f"{f['material'].strip()}: {int(numero(f.get('cantidad')))} {f.get('unidad', '').strip()}")
        flash("Material guardado.", "ok")
        return redirect(url_for("inventario"))
    return render_template("inventario.html", materiales=q(
        "SELECT * FROM inventario ORDER BY cantidad > minimo, material"))


@app.post("/inventario/<int:iid>/ajustar")
@solo("servicios", "profesor")
def inventario_ajustar(iid):
    m = q("SELECT * FROM inventario WHERE id = ?", (iid,), uno=True) or abort(404)
    if request.form.get("eliminar"):
        ejecutar("DELETE FROM inventario WHERE id = ?", (iid,))
        anotar("Eliminó material", m["material"])
    else:
        delta = request.form.get("delta", 0, type=int)
        ejecutar("UPDATE inventario SET cantidad = MAX(0, cantidad + ?) WHERE id = ?", (delta, iid))
        anotar("Ajustó inventario", f"{m['material']}: {delta:+d}")
    return redirect(url_for("inventario"))


# ---------- usuarios (profesor) ----------
@app.route("/usuarios", methods=["GET", "POST"])
@solo("profesor")
def usuarios():
    if request.method == "POST":
        f = {k: request.form.get(k, "").strip() for k in ("usuario", "nombre", "rol", "clave")}
        f["usuario"] = f["usuario"].lower()
        if not re.fullmatch(r"[a-z0-9._-]{3,30}", f["usuario"]):
            flash("El usuario debe tener de 3 a 30 letras o números, sin espacios ni tildes.", "error")
        elif not f["nombre"] or f["rol"] not in ROLES:
            flash("Completa el nombre y el rol.", "error")
        elif len(f["clave"]) < 6:
            flash("La clave debe tener al menos 6 caracteres.", "error")
        else:
            try:
                ejecutar("INSERT INTO usuarios(usuario, nombre, rol, clave) VALUES (?, ?, ?, ?)",
                         (f["usuario"], f["nombre"], f["rol"], generate_password_hash(f["clave"])))
                anotar("Creó usuario", f"{f['usuario']} ({ROLES[f['rol']]})")
                flash(f"Usuario {f['usuario']} creado.", "ok")
            except sqlite3.IntegrityError:
                flash("Ese nombre de usuario ya existe.", "error")
        return redirect(url_for("usuarios"))
    return render_template("usuarios.html", usuarios=q(
        "SELECT u.*, (SELECT COUNT(*) FROM pacientes p WHERE p.estudiante_id = u.id) AS pacientes "
        "FROM usuarios u ORDER BY u.activo DESC, u.rol, u.nombre"))


@app.post("/usuarios/<int:uid>")
@solo("profesor")
def usuario_actualizar(uid):
    u = q("SELECT * FROM usuarios WHERE id = ?", (uid,), uno=True) or abort(404)
    if uid == g.usuario["id"]:
        flash("No puedes modificar tu propia cuenta desde aquí.", "error")
    elif request.form.get("activo") in ("0", "1"):
        ejecutar("UPDATE usuarios SET activo = ? WHERE id = ?", (int(request.form["activo"]), uid))
        anotar("Activó usuario" if request.form["activo"] == "1" else "Desactivó usuario", u["usuario"])
        flash("Usuario actualizado.", "ok")
    elif len(request.form.get("clave", "")) >= 6:
        ejecutar("UPDATE usuarios SET clave = ? WHERE id = ?", (generate_password_hash(request.form["clave"]), uid))
        anotar("Restableció clave", u["usuario"])
        flash("Clave restablecida.", "ok")
    else:
        flash("La clave debe tener al menos 6 caracteres.", "error")
    return redirect(url_for("usuarios"))


# ---------- bitacora y copias de seguridad (profesor) ----------
@app.route("/bitacora")
@solo("profesor")
def bitacora():
    texto = request.args.get("q", "").strip()
    usuario = request.args.get("usuario", type=int)
    sql, args = BITACORA_SQL + " WHERE (b.accion LIKE ? OR b.detalle LIKE ? OR p.nombre LIKE ?)", [f"%{texto}%"] * 3
    if usuario:
        sql += " AND b.usuario_id = ?"
        args.append(usuario)
    return render_template("bitacora.html", texto=texto, usuario=usuario,
                           registros=q(sql + " ORDER BY b.id DESC LIMIT 300", args),
                           usuarios=q("SELECT id, nombre FROM usuarios ORDER BY nombre"),
                           respaldos=sorted((p.name for p in RESPALDOS.glob("dientecito-*.db")), reverse=True))


@app.route("/respaldo")
@solo("profesor")
def descargar_respaldo():
    """Descarga un .zip con la base de datos y todas las fotos, para guardarlo fuera del servidor."""
    carpeta = Path(tempfile.mkdtemp())
    copiar_db(carpeta / "dientecito.db")
    nombre = f"respaldo-dientecito-{ahora():%Y-%m-%d-%H%M}.zip"
    with zipfile.ZipFile(carpeta / nombre, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(carpeta / "dientecito.db", "dientecito.db")
        for foto in sorted(FOTOS.glob("*")) if FOTOS.exists() else []:
            z.write(foto, f"fotos/{foto.name}", compress_type=zipfile.ZIP_STORED)  # ya vienen comprimidas
    anotar("Descargó copia de seguridad")
    respuesta = send_file(carpeta / nombre, as_attachment=True, download_name=nombre)
    respuesta.call_on_close(lambda: shutil.rmtree(carpeta, ignore_errors=True))
    return respuesta


iniciar_db()

if __name__ == "__main__":
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except OSError:
        ip = "127.0.0.1"
    finally:
        s.close()
    print("\n  Dientecito Feliz")
    print("  En esta computadora:            http://localhost:5000")
    print(f"  En el telefono (misma Wi-Fi):   http://{ip}:5000")
    print(f"  Usuarios de ejemplo: profesor, estudiante, servicios (clave: {CLAVE_INICIAL})\n")
    app.run(host="0.0.0.0", port=5000)
