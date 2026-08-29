import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useThemeContext } from '../../contexts/ThemeContext';
import { cn, api } from '../../utils';
import { Save, X, Image as ImageIcon, Eye } from 'lucide-react';

interface Category {
  id: number;
  name: string;
}

interface Story {
  id: number;
  title: string;
  slug: string;
  content: string;
  excerpt: string | null;
  author: string;
  category: string;
  featured_image: string | null;
  published: boolean;
  published_at: string | null;
}

interface EditPageData {
  site_title: string;
  theme: string;
  story: Story;
  categories: Category[];
  user: {
    username: string;
    full_name: string | null;
    is_admin: boolean;
  };
  csrf_token: string;
}

export default function CMSEdit() {
  const { id } = useParams<{ id: string }>();
  const { theme } = useThemeContext();
  const navigate = useNavigate();
  const [data, setData] = useState<EditPageData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [excerpt, setExcerpt] = useState('');
  const [author, setAuthor] = useState('');
  const [category, setCategory] = useState('');
  const [featuredImage, setFeaturedImage] = useState<File | null>(null);
  const [featuredImageUrl, setFeaturedImageUrl] = useState('');
  const [published, setPublished] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchData = useCallback(async () => {
    if (!id) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await api.get(`/cms/edit/${id}`);
      setData(response.data);
      
      // Set form values
      const story = response.data.story;
      setTitle(story.title);
      setContent(story.content);
      setExcerpt(story.excerpt || '');
      setAuthor(story.author);
      setCategory(story.category);
      setFeaturedImageUrl(story.featured_image || '');
      setPublished(story.published);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load story');
    } finally {
      setIsLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await api.post('/api/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setFeaturedImageUrl(response.data.url);
      setFeaturedImage(file);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to upload image');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('title', title);
      formData.append('content', content);
      formData.append('excerpt', excerpt);
      formData.append('author', author);
      formData.append('category', category);
      formData.append('published', published.toString());
      formData.append('publish_now', 'true');
      
      // Add CSRF token
      formData.append('csrf_token', data?.csrf_token || '');
      
      // Add featured image if present
      if (featuredImage) {
        formData.append('featured_image', featuredImage);
      }

      const response = await api.post(`/cms/edit/${id}`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      if (response.data.success) {
        navigate('/cms/stories');
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update story');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = () => {
    if (window.confirm('Are you sure you want to discard your changes?')) {
      navigate('/cms/stories');
    }
  };

  const handlePreview = () => {
    window.open(`/story/${data?.story.slug}`, '_blank');
  };

  const handleDelete = async () => {
    if (!window.confirm('Are you sure you want to delete this story?')) {
      return;
    }

    try {
      const formData = new FormData();
      formData.append('csrf_token', data?.csrf_token || '');
      
      await api.post(`/cms/delete/${id}`, formData);
      navigate('/cms/stories');
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold mb-2">Edit Story</h1>
          <p className="text-gray-500 dark:text-gray-400">
            Edit your news article
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handlePreview}
            className="btn btn-secondary"
          >
            <Eye className="w-4 h-4 mr-2" />
            Preview
          </button>
          <button
            type="button"
            onClick={handleDelete}
            className="btn btn-danger"
            disabled={isSubmitting}
          >
            Delete
          </button>
        </div>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-6">
        <div
          className={cn(
            'cms-card space-y-6',
            theme === 'light' ? 'bg-white' : 'bg-gray-800'
          )}
        >
          {/* Basic Information */}
          <div>
            <h2 className="text-lg font-semibold mb-4 pb-2 border-b border-gray-200 dark:border-gray-700">
              Basic Information
            </h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label htmlFor="title" className="block text-sm font-medium mb-1">
                  Title *
                </label>
                <input
                  type="text"
                  id="title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="input"
                  placeholder="Enter story title"
                  required
                  autoFocus
                />
              </div>
              <div>
                <label htmlFor="category" className="block text-sm font-medium mb-1">
                  Category *
                </label>
                <select
                  id="category"
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="select"
                  required
                >
                  {data.categories.map((cat) => (
                    <option key={cat.id} value={cat.name}>
                      {cat.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
              <div>
                <label htmlFor="author" className="block text-sm font-medium mb-1">
                  Author
                </label>
                <input
                  type="text"
                  id="author"
                  value={author}
                  onChange={(e) => setAuthor(e.target.value)}
                  className="input"
                  placeholder="Enter author name"
                />
              </div>
              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={published}
                    onChange={(e) => setPublished(e.target.checked)}
                    className="w-4 h-4"
                  />
                  <span className="text-sm font-medium">Published</span>
                </label>
              </div>
            </div>
          </div>

          {/* Featured Image */}
          <div>
            <h2 className="text-lg font-semibold mb-4 pb-2 border-b border-gray-200 dark:border-gray-700">
              Featured Image
            </h2>
            
            <div className="flex items-center gap-4">
              {featuredImageUrl && (
                <div className="relative">
                  <img
                    src={featuredImageUrl}
                    alt="Featured"
                    className="w-24 h-24 object-cover rounded-lg"
                  />
                  <button
                    type="button"
                    onClick={() => {
                      setFeaturedImageUrl('');
                      setFeaturedImage(null);
                    }}
                    className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full w-6 h-6 flex items-center justify-center hover:bg-red-600 transition-colors"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              )}
              <label className="btn btn-secondary cursor-pointer">
                <ImageIcon className="w-4 h-4 mr-2" />
                {featuredImageUrl ? 'Change Image' : 'Upload Image'}
                <input
                  type="file"
                  accept="image/*"
                  onChange={handleImageUpload}
                  className="hidden"
                />
              </label>
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
              Recommended: 1200x630 pixels (16:9 ratio)
            </p>
          </div>

          {/* Excerpt */}
          <div>
            <h2 className="text-lg font-semibold mb-4 pb-2 border-b border-gray-200 dark:border-gray-700">
              Excerpt
            </h2>
            <textarea
              value={excerpt}
              onChange={(e) => setExcerpt(e.target.value)}
              className="textarea"
              placeholder="Enter a short excerpt (optional - will be auto-generated from content if not provided)"
              rows={4}
            />
          </div>

          {/* Content */}
          <div>
            <h2 className="text-lg font-semibold mb-4 pb-2 border-b border-gray-200 dark:border-gray-700">
              Content *
            </h2>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              className="textarea min-h-[300px]"
              placeholder="Write your story content here..."
              required
            />
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
              Supports Markdown formatting
            </p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end gap-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <button
            type="button"
            onClick={handleCancel}
            className="btn btn-secondary"
            disabled={isSubmitting}
          >
            <X className="w-4 h-4 mr-2" />
            Cancel
          </button>
          <button
            type="submit"
            className="btn btn-primary"
            disabled={isSubmitting || !title || !content}
          >
            {isSubmitting ? (
              <span className="flex items-center gap-2">
                <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></span>
                Saving...
              </span>
            ) : (
              <span className="flex items-center gap-2">
                <Save className="w-4 h-4" />
                Save Changes
              </span>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
