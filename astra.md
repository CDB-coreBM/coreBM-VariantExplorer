# Revisión técnica y funcional de coreBM Variant Explorer

Fecha: **17 de octubre de 2026**. Revisión del árbol de trabajo local; referencia de `main`: `707531014fc4a0b2acfc22da2bb74cf11153a7f4`.

## 1. Dictamen y prioridades

El repositorio tiene una base útil para un explorador: separa varios parsers, dispone de una factoría Flask, utiliza consultas parametrizadas, incorpora índices, pagina las tablas principales y permite guardar hallazgos por caso. Sin embargo, **la implementación actual debe considerarse un prototipo, pendiente de corregir errores de integridad e interpretación antes de utilizar sus resultados en decisiones asistenciales**.

El problema principal no es el estilo del código. Hay recorridos que transforman información ausente en resultados normales, fabrican anotaciones clínicas, muestran pistas de otra muestra o exportan un informe distinto del que se ha curado. Para un genetista que no conoce la implementación, la presentación transmite un grado de certeza que los datos no sostienen.

Esta revisión propone cambios; no modifica la aplicación ni sus datos. No es una validación clínica del producto ni una certificación de cumplimiento. Las prioridades se asignan por el efecto posible sobre el paciente y la trazabilidad:

| Prioridad | Significado | Actuación |
|---|---|---|
| **P0** | Puede atribuir evidencia al paciente equivocado, inventar resultados, emitir una interpretación clínica injustificada o exponer información | Resolver antes de uso asistencial o exposición a una red compartida |
| **P1** | Puede perder hallazgos, alterar la interpretación o impedir un flujo clínico reproducible | Resolver antes de un piloto asistencial controlado |
| **P2** | Deuda de mantenimiento, rendimiento, operativa o usabilidad | Planificar tras estabilizar la integridad de los datos |

Los cambios más urgentes son:

1. Separar por completo demostraciones, benchmarks y muestras clínicas; eliminar datos clínicos inventados como valores de reserva.
2. Corregir fase, repeticiones y selección de pistas de IGV por muestra.
3. Hacer que pantalla, JSON e informe imprimible representen la misma versión curada.
4. Mostrar «no evaluado» o «dato no disponible» cuando corresponda, sin convertirlo en «normal».
5. Incorporar control de acceso, aislamiento por caso y acceso a archivos mediante un registro autorizado.

## 2. Alcance, método y límites

Se revisaron los módulos de aplicación, parsers, motores de interpretación, persistencia, rutas HTTP, JavaScript propio, plantillas, configuración de instalación, pruebas y material de ejemplo. El inventario comprende **20 módulos Python de aplicación, 9 archivos JavaScript propios, 11 plantillas HTML y 8 archivos de pruebas**. Los módulos Python de aplicación suman 6.089 líneas. Se comprobó además la sintaxis de 31 archivos Python, incluyendo pruebas y scripts.

Se siguieron los recorridos de carga → almacenamiento → tabla → detalle → informe. Se ejecutaron pruebas existentes y comprobaciones adicionales con datos sintéticos en SQLite temporal. La base incluida se inspeccionó en modo de solo lectura para obtener recuentos, sin volcar datos de pacientes. Contiene 2 casos, 28.307 SNV, 535 SV, 348 regiones de metilación, 10 registros de repeticiones y ninguna fila en `clinical_reports` o `case_report_findings`.

La suite se ejecutó con Python 3.10.7 y Flask 3.1.2 instalado en una carpeta temporal. `pysam` no estaba disponible. Se fijó `VARIANT_EXPLORER_DB` a una base temporal y se desactivó la escritura de bytecode. **La base original mantuvo su SHA-256**: `23efde90671745cd04bcd53c63324fde4f067d0f0d366937e90db803ef4a8535`.

No se hizo una prueba visual en navegador, una auditoría de dependencias completa, una prueba de carga WGS, una evaluación de la red hospitalaria ni una validación analítica con muestras clínicas. Los hallazgos de interfaz derivan del código y sus contratos HTTP; los de concurrencia del navegador se describen como riesgos pendientes de reproducir visualmente. No se auditó línea por línea el JavaScript minificado de terceros.

Git rechazó las consultas de estado por la propiedad del repositorio en este entorno. Se leyó la referencia de `main` directamente; no se cambió la configuración global de Git. Por ello, el hash identifica la referencia local y no certifica que todo el árbol de trabajo coincida con ese commit.

En las fichas se distingue:

- **Reproducido:** observado mediante ejecución aislada.
- **Estático:** verificable en el código, sin una prueba de extremo a extremo.
- **Propuesta:** capacidad necesaria o deseable cuyo diseño debe acordarse con el laboratorio.

## 3. Hallazgos críticos de integridad y seguridad

### H01 — P0 · Anotaciones clínicas fabricadas sobre variantes de benchmark

**Evidencia estática:** [sample_manager.py](variant_explorer/sample_manager.py), `ingest_sample`, líneas 373–403 y 442–505. La carga CMRG asigna patogenicidad por tamaño o por `rec.pos % 7`; calcula aminoácidos y posiciones proteicas con módulos de la coordenada; inventa frecuencias de población, profundidad, identificadores ClinVar, exones, conjuntos de fase y puntuaciones. Reutiliza un mismo transcrito para diferentes genes. Los registros se etiquetan como `GIAB_CMRG_TruthSet`.

**Impacto:** una llamada de variante de referencia puede ser real, pero su interpretación clínica añadida no lo es. Esos campos alimentan filtros, priorización, fase e informes como si fueran evidencia. Un benchmark de detección no valida automáticamente patogenicidad, acción terapéutica ni anotación funcional.

**Propuesta:** conservar los campos originales y su procedencia; dejar los no disponibles en `NULL`. Anotar consecuencias con una canalización reproducible y un ensamblaje/transcrito versionado. Incorporar `data_origin = clinical | benchmark | synthetic` y origen por anotación. Mover la generación de ejemplos a un comando explícito de demostración, con identificación visible y exportaciones marcadas.

**Aceptación:** ninguna anotación clínica depende de operaciones aritméticas sobre la posición; toda frecuencia, HGVS y clasificación permite reconstruir su fuente. La demostración no genera informes con apariencia de resultados clínicos.

### H02 — P0 · Consultar repeticiones crea diez resultados normales sin análisis

**Reproducido:** [app.py](variant_explorer/app.py), `get_tandem_repeats`, línea 1334. Un caso sin registros pasa de 0 a 10 filas en `tandem_repeats` mediante un simple `GET /api/repeats`. Se insertan tamaños constantes. No se encontró un parser ni una vía de ingesta real de TRGT/Straglr. La descarga del informe genera además HTT y C9orf72 con valores constantes, sin consultar esa tabla.

**Impacto:** abrir una pestaña puede crear resultados negativos de un ensayo no realizado. La persistencia hace que parezcan resultados previos legítimos.

**Propuesta:** hacer que GET sea de solo lectura. Implementar adaptadores explícitos para formatos y versiones de callers, con muestra, locus, alelos, unidades, calidad e incertidumbre. Si falta el ensayo, mostrar «Repeticiones no evaluadas». El informe debe consumir los resultados reales curados.

**Aceptación:** visitar un caso vacío no escribe filas; el informe distingue ensayo ausente, fallido y negativo válido.

### H03 — P0 · C9orf72 y loci no implementados pueden aparecer normales

**Reproducido:** [tandem_repeats.py](variant_explorer/tandem_repeats.py), líneas 28 y 83. La clave del catálogo es `C9orf72`, pero la búsqueda utiliza `gene.upper()`. `evaluate_repeat_allele('C9orf72', 4, 1000)` devuelve `Normal / Non-Expanded` y `Negative for Repeat Expansion`. ATXN2, ATXN3, CACNA1A y ATXN7 aparecen en la interfaz sin reglas correspondientes en el motor.

**Propuesta:** normalizar identificadores al cargar y consultar el catálogo. Un locus no soportado debe devolver `unsupported_locus`, nunca normalidad. Mantener un catálogo único para motor, interfaz y exportación, con su versión clínica y estados interpretables.

**Aceptación:** prueba de contrato para todos los loci anunciados; un gen desconocido no puede producir un resultado negativo. Las pruebas de límites deben partir de criterios clínicos aprobados, no copiar las constantes del código.

### H04 — P0 · Fase inferida incorrectamente y equiparada a diagnóstico

**Reproducido:** [snv_parser.py](variant_explorer/snv_parser.py), línea 73, asigna haplotipo también a `0/1` y `1/0`. [phasing_engine.py](variant_explorer/phasing_engine.py), línea 86, admite fase si hay dos haplotipos aunque los `PS` sean distintos o falten. Dos VUS de CFTR sin fase generaron `Pathogenic Biallelic Pair`; el caso con bloques distintos también se declaró en trans.

El motor tampoco exige heterocigosis diploide válida ni un mecanismo recesivo específico, y afirma «asymptomatic carrier» para configuraciones en cis. Trunca arbitrariamente a diez variantes por gen.

**Propuesta:** separar configuración alélica, confianza de fase e interpretación del caso. Para fase física, exigir compatibilidad de muestra, cromosoma y bloque, o evidencia explícita que conecte bloques. No deducir fase de `/`. Preservar no llamadas y ploidía. Una pareja en trans puede ser candidata; la conclusión depende de ambas variantes, mecanismo, fenotipo y revisión.

**Aceptación:** `0/1` no se transforma en fase; bloques independientes no se comparan automáticamente; dos VUS no se convierten en diagnóstico por su configuración. La semántica de `GT`/`PS` debe ajustarse a la [especificación VCF](https://samtools.github.io/hts-specs/VCFv4.3.pdf).

### H05 — P0 · IGV utiliza HG002 para cualquier caso

**Reproducido:** [app.py](variant_explorer/app.py), `get_igv_config`, línea 1009, devuelve configuraciones idénticas para dos casos distintos. Las pistas BAM, cobertura, variantes y metilación apuntan a `data_store/samples/HG002`. `query_wgs_vcf` también consulta un mapa fijo de archivos HG002, sin selección de muestra. Algunos archivos anunciados, como `HG002_phased.bam` y el VCF WGS, no están en esta copia.

**Impacto:** inspeccionar una variante de un paciente puede mostrar datos de una referencia. El usuario puede interpretar una pista ajena como confirmación experimental.

**Propuesta:** registro `sample_files` con caso, muestra, análisis, ensamblaje, tipo, índice, checksum y estado de disponibilidad. Construir las pistas desde ese registro. Añadir muestra y versión del análisis a cada pista; las comparaciones con referencias deben ser explícitas. Destruir o recargar IGV al cambiar de muestra.

**Aceptación:** dos casos con archivos distintos reciben pistas distintas; un caso sin BAM muestra «BAM no disponible»; ninguna ausencia se resuelve con HG002.

### H06 — P0 · El informe descargado no refleja los hallazgos curados

**Reproducido:** [report_builder.js](variant_explorer/static/js/report_builder.js) utiliza `case_report_findings`, pero [app.py](variant_explorer/app.py), `download_report`, línea 1403, vuelve a consultar las tablas completas. Guardar un hallazgo en un caso sin SNV originales produce una fila visible en el listado de hallazgos y cero SNV en el JSON exportado. Las notas y decisiones de inclusión/exclusión no gobiernan la descarga.

**Impacto:** el genetista revisa un documento y entrega otro. Se pueden omitir VUS pertinentes o incluir variantes que decidió excluir.

**Propuesta:** introducir una única representación de informe versionado. Pantalla, HTML y JSON deben consumir exactamente esa representación. Las sugerencias automáticas deben permanecer pendientes hasta la decisión de inclusión. Conservar en la versión emitida el contexto y la evidencia utilizados.

**Aceptación:** mismo conjunto de identificadores, interpretaciones y notas en pantalla y exportaciones, incluyendo SNV, SV, metilación y repeticiones. Cambiar el análisis posteriormente no altera una versión ya emitida.

### H07 — P0 · Pérdida de SV y metilación en el generador de informes

**Reproducido para SV; estático para los demás campos:** [report_generator.py](variant_explorer/report_generator.py), líneas 41, 49, 130 y 159. El generador espera `acmg_class`, `gene_symbol`, `length` y `support`, mientras la tabla SV almacena `acmg_sv_class`, `genes_affected`, `sv_len` y `support_reads`. Una SV persistida como `Pathogenic` produjo cero SV en la exportación.

En metilación espera `overall_methylation` y `hp1_methylation`, no `percent_modified` y `hp1_percent`; puede imprimir 0 % para una región positiva. El filtro textual puede omitir la hipometilación anómala producida por el parser. El JSON incluye repeticiones y hallazgos secundarios que el HTML no desarrolla en sus secciones.

**Propuesta:** modelos de transferencia tipados y adaptadores explícitos por modalidad; estados clínicos estructurados en lugar de búsquedas de palabras. Validar la representación completa antes de exportarla.

**Aceptación:** una muestra de prueba con una alteración de cada modalidad conserva todos sus valores y decisiones en HTML y JSON. Ausencia de campo nunca equivale a cero.

### H08 — P0 · Narrativa, datos personales y métricas de informe prefijados

**Evidencia estática y reproducción de valores de reserva:** [templates/views/clinical_report.html](variant_explorer/templates/views/clinical_report.html) contiene una conclusión fija sobre TP53, EGFR, MLH1 y MSH2, fecha `2026-09-10`, estado «Actionable Findings», nombre de informante y aprobación institucional. No hay código que actualice `repCommentary` o `reportDate`.

[report_generator.py](variant_explorer/report_generator.py), líneas 59–75, busca `sex`, `mean_coverage` y `read_n50`, pero el esquema utiliza `gender`, `mean_depth` y `n50`. La exportación de un caso nuevo inventó `Male (XY)`, 32,5×, N50 de 28.500 bp y N50 de fase de 14,2 Mb. También fija basecaller, referencia y callers. Fecha/hora local se rotula como UTC.

**Propuesta:** generar la narrativa desde la versión del informe y permitir edición clínica auditada. Usar valores reales o «no disponible». No inferir cariotipo de un sexo registrado. Emplear identificadores únicos y fechas con zona horaria. Los nombres y aprobaciones solo deben aparecer tras una acción de profesionales autenticados.

**Aceptación:** un caso vacío no contiene hallazgos, métricas, firmas ni aprobaciones inventadas; dos pacientes distintos no comparten una conclusión fija.

### H09 — P0 · Acceso sin autenticación a datos, modificaciones y archivos del proyecto

**Reproducido:** `GET /api/stream/files/README.md` devuelve el archivo con HTTP 200 y `Access-Control-Allow-Origin: *`. [app.py](variant_explorer/app.py), líneas 28 y 1290, permite transmitir cualquier archivo regular dentro del proyecto, no solo datos genómicos autorizados. La misma lógica incluye la base SQLite y archivos internos si se conoce su ruta. No se observan autenticación ni autorización en las rutas. [run_server.py](run_server.py) escucha por defecto en `0.0.0.0`.

Además, `requested_path.startswith(safe_base)` no es una comprobación de pertenencia a directorio: rutas hermanas con el mismo prefijo y enlaces requieren tratamiento adicional. Ese escape no se explotó; el acceso amplio dentro del proyecto ya está confirmado.

**Propuesta:** autenticación institucional, permisos por rol/caso y usuario real para cada modificación. Sustituir rutas libres por identificadores de archivos registrados, resolviendo rutas canónicas y pertenencia con semántica de directorios. Restringir CORS a los orígenes necesarios. Aplicar protección CSRF si se usan cookies y límites de acceso/carga. Para desarrollo, limitar escucha a localhost por defecto.

**Aceptación:** una petición no autenticada no lista pacientes ni descarga archivos; un usuario sin permiso no accede a otro caso; ni `.git`, ni SQLite, ni rutas fuera del almacén pueden servirse. Esto describe la aplicación: no se ha evaluado si existe protección externa en un despliegue real.

### H10 — P0 · Contenido de entrada interpolado como HTML/SVG

**Reproducido parcialmente:** `render_html_report` conserva una etiqueta HTML de prueba dentro del nombre del paciente. Hay interpolación directa mediante f-strings y numerosos `innerHTML` en [report_generator.py](variant_explorer/report_generator.py), [app.js](variant_explorer/static/js/app.js), [snv_table.js](variant_explorer/static/js/snv_table.js), [report_builder.js](variant_explorer/static/js/report_builder.js) y los generadores SVG. Escapar únicamente apóstrofos en `onclick` no protege el contexto HTML/JavaScript.

**Impacto:** campos importados o notas pueden alterar la presentación del informe y crear vías de XSS. Se confirmó la ausencia de escape, sin ejecutar código malicioso en un navegador.

**Propuesta:** Jinja con autoescape para informes, `textContent` y eventos registrados con `addEventListener` en la interfaz, y escape XML para SVG. Si se necesita texto enriquecido, permitir solo un subconjunto sanitizado. Añadir una política CSP como defensa adicional.

**Aceptación:** texto con `<`, `>`, comillas y saltos de línea se representa literalmente y no cambia la estructura del documento ni sus eventos.

## 4. Interpretación genómica y formatos

### H11 — P1 · VCF multialélico, múltiples muestras y anotaciones incompletas

**Reproducido:** [snv_parser.py](variant_explorer/snv_parser.py) toma siempre `parts[9]`, conserva todos los ALT en una cadena, utiliza `AD[1]` y selecciona solo la primera anotación CSQ. Una variante `A → G,T`, `GT=0/2`, `AD=10,0,20` terminó con VAF 0 y consecuencia `frameshift_variant`. `AF=.` genera `ValueError`. El comentario anuncia ANN/SnpEff, pero no existe un adaptador equivalente a CSQ.

**Propuesta:** parsing con una biblioteca VCF mantenida y una capa de normalización. Selección explícita de muestra; descomposición por alelo preservando `Number=A/R/G`; conservación de GT, AD, PL, PS, FILTER y campos originales. Guardar anotaciones por alelo y transcrito, con selección clínica explícita. Manejar haploides, no llamadas, alelos simbólicos y gVCF.

**Aceptación:** corpus de VCF de varios callers/versiones y dos muestras, con alelos múltiples y valores ausentes; cada resultado queda asociado a la muestra y al alelo correctos. La [especificación VCF](https://samtools.github.io/hts-specs/VCFv4.3.pdf) debe ser el contrato de referencia.

### H12 — P0 · Ausencia de anotación interpretada como rareza o efecto funcional

**Reproducido:** el parser convierte una SNV sin consecuencia anotada en missense, cualquier cambio de longitud en frameshift y una frecuencia no suministrada en `0.0`. Con profundidad suficiente añade `PM2_Supp`. [snv_table.js](variant_explorer/static/js/snv_table.js), línea 103, muestra ese cero como variante nueva/no observada en gnomAD.

**Propuesta:** distinguir `not_annotated`, `not_found`, `not_callable` y frecuencia observada igual a cero. Usar `NULL` para evidencia ausente; no asignar consecuencia por longitud sin contexto transcripcional. Para frecuencia, conservar versión, población, AC, AN, cobertura y filtros de la fuente.

**Aceptación:** un VCF sin anotación no genera PM2 ni efecto codificante por defecto. «No anotada» no se presenta como «ausente en población». Esta distinción afecta tanto a reglas como a filtros y colores.

### H13 — P1 · Dos motores ACMG con contratos y resultados diferentes

**Reproducido:** la ingesta usa [acmg_classifier.py](variant_explorer/acmg_classifier.py); el detalle usa [acmg_engine.py](variant_explorer/acmg_engine.py). Este último busca `revel_score` y `splice_ai`, mientras SQLite guarda `revel` y `spliceai_ds_max`. En una prueba, la ingesta produjo `PP3,PM1` y la ruta de evidencia no produjo criterios. `classify` tampoco pasa `exon` a `evaluate_pvs1`.

**Propuesta:** un servicio de interpretación, un esquema de entrada y una versión de reglas. La evidencia mostrada debe ser la que produjo la clasificación persistida, no una segunda evaluación implícita. La reevaluación debe crear una versión nueva con comparación de cambios.

**Aceptación:** tabla, detalle e informe muestran la misma clasificación y criterios para la misma versión; la actualización del motor no reescribe silenciosamente decisiones previas.

### H14 — P0 · Reglas germinales insuficientes para la certeza que declaran

**Evidencia estática:** [acmg_classifier.py](variant_explorer/acmg_classifier.py), líneas 35–72, concede PVS1 a cualquier gen con una consecuencia nula y PM1 por pertenecer a una lista de genes de cáncer. Ambos motores suman PP5/BP6 por texto de ClinVar. El motor nuevo concede PVS1 de apoyo aun sin mecanismo LoF establecido, aproxima NMD por número de exón y aplica BP7 a cualquier sinónima. `evaluate_in_silico(.95, splice_ai_delta=.9)` produce dos `PP3_Strong`, sin control explícito de dependencia.

**Propuesta:** modelar evidencia por variante–gen–enfermedad–mecanismo y aplicar especificaciones pertinentes, versionadas y revisables. Desactivar reglas cuyo dato requerido no exista. Usar ClinVar como fuente trazable —condición, revisión, fecha, conflictos— y examinar la evidencia subyacente, sin convertir su etiqueta en puntos automáticos. Deduplicar evidencia y documentar dependencias.

PVS1 requiere evaluar el mecanismo LoF y contexto transcripcional, no solo el nombre de una consecuencia. Véanse las [recomendaciones PVS1](https://pmc.ncbi.nlm.nih.gov/articles/PMC6185798/). La retirada de PP5/BP6 se aborda en la [recomendación de ClinGen sobre fuentes reputadas](https://pmc.ncbi.nlm.nih.gov/articles/PMC6709533/). Las fuerzas computacionales deben corresponder a calibraciones aplicables; consultar [Pejaver et al.](https://pubmed.ncbi.nlm.nih.gov/36413997/).

**Aceptación:** pruebas de concordancia revisadas por expertos, con evidencia ausente, contradictoria, mecanismos no LoF y transcritos alternativos. Mantener una suma de puntos no basta: el [modelo de Tavtigian](https://pmc.ncbi.nlm.nih.gov/articles/PMC8011844/) depende de supuestos y de la evidencia que recibe. No se propone cambiar sus umbrales arbitrariamente.

### H15 — P0 · Patogenicidad germinal y acción terapéutica somática mezcladas

**Evidencia estática:** [acmg_classifier.py](variant_explorer/acmg_classifier.py), `classify_somatic_tier`, considera accionable una missense en un gen marcado como driver, sin variante específica, tumor, tratamiento ni nivel de evidencia. [acmg_engine.py](variant_explorer/acmg_engine.py) deriva tiers somáticos directamente de puntos germinales.

[circos_viewer.js](variant_explorer/static/js/circos_viewer.js), `renderComplexVariantInspector`, presenta EML4::ALK si aparece ALK **o** EML4, y KMT2A::AFF1 si aparece cualquiera de esos genes. También ofrece conclusiones terapéuticas y farmacogenéticas por presencia de símbolos.

**Propuesta:** separar clasificación germinal, oncogenicidad, significación clínica somática y acción terapéutica. Cada afirmación debe exigir alteración, contexto tumoral, evidencia, jurisdicción/fecha y revisión apropiados. Una anotación de gen o BND no demuestra una fusión funcional. Para farmacogenética, exigir un resultado de diplotipo/CNV/fase validado antes de interpretar metabolización.

**Aceptación:** una missense arbitraria de un driver no obtiene Tier I por el gen; una SV que solo afecta ALK no se transforma en EML4::ALK. El marco somático debe tener un flujo independiente conforme a la [guía AMP/ASCO/CAP](https://pmc.ncbi.nlm.nih.gov/articles/PMC5707196/).

### H16 — P1 · SV y CNV clasificadas por tamaño y listas de genes

**Evidencia estática:** [sv_parser.py](variant_explorer/sv_parser.py), líneas 115–140, asigna patogenicidad a DEL/DUP ≥1 kb en genes de listas o a grandes deleciones. Pierde ID original, ALT, MATEID, EVENT e intervalos de confianza. `ANN` se trata como lista de genes y se inventa profundidad cuando falta. [sv_engine.py](variant_explorer/sv_engine.py) espera nombres de campos diferentes y no está integrado en la ruta normal de ingesta SV.

**Propuesta:** separar registro de breakend, evento estructural, CNV y consecuencia sobre transcritos. Preservar orientación, reciprocidad, incertidumbre y soporte real. Para CNV constitucionales, implementar evaluación de contenido, dosis, herencia y evidencia; no extrapolar reglas CNV a todos los BND/INV. Mantener fusiones como candidatas hasta que su estructura y evidencia las sustenten.

**Aceptación:** un BND se reconstruye desde sus registros originales; tamaño o pertenencia a un gen no bastan para clasificar. Las pérdidas y ganancias requieren criterios diferenciados, como recoge la [guía ACMG/ClinGen de CNV](https://pmc.ncbi.nlm.nih.gov/articles/PMC7313390/).

### H17 — P0 · El parser bedMethyl interpreta contadores como haplotipos

**Reproducido:** [methylation_parser.py](variant_explorer/methylation_parser.py), líneas 75–80, usa columnas 15 y 16 como porcentajes HP1/HP2 en archivos de 18 columnas. En modkit son `N_delete` y `N_fail`. Una fila de prueba con esos contadores 50 y 0 produjo `hp1_percent=50`, `hp2_percent=0`, `is_asm=1`, sin datos de fase.

La columna 4 se interpreta como gen aunque contiene el código de modificación —por ejemplo, `m`—; se pierde la distinción 5mC/5hmC. El supuesto fallback a bedGraph de 4/5 columnas es inalcanzable por el descarte previo de filas con menos de diez columnas. Un bedGraph válido devolvió lista vacía. Tampoco hay un contrato DMR explícito.

**Propuesta:** parsers separados para bedMethyl estándar, resultados por haplotipo, DMR y extensiones internas versionadas. Preservar modificación, hebra, denominadores y filtros. Obtener fase de archivos/etiquetas reales y anotación de genes mediante intervalos de referencia.

**Aceptación:** ninguna fila bedMethyl estándar crea HP1/HP2; formatos no soportados generan error descriptivo, no éxito vacío. Contrastar las columnas con la [documentación de modkit](https://github.com/nanoporetech/modkit/blob/master/README.md).

### H18 — P1 · Metilación: unidades, umbrales e inferencias inconsistentes

**Evidencia estática:** [methylation_view.js](variant_explorer/static/js/methylation_view.js), líneas 93–104, presenta `n_mod + n_canonical` como número de CpG, aunque son llamadas de lecturas. El parser aplica umbrales específicos, la tabla usa 25/60 % y el SVG dibuja un corte general de 60 %. `matches_name` puede asignar un locus clínico por subcadena aunque no coincidan las coordenadas. Se utilizan expresiones como «Gene Silenced», «Active Promoter» y «ASM Confirmed» sin un estado explícito de validación.

**Propuesta:** distinguir número de posiciones CpG, número de llamadas, cobertura válida y resumen regional ponderado. Definir por ensayo/locus/tejido método, controles, umbrales, zona indeterminada y mínimo de cobertura. Separar observación de metilación e interpretación funcional; no concluir expresión, impronta parental o enfermedad solo a partir de un porcentaje.

**Aceptación:** cada cifra lleva unidad y denominador; interfaz e informe usan el mismo estado calculado; una región de baja calidad puede ser indeterminada; ausencia de fase no se denomina bialélica confirmada. Las reglas clínicas concretas deben validarlas especialistas del ensayo.

### H19 — P0 · Cobertura y gráficos pueden representar evidencia no medida

**Evidencia estática:** [igv_manager.py](variant_explorer/igv_manager.py), `calculate_dynamic_coverage`, genera cobertura mediante seno/coseno y cambios basados en SV, y reemplaza profundidades <10× por 55×. [locus_visualizer.py](variant_explorer/locus_visualizer.py) muestra por defecto 45×; su endpoint no obtiene la cobertura del caso.

[methylartist_visualizer.py](variant_explorer/methylartist_visualizer.py), líneas 165–166, duplica la media en HP1/HP2 si faltan; fija un TSS al 15 % del dibujo y una orientación. La ruta pasa `cpg_sites=None`; selecciona una fila con `LIMIT 1`, aunque haya muchos CpG del gen, y puede preferir el nombre del gen a la región solicitada. El script [generate_hg002_methylation.py](scripts/generate_hg002_methylation.py) genera porcentajes/coberturas a partir de `hash()`, bajo una descripción de datos «authentic». Además, `hash()` no garantiza reproducibilidad entre procesos sin controlar su semilla.

**Propuesta:** usar cobertura derivada del alineamiento y modificaciones por lectura/posición; representar agregados como agregados y esquemas como esquemas. Mostrar pistas ausentes sin inventarlas. No deducir origen parental de HP1/HP2. Para un gráfico regional, consultar y agregar las posiciones pertinentes, conservando procedencia y resolución.

**Aceptación:** cada marca que parezca una medición se remonta a un archivo o cálculo documentado; no hay perfiles simulados en rutas clínicas ni haplotipos de reserva. No basta con declarar «Zero Simulation Policy».

### H20 — P1 · Repeticiones: una regla común no representa todas las enfermedades

**Reproducido:** [tandem_repeats.py](variant_explorer/tandem_repeats.py) clasifica por el alelo máximo. FXN con 11 y 100 repeticiones afirma «Diagnostic for Friedreich Ataxia», sin evaluar el segundo alelo causal. La [descripción clínica de Friedreich](https://www.ncbi.nlm.nih.gov/books/NBK1281/) documenta herencia recesiva y la necesidad de considerar variantes bialélicas.

Hay inconsistencias de límites: FMR1 se evalúa con `>=200`, mientras la interfaz anuncia `>200`; `reduced_penetrance_max` no gobierna la evaluación. Se mezclan premutación y penetrancia reducida en una categoría genérica.

**Propuesta:** interpretación por alelo y por caso, incorporando herencia, ploidía, interrupciones, mosaicismo, intervalo de tamaño y evidencia del otro alelo. Versionar límites por locus y ensayo. Resolver discrepancias con el responsable clínico, sin sustituirlas por otro número universal.

**Aceptación:** un único alelo expandido de FXN no equivale por sí solo a diagnóstico; los límites de interfaz y motor coinciden; incertidumbre y loci no soportados permanecen visibles.

### H21 — P1 · Ensamblaje, coordenadas y transcritos no forman un contrato coherente

**Evidencia estática y reproducción de BND:** se mezclan POS VCF de base 1, BED de base 0 y coordenadas de IGV sin adaptadores centrales. En [igv_manager.py](variant_explorer/igv_manager.py), las SNV se convierten con `pos - 1`, pero las SV no. Al recuperar el extremo de una BND en chr22, se devolvió `chr22:130000000` usando la posición del extremo original de chr9, en vez de `pos2=23000000`.

IGV fija hg38 aunque `alignment_ref` sea un texto libre. Hay varias tablas manuales de coordenadas en catálogo, repeticiones, metilación y visor; algunas se derivan de variantes del paciente y se presentan como intervalos génicos.

**Propuesta:** tipo explícito `GenomicInterval(assembly, contig, start0, end0)`, conversión en límites de entrada/salida y representación especial para inserciones/breakends. Usar secuencias y transcritos versionados, con hebra y referencia comprobada. Rechazar mezcla de ensamblajes hasta disponer de una conversión validada.

**Aceptación:** pruebas de límites de intervalo, inserciones y ambos extremos de BND; navegar a una variante y volver a su registro conserva la identidad. El transcrito relevante se muestra con versión y criterio de selección.

### H22 — P1 · El catálogo local no equivale a validación HGNC

**Evidencia estática:** [gene_catalog.py](variant_explorer/gene_catalog.py), `_load_catalog`, mezcla listas manuales, genes encontrados en pacientes y paneles locales. Un gen de panel desconocido recibe `chr1:1000000–1050000`. No se observa consulta ni instantánea completa HGNC. Se fuerza mayúscula a todos los símbolos; eso debe ser una clave de búsqueda, no necesariamente su grafía oficial. El singleton lee una ruta fija de SQLite y no se invalida al cambiar paneles.

**Propuesta:** importar una instantánea oficial de HGNC con identificador estable, símbolo aprobado, alias, estado y fecha. Mantener separadas nomenclatura, coordenadas y pertenencia a paneles. Un símbolo válido puede carecer de coordenadas disponibles. Las coincidencias aproximadas deben proponerse para revisión, sin sustitución clínica silenciosa.

**Aceptación:** añadir un nombre arbitrario a un panel no lo valida ni le inventa coordenadas. La versión de nomenclatura puede reproducirse usando los [datos oficiales HGNC](https://www.genenames.org/download/).

### H23 — P1 · Paneles y hallazgos secundarios no fijan el contexto de análisis

**Reproducido para validación; estático para versionado:** `POST /api/panels` aceptó un símbolo inventado. [app.py](variant_explorer/app.py), líneas 878 y 928, no llama al validador. Los filtros usan siempre `is_active=1`; no existe asociación entre el análisis del caso y una versión concreta del panel. No hay restricción de versión única ni de una sola versión activa. Un panel inexistente se ignora y devuelve todos los resultados; uno vacío tampoco filtra a cero. En SV se usa `LIKE '%GEN%'`, con coincidencias parciales potenciales.

[report_generator.py](variant_explorer/report_generator.py), línea 88, crea hallazgos secundarios mediante una lista de siete genes sin filtro de clase, consentimiento ni condición. Existen otras listas distintas en `models.py` y `clinical_annotations.py`.

**Propuesta:** validar en servidor, usar identificadores génicos y relaciones normalizadas, y fijar `panel_version_id` por análisis/informe. Separar indicación principal y búsqueda secundaria, con política institucional, consentimiento cuando corresponda, versión de recomendaciones y criterios específicos. No cambiar automáticamente expedientes antiguos al actualizar un panel.

**Aceptación:** panel inválido produce error explícito; panel vacío produce cero coincidencias; informes previos conservan su alcance; pertenecer a un gen no convierte una variante en hallazgo secundario reportable. El marco germinal distingue clasificación de uso clínico de los resultados: [ACMG/AMP](https://pmc.ncbi.nlm.nih.gov/articles/PMC4544753/).

## 5. Flujos de trabajo del genetista

### H24 — P1 · La creación de caso desde la interfaz no está conectada

**Evidencia estática:** [components/modals.html](variant_explorer/templates/components/modals.html), línea 44, contiene `submitIngestBtn` fuera del formulario, sin `form=`, `onclick` ni listener en el JavaScript propio. No hay código que envíe ese formulario. La API exige `patient_name`, que el modal no recoge; instrumento y química del modal tampoco se transfieren mediante `api_create_case`.

**Propuesta:** asistente de alta con identificación de caso/muestra, indicación, tipo de análisis, referencia y archivos. Prevalidación de formatos y correspondencia de muestra; resumen previo a la carga; seguimiento de progreso y errores recuperables. Adaptar la identidad mostrada a la política de seudonimización del centro.

**Aceptación:** prueba de navegador desde «New Case» hasta consultar las variantes del nuevo caso, sin usar consola ni scripts. Los metadatos introducidos se conservan y un fallo de carga no deja un caso aparentemente listo.

### H25 — P1 · Filtros visibles sin efecto y navegación a loci desconectada

**Reproducido:** [snv_table.js](variant_explorer/static/js/snv_table.js), líneas 39–40, envía `min_dp` y `phased_only`; la API SNV no los aplica. Con `min_dp=9999&phased_only=true` siguieron apareciendo las dos variantes de prueba. [methylation_view.js](variant_explorer/static/js/methylation_view.js) envía `min_percent`, también ignorado.

Las acciones de IGV de metilación/repeticiones buscan `locusSearchInput` y `igvGoTo`, ausentes en el código propio; el visor ofrece otra entrada (`jumpToLocus`). Pueden abrir la pestaña sin navegar al locus pedido. Esta navegación no se verificó en navegador.

**Propuesta:** contrato único de filtros, con validación de parámetros y confirmación del filtro efectivo. Compartir una función de navegación que acepte intervalo, muestra y referencia. Añadir un resumen de filtros activos y su efecto sobre los recuentos.

**Aceptación:** cada control modifica realmente el conjunto o explica por qué no aplica; cada botón de inspección abre el intervalo del hallazgo seleccionado.

### H26 — P0 · Riesgo de mezclar casos por estado compartido y respuestas tardías

**Evidencia estática; requiere prueba de navegador:** [app.js](variant_explorer/static/js/app.js), `fetchActiveCaseDetails` y listener del selector, y [report_builder.js](variant_explorer/static/js/report_builder.js), `fetchCaseReportFindings`. Las respuestas escriben en `AppState` sin comprobar que el caso siga activo. El cambio de caso no limpia de forma atómica el detalle seleccionado y todos los resultados. Las peticiones de hallazgos no se esperan antes de pintar. IGV reutiliza la instancia existente para buscar coordenadas sin comprobar la muestra.

**Impacto:** una petición lenta de A puede repintar información mientras la cabecera indica B; un hallazgo aún abierto puede guardarse usando el caso activo nuevo. El servidor acepta el JSON del hallazgo sin comprobar su pertenencia al caso.

**Propuesta:** capturar un token de contexto por caso/análisis, cancelar peticiones previas y descartar respuestas antiguas. Vaciar selección y bloquear acciones durante transiciones. En servidor, resolver el hallazgo por identificador y verificar su pertenencia; las notas manuales deben ser campos separados.

**Aceptación:** prueba con respuestas de A/B deliberadamente invertidas; no se muestra ni guarda un hallazgo de A bajo B. Exportar sin caso seleccionado debe estar deshabilitado, no recurrir al caso 1.

### H27 — P1 · Identidad de hallazgos y edición de notas inconsistentes

**Reproducido:** [models.py](variant_explorer/models.py), `save_case_report_finding`, toma `id` antes que `variant_id`; el frontend construye otra identidad en `getVariantUniqueId`. Los duplicados pueden no reconocerse en pantalla aunque SQLite haga upsert. En una conexión, insertar A, insertar B y actualizar A devolvió el ID de B por confiar en `lastrowid` tras `ON CONFLICT DO UPDATE`.

`update_case_report_finding_notes` actualiza la columna, pero no el JSON. Al vaciar una nota, `get_case_report_findings` utiliza `or` y recupera la nota antigua del JSON. Se reprodujo: tras guardar cadena vacía volvió a aparecer `original`.

**Propuesta:** identificadores separados para variante, hallazgo e informe; devolver la fila afectada de manera inequívoca. Tener una sola fuente para cada campo editable y distinguir cadena vacía de valor ausente. Reconciliar objetos y resaltado de inclusión desde la respuesta del servidor.

**Aceptación:** actualizar A devuelve A; borrar una nota la deja vacía tras recargar; añadir, retirar y volver a añadir un hallazgo mantiene identidad y estado visual consistentes.

### H28 — P1 · Persistencia de notas no equivale a auditoría ni firma

**Evidencia estática:** `case_report_findings` conserva fechas y último contenido, pero no actor autenticado, motivo, versiones previas o historial de eliminaciones. `clinical_reports` define columnas de firma, pero no hay flujo que las utilice. Cambios concurrentes pueden sobrescribirse. README anuncia «full clinician audit trails» y el informe afirma certificaciones y aprobaciones que el código no demuestra.

**Propuesta:** flujo borrador → revisión → validado → emitido → rectificado, con responsables autorizados. Historial append-only de acciones y control de concurrencia mediante versión/ETag. Congelar contenido y referencias al emitir; una rectificación crea una versión enlazada. Configurar identidad/acreditación institucional solo con datos comprobados y alcance real.

**Aceptación:** reconstruir quién cambió qué y por qué; un informe emitido no se edita en sitio; el segundo de dos editores recibe conflicto y no pierde cambios. Eliminar un hallazgo del borrador conserva su rastro de auditoría.

### H29 — P0 · Calidad y resultados negativos sin distinguir falta de datos

**Evidencia estática:** [report_builder.js](variant_explorer/static/js/report_builder.js), `updateQcView`, sustituye datos ausentes por Q21.4, 182,4 Gb, Ti/Tv 5,0 y N50 38,4 kb. Fija porcentajes de fase para HG002 y el resto; estima bases mediante `total_reads * n50`, aunque N50 no es longitud media. La etiqueta «HiFi equivalent» se muestra sin una validación de equivalencia.

El generador emite frases de normalidad cuando no hay hallazgos de metilación y «NO PRIMARY PATHOGENIC VARIANTS DETECTED» sin comprobar alcance, ejecución ni calidad. Un error HTTP en SNV/metilación puede convertirse en tabla vacía porque no se comprueba `res.ok`.

**Propuesta:** estados por modalidad: no solicitado, pendiente, en proceso, fallido, insuficiente, evaluable y revisado. Métricas calculadas por la canalización, con método y versión. Mostrar cobertura por región/exón y limitaciones relevantes a la indicación; definir criterios de aceptación por ensayo, sin un umbral genérico universal.

**Aceptación:** datos ausentes no producen indicadores verdes ni negativos clínicos; una caída de la API se muestra como error. Un informe negativo incluye el alcance evaluable y sus limitaciones.

### H30 — P1 · Falta una vista clínica del caso y de su pregunta diagnóstica

**Propuesta basada en el modelo y las pantallas:** actualmente predomina la navegación por tecnología. El esquema agrupa paciente, muestra y análisis en `cases` y mantiene la indicación como texto, sin relaciones familiares ni evidencia de segregación. Tampoco distingue formalmente germinal, somático, farmacogenética o análisis de impronta.

Un genetista necesita empezar por «¿qué estamos intentando explicar?» y no por una tabla de todas las variantes. Propongo:

- Cabecera persistente con identidad suficiente, muestra, tejido, referencia, análisis y versión; etiqueta inequívoca de demostración.
- Indicación, fenotipo estructurado —por ejemplo HPO—, antecedentes y familia/trío, con acceso controlado.
- Resumen de modalidades solicitadas, disponibles y no evaluables; QC específico de la pregunta clínica.
- Lista de candidatos con herencia, correlación fenotípica, evidencia, incertidumbre y decisión de inclusión/exclusión.
- Estado de validación técnica, confirmación independiente cuando la política del ensayo la requiera, y revisión clínica.
- Informe con conclusión, hallazgos relevantes, VUS pertinentes, limitaciones y plan de revisión; secundarios separados según política.

**Aceptación:** sesiones de evaluación con genetistas y personal de laboratorio usando escenarios definidos; medir errores de selección de paciente, hallazgos omitidos y comprensión de «no evaluado» frente a «negativo». El diseño concreto debe acordarse con los usuarios, no inferirse de la apariencia de otras herramientas.

### H31 — P2 · Lenguaje, accesibilidad y densidad de interfaz

**Evidencia estática/propuesta:** interfaz principalmente en inglés con términos como «Fusion Studio», múltiples estilos inline, colores como señal principal y elementos de navegación `li` con clic. Las notas se editan mediante `prompt()`. Falta una presentación uniforme de transcrito, referencia, denominador y estado de revisión.

**Propuesta:** acordar castellano/catalán/inglés, mantener nomenclatura genética estándar y explicar etiquetas interpretativas en lenguaje clínico. Usar controles semánticos, navegación por teclado, foco gestionado en diálogos, etiquetas asociadas y estados que no dependan del color. Editor de notas con guardado explícito, autor y recuperación. Preferencias de columnas, filtros guardados y formato de unidades homogéneo.

**Aceptación:** tareas completas con teclado, mensajes de error persistentes y comprensibles, y revisión con profesionales. No se afirma conformidad de accesibilidad: debe medirse en navegador.

## 6. Arquitectura, rendimiento y operación

### H32 — P1 · Ingesta no idempotente, carga comprimida incorrecta y transacciones parciales

**Reproducido para gzip; estático para transacciones:** [app.py](variant_explorer/app.py), línea 120, lee el archivo completo y lo decodifica como UTF-8 con `errors='ignore'`, aunque el modal acepta `.vcf.gz` y `.bed.gz`. Una carga gzip devolvió éxito con cero variantes. Las SNV/SV se añaden en cada ingesta; metilación borra todas las regiones previas y las reemplaza. `ingest_sample(clear_existing=True)` confirma borrados antes de completar la nueva carga. Varias funciones hacen `commit()` sobre conexiones recibidas.

**Propuesta:** detección real de formato/compresión, validación de cabecera, identidad de muestra y referencia, informe de filas aceptadas/rechazadas. Ingesta por lotes con identificador, checksum y estado; área provisional antes de activar un análisis completo. Transacción controlada por el servicio que orquesta la operación. Distinguir añadir, reemplazar y crear nueva versión.

**Aceptación:** recargar el mismo archivo no duplica llamadas; gzip conserva el mismo resultado que texto; una carga fallida mantiene el análisis anterior; ningún archivo inválido termina con mensaje de éxito engañoso.

### H33 — P1 · Esquema clínico y migraciones insuficientes

**Evidencia estática:** [models.py](variant_explorer/models.py) utiliza `CREATE TABLE IF NOT EXISTS` como inicialización, sin migraciones versionadas. No hay restricciones de rangos para VAF/porcentajes, unicidad de llamadas por análisis, ni relaciones estructuradas de evidencia/transcrito. Los hallazgos guardan copias JSON que pueden sobrevivir a una recarga del caso y quedar desvinculadas de sus datos originales.

**Propuesta:** separar paciente, caso, muestra, análisis y archivo; mantener llamadas originales, anotaciones versionadas e interpretaciones. Añadir migraciones verificadas, integridad referencial y reglas de validez. Conservar un snapshot explícito al emitir informes, en lugar de una copia accidentalmente desactualizada.

**Aceptación:** migrar una base de versión anterior mediante un procedimiento probado; volver a anotar no destruye la interpretación anterior. Una referencia a un hallazgo deja claro de qué análisis proviene.

### H34 — P2 · Rutas demasiado acopladas y lógica clínica duplicada

**Evidencia estática:** [app.py](variant_explorer/app.py) concentra unas 1.460 líneas con SQL, validación, selección de archivos, representación y orquestación. Hay dos motores ACMG, dos rutas de metilación conceptual y reglas clínicas repetidas en Python/JavaScript. `models.py` mezcla DDL, semillas y acceso a datos; `sample_manager.py` mezcla ingesta genérica y fabricación/anotación de HG002. Algunos helpers ignoran `app.config['DB_PATH']` y abren la base predeterminada.

**Propuesta:** mantener inicialmente un monolito modular Flask. Separar blueprints HTTP, servicios de aplicación, dominio clínico, repositorios y adaptadores de formatos. Inyectar contexto de base y almacén de archivos. Retirar código no utilizado solo después de verificar sus consumidores; mover reglas clínicas del frontend a resultados estructurados del dominio.

**Aceptación:** una regla clínica se implementa una sola vez; los tests de dominio no requieren Flask; todas las rutas respetan la base configurada. No hace falta introducir microservicios ni reescribir todo el frontend para conseguirlo.

### H35 — P1 · Caché, memoria y consultas no preparadas para uso WGS real

**Reproducido:** [app.py](variant_explorer/app.py), `_snv_case_stats_cache`, guarda recuentos que no se invalidan tras ingesta. Después de consultar una variante e insertar otra, la API devolvió dos filas con `total_records=1`.

**Evidencia estática:** parsers e ingesta materializan archivos/listas completos; metilación y Circos devuelven todas las filas. `sv_viewer.js` vuelve a descargar todos los SV incluso al paginar la tabla y aunque Circos esté oculto. Fase e informes leen todas las SNV. La paginación usa OFFSET y no añade un desempate único; `%LIKE%` sobre listas de genes dificulta índices. No se midió latencia WGS y no se atribuyen cifras de rendimiento.

**Propuesta:** cachear por versión de análisis y filtros; invalidación explícita o métricas materializadas transaccionalmente. Ingesta en streaming con lotes y trabajos en segundo plano. Paginación estable con ID, y por cursor cuando las mediciones la justifiquen. Agregados regionales multirresolución, índices por intervalos y consultas tabix/BigWig para datos densos. Cargar Circos bajo demanda y declarar si representa todo el caso o el subconjunto filtrado.

**Aceptación:** filas y totales concuerdan tras cargas; presupuesto medido de memoria y latencia en un dataset representativo; no descargar un genoma entero para abrir una región. Evaluar PostgreSQL por necesidades reales de concurrencia, no como sustitución automática de SQLite.

### H36 — P1 · Validación HTTP incompleta, errores y recursos sin cerrar

**Reproducido:** `page=bad` y `max_gnomad_af=bad` devuelven 500. En el segundo caso se añade una condición SQL antes de convertir el valor, dejando un placeholder sin parámetro. Varias rutas devuelven éxito aunque el recurso no exista; identificadores no numéricos se convierten silenciosamente al caso 1 en algunas rutas IGV/fase.

**Evidencia estática:** conexiones sin `finally` y `get_tandem_repeats` sin `close`; el catálogo utiliza una ruta fija. Una comprobación dejó temporalmente bloqueada la base de prueba en Windows al intentar limpiarla. Algunos errores exponen `str(e)`; otros se silencian con `except Exception: pass`. `parse_range_header` acepta casos inválidos como sufijo cero sin validación suficiente.

**Propuesta:** esquemas de entrada, límites y enums; 400/422 para entrada inválida y 404 para recursos inexistentes; no recurrir a otro paciente. Gestionar conexiones con teardown/contexto y transacciones explícitas. Identificadores de error y registros técnicos sin contenido clínico innecesario. Probar rangos HTTP, archivos vacíos y comportamiento de HEAD.

**Aceptación:** entradas malformadas no generan 500; no quedan conexiones abiertas tras éxito/error; errores de archivo o dato no se convierten en resultados clínicos vacíos.

### H37 — P2 · Instalación, despliegue y reproducibilidad incompletos

**Evidencia estática:** `requirements.txt` y `setup.py` declaran dependencias diferentes; el segundo omite `pysam`, `numpy` y `requests`. `setup.py` declara 1.0.0 mientras README/CHANGELOG anuncian 1.2.0. No hay un manifiesto explícito de recursos de paquete que garantice plantillas/estáticos en una rueda. Se usa el servidor de desarrollo Flask y la base reside por defecto junto al código. `.gitignore` no excluye SQLite y sus WAL/SHM. No se encontraron pipeline CI ni instrucciones de recuperación.

**Propuesta:** `pyproject.toml`, versión única, dependencias runtime/dev coherentes y un entorno bloqueado probado. Construir e instalar el paquete en un entorno limpio, verificando assets. Configurar datos fuera del directorio de aplicación, servidor WSGI apropiado, proxy/TLS cuando proceda, copias consistentes de SQLite y restauración ensayada. Documentar compatibilidad de `pysam` y entorno objetivo; no prometer instalación nativa Windows sin probarla.

**Aceptación:** instalación reproducible, arranque sin depender del cwd, recursos incluidos y prueba de restauración. Aislar datos de prueba de datos operativos. No se propone borrar el historial o la base incluida sin un plan de conservación.

### H38 — P1 · Pruebas que validan apariencia o supuestos erróneos

**Evidencia estática y ejecución:** varias clases usan `create_app()` e `init_db()` sin base temporal. La ingesta de ejemplo puede duplicar datos; `clear_existing=True` puede borrar variantes de la base predeterminada. Algunos tests verifican texto o categorías generadas por el propio código, sin recorrer la representación persistida real. El test de informe utiliza `mean_coverage`, `length`, `support` y `acmg_class` en SV, precisamente los campos que no aporta el esquema real.

**Propuesta:** aislar cada prueba con fixtures mínimas e impedir por diseño el acceso a la base operativa. Separar unitarias, integración y pruebas que necesitan datos genómicos externos. Añadir pruebas negativas de identidad, ausencia, fase, límites y contratos, además del recorrido completo navegador → curación → exportación. Validar el motor con casos revisados por expertos independientes de su implementación.

**Aceptación:** un checkout limpio reproduce el resultado documentado; los datasets externos se obtienen con manifiesto y checksum o la prueba explica su omisión; una suite verde no se presenta como validación clínica.

### H39 — P1 · Documentación y benchmark atribuyen capacidades no demostradas

**Evidencia estática:** README anuncia manejo de errores por homopolímeros, TRGT/Straglr, validación HGNC y auditoría completa que no se observan implementados como recorridos integrados. `HG002_TRUTH_SET_DOCUMENTATION.md` presenta ejemplos clínicos, fusiones y metilación como truth set; `hg002_truth_set_metrics.json` contiene porcentajes de rendimiento sin una canalización que los reproduzca. Su cuenta de regiones de metilación también está desactualizada respecto de los archivos actuales.

**Propuesta:** inventario de capacidades con estados «implementada», «experimental», «demostración» y «planificada». Separar cada benchmark por origen, versión, referencia, regiones evaluables, checksum y licencia. Diferenciar exactitud de llamadas de validación de interpretación clínica. Publicar comandos, entradas y resultados para cualquier métrica propia.

La publicación de 2026 citada por el repositorio sí figura en [PubMed](https://pubmed.ncbi.nlm.nih.gov/42561913/); no se considera falsa por su fecha. Eso no acredita que los datos y porcentajes locales procedan de ella. El benchmark CMRG tiene su propia descripción en [NIST](https://www.nist.gov/publications/curated-variation-benchmarks-challenging-medically-relevant-autosomal-genes).

**Aceptación:** un tercero puede reconstruir cada métrica y distinguir ejemplos sintéticos de archivos oficiales. Ninguna afirmación de acreditación o validación se basa únicamente en un comentario del código.

## 7. Resultados de las comprobaciones

### Suite existente

Resultado: **59 pruebas ejecutadas, 54 satisfactorias, 3 fallos de aserción y 2 errores**. No es una ejecución con todas las dependencias y datos genómicos disponibles.

| Prueba | Resultado observado | Interpretación |
|---|---|---|
| `test_snv_aggregate_metrics_beyond_page_limit` | Espera 10 filas y recibe 7 | La fixture limpia no aporta las diez variantes que presupone el test; no demuestra un defecto de LIMIT |
| `test_bam_partial_content_streaming` | Espera 206 y recibe 404 | El BAM solicitado no está en esta copia |
| `test_cmrg_full_ingestion_and_gene_mapping` | Espera >25.000 SNV y recibe 25 | La carga CMRG no pudo ejecutarse sin `pysam`; la excepción se imprime y se continúa |
| `test_chr16_bam_coverage_and_hba_variant` | `ModuleNotFoundError: pysam` | Limitación del entorno; además requiere BAM |
| `test_wgs_tabix_vcf_query` | `ModuleNotFoundError: pysam` | Limitación del entorno; el archivo WGS anunciado tampoco está disponible localmente |

Para repetir la suite de forma aislada en un entorno con las dependencias instaladas, desde la raíz del repositorio:

```python
import os
import tempfile
import unittest
from pathlib import Path

with tempfile.TemporaryDirectory(prefix="variant-explorer-tests-") as tmp:
    os.environ["VARIANT_EXPLORER_DB"] = str(Path(tmp) / "tests.db")
    suite = unittest.defaultTestLoader.discover("tests")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    successful = result.wasSuccessful()

raise SystemExit(0 if successful else 1)
```

La variable protege las funciones que usan `get_db_connection`; el catálogo todavía contiene lecturas de una ruta fija. Esto debe corregirse para un aislamiento completo. No ejecutar las pruebas contra una base clínica.

### Comprobaciones adicionales realizadas

Estas comprobaciones fueron ejecutadas durante la revisión con datos sintéticos; no se han añadido como tests permanentes al repositorio.

| Entrada/acción | Resultado actual observado | Resultado que debería exigirse |
|---|---|---|
| Dos VUS CFTR `0/1` y `1/0`, sin PS | Pareja patogénica en trans | Fase desconocida; no diagnóstico automático |
| Dos variantes con bloques PS distintos | En trans, `Split Blocks` | No conectar bloques sin evidencia |
| C9orf72, alelos 4/1000 | Normal/negativo | Locus reconocido y evaluación válida |
| FXN, alelos 11/100 | Diagnóstico de Friedreich | Interpretación alélica y del segundo alelo |
| bedMethyl estándar con N_delete=50, N_fail=0 | ASM=1 y porcentajes HP inventados | HP ausentes |
| bedGraph de cuatro columnas | Cero registros | Parser soportado o rechazo explícito |
| ALT=G,T, GT=0/2, AD=10,0,20 | VAF=0 y frameshift | Resultado por alelo y anotación real |
| AF=. | Excepción | Dato ausente conservado |
| REVEL=.95 y SpliceAI=.9 | Dos PP3_Strong | Reglas de evidencia/dependencia explícitas |
| REVEL en esquema SQLite | Criterios diferentes entre motores | Un solo contrato de interpretación |
| Consulta → añadir SNV → consulta | Total=1, dos filas | Total=2 |
| `min_dp=9999&phased_only=true` | Devuelve variantes de baja profundidad sin fase | Filtros efectivos |
| `page=bad` / `max_gnomad_af=bad` | HTTP 500 | Error de validación |
| Panel inexistente | HTTP 200, sin filtrar | Error explícito |
| GET de repeticiones de caso vacío | Inserta diez filas | Lectura sin efectos secundarios |
| IGV de dos casos distintos | Misma configuración HG002 | Archivos propios por muestra |
| Hallazgo curado en caso sin SNV originales | Se guarda, no se exporta | Se exporta la selección curada |
| SV persistida Pathogenic | Cero SV en descarga | SV incluida si está curada para informe |
| Caso nuevo exportado | 32,5×, N50 y sexo prefijados | Datos reales o no disponibles |
| Actualizar A tras insertar A y B | Devuelve ID de B | ID de A |
| Vaciar una nota | Reaparece texto del JSON previo | Nota vacía persistente |
| Carga `.vcf.gz` | HTTP 200 y cero variantes | Descompresión y validación |
| Consultar extremo chr22 de BND chr9/chr22 | Posición de chr9 bajo chr22 | Posición del extremo solicitado |
| Crear panel con símbolo inventado | HTTP 201 | Rechazo o estado explícito pendiente |
| Leer README por streaming sin identidad | HTTP 200 y CORS `*` | Solo archivos autorizados |
| Nombre con etiqueta HTML inocua | Etiqueta conservada en informe | Texto escapado |

Las comprobaciones de inyección usaron marcas inocuas. No se descargó la base por HTTP ni se intentó acceder a archivos fuera del repositorio.

## 8. Arquitectura objetivo y modelo de datos

La opción inicial más proporcionada es un **monolito modular**, conservando Flask y las partes útiles del explorador. La separación propuesta es:

```text
variant_explorer/
  api/                 # Blueprints, validación HTTP, autenticación
  application/         # Ingesta, consulta, curación, emisión de informes
  domain/              # Identidad, coordenadas, evidencia e interpretación
  repositories/        # Acceso a base de datos y transacciones
  adapters/            # VCF, bedMethyl, repeats, BAM, referencias
  reporting/           # Snapshot único, HTML y JSON
  templates/
  static/js/           # API común, estado por caso, componentes
migrations/
tests/
  unit/
  integration/
  clinical_cases/      # Casos consensuados, no datos reales identificables
  e2e/
```

Relaciones mínimas que conviene hacer explícitas:

| Entidad | Responsabilidad y datos esenciales |
|---|---|
| Paciente / caso | Identidad controlada, indicación, contexto clínico y permisos |
| Muestra | Tejido, fecha, relación con paciente y otras muestras |
| Análisis | Pipeline, versiones, referencia, alcance, panel fijado, estado y QC |
| Archivo | Análisis, tipo, ruta interna, índice, checksum, procedencia y disponibilidad |
| Llamada | Identidad original, alelo/evento, coordenadas, genotipo, calidad y archivo |
| Anotación | Fuente/versionado, transcrito, frecuencia y consecuencia; ausencia explícita |
| Evidencia | Criterio, fuerza, justificación, referencias, aplicabilidad y dependencias |
| Interpretación | Contexto germinal/somático, enfermedad, clasificación, autor y versión |
| Hallazgo de informe | Selección, relevancia clínica, texto y vínculo a interpretación |
| Versión de informe | Snapshot, estado, responsables, fecha, firma y relación con rectificaciones |
| Evento de auditoría | Actor, acción, objeto, versión anterior/nueva y motivo |

Invariantes que deben atravesar todas las capas:

1. **Ningún dato clínico ausente se sustituye por una medición plausible.**
2. **Toda evidencia pertenece a una muestra y a un análisis identificables.**
3. **Clasificación de variante, causalidad en el caso y acción terapéutica son decisiones distintas.**
4. **Una visualización no puede aportar más certeza que sus datos de origen.**
5. **Un informe emitido representa una versión congelada y reconstruible.**
6. **La ausencia de hallazgos solo se interpreta dentro del alcance realmente evaluado.**

## 9. Plan de implementación por entregables

No conviene comenzar por una refactorización general que mantenga los mismos errores clínicos. Primero deben existir invariantes y pruebas de regresión de los fallos críticos.

| Entregable | Cambios concretos | Dependencias y criterio de salida |
|---|---|---|
| **A. Contención de resultados engañosos** | Retirar resultados por defecto, textos clínicos fijos, generación automática de repeats y anotaciones inventadas; separar demo | Caso vacío permanece vacío/no evaluado en todas las vistas y exportaciones |
| **B. Identidad y acceso** | Registro de archivos por muestra, aislamiento del contexto del navegador, validación de pertenencia, autenticación y permisos | Pruebas A/B y usuarios sin permiso; ninguna pista ajena ni archivo libre |
| **C. Contratos y datos originales** | Parsing validado, ausencia explícita, coordenadas normalizadas, modelos tipados y migraciones | Corpus de formatos y pruebas de conservación de datos; recarga idempotente |
| **D. Curación e informe único** | Identidad de hallazgos, notas, snapshot, exportaciones coherentes, historial y estados | Prueba completa de selección → revisión → emisión → rectificación |
| **E. Interpretación clínica** | Unificar motores, reglas versionadas por contexto, fase y repeats correctos, metilación por ensayo | Conjunto de casos revisado por especialistas; discrepancias resueltas y registradas |
| **F. Rendimiento y operación** | Cargas por lotes/trabajos, consultas regionales, caché correcta, empaquetado, CI, copias/restauración | Mediciones en datos representativos y despliegue reproducible |
| **G. Piloto de usabilidad y validación** | Escenarios clínicos, entrenamiento, control de incidencias y alcance aprobado | Aprobación del laboratorio basada en evidencia del uso previsto |

Los entregables A y B son prioritarios. C y D requieren coordinar la transición de la base existente; E exige disponibilidad de especialistas y no debería estimarse como una simple tarea de programación. F se dimensionará con mediciones. Las integraciones con LIMS/HCE y exportaciones interoperables se diseñarán cuando el informe interno y la identidad de análisis sean estables.

### Pruebas de aceptación clínica que faltan

- Caso sin ningún archivo: todas las modalidades «no evaluadas», sin hallazgos ni firma.
- Caso con SNV solamente: no aparecen resultados de repeticiones o metilación.
- Caso A y caso B abiertos sucesivamente con latencia artificial: ninguna contaminación visual o persistida.
- Variante sin anotación y variante no observada en población: estados distintos.
- Candidato recesivo con dos VUS, fase desconocida o bloques diferentes: sin diagnóstico automático.
- Cambio de panel/transcrito/base de anotación: nueva versión, con posibilidad de reconstruir la anterior.
- Variante FILTER no aprobada y región con cobertura insuficiente: visibles con su estado; no «validada» por una etiqueta clínica.
- Ensayo negativo válido frente a carga fallida: conclusiones distintas.
- Informe con SNV, SV, hipometilación, expansión y notas: igualdad semántica entre pantalla, HTML y JSON.
- Dos profesionales editando la misma interpretación: conflicto detectable y sin pérdida silenciosa.
- Reanálisis y reclasificación: comparación, responsable y procedimiento de comunicación definidos por el centro.

## 10. Aspectos que requieren decisión del laboratorio

Estas decisiones no pueden resolverse solo leyendo el repositorio, pero no impiden corregir los errores demostrados:

| Decisión | Por qué condiciona la implementación |
|---|---|
| Uso previsto: investigación, apoyo a revisión o emisión clínica | Determina alcance, validación, responsabilidades y controles de emisión |
| Germinal, somático, farmacogenética e impronta | Necesitan contexto, reglas e informes diferenciados |
| Muestras, tejidos, trío y consentimiento | Definen modelo clínico, permisos y reportabilidad |
| Referencias, transcritos y fuentes de anotación admitidos | Permiten reproducir resultados y comparar análisis |
| Ensayos y regiones validados, límites de detección | Determinan cuándo se puede decir negativo/evaluable |
| Política de VUS, secundarios, confirmación y reanálisis | Evita decisiones implícitas del software |
| Usuarios, firma, integración LIMS/HCE y conservación | Define auditoría, concurrencia, exportación y recuperación |

El criterio central para aceptar la siguiente versión debe ser que un genetista pueda responder, sin leer código: **de qué muestra sale cada resultado, qué se ha medido realmente, qué incertidumbre queda, quién lo ha interpretado y qué versión exacta está firmando**.
