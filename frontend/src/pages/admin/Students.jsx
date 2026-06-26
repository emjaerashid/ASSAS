import { useState, useEffect } from 'react';
import api from '../../utils/api';

export default function Students() {
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({
    student_id: '', full_name: '', ic_passport: '',
    programme_code: 'BCSSE', current_year: 1, current_semester: 1,
    status: 'active', is_repeat: false, is_transfer: false,
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const fetchStudents = () => {
    setLoading(true);
    api.get('/admin/students/')
      .then(setStudents)
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(fetchStudents, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    setError('');
    try {
      await api.post('/admin/students/create/', form);
      setSuccess('Student created successfully!');
      setShowModal(false);
      setForm({
        student_id: '', full_name: '', ic_passport: '',
        programme_code: 'BCSSE', current_year: 1, current_semester: 1,
        status: 'active', is_repeat: false, is_transfer: false,
      });
      fetchStudents();
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError(err.message);
    }
  };

  const statusBadge = (status) => {
    const map = {
      active: 'badge-green',
      probation: 'badge-red',
      graduated: 'badge-blue',
      suspended: 'badge-yellow',
    };
    return <span className={`badge ${map[status] || 'badge-gray'}`}>{status}</span>;
  };

  return (
    <div>
      <div className="page-header flex-between">
        <div>
          <h1>Student Management</h1>
          <p>View and manage student accounts</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowModal(true)}>
          + Add Student
        </button>
      </div>

      {success && <div className="alert alert-success">{success}</div>}

      <div className="card">
        <div className="table-container">
          {loading ? (
            <div className="loading-screen">Loading students...</div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Student ID</th>
                  <th>Name</th>
                  <th>Programme</th>
                  <th>Year</th>
                  <th>Semester</th>
                  <th>Status</th>
                  <th>Credits Earned</th>
                  <th>CGPA</th>
                </tr>
              </thead>
              <tbody>
                {students.map((s) => (
                  <tr key={s.id}>
                    <td><strong>{s.user.student_id}</strong></td>
                    <td>{s.user.full_name}</td>
                    <td>{s.programme.programme_code}</td>
                    <td>{s.current_year}</td>
                    <td>{s.current_semester}</td>
                    <td>{statusBadge(s.status)}</td>
                    <td>{s.total_credits_earned}</td>
                    <td>{s.cgpa}</td>
                  </tr>
                ))}
                {students.length === 0 && (
                  <tr><td colSpan="8" className="empty-state">No students found</td></tr>
                )}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Add New Student</h3>
              <button className="close-btn" onClick={() => setShowModal(false)}>&times;</button>
            </div>
            <form onSubmit={handleCreate}>
              <div className="modal-body">
                {error && <div className="alert alert-error">{error}</div>}
                <div className="grid-2">
                  <div className="form-group">
                    <label>Student ID</label>
                    <input className="form-control" value={form.student_id}
                      onChange={(e) => setForm({...form, student_id: e.target.value})} required />
                  </div>
                  <div className="form-group">
                    <label>Full Name</label>
                    <input className="form-control" value={form.full_name}
                      onChange={(e) => setForm({...form, full_name: e.target.value})} required />
                  </div>
                </div>
                <div className="form-group">
                  <label>IC / Passport Number</label>
                  <input className="form-control" value={form.ic_passport}
                    onChange={(e) => setForm({...form, ic_passport: e.target.value})} required />
                </div>
                <div className="grid-2">
                  <div className="form-group">
                    <label>Year</label>
                    <select className="form-control" value={form.current_year}
                      onChange={(e) => setForm({...form, current_year: parseInt(e.target.value)})}>
                      {[1,2,3,4].map(y => <option key={y} value={y}>Year {y}</option>)}
                    </select>
                  </div>
                  <div className="form-group">
                    <label>Semester</label>
                    <select className="form-control" value={form.current_semester}
                      onChange={(e) => setForm({...form, current_semester: parseInt(e.target.value)})}>
                      {[1,2].map(s => <option key={s} value={s}>Semester {s}</option>)}
                    </select>
                  </div>
                </div>
                <div className="form-group">
                  <label>Status</label>
                  <select className="form-control" value={form.status}
                    onChange={(e) => setForm({...form, status: e.target.value})}>
                    <option value="active">Active</option>
                    <option value="probation">On Probation</option>
                  </select>
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-outline" onClick={() => setShowModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Create Student</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
