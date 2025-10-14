import { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";
import { FeedSourceList } from "./components/FeedSourceList";
import { ArticleList } from "./components/ArticleList";
import { ArticleDetail } from "./components/ArticleDetail";
import { AddSourceDialog } from "./components/AddSourceDialog";
import { Toaster } from "./components/ui/toaster";

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

export default function App() {
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);

  return (
    <QueryClientProvider client={queryClient}>
      <div className="h-screen w-full overflow-hidden">
        <PanelGroup direction="horizontal">
          {/* Feed Source List Panel */}
          <Panel defaultSize={20} minSize={15} maxSize={30} className="overflow-hidden">
            <FeedSourceList onAddSource={() => setIsAddDialogOpen(true)} />
          </Panel>

          <PanelResizeHandle className="w-1 bg-border hover:bg-primary/50 transition-colors cursor-col-resize" />

          {/* Article List Panel */}
          <Panel defaultSize={30} minSize={20} maxSize={50} className="overflow-hidden">
            <ArticleList />
          </Panel>

          <PanelResizeHandle className="w-1 bg-border hover:bg-primary/50 transition-colors cursor-col-resize" />

          {/* Article Detail Panel */}
          <Panel defaultSize={50} minSize={30} className="overflow-hidden">
            <ArticleDetail />
          </Panel>
        </PanelGroup>
      </div>

      <AddSourceDialog
        open={isAddDialogOpen}
        onOpenChange={setIsAddDialogOpen}
      />

      {/* Toast Notifications */}
      <Toaster />
    </QueryClientProvider>
  );
}
