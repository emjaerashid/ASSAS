import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Login() {
  const [studentId, setStudentId] = useState('');
  const [icPassport, setIcPassport] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const user = await login(studentId, icPassport);
      navigate(user.role === 'admin' ? '/admin' : '/student');
    } catch (err) {
      setError(err.message || 'Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-header">
          <h1>ASSAS</h1>
          <p>Automated Subject Assignment System</p>
        </div>
        <form className="login-body" onSubmit={handleSubmit}>
          {error && <div className="login-error">{error}</div>}
          <div className="form-group">
            <label>Student ID / Admin ID</label>
            <input
              type="text"
              className="form-control"
              value={studentId}
              onChange={(e) => setStudentId(e.target.value)}
              placeholder="e.g. 202209020002"
              required
            />
          </div>
          <div className="form-group">
            <label>IC / Passport Number</label>
            <input
              type="password"
              className="form-control"
              value={icPassport}
              onChange={(e) => setIcPassport(e.target.value)}
              placeholder="Enter your IC or Passport number"
              required
            />
          </div>
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
        <div className="login-footer">
          City University Malaysia &middot; Faculty of Information Technology
        </div>
      </div>
    </div>
  );
}
