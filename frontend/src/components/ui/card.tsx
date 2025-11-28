import { cn } from "../../lib/utils";
import { PropsWithChildren, ReactNode } from "react";

interface CardProps extends PropsWithChildren {
  title?: string;
  className?: string;
  description?: string;
  action?: ReactNode;
}

export function Card({ title, description, className, action, children }: CardProps) {
  return (
    <div className={cn("card-glow rounded-2xl border border-slate-100 p-6", className)}>
      <div className="flex items-start justify-between gap-3">
        <div>
          {title && <h3 className="text-lg font-semibold text-slate-900">{title}</h3>}
          {description && <p className="text-sm text-slate-600 mt-1">{description}</p>}
        </div>
        {action}
      </div>
      <div className="mt-4">{children}</div>
    </div>
  );
}
