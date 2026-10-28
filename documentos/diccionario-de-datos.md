# Diccionario de datos — Clínicas Odontológicas

Base de datos SQLite (`sistema/dientecito.db`). Las mismas tablas existen para PostgreSQL en la nube en `sistema/neon.py` (Neon), donde `INTEGER PRIMARY KEY` pasa a `SERIAL` y `REAL` a `DOUBLE PRECISION`. Corresponde a la actividad 3.4 del cronograma.
Las fechas se guardan como texto ISO (`AAAA-MM-DD` o `AAAA-MM-DD HH:MM`) en hora de Nicaragua (UTC−6).

**Convenciones:** PK = llave primaria · FK = llave foránea · NN = obligatorio · Único = no admite repetidos.

## Diagrama de relaciones

```
usuarios ─┬─< pacientes (estudiante_id) ─┬─< citas >── salas ──< reportes >── usuarios
          │                              ├─< odontograma
          ├─< odonto_sesiones >──────────┤   (una sesión = foto presencial + odontograma digital)
          │        └─< odonto_registros  ├─< tratamientos
          ├─< asignaciones >─────────────┤   (un periodo de trabajo de un estudiante con el paciente)
          └─< bitacora >─────────────────┘
tarifario, inventario: tablas independientes
```

---

## usuarios
Personas que usan el sistema. El rol define la interfaz que ven.

| Campo | Tipo | Restricciones | Descripción |
|---|---|---|---|
| id | INTEGER | PK | Identificador del usuario |
| usuario | TEXT | NN, Único | Nombre para iniciar sesión: 3 a 30 letras o números, en minúsculas |
| nombre | TEXT | NN | Nombre completo que se muestra en pantalla |
| rol | TEXT | NN | `estudiante`, `profesor`, `servicios` o `admin` (Facultad). El profesor solo revisa; la Facultad lleva cuentas, salas, tarifario, inventario y los traspasos de pacientes |
| clave | TEXT | NN | Clave cifrada con *scrypt* (nunca se guarda en texto plano) |
| activo | INTEGER | Por defecto 1 | 1 = puede entrar · 0 = cuenta desactivada. Los usuarios no se borran |

## pacientes
Expediente clínico del paciente.

| Campo | Tipo | Restricciones | Descripción |
|---|---|---|---|
| id | INTEGER | PK | Identificador del paciente |
| nombre | TEXT | NN | Nombre completo |
| cedula | TEXT | NN, Único | Cédula de identidad |
| telefono | TEXT | | Teléfono o WhatsApp. Si tiene 8 dígitos se le antepone 505 |
| correo | TEXT | | Correo del paciente. Si está, habilita el botón "Correo" para enviarle el recordatorio de cita |
| nacimiento | TEXT | | Fecha de nacimiento; con ella se calcula la edad |
| sexo | TEXT | | `Femenino`, `Masculino` o vacío |
| direccion | TEXT | | Dirección de domicilio |
| contacto_emergencia_nombre | TEXT | | Nombre del contacto de emergencia |
| contacto_emergencia_telefono | TEXT | | Teléfono del contacto de emergencia |
| contacto_emergencia | TEXT | | *Obsoleto*: campo único usado antes de separar nombre y teléfono |
| alergias | TEXT | | Alergias conocidas. Si tiene valor, se muestra una alerta en el expediente |
| motivo_consulta | TEXT | | Razón por la que está el paciente. Se pide en el paso siguiente al registro y se muestra al lado de su nombre y en la página de citas |
| antecedentes | TEXT | | Antecedentes médicos |
| medicamentos | TEXT | | Medicamentos que toma actualmente |
| examen_clinico | TEXT | | Examen extraoral e intraoral |
| plan | TEXT | | Diagnóstico y plan de tratamiento |
| estudiante_id | INTEGER | FK → usuarios.id | Estudiante responsable **ahora**. Cada estudiante ve solo sus pacientes y sus citas. El historial completo está en `asignaciones` |
| aprobado | INTEGER | Por defecto 0 | 1 = aprobado por un profesor |
| docente | TEXT | | Nombre del profesor que lo aprobó |
| firma | TEXT | | Imagen PNG de la firma del consentimiento informado (en base64) |
| firma_fecha | TEXT | | Fecha en que se firmó el consentimiento |
| archivado | INTEGER | Por defecto 0 | 1 = archivado: no aparece en las listas, pero se conserva completo. Los pacientes no se borran |

## citas
| Campo | Tipo | Restricciones | Descripción |
|---|---|---|---|
| id | INTEGER | PK | Identificador de la cita |
| paciente_id | INTEGER | NN, FK → pacientes.id | Paciente citado |
| fecha | TEXT | NN | Fecha de la cita; no puede ser pasada |
| hora | TEXT | NN | Hora (`HH:MM`) |
| motivo | TEXT | | Motivo: valoración, profilaxis, control, etc. |
| sala_id | INTEGER | FK → salas.id | Sala asignada (opcional) |
| estado | TEXT | Por defecto `Pendiente` | `Pendiente`, `Confirmada`, `Atendida`, `No asistió` o `Cancelada` |
| token | TEXT | | Código al azar que da acceso al enlace público de la cita (`/c/<token>`), sin necesidad de cuenta |
| estudiante | TEXT | | *Obsoleto* (primera versión). El estudiante ahora se obtiene del paciente |

**Reglas:** un paciente no puede tener dos citas activas el mismo día. Un estudiante no puede tener dos citas a la misma hora. Una sala no puede usarse dos veces a la misma hora.

## odontograma
Estado **actual** de cada diente. Solo cambia al marcar dientes dentro de una sesión que ya tiene su foto presencial.

| Campo | Tipo | Restricciones | Descripción |
|---|---|---|---|
| paciente_id | INTEGER | PK, FK → pacientes.id | Paciente |
| diente | INTEGER | PK | Número FDI (11–18, 21–28, 31–38, 41–48) |
| estado | TEXT | | `Sano`, `Caries`, `Obturado`, `Corona`, `Endodoncia` o `Extraido` |

## odonto_sesiones
Cada vez que se llena un odontograma. **Primero se sube la foto del odontograma presencial** (obligatoria). Solo con una sesión abierta se habilita el odontograma digital.

| Campo | Tipo | Restricciones | Descripción |
|---|---|---|---|
| id | INTEGER | PK | Identificador de la sesión |
| paciente_id | INTEGER | NN, FK → pacientes.id | Paciente |
| foto | TEXT | NN | Foto del odontograma presencial (archivo en `fotos/`). Se verifica que sea JPG, PNG, WEBP o HEIC |
| nota | TEXT | | Tipo de práctica u observaciones del estudiante |
| fecha | TEXT | NN | Fecha y hora en que se subió la foto |
| usuario_id | INTEGER | FK → usuarios.id | Quién subió la foto |
| estado | TEXT | Por defecto `Abierta` | `Abierta` (en edición) → `Pendiente` (enviada al docente) → `Aprobado` o `Corregir` (vuelve a ser editable) |
| enviado | TEXT | | Fecha y hora del último envío a revisión |
| observacion | TEXT | | Comentario del docente; obligatorio al pedir corrección |
| revisado_por | INTEGER | FK → usuarios.id | Docente que revisó |
| revisado | TEXT | | Fecha y hora de la revisión |

**Reglas:** un paciente solo puede tener una sesión en edición (`Abierta` o `Corregir`) a la vez. Una sesión `Pendiente` o `Aprobado` no se puede modificar.

## odonto_registros
Dientes marcados en el odontograma digital de cada sesión.

| Campo | Tipo | Restricciones | Descripción |
|---|---|---|---|
| id | INTEGER | PK | Identificador del registro |
| sesion_id | INTEGER | FK → odonto_sesiones.id | Sesión a la que pertenece. Hay un registro por diente en cada sesión |
| paciente_id | INTEGER | NN, FK → pacientes.id | Paciente |
| diente | INTEGER | NN | Diente marcado (número FDI) |
| estado | TEXT | NN | Estado marcado |
| foto | TEXT | NN | Copia del nombre de la foto de la sesión |
| fecha | TEXT | NN | Fecha y hora en que se marcó |
| usuario_id | INTEGER | FK → usuarios.id | Quién lo marcó |
| descripcion, revision, observacion, revisado_por | | | *Obsoletos*: de la versión con una foto por diente. Al actualizar, esos registros se convierten en sesiones |

## tratamientos
Plan de tratamiento y cobros del paciente.

| Campo | Tipo | Restricciones | Descripción |
|---|---|---|---|
| id | INTEGER | PK | Identificador |
| paciente_id | INTEGER | NN, FK → pacientes.id | Paciente |
| procedimiento | TEXT | NN | Nombre del procedimiento |
| diente | TEXT | | Diente o dientes involucrados |
| costo | REAL | Por defecto 0 | Costo en córdobas (C$) |
| pagado | REAL | Por defecto 0 | Monto pagado. Nunca supera el costo |
| estado | TEXT | Por defecto `Pendiente` | `Pendiente` o `Realizado` |
| fecha | TEXT | | Fecha en que se agregó |

**Regla:** un tratamiento con pagos registrados solo puede eliminarlo un profesor, y queda constancia en la bitácora.

## tarifario
| Campo | Tipo | Restricciones | Descripción |
|---|---|---|---|
| id | INTEGER | PK | Identificador |
| procedimiento | TEXT | NN, Único | Nombre del procedimiento |
| precio | REAL | Por defecto 0 | Precio de referencia en C$; se sugiere al agregar tratamientos |

## salas
| Campo | Tipo | Restricciones | Descripción |
|---|---|---|---|
| id | INTEGER | PK | Identificador |
| nombre | TEXT | NN, Único | Nombre de la sala o unidad |

## reportes
Avisos de salas que necesitan reparación o limpieza, dirigidos a Servicios.

| Campo | Tipo | Restricciones | Descripción |
|---|---|---|---|
| id | INTEGER | PK | Identificador |
| sala_id | INTEGER | NN, FK → salas.id | Sala reportada |
| tipo | TEXT | NN | `Reparación` o `Limpieza` |
| descripcion | TEXT | | Detalle del problema |
| estado | TEXT | Por defecto `Pendiente` | `Pendiente`, `En proceso` o `Resuelto` |
| reportado_por | INTEGER | FK → usuarios.id | Quién reportó |
| fecha | TEXT | NN | Fecha y hora del reporte |
| atendido_por | INTEGER | FK → usuarios.id | Persona de Servicios que lo atendió |
| actualizado | TEXT | | Fecha y hora del último cambio de estado |

## inventario
| Campo | Tipo | Restricciones | Descripción |
|---|---|---|---|
| id | INTEGER | PK | Identificador |
| material | TEXT | NN, Único | Nombre del material o insumo |
| unidad | TEXT | | Unidad de medida (cajas, unidades…) |
| cantidad | INTEGER | Por defecto 0 | Existencia actual; nunca baja de 0 |
| minimo | INTEGER | Por defecto 0 | Si la cantidad llega a este valor, se marca "Reponer" |

## asignaciones
Periodos en los que un estudiante tuvo a su cargo a un paciente. Cuando el paciente cambia de estudiante, el periodo
del anterior se cierra con la fecha y el resumen de lo que se le hizo: así queda archivado su trabajo y no se pierde.

| Campo | Tipo | Restricciones | Descripción |
|---|---|---|---|
| id | INTEGER | PK | Identificador de la asignación |
| paciente_id | INTEGER | NN, FK → pacientes.id | Paciente |
| estudiante_id | INTEGER | FK → usuarios.id | Estudiante que lo atendió en ese periodo |
| desde | TEXT | NN | Fecha en que lo recibió |
| hasta | TEXT | | Fecha en que lo entregó. Vacío = es el estudiante que lo atiende ahora |
| resumen | TEXT | | Qué se le hizo al paciente y qué trabajó el estudiante. Obligatorio al traspasarlo |

## bitacora
Registro de auditoría: quién hizo qué y cuándo. La aplicación solo agrega registros; nunca los modifica ni los borra.

| Campo | Tipo | Restricciones | Descripción |
|---|---|---|---|
| id | INTEGER | PK | Identificador (orden cronológico) |
| fecha | TEXT | NN | Fecha y hora (`AAAA-MM-DD HH:MM:SS`) |
| usuario_id | INTEGER | | Usuario que realizó la acción. Vacío en intentos de acceso fallidos |
| accion | TEXT | NN | Acción, por ejemplo "Registró pago" o "Archivó paciente" |
| detalle | TEXT | | Datos de la acción. Al editar un paciente guarda el valor anterior y el nuevo |
| paciente_id | INTEGER | Índice | Paciente relacionado, si lo hay; alimenta el historial del expediente |

---

## Archivos fuera de la base de datos
| Carpeta | Contenido |
|---|---|
| `fotos/` | Fotos de los odontogramas presenciales, reducidas a un máximo de 1600 px. Nunca se borran |
| `respaldos/` | Copia automática diaria de la base de datos; se conservan las últimas 14 |
