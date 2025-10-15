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
import { useUpdateSource } from "../hooks/useQueries";
import { useToast } from "../hooks/useToast";
import type { RSSSource } from "../types";

interface RenameSourceDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  source: RSSSource | null;
}

export function RenameSourceDialog({
  open,
  onOpenChange,
  source,
}: RenameSourceDialogProps) {
  const [newTitle, setNewTitle] = useState("");
  const updateMutation = useUpdateSource();
  const { toast } = useToast();

  // Update local state when source changes or dialog opens
  useEffect(() => {
    if (open && source) {
      setNewTitle(source.title);
    }
  }, [open, source]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!source || !newTitle.trim()) return;

    try {
      await updateMutation.mutateAsync({
        sourceId: source.id,
        data: { title: newTitle.trim() },
      });

      toast({
        title: "RSS源已重命名",
        description: `已成功将 "${source.title}" 重命名为 "${newTitle.trim()}"`,
        variant: "success",
      });

      handleClose();
    } catch (error: any) {
      const errorMessage =
        error.response?.data?.detail || error.message || "重命名失败";

      toast({
        title: "重命名失败",
        description: errorMessage,
        variant: "error",
      });
    }
  };

  const handleClose = () => {
    setNewTitle("");
    updateMutation.reset();
    onOpenChange(false);
  };

  const isTitleChanged = newTitle.trim() !== source?.title;
  const isSubmitDisabled =
    !newTitle.trim() || !isTitleChanged || updateMutation.isPending;

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>重命名RSS源</DialogTitle>
          <DialogDescription>
            为 "{source?.title}" 输入新的名称
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="new-title">新名称</Label>
            <Input
              id="new-title"
              type="text"
              placeholder="输入新的RSS源名称"
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              autoFocus
            />
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
