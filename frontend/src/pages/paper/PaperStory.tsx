import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useThemeContext } from '../../contexts/ThemeContext';
import { MarkdownContent } from '../../components/MarkdownContent';
import { formatDate } from '../../utils/formatDate';
import { cn } from '../../utils/cn';

interface Story {
  id: number;
  title: string;
  slug: string;
  content: string;
  excerpt: string | null;
  author: string;
  category: string;
  featured_image: string | null;
  published_at: string | null;
}

interface StoryData {
  site_title: string;
  theme: string;
  font_family: string;
  story: Story;
}

export default function PaperStory() {
  const { slug } = useParams<{ slug: string }>();
  const { theme, fontFamily } = useThemeContext();
  const [data, setData] = useState<StoryData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const response = await fetch(`/story/${slug}`);
        
        if (!response.ok) {
          throw new Error('Story not found');
        }

        const result = await response.json();
        setData(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load story');
      } finally {
        setIsLoading(false);
      }
    };

    if (slug) {
      fetchData();
    }
  }, [slug]);

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
        <h2 className="text-2xl font-bold mb-4">Story Not Found</h2>
        <p className="text-paper-text-secondary mb-6">{error}</p>
        <Link to="/" className="btn btn-primary">
          Back to Home
        </Link>
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
    <article
      className={cn(
        'paper-card animate-fade-in',
        theme === 'light' ? 'bg-paper-card' : 'bg-gray-800'
      )}
    >
      {/* Header */}
      <header className="p-6 border-b border-paper-border dark:border-gray-700">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className="badge badge-category">{data.story.category}</span>
            <span className="text-sm text-paper-text-muted">
              {formatDate(data.story.published_at)}
            </span>
          </div>
          
          <h1 className="text-3xl md:text-4xl font-bold font-serif">
            {data.story.title}
          </h1>
          
          <p className="text-paper-text-secondary">
            By {data.story.author}
          </p>
        </div>
      </header>

      {/* Featured Image */}
      {data.story.featured_image && (
        <div className="overflow-hidden">
          <img
            src={data.story.featured_image}
            alt={data.story.title}
            className="w-full h-64 md:h-96 object-cover"
            loading="lazy"
          />
        </div>
      )}

      {/* Content */}
      <div className="p-6 md:p-8">
        <MarkdownContent content={data.story.content} />
      </div>

      {/* Footer */}
      <footer className="p-6 border-t border-paper-border dark:border-gray-700">
        <div className="flex items-center justify-between">
          <Link to="/" className="text-paper-text-secondary hover:text-primary-600 transition-colors">
            &laquo; Back to all stories
          </Link>
          <span className="text-paper-text-muted text-sm">
            Published {formatDate(data.story.published_at)}
          </span>
        </div>
      </footer>
    </article>
  );
}
