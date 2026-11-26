"""Arma el tablero web (index.html) a partir de los resultados del análisis."""
import json, html
import pandas as pd
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
r = json.loads((ROOT/"reporte"/"resumen.json").read_text())
al = pd.read_csv(ROOT/"reporte"/"alertas.csv")
filas = "".join(
    f"<tr><td>{html.escape(x.material)}</td><td class=c>{x.clase}</td><td>{html.escape(x.proveedor)}</td>"
    f"<td class=n>{int(x.stock_actual)}</td><td class=n>{int(x.punto_pedido)}</td><td class=n>{x.semanas_cobertura:.1f}</td>"
    f"<td class=n>{int(x.cantidad_sugerida)}</td><td><span class='tag {'cri' if x.estado=='Crítico' else 'ped'}'>{x.estado}</span></td></tr>"
    for x in al.itertuples())
mejora = 1 - r["error_regresion"]/r["error_promedio_movil"]
page = f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Análisis de abastecimiento · LuSan PRO</title>
<meta name="description" content="Proyecto de Data Science: curva ABC, pronóstico de demanda, punto de pedido y desempeño de proveedores.">
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@700;800&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@500&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box}}body{{margin:0;font-family:Inter,system-ui,sans-serif;color:#1f2937;background:#f8fafc}}
header{{background:#064e3b;color:#fff;padding:48px 24px 40px}}.w{{max-width:1100px;margin:0 auto}}
.k{{font-family:'JetBrains Mono',monospace;color:#6ee7b7;font-size:14px;margin:0 0 10px}}h1{{font-family:Montserrat,sans-serif;font-weight:800;font-size:clamp(28px,4vw,40px);margin:0 0 12px}}
header p{{max-width:760px;line-height:1.6;color:#d1fae5;margin:0}}.note{{margin-top:14px;font-size:14px;color:#a7f3d0}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;margin:-24px auto 0;padding:0 24px}}
.kpi{{background:#fff;border:1px solid #e5e7eb;border-radius:14px;padding:18px 20px;box-shadow:0 4px 14px rgba(0,0,0,.05)}}
.kpi b{{display:block;font-family:Montserrat,sans-serif;font-size:30px;color:#059669}}.kpi span{{font-size:14px;color:#475569}}
section{{padding:40px 24px 0}}h2{{font-family:Montserrat,sans-serif;font-size:22px;margin:0 0 6px}}section p{{color:#475569;line-height:1.6;margin:0 0 16px;max-width:820px}}
img{{width:100%;background:#fff;border:1px solid #e5e7eb;border-radius:14px}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:24px}}
table{{width:100%;border-collapse:collapse;background:#fff;border:1px solid #e5e7eb;border-radius:14px;overflow:hidden;font-size:14px}}
th,td{{padding:10px 12px;border-bottom:1px solid #f1f5f9;text-align:left}}th{{background:#ecfdf5;color:#064e3b;font-weight:600}}.n{{text-align:right;font-variant-numeric:tabular-nums}}.c{{text-align:center}}
.tag{{padding:3px 10px;border-radius:999px;font-size:12px;font-weight:600}}.cri{{background:#fee2e2;color:#b91c1c}}.ped{{background:#fef3c7;color:#92400e}}
.tw{{overflow-x:auto}}footer{{padding:48px 24px;text-align:center;color:#64748b;font-size:14px}}footer a{{color:#059669;font-weight:600}}
@media(max-width:520px){{.grid{{grid-template-columns:1fr}}}}
</style></head><body>
<header><div class="w"><p class="k">LuSan PRO // data science</p><h1>Análisis de abastecimiento y stock</h1>
<p>Qué materiales concentran el gasto, cuánto se va a consumir, cuándo hay que pedir y qué proveedores cumplen. Un tablero para dejar de decidir a ojo.</p>
<p class="note">Datos simulados ({r['materiales']} materiales, {r['semanas']} semanas de consumo y {r['pedidos']} pedidos de compra), generados para el proyecto. No corresponden a ninguna empresa real.</p></div></header>
<div class="kpis w">
<div class="kpi"><b>{r['clase_a']} de {r['materiales']}</b><span>materiales concentran el {r['pct_valor_a']:.0%} del valor (clase A)</span></div>
<div class="kpi"><b>{r['criticos'] + r['pedir_ya']}</b><span>materiales para reponer ({r['criticos']} críticos)</span></div>
<div class="kpi"><b>{mejora:.0%}</b><span>menos error de pronóstico que el promedio móvil</span></div>
<div class="kpi"><b>{r['mejor_a_tiempo']:.0%} vs {r['peor_a_tiempo']:.0%}</b><span>entregas a tiempo: mejor y peor proveedor</span></div>
</div>
<section class="w"><h2>1. Curva ABC</h2><p>Ordena los materiales por valor consumido en el último año. Los de clase A merecen control semanal; los de clase C, revisión mensual.</p><img src="img/curva_abc.png" alt="Curva ABC de materiales"></section>
<section class="w"><h2>2. Pronóstico de demanda</h2><p>Comparé dos métodos en las últimas 12 semanas. La regresión con tendencia y estacionalidad tuvo un error de {r['error_regresion']:.0%}, contra {r['error_promedio_movil']:.0%} del promedio móvil de 4 semanas.</p><img src="img/pronostico.png" alt="Pronóstico de demanda"></section>
<section class="w grid"><div><h2>3. Estado del stock</h2><p>Punto de pedido = demanda pronosticada durante el plazo de entrega + stock de seguridad (nivel de servicio 95%).</p><img src="img/estado_stock.png" alt="Estado del stock por clase"></div>
<div><h2>4. Proveedores</h2><p>Porcentaje de pedidos recibidos en la fecha prometida y demora media cuando llegan tarde.</p><img src="img/proveedores.png" alt="Cumplimiento de proveedores"></div></section>
<section class="w"><h2>Alertas de reposición</h2><p>Lista lista para pasar a compras, con la cantidad sugerida para cubrir el plazo de entrega más 4 semanas.</p>
<div class="tw"><table><thead><tr><th>Material</th><th class=c>Clase</th><th>Proveedor</th><th class=n>Stock</th><th class=n>Punto de pedido</th><th class=n>Semanas de cobertura</th><th class=n>Pedir</th><th>Estado</th></tr></thead><tbody>{filas}</tbody></table></div></section>
<footer>Hecho con Python (pandas, scikit-learn, matplotlib) por <a href="https://hernanarana.github.io">Hernán Arana · LuSan PRO</a> · <a href="https://github.com/hernanarana/hernanarana.github.io/tree/main/analisis-abastecimiento">Ver código</a></footer>
</body></html>"""
(ROOT/"index.html").write_text(page)
print("ok")
