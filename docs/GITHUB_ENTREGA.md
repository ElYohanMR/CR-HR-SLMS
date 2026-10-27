# Actualizar SLMS desde GitHub Desktop

Revisión del 27 de octubre de 2026. Versión de entrega: 1.14.5.
Remoto existente: https://github.com/ElYohanMR/CR-HR-SLMS, rama `main`.
No crear otro repositorio ni usar Publish repository para esta actualización.

## Subir los cambios del código

1. Abrir el repositorio **CR-HR-SLMS** en GitHub Desktop. Si no aparece, usar
   File > Add local repository y elegir la carpeta del proyecto.
2. Comprobar Current branch: **main**, y revisar la lista Changes.
3. Mantener seleccionados los cambios de esta entrega. El borrado de `assets/site.png`
   elimina el mapa anterior sin uso; la aplicación utiliza `assets/site-hd.jpg`.
4. En Summary escribir: **Preparar SLMS 1.14.5 para revisión de RH y TI**.
5. En Description escribir: **Mantenimiento automático por cortes, historial por
   fechas y diferencias, sincronización configurable, mejoras del mapa y guías actualizadas.**
6. Pulsar **Commit to main** y después **Push origin**. Si aparece Fetch origin,
   pulsarlo para comprobar el remoto. Si hay cambios remotos, revisarlos antes del envío.
7. Usar Repository > View on GitHub y comprobar el nuevo commit, README y versión 1.14.5.

## Programa compilado y documentos

GitHub Desktop sube los archivos versionados. El ejecutable y sus dependencias
se distribuyen como ZIP por el canal interno de Samtec, junto con los documentos
de uso y del servidor. No añadir el EXE, ZIP ni la carpeta AppData al repositorio.

La carpeta interna Documentos importantes contiene los dos WI, las dos presentaciones,
el inventario inicial, los contornos y las plantillas de empleados revisadas.
Los documentos son material para revisión de RH y TI, no una aprobación corporativa.

## Etiqueta y Release opcionales

Después de subir el commit, puede crearse una Release de evaluación con etiqueta
`v1.14.5`, dirigida a ese commit, y las notas de [RELEASE_1.14.5.md](RELEASE_1.14.5.md).
Seleccionar **This is a pre-release**. No reutilizar una etiqueta ya publicada.

Este repositorio es público y sus Releases también. No adjuntar allí material
interno como inventario, mapas de distribución, documentos corporativos o datos
de empleados. TI debe definir el canal y la visibilidad de la distribución binaria.
Cambiar la visibilidad del repositorio no es parte de esta preparación local.

## Material por destino

| Material | Destino |
| --- | --- |
| Código, migraciones, pruebas, recursos de la aplicación y guías Markdown | Repositorio |
| Plantilla CSV sin registros | Repositorio, carpeta templates |
| ZIP compilado, WI, presentaciones, inventario y contornos | Canal interno de Samtec |
| Empleados, asignaciones, fotografías, respaldos y secretos | Ubicación protegida definida por TI |

No se ha añadido una licencia nueva ni se han publicado cambios automáticamente.
La titularidad, los permisos y la aceptación operativa quedan a cargo de los responsables.

Referencia: [Confirmar y subir cambios con GitHub Desktop](https://docs.github.com/en/desktop/making-changes-in-a-branch/committing-and-reviewing-changes-to-your-project-in-github-desktop).
