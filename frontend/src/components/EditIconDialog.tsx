import { useState, useEffect } from "react";
import { Loader2, Image as ImageIcon } from "lucide-react";
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
import { useUpdateSource } from "../hooks/useQueries";
import { useToast } from "../hooks/useToast";
import { SourceIcon } from "./SourceIcon";
import type { RSSSource } from "../types";

interface EditIconDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  source: RSSSource | null;
}

export function EditIconDialog({
  open,
  onOpenChange,
  source,
}: EditIconDialogProps) {
  const [newIcon, setNewIcon] = useState("");
  const updateMutation = useUpdateSource();
  const { toast } = useToast();

  // Update local state when source changes or dialog opens
  useEffect(() => {
    if (open && source) {
      setNewIcon(source.icon);
    }
  }, [open, source]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!source || !newIcon.trim()) return;

    try {
      await updateMutation.mutateAsync({
        sourceId: source.id,
        data: { icon: newIcon.trim() },
      });

      toast({
        title: "图标已更新",
        description: `已成功更新 "${source.title}" 的图标`,
        variant: "success",
      });

      handleClose();
    } catch (error: any) {
      const errorMessage =
        error.response?.data?.detail || error.message || "更新图标失败";

      toast({
        title: "更新失败",
        description: errorMessage,
        variant: "error",
      });
    }
  };

  const handleClose = () => {
    setNewIcon("");
    updateMutation.reset();
    onOpenChange(false);
  };

  const isIconChanged = newIcon.trim() !== source?.icon;
  const isSubmitDisabled =
    !newIcon.trim() || !isIconChanged || updateMutation.isPending;

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[425px] overflow-hidden">
        <DialogHeader>
          <DialogTitle>自定义图标</DialogTitle>
          <DialogDescription>
            为 "{source?.title}" 设置自定义图标（emoji 或 URL）
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 overflow-hidden">
          {/* Icon Preview */}
          {newIcon.trim() && (
            <div className="flex items-center gap-3 p-3 bg-muted rounded-lg overflow-hidden">
              <div className="text-sm text-muted-foreground flex-shrink-0">预览:</div>
              <div className="flex-shrink-0">
                <SourceIcon icon={newIcon.trim()} size="md" />
              </div>
              <div className="flex-1 min-w-0 text-sm text-muted-foreground overflow-hidden">
                <div className="truncate">{newIcon.trim()}</div>
              </div>
            </div>
          )}

          <div className="space-y-2 overflow-hidden">
            <Label htmlFor="new-icon">图标</Label>
            <Input
              id="new-icon"
              type="text"
              placeholder="输入 emoji (🚀) 或图标 URL (https://...)"
              value={newIcon}
              onChange={(e) => setNewIcon(e.target.value)}
              autoFocus
              className="w-full min-w-0"
            />
            <p className="text-xs text-muted-foreground">
              支持 emoji 字符（例如：🚀 📰 🎯）或图标 URL
            </p>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={handleClose}
              disabled={updateMutation.isPending}
            >
              取消
            </Button>
            <Button type="submit" disabled={isSubmitDisabled}>
              {updateMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  保存中...
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
