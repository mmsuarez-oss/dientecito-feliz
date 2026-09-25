"""Pruebas automaticas de Dientecito Feliz (plan de pruebas, fase 6).

Ejecutar:   python pruebas.py
Usa una base de datos temporal: no toca dientecito.db ni las fotos reales.
Cada caso tiene un codigo (CP-xx) que coincide con docs/plan-de-pruebas.md.
"""
import io
import re
import sqlite3
import sys
import tempfile
import zipfile
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path

import app as m

TEMPORAL = Path(tempfile.mkdtemp())
m.DB, m.FOTOS, m.RESPALDOS = TEMPORAL / "prueba.db", TEMPORAL / "fotos", TEMPORAL / "respaldos"
fallos = []


@contextmanager
def caso(codigo, descripcion):
    try:
        yield
        print(f"  OK     {codigo}  {descripcion}")
    except Exception as e:  # noqa: BLE001 - se reporta cualquier fallo del caso
        fallos.append(codigo)
        print(f"  FALLO  {codigo}  {descripcion}\n         {type(e).__name__}: {e}")


def cliente(usuario, clave="uam2026"):
    c = m.app.test_client()
    r = c.post("/entrar", data={"usuario": usuario, "clave": clave})
    assert r.status_code == 302 and not r.location.endswith("/entrar"), f"no pudo entrar {usuario}"
    return c


def ok(r, *textos):
    assert r.status_code == 200, f"{r.request.path} respondió {r.status_code}"
    html = r.get_data(as_text=True)
    for t in textos:
        assert t in html, f"no aparece «{t}» en {r.request.path}"
    return html


def sql(consulta, args=()):
    con = sqlite3.connect(m.DB)
    fila = con.execute(consulta, args).fetchone()
    con.close()
    return fila[0] if fila else None


JPG = b"\xff\xd8\xff\xe0" + b"0" * 300


def foto():
    return io.BytesIO(JPG), "practica.jpg"


print("Dientecito Feliz - pruebas automáticas\n")
print("Migración")
with caso("CP-01", "Una base de la primera versión se actualiza sin perder datos"):
    viejo = sqlite3.connect(m.DB)
    viejo.executescript("""
        CREATE TABLE pacientes(id INTEGER PRIMARY KEY, nombre TEXT NOT NULL, cedula TEXT UNIQUE NOT NULL,
                               telefono TEXT, nacimiento TEXT, alergias TEXT);
        CREATE TABLE citas(id INTEGER PRIMARY KEY, paciente_id INTEGER NOT NULL, fecha TEXT NOT NULL,
                           hora TEXT NOT NULL, motivo TEXT, estudiante TEXT);
        CREATE TABLE odontograma(paciente_id INTEGER, diente INTEGER, estado TEXT, PRIMARY KEY(paciente_id, diente));
        INSERT INTO pacientes(nombre, cedula) VALUES ('Paciente antiguo', 'V-1');
        INSERT INTO odontograma VALUES (1, 16, 'Caries');""")
    viejo.commit()
    viejo.close()
    m.iniciar_db()
    assert sql("SELECT nombre FROM pacientes WHERE cedula = 'V-1'") == "Paciente antiguo"
    assert sql("SELECT estado FROM odontograma WHERE diente = 16") == "Caries"
    assert sql("SELECT COUNT(*) FROM usuarios") == 3 and sql("SELECT COUNT(*) FROM salas") == 3
    assert sql("SELECT estudiante_id FROM pacientes WHERE cedula = 'V-1'") is not None

print("Acceso y permisos")
anonimo = m.app.test_client()
with caso("CP-02", "Sin sesión, toda página redirige a la pantalla de entrada"):
    for ruta in ("/", "/pacientes", "/citas", "/avisos", "/bitacora"):
        assert anonimo.get(ruta).location.endswith("/entrar"), ruta
with caso("CP-03", "Clave incorrecta es rechazada y queda en la bitácora"):
    ok(anonimo.post("/entrar", data={"usuario": "profesor", "clave": "mala"}, follow_redirects=True), "incorrectos")
    assert sql("SELECT COUNT(*) FROM bitacora WHERE accion = 'Intento de acceso fallido'") == 1
prof, est, serv = cliente("profesor"), cliente("estudiante"), cliente("servicios")
with caso("CP-04", "Cada rol ve solo sus pestañas (403 en las ajenas)"):
    for c, prohibidas in [(est, ["/usuarios", "/tarifario", "/inventario", "/avisos", "/bitacora", "/respaldo"]),
                          (serv, ["/pacientes", "/citas", "/usuarios", "/bitacora"]),
                          (prof, ["/avisos"])]:
        for ruta in prohibidas:
            assert c.get(ruta).status_code == 403, ruta
    for c, permitidas in [(est, ["/", "/pacientes", "/citas", "/salas", "/cuenta"]),
                          (prof, ["/", "/pacientes", "/citas", "/salas", "/tarifario", "/usuarios", "/inventario", "/bitacora"]),
                          (serv, ["/avisos", "/salas", "/inventario", "/cuenta"])]:
        for ruta in permitidas:
            ok(c.get(ruta))
with caso("CP-05", "El profesor crea usuarios; se validan nombre de usuario y clave"):
    ok(prof.post("/usuarios", data={"nombre": "Ana Ruiz", "usuario": "Ana.Ruiz", "rol": "estudiante", "clave": "abc123"},
                 follow_redirects=True), "Usuario ana.ruiz creado")
    ok(prof.post("/usuarios", data={"nombre": "X", "usuario": "a b", "rol": "estudiante", "clave": "abc123"},
                 follow_redirects=True), "sin espacios")
    ok(prof.post("/usuarios", data={"nombre": "X", "usuario": "corto", "rol": "estudiante", "clave": "123"},
                 follow_redirects=True), "al menos 6")
ana = cliente("ana.ruiz", "abc123")
ana_id = sql("SELECT id FROM usuarios WHERE usuario = 'ana.ruiz'")

print("Pacientes y expediente")
with caso("CP-06", "Registrar paciente; nombre y cédula obligatorios; cédula única"):
    ok(est.post("/pacientes/nuevo", data={"nombre": "", "cedula": ""}, follow_redirects=True), "obligatorios")
    html = ok(est.post("/pacientes/nuevo", data={"nombre": "Luis Pérez", "cedula": "T-100", "telefono": "8888 0000",
                                                 "alergias": "Penicilina"}, follow_redirects=True), "ALERGIAS: Penicilina")
    ok(est.post("/pacientes/nuevo", data={"nombre": "Otro", "cedula": "T-100"}, follow_redirects=True), "Ya existe")
pid = int(re.search(r"/pacientes/(\d+)/editar", html).group(1))
with caso("CP-07", "Un estudiante no ve ni abre pacientes de otro estudiante"):
    assert ana.get(f"/pacientes/{pid}").status_code == 404
    assert "Luis Pérez" not in ana.get("/pacientes").get_data(as_text=True)
    ok(prof.get("/pacientes"), "Luis Pérez")
with caso("CP-08", "Editar la historia clínica deja el antes y el después en la bitácora"):
    est.post(f"/pacientes/{pid}/editar", data={"nombre": "Luis Pérez", "cedula": "T-100", "telefono": "8888 0000",
                                               "alergias": "Penicilina, látex"})
    detalle = sql("SELECT detalle FROM bitacora WHERE accion = 'Modificó datos del paciente' AND paciente_id = ?", (pid,))
    assert "«Penicilina» → «Penicilina, látex»" in detalle, detalle
with caso("CP-09", "Consentimiento: se guarda la firma dibujada"):
    ok(est.post(f"/pacientes/{pid}/firma", data={"firma": ""}, follow_redirects=True), "Falta la firma")
    ok(est.post(f"/pacientes/{pid}/firma", data={"firma": "data:image/png;base64,AAAA"}, follow_redirects=True), "Firmado el")
with caso("CP-10", "Solo el profesor aprueba pacientes"):
    assert est.post(f"/pacientes/{pid}/aprobacion", data={"aprobado": "1"}).status_code == 403
    ok(prof.post(f"/pacientes/{pid}/aprobacion", data={"aprobado": "1"}, follow_redirects=True),
       "Aprobado por Profesor de prueba")

print("Odontograma con foto")
with caso("CP-11", "Sin foto, o con un archivo que no es imagen, no se registra"):
    ok(est.post(f"/pacientes/{pid}/odontograma", data={"diente": "16", "estado": "Caries"}, follow_redirects=True),
       "Debes adjuntar una foto")
    ok(est.post(f"/pacientes/{pid}/odontograma", data={"diente": "16", "estado": "Caries",
                                                       "foto": (io.BytesIO(b"texto"), "x.jpg")}, follow_redirects=True),
       "Debes adjuntar una foto")
    ok(est.post(f"/pacientes/{pid}/odontograma", data={"diente": "99", "estado": "Caries", "foto": foto()},
                follow_redirects=True), "Selecciona un diente")
with caso("CP-12", "Con foto válida se registra y queda pendiente de revisión"):
    html = ok(est.post(f"/pacientes/{pid}/odontograma", data={"diente": "16", "estado": "Caries",
                                                              "descripcion": "Operatoria clase I", "foto": foto()},
                       follow_redirects=True), "Diente 16 registrado", "Operatoria clase I", "Pendiente")
    archivo_foto = re.search(r"/fotos/([0-9a-f]+\.jpg)", html).group(1)
    assert est.get(f"/fotos/{archivo_foto}").data == JPG
with caso("CP-13", "Las fotos solo las ven el estudiante dueño y el profesor"):
    assert ana.get(f"/fotos/{archivo_foto}").status_code == 404
    assert serv.get(f"/fotos/{archivo_foto}").status_code == 403
    assert prof.get(f"/fotos/{archivo_foto}").status_code == 200
rid = sql("SELECT MAX(id) FROM odonto_registros")
with caso("CP-14", "El profesor revisa: pedir corrección le aparece al estudiante"):
    assert est.post(f"/registros/{rid}/revision", data={"revision": "Aprobado"}).status_code == 403
    ok(prof.get("/"), "Odontogramas por revisar (1)")
    ok(prof.post(f"/registros/{rid}/revision", data={"revision": "Corregir", "observacion": "Foto borrosa", "volver": "/"},
                 follow_redirects=True), "Odontogramas por revisar (0)")
    ok(est.get("/"), "Foto borrosa", "Corregir")
with caso("CP-15", "Una dirección de regreso externa se ignora (sin redirección abierta)"):
    r = prof.post(f"/registros/{rid}/revision", data={"revision": "Aprobado", "volver": "//sitio-malicioso.com"})
    assert r.location.endswith("#odontograma"), r.location

print("Citas")
manana = (m.hoy() + timedelta(1)).isoformat()
ok(prof.post("/pacientes/nuevo", data={"nombre": "Rosa Díaz", "cedula": "T-200", "estudiante_id": ana_id},
             follow_redirects=True))
pid2 = sql("SELECT id FROM pacientes WHERE cedula = 'T-200'")
with caso("CP-16", "Agendar cita genera el enlace de recordatorio por WhatsApp"):
    ok(est.post("/citas", data={"paciente_id": pid, "fecha": manana, "hora": "09:00", "sala_id": "1"},
                follow_redirects=True), "Cita agendada", "wa.me/50588880000")
with caso("CP-17", "No se permiten citas pasadas ni dos citas del paciente el mismo día"):
    ok(est.post("/citas", data={"paciente_id": pid, "fecha": "2020-01-01", "hora": "09:00"}, follow_redirects=True),
       "fechas pasadas")
    ok(est.post("/citas", data={"paciente_id": pid, "fecha": manana, "hora": "11:00"}, follow_redirects=True),
       "ya tiene una cita ese día")
with caso("CP-18", "No se permite la misma sala a la misma hora"):
    ok(ana.post("/citas", data={"paciente_id": pid2, "fecha": manana, "hora": "09:00", "sala_id": "1"},
                follow_redirects=True), "sala ya está ocupada")
with caso("CP-19", "Un estudiante no puede agendar ni cambiar citas de pacientes ajenos"):
    ok(ana.post("/citas", data={"paciente_id": pid, "fecha": manana, "hora": "10:00"}, follow_redirects=True),
       "Elige paciente")
    cid = sql("SELECT MAX(id) FROM citas")
    assert ana.post(f"/citas/{cid}/estado", data={"estado": "Atendida"}).status_code == 404

print("Salas y avisos a Servicios")
with caso("CP-20", "Un reporte de sala aparece como aviso pendiente para Servicios"):
    ok(est.post("/salas", data={"sala_id": "2", "tipo": "Limpieza", "descripcion": "Derrame en el piso"},
                follow_redirects=True), "Servicios ya recibió el aviso")
    ok(serv.get("/avisos"), "Pendientes (1)", "Derrame en el piso", '<span class="contador">1</span>')
with caso("CP-21", "Al agendar en una sala con reporte pendiente se advierte"):
    ok(ana.post("/citas", data={"paciente_id": pid2, "fecha": manana, "hora": "10:00", "sala_id": "2"},
                follow_redirects=True), "la sala tiene un reporte pendiente")
with caso("CP-22", "Servicios atiende y resuelve; el estado se ve en Salas"):
    rep = sql("SELECT MAX(id) FROM reportes")
    serv.post(f"/reportes/{rep}", data={"estado": "En proceso"})
    ok(serv.post(f"/reportes/{rep}", data={"estado": "Resuelto"}, follow_redirects=True), "Pendientes (0)")
    ok(est.get("/salas"), "Resuelto")

print("Tratamientos y cobros")
ok(prof.post("/tarifario", data={"procedimiento": "Profilaxis", "precio": "300"}, follow_redirects=True), "C$ 300.00")
ok(est.post(f"/pacientes/{pid}/tratamientos", data={"procedimiento": "Profilaxis", "costo": "300"}, follow_redirects=True))
tid = sql("SELECT MAX(id) FROM tratamientos")
with caso("CP-23", "Un pago nunca supera el saldo pendiente"):
    est.post(f"/tratamientos/{tid}", data={"abono": "100"})
    est.post(f"/tratamientos/{tid}", data={"abono": "999"})
    assert sql("SELECT pagado FROM tratamientos WHERE id = ?", (tid,)) == 300
with caso("CP-24", "Un tratamiento con pagos solo lo puede eliminar el profesor"):
    ok(est.post(f"/tratamientos/{tid}", data={"eliminar": "1"}, follow_redirects=True), "solo un profesor")
    assert sql("SELECT COUNT(*) FROM tratamientos WHERE id = ?", (tid,)) == 1
    prof.post(f"/tratamientos/{tid}", data={"eliminar": "1"})
    assert sql("SELECT COUNT(*) FROM tratamientos WHERE id = ?", (tid,)) == 0
    assert "pagado C$ 300.00" in sql("SELECT detalle FROM bitacora WHERE accion = 'Eliminó tratamiento'")

print("Protección del expediente")
with caso("CP-25", "Ya no existe la opción de borrar pacientes"):
    assert est.post(f"/pacientes/{pid}/eliminar").status_code in (404, 405)
    assert est.post(f"/pacientes/{pid}/archivo", data={"motivo": "x"}).status_code == 403
with caso("CP-26", "El profesor archiva con motivo; el paciente desaparece de las listas pero se conserva"):
    ok(prof.post(f"/pacientes/{pid}/archivo", data={"motivo": ""}, follow_redirects=True), "Indique el motivo")
    ok(prof.post(f"/pacientes/{pid}/archivo", data={"motivo": "Alta del tratamiento"}, follow_redirects=True), "fue archivado")
    assert "Luis Pérez" not in prof.get("/pacientes").get_data(as_text=True)
    assert est.get(f"/pacientes/{pid}").status_code == 404
    ok(prof.get("/pacientes?archivados=1"), "Luis Pérez")
    ok(prof.get(f"/pacientes/{pid}"), "Paciente archivado", "Alta del tratamiento")
    assert sql("SELECT COUNT(*) FROM odonto_registros WHERE paciente_id = ?", (pid,)) == 1
with caso("CP-27", "El profesor puede restaurar un paciente archivado"):
    ok(prof.post(f"/pacientes/{pid}/archivo", data={"restaurar": "1"}, follow_redirects=True), "Paciente restaurado")
    ok(est.get(f"/pacientes/{pid}"), "Luis Pérez")
with caso("CP-28", "El historial del expediente muestra todas las acciones realizadas"):
    html = ok(prof.get(f"/pacientes/{pid}"), "Historial de cambios")
    for accion in ("Registró paciente", "Modificó datos del paciente", "Registró firma", "Aprobó paciente",
                   "Registró práctica en odontograma", "Revisó odontograma", "Agendó cita", "Registró pago",
                   "Archivó paciente", "Restauró paciente"):
        assert accion in html, accion
with caso("CP-29", "Se crea una copia diaria automática de la base de datos"):
    copias = list(m.RESPALDOS.glob("dientecito-*.db"))
    assert len(copias) == 1 and copias[0].name == f"dientecito-{m.hoy().isoformat()}.db"
with caso("CP-30", "El profesor descarga un .zip con la base de datos y las fotos"):
    r = prof.get("/respaldo")
    assert r.status_code == 200 and "attachment" in r.headers["Content-Disposition"]
    with zipfile.ZipFile(io.BytesIO(r.data)) as z:
        nombres = z.namelist()
        assert "dientecito.db" in nombres and f"fotos/{archivo_foto}" in nombres, nombres
        copia = TEMPORAL / "restaurada.db"
        copia.write_bytes(z.read("dientecito.db"))
    assert sqlite3.connect(copia).execute("SELECT COUNT(*) FROM pacientes").fetchone()[0] >= 3
    r.close()

print("Cuentas")
with caso("CP-31", "Cambio de clave propia y desactivación de cuentas"):
    ok(ana.post("/cuenta", data={"actual": "abc123", "nueva": "nueva123", "repetir": "otra"}, follow_redirects=True),
       "no coinciden")
    ok(ana.post("/cuenta", data={"actual": "abc123", "nueva": "nueva123", "repetir": "nueva123"}, follow_redirects=True),
       "Clave actualizada")
    cliente("ana.ruiz", "nueva123")
    prof.post(f"/usuarios/{ana_id}", data={"activo": "0"})
    assert ana.get("/").location.endswith("/entrar")

total = 31
print(f"\n{total - len(fallos)} de {total} casos correctos." + (f" Fallaron: {', '.join(fallos)}" if fallos else ""))
sys.exit(1 if fallos else 0)
