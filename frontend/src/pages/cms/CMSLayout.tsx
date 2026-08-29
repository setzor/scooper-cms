import React from 'react';
import { Outlet, Navigate, Link, useLocation } from 'react-router-dom';
import { useAuthContext } from '../../contexts/AuthContext';
import { useThemeContext } from '../../contexts/ThemeContext';
import { ThemeToggle } from '../../components/ThemeToggle';
import { cn } from '../../utils/cn';
import { Menu, X, Home, FileText, Plus, Settings, Eye } from 'lucide-react';

export default function CMSLayout() {
  const { isAuthenticated, user, logout } = useAuthContext();
  const { theme } = useThemeContext();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);

  // Check if we're on a login page
  const isLoginPage = location.pathname === '/cms/login';

  // If not authenticated and not on login page, redirect to login
  if (!isAuthenticated && !isLoginPage) {
    return <Navigate to="/cms/login" replace />;
  }

  // If authenticated and on login page, redirect to dashboard
  if (isAuthenticated && isLoginPage) {
    return <Navigate to="/cms/dashboard" replace />;
  }

  // If we get here without being authenticated, redirect to login
  if (!isAuthenticated) {
    return <Navigate to="/cms/login" replace />;
  }

  const navItems = [
    { path: '/cms/dashboard', label: 'Dashboard', icon: Home },
    { path: '/cms/stories', label: 'Stories', icon: FileText },
    { path: '/cms/create', label: 'New Story', icon: Plus },
    { path: '/cms/settings', label: 'Settings', icon: Settings },
  ];

  return (
    <div className="min-h-screen flex">
      {/* Mobile Sidebar Overlay */}
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed top-0 left-0 z-50 h-full w-64 bg-cms-sidebar text-white transform transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static lg:z-auto',
          mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <div className="flex items-center justify-between h-16 px-4 border-b border-gray-700">
          <Link to="/cms/dashboard" className="flex items-center gap-2">
            <span className="text-xl">&#128394;</span>
            <span className="font-bold">Pencil</span>
          </Link>
          <button
            onClick={() => setMobileMenuOpen(false)}
            className="lg:hidden p-2 rounded-lg hover:bg-gray-700"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <nav className="p-4">
          <ul className="space-y-2">
            {navItems.map((item) => {
              const isActive = location.pathname === item.path || 
                (item.path === '/cms/stories' && location.pathname.startsWith('/cms/stories')) ||
                (item.path === '/cms/create' && location.pathname.startsWith('/cms/create'));
              
              return (
                <li key={item.path}>
                  <Link
                    to={item.path}
                    className={cn(
                      'flex items-center gap-3 px-4 py-3 rounded-lg transition-colors',
                      isActive
                        ? 'bg-primary-600 text-white'
                        : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                    )}
                    onClick={() => setMobileMenuOpen(false)}
                  >
                    <item.icon className="w-5 h-5" />
                    <span>{item.label}</span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-700 bg-cms-sidebar">
          <Link
            to="/"
            className="flex items-center gap-2 text-gray-300 hover:text-white transition-colors"
            target="_blank"
          >
            <Eye className="w-5 h-5" />
            <span>View Paper</span>
          </Link>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-h-screen">
        {/* Header */}
        <header className="h-16 flex items-center justify-between px-4 md:px-8 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setMobileMenuOpen(true)}
              className="lg:hidden p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
            >
              <Menu className="w-5 h-5" />
            </button>
            <h1 className="text-xl font-bold">
              {navItems.find((item) => 
                location.pathname === item.path ||
                (item.path === '/cms/stories' && location.pathname.startsWith('/cms/stories')) ||
                (item.path === '/cms/create' && location.pathname.startsWith('/cms/create'))
              )?.label || 'CMS'}
            </h1>
          </div>
          
          <div className="flex items-center gap-4">
            <ThemeToggle size="md" />
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-500 dark:text-gray-400">
                {user?.full_name || user?.username}
              </span>
              {user?.is_admin && (
                <span className="badge badge-published text-xs">Admin</span>
              )}
              <button
                onClick={logout}
                className="btn btn-secondary btn-sm"
              >
                Logout
              </button>
            </div>
          </div>
        </header>

        {/* Content */}
        <div className="flex-1 p-4 md:p-8">
          <Outlet />
        </div>

        {/* Mobile Bottom Navigation */}
        <nav className="lg:hidden fixed bottom-0 left-0 right-0 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 z-30">
          <div className="flex justify-around">
            {navItems.map((item) => {
              const isActive = location.pathname === item.path ||
                (item.path === '/cms/stories' && location.pathname.startsWith('/cms/stories')) ||
                (item.path === '/cms/create' && location.pathname.startsWith('/cms/create'));
              
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={cn(
                    'flex flex-col items-center gap-1 py-3 px-4',
                    isActive
                      ? 'text-primary-600 dark:text-primary-400'
                      : 'text-gray-500 dark:text-gray-400'
                  )}
                >
                  <item.icon className="w-5 h-5" />
                  <span className="text-xs">{item.label}</span>
                </Link>
              );
            })}
          </div>
        </nav>
      </main>
    </div>
  );
}
