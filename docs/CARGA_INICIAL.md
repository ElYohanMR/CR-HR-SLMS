# Carga inicial del inventario y plantilla de empleados

La Release privada incluye la distribución creada por Yohan y extraída el
20/10/2026: **118 bloques, 1.416 casilleros, dos edificios y un plano**.
Se conserva la numeración de cuatro dígitos, posición interna, coordenadas y
rotación. No incluye empleados, cuentas de acceso, asignaciones, fotografías,
solicitudes ni secretos. Los casilleros importados quedan pendientes de verificar.

## 1. Preparar la base nueva

Configurar el servidor según [Despliegue TI](DESPLIEGUE_TI.md), en modo PostgreSQL
sin datos de demostración. Crear una cuenta administradora inicial propia de TI.
La instalación crea los edificios E1 y E2 y el plano `Campus · exteriores` con
la imagen del campus. Todavía no importar empleados ni crear bloques.

Los puestos usarán el mismo servidor. Esta carga se realiza una sola vez en la
base central, no una vez por laptop. No ejecutar sobre la base actual de Yohan.

## 2. Conservar los contornos actuales

El Excel conserva bloques y casilleros, pero no contornos ni imagen. La imagen
del ejecutable coincide con la actual; los contornos fueron ajustados después.
`SLMS_Contornos_2026-10-20.json` conserva esos ajustes sin información personal.

En el servidor, con el servicio iniciado y el entorno Python preparado mediante
`scripts/setup.ps1`, abrir PowerShell en la raíz del código. Colocar el JSON junto
a los otros archivos de entrega y ajustar la ruta del siguiente ejemplo:

```powershell
& "$env:LOCALAPPDATA\SamtecLockers\venvs\dev\Scripts\python.exe" .\scripts\import_initial_contours.py "C:\SLMS\Entrega\SLMS_Contornos_2026-10-20.json"
```

La utilidad solicita el usuario y la contraseña **de SLMS**, no de PostgreSQL,
y solo valida. No guarda la contraseña ni la muestra. Después de revisar la
validación, repetir agregando `--apply` al final para guardar los contornos.

Solo acepta conexión local en el servidor (`http://127.0.0.1:8765` por defecto),
administrador inicial y una base sin inventario ni empleados. Comprueba la imagen,
traduce los códigos de edificios a sus IDs de destino y utiliza la API normal,
con control de versión e historial. No requiere editar tablas directamente.
Si se cambia el puerto local, usar `--url http://127.0.0.1:PUERTO`.

## 3. Importar los bloques y casilleros

1. Entrar en SLMS con una cuenta administradora del servidor nuevo.
2. Abrir **Inventario → Más acciones → Importar bloques Excel / CSV**.
3. Elegir `SLMS_Inventario_Inicial_2026-10-20.xlsx`.
4. Revisar la vista previa y confirmar la importación.
5. Esperar confirmación en **Solicitudes**. Un registro pendiente aún no está aplicado.
6. Comprobar 118 bloques y 1.416 casilleros, sin empleados ni asignaciones.
7. Abrir el mapa, ajustar la vista y revisar bloques de ambos edificios.
8. Realizar verificación física antes de marcar casilleros como disponibles.

La hoja `Inventario` tiene una fila por casillero. Los campos `id_bloque` y
`version_bloque` están vacíos intencionalmente para crear registros nuevos.
No cambiar encabezados ni sustituir números por valores numéricos en Excel.
Fila 1 es arriba y columna 1 es la derecha. El archivo conserva cada posición
real guardada, sin volver a generar la numeración.

Si aparecen duplicados, comprobar que se seleccionó el servidor nuevo. No borrar
historial para forzar la carga. No reimportar esta semilla para editar registros:
exportar desde el servidor de destino y utilizar ese archivo con IDs y versiones.
La importación de inventario es atómica: un conflicto rechaza el conjunto.

## 4. Completar empleados

Abrir `SLMS_Plantilla_Empleados.xlsx`. La hoja **Empleados** está vacía y la hoja
**Guía de campos** indica cuáles datos completar. Los encabezados se mantienen
en el formato que reconoce SLMS.

| Campo | Requisito |
| --- | --- |
| ID (`employee_number`), nombre (`first_name`), primer apellido (`surname`) | Obligatorios |
| Segundo apellido, correo, departamento, turno y notas | Opcionales |

El ID es texto y no exige cinco dígitos; conservar sus ceros iniciales. El correo
debe ser válido si se completa. La guía de la hoja incluye límites de longitud.

1. Escribir una persona por fila, empezando en la fila 2, sin filas vacías intermedias.
2. Seleccionar **Empleados** y guardar una copia como **CSV UTF-8**.
3. En SLMS, usar **Empleados → Importar CSV** y revisar la vista previa.
4. Confirmar y revisar las altas en **Solicitudes**: cada persona se confirma por separado.

La versión 1.14.1 no importa empleados directamente desde XLSX. Se entrega también
`SLMS_Plantilla_Empleados.csv` vacío si se prefiere trabajar directamente con CSV.
Guardar el archivo solo con las filas completadas, sin filas vacías al final.
Importar de 1 a 1.000 personas nuevas por archivo. Los IDs duplicados se rechazan,
incluso si corresponden a empleados inactivos. Las altas se crean activas.
No se asignan casilleros ni se crean cuentas de acceso con esta plantilla.

## Alcance de los archivos

No son un respaldo completo. No trasladan historial, condición física, presencia
de candado, notas del casillero ni preferencias de cuentas. Esos datos se verifican
o configuran en la nueva instalación. El inventario inicial corresponde a la fecha
de extracción; cambios posteriores deben exportarse de nuevo.

El Excel de bloques, el JSON y las plantillas vacías pueden acompañar la Release
**privada** de esta entrega. Una plantilla completada con empleados debe circular
por el canal interno autorizado, no añadirse al repositorio ni a la Release.
