import { InputHTMLAttributes } from "react";
import { cn } from "../../lib/utils";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  description?: string;
}

export function Input({ label, description, className, ...props }: InputProps) {
  return (
    <label className="flex w-full flex-col gap-1 text-sm font-medium text-slate-700">
      {label}
      <input
        className={cn(
          "w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-slate-900 shadow-sm focus:border-primary-500 focus:outline-none",
          className
        )}
        {...props}
      />
      {description && <span className="text-xs font-normal text-slate-500">{description}</span>}
    </label>
  );
}
