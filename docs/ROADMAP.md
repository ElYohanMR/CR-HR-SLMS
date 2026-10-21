# Propuestas de evolución

Fecha: 20 de octubre de 2026. Base: SLMS 1.14.1.
Todas las iniciativas de este documento son **propuestas**, salvo lo descrito
expresamente como comportamiento actual. No constituyen funciones entregadas,
compromisos de fechas ni decisiones de arquitectura aprobadas.

## Etapa 1 — Entrega y operación bajo TI

- Definir responsable del servicio, servidor, DNS, HTTPS y puestos autorizados.
- Integrar supervisión del proceso, arranque tras reinicio y diagnóstico legible.
- Respaldos programados con copia externa, retención y restauración ensayada.
- Establecer recuperación de cuentas y transferencia del administrador inicial.
  Hoy esa identidad se fija al crear la base y no puede transferirse desde la UI.
- Certificados corporativos y proxy: añadir una configuración de confianza TLS
  administrada, validada y compatible con todos los puntos de conexión.
- Definir actualización de clientes/servidor, migraciones y recuperación anterior.

Aceptación: despliegue documentado reproducible, recuperación probada y piloto
con varios puestos, incluidos doble asignación, desconexión y reintentos.

## Etapa 2 — Microsoft y datos autorizados de HR

- Inicio con Microsoft Entra ID mediante navegador y permisos de aplicación.
- Relacionar identidades corporativas con permisos de SLMS de manera explícita.
- Microsoft Graph para envío delegado o buzón de servicio según decisión de TI.
- Bandeja de salida con estados y reintentos; distinguir aceptación del proveedor
  de entrega al destinatario. Una asignación no se revierte si falla el correo.
- Conciliación del padrón de HR por ID: mostrar altas, bajas y diferencias antes
  de aplicar; tratar archivos incompletos y reingresos sin borrar por ausencia.
- No inferir despido de una cuenta Microsoft deshabilitada. La fuente de situación
  laboral y su actualización deben acordarse con Recursos Humanos.

Aceptación: permisos mínimos verificados, sesión revocada, identidad incorrecta,
fallos de envío y conciliación parcial ensayados. Ver [MICROSOFT.md](MICROSOFT.md).

## Etapa 3 — Consola administrativa para TI

Objetivo: permitir al administrador inicial, previsiblemente bajo custodia de TI,
gestionar ampliamente los datos desde una interfaz administrativa dedicada.

- Vista de entidades y relaciones: empleados, edificios, planos, bloques,
  casilleros, asignaciones, revisiones y expedientes.
- Edición individual y masiva con filtros, vista previa y validación del lote.
- Importaciones que distingan crear, actualizar y corregir; informe de errores
  descargable y simulación antes de confirmar.
- Corrección documentada de registros: motivo, valores anteriores y posteriores,
  usuario y fecha. Reabrir expedientes solo mediante un flujo autorizado.
- Herramientas de archivo, restauración, retención, anonimización y eliminación
  sujetas a reglas acordadas con HR/TI y a integridad referencial.
- Separar funciones de TI, administración de RH, operación y consulta.
- Definir un procedimiento auditado para reemplazar al administrador inicial.

«Datos manipulables» significa operaciones controladas desde la aplicación.
No se propone habilitar SQL libre ni permitir borrar auditoría o relaciones sin
validación. Un editor genérico sin reglas podría dejar asignaciones incompatibles.
La eliminación definitiva actual solo admite inventario elegible, no constituye
esta consola ni una limpieza general de empleados.

Aceptación: operaciones masivas atómicas, límites de rol comprobados, historial
de corrección y recuperación ensayados antes de habilitar acciones destructivas.

## Etapa 4 — Ajustes completos y comodidad de uso

Separar preferencias personales, valores de la organización y configuración de TI.

| Categoría propuesta | Ejemplos | Responsable |
| --- | --- | --- |
| Apariencia y accesibilidad | Escala, contraste, tamaño de letra, movimiento reducido, teclado | Usuario |
| Tablas | Columnas visibles, anchos, orden, filtros y vistas guardadas | Usuario |
| Mapa | Fondo, vista inicial, tamaño de etiquetas y densidad visual | Usuario; geometría según permiso |
| Predeterminados | Bloques, numeración, rotación, turno y departamento | Usuario o RH según campo |
| Catálogos | Departamentos, turnos, motivos y encargados | Administración RH |
| Correo | Plantillas, firma y vista previa; remitentes autorizados | RH y TI |
| Operación | Reglas de asignación, revisiones y cierre de solicitudes | RH con TI |
| Conexión y seguridad | Servidor, certificados, identidad, sesiones y diagnósticos | TI |
| Mantenimiento | Respaldo, restauración, retención y actualizaciones | TI |

Agregar búsqueda de ajustes, ayuda junto al campo, vista previa, restablecimiento
por categoría y explicación de qué cambia solo para el usuario y qué afecta a
toda la organización. Aplicar permisos en el servidor, no solo ocultar controles.
Los predeterminados rellenan nuevas fichas sin sobrescribir registros anteriores.

Aceptación: RH y Recepción completan los flujos principales sin instrucciones
técnicas, con tamaños de pantalla distintos y navegación por teclado.

## Etapa 5 — Android primero

Crear un cliente móvil para consulta y tareas presenciales: localizar casillero,
leer QR/código, consultar asignación según permiso, registrar revisión física y
adjuntar evidencia a un corte. Definir primero quién usará el teléfono y qué
operaciones podrá ejecutar; no trasladar toda la administración a una pantalla pequeña.

- Consumir la API central; nunca conectar directamente el teléfono a PostgreSQL.
- Preparar contrato/versionado de API, paginación y compatibilidad entre clientes.
- Resolver autenticación corporativa y almacenamiento seguro de sesión.
- Adaptar cámara, compresión, permisos de fotos y eliminación de copias temporales.
- Rehacer la cola y caché móvil: DPAPI es de Windows y no se puede reutilizar.
- Mantener control de versiones y rechazo de conflictos; trabajar sin conexión
  no confirma asignaciones. Proteger el equipo perdido y los datos guardados.
- Elegir con TI desarrollo Android nativo o una base multiplataforma después de
  validar identidad, cámara, operación sin conexión y distribución corporativa.

Aceptación: piloto en dispositivos Android autorizados, roles y privacidad
verificados, sincronización con Windows y recuperación de red ensayadas.

## Etapa 6 — iOS posteriormente

Tras validar Android, adaptar y probar los flujos para iPhone/iPad. Reutilizar
contratos y reglas del servidor; revisar almacenamiento seguro, permisos, cámara,
restricciones de ejecución en segundo plano y distribución corporativa con TI.
Prever recursos de desarrollo y firma de Apple según el canal que se seleccione.
No se promete que la interfaz Python/Qt actual se convierta automáticamente.

Aceptación: mismos criterios de permisos, integridad y sincronización, con pruebas
específicas en iOS y documentación de distribución y soporte.

## Otras posibilidades a priorizar con los usuarios

- Informes de ocupación y disponibilidad por edificio, bloque y período.
- Folios legibles, fechas objetivo y seguimiento de solicitudes atrasadas.
- Etiquetas QR, constancias de entrega y exportaciones dirigidas a cada función.
- Campos configurables con tipos, límites y migraciones compatibles.
- Manuales y capacitación versionados en SharePoint, según control documental.

Registrar cada mejora como incidencia con necesidad, responsable, prioridad,
criterios de aceptación y estado. No fijar fechas hasta estimar dependencias.
