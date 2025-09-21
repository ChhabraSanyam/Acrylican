import React, { useState } from 'react';
import { Product, ProductFormData } from '../../types/product';
import { ProductService } from '../../services/product';
import { ProductList } from './ProductList';
import { ProductForm } from './ProductForm';
import { ProductDetail } from './ProductDetail';

type ViewMode = 'list' | 'create' | 'edit' | 'detail';

export const ProductManager: React.FC = () => {
  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [loading, setLoading] = useState(false);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const handleCreateProduct = async (formData: ProductFormData) => {
    setLoading(true);
    try {
      await ProductService.createProduct(formData);
      setViewMode('list');
      setRefreshTrigger(prev => prev + 1);
    } catch (error) {
      throw error; // Let the form handle the error
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateProduct = async (formData: ProductFormData) => {
    if (!selectedProduct) return;
    
    setLoading(true);
    try {
      const updatedProduct = await ProductService.updateProduct(selectedProduct.id, formData);
      setSelectedProduct(updatedProduct);
      setViewMode('detail');
      setRefreshTrigger(prev => prev + 1);
    } catch (error) {
      throw error; // Let the form handle the error
    } finally {
      setLoading(false);
    }
  };

  const handleProductSelect = (product: Product) => {
    setSelectedProduct(product);
    setViewMode('detail');
  };

  const handleProductEdit = (product: Product) => {
    setSelectedProduct(product);
    setViewMode('edit');
  };

  const handleProductDelete = () => {
    setRefreshTrigger(prev => prev + 1);
  };

  const handleBackToList = () => {
    setViewMode('list');
    setSelectedProduct(null);
  };

  const renderHeader = () => {
    switch (viewMode) {
      case 'create':
        return (
          <div className="flex items-center justify-between mb-6">
            <h1 className="text-2xl font-bold text-gray-900">Create New Product</h1>
            <button
              onClick={handleBackToList}
              className="text-gray-600 hover:text-gray-900"
            >
              ← Back to Products
            </button>
          </div>
        );
      case 'edit':
        return (
          <div className="flex items-center justify-between mb-6">
            <h1 className="text-2xl font-bold text-gray-900">Edit Product</h1>
            <button
              onClick={handleBackToList}
              className="text-gray-600 hover:text-gray-900"
            >
              ← Back to Products
            </button>
          </div>
        );
      case 'detail':
        return (
          <div className="flex items-center justify-between mb-6">
            <h1 className="text-2xl font-bold text-gray-900">Product Details</h1>
            <button
              onClick={handleBackToList}
              className="text-gray-600 hover:text-gray-900"
            >
              ← Back to Products
            </button>
          </div>
        );
      default:
        return (
          <div className="flex items-center justify-between mb-6">
            <h1 className="text-2xl font-bold text-gray-900">Product Management</h1>
            <button
              onClick={() => setViewMode('create')}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              Create Product
            </button>
          </div>
        );
    }
  };

  const renderContent = () => {
    switch (viewMode) {
      case 'create':
        return (
          <div className="max-w-2xl">
            <ProductForm
              onSubmit={handleCreateProduct}
              onCancel={handleBackToList}
              isLoading={loading}
              submitLabel="Create Product"
            />
          </div>
        );
      case 'edit':
        return selectedProduct ? (
          <div className="max-w-2xl">
            <ProductForm
              initialData={{
                title: selectedProduct.title,
                description: selectedProduct.description
              }}
              onSubmit={handleUpdateProduct}
              onCancel={handleBackToList}
              isLoading={loading}
              submitLabel="Update Product"
            />
          </div>
        ) : null;
      case 'detail':
        return selectedProduct ? (
          <ProductDetail
            product={selectedProduct}
            onEdit={() => handleProductEdit(selectedProduct)}
            onDelete={handleProductDelete}
            onBack={handleBackToList}
          />
        ) : null;
      default:
        return (
          <ProductList
            onProductSelect={handleProductSelect}
            onProductEdit={handleProductEdit}
            onProductDelete={handleProductDelete}
            refreshTrigger={refreshTrigger}
          />
        );
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {renderHeader()}
      {renderContent()}
    </div>
  );
};