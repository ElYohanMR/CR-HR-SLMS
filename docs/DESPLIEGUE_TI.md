# Instalación del servidor, clientes y rutas

Base revisada: 1.14.1. Fecha de esta guía: 20 de octubre de 2026.
Los nombres de equipos, carpetas y dominio que siguen son ejemplos. TI debe
sustituirlos y registrar los valores reales en su inventario de infraestructura.

## 1. Decisiones previas

| Dato | Ejemplo / decisión |
| --- | --- |
| Equipo del servicio | Windows administrado por TI |
| Carpeta de distribución | `C:\Apps\SLMS\1.14.1\SamtecLockers` |
| Perfil Windows del servicio | Cuenta dedicada definida por TI |
| Base de piloto | `samtec_lockers_piloto` |
| Cuenta PostgreSQL | `slms_piloto` con propiedad del esquema para migraciones |
| URL para los clientes | `https://slms.example.internal` (ejemplo, no dirección activa) |
| Administrador inicial SLMS | Cuenta local de recuperación bajo custodia de TI |
| Usuarios de operación | Cuentas individuales de RH y Recepción |
| Respaldo / retención / recuperación | Definir ubicación externa, frecuencia y responsables |

El servidor actual depende de Windows DPAPI. No asumir que se puede trasladar
a Linux, Docker o una cuenta LocalSystem sin adaptar la gestión de secretos.
No se proporciona instalador MSI, servicio nativo ni despliegue automatizado.

## 2. Instalar el servidor

1. Preparar PostgreSQL; la referencia probada del proyecto es PostgreSQL 18.
2. Crear una base vacía de piloto y su rol propietario. Introducir su contraseña
   mediante las herramientas de TI; nunca guardarla en Git, scripts o ejemplos.
3. Extraer `Samtec-Lockers-Windows.zip` completo. No separar `_internal` del EXE.
4. Bajo la cuenta Windows que ejecutará el servicio, abrir `SamtecLockers.exe`.
5. Elegir **Servidor local · PostgreSQL**. Introducir host de PostgreSQL, puerto
   (habitualmente 5432), base, usuario y contraseña. Crear la cuenta administradora
   inicial de SLMS con una contraseña propia de al menos 10 caracteres.
6. El asistente ejecuta migraciones y configura edificios y plano iniciales.
   No importa el inventario operativo del autor. Si la base ya tiene cuentas,
   conserva las existentes; el formulario no restablece su contraseña.
7. Comprobar `http://127.0.0.1:8765/health` en el servidor. Debe devolver
   `app: samtec-lockers`, versión e identificador de instalación.

PostgreSQL puede estar en otro servidor: ese host se configura en el asistente
del servicio. Los puestos de RH/Recepción solo hablan con la API de SLMS.

## 3. Mantener activo el servicio

El lanzador inicia el servidor local cuando es necesario y lo deja activo al
cerrar la ventana. Antes de instalar una tarea o supervisor, identificar y detener
esa instancia concreta para no abrir dos servicios sobre el mismo puerto.

Comando para el supervisor de TI (ruta de ejemplo):

```powershell
& 'C:\Apps\SLMS\1.14.1\SamtecLockers\SamtecLockers.exe' --server
```

Puede supervisarse con un mecanismo de ejecución de procesos aprobado por TI,
como una tarea programada configurada para reiniciar ante fallos. El EXE no es un
servicio Windows registrable directamente con `sc create`. Usar la misma cuenta
Windows y el mismo perfil/ruta de datos que en el asistente; comprobar arranque
tras reiniciar, disponibilidad sin sesión interactiva y permisos de archivos.

Si se define `SLMS_HOME`, debe existir como variable del proceso tanto en el
asistente como en el servidor. Por defecto utiliza `%LOCALAPPDATA%\SamtecLockers\data`.
No copiar `connection.dat` desde otro usuario: está cifrado para su identidad Windows.

## 4. HTTPS y acceso de red

Mantener `127.0.0.1:8765` si el proxy y el servicio están en el mismo equipo.
Configurar un proxy inverso aprobado por TI con esta ruta:

```text
Cliente → https://nombre-aprobado:443 → http://127.0.0.1:8765 → PostgreSQL
```

El proxy debe conservar rutas, cabeceras de autorización y respuestas; admitir
peticiones hasta el límite de 9.000.000 bytes de la API, y limitar el acceso a las
redes previstas. No añadir un formulario de autenticación de navegador delante
de la API que el cliente de escritorio no pueda procesar.

**Confianza del certificado:** esta versión usa HTTPX con certifi y
`trust_env=False`. No incorpora una opción de CA corporativa ni adopta
automáticamente el almacén de certificados de Windows. Importar una CA en Windows
o definir `SSL_CERT_FILE` no basta para este cliente actual. TI debe usar una cadena
ya reconocida por el cliente o implementar y validar soporte explícito de CA/sistema
en todas las conexiones de la aplicación. No desactivar la verificación TLS.
Comprobar desde SLMS; que el navegador acepte el certificado no prueba que SLMS lo haga.
Referencia: [HTTPX y certificados](https://www.python-httpx.org/advanced/ssl/).

| Puerto | Exposición prevista |
| --- | --- |
| 443/TCP | Clientes hacia proxy HTTPS |
| 8765/TCP | API local del servicio, loopback si proxy está en el mismo host |
| 5432/TCP | Servicio SLMS hacia PostgreSQL; no abrirlo a los puestos por SLMS |
| 22/TCP | Solo laboratorio SSH o administración autorizada; no requerido por SLMS corporativo |

Para cambiar la escucha desde código, con el servidor detenido y el mismo usuario:

```powershell
# Ejecutar desde la raíz del repositorio y en el entorno preparado
$env:PYTHONPATH = (Get-Location).Path
& "$env:LOCALAPPDATA\SamtecLockers\venvs\dev\Scripts\python.exe" scripts/server-settings.py --bind 127.0.0.1 --port 8765
```

El comando modifica la configuración cifrada; no configura HTTPS ni firewall.
El asistente vuelve a los valores locales predeterminados al reconfigurar, por
lo que cualquier puerto personalizado debe revisarse después.

## 5. Instalar los puestos

1. Extraer la misma versión del ZIP en cada equipo Windows.
2. Abrir el EXE y seleccionar **Conectar a servidor de TI**.
3. Escribir la URL HTTPS aprobada, sin usuario, contraseña ni `/health` al final.
4. Iniciar sesión con una cuenta de SLMS creada por el administrador.
5. Crear un registro ficticio autorizado y comprobarlo desde otro puesto.

No se requiere Python, PostgreSQL ni pgAdmin en los puestos que usan el EXE.
No seleccionar Demostración en cada laptop si se desea compartir información.
Para cambiar conexión, usar `Configurar conexion.cmd` de la distribución.

## 6. Rutas y archivos de la instalación

| Ruta / archivo | Contenido y tratamiento |
| --- | --- |
| `%LOCALAPPDATA%\SamtecLockers\data` | Datos por usuario Windows; predeterminado |
| `SLMS_HOME` | Sustituye la ruta de datos; coherente entre asistente, servidor y proceso |
| `connection.dat` | Configuración cifrada; incluye secreto PostgreSQL solo en servidor |
| `session.dat` | Sesión de SLMS cifrada; no distribuir |
| `workstation-<huella>.sqlite3` | Caché y cola del puesto, preferencias y borradores cifrados |
| `demo-server.sqlite3` | Base del modo demostración, si se eligió |
| `backups\` | Respaldos centralizados generados por la aplicación; requiere copia externa |
| `application.log`, `server.log`, `server-console.log` | Diagnóstico local; revisar antes de compartir |
| `%LOCALAPPDATA%\SamtecLockers\venvs\dev` | Entorno de desarrollo creado por setup.ps1 |
| `%LOCALAPPDATA%\SamtecLockers\release\SamtecLockers` | Salida predeterminada de build.ps1 |

La identidad `installation` separa las colas. No editar manualmente estos archivos
ni sustituir una base mientras el servicio esté activo. El respaldo central no
incluye solicitudes aún pendientes en las laptops ni su configuración DPAPI.

## 7. Datos iniciales y migración del entorno actual

El inventario mapeado pertenece a la base local del autor. Acordar una de estas vías:

- Respaldo y restauración controlada para conservar identidades, relaciones y planos.
- Exportación/importación de inventario para una base nueva, adaptando los IDs a
  alta nueva según la plantilla. Configurar planos/contornos por separado cuando
  corresponda: la hoja de inventario no sustituye todo el respaldo.

Transferir datos por un canal interno separado de GitHub. Validar números únicos,
filas/columnas, posiciones, planos, cantidades y disponibilidad física. Importar
empleados con la plantilla CSV (1–1.000 nuevos por archivo) conserva los IDs como
texto; no usar la ausencia en un archivo para dar de baja automáticamente.

No publicar el administrador inicial ni su contraseña en el repositorio. Acordar
custodia y cambio de credenciales con TI; la transferencia de su identidad desde
la UI aún no existe. No usar los scripts de limpieza excepcional de un laboratorio
como procedimiento de operación.

## 8. Respaldo, actualización y recuperación

Seguir [TI.md](TI.md). El respaldo PostgreSQL usa `pg_dump --format=custom`.
Disponer de pg_dump en PATH o en `C:\Program Files\PostgreSQL\18\bin`.
TI define frecuencia, retención, copia externa y restauración periódica comprobada.

Antes de actualizar: sincronizar/revisar pendientes, respaldar, detener el proceso
anterior y cambiar la distribución. Arrancar y comprobar versión, migraciones y
clientes. Una migración aplicada no se revierte solo copiando un EXE anterior:
ensayar restauración en una base separada y reconciliar operaciones posteriores.

## 9. Laboratorio temporal mediante SSH

Un túnel SSH autenticado puede conectar una laptop cliente a un servicio local sin
modificar la aplicación. Solo para el laboratorio, con SSH ya configurado:

```powershell
ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -L 127.0.0.1:8877:127.0.0.1:8765 usuario_pruebas@IP_DEL_SERVIDOR
```

Verificar la huella del servidor SSH. Mantener el túnel abierto. En el cliente,
seleccionar Conectar a servidor de TI y usar `http://127.0.0.1:8877`.
No escribir la IP remota con HTTP en el asistente: solo permite HTTP en loopback.
Este mecanismo no es una integración con Microsoft ni el despliegue corporativo.
