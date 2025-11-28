import { cn } from "../../lib/utils";

interface BadgeProps {
  children: React.ReactNode;
  tone?: "info" | "success" | "warning" | "danger";
}

export function Badge({ children, tone = "info" }: BadgeProps) {
  const classes = {
    info: "bg-blue-50 text-blue-700 border border-blue-100",
    success: "bg-green-50 text-green-700 border border-green-100",
    warning: "bg-amber-50 text-amber-700 border border-amber-100",
    danger: "bg-rose-50 text-rose-700 border border-rose-100",
  }[tone];
  return <span className={cn("tag", classes)}>{children}</span>;
}
