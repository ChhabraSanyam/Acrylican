import React, { useState } from 'react';
import { Product } from '../../types/product';
import { ProductService } from '../../services/product';
import ImageGallery from '../image/ImageGallery';

interface ProductDetailProps {
  product: Product;
  onEdit: () => void;
  onDelete: () => void;
  onBack: () => void;
}

const ProductDetail: React.FC<ProductDetailProps> = ({
  product,
  onEdit,
  onDelete,
  onBack
}) => {
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDelete = async () => {
    if (!window.confirm('Are you sure you want to delete this product? This action cannot be undone.')) {
      return;
    }

    setIsDeleting(true);
    try {
      await ProductService.deleteProduct(product.id);
      onDelete();
      onBack();
    } catch (error) {
      alert('Failed to delete product. Please try again.');
    } finally {
      setIsDeleting(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="bg-white shadow rounded-lg mb-6">
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex justify-between items-start">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 mb-2">{product.title}</h1>
              <div className="flex space-x-4 text-sm text-gray-500">
                <span>Created: {formatDate(product.created_at)}</span>
                {product.updated_at !== product.created_at && (
                  <span>Updated: {formatDate(product.updated_at)}</span>
                )}
              </div>
            </div>
            <div className="flex space-x-3">
              <button
                onClick={onEdit}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                Edit Product
              </button>
              <button
                onClick={handleDelete}
                disabled={isDeleting}
                className="px-4 py-2 text-sm font-medium text-red-600 bg-red-50 border border-red-200 rounded-md hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50"
              >
                {isDeleting ? 'Deleting...' : 'Delete Product'}
              </button>
            </div>
          </div>
        </div>

        {/* Description */}
        <div className="px-6 py-4">
          <h2 className="text-lg font-medium text-gray-900 mb-3">Description</h2>
          <div className="prose max-w-none">
            <p className="text-gray-700 whitespace-pre-wrap">{product.description}</p>
          </div>
        </div>
      </div>

      {/* Images Section */}
      <div className="bg-white shadow rounded-lg mb-6">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-medium text-gray-900">
            Product Images ({product.images.length})
          </h2>
        </div>
        <div className="p-6">
          {product.images.length > 0 ? (
            <ImageGallery 
              showUpload={false}
              allowMultiSelect={false}
            />
          ) : (
            <div className="text-center py-12">
              <div className="text-gray-400 mb-4">
                <svg className="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">No images uploaded</h3>
              <p className="text-gray-500">Upload images to showcase your product.</p>
            </div>
          )}
        </div>
      </div>

      {/* Generated Content Section */}
      {product.generated_content && (
        <div className="bg-white shadow rounded-lg">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-900">Generated Marketing Content</h2>
          </div>
          <div className="p-6">
            <pre className="bg-gray-50 p-4 rounded-md overflow-auto text-sm">
              {JSON.stringify(product.generated_content, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProductDetail;