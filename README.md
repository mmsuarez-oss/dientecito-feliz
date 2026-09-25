# 🦷 Dientecito Feliz

Sistema de gestión para la **Clínica Odontológica UAM**. Es una aplicación web en Python (Flask + SQLite) que funciona en computadora y en teléfonos Android e iOS.

**Funciones:** expediente e historia clínica, alerta de alergias, odontograma interactivo, consentimiento informado con firma digital, aprobación del docente, agenda de citas que evita duplicados, recordatorios por WhatsApp, plan de tratamiento con cobros y tarifario, e inventario de materiales con alertas de stock bajo.

## Ejecutar en tu computadora
```bash
pip install -r requirements.txt
python app.py
```
Abre `http://localhost:5000`. La clave por defecto es `uam2026`; para cambiarla, define la variable de entorno `DIENTECITO_CLAVE`.
Los teléfonos conectados a la misma red Wi-Fi pueden entrar con la dirección que aparece en la consola.

## Publicar en PythonAnywhere
1. En PythonAnywhere ve a *Account → API token* y crea un token. Guárdalo en un archivo `.pa_token` en esta carpeta (git lo ignora).
2. Ejecuta `python desplegar.py TU_USUARIO`. Si tu cuenta es de la región europea, agrega `--eu`.

Ese mismo comando sirve para publicar cada actualización. La base de datos del servidor no se toca, así que los datos se conservan.

> La base de datos local (`dientecito.db`) nunca se sube al repositorio.

Proyecto de curso · Equipo: Andrés Castillo, Camilo Cruz, Reynaldo Mondragón, Roberto Silva, Miguel Suárez.
