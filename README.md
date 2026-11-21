# StockAula · Inventario universitario

**Versión candidata** `v0.3.0-rc.1` · APF3, semana 15, modalidad individual. Responsable académico: Leonardo Josue Minaya Ormeño. Curso: Herramientas de Desarrollo.

StockAula registra materiales, entradas y salidas para un almacén universitario. El catálogo permite buscar por nombre o código y filtrar materiales en reposición (saldo menor o igual al mínimo). El panel muestra productos, unidades, alertas y movimientos. El historial consulta los últimos 100 movimientos.

## Ejecutar en tu equipo

Requisitos: Python 3.10 o posterior y Git. Para los dos contratos del pipeline se usan Python 3.12 y Node.js 24. El programa usa bibliotecas estándar.

1. Abre una terminal en la carpeta con este README. Comprueba `python --version`.
2. Ejecuta `python app.py`. En macOS/Linux puedes usar `python3`. En Windows también funciona `py app.py`.
3. Entra a <http://127.0.0.1:8000>. Pulsa **Nuevo material** y registra código, nombre, categoría y mínimo. Usa **Registrar movimiento** para ingresar o retirar unidades.
4. Finaliza con Ctrl+C. La base de datos se guarda en `data/stockaula-apf3.sqlite3`. Si el puerto está ocupado, usa `python app.py --port 8080` y abre ese puerto.

La base local nace vacía. El código crea el esquema, registra cada migración aplicada y conserva los datos al reiniciar. Usa archivos de esta candidata. La compatibilidad con una base privada del APF2 no se ha contrastado. La versión web utiliza un almacén D1 independiente.

## Demostración y pruebas

- `python scripts/demostrar.py` ejecuta SA-01 sobre una base temporal. Muestra alta, entrada de 20, salida de 6, reenvío y saldo final de 14.
- `python -m unittest discover -s tests -v` ejecuta el contrato HTTP de Python.
- En un clon **Git**, `python scripts/ci.py` verifica sintaxis, construye el Worker y ejecuta la suite contra Python/SQLite y contra el Worker compilado con un adaptador local de SQLite. Los registros quedan en `runs/<identificador>/`.
- `git config core.hooksPath .githooks` activa la ejecución automática después de cada commit en equipos con Git y `python3`. Un fallo queda registrado. La publicación vuelve a validar la candidata y se detiene ante un fallo.
- `git log --all --oneline --graph --decorate` muestra la rama de corrección y su integración. `git show eed330a` abre el cambio de SA-01. `git show v0.3.0-rc.1:issues/SA-01.md` muestra el seguimiento.

## Integración y entrega

La configuración de GitHub Actions está en `.github/workflows/stockaula-apf3.yml`. Las propuestas, cambios en ramas configuradas y etiquetas ejecutan la validación y entregan la bitácora y el archivo de publicación. En un tag `v*` aceptado, el segundo trabajo adjunta ese paquete a una versión preliminar en GitHub Releases. Requiere que Actions esté habilitado y permiso de escritura para crear la release.

La publicación de clase usa un flujo semiautomatizado en ChatGPT Sites. Sobre el commit candidato se ejecuta `python3 scripts/ci.py --event cd-candidata`. Solo tras salida 0 se empaquetan el Worker, el manifiesto y las migraciones. Sites sincroniza la fuente Git, aplica el esquema D1 y publica el artefacto con confirmación del operador. El recibo del proveedor y sus identificadores se conservan en la rama `evidencias/apf3` de la copia entregada.

Entorno de prueba privado: <https://stockaula-inventario.melizadasme960886.chatgpt.site>. Usa la cuenta propietaria durante la sustentación. Los registros de ejemplo son académicos. La instancia local se sirve en la interfaz de bucle local; el acceso a la instancia de nube se controla con la cuenta de Sites.

## Incidencias y evidencia

| Ruta | Contenido |
| --- | --- |
| `issues/registro.csv` | Estado, responsable, prioridad y resultado por incidencia. La rama de evidencias consigna el estado posterior al despliegue. |
| `issues/SA-01.md` | Reproducción, criterios de aceptación, cambio y cierre. |
| `evidence/ci/` | Bitácoras reales, incluyendo el fallo que motivó la corrección. Los registros completos de candidatas y publicación están en la rama de evidencias. |
| `evidence/sa-01-demo.txt` | Salida de la demostración repetible. |
| `app.py` / `cloud/worker.mjs` | Servidor local y adaptador para el entorno de nube. |
| `model/sql.json` / `drizzle/` | Consultas compartidas y migraciones SQLite/D1. |
| `static/` / `tests/` | Interfaz y suite de contrato común. |

## Continuidad con el APF2

Esta implementación reproduce el alcance funcional descrito en el APF1/APF2 de StockAula y añade control de reenvíos. El repositorio académico consignado en el avance anterior es <https://github.com/muramasanw1214-arch/stockaula-apf2>. Su código e historial anterior no pudieron recuperarse con el acceso disponible. La historia de esta candidata comienza en la reconstrucción, sin atribuir los commits anteriores a esta copia. Los cambios de esta entrega constan en el repositorio Git de despliegue y en el historial portátil entregado.

Antes de integrar al remoto académico, conservar su historial, crear una rama a partir de su main vigente y revisar las diferencias y el esquema del APF2. La ejecución de GitHub Actions en ese remoto queda pendiente de acceso. Las bitácoras entregadas corresponden al ejecutor Git local. La etapa final del curso incluye el empaquetado en contenedor.
