import { useState } from 'react';
import { getMockMode, setMockMode } from '../apiClient';
import type { AppPage } from '../types';
import type { ReactNode } from 'react';

interface LayoutProps {
  activePage: AppPage;
  onPageChange: (page: AppPage) => void;
  children: ReactNode;
}

const navItems: Array<{ page: AppPage; label: string }> = [
  { page: 'dashboard', label: '总览' },
  { page: 'config', label: '配置' },
  { page: 'calibration', label: '校准' },
  { page: 'history', label: '历史' },
];

function Layout({ activePage, onPageChange, children }: LayoutProps) {
  const [isMock, setIsMock] = useState(getMockMode());

  const handleToggleMock = () => {
    const nextValue = !isMock;
    setIsMock(nextValue);
    setMockMode(nextValue);
  };

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">CAR</span>
          <span>小车控制诊断台</span>
        </div>
        <nav className="nav-tabs" aria-label="主导航">
          {navItems.map((item) => (
            <button
              key={item.page}
              type="button"
              className={activePage === item.page ? 'nav-tab active' : 'nav-tab'}
              onClick={() => onPageChange(item.page)}
            >
              {item.label}
            </button>
          ))}
        </nav>
        <button
          type="button"
          className={isMock ? 'mode-switch mock' : 'mode-switch live'}
          onClick={handleToggleMock}
        >
          {isMock ? '模拟数据' : '真实后端'}
        </button>
      </header>
      <main className="page-content">{children}</main>
    </div>
  );
}

export default Layout;
