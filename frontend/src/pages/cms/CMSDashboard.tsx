import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuthContext } from '../../contexts/AuthContext';
import { useThemeContext } from '../../contexts/AuthContext';
import { formatDate, formatRelativeDate } from '../../utils/formatDate';
import { cn, api } from '../../utils';
import { Plus, FileText, CheckCircle, Clock, Tag, Eye } from 'lucide-react';

interface DashboardData {
  site_title: string;
  theme: string;
  stats: {
    total_stories: number;
    published_count: number;
    draft_count: number;
    categories_count: number;
  };
  recent_stories: Array<{
    id: number;
    title: string;
    slug: string;
    published: boolean;
    published_at: string | null;
  }>;
  user: {
    username: string;
    full_name: string | null;
    is_admin: boolean;
  };
}

export default function CMSDashboard() {
  const { user } = useAuthContext();
  const { theme } = useThemeContext();
  const [data, setData] = useState<DashboardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const response = await api.get('/cms/dashboard');
        setData(response.data);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load dashboard');
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, []);

  if (isLoading) {
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
        <button onClick={() => window.location.reload()} className="btn btn-primary">
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
    <div className="space-y-8">
      {/* Welcome */}
      <div>
        <h1 className="text-2xl font-bold mb-2">
          Welcome back, {user?.full_name || user?.username}!
        </h1>
        <p className="text-gray-500 dark:text-gray-400">
          Here's what's happening with your site.
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="stat-card">
          <div className="flex items-center justify-between mb-2">
            <FileText className="w-8 h-8 text-primary-600" />
            <span className="text-sm text-green-500 font-medium">+0%</span>
          </div>
          <div className="stat-number">{data.stats.total_stories}</div>
          <div className="stat-label">Total Stories</div>
        </div>

        <div className="stat-card">
          <div className="flex items-center justify-between mb-2">
            <CheckCircle className="w-8 h-8 text-green-500" />
            <span className="text-sm text-green-500 font-medium">
              {data.stats.published_count > 0 ? '+' : ''}
            </span>
          </div>
          <div className="stat-number">{data.stats.published_count}</div>
          <div className="stat-label">Published</div>
        </div>

        <div className="stat-card">
          <div className="flex items-center justify-between mb-2">
            <Clock className="w-8 h-8 text-yellow-500" />
            <span className="text-sm text-yellow-500 font-medium">
              {data.stats.draft_count > 0 ? '+' : ''}
            </span>
          </div>
          <div className="stat-number">{data.stats.draft_count}</div>
          <div className="stat-label">Drafts</div>
        </div>

        <div className="stat-card">
          <div className="flex items-center justify-between mb-2">
            <Tag className="w-8 h-8 text-purple-500" />
          </div>
          <div className="stat-number">{data.stats.categories_count}</div>
          <div className="stat-label">Categories</div>
        </div>
      </div>

      {/* Recent Stories */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div
          className={cn(
            'cms-card',
            theme === 'light' ? 'bg-white' : 'bg-gray-800'
          )}
        >
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold">Recent Stories</h2>
            <Link to="/cms/stories" className="btn btn-secondary btn-sm">
              View All
            </Link>
          </div>

          {data.recent_stories.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-gray-500 dark:text-gray-400">No stories yet</p>
              <Link to="/cms/create" className="btn btn-primary mt-4">
                <Plus className="w-4 h-4 mr-2" />
                Create Story
              </Link>
            </div>
          ) : (
            <div className="space-y-4">
              {data.recent_stories.map((story) => (
                <Link
                  key={story.id}
                  to={`/cms/edit/${story.id}`}
                  className="flex items-center justify-between p-4 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors group"
                >
                  <div className="flex-1">
                    <h3 className="font-medium group-hover:text-primary-600 transition-colors">
                      {story.title}
                    </h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      {formatRelativeDate(story.published_at || story.created_at)}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    {story.published ? (
                      <span className="badge badge-published">Published</span>
                    ) : (
                      <span className="badge badge-draft">Draft</span>
                    )}
                    <Eye className="w-4 h-4 text-gray-400" />
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Quick Actions */}
        <div
          className={cn(
            'cms-card',
            theme === 'light' ? 'bg-white' : 'bg-gray-800'
          )}
        >
          <h2 className="text-lg font-bold mb-4">Quick Actions</h2>
          <div className="space-y-3">
            <Link to="/cms/create" className="btn btn-primary w-full">
              <Plus className="w-4 h-4 mr-2" />
              Create New Story
            </Link>
            <Link to="/cms/stories" className="btn btn-secondary w-full">
              <FileText className="w-4 h-4 mr-2" />
              View All Stories
            </Link>
            <Link to="/cms/settings" className="btn btn-secondary w-full">
              <Settings className="w-4 h-4 mr-2" />
              Site Settings
            </Link>
            <Link to="/" className="btn btn-secondary w-full" target="_blank">
              <Eye className="w-4 h-4 mr-2" />
              View Paper Site
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

// Import Settings icon
import { Settings } from 'lucide-react';
