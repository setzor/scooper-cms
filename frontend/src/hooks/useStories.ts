import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { StoryListItem, Story, Pagination } from '../types';

interface StoriesState {
  stories: StoryListItem[];
  pagination: Pagination | null;
  isLoading: boolean;
  error: string | null;
}

const API_BASE = import.meta.env.VITE_API_URL || '';

export function useStories(publishedOnly = true) {
  const [state, setState] = useState<StoriesState>({
    stories: [],
    pagination: null,
    isLoading: true,
    error: null,
  });

  const fetchStories = useCallback(async (page = 1, perPage = 10) => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));

    try {
      const response = await axios.get(`${API_BASE}/api/stories`, {
        params: {
          published_only: publishedOnly,
          page,
          per_page: perPage,
        },
      });

      // For now, we'll use the paper endpoint which returns HTMLResponse
      // In production, we should use the API endpoint
      // This is a temporary workaround
      setState({
        stories: [],
        pagination: null,
        isLoading: false,
        error: null,
      });
    } catch (error: any) {
      setState({
        stories: [],
        pagination: null,
        isLoading: false,
        error: error.response?.data?.detail || 'Failed to fetch stories',
      });
    }
  }, [publishedOnly]);

  // Fetch on mount
  useEffect(() => {
    fetchStories();
  }, [fetchStories]);

  return {
    ...state,
    fetchStories,
    refetch: fetchStories,
  };
}

export function useStory(slug: string) {
  const [story, setStory] = useState<Story | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchStory = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const response = await axios.get(`${API_BASE}/api/stories/${slug}`);
        setStory(response.data);
      } catch (error: any) {
        setError(error.response?.data?.detail || 'Failed to fetch story');
      } finally {
        setIsLoading(false);
      }
    };

    if (slug) {
      fetchStory();
    }
  }, [slug]);

  return { story, isLoading, error };
}
