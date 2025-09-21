import React, { useState, useEffect, useCallback } from 'react';
import { ProcessedImage } from '../../types/image';
import { ImageService } from '../../services/image';
import ImagePreview from './ImagePreview';
import ImageUpload from './ImageUpload';

interface ImageGalleryProps {
  onImageSelect?: (images: ProcessedImage[]) => void;
  selectedImages?: string[];
  allowMultiSelect?: boolean;
  showUpload?: boolean;
  className?: string;
}

const ImageGallery: React.FC<ImageGalleryProps> = ({
  onImageSelect,
  selectedImages = [],
  allowMultiSelect = true,
  showUpload = true,
  className = '',
}) => {
  const [images, setImages] = useState<ProcessedImage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [selectedImageIds, setSelectedImageIds] = useState<string[]>(selectedImages);
  const [sortBy, setSortBy] = useState<'date' | 'name' | 'size'>('date');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [searchTerm, setSearchTerm] = useState('');

  // Load images on component mount
  useEffect(() => {
    loadImages();
  }, []);

  // Update selected images when prop changes
  useEffect(() => {
    if (JSON.stringify(selectedImageIds) !== JSON.stringify(selectedImages)) {
      setSelectedImageIds(selectedImages);
    }
  }, [selectedImages, selectedImageIds]);

  const loadImages = async () => {
    try {
      setLoading(true);
      setError('');
      const userImages = await ImageService.getUserImages();
      setImages(userImages);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load images');
    } finally {
      setLoading(false);
    }
  };

  const handleImageUpload = useCallback((newImages: ProcessedImage[]) => {
    setImages(prev => [...newImages, ...prev]);
  }, []);

  const handleImageDelete = useCallback(async (imageId: string) => {
    try {
      await ImageService.deleteImage(imageId);
      setImages(prev => prev.filter(img => img.id !== imageId));
      setSelectedImageIds(prev => prev.filter(id => id !== imageId));
      
      // Update parent component
      if (onImageSelect) {
        const updatedSelection = images.filter(img => 
          selectedImageIds.includes(img.id) && img.id !== imageId
        );
        onImageSelect(updatedSelection);
      }
    } catch (err) {
      console.error('Failed to delete image:', err);
      throw err;
    }
  }, [images, selectedImageIds, onImageSelect]);

  const handleImageSelect = useCallback((imageId: string) => {
    let newSelection: string[];
    
    if (allowMultiSelect) {
      if (selectedImageIds.includes(imageId)) {
        newSelection = selectedImageIds.filter(id => id !== imageId);
      } else {
        newSelection = [...selectedImageIds, imageId];
      }
    } else {
      newSelection = selectedImageIds.includes(imageId) ? [] : [imageId];
    }
    
    setSelectedImageIds(newSelection);
    
    if (onImageSelect) {
      const selectedImages = images.filter(img => newSelection.includes(img.id));
      onImageSelect(selectedImages);
    }
  }, [selectedImageIds, allowMultiSelect, images, onImageSelect]);

  const getFilteredAndSortedImages = useCallback(() => {
    let filtered = images;
    
    // Apply search filter
    if (searchTerm) {
      filtered = images.filter(img =>
        img.file_name.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }
    
    // Apply sorting
    return filtered.sort((a, b) => {
      let comparison = 0;
      
      switch (sortBy) {
        case 'name':
          comparison = a.file_name.localeCompare(b.file_name);
          break;
        case 'size':
          comparison = a.file_size - b.file_size;
          break;
        case 'date':
        default:
          comparison = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
          break;
      }
      
      return sortOrder === 'asc' ? comparison : -comparison;
    });
  }, [images, searchTerm, sortBy, sortOrder]);

  const handleSelectAll = useCallback(() => {
    const filteredImages = getFilteredAndSortedImages();
    const allIds = filteredImages.map(img => img.id);
    const newSelection = selectedImageIds.length === allIds.length ? [] : allIds;
    
    setSelectedImageIds(newSelection);
    
    if (onImageSelect) {
      const selectedImages = images.filter(img => newSelection.includes(img.id));
      onImageSelect(selectedImages);
    }
  }, [getFilteredAndSortedImages, selectedImageIds.length, onImageSelect, images]);

  const filteredImages = getFilteredAndSortedImages();

  if (loading) {
    return (
      <div className={`flex items-center justify-center py-12 ${className}`}>
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-500">Loading images...</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Upload Section */}
      {showUpload && (
        <ImageUpload
          onUploadComplete={handleImageUpload}
          onUploadError={(error) => setError(error)}
        />
      )}

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
          {error}
          <button
            onClick={() => setError('')}
            className="ml-2 text-red-500 hover:text-red-700"
          >
            ×
          </button>
        </div>
      )}

      {/* Gallery Header */}
      {images.length > 0 && (
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center space-x-4">
            <h3 className="text-lg font-medium text-gray-900">
              Image Gallery ({filteredImages.length})
            </h3>
            
            {allowMultiSelect && filteredImages.length > 0 && (
              <button
                onClick={handleSelectAll}
                className="text-sm text-primary-600 hover:text-primary-700"
              >
                {selectedImageIds.length === filteredImages.length ? 'Deselect All' : 'Select All'}
              </button>
            )}
          </div>

          <div className="flex items-center space-x-4">
            {/* Search */}
            <div className="relative">
              <input
                type="text"
                placeholder="Search images..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-8 pr-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              />
              <svg className="absolute left-2.5 top-2.5 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>

            {/* Sort Controls */}
            <select
              value={`${sortBy}-${sortOrder}`}
              onChange={(e) => {
                const [newSortBy, newSortOrder] = e.target.value.split('-') as [typeof sortBy, typeof sortOrder];
                setSortBy(newSortBy);
                setSortOrder(newSortOrder);
              }}
              className="text-sm border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            >
              <option value="date-desc">Newest First</option>
              <option value="date-asc">Oldest First</option>
              <option value="name-asc">Name A-Z</option>
              <option value="name-desc">Name Z-A</option>
              <option value="size-asc">Smallest First</option>
              <option value="size-desc">Largest First</option>
            </select>
          </div>
        </div>
      )}

      {/* Selected Images Info */}
      {selectedImageIds.length > 0 && (
        <div className="bg-primary-50 border border-primary-200 rounded-md p-3">
          <p className="text-sm text-primary-700">
            {selectedImageIds.length} image{selectedImageIds.length !== 1 ? 's' : ''} selected
          </p>
        </div>
      )}

      {/* Images Grid */}
      {filteredImages.length > 0 ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
          {filteredImages.map((image) => (
            <ImagePreview
              key={image.id}
              image={image}
              onDelete={handleImageDelete}
              onSelect={onImageSelect ? handleImageSelect : undefined}
              isSelected={selectedImageIds.includes(image.id)}
              showActions={true}
            />
          ))}
        </div>
      ) : (
        <div className="text-center py-12">
          <div className="mx-auto w-24 h-24 text-gray-300 mb-4">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1}
                d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
              />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">No images found</h3>
          <p className="text-gray-500 mb-4">
            {searchTerm ? 'No images match your search.' : 'Upload some images to get started.'}
          </p>
          {searchTerm && (
            <button
              onClick={() => setSearchTerm('')}
              className="text-primary-600 hover:text-primary-700 text-sm"
            >
              Clear search
            </button>
          )}
        </div>
      )}
    </div>
  );
};

export default ImageGallery;