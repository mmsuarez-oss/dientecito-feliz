"""Dientecito Feliz - Clinica Odontologica UAM
Aplicacion web (Flask + SQLite) para usar desde computadora y telefono (Android / iOS).

Ejecutar:   python app.py
Luego abrir la direccion que aparece en consola (el telefono debe estar en la misma red Wi-Fi).
"""
import os
import re
import secrets
import socket
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import quote

from flask import (Flask, abort, flash, g, jsonify, redirect, render_template,
                   request, session, url_for)

DB = Path(__file__).with_name("dientecito.db")
CLAVE = os.environ.get("DIENTECITO_CLAVE", "uam2026")  # clave de acceso de la clinica
DEMO = bool(os.environ.get("DIENTECITO_DEMO"))  # servidor publico de prueba: muestra aviso de datos ficticios

ESTADOS_DIENTE = {"Sano": "#ffffff", "Caries": "#ef5350", "Obturado": "#42a5f5",
                  "Corona": "#ffca28", "Endodoncia": "#ab47bc", "Extraido": "#90a4ae"}
ESTADOS_CITA = ["Pendiente", "Confirmada", "Atendida", "No asistió", "Cancelada"]
# Numeracion FDI por cuadrantes: 1 y 2 arriba, 4 y 3 abajo
SUPERIOR = [18, 17, 16, 15, 14, 13, 12, 11, 21, 22, 23, 24, 25, 26, 27, 28]
INFERIOR = [48, 47, 46, 45, 44, 43, 42, 41, 31, 32, 33, 34, 35, 36, 37, 38]
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

ESQUEMA = """
CREATE TABLE IF NOT EXISTS pacientes(
    id INTEGER PRIMARY KEY, nombre TEXT NOT NULL, cedula TEXT UNIQUE NOT NULL,
    telefono TEXT, nacimiento TEXT, alergias TEXT);
CREATE TABLE IF NOT EXISTS citas(
    id INTEGER PRIMARY KEY,
    paciente_id INTEGER NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,
    fecha TEXT NOT NULL, hora TEXT NOT NULL, motivo TEXT, estudiante TEXT);
CREATE TABLE IF NOT EXISTS odontograma(
    paciente_id INTEGER REFERENCES pacientes(id) ON DELETE CASCADE,
    diente INTEGER, estado TEXT, PRIMARY KEY(paciente_id, diente));
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
"""
# Columnas agregadas despues de la primera muestra; se anaden a bases ya existentes
COLUMNAS_NUEVAS = {
    "pacientes": ["sexo TEXT", "direccion TEXT", "contacto_emergencia TEXT", "motivo_consulta TEXT",
                  "antecedentes TEXT", "medicamentos TEXT", "examen_clinico TEXT", "plan TEXT",
                  "docente TEXT", "aprobado INTEGER DEFAULT 0", "firma TEXT", "firma_fecha TEXT"],
    "citas": ["estado TEXT DEFAULT 'Pendiente'"],
}
CAMPOS_PACIENTE = ["nombre", "cedula", "telefono", "nacimiento", "sexo", "direccion",
                   "contacto_emergencia", "alergias", "motivo_consulta", "antecedentes",
                   "medicamentos", "examen_clinico", "plan"]
CITAS_SQL = "SELECT c.*, p.nombre, p.telefono FROM citas c JOIN pacientes p ON p.id = c.paciente_id"

app = Flask(__name__)
app.secret_key = os.environ.get("DIENTECITO_SECRETO") or secrets.token_hex(16)
app.jinja_env.globals.update(ESTADOS_DIENTE=ESTADOS_DIENTE, ESTADOS_CITA=ESTADOS_CITA,
                             SUPERIOR=SUPERIOR, INFERIOR=INFERIOR, DEMO=DEMO)


# ---------- base de datos ----------
def iniciar_db():
    con = sqlite3.connect(DB)
    con.executescript(ESQUEMA)
    for tabla, columnas in COLUMNAS_NUEVAS.items():
        existentes = {fila[1] for fila in con.execute(f"PRAGMA table_info({tabla})")}
        for col in columnas:
            if col.split()[0] not in existentes:
                con.execute(f"ALTER TABLE {tabla} ADD COLUMN {col}")
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


def numero(texto):
    try:
        return max(0.0, float(str(texto).replace(",", ".")))
    except ValueError:
        return 0.0


def volver(pid, seccion):
    return redirect(url_for("expediente", pid=pid, _anchor=seccion))


# ---------- formato para las plantillas ----------
@app.template_filter("fecha")
def fecha_corta(iso):
    try:
        d = date.fromisoformat(iso)
    except (TypeError, ValueError):
        return iso or ""
    hoy = date.today()
    if d == hoy:
        return "Hoy"
    if d == hoy + timedelta(1):
        return "Mañana"
    return f"{DIAS[d.weekday()][:3]} {d.day} {MESES[d.month - 1][:3]}"


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
    hoy = date.today()
    return f"{hoy.year - n.year - ((hoy.month, hoy.day) < (n.month, n.day))} años"


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
                    "¿Nos confirma su asistencia? 🦷")


# ---------- acceso ----------
@app.before_request
def pedir_clave():
    if not session.get("ok") and request.endpoint not in ("entrar", "static"):
        return redirect(url_for("entrar"))


@app.route("/entrar", methods=["GET", "POST"])
def entrar():
    if request.method == "POST":
        if secrets.compare_digest(request.form.get("clave", ""), CLAVE):
            session.permanent = True
            session["ok"] = True
            return redirect(url_for("inicio"))
        flash("Clave incorrecta.", "error")
    return render_template("entrar.html")


@app.route("/salir")
def salir():
    session.clear()
    return redirect(url_for("entrar"))


# ---------- inicio ----------
@app.route("/")
def inicio():
    hoy = date.today()
    hora = datetime.now().hour
    return render_template(
        "inicio.html",
        saludo="Buenos días" if hora < 12 else "Buenas tardes" if hora < 19 else "Buenas noches",
        hoy=hoy.isoformat(),
        citas_hoy=q(CITAS_SQL + " WHERE c.fecha = ? ORDER BY c.hora", (hoy.isoformat(),)),
        por_recordar=q(CITAS_SQL + " WHERE c.fecha > ? AND c.fecha <= ? AND c.estado = 'Pendiente'"
                       " ORDER BY c.fecha, c.hora", (hoy.isoformat(), (hoy + timedelta(3)).isoformat())),
        stock_bajo=q("SELECT * FROM inventario WHERE cantidad <= minimo ORDER BY material"),
        stats=q("""SELECT (SELECT COUNT(*) FROM pacientes) AS pacientes,
                          (SELECT COUNT(*) FROM citas WHERE fecha >= ? AND estado != 'Cancelada') AS proximas,
                          (SELECT ROUND(100.0 * SUM(estado = 'Atendida') /
                                  NULLIF(SUM(estado IN ('Atendida', 'No asistió')), 0)) FROM citas) AS asistencia,
                          (SELECT COALESCE(SUM(costo - pagado), 0) FROM tratamientos) AS saldo""",
                (hoy.isoformat(),), uno=True))


# ---------- pacientes ----------
@app.route("/pacientes")
def pacientes():
    texto = request.args.get("q", "").strip()
    patron = f"%{texto}%"
    return render_template("pacientes.html", texto=texto, pacientes=q(
        "SELECT * FROM pacientes WHERE nombre LIKE ? OR cedula LIKE ? OR telefono LIKE ? ORDER BY nombre",
        (patron, patron, patron)))


def paciente_o_404(pid):
    return q("SELECT * FROM pacientes WHERE id = ?", (pid,), uno=True) or abort(404)


@app.route("/pacientes/nuevo", methods=["GET", "POST"])
@app.route("/pacientes/<int:pid>/editar", methods=["GET", "POST"])
def paciente_form(pid=None):
    p = dict(paciente_o_404(pid)) if pid else {}
    if request.method == "POST":
        p = {c: request.form.get(c, "").strip() for c in CAMPOS_PACIENTE}
        if not p["nombre"] or not p["cedula"]:
            flash("El nombre y la cédula son obligatorios.", "error")
        else:
            try:
                if pid:
                    ejecutar(f"UPDATE pacientes SET {', '.join(c + ' = ?' for c in p)} WHERE id = ?",
                             (*p.values(), pid))
                    flash("Cambios guardados.", "ok")
                else:
                    pid = ejecutar(f"INSERT INTO pacientes({', '.join(p)}) VALUES ({', '.join('?' * len(p))})",
                                   tuple(p.values()))
                    flash("Paciente registrado. Ya puedes llenar su odontograma y consentimiento.", "ok")
                return redirect(url_for("expediente", pid=pid))
            except sqlite3.IntegrityError:
                flash("Ya existe un paciente con esa cédula.", "error")
    return render_template("paciente_form.html", p=p, pid=pid)


@app.route("/pacientes/<int:pid>")
def expediente(pid):
    return render_template(
        "expediente.html", p=paciente_o_404(pid),
        dientes={d: e for d, e in q("SELECT diente, estado FROM odontograma WHERE paciente_id = ?", (pid,))},
        citas=q(CITAS_SQL + " WHERE c.paciente_id = ? ORDER BY c.fecha DESC, c.hora DESC", (pid,)),
        tratamientos=q("SELECT * FROM tratamientos WHERE paciente_id = ? ORDER BY id DESC", (pid,)),
        tarifario=q("SELECT * FROM tarifario ORDER BY procedimiento"))


@app.post("/pacientes/<int:pid>/eliminar")
def paciente_eliminar(pid):
    ejecutar("DELETE FROM pacientes WHERE id = ?", (pid,))
    flash("Paciente eliminado.", "ok")
    return redirect(url_for("pacientes"))


@app.post("/pacientes/<int:pid>/diente")
def marcar_diente(pid):
    datos = request.get_json(silent=True) or {}
    diente, estado = datos.get("diente"), datos.get("estado")
    if estado not in ESTADOS_DIENTE or diente not in SUPERIOR + INFERIOR:
        abort(400)
    ejecutar("INSERT OR REPLACE INTO odontograma VALUES (?, ?, ?)", (pid, diente, estado))
    return jsonify(ok=True)


@app.post("/pacientes/<int:pid>/firma")
def firmar(pid):
    firma = request.form.get("firma", "")
    if firma.startswith("data:image/png;base64,"):
        ejecutar("UPDATE pacientes SET firma = ?, firma_fecha = ? WHERE id = ?",
                 (firma, date.today().isoformat(), pid))
        flash("Consentimiento firmado y guardado.", "ok")
    else:
        flash("Dibuja la firma antes de guardar.", "error")
    return volver(pid, "consentimiento")


@app.post("/pacientes/<int:pid>/aprobacion")
def aprobar(pid):
    ejecutar("UPDATE pacientes SET docente = ?, aprobado = ? WHERE id = ?",
             (request.form.get("docente", "").strip(), 1 if request.form.get("aprobado") else 0, pid))
    flash("Aprobación del docente actualizada.", "ok")
    return volver(pid, "historia")


# ---------- tratamientos y cobros ----------
@app.post("/pacientes/<int:pid>/tratamientos")
def tratamiento_nuevo(pid):
    f = request.form
    if f.get("procedimiento", "").strip():
        ejecutar("INSERT INTO tratamientos(paciente_id, procedimiento, diente, costo, fecha) VALUES (?, ?, ?, ?, ?)",
                 (pid, f["procedimiento"].strip(), f.get("diente", "").strip(), numero(f.get("costo")),
                  date.today().isoformat()))
        flash("Tratamiento agregado al plan.", "ok")
    return volver(pid, "tratamientos")


@app.post("/tratamientos/<int:tid>")
def tratamiento_actualizar(tid):
    t = q("SELECT * FROM tratamientos WHERE id = ?", (tid,), uno=True) or abort(404)
    f = request.form
    if f.get("eliminar"):
        ejecutar("DELETE FROM tratamientos WHERE id = ?", (tid,))
    elif f.get("abono"):
        ejecutar("UPDATE tratamientos SET pagado = MIN(costo, pagado + ?) WHERE id = ?", (numero(f["abono"]), tid))
        flash("Pago registrado.", "ok")
    elif f.get("estado") in ("Pendiente", "Realizado"):
        ejecutar("UPDATE tratamientos SET estado = ? WHERE id = ?", (f["estado"], tid))
    return volver(t["paciente_id"], "tratamientos")


@app.route("/cobros", methods=["GET", "POST"])
def cobros():
    if request.method == "POST" and request.form.get("procedimiento", "").strip():
        ejecutar("INSERT INTO tarifario(procedimiento, precio) VALUES (?, ?) "
                 "ON CONFLICT(procedimiento) DO UPDATE SET precio = excluded.precio",
                 (request.form["procedimiento"].strip(), numero(request.form.get("precio"))))
        flash("Tarifario actualizado.", "ok")
        return redirect(url_for("cobros"))
    return render_template(
        "cobros.html",
        totales=q("SELECT COALESCE(SUM(pagado), 0) AS cobrado, COALESCE(SUM(costo - pagado), 0) AS pendiente "
                  "FROM tratamientos", uno=True),
        saldos=q("""SELECT p.id, p.nombre, p.telefono, SUM(t.costo) AS total, SUM(t.pagado) AS pagado,
                           SUM(t.costo - t.pagado) AS saldo
                    FROM tratamientos t JOIN pacientes p ON p.id = t.paciente_id
                    GROUP BY p.id HAVING saldo > 0 ORDER BY saldo DESC"""),
        tarifario=q("SELECT * FROM tarifario ORDER BY procedimiento"))


@app.post("/tarifario/<int:tid>/eliminar")
def tarifario_eliminar(tid):
    ejecutar("DELETE FROM tarifario WHERE id = ?", (tid,))
    return redirect(url_for("cobros"))


# ---------- citas ----------
@app.route("/citas", methods=["GET", "POST"])
def citas():
    if request.method == "POST":
        f = {k: request.form.get(k, "").strip() for k in ("paciente_id", "fecha", "hora", "motivo", "estudiante")}
        activas = " AND estado NOT IN ('Cancelada', 'No asistió')"
        if not (f["paciente_id"] and f["fecha"] and f["hora"]):
            flash("Elige paciente, fecha y hora.", "error")
        elif f["fecha"] < date.today().isoformat():
            flash("No se pueden agendar citas en fechas pasadas.", "error")
        elif q("SELECT 1 FROM citas WHERE paciente_id = ? AND fecha = ?" + activas,
               (f["paciente_id"], f["fecha"]), uno=True):
            flash("Este paciente ya tiene una cita ese día.", "error")
        elif f["estudiante"] and q("SELECT 1 FROM citas WHERE estudiante = ? AND fecha = ? AND hora = ?" + activas,
                                   (f["estudiante"], f["fecha"], f["hora"]), uno=True):
            flash(f"{f['estudiante']} ya tiene otra cita a esa misma hora.", "error")
        else:
            ejecutar("INSERT INTO citas(paciente_id, fecha, hora, motivo, estudiante) VALUES (?, ?, ?, ?, ?)",
                     tuple(f.values()))
            flash("Cita agendada. Recuerda enviarle el recordatorio por WhatsApp.", "ok")
            return redirect(url_for("citas"))
        return redirect(url_for("citas", paciente=f["paciente_id"], _anchor="nueva"))

    ver = request.args.get("ver", "proximas")
    hoy = date.today().isoformat()
    filas = q(CITAS_SQL + (" WHERE c.fecha >= ? ORDER BY c.fecha, c.hora" if ver == "proximas"
                           else " WHERE c.fecha < ? ORDER BY c.fecha DESC, c.hora DESC"), (hoy,))
    return render_template("citas.html", citas=filas, ver=ver, hoy=hoy,
                           pacientes=q("SELECT id, nombre, cedula FROM pacientes ORDER BY nombre"),
                           elegido=request.args.get("paciente", type=int))


@app.post("/citas/<int:cid>/estado")
def cita_estado(cid):
    if request.form.get("estado") in ESTADOS_CITA:
        ejecutar("UPDATE citas SET estado = ? WHERE id = ?", (request.form["estado"], cid))
    return redirect(request.referrer or url_for("citas"))


# ---------- inventario ----------
@app.route("/inventario", methods=["GET", "POST"])
def inventario():
    if request.method == "POST" and request.form.get("material", "").strip():
        f = request.form
        ejecutar("INSERT INTO inventario(material, unidad, cantidad, minimo) VALUES (?, ?, ?, ?) "
                 "ON CONFLICT(material) DO UPDATE SET unidad = excluded.unidad, cantidad = excluded.cantidad, "
                 "minimo = excluded.minimo",
                 (f["material"].strip(), f.get("unidad", "").strip(), int(numero(f.get("cantidad"))),
                  int(numero(f.get("minimo")))))
        flash("Material guardado.", "ok")
        return redirect(url_for("inventario"))
    return render_template("inventario.html", materiales=q(
        "SELECT * FROM inventario ORDER BY cantidad > minimo, material"))


@app.post("/inventario/<int:iid>/ajustar")
def inventario_ajustar(iid):
    if request.form.get("eliminar"):
        ejecutar("DELETE FROM inventario WHERE id = ?", (iid,))
    else:
        ejecutar("UPDATE inventario SET cantidad = MAX(0, cantidad + ?) WHERE id = ?",
                 (request.form.get("delta", 0, type=int), iid))
    return redirect(url_for("inventario", _anchor=f"m{iid}"))


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
    print(f"  Clave de acceso:                {CLAVE}\n")
    app.run(host="0.0.0.0", port=5000)
