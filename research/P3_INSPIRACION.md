# P3: celular e-ink "low attention" (inventado). Inspiración y direcciones

> Relevamiento del 25 de septiembre de 2026. Es la base para diseñar el tercer producto del estudio.
> El producto final es **original**: toma patrones del género, pero no copia ni imita ningún modelo ni marca real.
> "VELA" es un nombre de fantasía. No se verificó contra marcas registradas.

## Referencias relevadas

| Producto (año) | Medidas (mm) | Rasgo que aporta | Fuente |
|---|---|---|---|
| Light Phone II (2019) | 95,85 × 55,85 × 8,75 | El cuerpo tiene el mismo color que la tinta, así que el frente se lee como un solo bloque. La UI es una lista de "tools" en texto, sin íconos | [Wikipedia](https://en.wikipedia.org/wiki/Light_Phone_II) |
| Light Phone III (2025) | 106 × 71,5 × 12 | Controles de cámara analógica (rueda y disparador de dos pasos) y la grilla de parlante a la vista | [Wikipedia](https://en.wikipedia.org/wiki/Light_Phone_III) · [designboom](https://www.designboom.com/technology/light-phone-3-point-and-shoot-film-camera-clickable-wheel-flashlight-03-16-2025/) |
| Mudita Kompakt (2024–25) | 128 × 70 × 12,6 | Pantalla e-ink de 4,3" e interruptor físico de privacidad "Offline+" | [Mudita](https://www.mudita.com/products/phones/mudita-kompakt/) |
| Minimal Phone (2024) | 142 × 78 × 8,6 | Mitad pantalla e-ink, mitad teclado QWERTY, y un botón de refresco e-ink | [New Atlas](https://newatlas.com/mobile-technology/minimal-phone-production/) |
| Punkt MP02 (2018, Jasper Morrison) | 117 × 52,3 × 14,4 | Policarbonato texturado con detalles en aluminio anodizado | [Punkt](https://www.punkt.ch/products/mp02-4g-minimalist-phone) |
| Bigme HiBreak Pro (2024–25) | 159,8 × 80,9 × 8,9 | Pantalla hundida sin vidrio y espalda símil cuero | [Good e-Reader](https://goodereader.com/blog/reviews/bigme-hibreak-pro-color-e-ink-smartphone-full-review) |
| Boox Palma (2023–25) | 159 × 80 × 8,0 | Formato de lector de libros electrónicos con botón configurable | [Boox](https://shop.boox.com/products/palma) |
| Hisense A9 (2021–24) | 159 × 79,5 × 7,8 | Espalda de microfibra | [Good e-Reader](https://goodereader.com/blog/electronic-readers/the-hisense-a9-pro-is-a-great-e-ink-phone-with-upgraded-specs) |
| Teenage Engineering OP-1 field | — | Referencia de lenguaje: serigrafías finas, tornillería a la vista, aluminio con soft-touch | [TE](https://teenage.engineering/products/op-1) |

## Patrones del género

- **Escalas:** hay dos. El compacto mide entre 96 y 128 × 52 y 72 mm, con pantalla de 2,8" a 4,3". El tipo phablet mide unos 159 × 79 mm, con pantalla de 6,1".
- **Pantalla:** e-ink mate, a menudo hundida. El borde es grueso, más ancho abajo, y del mismo color que el cuerpo.
- **Botones:** pocos, pero con carácter. Siempre hay encendido y volumen, más un control distintivo: rueda, disparador, interruptor o teclado.
- **Acabados y color:** siempre mate (policarbonato texturado, soft-touch, microfibra, aluminio anodizado). Los colores repiten los de la tinta (negro, gris claro, blanco), con un solo acento.
- **UI:** reloj grande, la fecha y una lista vertical de apps en texto, en una sans grotesca, alineada a la izquierda y con mucho aire.

## Direcciones propuestas

| | A · Losa | B · Bloc | C · Dial |
|---|---|---|---|
| Medidas | 124 × 66 × 10,5 mm, radio 9 | 120 × 56 × 13 mm, espalda curva | 98 × 74 × 11 mm |
| Frente | e-ink de 4,3" hundida 0,6 mm y 3 teclas píldora (◀ ● ▶) | e-ink de 2,9", tecla de navegación circular, "MENÚ"/"ATRÁS" y teclado 3 × 4 con letras chicas ("2 ABC") | e-ink de 3,6" y una ranura de parlante |
| Laterales | Encendido, balancín de volumen e interruptor ON/OFF con punto naranja | Volumen (2 botones redondos) y encendido con una muesca grabada | Rueda moleteada de 40 estrías y botón "HOLD" |
| Espalda | Lente de 7 mm con anillo de aluminio, flash, "VELA" grabado y 2 líneas serigrafiadas de 1,5 mm | "VELA" y una tabla serigrafiada (IMEI, "HECHO PARA LEER") | Placa con 2 lentes, 4 tornillos Torx y goma con patrón de rombos |
| Colorways | Grafito `#2B2B2A` / Papel `#E6E3DC`, acento `#E8581C` | Niebla `#B9BDBF` / Tinta `#1F2226`, tecla 0 `#F2C230` | Musgo `#6E7563` / Arcilla `#C8B8A4` |
| Qué exige | Mucho texto en pantalla y en la espalda, contar las 3 teclas, botones chicos en los cantos | Letras chicas en 12 teclas, texto sobre una superficie curva | Patrones repetidos (estrías, rombos), contar tornillos |
| Métricas que aprovecha | OCR/CER, precisión de bordes (plana: la homografía funciona bien) | OCR con curvatura (la homografía se rompe) | Bordes y geometría; poco texto |

## Qué le cuesta a un modelo generativo

1. **Texto chico:** barra de estado, letras de las teclas, serigrafías de 1,5 mm.
2. **Tildes y símbolos:** "Menú", "·", "›", "°C".
3. **Conteos exactos:** cantidad de teclas, tornillos, agujeros y estrías.
4. **Botones chicos en los cantos:** desaparecen o se duplican.
5. **Aluminio y anillos de cámara:** los reflejos cambian con la vista.
6. **Patrones repetidos:** varían entre vistas.
7. **Texto de bajo contraste:** grabado tono sobre tono.
8. **Pantalla hundida:** si el modelo aplana el frente, se pierde la sombra interior.

## Decisión (25 de septiembre de 2026)

**Dirección A · Losa**, con la UI en inglés (igual que LUMEN y FIELD 16). Tiene dos agregados para volverla más exigente: el **anillo de aluminio pulido** en la cámara, que es la única parte brillante, y el **interruptor de foco con indicador naranja** en el canto superior. "VELA V-43" queda como nombre provisorio.

- **Vistas:** `front` (0°, 4°) y `back` (155°, 16°). La espalda entra porque ahí están las líneas serigrafiadas.
- **Texto de referencia** (lo que lee el OCR): `products/vela/product.json` → `text.screen` (10 líneas, generadas por `fixtures/vela/screen.py`) y `text.back` (3 líneas).
- **Construcción:** `fixtures/vela/build.py`, en código, como los otros dos productos.
- **Pendiente para la fase 1:** comprobar con OCR que las líneas de 1,5 mm de la espalda se leen **en el render de referencia**. Si no se leen, se agrandan a 2 mm antes de congelar el set, y el cambio se registra en el protocolo.
