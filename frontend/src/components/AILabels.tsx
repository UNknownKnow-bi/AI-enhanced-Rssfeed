import { Badge } from "./ui/badge";
import type { Article } from "../types";
import { cn } from "../lib/utils";

interface AILabelsProps {
  labels?: Article["ai_labels"];
  status?: Article["ai_label_status"];
  mode?: "compact" | "full";
  className?: string;
}

// 标签样式映射 - 基于Tailwind配色
const TAG_STYLES: Record<string, string> = {
  // 第一层 - 核心身份标签
  "#独立开发必备": "bg-blue-100 text-blue-700 border-blue-300",
  "#博主素材": "bg-purple-100 text-purple-700 border-purple-300",
  "#双重价值": "bg-green-100 text-green-700 border-green-300",
  "#可忽略": "bg-gray-100 text-gray-500 border-gray-300",

  // 第二层 - 主题标签
  "#模型动态": "bg-cyan-100 text-cyan-700 border-cyan-300",
  "#技术教程": "bg-orange-100 text-orange-700 border-orange-300",
  "#深度洞察": "bg-indigo-100 text-indigo-700 border-indigo-300",
  "#经验分享": "bg-pink-100 text-pink-700 border-pink-300",
  "#AI应用": "bg-teal-100 text-teal-700 border-teal-300",
  "#趣味探索": "bg-yellow-100 text-yellow-700 border-yellow-300",

  // 特殊标签 - VibeCoding 使用渐变背景
  "#VibeCoding": "bg-gradient-to-r from-violet-500 to-purple-500 text-white border-purple-400 font-semibold",

  // 默认样式
  default: "bg-slate-100 text-slate-700 border-slate-300",
};

// 状态徽章配置
const STATUS_BADGES = {
  processing: {
    text: "🏃 赶来的路上",
    className: "bg-gray-100 text-gray-600 border-gray-300",
  },
  error: {
    text: "❌ 寄掉了",
    className: "bg-red-100 text-red-600 border-red-300",
  },
};

/**
 * 获取标签的样式类名
 */
export function getTagStyle(tag: string): string {
  return TAG_STYLES[tag] || TAG_STYLES.default;
}

/**
 * 按优先级排序标签
 * 优先级: #VibeCoding > identities > themes > extra
 */
function sortTagsByPriority(labels?: Article["ai_labels"]): string[] {
  if (!labels) return [];

  const tags: string[] = [];

  // 1. VibeCoding (最高优先级)
  if (labels.vibe_coding) {
    tags.push("#VibeCoding");
  }

  // 2. Identities (核心身份)
  if (labels.identities && labels.identities.length > 0) {
    tags.push(...labels.identities);
  }

  // 3. Themes (主题)
  if (labels.themes && labels.themes.length > 0) {
    tags.push(...labels.themes);
  }

  // 4. Extra (其他)
  if (labels.extra && labels.extra.length > 0) {
    tags.push(...labels.extra);
  }

  return tags;
}

export function AILabels({
  labels,
  status,
  mode = "compact",
  className,
}: AILabelsProps) {
  // 如果状态是 processing 或 error，显示状态徽章
  if (status === "processing" || status === "error") {
    const statusConfig = STATUS_BADGES[status];
    return (
      <div className={cn("flex items-center gap-1.5", className)}>
        <Badge className={statusConfig.className}>{statusConfig.text}</Badge>
      </div>
    );
  }

  // 如果没有标签或状态是 pending，不显示
  if (!labels || status === "pending") {
    return null;
  }

  // 获取排序后的标签
  const sortedTags = sortTagsByPriority(labels);

  // 如果没有标签，不显示
  if (sortedTags.length === 0) {
    return null;
  }

  // Compact 模式：最多显示3个标签
  if (mode === "compact") {
    const displayTags = sortedTags.slice(0, 3);
    const remainingCount = sortedTags.length - displayTags.length;

    return (
      <div className={cn("flex flex-wrap items-center gap-1.5", className)}>
        {displayTags.map((tag, index) => (
          <Badge
            key={`${tag}-${index}`}
            className={cn(
              "text-xs px-2 py-0.5 rounded-md",
              getTagStyle(tag)
            )}
          >
            {tag}
          </Badge>
        ))}
        {remainingCount > 0 && (
          <Badge className="bg-gray-100 text-gray-500 border-gray-300 text-xs px-2 py-0.5 rounded-md">
            +{remainingCount}
          </Badge>
        )}
      </div>
    );
  }

  // Full 模式：显示所有标签
  return (
    <div className={cn("flex flex-wrap gap-2", className)}>
      {sortedTags.map((tag, index) => (
        <Badge
          key={`${tag}-${index}`}
          className={cn(
            "text-xs px-2.5 py-1 rounded-md",
            getTagStyle(tag)
          )}
        >
          {tag}
        </Badge>
      ))}
    </div>
  );
}
