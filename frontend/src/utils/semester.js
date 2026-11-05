// Registration-period semester codes follow <academic year><intake month>:
// Semester 1 -> January (01), Semester 2 -> May (05), Semester 3 -> September (09).
// e.g. 2024 Semester 1 -> "202401", 2024 Semester 2 -> "202405".
export const SEMESTER_MONTHS = { 1: '01', 2: '05', 3: '09' };
const MONTH_TO_SEMESTER = { '01': 1, '05': 2, '09': 3 };

export function buildSemesterCode(year, sem) {
  return `${year}${SEMESTER_MONTHS[sem] || '01'}`;
}

export function parseSemesterCode(code) {
  if (!/^\d{6}$/.test(code || '')) return null;
  const year = code.slice(0, 4);
  const sem = MONTH_TO_SEMESTER[code.slice(4, 6)];
  return sem ? { year, sem } : null;
}

export function currentAcademicYear() {
  return new Date().getFullYear();
}

// Buckets today's date into the nearest intake: Jan-Apr -> Sem 1, May-Aug -> Sem 2,
// Sep-Dec -> Sem 3, so callers get a live default instead of a stale hardcoded code.
export function currentSemesterCode() {
  const now = new Date();
  const month = now.getMonth() + 1;
  const sem = month <= 4 ? 1 : month <= 8 ? 2 : 3;
  return buildSemesterCode(now.getFullYear(), sem);
}

// The intake in a semester code fixes its length: January and May are long
// semesters (19 weeks), September is short (12 weeks). Subject ranges mirror
// the backend's SEMESTER_DURATION_MIN/MAX_SUBJECTS maps.
export const INTAKES = {
  1: { label: 'January Semester', durationWeeks: 19, minSubjects: 5, maxSubjects: 7 },
  2: { label: 'May Semester', durationWeeks: 19, minSubjects: 5, maxSubjects: 7 },
  3: { label: 'September Semester', durationWeeks: 12, minSubjects: 3, maxSubjects: 3 },
};

export function semesterIntake(code) {
  return INTAKES[parseSemesterCode(code)?.sem] || null;
}
