# Marca — QMetrika

Sistema de marca aplicado a los tableros y demos (`board/*.html`, `demos/*.html`).
Tema **oscuro** base (`#0d1014`), acento **terracota**, paleta de estados "espectro cálido".

## Paleta

| Rol | Valor |
|---|---|
| Fondo (oscuro, base) | `#0d1014` |
| Texto | `#e3e9f2` · atenuado `#8c99ab` · tenue `#566173` |
| **Acento terracota** (primario, tema oscuro) | `#D98A5E` |
| Acento terracota profundo (rellenos) | `#A6542E` |
| Gold (firma / opus) | `#e0b049` · `#e3b15a` |

### Estados del tablero (espectro cálido)

| Estado | Valor |
|---|---|
| queued | `#9A9184` |
| capped / ⚡ sin presupuesto | `#e0902e` |
| working (acento) | `#D98A5E` |
| needs input | `#E8B04A` |
| review | `#CE8FA6` |
| done | `#93BA6C` |
| red / fail | `#E3705E` |

> Los colores de proveedor (`--opus`, `--sonnet`, `--gpt`, `--gemini`, `--local`) **no**
> son de marca: identifican familias de modelo y se mantienen.

## Tipografía

- Titulares / wordmark: **Space Grotesk** (`--sans`).
- Datos / etiquetas / navegación: **IBM Plex Mono** (`--mono`).
- Los Capital Boards conservan **Fraunces** para las cifras grandes (`--display`).

## Halo de fondo

Gradientes radiales en terracota: `rgba(217,138,94,.07–.09)` y `rgba(166,84,46,.07–.08)`.

## Logo (círculos concéntricos)

Versión para **fondo oscuro** (anillo claro, punto terracota), inline SVG:

```html
<svg width="22" height="22" viewBox="0 0 56 56" fill="none">
  <circle cx="28" cy="28" r="18" stroke="#e3e9f2" stroke-width="4.5"/>
  <circle cx="41" cy="41" r="9.6" fill="#0d1014"/>
  <circle cx="41" cy="41" r="7.4" fill="#e3e9f2"/>
  <circle cx="41" cy="41" r="5.4" fill="#D98A5E"/>
</svg>
```

Versión clara (papel): anillo `#1B1B18`, hueco `#E9E7E0`, punto interior `#A6542E`.

## Enlaces

El wordmark de cada cabecera y la firma **QMetrika Labs** enlazan a
`https://qmetrika.xyz` (`target="_blank" rel="noopener"`).

---

Aplicado en: `demos/index`, `demos/board-demo`, `demos/como-funciona`/`how-it-works`,
`board/agent-board`, `board/capital-board`, `board/capital-central` (ES y EN). La
presentación (solo local) sigue el mismo sistema.
