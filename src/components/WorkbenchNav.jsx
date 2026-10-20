import { Clapperboard, Scissors, Captions, NotebookPen, FileJson2 } from 'lucide-react';
import './workbench-nav.css';

// Native anchors deliberately keep editing sections usable without JavaScript
// navigation state. Both desktop and GitHub Pages share the same section ids.
const sections = [
  { id: 'studio-video', label: 'Vídeo', icon: Clapperboard },
  { id: 'studio-cuts', label: 'Cortes', icon: Scissors },
  { id: 'studio-captions', label: 'Legendas', icon: Captions },
  { id: 'studio-script', label: 'Roteiro', icon: NotebookPen },
  { id: 'studio-project', label: 'Projeto', icon: FileJson2 },
];

export default function WorkbenchNav({ compact = false, onNavigate }) {
  return (
    <nav className={'workbench-nav' + (compact ? ' workbench-nav-compact' : '')} aria-label="Ir para uma etapa do editor">
      <span className="workbench-nav-heading">IR PARA</span>
      <div className="workbench-nav-links">
        {sections.map(({ id, label, icon: Icon }, index) => (
          <a key={id} href={'#' + id} className="workbench-nav-link" onClick={() => onNavigate?.(id)}>
            <span className="workbench-nav-index" aria-hidden="true">{String(index+1).padStart(2, '0')}</span>
            <Icon size={15} aria-hidden="true" />
            <span>{label}</span>
          </a>
        ))}
      </div>
    </nav>
  );
}
