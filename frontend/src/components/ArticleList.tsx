import { useEffect, useRef } from "react";
import { ArticleCard } from "./ArticleCard";
import { TagFilter } from "./TagFilter";
import { ScrollArea } from "./ui/scroll-area";
import { useArticles } from "../hooks/useQueries";
import { useAppStore } from "../store/useAppStore";

export function ArticleList() {
  const { selectedSourceId, selectedCategory, selectedArticleId, selectedTags, setSelectedArticleId } = useAppStore();
  const {
    data,
    isLoading,
    isFetchingNextPage,
    hasNextPage,
    fetchNextPage
  } = useArticles(
    selectedSourceId || undefined,
    selectedCategory || undefined,
    selectedTags.length > 0 ? selectedTags : undefined
  );

  // Flatten paginated data
  const articles = data?.pages.flat() ?? [];

  // Intersection Observer for infinite scroll
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
        <ScrollArea className="flex-1 h-0">
          <div>
            {articles.length === 0 ? (
              <div className="p-8 text-center text-muted-foreground">
                <p>暂无文章</p>
                <p className="text-xs mt-2">
                  {selectedTags.length > 0 ? '尝试调整标签过滤条件' : '添加RSS源后，文章将自动同步'}
                </p>
              </div>
            ) : (
              <>
                {articles.map((article) => (
                  <ArticleCard
                    key={article.id}
                    article={article}
                    isSelected={selectedArticleId === article.id}
                    onClick={() => setSelectedArticleId(article.id)}
                  />
                ))}

                {/* Intersection Observer Target */}
                <div ref={observerTarget} className="h-4" />

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
              </>
            )}
          </div>
        </ScrollArea>
      </div>
    </div>
  );
}
