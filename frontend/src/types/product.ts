export interface ProductImage {
  id: string;
  original_filename: string;
  original_url: string;
  compressed_url: string;
  thumbnail_urls: Record<string, string>;
  platform_optimized_urls?: Record<string, string>;
  storage_paths: Record<string, string>;
  file_size: number;
  dimensions: Record<string, number>;
  format: string;
  created_at: string;
}

export interface Product {
  id: string;
  user_id: string;
  title: string;
  description: string;
  generated_content?: Record<string, any>;
  images: ProductImage[];
  created_at: string;
  updated_at: string;
}

export interface ProductCreate {
  title: string;
  description: string;
}

export interface ProductUpdate {
  title?: string;
  description?: string;
}

export interface ProductListResponse {
  products: Product[];
  total: number;
  skip: number;
  limit: number;
}

export interface ProductFormData {
  title: string;
  description: string;
}

export interface ProductFormErrors {
  title?: string;
  description?: string;
  general?: string;
}