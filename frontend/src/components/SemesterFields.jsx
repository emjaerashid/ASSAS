import { buildSemesterCode, parseSemesterCode, currentAcademicYear } from '../utils/semester';

export default function SemesterFields({ value, onChange, label = 'Semester', required = true }) {
  const parsed = parseSemesterCode(value) || { year: currentAcademicYear(), sem: 1 };

  const update = (year, sem) => onChange(buildSemesterCode(year, sem));

  return (
    <div className="form-group">
      <label>{label}</label>
      <div style={{ display: 'flex', gap: '8px' }}>
        <input type="number" className="form-control" value={parsed.year} placeholder="Year"
          onChange={(e) => update(e.target.value, parsed.sem)} required={required} />
        <select className="form-control" value={parsed.sem}
          onChange={(e) => update(parsed.year, parseInt(e.target.value))}>
          <option value={1}>January Semester</option>
          <option value={2}>May Semester</option>
          <option value={3}>September Semester</option>
        </select>
      </div>
    </div>
  );
}
