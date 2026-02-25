interface SpinnerProps {
  /** Size in Tailwind units (e.g. "4" → `h-4 w-4`). Default: "5". */
  size?: string;
  /** Additional Tailwind classes forwarded to the wrapper. */
  className?: string;
}

/**
 * Spinner — an animated circular progress indicator built purely with Tailwind.
 * Used throughout the app wherever asynchronous work is in progress.
 */
export function Spinner({ size = "5", className = "" }: SpinnerProps) {
  return (
    <span
      role="status"
      aria-label="Loading"
      data-testid="spinner"
      className={`inline-block h-${size} w-${size} animate-spin rounded-full
                  border-2 border-gray-300 border-t-blue-600 ${className}`}
    />
  );
}
