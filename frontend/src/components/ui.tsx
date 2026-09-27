import type { ReactNode } from "react";
import { LEVEL_COLOR } from "../lib/format";
import type { RiskLevel } from "../lib/types";

export function Panel({ title, aside, children, className = "" }: { title?: string; aside?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`rounded-lg border border-line bg-panel ${className}`}>
      {title && (
        <header className="flex flex-wrap items-baseline justify-between gap-2 border-b border-line-soft px-5 py-3">
          <h3 className="text-[15px] font-semibold">{title}</h3>
          {aside && <div className="text-sm text-ink-soft">{aside}</div>}
        </header>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}

export function Tip({ label, children }: { label: ReactNode; children: ReactNode }) {
  return (
    <span className="tip inline-flex items-center">
      <button type="button" className="inline-flex cursor-help items-center gap-1 text-left underline decoration-line decoration-dotted underline-offset-4">
        {label}
      </button>
      <span role="tooltip" className="tip-body">{children}</span>
    </span>
  );
}

export function LevelBadge({ level, size = "sm" }: { level: RiskLevel; size?: "sm" | "lg" }) {
  const color = LEVEL_COLOR[level];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-semibold ${size === "lg" ? "px-3 py-1 text-sm" : "px-2 py-0.5 text-xs"}`}
      style={{ color, background: `color-mix(in srgb, ${color} 12%, white)` }}
    >
      <span className="h-2 w-2 rounded-full" style={{ background: color }} aria-hidden />
      {level.charAt(0) + level.slice(1).toLowerCase()} risk
    </span>
  );
}

export function Message({ tone = "neutral", title, children, action }: { tone?: "neutral" | "error" | "warning"; title: string; children?: ReactNode; action?: ReactNode }) {
  const styles = {
    neutral: "border-line bg-panel",
    error: "border-[color:var(--color-risk-critical)]/30 bg-[#fbf1f2]",
    warning: "border-[color:var(--color-risk-medium)]/40 bg-[#fbf6ea]",
  }[tone];
  return (
    <div role={tone === "error" ? "alert" : "status"} className={`rounded-lg border px-5 py-4 ${styles}`}>
      <p className="font-semibold">{title}</p>
      {children && <div className="mt-1 text-sm text-ink-soft">{children}</div>}
      {action && <div className="mt-3">{action}</div>}
    </div>
  );
}

export function Skeleton({ className = "h-24" }: { className?: string }) {
  return <div className={`animate-pulse rounded-lg bg-line-soft ${className}`} aria-hidden />;
}

export function Button({ children, variant = "primary", ...props }: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "ghost" }) {
  const styles = {
    primary: "bg-ink text-white hover:bg-[#2b3a48] disabled:bg-ink-faint",
    secondary: "border border-line bg-panel text-ink hover:border-ink-faint disabled:text-ink-faint",
    ghost: "text-ink-soft hover:text-ink",
  }[variant];
  return (
    <button {...props} className={`inline-flex items-center justify-center gap-2 rounded-md px-3.5 py-2 text-sm font-semibold transition-colors disabled:cursor-not-allowed ${styles} ${props.className ?? ""}`}>
      {children}
    </button>
  );
}
