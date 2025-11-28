import { SelectHTMLAttributes } from "react";
import { cn } from "../../lib/utils";

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  description?: string;
}

// Componente inspirado no select do shadcn, simplificado para não depender de portal/menu
export function Select({ label, description, className, children, ...props }: SelectProps) {
  return (
    <label className="flex w-full flex-col gap-1 text-sm font-medium text-slate-700">
      {label}
      <div className="relative">
        <select
          className={cn(
            "w-full appearance-none rounded-lg border border-slate-200 bg-white px-3 py-2 pr-10 text-left text-slate-900 shadow-sm transition focus:border-primary-500 focus:outline-none",
            className
          )}
          {...props}
        >
          {children}
        </select>
        <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-slate-400">▾</span>
      </div>
      {description && <span className="text-xs font-normal text-slate-500">{description}</span>}
    </label>
  );
}
