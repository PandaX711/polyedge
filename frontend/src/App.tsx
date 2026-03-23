import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Markets from './pages/Markets';
import Signals from './pages/Signals';
import Analysis from './pages/Analysis';
import WorldCup from './pages/WorldCup';

function Nav() {
  const link = 'px-4 py-2 rounded-lg text-sm font-medium transition-colors';
  const active = 'bg-indigo-600 text-white';
  const inactive = 'text-gray-400 hover:text-white hover:bg-gray-800';
  return (
    <nav className="bg-gray-900 border-b border-gray-800 px-6 py-3 flex items-center gap-2">
      <span className="text-indigo-400 font-bold text-lg mr-6">PolyEdge</span>
      {[
        ['/', 'Dashboard'],
        ['/worldcup', 'World Cup'],
        ['/markets', 'Markets'],
        ['/signals', 'Signals'],
        ['/analysis', 'AI Analysis'],
      ].map(([to, label]) => (
        <NavLink
          key={to}
          to={to}
          end={to === '/'}
          className={({ isActive }) => `${link} ${isActive ? active : inactive}`}
        >
          {label}
        </NavLink>
      ))}
    </nav>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-950 text-gray-100">
        <Nav />
        <main className="max-w-7xl mx-auto px-6 py-6">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/worldcup" element={<WorldCup />} />
            <Route path="/markets" element={<Markets />} />
            <Route path="/signals" element={<Signals />} />
            <Route path="/analysis" element={<Analysis />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
