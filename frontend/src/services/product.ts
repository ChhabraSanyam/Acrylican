import apiClient from '../utils/api';
import { Product, ProductCreate, ProductUpdate, ProductImage } from '../types/product';

export class ProductService {
  private static readonly BASE_URL = '/products';

  /**
   * Create a new product
   */
  static async createProduct(productData: ProductCreate): Promise<Product> {
    const response = await apiClient.post<Product>(this.BASE_URL, productData);
    return response.data;
  }

  /**
   * Get all products for the current user
   */
  static async getProducts(skip: number = 0, limit: number = 100): Promise<Product[]> {
    const response = await apiClient.get<Product[]>(this.BASE_URL, {
      params: { skip, limit }
    });
    return response.data;
  }

  /**
   * Get a specific product by ID
   */
  static async getProduct(productId: string): Promise<Product> {
    const response = await apiClient.get<Product>(`${this.BASE_URL}/${productId}`);
    return response.data;
  }

  /**
   * Update a product
   */
  static async updateProduct(productId: string, productData: ProductUpdate): Promise<Product> {
    const response = await apiClient.put<Product>(`${this.BASE_URL}/${productId}`, productData);
    return response.data;
  }

  /**
   * Delete a product
   */
  static async deleteProduct(productId: string): Promise<void> {
    await apiClient.delete(`${this.BASE_URL}/${productId}`);
  }

  /**
   * Get all images for a product
   */
  static async getProductImages(productId: string): Promise<ProductImage[]> {
    const response = await apiClient.get<ProductImage[]>(`${this.BASE_URL}/${productId}/images`);
    return response.data;
  }

  /**
   * Delete a specific image from a product
   */
  static async deleteProductImage(productId: string, imageId: string): Promise<void> {
    await apiClient.delete(`${this.BASE_URL}/${productId}/images/${imageId}`);
  }
}