"""Publica (o actualiza) Dientecito Feliz en PythonAnywhere usando su API.

Uso:   python desplegar.py USUARIO [--clave CLAVE] [--eu]
El token de la API se lee de la variable PA_TOKEN o del archivo .pa_token (no se sube a GitHub).
La base de datos del servidor NO se toca: los datos de prueba se conservan entre actualizaciones.
"""
import argparse
import json
import os
import secrets
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

RAIZ = Path(__file__).parent
ARCHIVOS = ["app.py", "requirements.txt", *[str(p.relative_to(RAIZ)).replace("\\", "/")
                                            for carpeta in ("templates", "static")
                                            for p in sorted((RAIZ / carpeta).rglob("*")) if p.is_file()]]

args = argparse.ArgumentParser()
args.add_argument("usuario")
args.add_argument("--clave", default="uam2026", help="clave de acceso que usaran los probadores")
args.add_argument("--eu", action="store_true", help="la cuenta es de eu.pythonanywhere.com")
args = args.parse_args()

token = os.environ.get("PA_TOKEN") or (RAIZ / ".pa_token").read_text(encoding="utf-8").strip()
host = "eu.pythonanywhere.com" if args.eu else "www.pythonanywhere.com"
dominio = f"{args.usuario}.{'eu.' if args.eu else ''}pythonanywhere.com"
api = f"https://{host}/api/v0/user/{args.usuario}"
carpeta = f"/home/{args.usuario}/dientecito"


def pedir(metodo, ruta, datos=None, archivo=None):
    headers = {"Authorization": f"Token {token}"}
    cuerpo = None
    if archivo is not None:  # multipart con el campo "content"
        limite = uuid.uuid4().hex
        headers["Content-Type"] = f"multipart/form-data; boundary={limite}"
        cuerpo = (f"--{limite}\r\nContent-Disposition: form-data; name=\"content\"; filename=\"f\"\r\n"
                  f"Content-Type: application/octet-stream\r\n\r\n").encode() + archivo + f"\r\n--{limite}--\r\n".encode()
    elif datos is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        cuerpo = urllib.parse.urlencode(datos).encode()
    req = urllib.request.Request(api + ruta, data=cuerpo, headers=headers, method=metodo)
    try:
        with urllib.request.urlopen(req) as r:
            texto = r.read().decode() or "{}"
            return r.status, json.loads(texto) if texto.lstrip()[:1] in "[{" else texto
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def subir(destino, contenido):
    estado, resp = pedir("POST", f"/files/path{destino}", archivo=contenido)
    if estado not in (200, 201):
        raise SystemExit(f"Error subiendo {destino}: {estado} {resp}")


print(f"Subiendo {len(ARCHIVOS)} archivos a {carpeta} ...")
for rel in ARCHIVOS:
    subir(f"{carpeta}/{rel}", (RAIZ / rel).read_bytes())

estado, apps = pedir("GET", "/webapps/")
if estado != 200:
    raise SystemExit(f"No se pudo consultar la cuenta ({estado}). ¿Token o usuario incorrectos?")
if not any(a["domain_name"] == dominio for a in apps):
    print("Creando la aplicacion web ...")
    for version in ("python313", "python312", "python311", "python310"):
        estado, resp = pedir("POST", "/webapps/", {"domain_name": dominio, "python_version": version})
        if estado in (200, 201):
            print(f"  usando {version}")
            break
    else:
        raise SystemExit(f"No se pudo crear la aplicacion: {estado} {resp}")

wsgi = f"""import os, sys
os.environ["DIENTECITO_CLAVE"] = {args.clave!r}
os.environ["DIENTECITO_SECRETO"] = {secrets.token_hex(24)!r}
os.environ["DIENTECITO_DEMO"] = "1"
sys.path.insert(0, {carpeta!r})
from app import app as application
"""
subir(f"/var/www/{dominio.replace('.', '_')}_wsgi.py", wsgi.encode())
pedir("PATCH", f"/webapps/{dominio}/", {"source_directory": carpeta, "force_https": True})

estado, mapeos = pedir("GET", f"/webapps/{dominio}/static_files/")
if estado == 200 and not any(m["url"] == "/static/" for m in mapeos):
    pedir("POST", f"/webapps/{dominio}/static_files/", {"url": "/static/", "path": f"{carpeta}/static"})

estado, resp = pedir("POST", f"/webapps/{dominio}/reload/")
if estado != 200:
    raise SystemExit(f"No se pudo recargar: {estado} {resp}")
print(f"\nListo: https://{dominio}\nClave de acceso: {args.clave}")
