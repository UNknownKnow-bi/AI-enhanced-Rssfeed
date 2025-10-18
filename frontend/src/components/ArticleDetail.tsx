import { Clock, Sparkles, ExternalLink, ChevronDown, ChevronUp, Copy, Loader2, Star, Trash2 } from "lucide-react";
import { ScrollArea } from "./ui/scroll-area";
import { Badge } from "./ui/badge";
import { Separator } from "./ui/separator";
import { Button } from "./ui/button";
import { SourceIcon } from "./SourceIcon";
import { AILabels } from "./AILabels";
import { useArticle, useMarkAsRead, useToggleFavorite, useTrashArticle } from "../hooks/useQueries";
import { useAppStore } from "../store/useAppStore";
import { sanitizeHTMLContent } from "../lib/sanitizeContent";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useState, useMemo, memo, useEffect } from "react";
import { toast } from "../hooks/useToast";

// Memoize ReactMarkdown component to prevent re-parsing on every render
const MemoizedMarkdown = memo(ReactMarkdown);

export function ArticleDetail() {
  const { selectedArticleId, setSelectedArticleId } = useAppStore();
  const { data: article, isLoading } = useArticle(selectedArticleId);
  const [isSummaryExpanded, setIsSummaryExpanded] = useState(true);

  const markAsReadMutation = useMarkAsRead();
  const toggleFavoriteMutation = useToggleFavorite();
  const trashArticleMutation = useTrashArticle();

  // Auto-mark as read after 2 seconds
  useEffect(() => {
    if (article && !article.is_read) {
      const timer = setTimeout(() => {
        markAsReadMutation.mutate({ articleId: article.id, isRead: true });
      }, 2000);

      return () => clearTimeout(timer);
    }
  }, [article?.id, article?.is_read]);

  const handleToggleFavorite = () => {
    if (!article) return;
    toggleFavoriteMutation.mutate(
      { articleId: article.id, isFavorite: !article.is_favorite },
      {
        onSuccess: () => {
          toast({
            title: article.is_favorite ? "已取消收藏" : "已加入收藏",
            variant: "success",
          });
        },
        onError: () => {
          toast({
            title: "操作失败",
            description: "请稍后重试",
            variant: "destructive",
          });
        },
      }
    );
  };

  const handleTrash = () => {
    if (!article) return;
    if (confirm("确定要将此文章移至回收站吗？")) {
      trashArticleMutation.mutate(article.id, {
        onSuccess: () => {
          toast({
            title: "已移至回收站",
            variant: "success",
          });
          // Close article detail view
          setSelectedArticleId(null);
        },
        onError: () => {
          toast({
            title: "操作失败",
            description: "请稍后重试",
            variant: "destructive",
          });
        },
      });
    }
  };

  // Memoize sanitized HTML content to avoid re-sanitizing on every render
  const sanitizedContent = useMemo(
    () => article?.content ? sanitizeHTMLContent(article.content) : '',
    [article?.content]
  );

  // Memoize formatted date
  const formattedDate = useMemo(
    () => {
      if (!article) return "未知时间";
      const dateString = article.pub_date || article.created_at;
      if (!dateString) return "未知时间";
      const date = new Date(dateString);
      return date.toLocaleString("zh-CN", {
        year: "numeric",
        month: "long",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    },
    [article?.pub_date, article?.created_at]
  );

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

  const handleCopySummary = () => {
    if (article?.ai_summary) {
      navigator.clipboard.writeText(article.ai_summary);
      toast({
        title: "复制成功",
        description: "AI 摘要已复制到剪贴板",
        variant: "success",
      });
    }
  };

  const renderAISummary = () => {
    // Don't show summary section if article is labeled as ignorable
    if (article?.ai_labels?.identities?.includes('#可忽略')) {
      return null;
    }

    const status = article?.ai_summary_status || 'pending';

    return (
      <div className="mb-6 p-4 bg-accent/30 rounded-lg border border-border">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-primary" />
            <h3 className="font-semibold">AI 摘要</h3>
            {status === 'pending' && (
              <Badge variant="secondary" className="flex items-center gap-1">
                <Loader2 className="w-3 h-3 animate-spin" />
                处理中
              </Badge>
            )}
            {status === 'success' && (
              <Badge variant="default">已生成</Badge>
            )}
            {status === 'error' && (
              <Badge variant="destructive">生成失败</Badge>
            )}
          </div>
          {status === 'success' && (
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={handleCopySummary}
                className="h-8"
              >
                <Copy className="w-4 h-4 mr-1" />
                复制
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsSummaryExpanded(!isSummaryExpanded)}
                className="h-8"
              >
                {isSummaryExpanded ? (
                  <>
                    <ChevronUp className="w-4 h-4 mr-1" />
                    折叠
                  </>
                ) : (
                  <>
                    <ChevronDown className="w-4 h-4 mr-1" />
                    展开
                  </>
                )}
              </Button>
            </div>
          )}
        </div>

        {status === 'pending' && (
          <p className="text-sm text-muted-foreground">
            正在赶来的路上...请稍候
          </p>
        )}

        {status === 'error' && (
          <div className="text-sm text-muted-foreground">
            <p className="mb-1">AI摘要生成失败</p>
            {article?.ai_summary_error && (
              <p className="text-xs opacity-70">{article.ai_summary_error}</p>
            )}
          </div>
        )}

        {status === 'success' && article?.ai_summary && isSummaryExpanded && (
          <div className="prose prose-sm prose-gray max-w-none">
            <MemoizedMarkdown remarkPlugins={[remarkGfm]}>
              {article.ai_summary}
            </MemoizedMarkdown>
          </div>
        )}

        {status === 'success' && !isSummaryExpanded && (
          <p className="text-sm text-muted-foreground italic">
            点击展开查看摘要内容
          </p>
        )}
      </div>
    );
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
                  <span>{formattedDate}</span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleToggleFavorite}
                  disabled={toggleFavoriteMutation.isPending}
                  title={article.is_favorite ? "取消收藏" : "收藏"}
                >
                  <Star
                    className={`w-4 h-4 ${
                      article.is_favorite ? "fill-yellow-400 text-yellow-400" : ""
                    }`}
                  />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleTrash}
                  disabled={trashArticleMutation.isPending}
                  title="移至回收站"
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
                <Button variant="outline" size="sm" asChild>
                  <a href={article.link} target="_blank" rel="noopener noreferrer">
                    <ExternalLink className="w-4 h-4 mr-2" />
                    原文链接
                  </a>
                </Button>
              </div>
            </div>

            <h1 className={`text-2xl font-bold mb-4 ${!article.is_read ? "font-extrabold" : ""}`}>
              {article.title}
            </h1>

            {/* AI标签 - Full模式 */}
            {article.ai_labels && (
              <div className="mb-4">
                <AILabels
                  labels={article.ai_labels}
                  status={article.ai_label_status}
                  mode="full"
                />
              </div>
            )}

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
          {renderAISummary()}

          <Separator className="my-6" />

          {/* Content */}
          <div className="prose prose-gray max-w-none">
            {sanitizedContent && (
              <div
                className="leading-relaxed"
                dangerouslySetInnerHTML={{
                  __html: sanitizedContent
                }}
              />
            )}
          </div>
        </div>
      </ScrollArea>
    </div>
  );
}
