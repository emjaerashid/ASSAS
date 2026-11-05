import { Link } from 'react-router-dom';

export default function Home() {
  return (
    <div className="login-page home-page">
      <main className="home-hero">
        <img className="home-crest" src="/cityu-crest.png" alt="City University Malaysia crest" />
        <h1>ASSAS <em>Portal</em></h1>
        <p className="home-desc">Automated Student Subject Allocation System</p>
        <Link className="home-login-btn" to="/login">Login</Link>
      </main>
    </div>
  );
}
