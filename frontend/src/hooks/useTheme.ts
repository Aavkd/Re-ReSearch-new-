import { useEffect } from "react";
import { useSettingsStore } from "../stores/settingsStore";

/**
 * Applies the user's selected theme to <html class="dark"> so Tailwind's
 * darkMode:"class" variant activates correctly.
 *
 * Mount this once near the app root (e.g. in App.tsx or main.tsx).
 */
export function useTheme() {
  const theme = useSettingsStore((s) => s.theme);

  useEffect(() => {
    const root = document.documentElement;
    const applyDark = () => root.classList.add("dark");
    const applyLight = () => root.classList.remove("dark");

    if (theme === "dark") {
      applyDark();
    } else if (theme === "light") {
      applyLight();
    } else {
      // system — follow OS preference
      const mq = window.matchMedia("(prefers-color-scheme: dark)");
      mq.matches ? applyDark() : applyLight();
      const handler = (e: MediaQueryListEvent) =>
        e.matches ? applyDark() : applyLight();
      mq.addEventListener("change", handler);
      return () => mq.removeEventListener("change", handler);
    }
  }, [theme]);
}
