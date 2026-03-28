import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000"

export function resolveBackendUrl(path?: string | null) {
  if (!path) {
    return null
  }

  try {
    return new URL(path, API_BASE_URL).toString()
  } catch {
    return null
  }
}
