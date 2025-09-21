import React, { useState, useEffect } from 'react';
import { platformService } from '../../services/platform';
import { preferencesService, PlatformPreferences as PlatformPreferencesType, ContentTemplate } from '../../services/preferences';

interface PlatformPreferencesProps {
  platform: string;
  onClose: () => void;
}

const CONTENT_STYLES = [
  { value: 'professional', label: 'Professional' },
  { value: 'casual', label: 'Casual' },
  { value: 'promotional', label: 'Promotional' },
  { value: 'storytelling', label: 'Storytelling' }
];

const HASHTAG_STRATEGIES = [
  { value: 'trending', label: 'Trending' },
  { value: 'branded', label: 'Branded' },
  { value: 'category', label: 'Category-based' },
  { value: 'mixed', label: 'Mixed' }
];

const DAYS_OF_WEEK = [
  'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'
];

export const PlatformPreferences: React.FC<PlatformPreferencesProps> = ({
  platform,
  onClose
}) => {
  const [preferences, setPreferences] = useState<PlatformPreferencesType | null>(null);
  const [templates, setTemplates] = useState<ContentTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'general' | 'content' | 'schedule' | 'advanced'>('general');

  useEffect(() => {
    loadPreferences();
    loadTemplates();
  }, [platform]);

  const loadPreferences = async () => {
    try {
      const prefs = await preferencesService.getPlatformPreferences(platform);
      setPreferences(prefs);
    } catch (err) {
      setError('Failed to load preferences');
      console.error('Error loading preferences:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadTemplates = async () => {
    try {
      const templateList = await preferencesService.getContentTemplates({ platform });
      setTemplates(templateList);
    } catch (err) {
      console.error('Error loading templates:', err);
    }
  };

  const handleSave = async () => {
    if (!preferences) return;

    setSaving(true);
    setError(null);

    try {
      const updated = await preferencesService.updatePlatformPreferences(platform, preferences);
      setPreferences(updated);
      // Show success message or close modal
    } catch (err) {
      setError('Failed to save preferences');
      console.error('Error saving preferences:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    if (!confirm('Are you sure you want to reset preferences to defaults?')) return;

    setSaving(true);
    try {
      await preferencesService.resetPlatformPreferences(platform);
      await loadPreferences();
    } catch (err) {
      setError('Failed to reset preferences');
      console.error('Error resetting preferences:', err);
    } finally {
      setSaving(false);
    }
  };

  const updatePreference = (field: keyof PlatformPreferencesType, value: any) => {
    if (!preferences) return;
    setPreferences({ ...preferences, [field]: value });
  };

  const updateSchedule = (day: string, times: string[]) => {
    if (!preferences) return;
    setPreferences({
      ...preferences,
      posting_schedule: {
        ...preferences.posting_schedule,
        [day]: times
      }
    });
  };

  const addTimeSlot = (day: string) => {
    const currentTimes = preferences?.posting_schedule?.[day] || [];
    const newTime = '09:00';
    updateSchedule(day, [...currentTimes, newTime]);
  };

  const removeTimeSlot = (day: string, index: number) => {
    const currentTimes = preferences?.posting_schedule?.[day] || [];
    const newTimes = currentTimes.filter((_, i) => i !== index);
    updateSchedule(day, newTimes);
  };

  const updateTimeSlot = (day: string, index: number, time: string) => {
    const currentTimes = preferences?.posting_schedule?.[day] || [];
    const newTimes = [...currentTimes];
    newTimes[index] = time;
    updateSchedule(day, newTimes);
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-6">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-2 text-gray-600">Loading preferences...</p>
        </div>
      </div>
    );
  }

  if (!preferences) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-6">
          <p className="text-red-600">Failed to load preferences</p>
          <button
            onClick={onClose}
            className="mt-4 px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600"
          >
            Close
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg w-full max-w-4xl max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-xl font-semibold">
            {platform.charAt(0).toUpperCase() + platform.slice(1)} Preferences
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
            aria-label="Close preferences modal"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Tabs */}
        <div className="border-b">
          <nav className="flex space-x-8 px-6">
            {[
              { id: 'general', label: 'General' },
              { id: 'content', label: 'Content' },
              { id: 'schedule', label: 'Schedule' },
              { id: 'advanced', label: 'Advanced' }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[60vh]">
          {error && (
            <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-md">
              <p className="text-red-600">{error}</p>
            </div>
          )}

          {/* General Tab */}
          {activeTab === 'general' && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={preferences.enabled}
                      onChange={(e) => updatePreference('enabled', e.target.checked)}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="ml-2 text-sm font-medium text-gray-700">
                      Enable platform for posting
                    </span>
                  </label>
                </div>

                <div>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={preferences.auto_post}
                      onChange={(e) => updatePreference('auto_post', e.target.checked)}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="ml-2 text-sm font-medium text-gray-700">
                      Enable auto-posting
                    </span>
                  </label>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Posting Priority (0-10)
                </label>
                <input
                  type="range"
                  min="0"
                  max="10"
                  value={preferences.priority}
                  onChange={(e) => updatePreference('priority', parseInt(e.target.value))}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>Low (0)</span>
                  <span>Current: {preferences.priority}</span>
                  <span>High (10)</span>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Timezone
                </label>
                <select
                  value={preferences.timezone || 'UTC'}
                  onChange={(e) => updatePreference('timezone', e.target.value)}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="UTC">UTC</option>
                  <option value="America/New_York">Eastern Time</option>
                  <option value="America/Chicago">Central Time</option>
                  <option value="America/Denver">Mountain Time</option>
                  <option value="America/Los_Angeles">Pacific Time</option>
                  <option value="Europe/London">London</option>
                  <option value="Europe/Paris">Paris</option>
                  <option value="Asia/Tokyo">Tokyo</option>
                  <option value="Asia/Kolkata">India</option>
                </select>
              </div>
            </div>
          )}

          {/* Content Tab */}
          {activeTab === 'content' && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Content Style
                  </label>
                  <select
                    value={preferences.content_style || 'professional'}
                    onChange={(e) => updatePreference('content_style', e.target.value)}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {CONTENT_STYLES.map((style) => (
                      <option key={style.value} value={style.value}>
                        {style.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Hashtag Strategy
                  </label>
                  <select
                    value={preferences.hashtag_strategy || 'mixed'}
                    onChange={(e) => updatePreference('hashtag_strategy', e.target.value)}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {HASHTAG_STRATEGIES.map((strategy) => (
                      <option key={strategy.value} value={strategy.value}>
                        {strategy.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Maximum Hashtags: {preferences.max_hashtags}
                </label>
                <input
                  type="range"
                  min="1"
                  max="50"
                  value={preferences.max_hashtags}
                  onChange={(e) => updatePreference('max_hashtags', parseInt(e.target.value))}
                  className="w-full"
                />
              </div>

              <div className="grid grid-cols-2 gap-6">
                <div>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={preferences.include_branding}
                      onChange={(e) => updatePreference('include_branding', e.target.checked)}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="ml-2 text-sm font-medium text-gray-700">
                      Include branding
                    </span>
                  </label>
                </div>

                <div>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={preferences.include_call_to_action}
                      onChange={(e) => updatePreference('include_call_to_action', e.target.checked)}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="ml-2 text-sm font-medium text-gray-700">
                      Include call-to-action
                    </span>
                  </label>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Title Format Template
                </label>
                <input
                  type="text"
                  value={preferences.title_format || '{title}'}
                  onChange={(e) => updatePreference('title_format', e.target.value)}
                  placeholder="{title}"
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Use {'{title}'} as placeholder for the product title
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Description Format Template
                </label>
                <textarea
                  value={preferences.description_format || '{description}'}
                  onChange={(e) => updatePreference('description_format', e.target.value)}
                  placeholder="{description}"
                  rows={3}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Use {'{description}'} as placeholder for the product description
                </p>
              </div>
            </div>
          )}

          {/* Schedule Tab */}
          {activeTab === 'schedule' && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={preferences.auto_schedule}
                      onChange={(e) => updatePreference('auto_schedule', e.target.checked)}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="ml-2 text-sm font-medium text-gray-700">
                      Enable auto-scheduling
                    </span>
                  </label>
                </div>

                <div>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={preferences.optimal_times_enabled}
                      onChange={(e) => updatePreference('optimal_times_enabled', e.target.checked)}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="ml-2 text-sm font-medium text-gray-700">
                      Use optimal posting times
                    </span>
                  </label>
                </div>
              </div>

              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4">Weekly Schedule</h3>
                <div className="space-y-4">
                  {DAYS_OF_WEEK.map((day) => (
                    <div key={day} className="flex items-center space-x-4">
                      <div className="w-24 text-sm font-medium text-gray-700 capitalize">
                        {day}
                      </div>
                      <div className="flex-1 flex flex-wrap gap-2">
                        {(preferences.posting_schedule?.[day] || []).map((time, index) => (
                          <div key={index} className="flex items-center space-x-2">
                            <input
                              type="time"
                              value={time}
                              onChange={(e) => updateTimeSlot(day, index, e.target.value)}
                              className="border border-gray-300 rounded px-2 py-1 text-sm"
                            />
                            <button
                              onClick={() => removeTimeSlot(day, index)}
                              className="text-red-500 hover:text-red-700"
                            >
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                              </svg>
                            </button>
                          </div>
                        ))}
                        <button
                          onClick={() => addTimeSlot(day)}
                          className="text-blue-500 hover:text-blue-700 text-sm"
                        >
                          + Add Time
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Advanced Tab */}
          {activeTab === 'advanced' && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={preferences.image_optimization}
                      onChange={(e) => updatePreference('image_optimization', e.target.checked)}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="ml-2 text-sm font-medium text-gray-700">
                      Enable image optimization
                    </span>
                  </label>
                </div>

                <div>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={preferences.watermark_enabled}
                      onChange={(e) => updatePreference('watermark_enabled', e.target.checked)}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="ml-2 text-sm font-medium text-gray-700">
                      Enable watermark
                    </span>
                  </label>
                </div>
              </div>

              {/* Platform-specific settings would go here */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4">Platform-Specific Settings</h3>
                <div className="bg-gray-50 p-4 rounded-md">
                  <p className="text-sm text-gray-600">
                    Platform-specific settings for {platform} will be displayed here.
                  </p>
                  {/* This would be dynamically populated based on the platform */}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t bg-gray-50">
          <button
            onClick={handleReset}
            disabled={saving}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
          >
            Reset to Defaults
          </button>
          <div className="flex space-x-3">
            <button
              onClick={onClose}
              disabled={saving}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save Preferences'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};