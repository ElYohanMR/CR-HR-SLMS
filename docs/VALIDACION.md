# Validación de la entrega

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
