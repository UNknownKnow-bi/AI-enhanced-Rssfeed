import { Clock } from "lucide-react";
import { SourceIcon } from "./SourceIcon";
import { AILabels } from "./AILabels";
import type { Article } from "../types";

interface ArticleCardProps {
  article: Article;
  isSelected: boolean;
  onClick: () => void;
}

export function ArticleCard({ article, isSelected, onClick }: ArticleCardProps) {
  // Format the date
  const formatDate = (dateString?: string) => {
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
              <span>{formatDate(article.pub_date || article.created_at)}</span>
            </div>
          </div>

          <h3 className="text-sm font-medium mb-2 line-clamp-2">
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
