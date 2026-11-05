import { describe, it, expect, vi, afterEach } from 'vitest';
import {
  buildSemesterCode, parseSemesterCode, currentAcademicYear, currentSemesterCode,
} from './semester';

describe('buildSemesterCode', () => {
  it('maps semester 1/2/3 to intake months 01/05/09', () => {
    expect(buildSemesterCode(2024, 1)).toBe('202401');
    expect(buildSemesterCode(2024, 2)).toBe('202405');
    expect(buildSemesterCode(2024, 3)).toBe('202409');
  });

  it('falls back to 01 for an unrecognised semester', () => {
    expect(buildSemesterCode(2024, 4)).toBe('202401');
  });
});

describe('parseSemesterCode', () => {
  it('parses a valid code into year and semester', () => {
    expect(parseSemesterCode('202405')).toEqual({ year: '2024', sem: 2 });
  });

  it('returns null for malformed codes', () => {
    expect(parseSemesterCode('2024')).toBeNull();
    expect(parseSemesterCode('20240599')).toBeNull();
    expect(parseSemesterCode('abcdef')).toBeNull();
    expect(parseSemesterCode(null)).toBeNull();
    expect(parseSemesterCode(undefined)).toBeNull();
  });

  it('returns null when the intake month has no matching semester', () => {
    expect(parseSemesterCode('202403')).toBeNull();
  });
});

describe('currentAcademicYear', () => {
  it('returns the current calendar year', () => {
    expect(currentAcademicYear()).toBe(new Date().getFullYear());
  });
});

describe('currentSemesterCode', () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it('buckets Jan-Apr into semester 1', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2024, 1, 15)); // Feb
    expect(currentSemesterCode()).toBe('202401');
  });

  it('buckets May-Aug into semester 2', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2024, 5, 15)); // Jun
    expect(currentSemesterCode()).toBe('202405');
  });

  it('buckets Sep-Dec into semester 3', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2024, 9, 15)); // Oct
    expect(currentSemesterCode()).toBe('202409');
  });

  it('handles the boundary months correctly', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2024, 3, 30)); // Apr 30 -> still sem 1
    expect(currentSemesterCode()).toBe('202401');

    vi.setSystemTime(new Date(2024, 4, 1)); // May 1 -> sem 2
    expect(currentSemesterCode()).toBe('202405');

    vi.setSystemTime(new Date(2024, 7, 31)); // Aug 31 -> still sem 2
    expect(currentSemesterCode()).toBe('202405');

    vi.setSystemTime(new Date(2024, 8, 1)); // Sep 1 -> sem 3
    expect(currentSemesterCode()).toBe('202409');
  });
});
