// Story types
export interface Story {
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
  created_at: string;
  updated_at: string;
}

export interface StoryListItem {
  id: number;
  title: string;
  slug: string;
  excerpt: string | null;
  author: string;
  category: string;
  featured_image: string | null;
  published: boolean;
  published_at: string | null;
}

// Settings types
export interface SiteSettings {
  site_title: string;
  site_description: string;
  theme: string;
  font_family: string;
}

export interface Settings {
  [key: string]: string;
}

// Category types
export interface Category {
  id: number;
  name: string;
}

// Pagination types
export interface Pagination {
  current_page: number;
  total_pages: number;
  total_count: number;
  has_previous: boolean;
  has_next: boolean;
}

// User types
export interface User {
  id: number;
  username: string;
  full_name: string | null;
  email: string | null;
  is_active: boolean;
  is_admin: boolean;
}

// API Response types
export interface ApiResponse<T = any> {
  success?: boolean;
  message?: string;
  data?: T;
  error?: string;
}

// CMS Dashboard types
export interface DashboardStats {
  total_stories: number;
  published_count: number;
  draft_count: number;
  categories_count: number;
}

export interface RecentStory {
  id: number;
  title: string;
  slug: string;
  published: boolean;
  published_at: string | null;
}

// Filter types
export interface StoryFilters {
  status?: string;
  category?: string;
  search?: string;
}

// Theme types
export type Theme = 'light' | 'dark';
export type FontFamily = 'serif' | 'sans';
