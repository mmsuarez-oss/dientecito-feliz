# Plan de pruebas — Dientecito Feliz

Corresponde a las actividades 6.1 (plan y casos de prueba) y 6.2 (pruebas unitarias y de integración) del cronograma.

## 1. Alcance y enfoque

| Tipo | Cómo se ejecuta | Qué cubre |
|---|---|---|
| **Automáticas de integración** | `python pruebas.py` | Los 31 casos de la sección 3: recorren la aplicación completa (servidor, reglas y base de datos) como lo haría cada usuario |
| **Manuales de interfaz** | Navegador de computadora y vista de teléfono (390 px) | Sección 4: diseño, uso táctil, fotos y firma |
| **De aceptación** | Con la clínica (actividad 6.4) | Sección 5: pendientes |

Las pruebas automáticas usan una **base de datos temporal**: no modifican `dientecito.db` ni las fotos reales. Cada caso tiene un código (CP-xx) que aparece en la salida del programa.

**Datos de prueba:**
- Cuentas de ejemplo `estudiante`, `profesor` y `servicios`, más una segunda estudiante creada durante la prueba (`ana.ruiz`).
- Pacientes ficticios: *Luis Pérez* (T-100) y *Rosa Díaz* (T-200).
- Fotos: archivos JPG mínimos.

## 2. Criterio de aceptación
Se aprueba la versión si los **31 casos automáticos** terminan en OK y las pruebas manuales no encuentran defectos que impidan el uso.

## 3. Casos de prueba automáticos

### Migración
| Código | Caso | Pasos / datos | Resultado esperado |
|---|---|---|---|
| CP-01 | Actualizar una base de versiones anteriores | Base con el esquema original, un paciente, un diente marcado y un registro con foto por diente | Se agregan tablas y columnas nuevas. El paciente y el diente se conservan. Se crean 3 usuarios y 3 salas de ejemplo. El registro antiguo se convierte en una sesión con su foto y su estado de revisión |

### Acceso y permisos
| Código | Caso | Pasos / datos | Resultado esperado |
|---|---|---|---|
| CP-02 | Páginas sin sesión | Abrir `/`, `/pacientes`, `/citas`, `/avisos` y `/bitacora` sin entrar | Redirige a la pantalla de entrada |
| CP-03 | Clave incorrecta | Usuario `profesor` con clave errónea | Mensaje "Usuario o clave incorrectos", y el intento queda en la bitácora |
| CP-04 | Pestañas por rol | Cada rol abre las páginas propias y las ajenas | Las propias responden; las ajenas dan error 403 |
| CP-05 | Crear usuarios | Usuario válido, usuario con espacio y clave de 3 caracteres | Crea el válido y rechaza los otros dos con su mensaje |

### Pacientes y expediente
| Código | Caso | Pasos / datos | Resultado esperado |
|---|---|---|---|
| CP-06 | Registrar paciente | Formulario vacío; luego un paciente válido con alergia; luego una cédula repetida | Pide los campos obligatorios, registra y muestra la alerta de alergia, y rechaza el duplicado |
| CP-07 | Privacidad entre estudiantes | `ana.ruiz` intenta abrir un paciente de `estudiante` | No lo ve en su lista y la página responde 404. El profesor sí lo ve |
| CP-08 | Auditoría de ediciones | Cambiar las alergias de «Penicilina» a «Penicilina, látex» | La bitácora guarda el valor anterior y el nuevo |
| CP-09 | Consentimiento | Guardar sin firma; luego con firma | Primero pide la firma; luego muestra "Firmado el…" |
| CP-10 | Aprobación docente | El estudiante intenta aprobar; luego el profesor | El estudiante recibe 403. Con el profesor aparece "Aprobado por…" |

### Odontograma: primero la foto presencial, después el digital
| Código | Caso | Pasos / datos | Resultado esperado |
|---|---|---|---|
| CP-11 | Sin foto no hay odontograma digital | Abrir el expediente sin foto; marcar un diente sin sesión; subir sin archivo; subir un archivo de texto | El odontograma aparece bloqueado. Marcar da 404. Las subidas inválidas se rechazan y no se crea ninguna sesión |
| CP-12 | Foto presencial y odontograma digital | Subir una foto JPG; marcar 16 Obturado, luego 16 Caries y 26 Obturado; marcar el diente 99; iniciar otra sesión | La foto se guarda y se habilita el odontograma. Queda un registro por diente (16 = Caries). El diente 99 da 400. No se permite una segunda sesión en curso |
| CP-13 | Privacidad de fotos | Abrir la foto y la sesión como otra estudiante, como Servicios y como docente | 404, 403 y 200. La otra estudiante tampoco puede abrir la sesión |
| CP-14 | Envío y revisión del docente | Enviar a revisión; intentar marcar; el docente abre la revisión; pide corrección sin observación y luego con observación; el estudiante corrige y reenvía; el docente aprueba | Tras enviar, marcar da 409. El docente ve la foto, el odontograma digital y "16: Caries". Sin observación se rechaza. Con observación, el estudiante la ve y el odontograma se desbloquea. Al final queda "Aprobado" |
| CP-15 | Redirección segura | Revisar con `volver=//sitio-malicioso.com` | Se ignora y regresa a la pantalla de revisión |

### Citas
| Código | Caso | Pasos / datos | Resultado esperado |
|---|---|---|---|
| CP-16 | Agendar cita | Paciente con teléfono 8888 0000, mañana 09:00, Sala 1 | Cita creada con el enlace `wa.me/50588880000` |
| CP-17 | Fechas y duplicados | Cita en 2020; segunda cita del mismo paciente el mismo día | Ambas son rechazadas |
| CP-18 | Sala ocupada | Otra cita en la Sala 1, mañana 09:00 | "Esa sala ya está ocupada a esa hora" |
| CP-19 | Pacientes ajenos | `ana.ruiz` agenda o cambia una cita de un paciente ajeno | Rechazada (404) |

### Salas y avisos
| Código | Caso | Pasos / datos | Resultado esperado |
|---|---|---|---|
| CP-20 | Enviar aviso | El estudiante reporta la Sala 2 por limpieza | Servicios la ve en *Avisos* y el contador muestra 1 |
| CP-21 | Advertencia al agendar | Cita en la Sala 2 con el reporte pendiente | La cita se crea y se advierte del reporte |
| CP-22 | Resolver aviso | Servicios marca "En proceso" y luego "Resuelto" | El contador baja a 0 y el estado se ve en *Salas* |

### Tratamientos y cobros
| Código | Caso | Pasos / datos | Resultado esperado |
|---|---|---|---|
| CP-23 | Tope de pagos | Tratamiento de C$ 300; pagos de 100 y luego de 999 | Lo pagado queda en C$ 300 exactos |
| CP-24 | Eliminar con pagos | El estudiante intenta eliminar; luego el profesor | Se niega al estudiante. El profesor lo elimina y la bitácora guarda el monto pagado |

### Protección del expediente
| Código | Caso | Pasos / datos | Resultado esperado |
|---|---|---|---|
| CP-25 | Sin borrado | El estudiante intenta borrar o archivar un paciente | No existe la opción de borrar, y archivar le da 403 |
| CP-26 | Archivar | El profesor archiva sin motivo y luego con "Alta del tratamiento" | Primero pide el motivo. Luego el paciente sale de las listas y de la vista del estudiante, se ve en "Ver archivados" y conserva su odontograma |
| CP-27 | Restaurar | El profesor presiona Restaurar | El paciente vuelve a las listas del estudiante |
| CP-28 | Historial del expediente | Abrir el *Historial de cambios* | Muestra todas las acciones realizadas: registro, edición, firma, aprobación, foto presencial, dientes marcados, envío y revisión del odontograma, cita, pago, archivo y restauración |
| CP-29 | Respaldo diario | Cualquier visita al sistema | Existe `respaldos/dientecito-<fecha de hoy>.db` |
| CP-30 | Descargar respaldo | El profesor presiona *Descargar copia* | Un `.zip` con `dientecito.db` y las fotos. La base del `.zip` se abre y contiene los pacientes |

### Cuentas
| Código | Caso | Pasos / datos | Resultado esperado |
|---|---|---|---|
| CP-31 | Clave y desactivación | Cambiar la clave con una confirmación distinta; luego correcta; luego el profesor desactiva la cuenta | Rechaza, luego acepta la clave nueva. Al desactivarla, la sesión deja de funcionar |

## 4. Pruebas manuales de interfaz

| Código | Caso | Resultado |
|---|---|---|
| PM-01 | Vista de computadora de los tres roles | Correcto |
| PM-02 | Vista de teléfono (390 px): sin desplazamiento horizontal de la página; las tablas se deslizan dentro de su recuadro; odontograma en filas de 8 | Correcto |
| PM-03 | Sin foto presencial, tocar un diente muestra el aviso "Primero suba la foto…". Con foto, tocar un diente lo guarda y le pone un marco | Correcto |
| PM-04 | Una foto de 3000 × 2000 px se reduce a 1600 × 1067 antes de subirse | Correcto |
| PM-05 | La firma se dibuja con el mouse o el dedo y *Borrar* limpia el recuadro | Correcto |
| PM-06 | Pantalla de revisión del docente: foto y odontograma digital lado a lado en computadora, uno debajo del otro en teléfono, sin desplazamiento horizontal | Correcto |
| PM-07 | Sitio publicado: entrada de los tres roles, permisos y flujo de odontograma con foto presencial | Correcto |

Pendiente: probar en teléfonos reales (Android y iPhone), en particular la cámara y las fotos HEIC del iPhone.

## 5. Pruebas de aceptación (pendientes, actividad 6.4)
Con estudiantes y coordinación de la clínica:
1. Un estudiante registra un paciente real de práctica, completa la historia clínica, toma la firma, sube desde su teléfono la foto del odontograma presencial y llena el odontograma digital.
2. Un docente compara la foto con el odontograma digital, pide una corrección, la aprueba cuando se corrige y aprueba al paciente.
3. Se reporta una sala y Servicios la atiende.
4. Se aplica la misma encuesta de satisfacción (escala 1–5) para compararla con la línea base de la encuesta de requerimientos: **2.9 de 5**.

## 6. Registro de ejecución

| Fecha | Versión | Resultado |
|---|---|---|
| 2026-09-25 | Roles, odontograma con foto, avisos de salas, archivo, bitácora y respaldos | 31 de 31 casos automáticos correctos; PM-01 a PM-06 correctos |
| 2026-09-25 | Odontograma por sesiones: primero la foto presencial, después el digital; revisión del docente lado a lado | 31 de 31 casos automáticos correctos; PM-01 a PM-07 correctos |
