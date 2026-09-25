# Diccionario de datos — Dientecito Feliz

Base de datos SQLite (`dientecito.db`). Corresponde a la actividad 3.4 del cronograma.
Las fechas se guardan como texto ISO (`AAAA-MM-DD` o `AAAA-MM-DD HH:MM`) en hora de Nicaragua (UTC−6).

**Convenciones:** PK = llave primaria · FK = llave foránea · NN = obligatorio · Único = no admite repetidos.

## Diagrama de relaciones

```
usuarios ─┬─< pacientes (estudiante_id) ─┬─< citas >── salas ──< reportes >── usuarios
          │                              ├─< odontograma
          ├─< odonto_registros >─────────┤
          │   (usuario_id, revisado_por) ├─< tratamientos
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
| rol | TEXT | NN | `estudiante`, `profesor` o `servicios` |
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
| nacimiento | TEXT | | Fecha de nacimiento; con ella se calcula la edad |
| sexo | TEXT | | `Femenino`, `Masculino` o vacío |
| direccion | TEXT | | Dirección de domicilio |
| contacto_emergencia | TEXT | | Nombre y teléfono de un contacto |
| alergias | TEXT | | Alergias conocidas. Si tiene valor, se muestra una alerta en el expediente |
| motivo_consulta | TEXT | | Motivo de consulta |
| antecedentes | TEXT | | Antecedentes médicos |
| medicamentos | TEXT | | Medicamentos que toma actualmente |
| examen_clinico | TEXT | | Examen extraoral e intraoral |
| plan | TEXT | | Diagnóstico y plan de tratamiento |
| estudiante_id | INTEGER | FK → usuarios.id | Estudiante responsable. Cada estudiante ve solo sus pacientes |
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
| estudiante | TEXT | | *Obsoleto* (primera versión). El estudiante ahora se obtiene del paciente |

**Reglas:** un paciente no puede tener dos citas activas el mismo día. Un estudiante no puede tener dos citas a la misma hora. Una sala no puede usarse dos veces a la misma hora.

## odontograma
Estado **actual** de cada diente. Solo cambia mediante un registro con foto (`odonto_registros`).

| Campo | Tipo | Restricciones | Descripción |
|---|---|---|---|
| paciente_id | INTEGER | PK, FK → pacientes.id | Paciente |
| diente | INTEGER | PK | Número FDI (11–18, 21–28, 31–38, 41–48) |
| estado | TEXT | | `Sano`, `Caries`, `Obturado`, `Corona`, `Endodoncia` o `Extraido` |

## odonto_registros
Historial de prácticas realizadas en el odontograma, cada una con su foto de evidencia.

| Campo | Tipo | Restricciones | Descripción |
|---|---|---|---|
| id | INTEGER | PK | Identificador del registro |
| paciente_id | INTEGER | NN, FK → pacientes.id | Paciente |
| diente | INTEGER | NN | Diente trabajado (número FDI) |
| estado | TEXT | NN | Estado en que quedó el diente |
| descripcion | TEXT | | Procedimiento realizado |
| foto | TEXT | NN | Nombre del archivo de la foto en la carpeta `fotos/`. Se verifica que sea JPG, PNG, WEBP o HEIC |
| fecha | TEXT | NN | Fecha y hora del registro |
| usuario_id | INTEGER | FK → usuarios.id | Quién registró la práctica |
| revision | TEXT | Por defecto `Pendiente` | `Pendiente`, `Aprobado` o `Corregir` |
| observacion | TEXT | | Comentario del profesor |
| revisado_por | INTEGER | FK → usuarios.id | Profesor que revisó |

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
| `fotos/` | Fotos de las prácticas del odontograma, reducidas a un máximo de 1600 px. Nunca se borran |
| `respaldos/` | Copia automática diaria de la base de datos; se conservan las últimas 14 |
