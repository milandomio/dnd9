import { createContext, useContext, useState, useEffect, type ReactNode } from "react";

export interface ThemeTokens {
  bg: string;
  surface: string;
  card: string;
  text: string;
  muted: string;
  border: string;
  accent: string;
}

const LIGHT: ThemeTokens = {
  bg: "#f5f5f5",
  surface: "#e0e0e0",
  card: "#d0d0d0",
  text: "#1a1a1a",
  muted: "#666",
  border: "#bbb",
  accent: "#0097a7",
};

const DARK: ThemeTokens = {
  bg: "#2c2c2c",
  surface: "#3a3a3a",
  card: "#444",
  text: "#ffffff",
  muted: "#aaa",
  border: "#555",
  accent: "#00bcd4",
};

const ThemeCtx = createContext<{
  dark: boolean;
  tokens: ThemeTokens;
  toggle: () => void;
}>({ dark: true, tokens: DARK, toggle: () => {} });

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [dark, setDark] = useState(true);
  const toggle = () => setDark((v) => !v);
  const tokens = dark ? DARK : LIGHT;

  useEffect(() => {
    const bg = dark ? "#2c2c2c" : "#f5f5f5";
    document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
    document.documentElement.style.background = bg;
    document.body.style.background = bg;
    document.body.style.margin = "0";
  }, [dark]);

  return <ThemeCtx.Provider value={{ dark, tokens, toggle }}>{children}</ThemeCtx.Provider>;
}

export function useTheme() {
  return useContext(ThemeCtx);
}
