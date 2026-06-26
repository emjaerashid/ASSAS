import { useState, useEffect } from 'react';
import api from '../../utils/api';

export default function StudentExceptions() {
  const [exceptions, setExceptions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/student/exceptions/')
      .then(setExceptions)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const reasonLabel = (reason) => reason.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

  return (
    <div>
      <div className="page-header">
        <h1>My Exceptions</h1>
        <p>View flagged exceptions from the subject assignment process</p>
      </div>

      {exceptions.some(e => e.status === 'pending') && (
        <div className="alert alert-info">
          You have pending exceptions. The administrator will review them and you will see updates here.
        </div>
      )}

      <div className="card">
        <div className="table-container">
          {loading ? (
            <div className="loading-screen">Loading exceptions...</div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Subject</th>
                  <th>Reason</th>
                  <th>Details</th>
                  <th>Status</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody>
                {exceptions.map((ex) => (
                  <tr key={ex.id}>
                    <td>
                      <strong>{ex.subject.subject_code}</strong>
                      <br /><span style={{ fontSize: '12px', color: 'var(--gray-500)' }}>{ex.subject.subject_name}</span>
                    </td>
                    <td><span className="badge badge-yellow">{reasonLabel(ex.reason)}</span></td>
                    <td style={{ fontSize: '13px', maxWidth: '300px' }}>{ex.details}</td>
                    <td>
                      {ex.status === 'pending' && <span className="badge badge-yellow">Pending Review</span>}
                      {ex.status === 'approved' && <span className="badge badge-green">Approved</span>}
                      {ex.status === 'rejected' && <span className="badge badge-red">Rejected</span>}
                    </td>
                    <td>{new Date(ex.created_at).toLocaleDateString()}</td>
                  </tr>
                ))}
                {exceptions.length === 0 && (
                  <tr><td colSpan="5" className="empty-state">No exceptions flagged for your account</td></tr>
                )}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
