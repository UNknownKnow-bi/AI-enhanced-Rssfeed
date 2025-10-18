import { useEffect, useRef, useMemo, useCallback } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { ArticleCard } from "./ArticleCard";
import { TagFilter } from "./TagFilter";
import { useArticles } from "../hooks/useQueries";
import { useAppStore } from "../store/useAppStore";

export function ArticleList() {
  const { selectedSourceId, selectedCategory, selectedArticleId, selectedTags, selectedView, setSelectedArticleId } = useAppStore();

  // Determine filter parameters based on selectedView
  const isRead = undefined;
  const isFavorite = selectedView === 'favorites' ? true : undefined;
  const isTrashed = selectedView === 'trash' ? true : undefined;

  const {
    data,
    isLoading,
    isFetchingNextPage,
    hasNextPage,
    fetchNextPage
  } = useArticles(
    selectedSourceId || undefined,
    selectedCategory || undefined,
    selectedTags.length > 0 ? selectedTags : undefined,
    isRead,
    isFavorite,
    isTrashed
  );

  // Memoize flattened paginated data to avoid recreating array on every render
  const articles = useMemo(() => data?.pages.flat() ?? [], [data?.pages]);

  // Ref for the scrollable container
  const parentRef = useRef<HTMLDivElement>(null);

  // Virtual scrolling configuration
  const virtualizer = useVirtualizer({
    count: articles.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 120, // Estimated height of each article card
    overscan: 5, // Render 5 extra items outside viewport for smooth scrolling
  });

  // Memoize onClick handler to prevent recreation on every render
  const handleArticleClick = useCallback(
    (articleId: string) => {
      setSelectedArticleId(articleId);
    },
    [setSelectedArticleId]
  );

  // Intersection Observer for infinite scroll (trigger when near bottom)
  const observerTarget = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasNextPage && !isFetchingNextPage) {
          fetchNextPage();
        }
      },
      { threshold: 1.0 }
    );

    const currentTarget = observerTarget.current;
    if (currentTarget) {
      observer.observe(currentTarget);
    }

    return () => {
      if (currentTarget) {
        observer.unobserve(currentTarget);
      }
    };
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

  if (isLoading) {
    return (
      <div className="w-full flex h-full">
        <TagFilter />
        <div className="flex-1 border-r border-border bg-background flex items-center justify-center">
          <p className="text-sm text-muted-foreground">加载中...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full flex h-full">
      {/* Tag Filter - Left Sidebar */}
      <TagFilter />

      {/* Article List - Main Content */}
      <div className="flex-1 border-r border-border bg-background flex flex-col h-full overflow-hidden">
        <div className="p-4 border-b border-border flex-shrink-0">
          <h2 className="font-semibold">文章列表</h2>
          <p className="text-sm text-muted-foreground mt-1">
            共 {articles.length} 篇文章
            {selectedTags.length > 0 && ` (已过滤 ${selectedTags.length} 个标签)`}
          </p>
        </div>

        {/* Virtual Scrolling Container */}
        <div ref={parentRef} className="flex-1 overflow-auto">
          {articles.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground">
              <p>暂无文章</p>
              <p className="text-xs mt-2">
                {selectedTags.length > 0 ? '尝试调整标签过滤条件' : '添加RSS源后，文章将自动同步'}
              </p>
            </div>
          ) : (
            <div
              style={{
                height: `${virtualizer.getTotalSize()}px`,
                width: '100%',
                position: 'relative',
              }}
            >
              {virtualizer.getVirtualItems().map((virtualItem) => {
                const article = articles[virtualItem.index];
                return (
                  <div
                    key={article.id}
                    style={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      width: '100%',
                      transform: `translateY(${virtualItem.start}px)`,
                    }}
                  >
                    <ArticleCard
                      article={article}
                      isSelected={selectedArticleId === article.id}
                      onClick={() => handleArticleClick(article.id)}
                    />
                  </div>
                );
              })}

              {/* Intersection Observer Target for infinite scroll */}
              <div
                ref={observerTarget}
                style={{
                  position: 'absolute',
                  bottom: '200px',
                  height: '1px',
                  width: '100%',
                }}
              />

              {/* Loading indicator */}
              {isFetchingNextPage && (
                <div className="p-4 text-center">
                  <p className="text-sm text-muted-foreground">加载更多...</p>
                </div>
              )}

              {/* End of list indicator */}
              {!hasNextPage && articles.length > 0 && (
                <div className="p-4 text-center">
                  <p className="text-xs text-muted-foreground">已加载全部文章</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
