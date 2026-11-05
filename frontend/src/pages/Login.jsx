import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

function EyeIcon({ off }) {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round">
      {off ? (
        <>
          <path d="M17.94 17.94A10.94 10.94 0 0 1 12 20c-7 0-11-8-11-8a18.5 18.5 0 0 1 5.06-5.94M9.9 4.24A10.94 10.94 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
          <line x1="1" y1="1" x2="23" y2="23" />
        </>
      ) : (
        <>
          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
          <circle cx="12" cy="12" r="3" />
        </>
      )}
    </svg>
  );
}

const REMEMBER_KEY = 'assas.rememberedId';

function readRememberedId() {
  try { return localStorage.getItem(REMEMBER_KEY) || ''; } catch { return ''; }
}

export default function Login() {
  const rememberedId = readRememberedId();
  const [studentId, setStudentId] = useState(rememberedId);
  const [icPassport, setIcPassport] = useState('');
  const [remember, setRemember] = useState(!!rememberedId);
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const user = await login(studentId.trim(), icPassport.trim());
      try {
        if (remember) localStorage.setItem(REMEMBER_KEY, studentId.trim());
        else localStorage.removeItem(REMEMBER_KEY);
      } catch { /* storage unavailable */ }
      navigate(user.role === 'admin' ? '/admin' : '/student');
    } catch (err) {
      setError(err.message || 'Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <nav className="login-nav">
        <div className="login-nav-links">
          <a className="login-nav-link" href="https://student.city.edu.my/sp-dev/" target="_blank" rel="noopener noreferrer">
            Student Portal
          </a>
        </div>
      </nav>

      <section className="login-hero">
        <div className="login-hero-copy">
          <div className="login-hero-title">
            <img className="login-hero-crest" src="/cityu-crest.png" alt="City University Malaysia crest" />
            <h1>ASSAS <em>Portal</em></h1>
          </div>
          <p className="login-hero-desc">Automated Student Subject Allocation System</p>
        </div>

        <form className="login-card" onSubmit={handleSubmit}>
          <h2>Welcome back</h2>
          <p className="login-card-sub">Sign in with your university ID to continue.</p>
          {error && (
            <div className="login-error" key={error}>
              <span className="material-symbols-outlined">error</span>{error}
            </div>
          )}
          <div className="form-group">
            <label htmlFor="login-id">Student ID / Admin ID</label>
            <div className="login-input-wrap">
              <span className="material-symbols-outlined">badge</span>
              <input
                id="login-id"
                type="text"
                className="form-control"
                value={studentId}
                onChange={(e) => setStudentId(e.target.value)}
                placeholder="e.g. 202209020002"
                autoComplete="username"
                autoFocus={!rememberedId}
                required
              />
            </div>
          </div>
          <div className="form-group">
            <label htmlFor="login-ic">IC / Passport Number</label>
            <div className="login-input-wrap">
              <span className="material-symbols-outlined">lock</span>
              <input
                id="login-ic"
                type={showPassword ? 'text' : 'password'}
                className="form-control"
                style={{ paddingRight: '44px' }}
                value={icPassport}
                onChange={(e) => setIcPassport(e.target.value)}
                placeholder="Enter your IC or Passport number"
                autoComplete="current-password"
                autoFocus={!!rememberedId}
                required
              />
              <button
                type="button"
                className="login-eye"
                onClick={() => setShowPassword((v) => !v)}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                <EyeIcon off={showPassword} />
              </button>
            </div>
          </div>
          <label className="login-remember">
            <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} />
            Remember my ID on this device
          </label>
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? <><span className="spinner" />Signing in...</> : <>Sign In<span className="material-symbols-outlined">arrow_forward</span></>}
          </button>
          <div className="login-footer">
            Trouble signing in? Contact the Faculty of Information Technology office.
          </div>
        </form>
      </section>

      <div className="login-copyright">&copy; {new Date().getFullYear()} City University Malaysia &middot; ASSAS</div>
    </div>
  );
}
