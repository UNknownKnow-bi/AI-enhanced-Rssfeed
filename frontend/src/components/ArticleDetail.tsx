import { Clock, Sparkles, ExternalLink } from "lucide-react";
import { ScrollArea } from "./ui/scroll-area";
import { Badge } from "./ui/badge";
import { Separator } from "./ui/separator";
import { Button } from "./ui/button";
import { SourceIcon } from "./SourceIcon";
import { useArticle } from "../hooks/useQueries";
import { useAppStore } from "../store/useAppStore";
import { sanitizeHTMLContent, stripHTMLTags } from "../lib/sanitizeContent";

export function ArticleDetail() {
  const { selectedArticleId } = useAppStore();
  const { data: article, isLoading } = useArticle(selectedArticleId);

  if (!selectedArticleId) {
    return (
      <div className="flex-1 bg-background flex items-center justify-center">
        <div className="text-center text-muted-foreground">
          <p>选择一篇文章以查看详情</p>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex-1 bg-background flex items-center justify-center">
        <p className="text-sm text-muted-foreground">加载中...</p>
      </div>
    );
  }

  if (!article) {
    return (
      <div className="flex-1 bg-background flex items-center justify-center">
        <p className="text-sm text-muted-foreground">文章未找到</p>
      </div>
    );
  }

  const formatDate = (dateString?: string) => {
    if (!dateString) return "未知时间";
    const date = new Date(dateString);
    return date.toLocaleString("zh-CN", {
      year: "numeric",
      month: "long",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const generateAISummary = (content?: string) => {
    if (!content) return "暂无内容摘要";

    // Strip HTML tags and generate summary
    const plainText = stripHTMLTags(content);
    if (plainText.length <= 200) return plainText;
    return plainText.substring(0, 200) + "...";
  };

  return (
    <div className="flex-1 bg-background flex flex-col h-full overflow-hidden">
      <ScrollArea className="flex-1 h-0">
        <div className="max-w-4xl mx-auto p-8">
          {/* Header */}
          <div className="mb-6">
            <div className="flex items-center gap-3 mb-4">
              <SourceIcon icon={article.source_icon} size="md" />
              <div className="flex-1">
                <p className="text-sm font-medium">{article.source_name}</p>
                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                  <Clock className="w-3 h-3" />
                  <span>{formatDate(article.pub_date || article.created_at)}</span>
                </div>
              </div>
              <Button variant="outline" size="sm" asChild>
                <a href={article.link} target="_blank" rel="noopener noreferrer">
                  <ExternalLink className="w-4 h-4 mr-2" />
                  原文链接
                </a>
              </Button>
            </div>

            <h1 className="text-2xl font-bold mb-4">{article.title}</h1>

            {article.cover_image && (
              <div className="mb-6 rounded-lg overflow-hidden">
                <img
                  src={article.cover_image}
                  alt={article.title}
                  className="w-full h-64 object-cover"
                  onError={(e) => {
                    e.currentTarget.style.display = "none";
                  }}
                />
              </div>
            )}
          </div>

          {/* AI Summary */}
          <div className="mb-6 p-4 bg-accent/30 rounded-lg border border-border">
            <div className="flex items-center gap-2 mb-3">
              <Sparkles className="w-5 h-5 text-primary" />
              <h3 className="font-semibold">AI 摘要</h3>
              <Badge variant="secondary">即将推出</Badge>
            </div>
            <p className="text-sm text-muted-foreground leading-relaxed">
              {generateAISummary(article.content)}
            </p>
          </div>

          <Separator className="my-6" />

          {/* Content */}
          <div className="prose prose-gray max-w-none">
            {article.content && (
              <div
                className="leading-relaxed"
                dangerouslySetInnerHTML={{
                  __html: sanitizeHTMLContent(article.content)
                }}
              />
            )}
          </div>
        </div>
      </ScrollArea>
    </div>
  );
}
