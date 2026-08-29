import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useThemeContext } from '../../contexts/ThemeContext';
import { formatDate, formatRelativeDate } from '../../utils/formatDate';
import { cn, api } from '../../utils';
import { Plus, Search, Filter, Eye, Edit, Trash2, CheckCircle, Clock } from 'lucide-react';

interface Story {
  id: number;
  title: string;
  slug: string;
  author: string;
  category: string;
  published: boolean;
  featured_image: string | null;
  published_at: string | null;
  updated_at: string | null;
}

interface Pagination {
  current_page: number;
  total_pages: number;
  total_count: number;
  has_previous: boolean;
  has_next: boolean;
}

interface Category {
  id: number;
  name: string;
}

interface StoriesData {
  site_title: string;
  theme: string;
  stories: Story[];
  pagination: Pagination;
  filters: {
    status?: string;
    category?: string;
    search?: string;
  };
  categories: Category[];
  user: {
    username: string;
    is_admin: boolean;
  };
}

type StoryStatus = 'all' | 'published' | 'draft';

export default function CMSStories() {
  const { theme } = useThemeContext();
  const [data, setData] = useState<StoriesData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<StoryStatus>('all');
  const [categoryFilter, setCategoryFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');

  const fetchData = useCallback(async (page = 1) => {
    setIsLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({
        page: page.toString(),
      });

      if (statusFilter !== 'all') {
        params.set('status', statusFilter);
      }
      if (categoryFilter) {
        params.set('category', categoryFilter);
      }
      if (searchQuery) {
        params.set('search', searchQuery);
      }

      const response = await api.get(`/cms/stories?${params.toString()}`);
      setData(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load stories');
    } finally {
      setIsLoading(false);
    }
  }, [statusFilter, categoryFilter, searchQuery]);

  useEffect(() => {
    fetchData(1);
  }, [fetchData]);

  const handleDelete = async (id: number) => {
    if (!window.confirm('Are you sure you want to delete this story?')) {
      return;
    }

    try {
      await api.post(`/cms/delete/${id}`);
      fetchData(data?.pagination?.current_page || 1);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete story');
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
        <button onClick={() => fetchData(1)} className="btn btn-primary">
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
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold mb-2">Stories</h1>
          <p className="text-gray-500 dark:text-gray-400">
            Manage all your news articles
          </p>
        </div>
        <Link to="/cms/create" className="btn btn-primary">
          <Plus className="w-4 h-4 mr-2" />
          Create New Story
        </Link>
      </div>

      {/* Filters */}
      <div
        className={cn(
          'cms-card p-6',
          theme === 'light' ? 'bg-white' : 'bg-gray-800'
        )}
      >
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search stories..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input pl-10"
            />
          </div>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as StoryStatus)}
            className="select"
          >
            <option value="all">All Statuses</option>
            <option value="published">Published</option>
            <option value="draft">Drafts</option>
          </select>

          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="select"
          >
            <option value="">All Categories</option>
            {data.categories.map((cat) => (
              <option key={cat.id} value={cat.name}>
                {cat.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Stories Table */}
      <div
        className={cn(
          'cms-card',
          theme === 'light' ? 'bg-white' : 'bg-gray-800'
        )}
      >
        {data.stories.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-500 dark:text-gray-400 mb-4">No stories found</p>
            <Link to="/cms/create" className="btn btn-primary">
              <Plus className="w-4 h-4 mr-2" />
              Create Story
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700">
                  <th className="text-left p-4 font-semibold">Title</th>
                  <th className="text-left p-4 font-semibold hidden md:table-cell">
                    Author
                  </th>
                  <th className="text-left p-4 font-semibold hidden md:table-cell">
                    Category
                  </th>
                  <th className="text-left p-4 font-semibold">Status</th>
                  <th className="text-left p-4 font-semibold hidden lg:table-cell">
                    Updated
                  </th>
                  <th className="text-right p-4 font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.stories.map((story) => (
                  <tr
                    key={story.id}
                    className="border-b border-gray-100 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                  >
                    <td className="p-4">
                      <div className="font-medium">{story.title}</div>
                      <div className="text-sm text-gray-500 dark:text-gray-400 md:hidden">
                        {story.author}
                      </div>
                    </td>
                    <td className="p-4 hidden md:table-cell">
                      {story.author}
                    </td>
                    <td className="p-4 hidden md:table-cell">
                      <span className="badge badge-category">{story.category}</span>
                    </td>
                    <td className="p-4">
                      {story.published ? (
                        <span className="badge badge-published">
                          <CheckCircle className="w-3 h-3 mr-1" />
                          Published
                        </span>
                      ) : (
                        <span className="badge badge-draft">
                          <Clock className="w-3 h-3 mr-1" />
                          Draft
                        </span>
                      )}
                    </td>
                    <td className="p-4 hidden lg:table-cell">
                      {formatRelativeDate(story.updated_at)}
                    </td>
                    <td className="p-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Link
                          to={`/story/${story.slug}`}
                          target="_blank"
                          className="p-2 text-gray-500 hover:text-primary-600 transition-colors"
                          title="View"
                        >
                          <Eye className="w-4 h-4" />
                        </Link>
                        <Link
                          to={`/cms/edit/${story.id}`}
                          className="p-2 text-gray-500 hover:text-primary-600 transition-colors"
                          title="Edit"
                        >
                          <Edit className="w-4 h-4" />
                        </Link>
                        <button
                          onClick={() => handleDelete(story.id)}
                          className="p-2 text-gray-500 hover:text-red-500 transition-colors"
                          title="Delete"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {data.pagination && data.pagination.total_pages > 1 && (
          <div className="flex items-center justify-between pt-4 border-t border-gray-200 dark:border-gray-700">
            <div className="text-sm text-gray-500 dark:text-gray-400">
              Showing {((data.pagination.current_page - 1) * 10) + 1} to{' '}
              {Math.min(data.pagination.current_page * 10, data.pagination.total_count)} of{' '}
              {data.pagination.total_count} stories
            </div>
            <div className="flex items-center gap-2">
              {data.pagination.has_previous && (
                <button
                  onClick={() => fetchData(data.pagination.current_page - 1)}
                  className="btn btn-secondary btn-sm"
                >
                  &laquo; Previous
                </button>
              )}

              {Array.from({ length: data.pagination.total_pages }, (_, i) => i + 1).map(
                (page) => (
                  <button
                    key={page}
                    onClick={() => fetchData(page)}
                    className={cn(
                      'btn btn-sm min-w-[40px]',
                      page === data.pagination.current_page
                        ? 'btn-primary'
                        : 'btn-secondary'
                    )}
                  >
                    {page}
                  </button>
                )
              )}

              {data.pagination.has_next && (
                <button
                  onClick={() => fetchData(data.pagination.current_page + 1)}
                  className="btn btn-secondary btn-sm"
                >
                  Next &raquo;
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
