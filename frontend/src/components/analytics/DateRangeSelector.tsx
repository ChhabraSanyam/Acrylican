import React, { useState } from 'react';
import { format, subDays, startOfWeek, startOfMonth, startOfYear } from 'date-fns';

interface DateRangeSelectorProps {
  startDate: Date;
  endDate: Date;
  onChange: (startDate: Date, endDate: Date) => void;
}

const DateRangeSelector: React.FC<DateRangeSelectorProps> = ({
  startDate,
  endDate,
  onChange
}) => {
  const [isCustom, setIsCustom] = useState(false);
  const [customStartDate, setCustomStartDate] = useState(format(startDate, 'yyyy-MM-dd'));
  const [customEndDate, setCustomEndDate] = useState(format(endDate, 'yyyy-MM-dd'));

  const presetRanges = [
    {
      label: 'Last 7 days',
      value: '7d',
      getRange: () => ({
        start: subDays(new Date(), 7),
        end: new Date()
      })
    },
    {
      label: 'Last 30 days',
      value: '30d',
      getRange: () => ({
        start: subDays(new Date(), 30),
        end: new Date()
      })
    },
    {
      label: 'Last 90 days',
      value: '90d',
      getRange: () => ({
        start: subDays(new Date(), 90),
        end: new Date()
      })
    },
    {
      label: 'This week',
      value: 'week',
      getRange: () => ({
        start: startOfWeek(new Date()),
        end: new Date()
      })
    },
    {
      label: 'This month',
      value: 'month',
      getRange: () => ({
        start: startOfMonth(new Date()),
        end: new Date()
      })
    },
    {
      label: 'This year',
      value: 'year',
      getRange: () => ({
        start: startOfYear(new Date()),
        end: new Date()
      })
    }
  ];

  const handlePresetChange = (preset: string) => {
    if (preset === 'custom') {
      setIsCustom(true);
      return;
    }

    setIsCustom(false);
    const range = presetRanges.find(p => p.value === preset);
    if (range) {
      const { start, end } = range.getRange();
      onChange(start, end);
    }
  };

  const handleCustomDateChange = () => {
    const start = new Date(customStartDate);
    const end = new Date(customEndDate);
    
    if (start <= end) {
      onChange(start, end);
      setIsCustom(false);
    }
  };

  const getCurrentPreset = () => {
    try {
      const currentRange = presetRanges.find(preset => {
        const { start, end } = preset.getRange();
        if (!start || !end || !startDate || !endDate) return false;
        return (
          Math.abs(start.getTime() - startDate.getTime()) < 24 * 60 * 60 * 1000 &&
          Math.abs(end.getTime() - endDate.getTime()) < 24 * 60 * 60 * 1000
        );
      });
      return currentRange?.value || 'custom';
    } catch (error) {
      return 'custom';
    }
  };

  return (
    <div className="flex items-center space-x-4">
      <div className="flex items-center space-x-2">
        <label htmlFor="date-range" className="text-sm font-medium text-gray-700">
          Date Range:
        </label>
        <select
          id="date-range"
          value={isCustom ? 'custom' : getCurrentPreset()}
          onChange={(e) => handlePresetChange(e.target.value)}
          className="border border-gray-300 rounded-md px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
        >
          {presetRanges.map(preset => (
            <option key={preset.value} value={preset.value}>
              {preset.label}
            </option>
          ))}
          <option value="custom">Custom Range</option>
        </select>
      </div>

      {isCustom && (
        <div className="flex items-center space-x-2">
          <input
            type="date"
            value={customStartDate}
            onChange={(e) => setCustomStartDate(e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          />
          <span className="text-gray-500">to</span>
          <input
            type="date"
            value={customEndDate}
            onChange={(e) => setCustomEndDate(e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          />
          <button
            onClick={handleCustomDateChange}
            className="px-3 py-1 bg-indigo-600 text-white text-sm rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            Apply
          </button>
          <button
            onClick={() => setIsCustom(false)}
            className="px-3 py-1 bg-gray-300 text-gray-700 text-sm rounded-md hover:bg-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-500"
          >
            Cancel
          </button>
        </div>
      )}

      {!isCustom && (
        <div className="text-sm text-gray-600">
          {format(startDate, 'MMM d, yyyy')} - {format(endDate, 'MMM d, yyyy')}
        </div>
      )}
    </div>
  );
};

export default DateRangeSelector;