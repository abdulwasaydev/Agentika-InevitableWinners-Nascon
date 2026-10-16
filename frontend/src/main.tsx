import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { WorkspaceProvider } from './Workspace';
import { AppRoutes } from './App';
import './styles.css';
createRoot(document.getElementById('root')!).render(<StrictMode><BrowserRouter><WorkspaceProvider><AppRoutes /></WorkspaceProvider></BrowserRouter></StrictMode>);
