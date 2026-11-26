"""Genera un dataset SIMULADO de abastecimiento (consumos, pedidos y proveedores).
Los datos son ficticios y reproducibles (semilla fija). No corresponden a ninguna empresa real."""
import numpy as np, pandas as pd
from pathlib import Path

rng = np.random.default_rng(42)
DATA = Path(__file__).resolve().parents[1] / "data"
DATA.mkdir(exist_ok=True)

familias = {
    "Rodamientos": ["Rodamiento 6205", "Rodamiento 6308", "Rodamiento cónico 32210", "Rodamiento de rodillos NU210"],
    "Filtros": ["Filtro de aceite", "Filtro de aire", "Filtro de combustible", "Filtro hidráulico"],
    "Frenos": ["Zapata de freno", "Pastilla de freno", "Disco de freno", "Válvula de freno"],
    "Eléctrico": ["Contactor 40A", "Relé 24V", "Fusible 63A", "Cable 4mm (rollo)", "Lámpara LED"],
    "Lubricantes": ["Aceite 15W40 (20L)", "Grasa EP2 (18kg)", "Aceite hidráulico (20L)"],
    "Ferretería": ["Bulón M16", "Tuerca M16", "Arandela M16", "Abrazadera 2\"", "Junta tórica"],
    "Seguridad": ["Guantes de trabajo", "Casco", "Anteojos de seguridad", "Chaleco reflectivo"],
    "Neumática": ["Electroválvula", "Manguera neumática", "Cilindro neumático", "Racor rápido"],
}
proveedores = ["Proveedor A", "Proveedor B", "Proveedor C", "Proveedor D", "Proveedor E", "Proveedor F"]
prov_demora = dict(zip(proveedores, [-2, 0, 3, -1, 6, 1]))      # demora media extra (días)
prov_lead = dict(zip(proveedores, [10, 15, 25, 12, 30, 20]))     # lead time pactado

rows = []
for fam, items in familias.items():
    for it in items:
        precio = float(np.round(rng.lognormal(mean=9.2, sigma=1.1), -1))   # ARS
        base = float(rng.gamma(2.0, 25 if precio < 20000 else 6))
        rows.append(dict(familia=fam, material=it, precio_unitario=precio,
                         consumo_base=base, estacionalidad=float(rng.uniform(0, .35)),
                         tendencia=float(rng.normal(0.004, 0.006)),
                         proveedor=rng.choice(proveedores)))
mat = pd.DataFrame(rows)
mat.insert(0, "codigo", [f"MAT-{1000+i}" for i in range(len(mat))])
mat["lead_time_dias"] = mat.proveedor.map(prov_lead)
mat["stock_actual"] = 0

# consumos semanales: 2 años
semanas = pd.date_range("2024-01-01", periods=104, freq="W-MON")
cons = []
for _, m in mat.iterrows():
    t = np.arange(len(semanas))
    media = m.consumo_base * (1 + m.tendencia) ** t * (1 + m.estacionalidad * np.sin(2*np.pi*t/52))
    q = rng.poisson(np.clip(media, 0.1, None))
    cons += [dict(fecha=d, codigo=m.codigo, cantidad=int(x)) for d, x in zip(semanas, q)]
consumos = pd.DataFrame(cons)

# stock actual: algunos materiales quedan bajos a propósito
ult = consumos[consumos.fecha >= semanas[-8]].groupby("codigo").cantidad.mean()
mat["stock_actual"] = [int(max(0, ult[c] * rng.uniform(0.5, 9))) for c in mat.codigo]

# pedidos de compra con fecha prometida y recibida
peds = []
n = 0
for _, m in mat.iterrows():
    for d in semanas[::rng.integers(3, 7)]:
        n += 1
        prom = d + pd.Timedelta(days=int(m.lead_time_dias))
        demora = int(max(-3, rng.normal(prov_demora[m.proveedor], 3)))
        peds.append(dict(pedido=f"OC-{50000+n}", codigo=m.codigo, proveedor=m.proveedor,
                         fecha_pedido=d, fecha_prometida=prom, fecha_recepcion=prom + pd.Timedelta(days=demora),
                         cantidad=int(m.consumo_base * rng.uniform(3, 6)) + 1))
pedidos = pd.DataFrame(peds)

mat.drop(columns=["consumo_base", "estacionalidad", "tendencia"]).to_csv(DATA/"materiales.csv", index=False)
consumos.to_csv(DATA/"consumos_semanales.csv", index=False)
pedidos.to_csv(DATA/"pedidos_compra.csv", index=False)
print(len(mat), "materiales |", len(consumos), "consumos |", len(pedidos), "pedidos")
