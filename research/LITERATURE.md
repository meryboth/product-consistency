# Consistencia de producto en workflows de diseño con IA generativa: estado del arte

> Revisión bibliográfica, 25 de septiembre de 2026. Base para el protocolo (`PROTOCOL.md`) y para la nota del portfolio.
> Alcance: cómo se mantiene la identidad de un producto (forma, color, logo, texto del packaging, materiales, estilo de marca) a lo largo de un pipeline generativo de imagen, y en menor medida de video. También cómo se mide.
>
> **Verificación de fuentes.** Los IDs de arXiv se cotejaron contra la API o la página de arXiv. Los links que no son de arXiv se abrieron o aparecieron tal cual en la búsqueda. Lo que no se pudo verificar está marcado **[sin verificar]**. Los números son los que reportan los autores: no se reprodujeron. La sección 8 lista las discrepancias entre fuentes que hay que resolver leyendo el PDF.

---

## 1. Resumen: siete hallazgos

1. **Ningún mecanismo solo garantiza la consistencia.** Las técnicas se organizan en cinco capas: lenguaje, referencia, entrenamiento, estructura 3D y composición de píxeles reales. Cada una fija cosas distintas. La industria combina una capa de generación con una capa de **verificación y corrección**.
2. **La línea de base del mercado es baja.** En el benchmark humano de Photoroom (850 productos, 3.400 imágenes, julio de 2026), los mejores modelos de edición conservan el producto sin errores en alrededor del **29 %** de los casos. Con su capa de corrección llegan a **38 %**. La falla más frecuente es **logo o texto deformado (20 %)**, seguida de elementos que faltan o cambian (12,5 %), patrón (11,4 %) y color (8,1 %). La forma casi no falla (1,5 %).
3. **El system prompt sirve para lo que se puede nombrar y no alcanza para lo que hay que ver.**
   - **Mejora:** atributos explícitos, como hex por componente, materiales, copy literal, encuadre y lista de invariantes. Hay evidencia a favor: DALL-E 3 recaptioning, OPT2I (+24,9 % en DSG), prompts JSON de FIBO y FLUX.2, 1Prompt1Story.
   - **No transmite bien:** la geometría del logo, la tipografía ni el texto chico. Lo reconoce la propia guía de Nano Banana Pro, y *Persistent Identity Preservation* (2026) muestra que la identidad no aparece sola aunque haya más contexto o un modelo mejor.
4. **La edición en varios turnos acumula deriva.** Los proveedores (OpenAI, Google, BFL) recomiendan lo mismo: **re-anclar a la referencia original y repetir los invariantes en cada turno**, o reiniciar la conversación. Ninguno publica una medición. Los papers de 2025–2026 (Multi-turn Consistent Editing, AnchorEdit, Edit-R2) lo atacan con arquitectura.
5. **Las métricas de embeddings no ven lo que le importa a una marca.**
   - Al juzgar identidad, DINO y CLIP-I coinciden con los humanos mucho menos que un VLM bien instruido (DreamBench++).
   - Todas ignoran el texto y los logos chicos.
   - DreamSim es la que mejor predice la similitud percibida (96 % 2AFC en NIGHTS), pero nadie la validó para texto ni logo.
   - PSNR y SSIM dan resultados casi al azar para este uso.
6. **Los VLM como jueces ordenan bien pero puntúan mal.** Son débiles en edición (VIEScore) y ciegos al detalle visual fino (*VLMs are blind*: 58 % en tareas triviales). Conviene usarlos en **modo comparativo y con un checklist atómico** (estilo DSG), no con umbrales absolutos, y siempre acompañados de chequeos determinísticos: OCR/CER, ΔE00 con máscara, keypoints.
7. **El hueco.** Nadie publica junto: (i) la comparación de las capas sobre el mismo set de productos, (ii) métricas **por región del producto** validadas contra juicio humano, (iii) una **línea base de variación entre fotos reales** del mismo producto y (iv) el costo por imagen aprobada. Los nodos de evaluación de ComfyUI que existen (CLIP, DINO y LPIPS sobre la imagen entera) no enmascaran ni están calibrados. Ahí puede aportar este proyecto.

---

## 2. Cinco capas y un loop

| Capa | Qué fija | Qué no fija | Ejemplos | Costo y setup |
|---|---|---|---|---|
| **L1. Lenguaje / spec** | Atributos nombrables: color (hex), materiales, copy, encuadre, invariantes | Geometría fina, tipografía, texto chico | Spec JSON (FIBO, FLUX.2), invariantes de OpenAI, RPG y LMD (prompt regional), 1Prompt1Story | Casi nulo |
| **L2. Referencia in-context / adapter** | Identidad global, look | Detalle de alta frecuencia; se degrada con los turnos | IP-Adapter, UNO, DreamO, OminiControl, FLUX Kontext, Qwen-Image-Edit-2509/2511, Nano Banana, gpt-image, Seedream | Sin entrenamiento |
| **L3. Entrenamiento por producto** | Identidad robusta en muchas escenas | Texto fino; riesgo de sobreajuste al fondo | DreamBooth-LoRA (FLUX, Qwen), Custom Diffusion, DisenBooth, CopyCat (2026) | Minutos u horas de GPU por SKU |
| **L4. Control estructural / 3D** | Forma, pose, perspectiva | Color y estampado | ControlNet o T2I-Adapter con depth, normal y canny renderizados; FreeInsert; NVIDIA 3D-conditioning Blueprint | Requiere un modelo 3D (CAD o image-to-3D) |
| **L5. Píxeles reales + armonización** | **Todo** lo del producto (los píxeles son reales) | Solo la vista y la pose disponibles; artefactos de borde y luz; "object expansion" | IC-Light + DetailTransfer, ZeroComp, Adobe Precise Composite, gemelos digitales (Unilever, Nestlé), T-Stars-Poster, PosterMaker, COLE | Barato; hace falta un packshot o un render |
| **Loop V. Verificar y corregir** | Detecta y localiza la falla; decide si aceptar, editar la región, regenerar o componer | Depende de lo que vea el verificador | Photoroom Fidelity Layer, "product truth" de Zalando, Idea2Img, SLD, GenArtist, T2I-Copilot, best-of-N con verificador | Cómputo por reintento |

**Arquitectura dominante en la industria.** El producto real (packshot o render del gemelo 3D) no pasa por el modelo generativo, o pasa y después se le reinyecta el detalle. La IA genera la escena y la luz, y un verificador filtra el resultado. La generación pura (L2 y L3) aparece cuando la vista del producto tiene que cambiar. **Lo que se puede componer no se genera** (COLE): el logo y el texto van como capas.

**Tensión central: fidelidad frente a integración.** Adobe la expone en su API (Precise contra Adaptive Composite): cuanto más se regenera el producto para que se integre con la escena, más fidelidad se pierde. Nadie publica esa curva.

---

## 3. La capa de lenguaje: qué puede hacer un system prompt

### Evidencia a favor
- **Captions descriptivos.** DALL-E 3 muestra que un texto rico y estructurado mejora la adherencia al prompt. OPT2I usa un LLM que reescribe el prompt en loop contra un score (DSG) y obtiene hasta +24,9 %.
- **Prompt estructurado.**
  - FIBO (Bria) usa un JSON de más de 1.000 palabras generado por un VLM, que según el proveedor permite cambiar un atributo "sin deriva". No hay benchmark independiente.
  - La guía de FLUX.2 recomienda un subject por componente con su `#HEX`, hasta 8 referencias con un rol cada una y texto literal entre comillas.
  - SCHEMA (Gemini 3 Pro Image, 2026) reporta 91 % de cumplimiento de obligatorios y 94 % de prohibiciones, pero es autorreportado y de un solo autor: evidencia débil.
- **Invariantes en cada turno.** OpenAI (cookbook de abril de 2026) recomienda "change only X / keep everything else the same", repitiendo la lista en cada iteración, y `input_fidelity="high"` para logos. Google recomienda reiniciar la conversación con una descripción detallada si hay deriva. BFL recomienda `Replace '[old]' with '[new]'`.
- **Lenguaje compartido.** 1Prompt1Story (ICLR 2025): concatenar los prompts de un set en uno solo ya sostiene parte de la identidad.
- **Planificación.** LMD, LayoutGPT y RPG separan el "dónde" (layout, región del producto) del "qué" y evitan que el brief creativo contamine la región del producto.

### Evidencia en contra
- El texto pierde información: la fidelidad real de producto se consigue con condicionamiento de imagen o entrenamiento (RefAdGen, ProductConsistency).
- *Persistent Identity Preservation* (sep. 2026): la calidad y el seguimiento de instrucciones **no garantizan** la identidad. Se degrada más con edición iterativa, sujetos chicos y composición de varios sujetos.
- Los reescritores entrenados para estética (Promptist, BeautifulPrompt) pueden **cambiar atributos de marca**. La spec tiene que quedar bloqueada para el reescritor.
- Un VLM usado como crítico también es "lenguaje": ve mal el detalle fino.

### Traducción práctica
La capa de lenguaje funciona como **spec canónica versionada** (JSON) con componentes, hex y materiales, copy literal, invariantes, prohibiciones, referencias con rol, zona segura del logo y tokens de estilo. Un **compilador por modelo** la traduce al dialecto de cada uno. La misma spec **genera el checklist del verificador**, estilo DSG: "¿la tapa es #86E04A?", "¿dice 'X'?". Así el prompt y la evaluación salen de una única fuente de verdad, como los design tokens.

---

## 4. Medición: batería propuesta

Principio: **primero enmascarar y alinear, después medir cada eje con dos métricas**, una gruesa que tolere cambios legítimos de escena y otra fina que atrape el detalle.

| Eje | Gruesa | Fina | Qué deja pasar si se usa sola |
|---|---|---|---|
| 0. Preparación | SAM o detector → máscara y recorte del producto | Homografía LightGlue + RANSAC por cara plana | Sin máscara, el fondo contamina todo |
| Identidad global | DINOv2 con máscara (coseno) | DreamSim con máscara | Texto y logos chicos |
| Forma | IoU de silueta tras alinear; "object expansion" | Proporción de inliers LightGlue/LoFTR; MEt3R si hay varias vistas | Deformación con la silueta intacta |
| Logo | Presencia y ubicación (detector) | DINOv2 o DreamSim sobre el recorte del logo + inliers | Un logo "parecido" con el trazo mal |
| Texto | Precisión exacta por línea | CER / NED contra el copy de la spec (con un OCR independiente) | Tipografía y color del texto |
| Color | Paleta dominante en Lab, comparada con ΔE00 | ΔE00 por región alineada (mediana, peor caso, % sobre umbral) | Cambios de iluminación: normalizar el balance de blancos o reportar ΔC·ΔH |
| Estilo de marca | CSD contra referencias de marca | Gap de discriminación y CSLS en el corpus propio | CSD crudo puede invertir el orden (Frochte 2026) |
| Nivel set y workflow | Media y dispersión (percentil 10) de DreamSim entre pares del set | Deriva por paso **contra el original**, no contra el paso anterior | La media esconde outliers |
| Juez holístico | VLM comparativo A/B frente a la referencia, con rúbrica DreamBench++ | Checklist atómico DSG derivado de la spec | Los puntajes absolutos no son confiables |

**Línea base de variación real.** Tomado de cubiq/FaceAnalysis: antes de comparar lo generado se mide la variación entre **fotos reales del mismo producto**, con distinta luz y ángulo. Un umbral que rechaza fotos reales está mal calibrado.

**Validación contra juicio humano**
1. Tests de sensibilidad con respuesta conocida (idea de RefVNLI): se perturban referencias reales (rotación de tono, errata de una letra, logo deformado, warp, cambio de fondo o luz que **no** debería penalizar) para obtener curvas dosis-respuesta por métrica.
2. Set humano estratificado por tipo de falla, siguiendo la taxonomía de Photoroom.
3. Dos formatos:
   - 2AFC con tripletes (referencia, A, B), analizado con pairwise accuracy calibrada para empates (Deutsch 2023);
   - checklist binario por atributo, para ROC-AUC y elección de umbrales.
4. El acuerdo entre anotadores (Cohen o Fleiss κ) es el **techo**. Las métricas se reportan relativas a ese techo, como en VIEScore y DreamBench++.
5. Separar dev y test. Bootstrap **por producto**, no por imagen.
6. Probar el juez VLM con el orden A/B invertido para medir el sesgo de posición.

Tamaños de referencia (cálculo propio, no sale de la literatura): unos 385 tripletes para estimar un 2AFC con ±5 %, y unos 220 ítems para un Spearman ≈ 0,5 con ±0,1. Para un portfolio esto es mucho: ver en el protocolo la versión reducida.

**Implementaciones disponibles:** `dreamsim`, `t2v_metrics` (VQAScore), LightGlue, CSD, pyiqa, torchmetrics. En ComfyUI existen ComfyUI-Image-Evaluation (CLIP y DINO), ComfyUI-Similarity-Score (CLIP y LPIPS) y ClipVision_Tools. **No se encontraron nodos con DreamSim, DINOv2 con máscara, OCR/CER, ΔE00 ni LightGlue.**

---

## 5. Industria: qué se hace y qué se publica

| Actor | Mecanismo | Métrica de fidelidad publicada |
|---|---|---|
| Photoroom (jul. 2026) | Fidelity Layer: compara, localiza, regenera la región; Visual Agents como gate | **Sí**: benchmark humano, 29 % → 38 % de aprobación, taxonomía de fallas |
| Zalando (ago. 2026) | Motor "product truth": QA automático de color, construcción y marcas frente al original; deriva a humanos | No (solo el tiempo de ciclo) |
| Adobe Firefly / GenStudio | Custom Models (<30 imágenes), Object Composite Precise/Adaptive, brand validation por checklist | No; el "brand score" mide copy y accesibilidad, no el producto |
| Unilever, Nestlé, WPP, NVIDIA | Gemelo 3D del CAD con etiquetas de imprenta; la IA solo arma la escena | No ("100 % brand consistency" es marketing) |
| Amazon Ads, Meta Advantage+ | Fondo generado alrededor de la foto; las "full variations" de Meta pueden alterar el producto | Solo de negocio (CTR, ROAS) y moderación |
| Bria (FIBO, Product Shot) | Prompt JSON; packshot con `placement_type` | Afirmaciones del proveedor |
| Typeface, Canva, Pebblely, Claid, Flair, Krea, Freepik, Figma Weave | Brand kit en contexto, LoRA de objeto, extracción de texto del packaging, "precise mode" | Ninguna |
| DeltaE (proyecto independiente) | Segmentación + corrección de color | ΔE00 mediana 1,96 (objetivo ≤ 3), 80 % pasa automático y 20 % va a humano |

Workflows de ComfyUI para producto que ya existen: IC-Light + **DetailTransfer** (kijai, huchenlei), "Product Photography Relight v3" con separación de frecuencias (risunobushi), IC-Light → ColorBlend → DetailTransfer (MyAIForce), Qwen-Image-Edit-2511 multi-imagen y FLUX.1 Kontext Dev. Varios workflows comunitarios dicen "100 % consistency" **sin medir**.

**Brand guidelines as code:** Frontify (tokens, JSON, MCP; "machine-readable brand governance"), Figma MCP, "Design Tokens as AI Guardrails" ("reduction, not instruction") y Monigle. Todo es propuesta: nada viene con evaluación.

---

## 6. Qué dejan abierto los papers

- **Deriva en varios turnos con packaging con texto.** No hay curva por modelo (Kontext, Qwen-Edit, Nano Banana, gpt-image) ni medición de si el re-anclaje la elimina.
- **Validez de las métricas.** DINO y CLIP-I no ven texto ni color fino. ¿Cuánto mejora el acuerdo con humanos si se agrega máscara, OCR, ΔE00 y keypoints?
- **Frontera costo-calidad.** Composición + relight, referencia in-context, LoRA por SKU y control 3D, comparados sobre los mismos SKUs, midiendo el costo por imagen aprobada.
- **Fidelidad frente a integración.** ¿A partir de qué cambio de vista o de luz conviene pasar de componer a regenerar? ¿Cómo se detectan automáticamente los artefactos de borde, reflejos y expansión?
- **El crítico.** Un verificador compuesto (determinístico + VLM con checklist) frente a solo VLM en best-of-N, con riesgo de que el sistema optimice la métrica y no la identidad ("verifier hacking", Ma et al. 2025).

---

## 7. Referencias

### 7.1 Métodos de modelo y condicionamiento
**Entrenamiento por sujeto**
- DreamBooth — Ruiz et al., CVPR 2023 — [2208.12242](https://arxiv.org/abs/2208.12242)
- Textual Inversion — Gal et al., ICLR 2023 — [2208.01618](https://arxiv.org/abs/2208.01618)
- LoRA — Hu et al., ICLR 2022 — [2106.09685](https://arxiv.org/abs/2106.09685)
- Custom Diffusion — Kumari et al., CVPR 2023 — [2212.04488](https://arxiv.org/abs/2212.04488)
- SVDiff — Han et al., ICCV 2023 — [2303.11305](https://arxiv.org/abs/2303.11305)
- DisenBooth — Chen et al., 2023 — [2305.03374](https://arxiv.org/abs/2305.03374)
- HiFi Tuner — Wang et al., 2023 — [2312.00079](https://arxiv.org/abs/2312.00079)
- Break-A-Scene — Avrahami et al., 2023 — [2305.16311](https://arxiv.org/abs/2305.16311)
- LoRAShop — Dalva et al., 2025 — [2505.23758](https://arxiv.org/abs/2505.23758)
- CopyCat — Zheng et al., 2026 — [2608.00674](https://arxiv.org/abs/2608.00674)

**Encoders y adapters zero-shot**
- IP-Adapter — Ye et al., 2023 — [2308.06721](https://arxiv.org/abs/2308.06721)
- BLIP-Diffusion — Li et al., NeurIPS 2023 — [2305.14720](https://arxiv.org/abs/2305.14720)
- ELITE — Wei et al., ICCV 2023 — [2302.13848](https://arxiv.org/abs/2302.13848)
- InstantID — Wang et al., 2024 — [2401.07519](https://arxiv.org/abs/2401.07519)
- PhotoMaker — Li et al., CVPR 2024 — [2312.04461](https://arxiv.org/abs/2312.04461)
- MS-Diffusion — Wang et al., 2024 — [2406.07209](https://arxiv.org/abs/2406.07209)
- OminiControl — Tan et al., 2024 — [2411.15098](https://arxiv.org/abs/2411.15098)
- UNO (Less-to-More) — Wu et al., 2025 — [2504.02160](https://arxiv.org/abs/2504.02160)
- DreamO — Mou et al., 2025 — [2504.16915](https://arxiv.org/abs/2504.16915)
- Diffusion Self-Distillation — Cai et al., 2024 — [2411.18616](https://arxiv.org/abs/2411.18616)
- In-Context LoRA — Huang et al., 2024 — [2410.23775](https://arxiv.org/abs/2410.23775)
- EasyControl — Zhang et al., 2025 — [2503.07027](https://arxiv.org/abs/2503.07027)
- Personalize Anything — Feng et al., 2025 — [2503.12590](https://arxiv.org/abs/2503.12590)
- TokenVerse — Garibi et al., 2025 — [2501.12224](https://arxiv.org/abs/2501.12224)
- FlowFixer — Jun et al., 2026 — [2602.21402](https://arxiv.org/abs/2602.21402) (propone una métrica por keypoint matching)

**Producto y objeto**
- Paint by Example — Yang et al., CVPR 2023 — [2211.13227](https://arxiv.org/abs/2211.13227)
- ObjectStitch — Song et al., CVPR 2023 — [2212.00932](https://arxiv.org/abs/2212.00932)
- IMPRINT — Song et al., CVPR 2024 — [2403.10701](https://arxiv.org/abs/2403.10701)
- AnyDoor — Chen et al., CVPR 2024 — [2307.09481](https://arxiv.org/abs/2307.09481)
- MimicBrush — Chen et al., 2024 — [2406.07547](https://arxiv.org/abs/2406.07547)
- Add-it — Tewel et al., 2024 — [2411.07232](https://arxiv.org/abs/2411.07232)
- ObjectMate — Winter et al., 2024 — [2412.08645](https://arxiv.org/abs/2412.08645)
- Insert Anything — Song et al., 2025 — [2504.15009](https://arxiv.org/abs/2504.15009)
- ACE++ — Mao et al., 2025 — [2501.02487](https://arxiv.org/abs/2501.02487)
- ZeroComp — Zhang et al., 2024 — [2410.08168](https://arxiv.org/abs/2410.08168)
- IC-Light — Zhang, Rao, Agrawala, ICLR 2025 — [OpenReview](https://openreview.net/forum?id=u1cQYxRI1H) · [GitHub](https://github.com/lllyasviel/IC-Light)
- Salient Object-Aware Background Generation — Eshratifar et al., CVPRW 2024 — [2404.10157](https://arxiv.org/abs/2404.10157) (afiliación: Yahoo o Amazon según la fuente [sin verificar])
- Staging E-Commerce Products… — Ku et al., 2023 — [2307.15326](https://arxiv.org/abs/2307.15326)
- Generate E-commerce Product Background… — Wang et al., 2023 — [2312.13309](https://arxiv.org/abs/2312.13309)
- T-Stars-Poster — Chen et al., 2025 — [2501.14316](https://arxiv.org/abs/2501.14316)
- PosterMaker — Gao et al., CVPR 2025 — [2504.06632](https://arxiv.org/abs/2504.06632)
- AnyText — Tuo et al., ICLR 2024 — [2311.03054](https://arxiv.org/abs/2311.03054)
- RefAdGen — Chen et al., 2025 — [2508.11695](https://arxiv.org/abs/2508.11695)
- Preserving Product Fidelity in Large Scale Image Recontextualization — Malhi et al., 2025 — [2503.08729](https://arxiv.org/abs/2503.08729)
- ProductConsistency — Khanna, Yadav, Singh, 2026 — [2606.19103](https://arxiv.org/abs/2606.19103)
- LogoSticker — Zhu et al., ECCV 2024 — [2407.13752](https://arxiv.org/abs/2407.13752)

**Edición in-context y varios turnos**
- FLUX.1 Kontext — BFL, 2025 — [2506.15742](https://arxiv.org/abs/2506.15742)
- Qwen-Image Technical Report — 2025 — [2508.02324](https://arxiv.org/abs/2508.02324) · [Qwen-Image-Edit-2509](https://huggingface.co/Qwen/Qwen-Image-Edit-2509)
- OmniGen — Xiao et al., 2024 — [2409.11340](https://arxiv.org/abs/2409.11340) · OmniGen2 — [2506.18871](https://arxiv.org/abs/2506.18871)
- SeedEdit — [2411.06686](https://arxiv.org/abs/2411.06686) · SeedEdit 3.0 — [2506.05083](https://arxiv.org/abs/2506.05083) · Seedream 4.0 — [2509.20427](https://arxiv.org/abs/2509.20427)
- Step1X-Edit — [2504.17761](https://arxiv.org/abs/2504.17761) · ICEdit — [2504.20690](https://arxiv.org/abs/2504.20690) · ImgEdit — [2505.20275](https://arxiv.org/abs/2505.20275)
- Multi-turn Consistent Image Editing — Zhou et al., 2025 — [2505.04320](https://arxiv.org/abs/2505.04320)
- AnchorEdit — Xu et al., 2026 — [2606.11751](https://arxiv.org/abs/2606.11751)
- Edit-R2 — Ye et al., 2026 — [2606.05950](https://arxiv.org/abs/2606.05950)
- Towards Generalized Multi-Image Editing — Xu et al., 2026 — [2601.05572](https://arxiv.org/abs/2601.05572)
- VINCIE — Qu et al., 2025 — [2506.10941](https://arxiv.org/abs/2506.10941)
- GPT-ImgEval — Yan et al., 2025 — [2504.02782](https://arxiv.org/abs/2504.02782)

**Control estructural y 3D**
- ControlNet — [2302.05543](https://arxiv.org/abs/2302.05543)
- T2I-Adapter — [2302.08453](https://arxiv.org/abs/2302.08453)
- LooseControl — [2312.03079](https://arxiv.org/abs/2312.03079)
- FreeInsert — [2509.20756](https://arxiv.org/abs/2509.20756)

**Video**
- VideoBooth — [2312.00777](https://arxiv.org/abs/2312.00777)
- ConsisID — [2411.17440](https://arxiv.org/abs/2411.17440)
- Phantom — [2502.11079](https://arxiv.org/abs/2502.11079)
- ConceptMaster — [2501.04698](https://arxiv.org/abs/2501.04698)
- SkyReels-A2 — [2504.02436](https://arxiv.org/abs/2504.02436)
- VACE — [2503.07598](https://arxiv.org/abs/2503.07598)
- HunyuanCustom — [2505.04512](https://arxiv.org/abs/2505.04512)

### 7.2 Prompt, LLM y orquestación
**Prompt descriptivo, reescritura y layout**
- Improving Image Generation with Better Captions (DALL-E 3) — [PDF](https://cdn.openai.com/papers/dall-e-3.pdf)
- Promptist — [2212.09611](https://arxiv.org/abs/2212.09611)
- BeautifulPrompt — [2311.06752](https://arxiv.org/abs/2311.06752)
- OPT2I — [2403.17804](https://arxiv.org/abs/2403.17804)
- LMD — [2305.13655](https://arxiv.org/abs/2305.13655)
- LayoutGPT — [2305.15393](https://arxiv.org/abs/2305.15393)
- RPG — [2401.11708](https://arxiv.org/abs/2401.11708)
- FIBO — [GitHub](https://github.com/Bria-AI/FIBO)
- SCHEMA (Gemini 3 Pro Image) — [2602.18903](https://arxiv.org/abs/2602.18903)

**Consistencia entre imágenes sin entrenamiento**
- ConsiStory — [2402.03286](https://arxiv.org/abs/2402.03286)
- StoryDiffusion — [2405.01434](https://arxiv.org/abs/2405.01434)
- 1Prompt1Story — [2501.13554](https://arxiv.org/abs/2501.13554)
- The Chosen One — [2311.10093](https://arxiv.org/abs/2311.10093)
- StyleAligned — [2312.02133](https://arxiv.org/abs/2312.02133)
- Visual Style Prompting — [2402.12974](https://arxiv.org/abs/2402.12974)
- Text-to-ImageSet (T2IS) — [2506.23275](https://arxiv.org/abs/2506.23275)

**Loops con crítico y agentes**
- Idea2Img — [2310.08541](https://arxiv.org/abs/2310.08541)
- SLD — [2311.16090](https://arxiv.org/abs/2311.16090)
- GenArtist — [2407.05600](https://arxiv.org/abs/2407.05600)
- T2I-Copilot — [2507.20536](https://arxiv.org/abs/2507.20536)
- Inference-time scaling for diffusion — [2501.09732](https://arxiv.org/abs/2501.09732)
- Reflect-DiT — [2503.12271](https://arxiv.org/abs/2503.12271)
- ReflectionFlow — [2504.16080](https://arxiv.org/abs/2504.16080)

**Diseño gráfico y publicidad**
- COLE — [2311.16974](https://arxiv.org/abs/2311.16974)
- OpenCOLE — [2406.08232](https://arxiv.org/abs/2406.08232)
- Graphist — [2404.14368](https://arxiv.org/abs/2404.14368)
- BannerAgency — [2503.11060](https://arxiv.org/abs/2503.11060)
- MIMO — [2507.03326](https://arxiv.org/abs/2507.03326)

**Guías de proveedores**
- [OpenAI GPT Image prompting guide](https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide)
- [Gemini 2.5 Flash Image prompting](https://developers.googleblog.com/how-to-prompt-gemini-2-5-flash-image-generation-for-the-best-results/)
- [Nano Banana ultimate guide](https://cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-nano-banana)
- [Nano Banana Pro tips](https://blog.google/products-and-platforms/products/gemini/prompting-tips-nano-banana-pro/)
- [FLUX.2 prompting guide](https://docs.bfl.ml/guides/prompting_guide_flux2)
- [Kontext image editing](https://docs.bfl.ai/kontext/kontext_image_editing) (la guía i2i dio 404 [sin verificar])

### 7.3 Métricas y evaluación
**Similitud perceptual y embeddings**
- LPIPS — [1801.03924](https://arxiv.org/abs/1801.03924)
- DreamSim — Fu et al., NeurIPS 2023 — [2306.09344](https://arxiv.org/abs/2306.09344) · [código](https://github.com/ssundaram21/dreamsim)
- DINOv2 — [2304.07193](https://arxiv.org/abs/2304.07193)
- SigLIP — [2303.15343](https://arxiv.org/abs/2303.15343)

**Consistencia de sujeto y edición**
- DreamBench++ — [2406.16855](https://arxiv.org/abs/2406.16855)
- RefVNLI — [2504.17502](https://arxiv.org/abs/2504.17502)
- MultiRef — [2508.06905](https://arxiv.org/abs/2508.06905)
- TRACE-Bench — [2608.16765](https://arxiv.org/abs/2608.16765)
- Persistent Identity Preservation — Ren, Zhang, Xia, 2026 — [2609.04151](https://arxiv.org/abs/2609.04151)

**Alineación texto-imagen y VLM como juez**
- VIEScore — [2312.14867](https://arxiv.org/abs/2312.14867)
- TIFA — [2303.11897](https://arxiv.org/abs/2303.11897)
- DSG — [2310.18235](https://arxiv.org/abs/2310.18235)
- VQAScore / GenAI-Bench — [2404.01291](https://arxiv.org/abs/2404.01291) · [t2v_metrics](https://github.com/linzhiqiu/t2v_metrics)
- GenEval — [2310.11513](https://arxiv.org/abs/2310.11513)
- T2I-CompBench — [2307.06350](https://arxiv.org/abs/2307.06350)
- MLLM-as-a-Judge — [2402.04788](https://arxiv.org/abs/2402.04788)
- MJ-Bench — [2407.04842](https://arxiv.org/abs/2407.04842)
- VLM Judges Can Rank but Cannot Score — [2604.25235](https://arxiv.org/abs/2604.25235)
- Vision language models are blind — [2407.06581](https://arxiv.org/abs/2407.06581)

**Preferencia humana y fallas localizadas**
- ImageReward — [2304.05977](https://arxiv.org/abs/2304.05977)
- HPS v2 — [2306.09341](https://arxiv.org/abs/2306.09341)
- Pick-a-Pic — [2305.01569](https://arxiv.org/abs/2305.01569)
- Rich Human Feedback — [2312.10240](https://arxiv.org/abs/2312.10240)

**Texto, color, geometría y estilo**
- TextDiffuser (MARIO-Eval) — [2305.10855](https://arxiv.org/abs/2305.10855)
- X-Omni / LongText-Bench — [2507.22058](https://arxiv.org/abs/2507.22058)
- LogoDet-3K — [2008.05359](https://arxiv.org/abs/2008.05359)
- CIEDE2000 implementation notes — Sharma, Wu, Dalal 2005 — [DOI](https://onlinelibrary.wiley.com/doi/10.1002/col.20070)
- LightGlue — [2306.13643](https://arxiv.org/abs/2306.13643)
- LoFTR — [2104.00680](https://arxiv.org/abs/2104.00680)
- SAM — [2304.02643](https://arxiv.org/abs/2304.02643)
- MEt3R — [2501.06336](https://arxiv.org/abs/2501.06336)
- CSD — [2404.01292](https://arxiv.org/abs/2404.01292)
- When Style Similarity Scores Fail — [2605.09030](https://arxiv.org/abs/2605.09030)

**Meta-evaluación**
- Ties Matter — [2305.14324](https://arxiv.org/abs/2305.14324)

**Nodos ComfyUI de evaluación**
- [ComfyUI-Image-Evaluation](https://github.com/wu12023/ComfyUI-Image-Evaluation)
- [ComfyUI-Similarity-Score](https://github.com/risunobushi/ComfyUI-Similarity-Score)
- [ClipVision_Tools](https://github.com/MoonMoon82/ClipVision_Tools)
- [ComfyUI-ImageSimilarity](https://github.com/ngosset/ComfyUI-ImageSimilarity)
- [ComfyUI_FaceAnalysis](https://github.com/cubiq/ComfyUI_FaceAnalysis)

### 7.4 Industria y comunidad
**Benchmarks y QA en producción**
- Photoroom — [Product Fidelity Benchmark](https://www.photoroom.com/blog/top-editing-image-models-maintain-product-details-only-28-of-the-time) · [Nobody returns a photo](https://www.photoroom.com/inside-photoroom/nobody-returns-a-photo) · [Fidelity gap](https://www.photoroom.com/blog/fidelity-gap-ai-product-photography)
- Zalando — [AI-powered content accuracy](https://corporate.zalando.com/en/technology/how-zalando-approaches-ai-powered-content-accuracy-customer-value-and-human-judgement)
- DeltaE (Santopaolo) — [automated color correction](https://genmind.ch/posts/DeltaE-Automated-Color-Correction-for-AI-Generated-Fashion-Photography/)

**Adobe**
- [Object Composite API](https://developer.adobe.com/firefly-services/docs/firefly-api/guides/how-tos/object-composite/)
- [Custom Models](https://business.adobe.com/products/firefly-business/custom-models.html)
- [GenStudio brand validation](https://experienceleague.adobe.com/en/docs/genstudio-for-performance-marketing/user-guide/guidelines/brand-validation)
- [MAX 2025](https://news.adobe.com/news/2025/10/adobe-max-2025-genstudio)

**Plataformas de generación de producto**
- Typeface — [Image Agent](https://www.typeface.ai/blog/instantly-turn-your-idea-into-visuals-with-image-agent)
- Bria — [Product Shot API](https://docs.bria.ai/product-shot-editing/product-endpoints/product-lifestyle-shot-by-image)
- Google — [Imagen product recontext](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/image/recontextualize-product-images) · [Product Studio](https://blog.google/products-and-platforms/products/shopping/google-product-studio-generative-ai-product-photos/)
- Amazon Ads — [arquitectura (AWS)](https://aws.amazon.com/blogs/machine-learning/learn-how-amazon-ads-created-a-generative-ai-powered-image-generation-capability-using-amazon-sagemaker)
- Meta Advantage+ — [TechCrunch](https://techcrunch.com/2024/05/07/metas-ai-tools-for-advertisers-can-now-create-new-images-not-just-new-backgrounds/)
- Canva — [on-brand images](https://www.canva.com/help/create-onbrand-images-with-ai/) [contenido sin verificar, 403]
- [Pebblely](https://pebblely.com/blog/ai-product-photos-text-extraction/) · [Claid](https://claid.ai/product/ai-photoshoot) · [Flair](https://flair.ai/resources/faq) · [Krea training](https://docs.krea.ai/user-guide/features/training) · [Freepik Objects](https://www.freepik.com/ai/docs/objects) · [Figma Weave](https://www.figma.com/blog/five-figma-weave-workflows/)
- Google Veo 3.1 — [Ingredients to Video](https://blog.google/innovation-and-ai/technology/ai/veo-3-1-ingredients-to-video/)

**Gemelos digitales 3D**
- Unilever / NVIDIA — [caso](https://www.nvidia.com/en-us/case-studies/unilever/)
- Nestlé — [digital twins](https://www.nestle.com/media/news/brands-ai-digital-twins-content-service)
- NVIDIA — [3D conditioning blueprint](https://blogs.nvidia.com/blog/generative-ai-openusd-fuels-3d-product-configurators)
- WPP / Coca-Cola — [NVIDIA blog](https://blogs.nvidia.com/blog/coca-cola-wpp-omniverse-generative-ai)

**Workflows de ComfyUI**
- [kijai/ComfyUI-IC-Light](https://github.com/kijai/ComfyUI-IC-Light)
- [huchenlei/ComfyUI-IC-Light-Native](https://github.com/huchenlei/ComfyUI-IC-Light-Native)
- [Product Photography Relight v3](https://civitai.com/articles/5393/product-photography-relight-v3-with-internal-frequency-separation-for-preserving-details)
- [MyAIForce product photography](https://myaiforce.com/comfyui-product-photography/)
- [Qwen-Image-Edit-2511 en Comfy](https://docs.comfy.org/tutorials/image/qwen/qwen-image-edit-2511)
- [FLUX.1 Kontext Dev en Comfy](https://docs.comfy.org/tutorials/flux/flux-1-kontext-dev)

**Brand guidelines as code**
- [Frontify](https://www.frontify.com/en/blog/the-future-of-brand-governance-is-machine-readable)
- [Monigle](https://www.monigle.com/blog/converting-brand-guidelines-into-ai-ready-systems/)
- [Design Tokens as AI Guardrails](https://dev.to/davekurian/design-tokens-as-ai-guardrails-keeping-ai-generated-screens-on-brand-59n9)
- [Figma MCP](https://www.figma.com/blog/design-systems-ai-mcp/)

---

## 8. Discrepancias y pendientes de verificación

| Punto | Qué dicen las fuentes | Qué hacer |
|---|---|---|
| DreamBench++: acuerdo de GPT-4o con humanos en preservación de concepto | Una búsqueda da 83,3 % (relativo al acuerdo humano-humano de 68,5 %); otra da 79,6 % | Leer la tabla del paper antes de citarlo |
| ProductConsistency: tamaño del benchmark | "174 productos, 870 muestras" frente a "131 productos con texto" | Puede ser el total frente al subset con texto. Verificar en el PDF |
| Photoroom: aprobación | El título dice "28 %" y el cuerpo, 29,0 % para Nano Banana 2 | Citar la tabla, no el título |
| Afiliación de *Salient Object-Aware Background Generation* | Yahoo Research o Amazon, según la fuente | Verificar en el PDF |
| Métricas exactas de Malhi et al., Persistent Identity, ImgEdit y VINCIE | No confirmadas | Leer antes de adoptar sus protocolos |
| Nodos ComfyUI citados como "nativos" o con wrapper | Citados de memoria en algunos casos | Verificar en el ComfyUI Manager al armar el entorno |
