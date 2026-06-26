import { useState, useEffect } from 'react';
import api from '../../utils/api';

export default function Subjects() {
  const [subjects, setSubjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [yearFilter, setYearFilter] = useState('');
  const [semFilter, setSemFilter] = useState('');

  useEffect(() => {
    setLoading(true);
    let query = '?programme=BCSSE';
    if (yearFilter) query += `&year=${yearFilter}`;
    if (semFilter) query += `&semester=${semFilter}`;

    api.get(`/subjects/${query}`)
      .then(setSubjects)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [yearFilter, semFilter]);

  return (
    <div>
      <div className="page-header">
        <h1>Subject Catalogue</h1>
        <p>BCSSE programme subjects and prerequisites</p>
      </div>

      <div className="mb-16" style={{ display: 'flex', gap: '12px' }}>
        <select className="form-control" style={{ width: '150px' }} value={yearFilter}
          onChange={(e) => setYearFilter(e.target.value)}>
          <option value="">All Years</option>
          {[1, 2, 3, 4].map((y) => <option key={y} value={y}>Year {y}</option>)}
        </select>
        <select className="form-control" style={{ width: '180px' }} value={semFilter}
          onChange={(e) => setSemFilter(e.target.value)}>
          <option value="">All Semesters</option>
          <option value="1">Semester 1</option>
          <option value="2">Semester 2</option>
        </select>
      </div>

      <div className="card">
        <div className="table-container">
          {loading ? (
            <div className="loading-screen">Loading subjects...</div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Subject Name</th>
                  <th>Credits</th>
                  <th>Year</th>
                  <th>Semester</th>
                  <th>Prerequisites</th>
                </tr>
              </thead>
              <tbody>
                {subjects.map((s) => (
                  <tr key={s.subject_code}>
                    <td><strong>{s.subject_code}</strong></td>
                    <td>{s.subject_name}</td>
                    <td>{s.credit_hours}</td>
                    <td>{s.year}</td>
                    <td>{s.semester}</td>
                    <td>
                      {s.prerequisites.length > 0 ? (
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                          {s.prerequisites.map((p) => (
                            <span key={p.subject_code} className="badge badge-blue" title={p.subject_name}>
                              {p.subject_code}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span style={{ color: 'var(--gray-400)' }}>None</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
