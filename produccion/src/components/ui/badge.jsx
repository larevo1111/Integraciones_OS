import { cva } from "class-variance-authority"
import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors whitespace-nowrap",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary text-primary-foreground",
        secondary: "border-transparent bg-secondary text-secondary-foreground",
        outline: "text-foreground border-border",
        solicitado: "border-blue-500/30 bg-blue-500/10 text-blue-400",
        programado: "border-amber-500/30 bg-amber-500/10 text-amber-400",
        en_produccion: "border-purple-500/30 bg-purple-500/10 text-purple-400",
        producido: "border-emerald-500/30 bg-emerald-500/10 text-emerald-400",
        validado: "border-green-500/30 bg-green-500/10 text-green-400",
        cancelado: "border-red-500/30 bg-red-500/10 text-red-400",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

function Badge({ className, variant, ...props }) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />
}

export { Badge, badgeVariants }
