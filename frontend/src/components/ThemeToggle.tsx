import React from 'react';
import { useThemeContext } from '../contexts/ThemeContext';
import { Sun, Moon } from 'lucide-react';

interface ThemeToggleProps {
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

export function ThemeToggle({ className = '', size = 'md' }: ThemeToggleProps) {
  const { theme, toggleTheme } = useThemeContext();

  const sizeClasses = {
    sm: 'w-5 h-5',
    md: 'w-6 h-6',
    lg: 'w-7 h-7',
  };

  return (
    <button
      onClick={toggleTheme}
      className={`flex items-center justify-center p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors ${className}`}
      aria-label="Toggle theme"
      title="Toggle dark/light mode"
    >
      {theme === 'light' ? (
        <Sun className={`text-yellow-500 ${sizeClasses[size]}`} />
      ) : (
        <Moon className={`text-blue-400 ${sizeClasses[size]}`} />
      )}
    </button>
  );
}
