# Cómo mantener un producto consistente en un workflow de diseño generativo

> Informe de investigación · v0, 25 de septiembre de 2026 · Estado: **estado del arte y diseño experimental; todavía no hay corridas.**
> Los resultados se agregan como `report.md`, generado desde `results.json` con `render_report.py` (estándar research-rigor).
> Las fuentes completas, con links verificados, están en [`LITERATURE.md`](LITERATURE.md). La definición formal de cada condición y cada métrica está en [`PROTOCOL.md`](PROTOCOL.md).

---

## 1. Pregunta

Un modelo generativo produce muy bien *una* imagen linda y mal *la segunda*: otro ángulo, otra escena u otra edición, y el producto cambia. Para una campaña, un catálogo o un sistema de diseño eso es fatal, porque todas las piezas tienen que mostrar el mismo objeto.

La investigación tiene dos preguntas, en este orden:

1. **¿Cómo se mide la consistencia de forma que coincida con lo que ve una persona?** Esto incluye color, forma, partes, texto y logo, y detecta tanto lo que falta como lo que sobra.
2. **Con esa medición, ¿cuánto aporta cada técnica para sostener el producto?** En particular, las técnicas de la capa de lenguaje (spec en el prompt, invariantes, re-anclaje), que son las únicas disponibles cuando el modelo es una API cerrada.

El punto de partida es mi investigación anterior, [From CAD to Shelf](https://marilynbotheatoz.vercel.app/research/cad-to-shelf) ([código](https://github.com/meryboth/from-cad-to-shelf)). Ese pipeline sostiene el producto con geometría 3D y lo mide con ΔE de color. Este trabajo parte de sus límites.

---

## 2. Estado del arte

### 2.1 Cinco maneras de sostener un producto, y un loop

La literatura (2022–2026) y la industria se pueden ordenar según **qué fija cada técnica**:

| Capa | Qué fija | Qué no fija | Ejemplos |
|---|---|---|---|
| **L1. Lenguaje / spec** | Lo que se puede nombrar: color (hex), materiales, cantidad de partes, copy literal, invariantes | Geometría fina, tipografía, texto chico | Prompts JSON (Bria FIBO, FLUX.2), invariantes de OpenAI, prompt regional (RPG, LMD), 1Prompt1Story |
| **L2. Referencia in-context / adapter** | Identidad global y look | Detalle de alta frecuencia; se degrada con los turnos | IP-Adapter, UNO, OminiControl, FLUX.1 Kontext, Qwen-Image-Edit, Nano Banana, gpt-image |
| **L3. Entrenamiento por producto** | Identidad robusta en muchas escenas | Texto fino; se sobreajusta al fondo | DreamBooth-LoRA, Custom Diffusion, CopyCat (2026) |
| **L4. Control estructural 3D** | Forma, pose, perspectiva | Color y estampado | ControlNet con depth y normales renderizados, FreeInsert, el blueprint de NVIDIA |
| **L5. Píxeles reales + armonización** | Todo lo que ya tiene el producto | Solo la vista disponible; artefactos de borde y luz | IC-Light + DetailTransfer, ZeroComp, Adobe Precise Composite, gemelos digitales de Unilever y Nestlé |
| **V. Verificar y corregir** | Detecta y localiza la falla, y decide qué hacer | Lo que el verificador no ve | Photoroom Fidelity Layer, "product truth" de Zalando, Idea2Img, SLD, best-of-N con verificador |

Lo que hace la industria es combinar **L4 o L5 con V**. El producto real (packshot o render del gemelo 3D) no pasa por el modelo, o pasa y después se le reinyecta el detalle. La IA genera la escena y la luz, y un verificador filtra. El principio lo resume COLE: **lo que se puede componer no se genera**. La tensión central es fidelidad contra integración, y Adobe la expone en su API con dos modos (*Precise* y *Adaptive composite*). Nadie publica cómo se reparte esa tensión.

### 2.2 La línea de base es baja

El único benchmark de fidelidad de producto con metodología pública que encontré es el de **Photoroom** (julio 2026):

- **Muestra:** 850 productos y 3.400 imágenes, revisadas por 10 personas; cada imagen la ve un mínimo de 3.
- **Sin corrección:** los mejores editores (Nano Banana 2 y Pro, GPT Image 2) conservan el producto sin errores en **alrededor del 29 %** de los casos.
- **Con su capa de corrección:** **38 %**.
- **Fallas más comunes:** logo o texto deformado (20 %), elementos faltantes o cambiados (12,5 %), patrón (11,4 %), color (8,1 %), elementos agregados (4,8 %). La forma casi no falla (1,5 %).

Dos consecuencias:

- **Un gate automático antes de publicar es obligatorio.**
- **Las métricas tienen que ver texto, logo y partes agregadas**, no solo color y silueta.

### 2.3 Qué puede hacer un system prompt

**A favor.** El texto descriptivo y estructurado mejora la adherencia:

- el recaptioning de DALL-E 3;
- OPT2I, un LLM que reescribe el prompt contra un score, con hasta +24,9 % en DSG;
- FIBO y FLUX.2, que proponen un JSON por componente con su hex, referencias con rol explícito y texto literal entre comillas.

Los tres grandes proveedores coinciden en la edición de varios turnos: **"cambiá solo X, mantené todo lo demás"**, **repetir la lista de invariantes en cada turno** (OpenAI), **reiniciar desde una descripción detallada si hay deriva** (Google) y `input_fidelity="high"` para logos.

**En contra.** El lenguaje pierde información en exactamente lo que más falla:

- La guía de Nano Banana Pro admite que el texto chico y la ortografía "pueden fallar".
- *Persistent Identity Preservation* (sep. 2026) muestra que la calidad del modelo y el seguimiento de instrucciones **no garantizan** la identidad, y que esta se degrada con la edición iterativa y con sujetos chicos.
- Los reescritores entrenados para estética (Promptist, BeautifulPrompt) pueden **cambiar atributos de marca** si la spec no está bloqueada.
- Casi todas las recomendaciones de proveedores **no vienen con ninguna medición**.

**Lectura.** La capa de lenguaje sirve como **fuente única de verdad**: una spec canónica que se compila al prompt de cada modelo *y* genera el checklist del verificador, como los design tokens. Pero no reemplaza al condicionamiento por imagen ni a la verificación. **Cuánto aporta es justamente lo que no está medido** para producto.

### 2.4 Cómo se mide la consistencia (y por qué casi todas las métricas se quedan cortas)

- **DINO y CLIP-I** son el estándar desde DreamBooth. Al juzgar identidad coinciden con los humanos mucho menos que un VLM bien instruido (DreamBench++), y no ven texto ni logos chicos.
- **DreamSim** es la métrica de similitud que mejor predice el juicio humano: 96 % en 2AFC en NIGHTS, contra 70,7 % de LPIPS y 57 % de SSIM/PSNR. Nadie la validó para texto ni logo.
- **Los VLM como jueces ordenan bien pero puntúan mal** (*VLM Judges Can Rank but Cannot Score*, 2026). Son débiles en edición (VIEScore) y **ciegos al detalle fino** (*VLMs are blind*: 58 % en tareas triviales). Sirven en **modo comparativo y con un checklist atómico** (DSG), no con umbrales absolutos.
- **Métricas específicas de producto:**
  - **OCR:** CER y NED del texto contra el copy, como en AnyText y TextDiffuser.
  - **Color:** ΔE00 por región, con las notas de implementación de Sharma 2005.
  - **Geometría:** keypoints (LightGlue + RANSAC, que FlowFixer propone como métrica de detalle fino).
  - **Silueta:** IoU, más la *object expansion* (el producto que "crece" al generar el fondo).
  - **Varias vistas:** MEt3R.
- **Nivel set:** ConsiStory mide la consistencia con DreamSim de a pares sobre el objeto sin fondo. Para el estilo, CSD, con el diagnóstico de fallas de Frochte (2026).
- **Validación contra humanos:** 2AFC con tripletes, checklist binario por atributo, κ entre anotadores como techo, calibración y evaluación separadas, bootstrap por producto (DreamSim, DreamBench++, Deutsch 2023).
- **En ComfyUI** existen nodos que calculan CLIP, DINO o LPIPS **sobre la imagen entera**. No encontré ninguno con máscara, OCR, ΔE00, keypoints ni validación humana.

### 2.5 El hueco

Nadie publica junto:

- una comparación de técnicas **sobre los mismos productos**;
- métricas **por región del producto** validadas contra juicio humano;
- una **línea base de variación real** (cuánto difieren entre sí las fotos o renders del mismo producto);
- el **costo por imagen aprobada**.

Los workflows comunitarios dicen "100 % consistency" sin medirlo. Ahí apunta este trabajo.

---

## 3. Punto de partida: qué deja From CAD to Shelf

From CAD to Shelf ya ocupa las capas L4 y L5 y tiene un verificador V:

- Blender genera depth, normales, máscaras y un mapa de partes.
- ControlNet trabaja al 0,95 y al 0,60, con denoise 0,62.
- A cada parte se le devuelve el color del spec y el detalle del render.
- Un gate decide si la foto se publica, va a revisión o se regenera.

Es la misma arquitectura que los gemelos digitales de la industria, con una diferencia: **publica sus números**. Al leer su código con el estándar research-rigor aparecen cuatro límites.

**1. El gate no ve lo que sobra.** En la ablación publicada, la variante "ControlNet at half strength" tiene **botones inventados, otra grilla y texto que no existe**, y salió **publish** (color 2,1 y partes 0,1). La columna "worst part vs spec" da 7,0 en las tres variantes. El motivo está en `pipeline/qa.py`:

- `colour` es la **mediana** del cuerpo contra el spec, en tono y croma. Un botón inventado ocupa pocos píxeles y no mueve la mediana.
- `parts` compara la mediana de las partes protegidas **en la imagen terminada, después de volver a pegarlas** desde el render. Mide si el pegado funcionó, no la foto.
- Lo inventado aparece **fuera** de la máscara protegida, donde solo mira la mediana de color.

La frase de la nota "it takes both checks to catch both failures" no se sostiene: la falla de geometría no la ve ninguno de los dos checks.

**2. Umbrales a ojo, N = 1.**

- Los umbrales son `LIMITS = {'colour': (5, 10), 'parts': (6, 12)}` y deriva ≤ 6, fijos en el código.
- Nunca se contrastaron con juicio humano ni se evaluaron en un set separado.
- La ablación usa una sola semilla por variante.

**3. El color no se mide con ΔE00.** Es un CIE94 sin el término de luminosidad (ΔC·ΔH), y la decisión tiene sentido: la luz de la escena no debería penalizar. Pero conviene nombrarlo así y reportar también el peor caso por región, no solo la mediana.

**4. El backend pago corre sin guardas.** Las guardas necesitan que la cámara sea exacta. En los modelos de Gemini la consistencia depende de un prompt de texto libre ("keep its shape, proportions, colours, buttons…") y de una sola imagen de referencia. La nota misma describe el dilema: lo local "looks rendered" y nano-banana-2 es "faithful and photographic", pero sin garantías.

**Qué se reutiliza:** los dos productos inventados (LUMEN y FIELD 16, construidos en código, con geometría exacta), los pases de Blender, el grafo local y el cliente de ComfyUI.

---

## 4. Diseño del experimento

La investigación tiene dos estudios. **A va primero**: sin una medición validada, B no puede declarar ganadores (principio 3 de research-rigor: *una métrica se valida antes de volverse un gate*).

### 4.1 Productos

| Caso | Por qué está | Calibra o evalúa |
|---|---|---|
| **LUMEN** (consola portátil) | Caso típico, con partes chicas y brillantes (A/B) | Calibración |
| **FIELD 16** (cámara de bolsillo) | Distinta forma; una banda de color que capta la luz lateral | Evaluación |
| **P3, nuevo: lata o envase con etiqueta impresa** | **Elegido para romper** las técnicas: superficie curva y especular, y **mucho texto**, que es la falla n.º 1 según Photoroom y la que LUMEN y FIELD 16 casi no tienen | Evaluación |

Los tres son inventados y se construyen en código, como en From CAD to Shelf: nada imita una marca real. Separar calibración y evaluación **por producto** evita que los umbrales se ajusten a las mismas imágenes con que se evalúan.

### 4.2 Estudio A: ¿el gate ve lo que ve una persona?

**Set de imágenes con fallas conocidas.** Tiene dos fuentes:

1. **Perturbaciones controladas** sobre renders y fotos buenas, cuya respuesta correcta se conoce:
   - rotación de tono de 2, 5 y 10 ΔE;
   - un botón inventado, pegado fuera de la máscara;
   - una errata de una letra en el texto;
   - logo borrado o deformado;
   - warp local;
   - **cambios que no deberían penalizar**: fondo y luz de escena.

   De acá salen curvas dosis-respuesta por métrica, antes de cualquier etiqueta humana.
2. **Generaciones reales** que cubren las fallas naturales: el grafo local a distintas fuerzas de ControlNet (1,0 / 0,75 / 0,5), con y sin guardas, y salidas crudas de los backends pagos.

**Jueces comparados**

| Rol | Juez |
|---|---|
| Baseline | Gate de From CAD to Shelf (`qa.check`: color + partes) |
| Baseline ingenuo | CLIP-I y DINOv2 sobre la imagen completa (lo que hacen los nodos de la comunidad) |
| **Método** | **Batería por región**: todo dentro de la máscara del producto, cada eje con una métrica de lo que falta y otra de lo que sobra (tabla abajo) |
| Ablación | La misma batería sin máscara |
| Comparador | Juez VLM con checklist atómico derivado de la spec (estilo DSG), en modo A/B y con el orden invertido para medir el sesgo de posición |

**Batería por región**

| Eje | Lo que falta | Lo que sobra |
|---|---|---|
| Geometría | Recall de bordes: bordes del render (discontinuidades de normales y depth) presentes en la foto, ±2 px | **Precisión de bordes: bordes de la foto que no existen en el render** (botones y grillas inventados) |
| Silueta | IoU de la máscara | Expansión del objeto |
| Color | ΔC·ΔH por parte contra el spec: mediana **y peor percentil 95** | Fracción de píxeles de cada parte fuera de tolerancia |
| Identidad | DINOv2 con máscara | DreamSim con máscara |
| Texto (P3) | CER del OCR contra el copy del spec | Caracteres detectados que no están en el spec |

**Etiquetado humano**

- Marilyn más 1 o 2 personas, a ciegas respecto de la condición y del valor de la métrica.
- Checklist por atributo (forma, partes, color, texto: "sirve / no sirve") y alrededor de 150 tripletes 2AFC.
- El κ entre personas se reporta como techo.

**Qué se reporta**

- Por juez: ROC-AUC y la matriz gate contra humano en el set de **evaluación**, con el umbral congelado (v1) antes de abrirlo.
- IC95 por bootstrap sobre productos.
- La **línea base de variación real**: cuánto marca cada métrica entre renders buenos del mismo producto con distinta luz. Un umbral que rechaza renders buenos está mal calibrado.

### 4.3 Estudio B: sostener el producto en el backend pago

La pregunta del system prompt, medida con el gate validado en A.

**Condiciones.** Backend nano-banana-2, el mejor valor según From CAD to Shelf. Todas usan las mismas vistas, escenas y semillas.

| Condición | Qué cambia |
|---|---|
| **B0. Prompt libre** (baseline) | El prompt actual de `generate.gemini()`: invariantes en prosa y una referencia |
| **B1. Spec compilada** | El `product.json` se compila a un bloque estructurado: cada parte con su nombre, color (nombre + hex) y cantidad ("exactly two round buttons, A and B"); copy literal entre comillas; lista de prohibiciones ("no additional buttons, grilles, text or logos") |
| **B2. Spec + referencias con rol** | B1, más el mapa de partes y una segunda vista como imágenes indexadas ("Image 1: the product. Image 2: parts map, one colour per part…") |
| **B3. Spec + guardas alineadas** | B1, más un **post-proceso gratuito**: la foto se registra contra el render (LightGlue + homografía) y después corren las guardas de From CAD to Shelf. No cuesta llamadas nuevas porque reusa las salidas de B1 |
| Referencia local | El grafo local de From CAD to Shelf tal como sale (gratis), para ubicar a todas en la misma escala |

**Edición en varios turnos** (subestudio). Una misma foto pasa por 5 cambios de escena encadenados:

- **B-chain:** cada turno parte del resultado anterior.
- **B-anchor:** cada turno parte del render original y repite los invariantes de la spec, como recomiendan los proveedores.

Se mide la deriva en cada turno **contra la referencia original**.

**Realismo.** Hay una comparación humana 2AFC a ciegas ("¿cuál parece una foto?") entre la referencia local, B1 y B3. Sirve para medir el otro lado del dilema de la nota original: si alinear y aplicar guardas le devuelve a la foto paga el "look" de render.

### 4.4 Hipótesis y qué las refutaría

| # | Hipótesis | La confirma | La refuta |
|---|---|---|---|
| H1 | La batería por región coincide con el humano más que el gate actual | AUC más alto en el set de evaluación, con IC95 de la diferencia fuera de cero | IC que cruza el cero |
| H2 | La precisión de bordes detecta la geometría inventada que el gate actual deja pasar | La variante a media fuerza y las perturbaciones con botón inventado caen bajo el umbral v1 en ≥ 80 % de los casos | < 80 %, o falsos positivos > 20 % en renders buenos |
| H3 | El juez VLM coincide con los humanos en lo grueso pero no en lo fino | κ ≥ 0,6 en presencia y forma general; κ < 0,4 en partes chicas y texto | El VLM iguala a la batería en lo fino |
| H4 | La spec compilada (B1) mejora la fidelidad frente al prompt libre (B0), pero no alcanza en el texto | Mejor tasa de aprobación del gate v1 y menos partes inventadas; CER sin diferencia significativa | Sin diferencia en aprobación, o CER que también mejora |
| H5 | Las guardas alineadas (B3) llevan la fidelidad del backend pago al nivel local sin perder el realismo | Aprobación de B3 ≥ referencia local, y B3 le gana a la referencia local en realismo ≥ 60 % de los pares | La alineación falla en > 20 % de las fotos, o el realismo cae al nivel local |
| H6 | Re-anclar deriva menos que encadenar | La identidad con máscara en el turno 5 cae menos, con IC fuera de cero | Curvas superpuestas |

En todas las hipótesis, con n < 5 por condición no se declara ganador. Si el intervalo cruza el cero, se escribe "empate dentro del ruido".

### 4.5 Muestra y presupuesto

| Bloque | Cálculo | Imágenes | Costo estimado |
|---|---|---|---|
| A: perturbaciones | 3 productos × 2 vistas × 12 perturbaciones | 72 | $0 |
| A: generaciones locales | 3 productos × 2 vistas × 3 fuerzas × 2 (guardas sí/no) × 5 semillas | 180 | $0 (≈ 3,5 min/img en la RTX 2060, unas 10 h) |
| A: juez VLM | ≈ 300 llamadas | — | ≈ USD 3–6 [verificar el precio vigente] |
| B0 / B1 / B2 | 3 condiciones × 3 productos × 2 vistas × 5 semillas | 90 | ≈ USD 7,5 (a USD 0,0835) |
| B3 | Post-proceso de B1 | 30 | $0 |
| Varios turnos | 2 estrategias × 5 turnos × 3 productos × 5 semillas | 150 | ≈ USD 12,5 |
| **Total** | | ≈ 520 | **≈ USD 25–30, tope a definir** |

Toda corrida paga se aprueba antes de lanzarse, y el costo real sale del ledger de Comfy.

### 4.6 Plan de ejecución

| Fase | Qué | Entregable | Costo |
|---|---|---|---|
| 0 | Repo nuevo: portar fixtures, pases y cliente de From CAD to Shelf; construir P3; `runs.jsonl` | Pases de los 3 productos y línea base de variación real | $0 |
| 1 | Métricas de la batería + perturbaciones | Curvas dosis-respuesta por métrica | $0 |
| 2 | Generaciones locales del Estudio A | ≈ 180 imágenes | $0 |
| 3 | Etiquetado humano, calibración con LUMEN, **congelar gate v1**, evaluación con FIELD 16 + P3 | H1–H3, matriz gate contra humano | ≈ USD 5 (VLM) |
| 4 | Estudio B (B0–B3 + varios turnos) | H4–H6 | ≈ USD 20 |
| 5 | Informe generado desde `results.json`, custom node de ComfyUI con el gate v1, nota del portfolio (en inglés) | `report.md`, nodo, nota | $0 |

### 4.7 Límites que ya se ven

- Todos los productos son **sintéticos, construidos en código**: la geometría es exacta y el mapa de partes, perfecto. Con fotos reales de producto (sin CAD) habría que segmentar, y la batería quedaría peor de lo que se va a medir acá.
- Hay tres productos y **un solo backend pago**. Los resultados de B valen para nano-banana-2, no para "los modelos de API".
- Con alrededor de 240 imágenes etiquetadas, el IC del acuerdo queda cerca de ±9 %, no ±5 %.
- La precisión de bordes asume que la cámara coincide con el render. Para B se necesita el registro de B3, y si el registro falla, la métrica falla con él.
- El realismo se juzga con pocas personas y es un juicio, no una medida física.
