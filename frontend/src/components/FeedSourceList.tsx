import { useState } from "react";
import { ChevronDown, ChevronRight, Plus } from "lucide-react";
import { ScrollArea } from "./ui/scroll-area";
import { Button } from "./ui/button";
import { SourceIcon } from "./SourceIcon";
import { SourceContextMenu } from "./SourceContextMenu";
import { ConfirmDialog } from "./ConfirmDialog";
import { useRSSSources, useDeleteSource } from "../hooks/useQueries";
import { useAppStore } from "../store/useAppStore";
import { useToast } from "../hooks/useToast";
import type { RSSSource } from "../types";

interface FeedSourceListProps {
  onAddSource: () => void;
}

export function FeedSourceList({ onAddSource }: FeedSourceListProps) {
  const { data: sources = [], isLoading } = useRSSSources();
  const { selectedSourceId, setSelectedSourceId } = useAppStore();
  const deleteMutation = useDeleteSource();
  const { toast } = useToast();

  const [expandedCategories, setExpandedCategories] = useState<Record<string, boolean>>({
    "全部": true,
  });
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [sourceToDelete, setSourceToDelete] = useState<RSSSource | null>(null);

  // Get unique categories
  const categories = ["全部", ...Array.from(new Set(sources.map((s) => s.category)))];

  const toggleCategory = (category: string) => {
    setExpandedCategories((prev) => ({
      ...prev,
      [category]: !prev[category],
    }));
  };

  const getSourcesByCategory = (category: string): RSSSource[] => {
    if (category === "全部") return sources;
    return sources.filter((s) => s.category === category);
  };

  const getCategoryUnreadCount = (category: string): number => {
    const categorySources = getSourcesByCategory(category);
    return categorySources.reduce((acc, s) => acc + (s.unread_count || 0), 0);
  };

  const handleDeleteRequest = (source: RSSSource) => {
    setSourceToDelete(source);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!sourceToDelete) return;

    try {
      await deleteMutation.mutateAsync(sourceToDelete.id);

      toast({
        title: "RSS源已删除",
        description: `已成功删除 "${sourceToDelete.title}"`,
        variant: "success",
      });

      // If the deleted source was selected, clear selection
      if (selectedSourceId === sourceToDelete.id) {
        setSelectedSourceId(null);
      }

      setDeleteDialogOpen(false);
      setSourceToDelete(null);
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.message || "删除失败";

      toast({
        title: "删除失败",
        description: errorMessage,
        variant: "error",
      });
    }
  };

  if (isLoading) {
    return (
      <div className="w-full border-r border-border bg-background flex items-center justify-center h-full">
        <p className="text-sm text-muted-foreground">加载中...</p>
      </div>
    );
  }

  return (
    <div className="w-full border-r border-border bg-background flex flex-col h-full overflow-hidden">
      <div className="p-4 border-b border-border flex items-center justify-between flex-shrink-0">
        <h2 className="font-semibold">信息源</h2>
        <Button size="sm" variant="ghost" onClick={onAddSource}>
          <Plus className="w-4 h-4" />
        </Button>
      </div>
      <ScrollArea className="flex-1 h-0">
        <div className="p-2">
          {categories.map((category) => {
            const categorySource = getSourcesByCategory(category);
            const isExpanded = expandedCategories[category] ?? false;
            const unreadCount = getCategoryUnreadCount(category);

            return (
              <div key={category} className="mb-2">
                <button
                  onClick={() => toggleCategory(category)}
                  className="w-full flex items-center gap-2 px-3 py-2 hover:bg-accent rounded-lg transition-colors"
                >
                  {isExpanded ? (
                    <ChevronDown className="w-4 h-4" />
                  ) : (
                    <ChevronRight className="w-4 h-4" />
                  )}
                  <span className="flex-1 text-left text-sm font-medium">{category}</span>
                  {unreadCount > 0 && (
                    <span className="text-muted-foreground text-xs">
                      {unreadCount}
                    </span>
                  )}
                </button>

                {isExpanded && category !== "全部" && (
                  <div className="ml-2 mt-1">
                    {categorySource.map((source) => (
                      <SourceContextMenu
                        key={source.id}
                        source={source}
                        onDelete={handleDeleteRequest}
                      >
                        <button
                          onClick={() => setSelectedSourceId(source.id)}
                          className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg transition-colors text-sm ${
                            selectedSourceId === source.id
                              ? "bg-accent"
                              : "hover:bg-accent/50"
                          }`}
                        >
                          <SourceIcon icon={source.icon} size="sm" />
                          <span className="flex-1 text-left truncate">{source.title}</span>
                          {source.unread_count > 0 && (
                            <span className="text-xs text-muted-foreground">
                              {source.unread_count}
                            </span>
                          )}
                        </button>
                      </SourceContextMenu>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </ScrollArea>

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        title="删除RSS源"
        description={
          sourceToDelete
            ? `确定要删除 "${sourceToDelete.title}" 吗？这将同时删除该源的所有文章。`
            : ""
        }
        confirmText="删除"
        cancelText="取消"
        variant="danger"
        requireCheck={true}
        checkLabel="我了解这将删除所有相关文章"
        onConfirm={handleDeleteConfirm}
        loading={deleteMutation.isPending}
      />
    </div>
  );
}
