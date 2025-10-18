import { memo, useMemo } from "react";
import { Clock } from "lucide-react";
import { SourceIcon } from "./SourceIcon";
import { AILabels } from "./AILabels";
import type { Article } from "../types";

interface ArticleCardProps {
  article: Article;
  isSelected: boolean;
  onClick: () => void;
}

// Memoized date formatter function
const formatDate = (dateString?: string): string => {
  if (!dateString) return "未知时间";

  const date = new Date(dateString);
  const now = new Date();
  const diffInHours = (now.getTime() - date.getTime()) / (1000 * 60 * 60);

  if (diffInHours < 1) {
    return `${Math.floor(diffInHours * 60)} 分钟前`;
  } else if (diffInHours < 24) {
    return `${Math.floor(diffInHours)} 小时前`;
  } else if (diffInHours < 48) {
    return "1 天前";
  } else {
    return `${Math.floor(diffInHours / 24)} 天前`;
  }
};

function ArticleCardComponent({ article, isSelected, onClick }: ArticleCardProps) {
  // Memoize formatted date to avoid recalculating on every render
  const formattedDate = useMemo(
    () => formatDate(article.pub_date || article.created_at),
    [article.pub_date, article.created_at]
  );

  return (
    <div
      onClick={onClick}
      className={`p-4 border-b border-border cursor-pointer transition-colors hover:bg-accent/50 ${
        isSelected ? "bg-accent" : ""
      }`}
    >
      <div className="flex gap-3">
        <div className="flex-shrink-0">
          <SourceIcon icon={article.source_icon} size="lg" />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-sm text-muted-foreground">{article.source_name}</span>
            <span className="text-sm text-muted-foreground">·</span>
            <div className="flex items-center gap-1 text-sm text-muted-foreground">
              <Clock className="w-3 h-3" />
              <span>{formattedDate}</span>
            </div>
          </div>

          <h3 className={`text-sm mb-2 line-clamp-2 ${!article.is_read ? "font-bold" : "font-medium"}`}>
            {article.title}
          </h3>

          {/* AI标签 - Compact模式 */}
          <AILabels
            labels={article.ai_labels}
            status={article.ai_label_status}
            mode="compact"
          />
        </div>
      </div>
    </div>
  );
}

// Memoize the component to prevent unnecessary re-renders
// Only re-render when article.id, isSelected, is_read, or onClick changes
export const ArticleCard = memo(ArticleCardComponent, (prevProps, nextProps) => {
  return (
    prevProps.article.id === nextProps.article.id &&
    prevProps.article.is_read === nextProps.article.is_read &&
    prevProps.isSelected === nextProps.isSelected &&
    prevProps.onClick === nextProps.onClick
  );
});
