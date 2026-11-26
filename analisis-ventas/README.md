# Análisis de ventas de una tienda online

Proyecto de Data Science de **LuSan PRO**: cuatro preguntas que se hace cualquier tienda.

1. **¿Cuánto crece y cuánto voy a vender?** Ventas mensuales y pronóstico del próximo trimestre (regresión con tendencia, estacionalidad y meses de campaña).
2. **¿Qué categorías dejan plata?** Ventas y margen por categoría.
3. **¿Quiénes son mis mejores clientes?** Segmentación RFM (recencia, frecuencia y monto) con K-means.
4. **¿Cuándo compran?** Mapa de calor por día y hora.

👉 **Ver el tablero:** https://hernanarana.github.io/analisis-ventas/

> Los datos son **simulados** (2 años de ventas de una tienda online), generados con semilla fija para que el análisis sea reproducible. No corresponden a ninguna empresa real.

## Cómo correrlo

```bash
pip install pandas numpy scikit-learn matplotlib openpyxl
python src/generar_datos.py
python src/analisis.py
python src/dashboard.py
```

Hecho por [Hernán Arana · LuSan PRO](https://hernanarana.github.io) con Python, pandas, scikit-learn y matplotlib.
