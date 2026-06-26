import { useState } from 'react';
import api from '../../utils/api';

export default function AssignSubjects() {
  const [semester, setSemester] = useState('202601');
  const [studentId, setStudentId] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleAssign = async (e) => {
    e.preventDefault();
    setError('');
    setResults(null);
    setLoading(true);

    try {
      const body = { semester };
      if (studentId.trim()) body.student_id = studentId.trim();
      const data = await api.post('/admin/assign/', body);
      setResults(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const renderSingleResult = (result) => (
    <div className="card mb-24" key={result.student_id}>
      <div className="card-header">
        <h3>Student: {result.student_id}</h3>
        <span className="badge badge-blue">{result.assigned_credits} credits assigned</span>
      </div>
      <div className="card-body">
        {result.assigned.length > 0 && (
          <div className="mb-16">
            <strong>Assigned Subjects:</strong>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '8px' }}>
              {result.assigned.map((code) => (
                <span key={code} className="badge badge-green">{code}</span>
              ))}
            </div>
          </div>
        )}
        {result.exceptions.length > 0 && (
          <div>
            <strong>Exceptions Flagged:</strong>
            <table style={{ marginTop: '8px' }}>
              <thead>
                <tr>
                  <th>Subject</th>
                  <th>Reason</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {result.exceptions.map((ex, i) => (
                  <tr key={i}>
                    <td><span className="badge badge-red">{ex.subject_code}</span></td>
                    <td>{ex.reason.replace(/_/g, ' ')}</td>
                    <td style={{ fontSize: '13px', color: 'var(--gray-500)' }}>{ex.details}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {result.assigned.length === 0 && result.exceptions.length === 0 && (
          <p className="empty-state">No subjects to assign for this semester.</p>
        )}
      </div>
    </div>
  );

  return (
    <div>
      <div className="page-header">
        <h1>Assign Subjects</h1>
        <p>Trigger the rule engine to automatically assign subjects to students</p>
      </div>

      <div className="card mb-24">
        <div className="card-body">
          <form onSubmit={handleAssign}>
            {error && <div className="alert alert-error">{error}</div>}
            <div className="grid-2">
              <div className="form-group">
                <label>Semester Code</label>
                <input className="form-control" value={semester}
                  onChange={(e) => setSemester(e.target.value)}
                  placeholder="e.g. 202601" required />
              </div>
              <div className="form-group">
                <label>Student ID (leave empty for all students)</label>
                <input className="form-control" value={studentId}
                  onChange={(e) => setStudentId(e.target.value)}
                  placeholder="e.g. 202209020001" />
              </div>
            </div>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Running Rule Engine...' : 'Run Subject Assignment'}
            </button>
          </form>
        </div>
      </div>

      {results && (
        <div>
          {results.results ? (
            <>
              <div className="alert alert-success">
                Assignment completed for {results.total_students} student(s) in semester {results.semester}.
              </div>
              {results.results.map(renderSingleResult)}
            </>
          ) : (
            renderSingleResult(results)
          )}
        </div>
      )}
    </div>
  );
}
