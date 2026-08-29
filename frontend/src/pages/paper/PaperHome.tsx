import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useThemeContext } from '../../contexts/ThemeContext';
import { MarkdownContent } from '../../components/MarkdownContent';
import { formatDate } from '../../utils/formatDate';
import { cn } from '../../utils/cn';

interface Story {
  id: number;
  title: string;
  slug: string;
  excerpt: string | null;
  author: string;
  category: string;
  featured_image: string | null;
  published_at: string | null;
}

interface Pagination {
  current_page: number;
  total_pages: number;
  total_count: number;
  has_previous: boolean;
  has_next: boolean;
}

interface PaperHomeData {
  site_title: string;
  site_description: string;
  theme: string;
  font_family: string;
  stories: Story[];
  pagination: Pagination;
}

export default function PaperHome() {
  const { theme, fontFamily } = useThemeContext();
  const [data, setData] = useState<PaperHomeData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async (page = 1) => {
    setIsLoading(true);
    setError(null);

    try {
      // In development, fetch from Vite proxy
      // In production, this will be served by the backend
      const response = await fetch(`/paper?page=${page}`);
      
      if (!response.ok) {
        throw new Error('Failed to fetch data');
      }

      const result = await response.json();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
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
        <button onClick={() => fetchData()} className="btn btn-primary">
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
    <div className="space-y-12">
      {/* Hero Section */}
      <section className="text-center">
        <h1 className="text-4xl md:text-5xl font-bold font-serif mb-4">
          {data.site_title}
        </h1>
        <p className="text-xl text-paper-text-secondary max-w-2xl mx-auto">
          {data.site_description}
        </p>
      </section>

      {/* Featured Stories */}
      <section>
        <h2 className="text-2xl font-bold font-serif mb-8 border-b border-paper-border dark:border-gray-700 pb-2">
          Featured Stories
        </h2>

        {data.stories.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-paper-text-secondary">No stories yet</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {data.stories.map((story) => (
              <article
                key={story.id}
                className={cn(
                  'paper-card animate-fade-in',
                  theme === 'light' ? 'bg-paper-card' : 'bg-gray-800'
                )}
              >
                {story.featured_image && (
                  <div className="overflow-hidden">
                    <img
                      src={story.featured_image}
                      alt={story.title}
                      className="w-full h-48 object-cover"
                      loading="lazy"
                    />
                  </div>
                )}
                
                <div className="p-6">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="badge badge-category">
                      {story.category}
                    </span>
                    <span className="text-sm text-paper-text-muted">
                      {formatDate(story.published_at)}
                    </span>
                  </div>
                  
                  <h3 className="text-xl font-bold font-serif mb-2">
                    <Link
                      to={`/story/${story.slug}`}
                      className="hover:text-primary-600 dark:hover:text-primary-400 transition-colors"
                    >
                      {story.title}
                    </Link>
                  </h3>
                  
                  <p className="text-paper-text-secondary mb-4 line-clamp-3">
                    {story.excerpt}
                  </p>
                  
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-paper-text-muted">
                      By {story.author}
                    </span>
                    <Link
                      to={`/story/${story.slug}`}
                      className="text-primary-600 dark:text-primary-400 hover:underline text-sm font-medium"
                    >
                      Read More &raquo;
                    </Link>
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}

        {/* Pagination */}
        {data.pagination && data.pagination.total_pages > 1 && (
          <nav className="flex items-center justify-center gap-2 mt-12">
            {data.pagination.has_previous && (
              <Link
                to={`/?page=${data.pagination.current_page - 1}`}
                className="btn btn-secondary btn-sm"
              >
                &laquo; Previous
              </Link>
            )}

            {Array.from({ length: data.pagination.total_pages }, (_, i) => i + 1).map(
              (page) => (
                <Link
                  key={page}
                  to={`/?page=${page}`}
                  className={cn(
                    'btn btn-sm min-w-[40px]',
                    page === data.pagination.current_page
                      ? 'btn-primary'
                      : 'btn-secondary'
                  )}
                >
                  {page}
                </Link>
              )
            )}

            {data.pagination.has_next && (
              <Link
                to={`/?page=${data.pagination.current_page + 1}`}
                className="btn btn-secondary btn-sm"
              >
                Next &raquo;
              </Link>
            )}
          </nav>
        )}
      </section>
    </div>
  );
}
