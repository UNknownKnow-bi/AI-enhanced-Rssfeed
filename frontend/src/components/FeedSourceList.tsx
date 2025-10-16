import { useState } from "react";
import { ChevronDown, ChevronRight, Plus } from "lucide-react";
import { ScrollArea } from "./ui/scroll-area";
import { Button } from "./ui/button";
import { SourceIcon } from "./SourceIcon";
import { SourceContextMenu } from "./SourceContextMenu";
import { CategoryContextMenu } from "./CategoryContextMenu";
import { ConfirmDialog } from "./ConfirmDialog";
import { RenameSourceDialog } from "./RenameSourceDialog";
import { RenameCategoryDialog } from "./RenameCategoryDialog";
import { EditIconDialog } from "./EditIconDialog";
import { useRSSSources, useDeleteSource } from "../hooks/useQueries";
import { useAppStore } from "../store/useAppStore";
import { useToast } from "../hooks/useToast";
import type { RSSSource } from "../types";

interface FeedSourceListProps {
  onAddSource: () => void;
}

export function FeedSourceList({ onAddSource }: FeedSourceListProps) {
  const { data: sources = [], isLoading } = useRSSSources();
  const { selectedSourceId, selectedCategory, setSelectedSourceId, setSelectedCategory } = useAppStore();
  const deleteMutation = useDeleteSource();
  const { toast } = useToast();

  const [expandedCategories, setExpandedCategories] = useState<Record<string, boolean>>({
    "全部": true,
  });
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [renameDialogOpen, setRenameDialogOpen] = useState(false);
  const [editIconDialogOpen, setEditIconDialogOpen] = useState(false);
  const [renameCategoryDialogOpen, setRenameCategoryDialogOpen] = useState(false);
  const [sourceToDelete, setSourceToDelete] = useState<RSSSource | null>(null);
  const [activeSource, setActiveSource] = useState<RSSSource | null>(null);
  const [categoryToRename, setCategoryToRename] = useState<string | null>(null);

  // Get unique categories (exclude "全部" from regular categories)
  const realCategories = Array.from(new Set(sources.map((s) => s.category)));

  const toggleCategory = (category: string) => {
    setExpandedCategories((prev) => ({
      ...prev,
      [category]: !prev[category],
    }));
  };

  const handleSelectCategory = (category: string) => {
    // Only select category, do NOT toggle expansion
    // null for "全部" means show all articles
    setSelectedCategory(category === "全部" ? null : category);
  };

  const getSourcesByCategory = (category: string): RSSSource[] => {
    if (category === "全部") return sources;
    return sources.filter((s) => s.category === category);
  };

  const getCategoryUnreadCount = (category: string): number => {
    const categorySources = getSourcesByCategory(category);
    return categorySources.reduce((acc, s) => acc + (s.unread_count || 0), 0);
  };

  const handleCopyLink = async (source: RSSSource) => {
    try {
      await navigator.clipboard.writeText(source.url);
      toast({
        title: "已复制",
        description: "RSS订阅链接已复制到剪贴板",
        variant: "success",
      });
    } catch (error) {
      toast({
        title: "复制失败",
        description: "无法访问剪贴板",
        variant: "error",
      });
    }
  };

  const handleRenameRequest = (source: RSSSource) => {
    setActiveSource(source);
    setRenameDialogOpen(true);
  };

  const handleEditIconRequest = (source: RSSSource) => {
    setActiveSource(source);
    setEditIconDialogOpen(true);
  };

  const handleDeleteRequest = (source: RSSSource) => {
    setSourceToDelete(source);
    setDeleteDialogOpen(true);
  };

  const handleRenameCategoryRequest = (category: string) => {
    setCategoryToRename(category);
    setRenameCategoryDialogOpen(true);
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
        <div className="flex items-center gap-2">
          <img src="/src/assets/logo.png" alt="logo" className="w-10 h-8.5 rounded-sm" />
          <h2 className="font-semibold">信息源</h2>
        </div>
        <Button size="sm" variant="ghost" onClick={onAddSource}>
          <Plus className="w-4 h-4" />
        </Button>
      </div>
      <ScrollArea className="flex-1 h-0">
        <div className="p-2">
          {/* Level 1: "全部" as top-level parent */}
          <div className="mb-2">
            <button
              onClick={() => handleSelectCategory("全部")}
              className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
                selectedCategory === null && selectedSourceId === null
                  ? "bg-accent"
                  : "hover:bg-accent/50"
              }`}
            >
              {/* Chevron with separate click handler for fold/expand only */}
              <div
                onClick={(e) => {
                  e.stopPropagation(); // Prevent selection when clicking chevron
                  toggleCategory("全部");
                }}
                className="flex items-center cursor-pointer"
              >
                {expandedCategories["全部"] ? (
                  <ChevronDown className="w-4 h-4" />
                ) : (
                  <ChevronRight className="w-4 h-4" />
                )}
              </div>
              <span className="flex-1 text-left text-sm font-medium">全部</span>
              {getCategoryUnreadCount("全部") > 0 && (
                <span className="text-muted-foreground text-xs">
                  {getCategoryUnreadCount("全部")}
                </span>
              )}
            </button>

            {/* Level 2: Categories nested under "全部" */}
            {expandedCategories["全部"] && (
              <div className="ml-4 mt-1">
                {realCategories.map((category) => {
                  const categorySource = getSourcesByCategory(category);
                  const isExpanded = expandedCategories[category] ?? false;
                  const unreadCount = getCategoryUnreadCount(category);

                  return (
                    <div key={category} className="mb-1">
                      <CategoryContextMenu
                        category={category}
                        onRename={handleRenameCategoryRequest}
                      >
                        <button
                          onClick={() => handleSelectCategory(category)}
                          className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
                            selectedCategory === category
                              ? "bg-accent"
                              : "hover:bg-accent/50"
                          }`}
                        >
                          {/* Chevron with separate click handler for fold/expand only */}
                          <div
                            onClick={(e) => {
                              e.stopPropagation(); // Prevent selection when clicking chevron
                              toggleCategory(category);
                            }}
                            className="flex items-center cursor-pointer"
                          >
                            {isExpanded ? (
                              <ChevronDown className="w-4 h-4" />
                            ) : (
                              <ChevronRight className="w-4 h-4" />
                            )}
                          </div>
                          <span className="flex-1 text-left text-sm font-medium">{category}</span>
                          {unreadCount > 0 && (
                            <span className="text-muted-foreground text-xs">
                              {unreadCount}
                            </span>
                          )}
                        </button>
                      </CategoryContextMenu>

                      {/* Level 3: Sources nested under each category */}
                      {isExpanded && (
                        <div className="ml-4 mt-1">
                          {categorySource.map((source) => (
                            <SourceContextMenu
                              key={source.id}
                              source={source}
                              onDelete={handleDeleteRequest}
                              onRename={handleRenameRequest}
                              onEditIcon={handleEditIconRequest}
                              onCopyLink={handleCopyLink}
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
            )}
          </div>
        </div>
      </ScrollArea>

      {/* Rename Dialog */}
      <RenameSourceDialog
        open={renameDialogOpen}
        onOpenChange={setRenameDialogOpen}
        source={activeSource}
      />

      {/* Edit Icon Dialog */}
      <EditIconDialog
        open={editIconDialogOpen}
        onOpenChange={setEditIconDialogOpen}
        source={activeSource}
      />

      {/* Rename Category Dialog */}
      <RenameCategoryDialog
        open={renameCategoryDialogOpen}
        onOpenChange={setRenameCategoryDialogOpen}
        category={categoryToRename}
        sources={sources}
      />

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
