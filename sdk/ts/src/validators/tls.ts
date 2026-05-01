import { ValidationResult } from "../types"

export function validateTls(url: string): ValidationResult {
  try {
    const parsed = new URL(url)
    if (parsed.protocol !== "https:") {
      return {
        valid: false,
        reason: `[DoorNo.402] BLOCKED -- payment refused over non-TLS connection: ${url}`,
      }
    }
    return { valid: true, reason: "TLS ok" }
  } catch {
    return { valid: false, reason: "invalid URL" }
  }
}

export function validateRedirect(
  originalUrl: string,
  finalUrl: string
): ValidationResult {
  try {
    const orig = new URL(originalUrl)
    const final_ = new URL(finalUrl)
    if (orig.hostname !== final_.hostname) {
      return {
        valid: false,
        reason: `[DoorNo.402] BLOCKED -- redirect hijack: ${orig.hostname} -> ${final_.hostname}`,
      }
    }
    if (orig.protocol === "https:" && final_.protocol === "http:") {
      return {
        valid: false,
        reason: "[DoorNo.402] BLOCKED -- TLS downgrade via redirect",
      }
    }
    return { valid: true, reason: "redirect is safe" }
  } catch {
    return { valid: false, reason: "invalid URL" }
  }
}
