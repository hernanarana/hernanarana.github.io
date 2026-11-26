"""Genera ventas SIMULADAS de una tienda online (2 años). Datos ficticios, semilla fija."""
import numpy as np, pandas as pd
from pathlib import Path
rng = np.random.default_rng(7)
DATA = Path(__file__).resolve().parents[1] / "data"; DATA.mkdir(exist_ok=True)
cats = {"Perfumería": (38000, .42), "Cuidado personal": (12000, .38), "Accesorios": (9000, .55),
        "Hogar": (22000, .30), "Regalos": (18000, .48)}
prods = []
for c, (p, m) in cats.items():
    for i in range(8):
        precio = round(p * rng.uniform(.5, 1.8), -2)
        prods.append(dict(producto=f"{c[:4].upper()}-{i+1:02d}", categoria=c, precio=precio, costo=round(precio * (1 - m * rng.uniform(.8, 1.2)), -2)))
prods = pd.DataFrame(prods)
pop = rng.dirichlet(np.ones(len(prods)) * .6)
n_cli = 1800
cli_act = rng.gamma(1.2, 1.0, n_cli)
fechas = pd.date_range("2024-01-01", "2025-12-31", freq="D")
rows = []; oid = 0
for f in fechas:
    t = (f - fechas[0]).days
    base = 22 * (1 + .0012 * t)
    estac = 1 + .35 * np.sin(2 * np.pi * (f.dayofyear - 80) / 365)
    if f.month == 12: estac *= 1.8
    if f.month == 11 and 25 <= f.day <= 30: estac *= 2.4   # Black Friday
    if f.month == 5 and 10 <= f.day <= 14: estac *= 1.9    # Hot Sale
    if f.dayofweek >= 5: estac *= .8
    for _ in range(rng.poisson(base * estac)):
        oid += 1
        c = rng.choice(n_cli, p=cli_act / cli_act.sum())
        hora = int(round(rng.normal(20, 3))) % 24
        for _ in range(rng.choice([1, 1, 1, 2, 2, 3])):
            j = rng.choice(len(prods), p=pop)
            rows.append(dict(orden=f"P{oid:06d}", fecha=f, hora=hora, cliente=f"C{c:04d}", producto=prods.producto[j], cantidad=int(rng.choice([1, 1, 1, 2]))))
v = pd.DataFrame(rows)
prods.to_csv(DATA/"productos.csv", index=False); v.to_csv(DATA/"ventas.csv", index=False)
print(len(prods), "productos |", v.orden.nunique(), "órdenes |", len(v), "líneas")
