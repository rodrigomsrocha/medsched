import { ButtonHTMLAttributes } from "react";
import { cn } from "../../lib/utils";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost";
  loading?: boolean;
}

export function Button({
  variant = "primary",
  className,
  loading,
  children,
  disabled,
  ...props
}: ButtonProps) {
  const base = {
    primary: "bg-primary-600 hover:bg-primary-700 text-white shadow-sm",
    secondary: "bg-white border border-slate-200 hover:bg-slate-50 text-slate-900",
    ghost: "bg-transparent hover:bg-slate-100 text-slate-700",
  }[variant];

  return (
    <button
      className={cn(
        "btn px-4 py-2 rounded-md",
        base,
        loading && "opacity-70",
        className
      )}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? "Carregando..." : children}
    </button>
  );
}
