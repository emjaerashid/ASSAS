import { useState, useEffect } from 'react';
import api from '../../utils/api';
import { useFeedback } from '../../context/FeedbackContext';

const emptyForm = { name: '', capacity: '' };

export default function Venues() {
  const { toast, confirm } = useFeedback();
  const [venues, setVenues] = useState([]);
  const [loading, setLoading] = useState(true);

  const [showModal, setShowModal] = useState(false);
  const [editingName, setEditingName] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState('');

  const fetchVenues = () => {
    setLoading(true);
    api.get('/admin/venues/')
      .then(setVenues)
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(fetchVenues, []);

  const openCreateModal = () => {
    setEditingName(null);
    setForm(emptyForm);
    setError('');
    setShowModal(true);
  };

  const openEditModal = (v) => {
    setEditingName(v.name);
    setForm({ name: v.name, capacity: v.capacity });
    setError('');
    setShowModal(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      if (editingName) {
        await api.put(`/admin/venues/${editingName}/`, { capacity: form.capacity });
        toast.success('Venue updated.');
      } else {
        await api.post('/admin/venues/', form);
        toast.success('Venue created.');
      }
      setShowModal(false);
      fetchVenues();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDelete = async (name) => {
    if (!(await confirm({ title: `Delete venue ${name}?`, message: 'This cannot be undone.', confirmLabel: 'Delete', danger: true }))) return;
    try {
      await api.delete(`/admin/venues/${name}/`);
      fetchVenues();
    } catch (err) {
      toast.error(err.message);
    }
  };

  return (
    <div>
      <div className="page-header flex-between">
        <div>
          <h1>Venues</h1>
          <p>Classrooms, labs, and auditoriums with their maximum student capacity</p>
        </div>
        <button className="btn btn-primary" onClick={openCreateModal}>
          <span className="material-symbols-outlined">add</span>Add Venue
        </button>
      </div>


      <div className="card">
        <div className="table-container">
          {loading ? (
            <div className="loading-screen">Loading venues...</div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Capacity</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {venues.map((v) => (
                  <tr key={v.name}>
                    <td><strong>{v.name}</strong></td>
                    <td>{v.capacity}</td>
                    <td>
                      <div className="btn-group">
                        <button className="btn btn-secondary btn-sm" onClick={() => openEditModal(v)}>
                          Edit
                        </button>
                        <button className="btn btn-danger btn-sm" onClick={() => handleDelete(v.name)}>
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {venues.length === 0 && (
                  <tr><td colSpan="3" className="empty-state">No venues found</td></tr>
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
              <h3>{editingName ? `Edit Venue ${editingName}` : 'Add New Venue'}</h3>
              <button className="close-btn" onClick={() => setShowModal(false)}>&times;</button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="modal-body">
                {error && <div className="alert alert-error">{error}</div>}
                <div className="form-group">
                  <label>Name</label>
                  <input className="form-control" value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    disabled={!!editingName} placeholder="e.g. C101 or Lab 1" required />
                </div>
                <div className="form-group">
                  <label>Capacity</label>
                  <input type="number" min="1" className="form-control" value={form.capacity}
                    onChange={(e) => setForm({ ...form, capacity: e.target.value })} required />
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-outline" onClick={() => setShowModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">
                  {editingName ? 'Save Changes' : 'Create Venue'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
