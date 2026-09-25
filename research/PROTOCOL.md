# Protocolo: consistencia de producto en un workflow de diseño generativo

> Se completa **antes** de la primera corrida. Los cambios posteriores se anotan en "Cambios al protocolo", con fecha y motivo.
> El razonamiento detrás de cada decisión está en [`INFORME.md`](INFORME.md) §4. Las fuentes, en [`LITERATURE.md`](LITERATURE.md).
> Los ítems **[DECIDIR]** están abiertos y tienen que cerrarse antes de la fase indicada.

Fecha de inicio: 2026-09-25 · Commit del protocolo: <al crear el repo>

## 1. Pregunta

- **A.** Una batería de métricas por región del producto, que mide lo que falta y lo que sobra, ¿coincide con el juicio humano más que el gate de From CAD to Shelf y que un juez VLM?
- **B.** Midiendo con ese gate validado, ¿cuánto aporta cada técnica de la capa de lenguaje (spec compilada, referencias con rol, re-anclaje) y un post-proceso de alineación más guardas para sostener el producto en un backend de imagen pago?

## 2. Hipótesis y refutación

| Hipótesis | La confirma | La refuta |
|---|---|---|
| H1: la batería coincide con el humano más que el gate actual | ROC-AUC contra la etiqueta humana "sirve", en el set de evaluación: diferencia batería − gate actual con IC95 bootstrap (por producto) > 0 | IC que cruza el 0 |
| H2: la precisión de bordes atrapa la geometría inventada | ≥ 80 % de las imágenes con partes inventadas (perturbación o ControlNet a 0,5) quedan bajo el umbral v1, con ≤ 20 % de rechazos entre los renders buenos | < 80 % detectadas o > 20 % de falsos rechazos |
| H3: el juez VLM coincide con los humanos en lo grueso, no en lo fino | κ(VLM, humano) ≥ 0,6 en presencia y forma general; < 0,4 en partes chicas y texto | κ ≥ 0,6 también en lo fino |
| H4: B1 (spec compilada) > B0 (prompt libre) en aprobación, pero no en texto | Tasa de aprobación del gate v1 y partes inventadas: diferencia emparejada con IC fuera de 0; CER sin diferencia | Aprobación sin diferencia; o CER que también mejora (esto refuta solo la parte negativa) |
| H5: B3 (B1 + alineación + guardas) iguala a la referencia local en fidelidad y la supera en realismo | Aprobación de B3 ≥ referencia local (IC de la diferencia ∋ 0 o > 0) y realismo 2AFC de B3 contra local ≥ 60 % | Registro fallido en > 20 % de las fotos, o realismo < 60 % |
| H6: re-anclar deriva menos que encadenar | Identidad con máscara (DreamSim) en el turno 5 contra el original: B-anchor mejor, con IC fuera de 0 | IC que cruza el 0 |

## 3. Condiciones

**Estudio A (jueces)**

| Rol | Juez | Qué cambia |
|---|---|---|
| Baseline | `qa.check` de From CAD to Shelf (commit <hash>) | — |
| Baseline ingenuo | CLIP-I (ViT-L/14) y DINOv2 (ViT-B/14) sobre la imagen completa | Sin máscara ni ejes |
| Método | Batería por región (§5) | Máscara y ejes separados para lo que falta y lo que sobra |
| Ablación | La batería sin máscara | Mide qué aporta la segmentación |
| Comparador | Juez VLM con checklist derivado de la spec, en modo A/B y con el orden invertido [DECIDIR modelo] | — |

**Estudio A (generaciones que alimentan el set)**: grafo local de From CAD to Shelf con fuerza de ControlNet ∈ {1,0 (tal como sale), 0,75, 0,5} × guardas ∈ {sí, no}.

**Estudio B**

| Rol | Condición | Qué cambia respecto del baseline |
|---|---|---|
| Baseline | B0: prompt de `generate.gemini()` y una referencia | — |
| Método | B1: spec compilada (partes, hex, cantidades, copy literal, prohibiciones) | Solo el prompt |
| Método | B2: B1 + mapa de partes y segunda vista como referencias indexadas | Suma referencias |
| Método | B3: salidas de B1 + registro LightGlue/homografía + `finish()` | Post-proceso, sin llamadas nuevas |
| Ablación de B3 | B3 sin el registro (guardas sobre la imagen sin alinear) | Mide si el registro es imprescindible |
| Referencia | Local SDXL + ControlNet, tal como sale | — |
| Varios turnos | B-chain contra B-anchor, 5 turnos | Qué imagen es la entrada de cada turno |

Backend de B: nano-banana-2 (Gemini 3.1 Flash Image) a 1K [DECIDIR: confirmar precio y disponibilidad en Comfy].

Todas las condiciones usan las mismas vistas, escenas y semillas. Solo varía lo que se estudia.

## 4. Casos

| Caso | Por qué está | Set |
|---|---|---|
| LUMEN | Típico; partes chicas y especulares | Calibración |
| FIELD 16 | Otra forma; banda de color expuesta a la luz lateral | Evaluación |
| P3: VELA V-43, celular e-ink "low attention", inventado (`fixtures/vela`) | Elegido para romper: pantalla con 10 líneas de texto (OCR), 3 teclas chicas, interruptor en el canto, serigrafía de 1,5 mm en la espalda, anillo de aluminio pulido | Evaluación |

Vistas: LUMEN y FIELD 16 usan front y right; VELA usa front y back (155°, 16°), porque el texto impreso está en la espalda. Escenas: studio-paper y concrete-desk (brand meridian).

## 5. Métricas

Salvo que se indique otra cosa, todas se calculan dentro de `mask.png` del pase correspondiente. En B0–B2, la máscara se obtiene del registro o por segmentación [DECIDIR: BiRefNet o SAM].

| Métrica | Definición exacta | Unidad | Mejor | Ve | No ve (y qué lo cubre) |
|---|---|---|---|---|---|
| Precisión de bordes | Bordes de la foto (Canny, [σ, umbrales a fijar en fase 1]) a ≤ 2 px de un borde del render / bordes de la foto. Borde del render = discontinuidad de normales (ángulo > 30°) ∪ depth ∪ bordes de `mask_parts` | 0–1 | ↑ | Partes, grillas y texto inventados | Partes faltantes → recall |
| Recall de bordes | Bordes del render a ≤ 2 px de un borde de la foto / bordes del render | 0–1 | ↑ | Partes que faltan | Inventadas → precisión |
| IoU de silueta | IoU(máscara de la foto, `mask.png`) | 0–1 | ↑ | Silueta | Detalle interno → bordes |
| Expansión | área(máscara de la foto) / área(`mask.png`) − 1 | % | → 0 | "Object expansion" | — |
| Color por parte | ΔC·ΔH (CIE94 sin L; implementación de `qa.chroma_delta`) entre cada píxel de la parte y el color del spec: mediana y percentil 95 | ΔE | ↓ | Deriva de color | Color correcto sobre forma equivocada → bordes |
| Fuera de tolerancia | Fracción de píxeles de la parte con ΔC·ΔH > umbral | 0–1 | ↓ | Manchas locales que la mediana esconde | — |
| Identidad DINOv2 | Coseno CLS de DINOv2 ViT-B/14 entre la foto y el render, ambos con máscara sobre gris (200,200,198) | −1..1 | ↑ | Identidad global | Detalle chico → bordes, CER |
| Identidad DreamSim | Distancia DreamSim (ensamble por defecto) entre los mismos recortes | 0..1 | ↓ | Similitud percibida | Texto → CER |
| CER (P3) | Levenshtein(OCR, línea de `product.json → text`) / longitud de la línea, emparejando cada línea con la mejor detección; OCR [DECIDIR: PaddleOCR o docTR]. Se reporta por separado para la salida cruda y para la foto terminada (en el grafo local la pantalla se copia exacta, así que su CER terminado es ≈ 0 por construcción) | 0..1+ | ↓ | Texto mal, faltante o inventado | Tipografía |
| Deriva multi-turn | DreamSim en el turno k contra el render original | 0..1 | ↓ | Deriva acumulada | — |
| Realismo | 2AFC humano a ciegas: "¿cuál parece una foto real?" | % de victorias | ↑ | Integración y luz | — |
| Costo por aprobada | USD del ledger (incluye descartes) / imágenes aprobadas por el gate v1 | USD | ↓ | — | — |
| Tiempo | Segundos por imagen, del ledger; arranque en frío separado | s | ↓ | — | — |

El juicio de cada juez es "sirve / no sirve" por imagen. Cómo se combinan las métricas de la batería en ese veredicto (regla AND de umbrales, o regresión logística) se decide en calibración y se congela en v1.

## 6. Muestra

- Semillas: 1, 2, 3, 4, 5 para todas las condiciones generativas.
- A, perturbaciones: 3 productos × 2 vistas × 12 perturbaciones = 72.
- A, locales: 3 × 2 vistas × 3 fuerzas × 2 guardas × 5 semillas = 180.
- B0–B2: 3 × 3 productos × 2 vistas × 5 semillas = 90 pagas. B3 y su ablación: 60, sin costo.
- Varios turnos: 2 × 3 productos × 5 semillas × 5 turnos = 150 pagas.
- Total ≈ 550 imágenes, ≈ 240 pagas.

## 7. Umbrales y evaluación humana

- **Línea base real:** las métricas se calculan entre renders buenos del mismo producto con 3 iluminaciones. Se reporta el rango.
- **Calibración:** todas las imágenes de LUMEN (≈ 100 locales + perturbaciones).
- **Evaluación:** FIELD 16 + P3. **No se miran** hasta congelar v1.
- **Etiquetas automáticas por construcción:** en las perturbaciones, la respuesta correcta se conoce porque la falla se inyecta. Se usan para H2 y para las curvas dosis-respuesta, sin intervención humana.
- **Etiquetado humano:** solo Marilyn, a ciegas respecto de la condición y de las métricas, con una página local de etiquetado que muestra las imágenes en orden aleatorio y se opera con teclado. Checklist por atributo (forma/partes, color, texto, "sirve") + ≈ 150 tripletes 2AFC.
- **Techo de acuerdo:** con una sola anotadora no se puede calcular el κ entre personas. Se usa **test-retest**: un 20 % elegido al azar se vuelve a etiquetar, a ciegas, al menos 3 días después, y se reporta el κ intra-anotadora como techo.
- El juez VLM **no** sirve como fuente de etiquetas: es uno de los jueces evaluados, y usarlo como verdad sería circular.
- **Gate v1:** congelado el <fecha> con hash de commit, antes de abrir el set de evaluación.

## 8. Presupuesto

| Paso | Dónde corre | Costo estimado | Tope |
|---|---|---|---|
| Pases, locales, métricas, perturbaciones | RTX 2060 6 GB local | $0 + energía (≈ 10 h de GPU) | — |
| Juez VLM | API [DECIDIR] | ≈ USD 3–6 | [DECIDIR] |
| B0–B2 | Comfy API, nano-banana-2 | ≈ 90 × 0,0835 ≈ USD 7,5 | [DECIDIR] |
| Varios turnos | Comfy API, nano-banana-2 | ≈ 150 × 0,0835 ≈ USD 12,5 | [DECIDIR] |

Toda corrida paga necesita la aprobación explícita de Marilyn antes de lanzarse. El costo real se toma del ledger.

## 9. Qué se publica

- `research/runs.jsonl`, `research/results.json`, las salidas crudas y las etiquetas humanas (anonimizadas).
- `research/report.md`, generado con `render_report.py`.
- Un custom node de ComfyUI con el gate v1 y su matriz contra humano en el README.
- Nota del portfolio en inglés [DECIDIR título].

## Anexo posible (fuera del experimento): Midjourney, en forma manual

**No es parte del experimento.** Ninguna hipótesis ni conclusión depende de este anexo. Solo se corre si hay suscripción activa y tiempo, y cuando termine el Estudio B.

- **Por qué es manual.** Midjourney no tiene API oficial, y sus términos prohíben automatizar el servicio ("You may not use automated tools to access, interact with, or generate Assets through the Services"). Los wrappers de terceros violan esos términos y no garantizan qué versión ni qué parámetros corren, así que quedan descartados.
- **Condición B-MJ.** Marilyn genera a mano en midjourney.com con los mismos prompts compilados de B0 y B1, la misma imagen de referencia (con su parámetro de referencia de objeto, `--oref` en V7; verificar en V8.x) y las semillas 1–5 con `--seed`. Las imágenes descargadas se miden con el gate v1 congelado, igual que el resto.
- **Qué se registra:** la versión del modelo y los parámetros exactos de cada imagen, y el costo como una fracción de la suscripción. En los límites se aclara que la condición no está automatizada y que el N es chico.
- **Cómo se reporta:** como estudio de casos, aparte de los resultados de B. No se declara ganador contra las condiciones automatizadas.

## Cambios al protocolo

| Fecha | Qué cambió | Por qué | ¿Se decidió antes o después de ver resultados? |
|---|---|---|---|
| 2026-09-25 | La investigación pasa a un repo nuevo (antes se pensaba como continuación de from-cad-to-shelf) | Pedido de Marilyn | Antes |
| 2026-09-25 | P3 pasa a ser un celular e-ink inventado (antes, un envase con etiqueta) | Pedido de Marilyn. Sigue siendo exigente en texto (pantalla con UI de texto), pero pierde lo curvo y especular: puede sumarse una tapa trasera brillante | Antes |
| 2026-09-25 | Una sola anotadora, con test-retest como techo, en lugar de κ entre 2–3 personas | Recursos disponibles | Antes |
| 2026-09-25 | **Se revierte el cambio siguiente: vuelve el etiquetado humano.** Marilyn etiqueta a ciegas con `tools/label.py`, como en el diseño original (test-retest del 20 % como techo). Quedan guardadas las 8 respuestas del piloto de jueces VLM (4 fotos × Gemini 3.1 Pro y GPT-5.5, 31,7 créditos de Comfy, ≈ USD 0,15, en `research/labels/vlm.jsonl`): no se usan como etiquetas; si más adelante se corre un juez VLM sobre más fotos, sirven para H3 | Costo: los dos jueces sobre las 176 fotos restantes usarían ≈ 1.390 de 1.761 créditos, que hacen falta para el Estudio B | Antes de ver cualquier etiqueta humana; el piloto solo se usó para verificar el formato y el costo |
| 2026-09-25 | **Sin etiquetas humanas.** Las etiquetas de la fase 3 las ponen dos jueces VLM de familias distintas (Gemini y GPT), a ciegas respecto de la condición, con la misma consigna que la página de etiquetado. La etiqueta es el consenso; los desacuerdos quedan como "dudosos" y se excluyen de la calibración. El κ entre los dos jueces reemplaza al test-retest como techo. **Consecuencias:** H1 y H2 pasan a medir el acuerdo con jueces VLM, no con humanos; H3 no se puede evaluar (sin humanos no hay contra qué medir al VLM), y el informe no puede decir que el gate coincide con el juicio humano: eso va a "Límites" y a la nota del portfolio. Las fallas por construcción (perturbaciones) siguen siendo la única verdad independiente | Decisión de Marilyn: prefiere no etiquetar | Antes de ver cualquier etiqueta |
| 2026-09-25 | CER: el texto se separa en principal (líneas de 52 px o más en la textura, y el logo de la espalda) y secundario (letra chica). Decide el principal; el secundario se reporta aparte | El OCR lee mal la letra chica apenas se degrada la imagen (JPEG 35: "focus" → "foous"), aunque el producto esté bien | **Después** de ver las perturbaciones de la fase 1 (set de calibración sintético; no hay datos de evaluación todavía) |
| 2026-09-25 | Batería v1: se suman candidatos de color normalizado por la luz (v1), de contraste relativo (v2) y de presencia por pieza (mínimo 200 px por pieza, fijado antes de la corrida). Se miden al lado de los de v0 y el set de perturbaciones decide cuáles pasan a la fase 2 | En la fase 1, el color absoluto quedó tapado por la variación de luz | Después de la fase 1, antes de medir v1 |
| 2026-09-25 | Se agrega un anexo opcional con Midjourney manual, fuera de las hipótesis | Pedido de Marilyn. No hay API oficial | Antes |
| 2026-09-25 | VELA: la serigrafía de la espalda pasa de 1,5 a ~2,5 mm de alto de letra, y el grabado "VELA" sube de contraste | En el render de referencia no se leía: un texto que no cumple ni la referencia no puede ser meta del OCR | Antes (revisión visual de los renders; todavía no hay métricas) |
