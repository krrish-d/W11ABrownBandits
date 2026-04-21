import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function getInvoiceStatus(status: string, dueDate?: string) {
  if (status?.toLowerCase() === "paid") return "paid";
  if (dueDate && new Date(dueDate).getTime() < Date.now()) return "overdue";
  return "pending";
}
