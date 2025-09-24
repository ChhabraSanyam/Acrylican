import React from 'react';
import PostingManagementPage from '../components/posting/PostingManagementPage';

const PostingPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Content Posting</h1>
        <p className="text-gray-600">Create, schedule, and manage your posts across platforms</p>
      </div>

      <PostingManagementPage />
    </div>
  );
};

export default PostingPage;