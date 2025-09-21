import React from 'react';
import { render, screen } from '@testing-library/react';
import App from './App';

test('renders artisan promotion platform header', () => {
  render(<App />);
  const titleElement = screen.getByRole('heading', { name: /artisan promotion platform/i });
  expect(titleElement).toBeInTheDocument();
});

test('renders welcome message', () => {
  render(<App />);
  const welcomeElement = screen.getByText(/welcome to the artisan promotion platform/i);
  expect(welcomeElement).toBeInTheDocument();
});