import React, { useState, KeyboardEvent } from 'react';
import { XMarkIcon } from '@heroicons/react/24/outline';

interface HashtagInputProps {
  hashtags: string[];
  onChange: (hashtags: string[]) => void;
  placeholder?: string;
  maxTags?: number;
}

const HashtagInput: React.FC<HashtagInputProps> = ({
  hashtags,
  onChange,
  placeholder = "Type hashtag and press Enter...",
  maxTags = 30
}) => {
  const [inputValue, setInputValue] = useState('');

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      addHashtag();
    } else if (e.key === 'Backspace' && inputValue === '' && hashtags.length > 0) {
      // Remove last hashtag if input is empty and backspace is pressed
      removeHashtag(hashtags.length - 1);
    }
  };

  const addHashtag = () => {
    const trimmedValue = inputValue.trim();
    if (trimmedValue && !hashtags.includes(trimmedValue) && hashtags.length < maxTags) {
      // Ensure hashtag starts with #
      const hashtag = trimmedValue.startsWith('#') ? trimmedValue : `#${trimmedValue}`;
      onChange([...hashtags, hashtag]);
      setInputValue('');
    }
  };

  const removeHashtag = (index: number) => {
    const newHashtags = hashtags.filter((_, i) => i !== index);
    onChange(newHashtags);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    // Prevent spaces in the middle of typing
    if (value.includes(' ')) {
      const parts = value.split(' ');
      const lastPart = parts[parts.length - 1];
      
      // Add all complete hashtags
      parts.slice(0, -1).forEach(part => {
        const trimmedPart = part.trim();
        if (trimmedPart && !hashtags.includes(trimmedPart) && hashtags.length < maxTags) {
          const hashtag = trimmedPart.startsWith('#') ? trimmedPart : `#${trimmedPart}`;
          hashtags.push(hashtag);
        }
      });
      
      onChange([...hashtags]);
      setInputValue(lastPart);
    } else {
      setInputValue(value);
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2 p-3 border border-gray-300 rounded-md min-h-[42px] focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-blue-500">
        {hashtags.map((hashtag, index) => (
          <span
            key={index}
            className="inline-flex items-center px-2 py-1 rounded-full text-sm bg-blue-100 text-blue-800"
          >
            {hashtag}
            <button
              type="button"
              onClick={() => removeHashtag(index)}
              className="ml-1 inline-flex items-center justify-center w-4 h-4 rounded-full hover:bg-blue-200 focus:outline-none"
            >
              <XMarkIcon className="w-3 h-3" />
            </button>
          </span>
        ))}
        <input
          type="text"
          value={inputValue}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onBlur={addHashtag}
          className="flex-1 min-w-[120px] outline-none bg-transparent"
          placeholder={hashtags.length === 0 ? placeholder : ""}
          disabled={hashtags.length >= maxTags}
        />
      </div>
      <div className="flex justify-between text-sm text-gray-500">
        <span>Press Enter or Space to add hashtag</span>
        <span>{hashtags.length}/{maxTags} hashtags</span>
      </div>
    </div>
  );
};

export default HashtagInput;