import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { Theme, FontFamily } from '../types';

interface ThemeContextType {
  theme: Theme;
  fontFamily: FontFamily;
  toggleTheme: () => void;
  setFontFamily: (font: FontFamily) => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

interface ThemeProviderProps {
  children: ReactNode;
  initialTheme?: Theme;
  initialFontFamily?: FontFamily;
}

export function ThemeProvider({
  children,
  initialTheme = 'light',
  initialFontFamily = 'serif',
}: ThemeProviderProps) {
  const [theme, setTheme] = useState<Theme>(initialTheme);
  const [fontFamily, setFontFamily] = useState<FontFamily>(initialFontFamily);

  useEffect(() => {
    // Load from localStorage
    const savedTheme = localStorage.getItem('scooper-theme') as Theme | null;
    const savedFont = localStorage.getItem('scooper-font') as FontFamily | null;

    if (savedTheme && (savedTheme === 'light' || savedTheme === 'dark')) {
      setTheme(savedTheme);
    }

    if (savedFont && (savedFont === 'serif' || savedFont === 'sans')) {
      setFontFamily(savedFont);
    }
  }, []);

  useEffect(() => {
    // Update document
    document.documentElement.classList.remove('light', 'dark');
    document.documentElement.classList.add(theme);
    document.documentElement.setAttribute('data-theme', theme);
    document.documentElement.setAttribute('data-font', fontFamily);

    // Save to localStorage
    localStorage.setItem('scooper-theme', theme);
    localStorage.setItem('scooper-font', fontFamily);
  }, [theme, fontFamily]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'light' ? 'dark' : 'light'));
  };

  const handleSetFontFamily = (font: FontFamily) => {
    setFontFamily(font);
  };

  return (
    <ThemeContext.Provider value={{ theme, fontFamily, toggleTheme, setFontFamily: handleSetFontFamily }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useThemeContext() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useThemeContext must be used within a ThemeProvider');
  }
  return context;
}
