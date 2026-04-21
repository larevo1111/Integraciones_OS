import { cva } from "class-variance-authority"
import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded px-1.5 h-5 text-[11px] font-medium whitespace-nowrap",
  {
    variants: {
      variant: {
        default: "bg-primary/15 text-primary",
        secondary: "bg-accent text-accent-foreground",
        outline: "text-muted-foreground border border-border",
        solicitado: "bg-blue-500/12 text-blue-400",
        programado: "bg-amber-500/12 text-amber-400",
        en_produccion: "bg-violet-500/12 text-violet-400",
        producido: "bg-emerald-500/12 text-emerald-400",
        validado: "bg-green-500/12 text-green-400",
        cancelado: "bg-red-500/12 text-red-400",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

function Badge({ className, variant, ...props }) {
  return (
    <span className={cn(badgeVariants({ variant }), className)}>
      <span className="w-1 h-1 rounded-full bg-current opacity-80" />
      <span>{props.children}</span>
    </span>
  )
}

export { Badge, badgeVariants }
