## Prøv selv i Python

Koden under regner ut arbeidet en snorkraft gjør på en kjelke. Endre vinkelen eller kraften og trykk **Kjør**. Hva skjer når vinkelen nærmer seg 90°?

```{.python .kjor}
import numpy as np

F = 50        # snorkraft i newton
s = 20        # strekning i meter
theta = 30    # vinkel i grader

W = F * s * np.cos(np.radians(theta))
print(f"Arbeid: W = {W:.0f} J")
```

Her ser du arbeid som areal under grafen når kraften varierer langs strekningen. Prøv å bytte ut kraftfunksjonen:

```{.python .kjor}
import numpy as np
import matplotlib.pyplot as plt

s = np.linspace(0, 3000, 600)            # strekning i meter
F = 400 + 60 * np.sin(s / 250)           # kraften varierer litt underveis (N)

W = np.trapezoid(F, s)                   # arbeid = areal under grafen
print(f"Arbeid: W = {W/1e6:.2f} MJ")

plt.figure(figsize=(7, 3.2))
plt.plot(s, F, color="#3b9a2a", lw=2)
plt.fill_between(s, F, alpha=0.3, color="#6ef04a")
plt.xlabel("s (m)"); plt.ylabel("F (N)")
plt.title("W = arealet under kraft–strekning-grafen")
plt.ylim(0, 520)
plt.tight_layout()
plt.show()
```
