import { Trash2, Copy, Edit, Image } from "lucide-react";
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuTrigger,
} from "./ui/context-menu";
import type { RSSSource } from "../types";

interface SourceContextMenuProps {
  source: RSSSource;
  onDelete: (source: RSSSource) => void;
  onRename?: (source: RSSSource) => void;
  onEditIcon?: (source: RSSSource) => void;
  onCopyLink?: (source: RSSSource) => void;
  children: React.ReactNode;
}

export function SourceContextMenu({
  source,
  onDelete,
  onRename,
  onEditIcon,
  onCopyLink,
  children,
}: SourceContextMenuProps) {
  const handleDelete = () => {
    onDelete(source);
  };

  const handleRename = () => {
    onRename?.(source);
  };

  const handleEditIcon = () => {
    onEditIcon?.(source);
  };

  const handleCopyLink = () => {
    onCopyLink?.(source);
  };

  return (
    <ContextMenu>
      <ContextMenuTrigger asChild>{children}</ContextMenuTrigger>
      <ContextMenuContent className="w-48">
        <ContextMenuItem onSelect={handleCopyLink}>
          <Copy className="w-4 h-4 mr-2" />
          复制订阅源
        </ContextMenuItem>

        <ContextMenuItem onSelect={handleRename}>
          <Edit className="w-4 h-4 mr-2" />
          重命名
        </ContextMenuItem>

        <ContextMenuItem onSelect={handleEditIcon}>
          <Image className="w-4 h-4 mr-2" />
          自定义图标
        </ContextMenuItem>

        <ContextMenuSeparator />

        <ContextMenuItem
          className="text-red-600 dark:text-red-400 focus:text-red-600 focus:bg-red-50 dark:focus:bg-red-950/50"
          onSelect={handleDelete}
        >
          <Trash2 className="w-4 h-4 mr-2" />
          删除源
        </ContextMenuItem>
      </ContextMenuContent>
    </ContextMenu>
  );
}
