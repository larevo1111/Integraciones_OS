import * as React from "react"
import * as Popover from "@radix-ui/react-popover"
import { Check, ChevronDown, Search } from "lucide-react"
import { cn } from "@/lib/utils"

export function Combobox({ value, onChange, options, placeholder = "Seleccionar...", searchPlaceholder = "Buscar..." }) {
  const [open, setOpen] = React.useState(false)
  const [search, setSearch] = React.useState("")

  const filtered = React.useMemo(() => {
    const s = search.toLowerCase().trim()
    if (!s) return options.slice(0, 50)
    return options.filter(o =>
      (o.label || '').toLowerCase().includes(s) ||
      (o.value || '').toLowerCase().includes(s) ||
      (o.subtitle || '').toLowerCase().includes(s)
    ).slice(0, 50)
  }, [options, search])

  const selected = options.find(o => o.value === value)

  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger asChild>
        <button
          type="button"
          className="flex h-9 w-full items-center justify-between rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm ring-offset-background focus:outline-none focus:ring-1 focus:ring-ring cursor-pointer"
        >
          <span className={cn("truncate text-left", !selected && "text-muted-foreground")}>
            {selected ? selected.label : placeholder}
          </span>
          <ChevronDown className="h-4 w-4 opacity-50 shrink-0 ml-2" />
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          className="z-50 w-[var(--radix-popover-trigger-width)] max-w-none rounded-md border bg-card shadow-lg"
          sideOffset={4}
          align="start"
        >
          <div className="flex items-center border-b px-3 py-2 gap-2">
            <Search className="h-4 w-4 opacity-50 shrink-0" />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder={searchPlaceholder}
              className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
              autoFocus
            />
          </div>
          <div
            className="max-h-96 overflow-y-auto p-1"
            onWheel={e => e.stopPropagation()}
          >
            {filtered.length === 0 ? (
              <div className="px-2 py-6 text-center text-[13px] text-muted-foreground">Sin resultados</div>
            ) : filtered.map(opt => (
              <button
                key={opt.value}
                type="button"
                onClick={() => { onChange(opt.value, opt); setOpen(false); setSearch("") }}
                className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-[13px] text-left hover:bg-accent cursor-pointer"
              >
                <Check className={cn("h-4 w-4 shrink-0", opt.value === value ? "opacity-100" : "opacity-0")} />
                <div className="flex-1 min-w-0">
                  <div className="truncate">{opt.label}</div>
                  {opt.subtitle && <div className="text-[11px] text-muted-foreground truncate">{opt.subtitle}</div>}
                </div>
                {opt.badge && (
                  <span className="text-[11px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">{opt.badge}</span>
                )}
              </button>
            ))}
          </div>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  )
}
