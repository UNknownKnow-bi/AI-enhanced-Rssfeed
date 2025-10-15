import { useState, useEffect } from "react";
import { Loader2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "./ui/dialog";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { useRenameCategoryMutation } from "../hooks/useQueries";
import { useToast } from "../hooks/useToast";
import type { RSSSource } from "../types";

interface RenameCategoryDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  category: string | null;
  sources: RSSSource[];
}

export function RenameCategoryDialog({
  open,
  onOpenChange,
  category,
  sources,
}: RenameCategoryDialogProps) {
  const [newCategoryName, setNewCategoryName] = useState("");
  const renameMutation = useRenameCategoryMutation();
  const { toast } = useToast();

  // Get all unique categories from sources
  const existingCategories = Array.from(new Set(sources.map((s) => s.category)));

  // Update local state when category changes or dialog opens
  useEffect(() => {
    if (open && category) {
      setNewCategoryName(category);
    }
  }, [open, category]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!category || !newCategoryName.trim()) return;

    const trimmedName = newCategoryName.trim();

    // Check for duplicate category name
    if (trimmedName !== category && existingCategories.includes(trimmedName)) {
      toast({
        title: "类别名称已存在",
        description: `类别 "${trimmedName}" 已经存在，请使用其他名称`,
        variant: "error",
      });
      return;
    }

    // Get all sources in this category
    const sourcesInCategory = sources.filter((s) => s.category === category);
    const sourceIds = sourcesInCategory.map((s) => s.id);

    if (sourceIds.length === 0) {
      toast({
        title: "无可更新的源",
        description: "该类别下没有任何RSS源",
        variant: "error",
      });
      return;
    }

    try {
      await renameMutation.mutateAsync({
        oldCategory: category,
        newCategory: trimmedName,
        sourceIds,
      });

      toast({
        title: "类别已重命名",
        description: `已成功将 "${category}" 重命名为 "${trimmedName}"`,
        variant: "success",
      });

      handleClose();
    } catch (error: any) {
      const errorMessage =
        error.message || "重命名失败，请重试";

      toast({
        title: "重命名失败",
        description: errorMessage,
        variant: "error",
      });
    }
  };

  const handleClose = () => {
    setNewCategoryName("");
    renameMutation.reset();
    onOpenChange(false);
  };

  const isCategoryChanged = newCategoryName.trim() !== category;
  const isSubmitDisabled =
    !newCategoryName.trim() || !isCategoryChanged || renameMutation.isPending;

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[425px] overflow-hidden">
        <DialogHeader>
          <DialogTitle>重命名类别</DialogTitle>
          <DialogDescription>
            为类别 "{category}" 输入新的名称
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 overflow-hidden">
          <div className="space-y-2 overflow-hidden">
            <Label htmlFor="new-category-name">新名称</Label>
            <Input
              id="new-category-name"
              type="text"
              placeholder="输入新的类别名称"
              value={newCategoryName}
              onChange={(e) => setNewCategoryName(e.target.value)}
              autoFocus
              className="w-full min-w-0"
            />
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={handleClose}
              disabled={renameMutation.isPending}
            >
              取消
            </Button>
            <Button type="submit" disabled={isSubmitDisabled}>
              {renameMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  更新中...
                </>
              ) : (
                "保存"
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
