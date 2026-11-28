# Validación del español · EVIDENCIA FINAL — índice definitivo confirmado por quien ejecuta

- Core: `ri` · documentos: 62 · sinónimos (huella): `6d05cb3057bf435a`
- Consulta: `defType=edismax q.op=OR qf=titulo^4 contenido`
- Solo hechos observados; no se calculan métricas de calidad.

| ID | Criterio | Consulta A | Tokens A | Consulta B | Tokens B | Docs A | Docs B | ¿Mismos docs? |
|---|---|---|---|---|---|---|---|---|
| A01 | mayusculas_acentos | función | funcion function | FUNCION | funcion function | 35 | 35 | sí |
| A02 | mayusculas_acentos | búsqueda | busqued | BUSQUEDA | busqued | 13 | 13 | sí |
| A03 | mayusculas_acentos | MÉTODOS | metod | metodos | metod | 25 | 25 | sí |
| S01 | stopwords | la cadena de prototipos | caden prototip | cadena prototipos | caden prototip | 26 | 26 | sí |
| S02 | stopwords | el modelo de caja | model caja | modelo caja | model caja | 10 | 10 | sí |
| M01 | morfologia | promesas | promes promis | promesa | promes promise | 2 | 2 | sí |
| M02 | morfologia | selectores | selector | selector | selector | 9 | 9 | sí |
| M03 | morfologia | funciones | funcion functions | función | funcion function | 32 | 35 | no |
| P01 | morfologia_protegida | media | media | medio | medi | 12 | 9 | no |
| P02 | morfologia_protegida | arrays | arrays arregl matriz | array | array arregl matriz | 13 | 14 | no |
| Y01 | sinonimos | relleno | padding rellen | padding | padding rellen | 8 | 8 | sí |
| Y02 | sinonimos | margen | margen margin | margin | margen margin | 15 | 15 | sí |
| Y03 | sinonimos | arreglo | array arregl matriz | array | array arregl matriz | 14 | 14 | sí |

## Sinónimos: con y sin expansión

| ID | Consulta | Sin expansión | Con expansión | Nuevos por expansión |
|---|---|---|---|---|
| Y01 | relleno | 3 | 8 | CSS/Reference; CSS/Guides/Cascade/Property_value_processing; HTML/Reference/Elements/article (+2) |
| Y01 | padding | 7 | 8 | JavaScript/Reference/Global_Objects/String |
| Y02 | margen | 6 | 15 | HTML/Reference/Elements/article; CSS/Guides/Cascade/Property_value_processing; CSS/Guides/Syntax/Comments (+6) |
| Y02 | margin | 14 | 15 | CSS |
| Y03 | arreglo | 9 | 14 | JavaScript/Reference/Global_Objects/Array; JavaScript/Reference/Classes; JavaScript/Reference/Global_Objects/Symbol (+2) |
| Y03 | array | 9 | 14 | JavaScript/Guide; JavaScript/Reference/Operators; JavaScript/Reference/Global_Objects/String (+2) |
