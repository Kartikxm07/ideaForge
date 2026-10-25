import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatNumber(val: number | string | null | undefined): string {
  if (val == null) return "—";
  const num = typeof val === "number" ? val : Number(val);
  if (isNaN(num)) return String(val);
  return num.toLocaleString("en-US");
}

export function formatCurrency(val: number | string | null | undefined): string {
  if (val == null) return "—";
  const num = typeof val === "number" ? val : Number(val);
  if (isNaN(num)) return "—";
  return `$${num.toLocaleString("en-US")}`;
}
