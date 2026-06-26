import { useState, useEffect } from 'react';
import api from '../../utils/api';

export default function Timetables() {
  const [timetables, setTimetables] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [title, setTitle] = useState('');
  const [semester, setSemester] = useState('202601');
  const [programme, setProgramme] = useState('BCSSE');
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');

  const fetchTimetables = () => {
    setLoading(true);
    api.get('/admin/timetables/')
      .then(setTimetables)
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(fetchTimetables, []);

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) return;
    setError('');
    setUploading(true);

    try {
      const formData = new FormData();
      formData.append('title', title);
      formData.append('semester', semester);
      formData.append('programme', programme);
      formData.append('file', file);

      await api.post('/admin/timetables/', formData);
      setShowModal(false);
      setTitle('');
      setFile(null);
      fetchTimetables();
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Delete this timetable?')) return;
    try {
      await api.delete(`/admin/timetables/${id}/`);
      fetchTimetables();
    } catch (err) {
      alert(err.message);
    }
  };

  return (
    <div>
      <div className="page-header flex-between">
        <div>
          <h1>Timetable Management</h1>
          <p>Upload and manage faculty master timetables</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowModal(true)}>
          + Upload Timetable
        </button>
      </div>

      <div className="card">
        <div className="table-container">
          {loading ? (
            <div className="loading-screen">Loading timetables...</div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Programme</th>
                  <th>Semester</th>
                  <th>Uploaded By</th>
                  <th>Date</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {timetables.map((tt) => (
                  <tr key={tt.id}>
                    <td><strong>{tt.title}</strong></td>
                    <td>{tt.programme}</td>
                    <td>{tt.semester}</td>
                    <td>{tt.uploaded_by_name || '—'}</td>
                    <td>{new Date(tt.uploaded_at).toLocaleDateString()}</td>
                    <td>
                      <div className="btn-group">
                        <a href={tt.file} target="_blank" rel="noreferrer" className="btn btn-secondary btn-sm">
                          View
                        </a>
                        <button className="btn btn-danger btn-sm" onClick={() => handleDelete(tt.id)}>
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {timetables.length === 0 && (
                  <tr><td colSpan="6" className="empty-state">No timetables uploaded</td></tr>
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
              <h3>Upload Timetable</h3>
              <button className="close-btn" onClick={() => setShowModal(false)}>&times;</button>
            </div>
            <form onSubmit={handleUpload}>
              <div className="modal-body">
                {error && <div className="alert alert-error">{error}</div>}
                <div className="form-group">
                  <label>Title</label>
                  <input className="form-control" value={title}
                    onChange={(e) => setTitle(e.target.value)} required
                    placeholder="e.g. BCSSE Semester 1 2026 Timetable" />
                </div>
                <div className="grid-2">
                  <div className="form-group">
                    <label>Semester</label>
                    <input className="form-control" value={semester}
                      onChange={(e) => setSemester(e.target.value)} required />
                  </div>
                  <div className="form-group">
                    <label>Programme</label>
                    <input className="form-control" value={programme}
                      onChange={(e) => setProgramme(e.target.value)} required />
                  </div>
                </div>
                <div className="form-group">
                  <label>File (PDF or Image)</label>
                  <input type="file" className="form-control"
                    accept=".pdf,.png,.jpg,.jpeg"
                    onChange={(e) => setFile(e.target.files[0])} required />
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-outline" onClick={() => setShowModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={uploading}>
                  {uploading ? 'Uploading...' : 'Upload'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
