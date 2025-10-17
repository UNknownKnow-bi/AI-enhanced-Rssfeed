import { Clock, Sparkles, ExternalLink, ChevronDown, ChevronUp, Copy, Loader2 } from "lucide-react";
import { ScrollArea } from "./ui/scroll-area";
import { Badge } from "./ui/badge";
import { Separator } from "./ui/separator";
import { Button } from "./ui/button";
import { SourceIcon } from "./SourceIcon";
import { AILabels } from "./AILabels";
import { useArticle } from "../hooks/useQueries";
import { useAppStore } from "../store/useAppStore";
import { sanitizeHTMLContent } from "../lib/sanitizeContent";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useState } from "react";
import { toast } from "../hooks/useToast";

export function ArticleDetail() {
  const { selectedArticleId } = useAppStore();
  const { data: article, isLoading } = useArticle(selectedArticleId);
  const [isSummaryExpanded, setIsSummaryExpanded] = useState(true);

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
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {article.ai_summary}
            </ReactMarkdown>
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
