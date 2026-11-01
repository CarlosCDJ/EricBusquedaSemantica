# Pendiente: entender y aprovechar el proyecto

## ¿Qué hace el modelo y qué ha hecho el autor?

Una forma de separarlo es imaginar una fábrica:

- **El modelo es una máquina especializada**: recibe texto o imágenes y produce vectores —listas de números— que representan su contenido.
- **El programa del autor organiza el trabajo**: decide qué archivos leer, qué mandar al modelo, qué guardar, cómo comparar y cómo presentar los resultados.

Más concretamente:

| Trabajo | Quién lo hace en este proyecto |
|---|---|
| Encontrar imágenes y PDF en la carpeta | Código del autor |
| Convertir cada página PDF en imagen | Código del autor usando una biblioteca |
| Extraer el texto que exista en el PDF | Código del autor usando una biblioteca |
| Dividir ese texto en fragmentos | Código del autor |
| Durante la indexación, convertir imágenes y fragmentos de texto en vectores | **Modelo EmbeddingGemma 2** |
| Durante la búsqueda, convertir la consulta en un vector | **Modelo EmbeddingGemma 2** |
| Guardar vectores y datos de los archivos | Código del autor, en archivos locales |
| Comparar una consulta con los vectores guardados | Código del autor, con NumPy |
| Ordenar resultados y mostrarlos | Código del autor y su interfaz |

Lo esencial es que **el autor no ha entrenado el modelo para esta práctica**: lo integra en una aplicación y construye alrededor todo el proceso de lectura, indexación y búsqueda.

### ¿Qué tiene de interesante su aportación?

Para aprender, yo destacaría estas piezas:

1. **La gestión de los PDF por dos vías:** trata cada página como imagen y también extrae su texto cuando existe.
2. **La búsqueda conjunta de texto e imagen:** adapta las puntuaciones para poder mezclar resultados de ambas modalidades.
3. **La búsqueda de identificadores exactos:** añade una bonificación cuando encuentra literalmente códigos que un embedding podría tratar mal.
4. **La actualización del índice:** intenta reutilizar lo ya procesado cuando un archivo no ha cambiado.
5. **La aplicación completa:** selección de carpeta, seguimiento del progreso, resultados, miniaturas y apertura de archivos.

Esas ideas y buena parte del código **se pueden estudiar y algunas se pueden adaptar**, aunque cambiemos el modelo o el almacenamiento. Pero hay una pieza que sí depende mucho del modelo elegido: que **texto e imágenes puedan compararse directamente en un mismo espacio**.

## Indexación y búsqueda: ¿cuándo interviene el modelo?

### 1. ¿Qué significa «indexar» en este proyecto?

**Indexar es preparar una carpeta para poder buscar en ella después.** No es una sola operación: engloba varias fases.

Cuando eliges una carpeta y pulsas **Index**, el proceso es, simplificando:

```text
1. Encontrar los archivos
            ↓
2. Preparar su contenido
   - Abrir imágenes
   - Convertir páginas PDF en imágenes
   - Extraer y dividir el texto de los PDF, si existe
            ↓
3. Usar el modelo de embeddings
   - Crear vectores de las imágenes
   - Crear vectores de los fragmentos de texto
            ↓
4. Guardar los vectores y los datos de los archivos
            ↓
   Índice preparado para buscar
```

**El modelo de embeddings interviene dentro de la indexación.** En este código se utiliza después de preparar las imágenes y los fragmentos de texto, pero la indexación todavía no ha terminado: después hay que guardar los resultados.

Durante los doce minutos y medio que esperamos, la aplicación indicaba que estaba en la fase **“Reading images”**. Por el código, esa fase incluye pasar las imágenes preparadas al modelo para generar sus embeddings. El contador seguía a cero porque todavía no había terminado el primer lote.

### 2. Un ejemplo: indexar una factura PDF

Supongamos una carpeta que contiene una factura de una página. Al indexarla, el proyecto sigue **dos caminos para esa misma página**:

```text
                     ┌─→ Imagen de la página
                     │          ↓
                     │   Modelo de embeddings
                     │          ↓
Factura PDF ─────────┤   Vector de imagen
                     │
                     └─→ Texto extraído del PDF
                                ↓
                         Dividir en fragmentos
                                ↓
                         Modelo de embeddings
                                ↓
                         Un vector por fragmento
```

El autor ha programado la preparación de la imagen, la extracción y división del texto, y el almacenamiento. El **modelo**, por su parte, convierte cada imagen y cada fragmento en su vector correspondiente.

Una vez hecho eso, la aplicación guarda los vectores junto con información que permite saber **a qué archivo y a qué página pertenecen**. Ese conjunto forma el índice que se utilizará al buscar.

Si el PDF es un escaneo sin texto extraíble, puede que solo se obtenga la **imagen de la página** y su vector de imagen. No habrá fragmentos de texto si no se ha podido extraer texto.

### 3. ¿A qué nos referimos con «consultas»?

A **lo que tú escribes cuando quieres buscar**, una vez que la carpeta ya está indexada. Por ejemplo:

> `factura del servidor`

Eso es una **consulta**. Es distinta de los documentos de la carpeta:

- Los **documentos** son el contenido donde quieres buscar.
- La **consulta** es la pregunta o frase que introduces para encontrar algo.

El proyecto también pasa esa consulta al modelo de embeddings, pero **en el momento de la búsqueda**, no cuando estás indexando la carpeta.

```text
ANTES: INDEXACIÓN

Factura PDF → preparar contenido → modelo → vectores → guardar índice


DESPUÉS: BÚSQUEDA

«factura del servidor» → modelo → vector de la consulta
                                      ↓
                      comparar con los vectores del índice
                                      ↓
                      mostrar archivos o páginas similares
```

El programa necesita convertir también tu consulta en vector para poder **compararla numéricamente** con los vectores que ya guardó.

### 4. Entonces, ¿el modelo se usa dos veces?

Sí, pero para tareas distintas y en momentos distintos:

| Momento | Qué recibe el modelo | Para qué |
|---|---|---|
| **Indexación** | Imágenes y fragmentos de texto de los archivos. | Crear y guardar representaciones del contenido de la carpeta. |
| **Búsqueda** | La consulta que escribes —o una imagen, si buscas con una imagen—. | Crear una representación que se pueda comparar con el índice. |

La ventaja de guardar el índice es que **no hace falta volver a procesar todos los archivos para cada búsqueda**. Se procesa la consulta y se compara con lo que ya se había guardado. Si luego añades o modificas archivos, puedes actualizar el índice.

## ¿Podemos cambiarlo por PostgreSQL y un modelo gratuito?

**Sí, como idea de proyecto es totalmente viable.** Pero conviene separar los componentes:

```text
ARCHIVOS
   ↓
Código que lee PDF, extrae texto y lo divide
   ↓
Modelo de embeddings → crea los vectores
   ↓
PostgreSQL + pgvector → guarda los vectores
   ↓
Consulta del usuario → mismo modelo de embeddings
   ↓
PostgreSQL busca los vectores más parecidos
```

- **PostgreSQL con `pgvector`** guardaría y buscaría vectores. **No crea los embeddings por sí mismo**: necesitamos un modelo que los genere.
- Ese modelo podría ejecutarse **en un servicio externo**, evitando cargarlo en tu portátil. Hay proveedores con modalidades gratuitas o cuotas de prueba, pero habría que comprobar las condiciones actuales antes de elegir uno: límites, registro, clave API y privacidad.
- La primera vez habría que generar vectores para los documentos. Cada búsqueda también necesita convertir la consulta en vector.
- Si cambiamos de modelo más adelante, normalmente habrá que **volver a generar los embeddings**, porque los vectores de modelos distintos no tienen por qué ser comparables.

### El límite importante: las imágenes

Si elegimos un modelo gratuito de embeddings **solo de texto**, podríamos buscar en el texto extraído de los PDF. Pero **no reproduciríamos automáticamente** la capacidad actual de buscar dentro de fotos, capturas o escaneos.

Para eso hay varias posibilidades:

- Usar un **modelo multimodal** compatible que convierta texto e imágenes en vectores comparables.
- Aplicar **OCR** a capturas y escaneos, y después generar embeddings del texto reconocido. Esto permite buscar el texto visible, aunque no equivale a entender todo el contenido visual de una foto.
- Empezar solo con PDF que ya tengan texto, para aprender el flujo sin complicar la primera versión.

Si se usa un servicio externo, habría que revisar **qué texto o imágenes se envían** y sus condiciones de privacidad. «Gratis» no significa necesariamente «privado», «ilimitado» ni «sin registro».

## ¿Y sería un RAG?

Lo que ha hecho este autor es sobre todo **búsqueda semántica**: encuentra y muestra archivos o páginas relevantes.

Para convertirlo en un **RAG**, añadiríamos otra fase:

```text
Buscar fragmentos relevantes
        ↓
Pasar esos fragmentos a un modelo de lenguaje
        ↓
Generar una respuesta basada en ellos
```

Así que tu idea de relacionarlo con **Extracto** tiene sentido. No conozco todavía su arquitectura ni qué parte teníais resuelta, por lo que no voy a fingir que puedo compararlos en detalle. Pero conceptualmente podríamos estudiar cómo conectar la lectura y búsqueda de este proyecto con PostgreSQL y, si interesa, con una fase posterior de respuesta.

**Mi recomendación para aprender sin comprar hardware:** conservar el código, limpiar los archivos pesados cuando tú decidas y analizar primero el recorrido de **un PDF con texto**. Después podríamos diseñar una versión pequeña con `pgvector` y embeddings externos gratuitos, dejando imágenes y escaneos para una segunda fase. No implica ejecutar ni instalar nada ahora.

---

## Diferencia conceptual entre este proyecto y un RAG

La diferencia conceptual está en **qué se hace después de encontrar la información**:

### Lo que hace este proyecto: buscar

Tú escribes:

> «¿Cómo se descalcifica la cafetera?»

El programa busca entre los archivos y te devuelve, por ejemplo:

> **`manual_es.pdf`, página 4** — esta página parece relacionada con tu consulta.

Después **tú abres el documento y lees la respuesta**. El programa recupera los archivos o páginas más relevantes, pero no redacta una explicación.

### Un RAG: buscar y después responder

Ante la misma pregunta, un sistema RAG haría dos cosas:

1. **Recuperar** los fragmentos relevantes del manual, mediante un buscador como este.
2. Entregar esos fragmentos a un **modelo de lenguaje generativo**, que redacta una respuesta apoyándose en ellos:

> «Según el manual, llena el depósito con la solución descalcificadora y activa el programa de limpieza…»

La idea es que el modelo no responda solo de memoria, sino utilizando la información recuperada. Idealmente, también indicaría de dónde la ha sacado.

```text
ESTE PROYECTO

Tu consulta → busca contenido relevante → te muestra archivos o páginas


RAG

Tu pregunta → busca contenido relevante → un modelo lo utiliza → te redacta una respuesta
```

Por tanto, **la búsqueda que hace este chico podría ser la primera parte de un RAG**. No habría que confundir los dos modelos que podrían intervenir: el de **embeddings** ayuda a encontrar contenido; el **generativo** redacta la respuesta. Son funciones distintas, aunque un mismo sistema pueda combinar ambas.
