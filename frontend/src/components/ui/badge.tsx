import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva("inline-flex items-center rounded-full px-3 py-1 text-xs font-medium", {
  variants: {
    variant: {
      paid: "bg-sage text-foreground",
      pending: "bg-lavender text-foreground",
      overdue: "bg-rose/30 text-foreground",
      outline: "border border-border text-foreground",
    },
  },
  defaultVariants: {
    variant: "outline",
  },
});

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}
