import { ArticleCard } from "./ArticleCard";
import { ScrollArea } from "./ui/scroll-area";
import { useArticles } from "../hooks/useQueries";
import { useAppStore } from "../store/useAppStore";

export function ArticleList() {
  const { selectedSourceId, selectedArticleId, setSelectedArticleId } = useAppStore();
  const { data: articles = [], isLoading } = useArticles(selectedSourceId || undefined);

  if (isLoading) {
    return (
      <div className="w-full border-r border-border bg-background flex items-center justify-center h-full">
        <p className="text-sm text-muted-foreground">加载中...</p>
      </div>
    );
  }

  return (
    <div className="w-full border-r border-border bg-background flex flex-col h-full overflow-hidden">
      <div className="p-4 border-b border-border flex-shrink-0">
        <h2 className="font-semibold">文章列表</h2>
        <p className="text-sm text-muted-foreground mt-1">
          共 {articles.length} 篇文章
        </p>
      </div>
      <ScrollArea className="flex-1 h-0">
        <div>
          {articles.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground">
              <p>暂无文章</p>
              <p className="text-xs mt-2">添加RSS源后，文章将自动同步</p>
            </div>
          ) : (
            articles.map((article) => (
              <ArticleCard
                key={article.id}
                article={article}
                isSelected={selectedArticleId === article.id}
                onClick={() => setSelectedArticleId(article.id)}
              />
            ))
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
