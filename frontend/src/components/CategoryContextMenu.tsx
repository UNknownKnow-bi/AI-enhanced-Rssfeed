import { Edit } from "lucide-react";
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuTrigger,
} from "./ui/context-menu";

interface CategoryContextMenuProps {
  category: string;
  onRename: (category: string) => void;
  children: React.ReactNode;
}

export function CategoryContextMenu({
  category,
  onRename,
  children,
}: CategoryContextMenuProps) {
  const handleRename = () => {
    onRename(category);
  };

  return (
    <ContextMenu>
      <ContextMenuTrigger asChild>{children}</ContextMenuTrigger>
      <ContextMenuContent className="w-48">
        <ContextMenuItem onSelect={handleRename}>
          <Edit className="w-4 h-4 mr-2" />
          重命名
        </ContextMenuItem>
      </ContextMenuContent>
    </ContextMenu>
  );
}
