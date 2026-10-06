# Samtec Lockers · 1.2

Aplicación Windows con servicio central para recepción y Recursos Humanos.

La versión 1.2 agrega baja y liberación en una operación, devolución voluntaria, filtro de empleados activos/inactivos y avisos simulados con destinatario de HR configurable. Los casilleros devueltos requieren revisión física antes de volver a asignarse, salvo confirmación explícita de que están vacíos y utilizables.

La versión 1.1 incorpora la identidad visual de referencia de Samtec: logo, tipografía Montserrat, encabezado gris y acentos naranjas. Corrige el contraste de los formularios en Windows con modo oscuro. El asistente separa la conexión de la cuenta administradora y permite desplazarse en pantallas pequeñas.

## Abrir

En esta computadora, abre **Iniciar Samtec Lockers.cmd**. La distribución independiente se abre con **SamtecLockers.exe**; conserva su carpeta _internal junto al ejecutable.

El asistente inicial permite elegir PostgreSQL local, un servidor corporativo HTTPS o una demostración separada con datos ficticios.

Para tu base de desarrollo:

| Campo | Valor |
| --- | --- |
| Host PostgreSQL | 127.0.0.1 |
| Puerto | 5432 |
| Base | samtec_lockers_dev |
| Usuario PostgreSQL | slms_dev |
| Contraseña PostgreSQL | La creada en pgAdmin |
| Usuario de la aplicación | El nombre que elijas |
| Contraseña de la aplicación | Una nueva, de al menos 10 caracteres |

Las cuentas de la aplicación y las credenciales de PostgreSQL son independientes. El asistente crea el esquema mediante migraciones y prepara los dos edificios y el mapa inicial. Si ya existen administradores, conserva sus cuentas y datos. **Configurar conexion.cmd** vuelve a abrir el asistente.

## Funciones implementadas

- Resumen de ocupación y disponibilidad.
- Mapa con imagen original, zoom, desplazamiento, bloques móviles y rotación.
- Contornos editables mediante sus vértices; alta y eliminación de contornos.
- Planos interiores/exteriores, edificios y pisos configurables.
- Bloques con filas y columnas configurables; numeración consecutiva o individual.
- Verificación física de casilleros, individual o por bloque.
- Empleados, correo opcional, departamento, turno, estado y notas.
- Asignación, liberación y reasignación atómica con responsable y motivo.
- Historial de asignaciones y auditoría con valores anteriores y nuevos.
- Importación CSV con vista previa; exportación de empleados, inventario e historial.
- Cola local persistente y cifrada; reintentos, conflictos y separación por responsable.
- Cuentas de administración, operación y consulta.
- Respaldos PostgreSQL y SQLite.
- Registro de notificaciones de correo en modo simulado.

## Primera carga

1. Confirma los nombres y códigos en Administración → Edificios.
2. Revisa los contornos del mapa y agrega los bloques con sus números físicos.
3. Verifica en sitio qué casilleros están vacíos y utilizables.
4. Registra empleados o importa la plantilla CSV.
5. Asigna desde Inventario, Empleados o el bloque del mapa.
6. Comprueba la confirmación en Solicitudes.

E1/E2 y los contornos iniciales son aproximaciones por confirmar. No se generan 2000 casilleros supuestos. Los casilleros nuevos quedan **pendientes de verificar**: no tener un empleado registrado no demuestra que estén vacíos.

## Sin conexión

Se conserva la última información recibida y se muestra su fecha. Con una identidad previamente autenticada se pueden registrar solicitudes, que permanecen pendientes hasta ser aceptadas por el servidor.

Cada solicitud conserva su UUID, equipo, fecha local y versiones consultadas. El servidor verifica permisos, estado y disponibilidad, y registra la fecha de recepción. Reenviar una solicitud devuelve el resultado anterior. Un cambio incompatible genera un conflicto: no se sobrescribe automáticamente ni se da prioridad retroactiva al reloj de una computadora.

Después de ocho errores temporales consecutivos se requiere reintento manual. Los conflictos se resuelven revisando los registros actuales y creando una solicitud nueva. Las colas de instalaciones diferentes están separadas.

## Datos y desarrollo

Los datos locales se guardan bajo **%LOCALAPPDATA%/SamtecLockers/data**, fuera de OneDrive. La configuración privada, la sesión y el contenido de la cola usan Windows DPAPI, vinculado al usuario Windows. Las cuentas emplean PBKDF2 con sal individual; la base central impide asignaciones activas duplicadas.

- Python 3.13 de 64 bits.
- requirements.in: dependencias directas; requirements.txt: versiones fijadas.
- scripts/setup.ps1: prepara el entorno externo a OneDrive.
- slms/: interfaz, dominio, servidor y sincronización.
- migrations/: migraciones Alembic.
- tests/: pruebas de concurrencia, recuperación, permisos, mapa y respaldos.
- scripts/build.ps1: crea el ejecutable en %LOCALAPPDATA%/SamtecLockers/release.
- python -m slms: iniciar desde el entorno del proyecto.
- python -m pytest -q: ejecutar pruebas SQLite e interfaz.
- python tests/run_postgres.py: probar contra un clúster PostgreSQL temporal y separado.

## Alcance

Esta entrega permite pruebas funcionales y el levantamiento inicial. La conexión a tu base se termina en el asistente local. El correo permanece simulado y la autenticación utiliza cuentas propias. Microsoft Graph / Entra ID y el despliegue corporativo con HTTPS dependen de la infraestructura que TI suministre.

Regla inicial: un casillero vigente por empleado. Las dimensiones del bloque se fijan al crearlo; las posiciones, números y condiciones se editan sin cambiar la identidad de los casilleros. El historial presenta inicialmente los últimos 2000 eventos y permite cargar anteriores.

No se publican datos ni código automáticamente. El repositorio remoto se publicará privado al finalizar la revisión acordada. Consulta docs/OPERACION.md y docs/TI.md.
