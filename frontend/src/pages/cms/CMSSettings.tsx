import React, { useState, useEffect, useCallback } from 'react';
import { useThemeContext } from '../../contexts/ThemeContext';
import { cn, api } from '../../utils';
import { Save, Sun, Moon, Type } from 'lucide-react';

interface SettingsData {
  site_title: string;
  theme: string;
  settings: {
    site_title: string;
    site_description: string;
    theme: string;
    font_family: string;
  };
  user: {
    username: string;
    full_name: string | null;
    is_admin: boolean;
  };
  csrf_token: string;
}

export default function CMSSettings() {
  const { theme: currentTheme, setFontFamily } = useThemeContext();
  const [data, setData] = useState<SettingsData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [siteTitle, setSiteTitle] = useState('');
  const [siteDescription, setSiteDescription] = useState('');
  const [theme, setTheme] = useState('light');
  const [fontFamily, setFontFamilyLocal] = useState('serif');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await api.get('/cms/settings');
      setData(response.data);
      
      // Set form values
      setSiteTitle(response.data.settings.site_title || '');
      setSiteDescription(response.data.settings.site_description || '');
      setTheme(response.data.settings.theme || 'light');
      setFontFamilyLocal(response.data.settings.font_family || 'serif');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load settings');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Sync font family with context
  useEffect(() => {
    if (fontFamily) {
      setFontFamily(fontFamily as 'serif' | 'sans');
    }
  }, [fontFamily, setFontFamily]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('site_title', siteTitle);
      formData.append('site_description', siteDescription);
      formData.append('theme', theme);
      formData.append('font_family', fontFamily);
      formData.append('csrf_token', data?.csrf_token || '');

      await api.post('/cms/settings', formData);
      
      // Refresh data
      fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save settings');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading && !data) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-red-500 mb-4">{error}</p>
        <button onClick={fetchData} className="btn btn-primary">
          Retry
        </button>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="text-center py-12">
        <p>No data available</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold mb-2">Site Settings</h1>
        <p className="text-gray-500 dark:text-gray-400">
          Configure your site's appearance and basic information
        </p>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-6">
        <div
          className={cn(
            'cms-card space-y-6',
            currentTheme === 'light' ? 'bg-white' : 'bg-gray-800'
          )}
        >
          {/* Site Information */}
          <div>
            <h2 className="text-lg font-semibold mb-4 pb-2 border-b border-gray-200 dark:border-gray-700">
              Site Information
            </h2>
            
            <div className="space-y-4">
              <div>
                <label htmlFor="site_title" className="block text-sm font-medium mb-1">
                  Site Title *
                </label>
                <input
                  type="text"
                  id="site_title"
                  value={siteTitle}
                  onChange={(e) => setSiteTitle(e.target.value)}
                  className="input"
                  placeholder="Enter your site title"
                  required
                />
              </div>
              <div>
                <label htmlFor="site_description" className="block text-sm font-medium mb-1">
                  Site Description
                </label>
                <textarea
                  id="site_description"
                  value={siteDescription}
                  onChange={(e) => setSiteDescription(e.target.value)}
                  className="textarea"
                  placeholder="Enter a brief description of your site"
                  rows={3}
                />
              </div>
            </div>
          </div>

          {/* Appearance */}
          <div>
            <h2 className="text-lg font-semibold mb-4 pb-2 border-b border-gray-200 dark:border-gray-700">
              Appearance
            </h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Theme</label>
                <div className="flex gap-4">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="theme"
                      value="light"
                      checked={theme === 'light'}
                      onChange={() => setTheme('light')}
                      className="w-4 h-4"
                    />
                    <Sun className="w-5 h-5 text-yellow-500" />
                    <span>Light</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="theme"
                      value="dark"
                      checked={theme === 'dark'}
                      onChange={() => setTheme('dark')}
                      className="w-4 h-4"
                    />
                    <Moon className="w-5 h-5 text-blue-400" />
                    <span>Dark</span>
                  </label>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">
                  Font Family
                </label>
                <div className="flex gap-4">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="font_family"
                      value="serif"
                      checked={fontFamily === 'serif'}
                      onChange={() => setFontFamilyLocal('serif')}
                      className="w-4 h-4"
                    />
                    <Type className="w-5 h-5" />
                    <span className="font-serif">Serif</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="font_family"
                      value="sans"
                      checked={fontFamily === 'sans'}
                      onChange={() => setFontFamilyLocal('sans')}
                      className="w-4 h-4"
                    />
                    <Type className="w-5 h-5" />
                    <span className="font-sans">Sans</span>
                  </label>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end gap-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <button
            type="submit"
            className="btn btn-primary"
            disabled={isSubmitting}
          >
            {isSubmitting ? (
              <span className="flex items-center gap-2">
                <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></span>
                Saving...
              </span>
            ) : (
              <span className="flex items-center gap-2">
                <Save className="w-4 h-4" />
                Save Settings
              </span>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
