"""Análisis de abastecimiento: curva ABC, pronóstico de demanda, punto de pedido y desempeño de proveedores."""
import json
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA, IMG, REP = ROOT/"data", ROOT/"img", ROOT/"reporte"
IMG.mkdir(exist_ok=True); REP.mkdir(exist_ok=True)
VERDE, VERDE2, OSCURO, GRIS, ROJO, AMBAR = "#059669", "#6ee7b7", "#064e3b", "#9ca3af", "#dc2626", "#f59e0b"
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#cbd5e1", "axes.labelcolor": "#334155", "xtick.color": "#475569",
                     "ytick.color": "#475569", "axes.titleweight": "bold", "axes.titlesize": 13})

mat = pd.read_csv(DATA/"materiales.csv")
cons = pd.read_csv(DATA/"consumos_semanales.csv", parse_dates=["fecha"])
ped = pd.read_csv(DATA/"pedidos_compra.csv", parse_dates=["fecha_pedido", "fecha_prometida", "fecha_recepcion"])

# ---------- 1. Curva ABC (último año) ----------
ult_anio = cons[cons.fecha >= cons.fecha.max() - pd.Timedelta(weeks=52)]
anual = ult_anio.groupby("codigo").cantidad.sum().rename("consumo_anual")
abc = mat.set_index("codigo").join(anual)
abc["valor_anual"] = abc.consumo_anual * abc.precio_unitario
abc = abc.sort_values("valor_anual", ascending=False)
abc["pct_acum"] = abc.valor_anual.cumsum() / abc.valor_anual.sum()
abc["clase"] = np.where(abc.pct_acum <= .80, "A", np.where(abc.pct_acum <= .95, "B", "C"))
# el primer material que cruza el 80% también es A
first_b = abc.index[abc.clase.eq("B")][0] if (abc.clase == "B").any() else None

fig, ax = plt.subplots(figsize=(10, 4.6))
cols = abc.clase.map({"A": VERDE, "B": VERDE2, "C": GRIS})
ax.bar(range(len(abc)), abc.valor_anual / 1e6, color=cols)
ax2 = ax.twinx(); ax2.plot(range(len(abc)), abc.pct_acum * 100, color=OSCURO, lw=2, marker="o", ms=3)
ax2.axhline(80, color=OSCURO, ls=":", lw=1); ax2.axhline(95, color=OSCURO, ls=":", lw=1)
ax2.set_ylim(0, 105); ax2.set_ylabel("% acumulado"); ax2.spines["top"].set_visible(False)
ax.set_xticks([]); ax.set_ylabel("Valor anual (millones ARS)"); ax.set_xlabel("Materiales, de mayor a menor valor")
nA = (abc.clase == "A").sum()
ax.set_title(f"Curva ABC: {nA} de {len(abc)} materiales concentran el {abc[abc.clase=='A'].valor_anual.sum()/abc.valor_anual.sum():.0%} del valor")
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=VERDE, label="A"), Patch(color=VERDE2, label="B"), Patch(color=GRIS, label="C")], loc="center right", frameon=False)
fig.tight_layout(); fig.savefig(IMG/"curva_abc.png", dpi=150); plt.close(fig)

# ---------- 2. Pronóstico de demanda ----------
def features(t):
    return np.column_stack([t, np.sin(2*np.pi*t/52), np.cos(2*np.pi*t/52)])

res_pron, pron_prox = [], {}
for cod, g in cons.groupby("codigo"):
    y = g.sort_values("fecha").cantidad.values.astype(float); t = np.arange(len(y))
    tr, te = slice(0, len(y)-12), slice(len(y)-12, len(y))
    ma = np.full(12, y[tr][-4:].mean())                                  # promedio móvil 4 semanas
    lr = LinearRegression().fit(features(t[tr]), y[tr]).predict(features(t[te]))
    lr = np.clip(lr, 0, None)
    wape = lambda p: np.abs(y[te]-p).sum() / max(y[te].sum(), 1)
    res_pron.append(dict(codigo=cod, error_promedio_movil=wape(ma), error_regresion=wape(lr)))
    full = LinearRegression().fit(features(t), y)
    pron_prox[cod] = float(np.clip(full.predict(features(np.arange(len(y), len(y)+4))), 0, None).mean())
res_pron = pd.DataFrame(res_pron).set_index("codigo")
tot = cons.groupby("codigo").cantidad.sum()
err_ma = (res_pron.error_promedio_movil * tot).sum() / tot.sum()
err_lr = (res_pron.error_regresion * tot).sum() / tot.sum()

# gráfico del material A con más valor
top = abc.index[0]; g = cons[cons.codigo == top].sort_values("fecha"); y = g.cantidad.values.astype(float); t = np.arange(len(y))
fit = LinearRegression().fit(features(t[:-12]), y[:-12])
fig, ax = plt.subplots(figsize=(10, 4.2))
ax.plot(g.fecha, y, color=GRIS, lw=1.2, label="Consumo real")
ax.plot(g.fecha.iloc[-12:], np.clip(fit.predict(features(t[-12:])), 0, None), color=VERDE, lw=2.5, label="Pronóstico (regresión con estacionalidad)")
ax.plot(g.fecha.iloc[-12:], np.full(12, y[:-12][-4:].mean()), color=AMBAR, lw=2, ls="--", label="Promedio móvil 4 semanas")
ax.axvspan(g.fecha.iloc[-12], g.fecha.iloc[-1], color=VERDE2, alpha=.15)
ax.set_title(f"Pronóstico de demanda · {abc.loc[top, 'material']}"); ax.set_ylabel("Unidades por semana")
ax.legend(frameon=False, loc="upper left"); fig.tight_layout(); fig.savefig(IMG/"pronostico.png", dpi=150); plt.close(fig)

# ---------- 3. Stock de seguridad y punto de pedido ----------
Z = 1.65  # nivel de servicio 95%
sem = cons[cons.fecha >= cons.fecha.max() - pd.Timedelta(weeks=26)].groupby("codigo").cantidad.agg(["mean", "std"])
rp = mat.set_index("codigo").join(sem)
rp["demanda_semanal_pron"] = pd.Series(pron_prox)
rp["lt_sem"] = rp.lead_time_dias / 7
rp["stock_seguridad"] = np.ceil(Z * rp["std"] * np.sqrt(rp.lt_sem))
rp["punto_pedido"] = np.ceil(rp.demanda_semanal_pron * rp.lt_sem + rp.stock_seguridad)
rp["semanas_cobertura"] = rp.stock_actual / rp.demanda_semanal_pron.clip(lower=.1)
rp["estado"] = np.where(rp.stock_actual < rp.stock_seguridad, "Crítico",
               np.where(rp.stock_actual < rp.punto_pedido, "Pedir ya", "OK"))
rp["cantidad_sugerida"] = np.where(rp.estado != "OK", np.ceil(rp.punto_pedido + rp.demanda_semanal_pron*4 - rp.stock_actual), 0)
rp["clase"] = abc.clase
alertas = rp[rp.estado != "OK"].sort_values(["estado", "semanas_cobertura"])

fig, ax = plt.subplots(figsize=(10, 4.6))
cnt = rp.groupby(["clase", "estado"]).size().unstack(fill_value=0).reindex(columns=["Crítico", "Pedir ya", "OK"], fill_value=0)
left = np.zeros(len(cnt))
for est, c in zip(cnt.columns, [ROJO, AMBAR, VERDE]):
    ax.barh(cnt.index, cnt[est], left=left, color=c, label=est); left += cnt[est].values
ax.invert_yaxis(); ax.set_xlabel("Cantidad de materiales"); ax.set_ylabel("Clase ABC")
ax.set_title(f"Estado del stock: {len(alertas)} materiales necesitan reposición")
ax.set_xlim(0, left.max()*1.3); ax.legend(frameon=False, loc="center right"); fig.tight_layout(); fig.savefig(IMG/"estado_stock.png", dpi=150); plt.close(fig)

# ---------- 4. Desempeño de proveedores ----------
ped["demora_dias"] = (ped.fecha_recepcion - ped.fecha_prometida).dt.days
prov = ped.groupby("proveedor").agg(pedidos=("pedido", "count"),
                                    a_tiempo=("demora_dias", lambda d: (d <= 0).mean()),
                                    demora_media=("demora_dias", lambda d: d.clip(lower=0).mean())).sort_values("a_tiempo")
fig, ax = plt.subplots(figsize=(10, 4.2))
colp = [ROJO if v < .6 else AMBAR if v < .85 else VERDE for v in prov.a_tiempo]
ax.barh(prov.index, prov.a_tiempo*100, color=colp)
for i, (v, dm) in enumerate(zip(prov.a_tiempo, prov.demora_media)):
    ax.text(v*100+1, i, f"{v:.0%} · demora media {dm:.1f} días", va="center", fontsize=10, color="#334155")
ax.set_xlim(0, 125); ax.set_xlabel("% de pedidos entregados a tiempo"); ax.set_title("Cumplimiento de proveedores")
fig.tight_layout(); fig.savefig(IMG/"proveedores.png", dpi=150); plt.close(fig)

# ---------- Reporte Excel ----------
with pd.ExcelWriter(REP/"reporte_abastecimiento.xlsx", engine="openpyxl") as xw:
    a = alertas.reset_index()[["codigo", "material", "familia", "clase", "proveedor", "stock_actual", "stock_seguridad", "punto_pedido", "semanas_cobertura", "cantidad_sugerida", "estado"]]
    a.round(1).to_excel(xw, sheet_name="Alertas de reposición", index=False)
    abc.reset_index()[["codigo", "material", "familia", "consumo_anual", "precio_unitario", "valor_anual", "pct_acum", "clase"]].round(3).to_excel(xw, sheet_name="Curva ABC", index=False)
    rp.reset_index()[["codigo", "material", "demanda_semanal_pron", "lead_time_dias", "stock_seguridad", "punto_pedido", "stock_actual", "estado"]].round(1).to_excel(xw, sheet_name="Punto de pedido", index=False)
    prov.reset_index().round(3).to_excel(xw, sheet_name="Proveedores", index=False)
    for ws in xw.book.worksheets:
        for col in ws.columns:
            ws.column_dimensions[col[0].column_letter].width = max(12, min(34, max(len(str(c.value or "")) for c in col) + 2))
        ws.freeze_panes = "A2"

resumen = dict(materiales=len(mat), semanas=int(cons.fecha.nunique()), pedidos=len(ped),
               clase_a=int(nA), pct_valor_a=float(abc[abc.clase == "A"].valor_anual.sum()/abc.valor_anual.sum()),
               error_promedio_movil=float(err_ma), error_regresion=float(err_lr),
               criticos=int((rp.estado == "Crítico").sum()), pedir_ya=int((rp.estado == "Pedir ya").sum()),
               peor_proveedor=prov.index[0], peor_a_tiempo=float(prov.a_tiempo.iloc[0]),
               mejor_proveedor=prov.index[-1], mejor_a_tiempo=float(prov.a_tiempo.iloc[-1]))
(REP/"resumen.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=2))
alertas.reset_index()[["codigo", "material", "clase", "proveedor", "stock_actual", "punto_pedido", "semanas_cobertura", "cantidad_sugerida", "estado"]].round(1).to_csv(REP/"alertas.csv", index=False)
print(json.dumps(resumen, ensure_ascii=False, indent=2))
