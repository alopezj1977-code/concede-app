# CONCEDE V3 — CARGA A GITHUB

## Rama
Crear `motor-v3` desde `main`. No modificar `main` ni `motor-v2`.

## Carga
Subir TODO el contenido de esta carpeta a la raíz de la rama `motor-v3`.

## Entry point
El archivo principal es `app.py`.

## Estructura esperada
- app.py
- requirements.txt
- compat/
- config/
- docs/
- engine/
- source_contract/
- tests/

## No subir
No subir el CSV DENUE de 296,441 registros al repositorio público.

## Validación previa
9 pruebas deben pasar:
`python -m pytest -q tests/test_v3.py tests/test_v2_regression.py`

Resultado validado del paquete:
`9 passed`

## Streamlit
Repository: `alopezj1977-code/concede-app`
Branch: `motor-v3`
Main file path: `app.py`

## Importante
La compatibilidad V2 es un perfil histórico aislado. No redefine las reglas V3.
