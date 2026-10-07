# Validación de la entrega

## Versión 1.3 · 6 de octubre de 2026

- 51 pruebas pasan con SQLite. En PostgreSQL, 50 pasan en esquemas temporales; la prueba restante de respaldo/restauración pasa en un clúster temporal independiente. La cuenta de aplicación no tiene permiso para crear bases, por lo que esa prueba se trasladó al clúster de pruebas sin elevar sus permisos.
- Excel y CSV: creación de bloques 3 × 4, lectura/escritura preservando ceros iniciales, exportación/reimportación sin cambios, edición de posiciones y nombres conservando casilleros y asignaciones.
- Rechazo de filas incompletas, duplicadas, inconsistentes, coordenadas no finitas, dimensiones fraccionarias, numeración modificada, versiones antiguas y fórmulas de Excel.
- Importación atómica: un conflicto revierte todos los bloques y su auditoría; los reintentos no duplican bloques. Importación restringida a Administración.
- Interfaz: fila de 40 bloques sin solapamiento en la disposición probada, consulta con un clic, acceso a la lista de asignaciones vigentes, códigos de color verde/rojo/ámbar y movimiento conservando coordenadas normalizadas.
- Imagen 3956 × 2478 conservando proporciones. Realineación del plano existente mediante 1738 correspondencias visuales entre imágenes; respaldo cifrado local previo de contornos y posiciones. No se añadieron bloques ficticios al inventario real.
- Revisión visual con 40 bloques ficticios: textos escalados sin perder dígitos; vista de consulta e inventario sin recortes. Las etiquetas cercanas requieren acercar el mapa para leerlas.
- Ejecutable verificado en un perfil aislado: interfaz, servidor, autenticación, importación Excel, actualización de posiciones, idempotencia y avisos simulados.

No cambió el esquema de base de datos. El plano existente se actualizó con auditoría, conservando empleados, casilleros y asignaciones. Los demás datos de pruebas se mantuvieron en entornos temporales.

## Versión 1.2 · 6 de octubre de 2026

- 36 pruebas verificadas en SQLite y PostgreSQL, utilizando bases temporales.
- Baja por despido, renuncia, fin de contrato u otra causa, con cierre atómico de asignación e historial.
- Baja sin casillero, datos desactualizados, operaciones simultáneas y reintento tras pérdida de respuesta.
- Devolución voluntaria manteniendo al empleado activo; disponibilidad condicionada a revisión física.
- Avisos simulados a HR y al empleado, copias opcionales, correos ausentes y destinatarios repetidos.
- Los motivos internos no aparecen en los avisos; solo Administración puede cambiar el destinatario de HR.
- Migración desde el esquema anterior conservando empleados, asignaciones y notificaciones.
- Revisión visual de los formularios de baja, devolución y configuración de avisos.
- Ejecutable independiente verificado: interfaz, servidor, autenticación, baja atómica y aviso simulado único a HR incluso al repetir la solicitud.

Validación realizada en Windows 11 Pro de 64 bits, Python 3.13.15 y PostgreSQL 18.

## Resultados

- 20 pruebas pasaron con SQLite y la interfaz Qt.
- Las mismas 20 pruebas pasaron contra PostgreSQL en un clúster temporal independiente.
- Revisión estática de slms, migraciones y tests: sin errores.
- Prueba del ejecutable independiente: interfaz, migraciones, configuración cifrada, servidor HTTP, autenticación e inventario correctos.
- Revisión visual de las pantallas de resumen, mapa e inventario del ejecutable.

## Casos cubiertos

- Dos solicitudes concurrentes para el mismo casillero o empleado: una única asignación vigente.
- Pérdida de respuesta después de confirmar: reenvío con el mismo UUID sin duplicar efectos.
- Reutilización de UUID con otro contenido: rechazada.
- Reasignación fallida: conserva la asignación original completa.
- Liberación, bajas con asignaciones activas y versiones desactualizadas.
- Casilleros pendientes de verificar: no disponibles para asignación.
- Verificación por bloque: todos los cambios o ninguno.
- Permisos de consulta y rechazo de peticiones sin autenticar.
- Persistencia cifrada de cola y configuración, sesiones vencidas y dependencias de solicitudes.
- Separación de colas por responsable e instalación.
- Coordenadas y contornos: persistencia y rechazo de geometría inválida.
- 2000 casilleros: carga de inventario, mapa y filtrado de disponibilidad.
- Respaldos y restauración comprobada en SQLite y PostgreSQL.
- Protección de las exportaciones CSV frente a fórmulas en campos de texto.
- El asistente no sobrescribe administradores existentes.

Las pruebas utilizaron información ficticia. No se conectaron mediante credenciales extraídas de pgAdmin ni modificaron la base de desarrollo del usuario. Esa conexión se configura localmente en el asistente.

La dependencia Starlette emite una advertencia de deprecación sobre su cliente HTTP de pruebas; no afecta estos resultados. Las versiones quedan fijadas en requirements.txt.

La distribución inicial tuvo una incompatibilidad de DLL detectada durante la prueba. Se corrigió excluyendo del entorno de empaquetado bibliotecas ajenas procedentes del runtime de herramientas. Se reconstruyó y se volvió a verificar el ejecutable corregido.

## Actualización visual 1.1 · 30 de septiembre de 2026

- Tema compartido inspirado en samtec.com, con fuente y logotipo incluidos localmente.
- Paleta explícita para evitar texto blanco sobre fondos claros cuando Windows usa modo oscuro.
- Secciones de conexión y cuenta en el asistente; desplazamiento vertical en pantallas pequeñas.
- Revisión visual del asistente, acceso, resumen, mapa e inventario.
- Prueba de regresión con paleta oscura y cambio entre los tres tipos de conexión.
- Las 21 pruebas de la suite local pasan. Las 20 pruebas de PostgreSQL de la versión inicial se conservan; esta actualización no cambia el esquema ni la lógica de asignaciones.
