"""Análisis de ventas: tendencia y pronóstico, margen por categoría, segmentos de clientes (RFM + KMeans) y horarios."""
import json
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; DATA, IMG, REP = ROOT/"data", ROOT/"img", ROOT/"reporte"
VERDE, VERDE2, OSCURO, GRIS, AMBAR, ROJO = "#059669", "#6ee7b7", "#064e3b", "#9ca3af", "#f59e0b", "#dc2626"
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": "#cbd5e1",
                     "axes.labelcolor": "#334155", "xtick.color": "#475569", "ytick.color": "#475569", "axes.titleweight": "bold", "axes.titlesize": 13})
p = pd.read_csv(DATA/"productos.csv"); v = pd.read_csv(DATA/"ventas.csv", parse_dates=["fecha"]).merge(p, on="producto")
v["venta"] = v.cantidad * v.precio; v["margen"] = v.cantidad * (v.precio - v.costo)

# 1. Ventas mensuales + pronóstico 3 meses
m = v.set_index("fecha").resample("MS").venta.sum()
t = np.arange(len(m)); X = lambda t: np.column_stack([t, np.sin(2*np.pi*t/12), np.cos(2*np.pi*t/12), (np.asarray(t) % 12 == 11).astype(float), (np.asarray(t) % 12 == 10).astype(float)])
lr = LinearRegression().fit(X(t[:-3]), m.values[:-3]); pred_test = lr.predict(X(t[-3:]))
err = float(np.abs(pred_test - m.values[-3:]).sum() / m.values[-3:].sum())
lr = LinearRegression().fit(X(t), m.values); tf = np.arange(len(m), len(m)+3); fut = lr.predict(X(tf))
fidx = pd.date_range(m.index[-1] + pd.offsets.MonthBegin(), periods=3, freq="MS")
crec = float(m["2025"].sum() / m["2024"].sum() - 1)
fig, ax = plt.subplots(figsize=(10, 4.3))
ax.bar(m.index, m.values/1e6, width=20, color=[VERDE if d.year == 2025 else VERDE2 for d in m.index])
ax.bar(fidx, fut/1e6, width=20, color="white", edgecolor=VERDE, hatch="///", label="Pronóstico 2026")
from matplotlib.patches import Patch
ax.set_ylabel("Ventas (millones ARS)"); ax.set_title(f"Ventas mensuales: +{crec:.0%} en 2025 vs 2024"); h,l=ax.get_legend_handles_labels(); ax.legend([Patch(color=VERDE2),Patch(color=VERDE)]+h,["2024","2025"]+l,frameon=False, loc="upper left", ncol=3)
fig.tight_layout(); fig.savefig(IMG/"ventas_mensuales.png", dpi=150); plt.close(fig)

# 2. Margen por categoría
c = v.groupby("categoria").agg(venta=("venta", "sum"), margen=("margen", "sum")); c["margen_pct"] = c.margen / c.venta; c = c.sort_values("margen")
fig, ax = plt.subplots(figsize=(10, 4.2))
ax.barh(c.index, c.venta/1e6, color="#d1fae5", label="Ventas"); ax.barh(c.index, c.margen/1e6, color=VERDE, label="Margen")
for i, (vv, mp) in enumerate(zip(c.venta, c.margen_pct)): ax.text(vv/1e6 + 2, i, f"margen {mp:.0%}", va="center", fontsize=10, color="#334155")
ax.set_xlabel("Millones ARS (2 años)"); ax.set_xlim(0, c.venta.max()/1e6*1.3); ax.legend(frameon=False, loc="lower right")
top = c.margen.idxmax(); ax.set_title(f"{top} deja el mayor margen en pesos")
fig.tight_layout(); fig.savefig(IMG/"margen_categoria.png", dpi=150); plt.close(fig)

# 3. Segmentos RFM
hoy = v.fecha.max() + pd.Timedelta(days=1)
rfm = v.groupby("cliente").agg(recencia=("fecha", lambda d: (hoy - d.max()).days), frecuencia=("orden", "nunique"), monto=("venta", "sum"))
Z = StandardScaler().fit_transform(np.column_stack([rfm.recencia, np.log1p(rfm.frecuencia), np.log1p(rfm.monto)]))
rfm["k"] = KMeans(4, n_init=10, random_state=0).fit_predict(Z)
prof = rfm.groupby("k").agg(clientes=("monto", "size"), recencia=("recencia", "mean"), frecuencia=("frecuencia", "mean"), monto=("monto", "sum"))
order = prof.sort_values("monto", ascending=False).index
names = {}
for k in order:
    r = prof.loc[k]
    if r.frecuencia == prof.frecuencia.max(): names[k] = "Fieles"
for k in order:
    if k in names: continue
    r = prof.loc[k]
    if r.recencia == prof.recencia.max(): names[k] = "Perdidos"
for k in order:
    if k in names: continue
    names[k] = "Ocasionales" if "Ocasionales" not in names.values() else "En riesgo"
prof["segmento"] = prof.index.map(names); rfm["segmento"] = rfm.k.map(names)
prof["pct_clientes"] = prof.clientes / prof.clientes.sum(); prof["pct_ventas"] = prof.monto / prof.monto.sum()
prof = prof.set_index("segmento").loc[[s for s in ["Fieles", "Ocasionales", "En riesgo", "Perdidos"] if s in prof.segmento.values]]
fig, ax = plt.subplots(figsize=(10, 4.2)); y = np.arange(len(prof))
ax.barh(y + .2, prof.pct_clientes*100, .38, color=VERDE2, label="% de clientes"); ax.barh(y - .2, prof.pct_ventas*100, .38, color=VERDE, label="% de ventas")
ax.set_yticks(y, prof.index); ax.invert_yaxis(); ax.set_xlabel("%"); ax.legend(frameon=False, loc="lower right")
fi = prof.loc["Fieles"]; ax.set_title(f"Los clientes fieles son el {fi.pct_clientes:.0%} y dejan el {fi.pct_ventas:.0%} de las ventas")
fig.tight_layout(); fig.savefig(IMG/"segmentos.png", dpi=150); plt.close(fig)

# 4. Día y hora
dias = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
hm = v.drop_duplicates("orden").assign(dia=lambda d: d.fecha.dt.dayofweek).pivot_table(index="dia", columns="hora", values="orden", aggfunc="count", fill_value=0)
hm = hm.reindex(columns=range(24), fill_value=0)
fig, ax = plt.subplots(figsize=(10, 3.8)); im = ax.imshow(hm.values, aspect="auto", cmap="Greens")
ax.set_yticks(range(7), dias); ax.set_xticks(range(0, 24, 2), [f"{h}h" for h in range(0, 24, 2)])
pico = hm.stack().idxmax(); ax.set_title(f"Pico de compras: {dias[pico[0]]} a las {pico[1]} h"); fig.colorbar(im, ax=ax, label="Órdenes")
fig.tight_layout(); fig.savefig(IMG/"dia_hora.png", dpi=150); plt.close(fig)

with pd.ExcelWriter(REP/"reporte_ventas.xlsx", engine="openpyxl") as xw:
    m.rename("ventas").reset_index().to_excel(xw, sheet_name="Ventas mensuales", index=False)
    c.reset_index().round(3).to_excel(xw, sheet_name="Categorías", index=False)
    prof.reset_index()[["segmento", "clientes", "recencia", "frecuencia", "monto", "pct_clientes", "pct_ventas"]].round(2).to_excel(xw, sheet_name="Segmentos", index=False)
    rfm.reset_index()[["cliente", "recencia", "frecuencia", "monto", "segmento"]].round(0).to_excel(xw, sheet_name="Clientes", index=False)
    for ws in xw.book.worksheets:
        for col in ws.columns: ws.column_dimensions[col[0].column_letter].width = max(12, min(30, max(len(str(x.value or "")) for x in col) + 2))
        ws.freeze_panes = "A2"
res = dict(ordenes=int(v.orden.nunique()), clientes=int(v.cliente.nunique()), productos=len(p), crecimiento=crec, error_pron=err,
           pron_3m=float(fut.sum()), top_margen=top, top_margen_pct=float(c.loc[top].margen_pct),
           fieles_pct_cli=float(fi.pct_clientes), fieles_pct_ventas=float(fi.pct_ventas),
           en_riesgo=int(prof.loc["En riesgo"].clientes) if "En riesgo" in prof.index else 0,
           pico_dia=dias[pico[0]], pico_hora=int(pico[1]))
(REP/"resumen.json").write_text(json.dumps(res, ensure_ascii=False, indent=2)); print(json.dumps(res, ensure_ascii=False, indent=2)); print(prof.round(2))
