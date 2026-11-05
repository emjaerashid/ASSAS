import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../../utils/api';
import { useFeedback } from '../../context/FeedbackContext';

const emptyFacultyForm = { faculty_code: '', faculty_name: '' };
const emptyProgrammeForm = {
  programme_code: '', programme_name: '', faculty_code: '',
  total_credits: 120, max_credits_per_sem: 21, probation_credit_cap: 12, total_semesters: 9,
};

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [faculties, setFaculties] = useState([]);
  const [programmes, setProgrammes] = useState([]);

  const [showFacultyModal, setShowFacultyModal] = useState(false);
  const [facultyForm, setFacultyForm] = useState(emptyFacultyForm);
  const [facultyError, setFacultyError] = useState('');
  const [editingFacultyCode, setEditingFacultyCode] = useState(null);

  const [showProgrammeModal, setShowProgrammeModal] = useState(false);
  const [programmeForm, setProgrammeForm] = useState(emptyProgrammeForm);
  const [programmeError, setProgrammeError] = useState('');
  const [editingProgrammeCode, setEditingProgrammeCode] = useState(null);

  const { toast, confirm } = useFeedback();

  const fetchFaculties = () => {
    api.get('/admin/faculties/').then(setFaculties).catch(console.error);
  };

  const fetchProgrammes = () => {
    api.get('/programmes/').then(setProgrammes).catch(console.error);
  };

  const handleDeleteFaculty = async (facultyCode) => {
    const ok = await confirm({
      title: `Delete faculty ${facultyCode}?`,
      message: 'This cannot be undone.',
      confirmLabel: 'Delete faculty',
      danger: true,
    });
    if (!ok) return;
    try {
      await api.delete(`/admin/faculties/${facultyCode}/`);
      toast.success(`Faculty ${facultyCode} deleted.`);
      fetchFaculties();
    } catch (err) {
      toast.error(err.message);
    }
  };

  const handleDeleteProgramme = async (programmeCode) => {
    const ok = await confirm({
      title: `Delete programme ${programmeCode}?`,
      message: 'This cannot be undone.',
      confirmLabel: 'Delete programme',
      danger: true,
    });
    if (!ok) return;
    try {
      await api.delete(`/admin/programmes/${programmeCode}/`);
      toast.success(`Programme ${programmeCode} deleted.`);
      fetchProgrammes();
    } catch (err) {
      toast.error(err.message);
    }
  };

  useEffect(() => {
    api.get('/admin/dashboard/')
      .then(setStats)
      .catch(console.error)
      .finally(() => setLoading(false));
    fetchFaculties();
    fetchProgrammes();
  }, []);

  const openFacultyModal = () => {
    setFacultyForm(emptyFacultyForm);
    setEditingFacultyCode(null);
    setFacultyError('');
    setShowFacultyModal(true);
  };

  const openEditFacultyModal = (f) => {
    setFacultyForm({ faculty_code: f.faculty_code, faculty_name: f.faculty_name });
    setEditingFacultyCode(f.faculty_code);
    setFacultyError('');
    setShowFacultyModal(true);
  };

  const openProgrammeModal = () => {
    setProgrammeForm({ ...emptyProgrammeForm, faculty_code: faculties[0]?.faculty_code || '' });
    setEditingProgrammeCode(null);
    setProgrammeError('');
    setShowProgrammeModal(true);
  };

  const openEditProgrammeModal = (p) => {
    setProgrammeForm({
      programme_code: p.programme_code,
      programme_name: p.programme_name,
      faculty_code: p.faculty,
      total_credits: p.total_credits,
      max_credits_per_sem: p.max_credits_per_sem,
      probation_credit_cap: p.probation_credit_cap,
      total_semesters: p.total_semesters,
    });
    setEditingProgrammeCode(p.programme_code);
    setProgrammeError('');
    setShowProgrammeModal(true);
  };

  const handleSubmitFaculty = async (e) => {
    e.preventDefault();
    setFacultyError('');
    try {
      if (editingFacultyCode) {
        await api.put(`/admin/faculties/${editingFacultyCode}/`, { faculty_name: facultyForm.faculty_name });
        toast.success('Faculty updated.');
      } else {
        await api.post('/admin/faculties/', facultyForm);
        toast.success('Faculty created.');
      }
      setShowFacultyModal(false);
      fetchFaculties();
    } catch (err) {
      setFacultyError(err.message);
    }
  };

  const handleSubmitProgramme = async (e) => {
    e.preventDefault();
    setProgrammeError('');
    try {
      const payload = {
        ...programmeForm,
        total_credits: parseInt(programmeForm.total_credits),
        max_credits_per_sem: parseInt(programmeForm.max_credits_per_sem),
        probation_credit_cap: parseInt(programmeForm.probation_credit_cap),
        total_semesters: parseInt(programmeForm.total_semesters),
      };
      if (editingProgrammeCode) {
        await api.put(`/admin/programmes/${editingProgrammeCode}/`, payload);
        toast.success('Programme updated.');
      } else {
        await api.post('/admin/programmes/create/', payload);
        toast.success('Programme created.');
      }
      setShowProgrammeModal(false);
      fetchProgrammes();
    } catch (err) {
      setProgrammeError(err.message);
    }
  };

  if (loading) return <div className="loading-screen">Loading dashboard...</div>;

  const pendingTotal = (stats?.pending_exceptions || 0) + (stats?.pending_add_drop || 0);

  const statCards = [
    { label: 'Total Students', value: stats?.total_students || 0, icon: 'group', variant: 'sky', to: '/admin/students' },
    { label: 'Active Students', value: stats?.active_students || 0, icon: 'how_to_reg', variant: 'green', to: '/admin/students' },
    { label: 'On Probation', value: stats?.probation_students || 0, icon: 'warning', variant: 'amber', to: '/admin/students' },
    { label: 'Total Subjects', value: stats?.total_subjects || 0, icon: 'menu_book', variant: 'sky', to: '/admin/subjects' },
    { label: 'Pending Exceptions', value: stats?.pending_exceptions || 0, icon: 'flag', variant: 'red', to: '/admin/exceptions' },
    { label: 'Pending Add/Drop', value: stats?.pending_add_drop || 0, icon: 'swap_horiz', variant: 'red', to: '/admin/add-drop' },
  ];

  return (
    <div>
      <div className="page-header flex-between">
        <div>
          <h1>Admin Dashboard</h1>
          <p>Overview of the Automated Subject Allocation System</p>
        </div>
        <div className="btn-group">
          <button className="btn btn-secondary" onClick={openFacultyModal}>
            <span className="material-symbols-outlined">add</span>Add Faculty
          </button>
          <button className="btn btn-primary" onClick={openProgrammeModal}>
            <span className="material-symbols-outlined">add</span>Add Programme
          </button>
        </div>
      </div>

      {pendingTotal > 0 && (
        <div className="attention">
          <span className="material-symbols-outlined">notification_important</span>
          <div className="attention-text">
            <strong>{pendingTotal} item{pendingTotal === 1 ? '' : 's'} awaiting review</strong>
            {' · '}{stats.pending_exceptions} exception{stats.pending_exceptions === 1 ? '' : 's'},
            {' '}{stats.pending_add_drop} add/drop request{stats.pending_add_drop === 1 ? '' : 's'}
          </div>
          <div className="btn-group">
            {stats.pending_exceptions > 0 && (
              <Link className="btn btn-secondary btn-sm" to="/admin/exceptions">Review exceptions</Link>
            )}
            {stats.pending_add_drop > 0 && (
              <Link className="btn btn-secondary btn-sm" to="/admin/add-drop">Review requests</Link>
            )}
          </div>
        </div>
      )}

      <div className="stats-grid">
        {statCards.map((c) => (
          <Link to={c.to} className={`stat-card ${c.variant}`} key={c.label}>
            <div className="stat-card-head">
              <div className="stat-label">{c.label}</div>
              <div className={`stat-icon ${c.variant}`}>
                <span className="material-symbols-outlined">{c.icon}</span>
              </div>
            </div>
            <div className="stat-value-row">
              <div className="stat-value">{c.value}</div>
            </div>
          </Link>
        ))}
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-header"><h3>Faculties</h3></div>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Name</th>
                  <th>Programmes</th>
                  <th style={{ width: '1%' }}></th>
                </tr>
              </thead>
              <tbody>
                {faculties.map((f) => (
                  <tr key={f.faculty_code}>
                    <td><strong>{f.faculty_code}</strong></td>
                    <td>{f.faculty_name}</td>
                    <td>{programmes.filter((p) => p.faculty === f.faculty_code).length}</td>
                    <td>
                      <div className="btn-group">
                        <button className="icon-btn" title="Edit faculty" aria-label="Edit faculty" onClick={() => openEditFacultyModal(f)}>
                          <span className="material-symbols-outlined">edit</span>
                        </button>
                        <button className="icon-btn" title="Delete faculty" aria-label="Delete faculty" onClick={() => handleDeleteFaculty(f.faculty_code)}>
                          <span className="material-symbols-outlined">delete</span>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {faculties.length === 0 && (
                  <tr><td colSpan="4" className="empty-state">No faculties yet</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="card">
          <div className="card-header"><h3>Programmes</h3></div>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Name</th>
                  <th>Faculty</th>
                  <th>Semesters</th>
                  <th style={{ width: '1%' }}></th>
                </tr>
              </thead>
              <tbody>
                {programmes.map((p) => (
                  <tr key={p.programme_code}>
                    <td><strong>{p.programme_code}</strong></td>
                    <td>{p.programme_name}</td>
                    <td>{p.faculty_name || p.faculty || '—'}</td>
                    <td>{p.total_semesters}</td>
                    <td>
                      <div className="btn-group">
                        <button className="icon-btn" title="Edit programme" aria-label="Edit programme" onClick={() => openEditProgrammeModal(p)}>
                          <span className="material-symbols-outlined">edit</span>
                        </button>
                        <button className="icon-btn" title="Delete programme" aria-label="Delete programme" onClick={() => handleDeleteProgramme(p.programme_code)}>
                          <span className="material-symbols-outlined">delete</span>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {programmes.length === 0 && (
                  <tr><td colSpan="5" className="empty-state">No programmes yet</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {showFacultyModal && (
        <div className="modal-overlay" onClick={() => setShowFacultyModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{editingFacultyCode ? `Edit Faculty ${editingFacultyCode}` : 'Add New Faculty'}</h3>
              <button className="close-btn" onClick={() => setShowFacultyModal(false)}>&times;</button>
            </div>
            <form onSubmit={handleSubmitFaculty}>
              <div className="modal-body">
                {facultyError && <div className="alert alert-error">{facultyError}</div>}
                <div className="form-group">
                  <label>Faculty Code</label>
                  <input className="form-control" value={facultyForm.faculty_code}
                    onChange={(e) => setFacultyForm({ ...facultyForm, faculty_code: e.target.value })}
                    placeholder="e.g. FIT" disabled={!!editingFacultyCode} required />
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
                <button type="submit" className="btn btn-primary">{editingFacultyCode ? 'Save Changes' : 'Create Faculty'}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showProgrammeModal && (
        <div className="modal-overlay" onClick={() => setShowProgrammeModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{editingProgrammeCode ? `Edit Programme ${editingProgrammeCode}` : 'Add New Programme'}</h3>
              <button className="close-btn" onClick={() => setShowProgrammeModal(false)}>&times;</button>
            </div>
            <form onSubmit={handleSubmitProgramme}>
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
                          placeholder="e.g. BCSSE" disabled={!!editingProgrammeCode} required />
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
                <button type="submit" className="btn btn-primary" disabled={faculties.length === 0}>
                  {editingProgrammeCode ? 'Save Changes' : 'Create Programme'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
