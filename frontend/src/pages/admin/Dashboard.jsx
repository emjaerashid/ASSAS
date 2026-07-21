import { useState, useEffect } from 'react';
import api from '../../utils/api';

const emptyFacultyForm = { faculty_code: '', faculty_name: '' };
const emptyProgrammeForm = {
  programme_code: '', programme_name: '', faculty_code: '',
  total_credits: 120, max_credits_per_sem: 21, probation_credit_cap: 12, total_semesters: 8,
};

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [faculties, setFaculties] = useState([]);

  const [showFacultyModal, setShowFacultyModal] = useState(false);
  const [facultyForm, setFacultyForm] = useState(emptyFacultyForm);
  const [facultyError, setFacultyError] = useState('');

  const [showProgrammeModal, setShowProgrammeModal] = useState(false);
  const [programmeForm, setProgrammeForm] = useState(emptyProgrammeForm);
  const [programmeError, setProgrammeError] = useState('');

  const [success, setSuccess] = useState('');

  const fetchFaculties = () => {
    api.get('/admin/faculties/').then(setFaculties).catch(console.error);
  };

  useEffect(() => {
    api.get('/admin/dashboard/')
      .then(setStats)
      .catch(console.error)
      .finally(() => setLoading(false));
    fetchFaculties();
  }, []);

  const openFacultyModal = () => {
    setFacultyForm(emptyFacultyForm);
    setFacultyError('');
    setShowFacultyModal(true);
  };

  const openProgrammeModal = () => {
    setProgrammeForm({ ...emptyProgrammeForm, faculty_code: faculties[0]?.faculty_code || '' });
    setProgrammeError('');
    setShowProgrammeModal(true);
  };

  const handleCreateFaculty = async (e) => {
    e.preventDefault();
    setFacultyError('');
    try {
      await api.post('/admin/faculties/', facultyForm);
      setShowFacultyModal(false);
      setSuccess('Faculty created successfully!');
      fetchFaculties();
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setFacultyError(err.message);
    }
  };

  const handleCreateProgramme = async (e) => {
    e.preventDefault();
    setProgrammeError('');
    try {
      await api.post('/admin/programmes/create/', {
        ...programmeForm,
        total_credits: parseInt(programmeForm.total_credits),
        max_credits_per_sem: parseInt(programmeForm.max_credits_per_sem),
        probation_credit_cap: parseInt(programmeForm.probation_credit_cap),
        total_semesters: parseInt(programmeForm.total_semesters),
      });
      setShowProgrammeModal(false);
      setSuccess('Programme created successfully!');
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setProgrammeError(err.message);
    }
  };

  if (loading) return <div className="loading-screen">Loading dashboard...</div>;

  return (
    <div>
      <div className="page-header flex-between">
        <div>
          <h1>Admin Dashboard</h1>
          <p>Overview of the Automated Subject Assignment System</p>
        </div>
        <div className="btn-group">
          <button className="btn btn-secondary" onClick={openFacultyModal}>+ Add Faculty</button>
          <button className="btn btn-primary" onClick={openProgrammeModal}>+ Add Programme</button>
        </div>
      </div>

      {success && <div className="alert alert-success">{success}</div>}

      <div className="stats-grid">
        <div className="stat-card sky">
          <div className="stat-label">Total Students</div>
          <div className="stat-value">{stats?.total_students || 0}</div>
        </div>
        <div className="stat-card sky">
          <div className="stat-label">Active Students</div>
          <div className="stat-value">{stats?.active_students || 0}</div>
        </div>
        <div className="stat-card red">
          <div className="stat-label">On Probation</div>
          <div className="stat-value">{stats?.probation_students || 0}</div>
        </div>
        <div className="stat-card sky">
          <div className="stat-label">Total Subjects</div>
          <div className="stat-value">{stats?.total_subjects || 0}</div>
        </div>
        <div className="stat-card red">
          <div className="stat-label">Pending Exceptions</div>
          <div className="stat-value">{stats?.pending_exceptions || 0}</div>
        </div>
        <div className="stat-card red">
          <div className="stat-label">Pending Add/Drop</div>
          <div className="stat-value">{stats?.pending_add_drop || 0}</div>
        </div>
      </div>

      {showFacultyModal && (
        <div className="modal-overlay" onClick={() => setShowFacultyModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Add New Faculty</h3>
              <button className="close-btn" onClick={() => setShowFacultyModal(false)}>&times;</button>
            </div>
            <form onSubmit={handleCreateFaculty}>
              <div className="modal-body">
                {facultyError && <div className="alert alert-error">{facultyError}</div>}
                <div className="form-group">
                  <label>Faculty Code</label>
                  <input className="form-control" value={facultyForm.faculty_code}
                    onChange={(e) => setFacultyForm({ ...facultyForm, faculty_code: e.target.value })}
                    placeholder="e.g. FIT" required />
                </div>
                <div className="form-group">
                  <label>Faculty Name</label>
                  <input className="form-control" value={facultyForm.faculty_name}
                    onChange={(e) => setFacultyForm({ ...facultyForm, faculty_name: e.target.value })}
                    placeholder="e.g. Faculty of Information Technology" required />
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-outline" onClick={() => setShowFacultyModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Create Faculty</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showProgrammeModal && (
        <div className="modal-overlay" onClick={() => setShowProgrammeModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Add New Programme</h3>
              <button className="close-btn" onClick={() => setShowProgrammeModal(false)}>&times;</button>
            </div>
            <form onSubmit={handleCreateProgramme}>
              <div className="modal-body">
                {programmeError && <div className="alert alert-error">{programmeError}</div>}
                {faculties.length === 0 ? (
                  <p className="empty-state">Create a faculty first before adding a programme.</p>
                ) : (
                  <>
                    <div className="form-group">
                      <label>Faculty</label>
                      <select className="form-control" value={programmeForm.faculty_code}
                        onChange={(e) => setProgrammeForm({ ...programmeForm, faculty_code: e.target.value })} required>
                        {faculties.map((f) => (
                          <option key={f.faculty_code} value={f.faculty_code}>
                            {f.faculty_code} - {f.faculty_name}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div className="grid-2">
                      <div className="form-group">
                        <label>Programme Code</label>
                        <input className="form-control" value={programmeForm.programme_code}
                          onChange={(e) => setProgrammeForm({ ...programmeForm, programme_code: e.target.value })}
                          placeholder="e.g. BCSSE" required />
                      </div>
                      <div className="form-group">
                        <label>Programme Name</label>
                        <input className="form-control" value={programmeForm.programme_name}
                          onChange={(e) => setProgrammeForm({ ...programmeForm, programme_name: e.target.value })}
                          placeholder="e.g. Bachelor of Computer Science" required />
                      </div>
                    </div>
                    <div className="grid-2">
                      <div className="form-group">
                        <label>Total Credits</label>
                        <input type="number" min="1" className="form-control" value={programmeForm.total_credits}
                          onChange={(e) => setProgrammeForm({ ...programmeForm, total_credits: e.target.value })} required />
                      </div>
                      <div className="form-group">
                        <label>Total Semesters</label>
                        <input type="number" min="1" className="form-control" value={programmeForm.total_semesters}
                          onChange={(e) => setProgrammeForm({ ...programmeForm, total_semesters: e.target.value })} required />
                      </div>
                    </div>
                    <div className="grid-2">
                      <div className="form-group">
                        <label>Max Credits / Semester</label>
                        <input type="number" min="1" className="form-control" value={programmeForm.max_credits_per_sem}
                          onChange={(e) => setProgrammeForm({ ...programmeForm, max_credits_per_sem: e.target.value })} required />
                      </div>
                      <div className="form-group">
                        <label>Probation Credit Cap</label>
                        <input type="number" min="1" className="form-control" value={programmeForm.probation_credit_cap}
                          onChange={(e) => setProgrammeForm({ ...programmeForm, probation_credit_cap: e.target.value })} required />
                      </div>
                    </div>
                  </>
                )}
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-outline" onClick={() => setShowProgrammeModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={faculties.length === 0}>Create Programme</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
