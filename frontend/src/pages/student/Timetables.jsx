import { useState, useEffect } from 'react';
import api from '../../utils/api';

export default function StudentTimetables() {
  const [timetables, setTimetables] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/student/timetables/')
      .then(setTimetables)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <div className="page-header">
        <h1>Faculty Timetables</h1>
        <p>View master timetables for your programme</p>
      </div>

      {loading ? (
        <div className="loading-screen">Loading timetables...</div>
      ) : timetables.length === 0 ? (
        <div className="card">
          <div className="card-body empty-state">
            <p>No timetables have been uploaded for your programme yet.</p>
          </div>
        </div>
      ) : (
        <div style={{ display: 'grid', gap: '16px' }}>
          {timetables.map((tt) => (
            <div className="card" key={tt.id}>
              <div className="card-header">
                <h3>{tt.title}</h3>
                <span className="badge badge-blue">{tt.semester}</span>
              </div>
              <div className="card-body">
                <p style={{ marginBottom: '12px', fontSize: '13px', color: 'var(--gray-500)' }}>
                  Uploaded on {new Date(tt.uploaded_at).toLocaleDateString()}
                </p>
                {tt.file && (tt.file.endsWith('.pdf') ? (
                  <a href={tt.file} target="_blank" rel="noreferrer" className="btn btn-secondary">
                    View PDF Timetable
                  </a>
                ) : (
                  <div>
                    <img
                      src={tt.file}
                      alt={tt.title}
                      style={{ maxWidth: '100%', borderRadius: '8px', border: '1px solid var(--gray-200)' }}
                    />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
