import { useMemo, useState } from 'react';
import Layout from './components/Layout';
import Calibration from './pages/Calibration';
import ConfigCheck from './pages/ConfigCheck';
import Dashboard from './pages/Dashboard';
import History from './pages/History';
import type { AppPage } from './types';
import './App.css';

function App() {
  const [page, setPage] = useState<AppPage>('dashboard');

  const content = useMemo(() => {
    if (page === 'calibration') {
      return <Calibration />;
    }
    if (page === 'config') {
      return <ConfigCheck />;
    }
    if (page === 'history') {
      return <History />;
    }
    return <Dashboard />;
  }, [page]);

  return (
    <Layout activePage={page} onPageChange={setPage}>
      {content}
    </Layout>
  );
}

export default App;
