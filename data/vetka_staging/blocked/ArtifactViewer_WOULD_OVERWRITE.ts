```diff
--- a/client/src/components/artifact/ArtifactViewer.tsx
+++ b/client/src/components/artifact/ArtifactViewer.tsx
@@ -1,4 +1,4 @@
-import { useState } from 'react';
+import { useState, useEffect } from 'react';
 import { Loader2, Check, X, AlertCircle } from 'lucide-react';
 import { CodeViewer } from './viewers/CodeViewer';
 import { MarkdownViewer } from './viewers/MarkdownViewer';
@@ -12,6 +12,16 @@ interface ArtifactViewerProps {
 export function ArtifactViewer({ artifact, onApprove, onReject }: ArtifactViewerProps) {
   const [loading, setLoading] = useState(false);
   const [error, setError] = useState<string | null>(null);
+  const [isLoadingSkeleton, setIsLoadingSkeleton] = useState(true);
+
+  // Simulate initial loading state for skeleton
+  useEffect(() => {
+    const timer = setTimeout(() => {
+      setIsLoadingSkeleton(false);
+    }, 300);
+    
+    return () => clearTimeout(timer);
+  }, []);
 
   const handleApprove = async () => {
     setLoading(true);
@@ -44,11 +54,25 @@ export function ArtifactViewer({ artifact, onApprove, onReject }: ArtifactViewer
   };
 
   const renderArtifactContent = () => {
+    // Loading skeleton for initial render
+    if (isLoadingSkeleton) {
+      return (
+        <div style={{ padding: '16px' }}>
+          <div style={{ height: '20px', backgroundColor: '#333', borderRadius: '4px', marginBottom: '12px', width: '80%' }} />
+          <div style={{ height: '20px', backgroundColor: '#333', borderRadius: '4px', marginBottom: '12px', width: '60%' }} />
+          <div style={{ height: '20px', backgroundColor: '#333', borderRadius: '4px', marginBottom: '12px', width: '90%' }} />
+          <div style={{ height: '20px', backgroundColor: '#333', borderRadius: '4px', marginBottom: '12px', width: '70%' }} />
+        </div>
+      );
+    }
+
     switch (artifact.type) {
       case 'code':
-        return <CodeViewer content={artifact.content} language="javascript" />;
+        return artifact.content ? <CodeViewer content={artifact.content} language="javascript" /> : null;
       case 'markdown':
-        return <MarkdownViewer content={artifact.content} />;
+        return artifact.content ? <MarkdownViewer content={artifact.content} /> : null;
       case 'image':
         return <ImageViewer src={artifact.content} alt="Artifact image" />;
       default:
@@ -72,6 +96,15 @@ export function ArtifactViewer({ artifact, onApprove, onReject }: ArtifactViewer
         );
       case 'error':
         return (
+          <div style={{ 
+            display: 'flex', 
+            alignItems: 'center', 
+            gap: '8px', 
+            color: '#ef4444',
+            padding: '4px 8px',
+            backgroundColor: 'rgba(239, 68, 68, 0.1)',
+            borderRadius: '4px'
+          }}>
+            <AlertCircle size={16} />
+            Error loading artifact
+          </div>
+        );
+      case 'loading':
+        return (
+          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#666' }}>
+            <Loader2 size={16} className="animate-spin" />
+            Loading...
+          </div>
+        );
+      default:
+        return null;
+    }
+  };
+
+  const renderStatus = () => {
+    // Error boundary UI for critical errors
+    if (artifact.status === 'error' && error) {
+      return (
+        <div style={{ 
+          display: 'flex', 
+          alignItems: 'center', 
+          gap: '8px', 
+          color: '#ef4444',
+          padding: '8px 12px',
+          backgroundColor: 'rgba(239, 68, 68, 0.1)',
+          borderRadius: '4px'
+        }}>
+          <AlertCircle size={16} />
+          Error: {error}
+        </div>
+      );
+    }
+
+    if (loading) {
+      return (
+        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#666' }}>
+          <Loader2 size={16} className="animate-spin" />
+          Processing...
+        </div>
+      );
+    }
+
+    if (error) {
+      return (
+        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#ef4444' }}>
+          <AlertCircle size={16} />
+          {error}
+        </div>
+      );
+    }
+
+    switch (artifact.status) {
+      case 'approved':
+        return (
+          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#10b981' }}>
+            <Check size={16} />
+            Approved
+          </div>
+        );
+      case 'rejected':
+        return (
+          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#ef4444' }}>
+            <X size={16} />
+            Rejected
+          </div>
+        );
+      case 'error':
         return (
           <div style={{ 
             display: 'flex', 
@@ -105,6 +187,20 @@ export function ArtifactViewer({ artifact, onApprove, onReject }: ArtifactViewer
             justifyContent: 'center'
           }}>
             <Loader2 size={32} className="animate-spin" style={{ color: '#666' }} />
+          </div>
+        ) : artifact.status === 'error' ? (
+          <div style={{
+            height: '200px',
+            display: 'flex',
+            flexDirection: 'column',
+            alignItems: 'center',
+            justifyContent: 'center',
+            gap: '8px',
+            color: '#999'
+          }}>
+            <AlertCircle size={32} style={{ color: '#ef4444' }} />
+            <div>Failed to load artifact</div>
+            {error && <div style={{ fontSize: '14px', color: '#ef4444' }}>{error}</div>}
           </div>
         ) : (
           renderArtifactContent()
```