import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
/**
 * Parse a UTC ISO string (without Z indicator) into a proper Date object
 * Ensures the string is treated as UTC, not local time
 */
export function parseUTCDateTime(dateString: string | null | undefined): Date | null {
  if (!dateString) return null
  
  try {
    // Append 'Z' if not present to explicitly mark as UTC
    const utcString = dateString.endsWith('Z') ? dateString : dateString + 'Z'
    return new Date(utcString)
  } catch (e) {
    console.error('Date parsing error:', e, dateString)
    return null
  }
}

/**
 * Convert UTC ISO string to local time and format it
 * Explicitly treats incoming times as UTC and converts to local timezone
 */
export function formatLocalDateTime(dateString: string | null | undefined): string {
  const date = parseUTCDateTime(dateString)
  if (!date) return 'N/A'
  
  try {
    // Format in local timezone
    const formatted = date.toLocaleString('en-US', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true,
      timeZoneName: 'short'
    })
    
    return formatted
  } catch (e) {
    console.error('Date formatting error:', e)
    return 'Invalid date'
  }
}