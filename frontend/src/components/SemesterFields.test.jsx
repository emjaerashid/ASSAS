import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SemesterFields from './SemesterFields';
import { currentAcademicYear } from '../utils/semester';

describe('SemesterFields', () => {
  it('defaults to the current academic year and January semester when value is empty', () => {
    render(<SemesterFields value="" onChange={() => {}} />);

    expect(screen.getByPlaceholderText('Year')).toHaveValue(currentAcademicYear());
    expect(screen.getByRole('combobox')).toHaveValue('1');
  });

  it('parses an existing semester code into the year and semester fields', () => {
    render(<SemesterFields value="202405" onChange={() => {}} />);

    expect(screen.getByPlaceholderText('Year')).toHaveValue(2024);
    expect(screen.getByRole('combobox')).toHaveValue('2');
  });

  it('calls onChange with a rebuilt code when the year changes', () => {
    const onChange = vi.fn();
    render(<SemesterFields value="202405" onChange={onChange} />);

    fireEvent.change(screen.getByPlaceholderText('Year'), { target: { value: '2025' } });

    expect(onChange).toHaveBeenLastCalledWith('202505');
  });

  it('calls onChange with a rebuilt code when the semester changes', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<SemesterFields value="202401" onChange={onChange} />);

    await user.selectOptions(screen.getByRole('combobox'), '3');

    expect(onChange).toHaveBeenCalledWith('202409');
  });

  it('renders the given label', () => {
    render(<SemesterFields value="" onChange={() => {}} label="Target Semester" />);
    expect(screen.getByText('Target Semester')).toBeInTheDocument();
  });
});
