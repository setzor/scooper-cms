import React from 'react';
import { Outlet } from 'react-router-dom';
import { useThemeContext } from '../../contexts/ThemeContext';
import { ThemeToggle } from '../../components/ThemeToggle';
import { cn } from '../../utils/cn';

export default function PaperLayout() {
  const { theme, fontFamily } = useThemeContext();

  return (
    <div
      className={cn(
        'min-h-screen transition-colors duration-300',
        theme === 'light' ? 'bg-paper-light text-paper-text' : 'bg-paper-dark text-paper-text'
      )}
      data-theme={theme}
      data-font={fontFamily}
    >
      <header className="paper-header border-b border-paper-border dark:border-gray-700 sticky top-0 z-50 bg-paper-light dark:bg-paper-dark/80 backdrop-blur-sm">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <a href="/" className="text-xl font-bold font-serif">
                Scooper Paper
              </a>
              <span className="text-paper-text-secondary text-sm hidden md:block">
                Your News, Delivered
              </span>
            </div>
            <div className="flex items-center gap-2">
              <ThemeToggle size="md" />
              <a
                href="/cms"
                className="btn btn-secondary btn-sm flex items-center gap-2"
              >
                <span>&#128394;</span>
                <span className="hidden md:inline">CMS</span>
              </a>
            </div>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <Outlet />
      </main>

      <footer className="paper-footer border-t border-paper-border dark:border-gray-700 mt-16 py-8">
        <div className="container mx-auto px-4">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <p className="text-paper-footer-text text-sm">
              &copy; {new Date().getFullYear()} Scooper Paper. All rights reserved.
            </p>
            <div className="flex items-center gap-4">
              <a
                href="/cms"
                className="text-paper-footer-text hover:text-primary-400 transition-colors text-sm"
              >
                &#128394; Pencil
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
