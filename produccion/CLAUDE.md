# Producción OS — Programación de Producción

## Stack

| Capa | Tecnología |
|---|---|
| Framework base | React 18 |
| Bundler | Vite |
| Admin framework | Refine (CRUDs, auth, permisos, layouts) |
| UI library | Shadcn/ui (componentes en `src/components/ui/`) |
| Estilos | Tailwind CSS v4 (única vía, cero CSS custom) |
| Routing | React Router v7 |
| Data provider | @refinedev/simple-rest (API REST) |

## Estructura

```
produccion/
├── src/
│   ├── components/
│   │   ├── ui/          # Shadcn/ui components (button, card, etc.)
│   │   └── layout.jsx   # Layout principal con header
│   ├── pages/
│   │   └── dashboard.jsx
│   ├── providers/       # Auth provider, data provider custom
│   ├── lib/
│   │   └── utils.js     # cn() helper para class merging
│   ├── App.jsx          # Refine config + routes
│   ├── main.jsx         # Entry point
│   └── index.css        # Tailwind + theme vars
├── vite.config.js       # Vite + Tailwind plugin + alias @/
├── package.json
└── CLAUDE.md
```

## Reglas

- **Tailwind only** — cero CSS custom, cero style=, cero styled-components
- **Shadcn/ui** — copiar componentes a `src/components/ui/`, no instalar como paquete
- **JavaScript** — no TypeScript
- **Dark mode** — tema dark por defecto (variables en index.css)
- **Acento verde** (#22c55e) — consistente con el resto de OS

## Comandos

```bash
cd produccion
npm run dev    # Dev server (port 5173)
npm run build  # Build a dist/
```

## Agregar componentes Shadcn/ui

Los componentes se copian manualmente a `src/components/ui/`. Referencia: https://ui.shadcn.com/docs/components

Cada componente usa:
- `cn()` de `@/lib/utils` para merge de clases
- `cva` de `class-variance-authority` para variants
- `@radix-ui/*` para primitivos accesibles

## API

El data provider apunta a `{origin}/api`. La API de producción se servirá desde el mismo backend (por definir).
