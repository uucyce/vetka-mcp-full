import { Toaster } from 'sonner';
import { ArtifactPanel } from './components/ArtifactPanel';

function App() {
  // Get initial file from URL query (optional)
  const params = new URLSearchParams(window.location.search);
  const initialFilePath = params.get('file') || undefined;

  // ALWAYS render ArtifactPanel so PostMessage listener is active!
  // Without this, iframe mode (parent sends OPEN_FILE) wouldn't work
  return (
    <>
      <Toaster position="top-right" theme="dark" />
      <div className="h-screen bg-vetka-bg">
        <ArtifactPanel filePath={initialFilePath} />
      </div>
    </>
  );
}

export default App;
