import React, { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { UserRegistration } from '../../types/auth';

interface RegisterFormProps {
  onSuccess?: () => void;
}

const RegisterForm: React.FC<RegisterFormProps> = ({ onSuccess }) => {
  const { register, isLoading } = useAuth();
  const [formData, setFormData] = useState<UserRegistration>({
    email: '',
    password: '',
    business_name: '',
    business_type: '',
    business_description: '',
    website: '',
    location: '',
  });
  const [errors, setErrors] = useState<Partial<UserRegistration>>({});
  const [submitError, setSubmitError] = useState<string>('');

  const businessTypes = [
    'Handicrafts',
    'Jewelry',
    'Textiles',
    'Pottery',
    'Woodwork',
    'Metalwork',
    'Art & Paintings',
    'Food & Beverages',
    'Cosmetics & Beauty',
    'Home Decor',
    'Other',
  ];

  const validateForm = (): boolean => {
    const newErrors: Partial<UserRegistration> = {};

    if (!formData.email) {
      newErrors.email = 'Email is required';
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      newErrors.email = 'Email is invalid';
    }

    if (!formData.password) {
      newErrors.password = 'Password is required';
    } else if (formData.password.length < 8) {
      newErrors.password = 'Password must be at least 8 characters long';
    }

    if (!formData.business_name) {
      newErrors.business_name = 'Business name is required';
    }

    if (!formData.business_type) {
      newErrors.business_type = 'Business type is required';
    }

    if (formData.website && !/^https?:\/\/.+/.test(formData.website)) {
      newErrors.website = 'Website must be a valid URL (include http:// or https://)';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    
    // Clear error when user starts typing
    if (errors[name as keyof UserRegistration]) {
      setErrors(prev => ({ ...prev, [name]: '' }));
    }
    
    // Clear submit error
    if (submitError) {
      setSubmitError('');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    try {
      // Remove empty optional fields
      const registrationData: UserRegistration = {
        email: formData.email,
        password: formData.password,
        business_name: formData.business_name,
        business_type: formData.business_type,
        business_description: formData.business_description || '',
        website: formData.website || '',
        location: formData.location || '',
      };

      await register(registrationData);
      onSuccess?.();
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : 'Registration failed');
    }
  };

  return (
    <div className="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10">
      <form onSubmit={handleSubmit} className="space-y-6">
        {submitError && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
            {submitError}
          </div>
        )}

        <div>
          <label htmlFor="email" className="block text-sm font-medium text-gray-700">
            Email Address *
          </label>
          <div className="mt-1">
            <input
              type="email"
              id="email"
              name="email"
              value={formData.email}
              onChange={handleInputChange}
              className={`appearance-none block w-full px-3 py-2 border rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm ${
                errors.email ? 'border-red-300' : 'border-gray-300'
              }`}
              placeholder="Enter your email"
              disabled={isLoading}
            />
          </div>
          {errors.email && (
            <p className="mt-2 text-sm text-red-600">{errors.email}</p>
          )}
        </div>

        <div>
          <label htmlFor="password" className="block text-sm font-medium text-gray-700">
            Password *
          </label>
          <div className="mt-1">
            <input
              type="password"
              id="password"
              name="password"
              value={formData.password}
              onChange={handleInputChange}
              className={`appearance-none block w-full px-3 py-2 border rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm ${
                errors.password ? 'border-red-300' : 'border-gray-300'
              }`}
              placeholder="Enter your password (min 8 characters)"
              disabled={isLoading}
            />
          </div>
          {errors.password && (
            <p className="mt-2 text-sm text-red-600">{errors.password}</p>
          )}
        </div>

        <div>
          <label htmlFor="business_name" className="block text-sm font-medium text-gray-700">
            Business Name *
          </label>
          <div className="mt-1">
            <input
              type="text"
              id="business_name"
              name="business_name"
              value={formData.business_name}
              onChange={handleInputChange}
              className={`appearance-none block w-full px-3 py-2 border rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm ${
                errors.business_name ? 'border-red-300' : 'border-gray-300'
              }`}
              placeholder="Enter your business name"
              disabled={isLoading}
            />
          </div>
          {errors.business_name && (
            <p className="mt-2 text-sm text-red-600">{errors.business_name}</p>
          )}
        </div>

        <div>
          <label htmlFor="business_type" className="block text-sm font-medium text-gray-700">
            Business Type *
          </label>
          <div className="mt-1">
            <select
              id="business_type"
              name="business_type"
              value={formData.business_type}
              onChange={handleInputChange}
              className={`appearance-none block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm ${
                errors.business_type ? 'border-red-300' : 'border-gray-300'
              }`}
              disabled={isLoading}
            >
              <option value="">Select business type</option>
              {businessTypes.map(type => (
                <option key={type} value={type}>{type}</option>
              ))}
            </select>
          </div>
          {errors.business_type && (
            <p className="mt-2 text-sm text-red-600">{errors.business_type}</p>
          )}
        </div>

        <div>
          <label htmlFor="business_description" className="block text-sm font-medium text-gray-700">
            Business Description
          </label>
          <div className="mt-1">
            <textarea
              id="business_description"
              name="business_description"
              value={formData.business_description}
              onChange={handleInputChange}
              rows={3}
              className="appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              placeholder="Describe your business (optional)"
              disabled={isLoading}
            />
          </div>
        </div>

        <div>
          <label htmlFor="website" className="block text-sm font-medium text-gray-700">
            Website
          </label>
          <div className="mt-1">
            <input
              type="url"
              id="website"
              name="website"
              value={formData.website}
              onChange={handleInputChange}
              className={`appearance-none block w-full px-3 py-2 border rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm ${
                errors.website ? 'border-red-300' : 'border-gray-300'
              }`}
              placeholder="https://your-website.com (optional)"
              disabled={isLoading}
            />
          </div>
          {errors.website && (
            <p className="mt-2 text-sm text-red-600">{errors.website}</p>
          )}
        </div>

        <div>
          <label htmlFor="location" className="block text-sm font-medium text-gray-700">
            Location
          </label>
          <div className="mt-1">
            <input
              type="text"
              id="location"
              name="location"
              value={formData.location}
              onChange={handleInputChange}
              className="appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              placeholder="City, State/Country (optional)"
              disabled={isLoading}
            />
          </div>
        </div>

        <div>
          <button
            type="submit"
            disabled={isLoading}
            className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? 'Creating Account...' : 'Create Account'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default RegisterForm;