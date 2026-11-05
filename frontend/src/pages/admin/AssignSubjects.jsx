import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../../utils/api';
import { useFeedback, notifyCountsChanged } from '../../context/FeedbackContext';
import SemesterFields from '../../components/SemesterFields';
import { currentSemesterCode, semesterIntake } from '../../utils/semester';

function needsAttention(result) {
  return result.underload || result.exceptions.length > 0;
}

export default function AssignSubjects() {
  const { toast } = useFeedback();
  const [semester, setSemester] = useState(currentSemesterCode);
  const [facultyCode, setFacultyCode] = useState('');
  const [faculties, setFaculties] = useState([]);
  const [programmeCode, setProgrammeCode] = useState('');
  const [programmes, setProgrammes] = useState([]);
  const [results, setResults] = useState(null);
  const [attentionOnly, setAttentionOnly] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    api.get('/programmes/').then(setProgrammes).catch(console.error);
    api.get('/admin/faculties/').then(setFaculties).catch(console.error);
  }, []);

  const intake = semesterIntake(semester);

  const visibleProgrammes = facultyCode
    ? programmes.filter((p) => p.faculty === facultyCode)
    : programmes;

  const handleFacultyChange = (value) => {
    setFacultyCode(value);
    if (programmeCode && !programmes.some((p) => p.programme_code === programmeCode && (!value || p.faculty === value))) {
      setProgrammeCode('');
    }
  };

  const handleAssign = async (e) => {
    e.preventDefault();
    setError('');
    setResults(null);
    setLoading(true);

    try {
      const body = { semester, duration_weeks: intake?.durationWeeks };
      if (programmeCode) body.programme_code = programmeCode;
      if (facultyCode) body.faculty_code = facultyCode;
      const data = await api.post('/admin/assign/', body);
      setResults(data);
      setAttentionOnly(data.results.some(needsAttention));
      notifyCountsChanged();
      toast.success(`Assignment completed for ${data.total_students} student(s).`);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const renderSingleResult = (result) => (
    <div className="card mb-24" key={result.student_id}>
      <div className="card-header">
        <h3>
          {result.student_name || result.student_id}
          {result.student_name && (
            <span className="mono" style={{ marginLeft: '8px', fontWeight: 400, color: 'var(--gray-500)', fontSize: '12.5px' }}>
              {result.student_id}
            </span>
          )}
        </h3>
        <div className="btn-group">
          {result.underload && (
            <span className="badge badge-red" title={`Fewer than the required ${result.min_subjects_required} subjects for this semester`}>
              Underload
            </span>
          )}
          {result.exceptions.length > 0 && (
            <span className="badge badge-yellow">{result.exceptions.length} exception(s)</span>
          )}
          {result.skipped ? (
            <span className="badge badge-gray">Already assigned — skipped</span>
          ) : (
            <span className="badge badge-blue">{result.assigned_credits} credits assigned</span>
          )}
        </div>
      </div>
      <div className="card-body">
        {result.skipped && (
          <p style={{ marginBottom: '12px', fontSize: '13px', color: 'var(--gray-500)' }}>
            This student already has subjects assigned for semester {result.semester}; assignment was not repeated.
          </p>
        )}
        {result.underload && (
          <p style={{ marginBottom: '12px', fontSize: '13px', color: 'var(--red)' }}>
            Only {result.assigned.length} subject(s) assigned — below the minimum of {result.min_subjects_required} for this semester. Review for missing time slots, unmet prerequisites, or exceptions.
          </p>
        )}
        {result.assigned.length > 0 && (
          <div className="mb-16">
            <strong>{result.skipped ? 'Existing Assigned Subjects:' : 'Assigned Subjects:'}</strong>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '8px' }}>
              {result.assigned.map((code) => (
                <span key={code} className={`mono ${result.skipped ? 'badge badge-blue' : 'badge badge-green'}`}>{code}</span>
              ))}
            </div>
          </div>
        )}
        {result.exceptions.length > 0 && (
          <div>
            <strong>Exceptions Flagged:</strong>
            <div className="card table-container" style={{ marginTop: '8px', boxShadow: 'none' }}>
              <table>
                <thead>
                  <tr>
                    <th>Student ID</th>
                    <th>Name</th>
                    <th>Current Semester</th>
                    <th>Subject</th>
                    <th>Reason</th>
                    <th>Details</th>
                  </tr>
                </thead>
                <tbody>
                  {result.exceptions.map((ex, i) => (
                    <tr key={i}>
                      <td className="mono">{result.student_id}</td>
                      <td>{result.student_name}</td>
                      <td>Semester {result.current_semester}</td>
                      <td><span className="badge badge-red mono">{ex.subject_code}</span></td>
                      <td style={{ textTransform: 'capitalize' }}>{ex.reason.replace(/_/g, ' ')}</td>
                      <td style={{ fontSize: '13px', color: 'var(--gray-500)' }}>{ex.details}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
        {!result.skipped && result.assigned.length === 0 && result.exceptions.length === 0 && (
          <p className="empty-state">No subjects to assign for this semester.</p>
        )}
      </div>
    </div>
  );

  const summary = results && {
    assigned: results.results.reduce((n, r) => n + (r.skipped ? 0 : r.assigned.length), 0),
    exceptions: results.results.reduce((n, r) => n + r.exceptions.length, 0),
    underload: results.results.filter((r) => r.underload).length,
    skipped: results.results.filter((r) => r.skipped).length,
  };
  const shownResults = results
    ? results.results.filter((r) => !attentionOnly || needsAttention(r))
    : [];

  return (
    <div>
      <div className="page-header">
        <h1>Assign Subjects</h1>
        <p>Run the rule engine to assign subjects to every eligible student automatically</p>
      </div>

      <div className="card mb-24">
        <div className="card-body">
          <form onSubmit={handleAssign}>
            {error && <div className="alert alert-error">{error}</div>}
            <div className="grid-2">
              <div>
                <SemesterFields value={semester} onChange={setSemester} />
                {intake && (
                  <p className="form-hint" style={{ marginTop: '-10px', marginBottom: '16px' }}>
                    Code <span className="mono">{semester}</span> · {intake.durationWeeks}-week semester
                    · {intake.minSubjects === intake.maxSubjects ? intake.maxSubjects : `${intake.minSubjects}–${intake.maxSubjects}`} subjects per student
                  </p>
                )}
              </div>
              <div className="form-group">
                <label>Faculty</label>
                <select className="form-control" value={facultyCode}
                  onChange={(e) => handleFacultyChange(e.target.value)}>
                  <option value="">All Faculties</option>
                  {faculties.map((f) => (
                    <option key={f.faculty_code} value={f.faculty_code}>
                      {f.faculty_code} - {f.faculty_name}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className="grid-2">
              <div className="form-group">
                <label>Programme</label>
                <select className="form-control" value={programmeCode}
                  onChange={(e) => setProgrammeCode(e.target.value)}>
                  <option value="">All Programmes</option>
                  {visibleProgrammes.map((p) => (
                    <option key={p.programme_code} value={p.programme_code}>
                      {p.programme_code} - {p.programme_name}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <button type="submit" className="btn btn-primary" disabled={loading || !intake}>
              {loading
                ? <><span className="spinner" />Running Rule Engine...</>
                : <><span className="material-symbols-outlined">bolt</span>Run Subject Assignment</>}
            </button>
          </form>
        </div>
      </div>

      {results && (
        <div>
          <div className="result-summary">
            <div className="stat-card">
              <div className="stat-label">Students processed</div>
              <div className="stat-value">{results.total_students}</div>
            </div>
            <div className="stat-card green">
              <div className="stat-label">Subjects assigned</div>
              <div className="stat-value">{summary.assigned}</div>
            </div>
            <div className="stat-card amber">
              <div className="stat-label">Exceptions flagged</div>
              <div className="stat-value">{summary.exceptions}</div>
            </div>
            <div className="stat-card red">
              <div className="stat-label">Underloaded</div>
              <div className="stat-value">{summary.underload}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Skipped</div>
              <div className="stat-value">{summary.skipped}</div>
            </div>
          </div>

          <div className="flex-between mb-16" style={{ gap: '12px', flexWrap: 'wrap' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', cursor: 'pointer' }}>
              <input type="checkbox" checked={attentionOnly} onChange={(e) => setAttentionOnly(e.target.checked)} />
              Only show students that need attention
            </label>
            {summary.exceptions > 0 && (
              <Link className="btn btn-secondary btn-sm" to="/admin/exceptions">
                <span className="material-symbols-outlined">flag</span>Review {summary.exceptions} exception(s)
              </Link>
            )}
          </div>

          {shownResults.map(renderSingleResult)}
          {shownResults.length === 0 && (
            <div className="card"><p className="empty-state">Every student was assigned cleanly — nothing needs attention.</p></div>
          )}
        </div>
      )}
    </div>
  );
}
