# Publicar el proyecto privado y entregarlo a TI

Guía para Yohan. Preparada el 20 de octubre de 2026.
El proyecto ya tiene un repositorio Git local y rama `main`. No crear una carpeta
nueva dentro del proyecto ni volver a inicializarlo. Esta guía no publica nada por sí sola.

## 1. Abrir el proyecto en GitHub Desktop

1. Abrir GitHub Desktop e iniciar sesión con la cuenta deseada.
2. Elegir **File → Add local repository → Choose**.
3. Seleccionar la carpeta actual de `CR-HR-SLMS-Samtec_Locker_Management_System`.
4. Pulsar **Add repository** y comprobar que no sea otro proyecto, como TEC-App.
5. Revisar Changes. Si hay cambios propios pendientes, revisarlos y crear el commit
   antes de publicar. No incluir bases, credenciales, listas de empleados o respaldos.

## 2. Crear el remoto privado

1. Pulsar **Publish repository**.
2. Nombre sugerido: `CR-HR-SLMS`.
3. Descripción: `Sistema de gestión de casilleros para Recursos Humanos y Recepción. Versión para revisión de TI y piloto controlado.`
4. Mantener marcada **Keep this code private**.
5. Propietario: cuenta personal si la entrega empieza allí; organización de la
   empresa si TI proporciona una y concede permiso para crear el repositorio.
6. Pulsar **Publish repository**.
7. Elegir **Repository → View on GitHub** y comprobar la etiqueta **Private**,
   el README nuevo, la rama `main` y los documentos de `docs/`.

No crear otro repositorio vacío desde la web si se sigue este recorrido de Desktop.
Si ya existe un remoto, comprobar primero su dirección y propietario antes de cambiarlo.

## 3. Invitar a TI

1. Pedir los nombres de usuario GitHub de los revisores.
2. En GitHub: **Settings → Collaborators → Add people** (el nombre varía en organizaciones).
3. Seleccionar las cuentas correctas y enviar las invitaciones.
4. Esperar a que las acepten y comprobar que pueden abrir el repositorio.
5. Compartir entonces el enlace mediante el correo interno.

Un repositorio privado no es «accesible a cualquiera con el enlace». Requiere
cuenta autorizada. En un repositorio privado personal, los colaboradores tienen
acceso de escritura; para equipos con roles de lectura y administración separados,
conviene la organización que TI determine. El enlace a Releases también es privado.

## 4. Crear la primera Release de evaluación

1. En la página del repositorio: **Releases → Draft a new release**.
2. Tag: `v1.14.1` si no existe. Target: el commit de entrega en `main`.
3. Título: `SLMS 1.14.1 — Evaluación de RH, Recepción y TI`.
4. Copiar el texto de [RELEASE_1.14.1.md](RELEASE_1.14.1.md).
5. Adjuntar desde la carpeta local de entrega preparada:
   - `Samtec-Lockers-Windows.zip`.
   - `Samtec-Lockers-Codigo.zip` (código del commit documentado).
   - `SLMS_Instruccion_de_trabajo.docx`.
   - `SLMS_Capacitacion_RH_Recepcion.pptx`.
   - `SLMS_Inventario_Inicial_2026-10-20.xlsx`.
   - `SLMS_Contornos_2026-10-20.json`.
   - `SLMS_Plantilla_Empleados.xlsx` y `SLMS_Plantilla_Empleados.csv`.
   - `00_LEER_PRIMERO.txt`.
   - `SHA256.json`.
   - `PROCEDENCIA.txt`.
6. Marcar **This is a pre-release** para identificar su etapa de evaluación.
7. Comprobar los adjuntos y pulsar **Publish release**, o Save draft para revisarla.

El binario sigue siendo 1.14.1: esta entrega añade documentación, archivos de carga inicial y una utilidad de
restauración de contornos para TI, sin modificar el ejecutable.
Las Releases permiten distribuir el programa sin añadir sus archivos generados
al historial Git. No adjuntar la base local ni la carpeta completa de AppData.

## 5. Qué va a cada lugar

| Material | Destino |
| --- | --- |
| Código, pruebas, migraciones, recursos y guías Markdown | Repositorio |
| EXE con _internal, dentro del ZIP | Release |
| WI y presentación editables | Release; copia aprobada en SharePoint si corresponde |
| Inventario inicial autorizado sin personas, contornos y plantillas vacías | Release privada; ver [Carga inicial](CARGA_INICIAL.md) |
| Listas de empleados, fotografías, asignaciones y backups | Canal interno de datos definido por TI |
| Contraseñas, claves, tokens y archivos connection.dat/session.dat | Gestor de secretos/perfil protegido; nunca GitHub |

`.gitignore` reduce inclusiones accidentales; no borra archivos ya versionados
ni elimina secretos de commits antiguos. Revisar también el historial antes del
primer envío. Los recursos corporativos del proyecto siguen siendo de acceso privado.
No añadir automáticamente una licencia MIT/Apache u otra licencia de código abierto.

## 6. Mantenimiento del repositorio

- Crear una rama por cambio y usar Pull Requests con revisión de TI.
- No modificar etiquetas de versiones entregadas; publicar una versión nueva.
- Registrar errores y mejoras con las plantillas de Issues.
- Configurar protección/revisión de `main` según las funciones del plan de GitHub.
- Revisar quién conserva propiedad y acceso; transferir a la organización de TI
  cuando se acuerde, conservando el historial y verificando el remoto de Desktop.
- El sitio web GitHub aloja el código: no ejecuta el servidor PostgreSQL/SLMS.

## Fuentes oficiales

- [Publicar con GitHub Desktop](https://docs.github.com/en/desktop/overview/creating-your-first-repository-using-github-desktop)
- [Invitar colaboradores](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/repository-access-and-collaboration/inviting-collaborators-to-a-personal-repository)
- [Permisos de repositorios personales](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/repository-access-and-collaboration/permission-levels-for-a-personal-account-repository)
- [Crear Releases](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository)
- [Archivos de Releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)
