import { Trash2 } from "lucide-react";
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuTrigger,
} from "./ui/context-menu";
import type { RSSSource } from "../types";

interface SourceContextMenuProps {
  source: RSSSource;
  onDelete: (source: RSSSource) => void;
  children: React.ReactNode;
}

export function SourceContextMenu({
  source,
  onDelete,
  children,
}: SourceContextMenuProps) {
  const handleDelete = () => {
    onDelete(source);
  };

  return (
    <ContextMenu>
      <ContextMenuTrigger asChild>{children}</ContextMenuTrigger>
      <ContextMenuContent className="w-48">
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
