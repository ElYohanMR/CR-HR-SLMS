# Investigación de referencias para Samtec Lockers

Fecha: 8 de octubre de 2026. Base comparada: Samtec Lockers 1.7.1.

Se revisaron repositorios públicos, documentación de sus autores y fragmentos de código publicados. No se instalaron ni se probaron estos sistemas. Las funciones descritas como existentes pertenecen a sus fuentes; las adaptaciones y prioridades son propuestas para Samtec Lockers, todavía sin implementar.

## Referencias seleccionadas

| Proyecto | Evidencia revisada | Utilidad para Samtec |
| --- | --- | --- |
| [MIS-Projects-2025/LMS](https://github.com/MIS-Projects-2025/LMS) | Sistema de lockers de empleados; documenta transferencias, Excel, historial, acceso corporativo y actualización de estado desde HR. | Es la referencia funcional más cercana. Adaptar la conciliación con el padrón de empleados. [Arquitectura](https://github.com/MIS-Projects-2025/LMS/blob/main/docs/ARCHITECTURE.md). |
| [Snipe-IT](https://github.com/grokability/snipe-it) | Gestión de activos asignados a personas. Su documentación incluye etiquetas, aceptación, campos configurables y avisos de revisión. | Referencia para seguimiento, entrega y revisión física del casillero. |
| [Seatsurfing](https://github.com/seatsurfing/seatsurfing) | Planos, colocación de espacios mediante arrastre, filtros, atributos y estadísticas de utilización. | Referencia visual para organizar edificios, planos y disponibilidad. [Funciones oficiales](https://seatsurfing.io/docs/features/). |
| [AnyLock-LS](https://github.com/Dmitri-2/AnyLock-LS) | Gestión de alquiler de lockers y confirmación presencial de una solicitud por un administrador. Proyecto originado en un equipo universitario en 2020. | Separar la solicitud de uso de la entrega física. La antigüedad de origen no prueba por sí sola el estado actual de mantenimiento. |

Snipe-IT declara desarrollo activo. No se hizo una auditoría de seguridad o mantenimiento de los cuatro repositorios. Las licencias mostradas en sus repositorios son AGPL-3.0 para Snipe-IT, GPL-3.0 para Seatsurfing y MIT para AnyLock. No se identificó una licencia en la portada revisada de LMS. Esta investigación propone funcionalidades propias, sin incorporar código externo.

## Lo que nuestra aplicación ya cubre

Mapa por planos, bloques con filas y columnas, asignaciones y devoluciones, baja de empleados, historial de cambios, roles, eliminación recuperable, importación/exportación de inventario, estados de revisión física y una cola local de solicitudes. Los avisos de correo siguen siendo simulados. Hay una estructura `extra` en empleados, pero aún no un editor de campos adicionales para HR.

Por ello, volver a añadir funciones genéricas de inventario aportaría menos que mejorar los flujos cotidianos y las revisiones.

## Mejoras propuestas, por prioridad

### 1. Editor para registrar filas completas de bloques

Prioridad alta; esfuerzo estimado medio. Propuesta propia adaptada a los hasta 40 bloques alineados mencionados por el usuario, inspirada en la edición visual de Seatsurfing.

- Marcar inicio y final de una fila en la pared; indicar cantidad de bloques y nombres iniciales.
- Generar una vista previa con separación uniforme y numeración editable antes de guardar.
- Seleccionar varios bloques para alinear, distribuir o girar; bloquear posiciones verificadas.
- Deshacer movimientos todavía no enviados. Los cambios ya confirmados tendrían una nueva operación auditada, no una desaparición del historial.

Criterio de aceptación: poder preparar 40 bloques sin colocarlos individualmente; detectar números repetidos y conservar el tamaño fijo de las etiquetas al acercar, crear o sincronizar.

### 2. Recorrido de verificación física

Prioridad alta; esfuerzo medio. Snipe-IT contempla intervalos y avisos de auditoría; nuestra adaptación sería una lista por edificio, lado y bloque, con fecha, responsable y resultado de cada revisión. [Documentación de avisos](https://snipe-it.readme.io/docs/notifications).

Separar claramente “está asignado según el sistema” de “se revisó físicamente”. Registrar vacío confirmado, ocupación sin identificar, daño o datos que no coinciden. La revisión de un casillero ocupado no debe liberarlo automáticamente. Mostrar pendientes y próxima revisión según una periodicidad definida por HR.

Criterio de aceptación: completar una inspección por etapas, retomarla después y exportar sus discrepancias sin modificar asignaciones por inferencia.

### 3. Resolución de conflictos comprensible

Prioridad alta; esfuerzo medio. Ya existe control de versiones y rechazo de conflictos; falta una pantalla cómoda para resolverlos.

Mostrar “lo que solicitaste” frente a “lo que está confirmado ahora”, con empleado, casillero, responsable y fecha. Ofrecer actualizar la vista, elegir otro casillero o preparar una nueva solicitud. Mantener el resultado original en el historial.

La documentación de [conflictos de PouchDB](https://pouchdb.com/guides/conflicts.html) sirve como referencia conceptual para presentar versiones alternativas. No se propone sustituir PostgreSQL por PouchDB ni aplicar automáticamente la última escritura. Dos solicitudes sin conexión no pueden confirmar el mismo casillero; el reloj del equipo no decide la asignación.

Criterio de aceptación: dos equipos solicitan el mismo casillero; solo una asignación se confirma y la otra persona recibe una explicación con opciones válidas.

### 4. Conciliación del personal con HR

Prioridad media-alta; esfuerzo medio, dependiente de la fuente disponible. Inspiración: sincronización de estado de empleados documentada por LMS.

Primera etapa: cargar una lista autorizada de HR y previsualizar cambios, empleados nuevos y personas inactivas con casillero. Identificar por ID conservado como texto; no por coincidencia de nombres. La ausencia en un archivo parcial no implica una baja. Una baja confirmada debe conservar la revisión física antes de volver a ofrecer el casillero.

Segunda etapa: una integración de lectura con el servicio que TI indique. Mantener separadas la cuenta administradora del programa y la ficha del empleado.

Criterio de aceptación: un cambio de nombre conserva el empleado y su historial; un archivo incompleto no ocasiona bajas masivas.

### 5. Etiquetas y acceso por escaneo

Prioridad media; esfuerzo bajo-medio para etiquetas, mayor para acceso móvil. Snipe-IT permite etiquetas con QR y código de barras. [Etiquetas oficiales](https://snipe-it.readme.io/docs/asset-labels).

Propuesta: imprimir código de bloque/casillero y un identificador escaneable. Un lector conectado a recepción puede introducir el identificador en el buscador. Para abrir una ficha desde el teléfono mediante QR haría falta una vista móvil autenticada y una dirección accesible en la red; la aplicación de escritorio actual no proporciona esa página.

El identificador impreso debe seguir siendo válido si cambia el ocupante. Los nombres y correos del empleado se consultarían dentro del sistema, no en la etiqueta pública.

### 6. Entrega física y constancia de asignación

Prioridad media; esfuerzo medio. AnyLock distingue solicitud y confirmación presencial; Snipe-IT permite aceptación de entrega. [Aceptación de activos](https://snipe-it.readme.io/docs/requiring-acceptance).

Propuesta: fecha y responsable de entrega, constancia imprimible y confirmación de recepción según el procedimiento que HR defina. Una solicitud técnica pendiente de sincronización, una reserva de casillero y una entrega física son estados diferentes. Si se incorporan reservas, deben tener vencimiento y reglas para que no bloqueen espacios indefinidamente.

### 7. Campos configurables y vistas guardadas

Prioridad posterior; esfuerzo medio. Snipe-IT documenta campos adicionales con tipos, validación y conjuntos de campos. [Campos configurables](https://snipe-it.readme.io/docs/custom-fields).

Aprovechar la extensión prevista en empleados para añadir campos definidos por HR sin multiplicar columnas específicas innecesariamente. Incluir tipo, obligatoriedad y visibilidad. Complementar con filtros guardados, selección de columnas y vistas como “T3 · pendientes de entrega”.

## Decisiones para nuestro proyecto

La propuesta es mantener la arquitectura actual y desarrollar primero el editor de filas de bloques, el recorrido de verificación y la pantalla de conflictos. Las demás mejoras pueden planificarse según el uso de recepción y los servicios que aporte TI.

El plano y sus marcadores de disponibilidad ya son una buena base; la mejora concreta es acelerar su edición. Las estadísticas futuras deberían distinguir porcentaje asignado de uso físico real, porque el sistema no sabe si una persona utiliza diariamente su casillero.

La documentación consultada no demuestra que los cuatro productos resuelvan exactamente nuestra cola offline entre equipos Windows y PostgreSQL. Una PWA instalable no prueba que confirme asignaciones correctamente sin conexión. Mantener nuestras pruebas de concurrencia e idempotencia como requisito de cualquier incorporación.

Como criterio propio, conservar cuentas individuales y eliminación recuperable. La documentación de LMS describe una contraseña compartida de confirmación y eliminación irreversible; esos mecanismos no son mejoras para el historial y la responsabilidad individual que ya implementamos.

## Alcance de esta entrega

Se entregan hallazgos y propuestas. No se ha cambiado el funcionamiento de Samtec Lockers, instalado productos externos, enviado información de empleados a demos ni conectado servicios corporativos.
