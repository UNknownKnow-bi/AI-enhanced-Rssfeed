import { useState } from "react";
import { Loader2, CheckCircle, XCircle } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "./ui/dialog";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { useCreateSource, useValidateURL } from "../hooks/useQueries";

interface AddSourceDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function AddSourceDialog({ open, onOpenChange }: AddSourceDialogProps) {
  const [url, setUrl] = useState("");
  const [sourceName, setSourceName] = useState("");
  const [category, setCategory] = useState("未分类");

  const validateMutation = useValidateURL();
  const createMutation = useCreateSource();

  const handleValidate = async () => {
    if (!url.trim()) return;
    const result = await validateMutation.mutateAsync(url.trim());
    // Auto-populate source name with RSS title after successful validation
    if (result.valid && result.title) {
      setSourceName(result.title);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!url.trim() || !sourceName.trim()) return;

    // Validate first if not already validated
    if (!validateMutation.data?.valid) {
      await handleValidate();
      return;
    }

    // Create the source
    try {
      await createMutation.mutateAsync({
        url: url.trim(),
        title: sourceName.trim(),
        category: category.trim() || "未分类",
      });

      // Reset and close
      setUrl("");
      setSourceName("");
      setCategory("未分类");
      validateMutation.reset();
      onOpenChange(false);
    } catch (error) {
      console.error("Failed to create source:", error);
    }
  };

  const handleClose = () => {
    setUrl("");
    setSourceName("");
    setCategory("未分类");
    validateMutation.reset();
    createMutation.reset();
    onOpenChange(false);
  };

  const isValidated = validateMutation.data?.valid;
  const validationError = validateMutation.data?.error;

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>添加RSS源</DialogTitle>
          <DialogDescription>
            输入RSS订阅源的URL，系统将自动验证并获取源信息
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="url">RSS URL</Label>
            <div className="flex gap-2">
              <Input
                id="url"
                type="url"
                placeholder="https://example.com/feed.xml"
                value={url}
                onChange={(e) => {
                  setUrl(e.target.value);
                  setSourceName("");
                  validateMutation.reset();
                }}
                className="flex-1"
              />
              <Button
                type="button"
                variant="outline"
                onClick={handleValidate}
                disabled={!url.trim() || validateMutation.isPending}
              >
                {validateMutation.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  "验证"
                )}
              </Button>
            </div>

            {/* Validation feedback */}
            {validateMutation.isPending && (
              <p className="text-sm text-muted-foreground flex items-center gap-2">
                <Loader2 className="w-3 h-3 animate-spin" />
                正在验证RSS源...
              </p>
            )}

            {isValidated && (
              <div className="p-3 bg-green-50 dark:bg-green-950 rounded-lg border border-green-200 dark:border-green-800">
                <div className="flex items-start gap-2">
                  <CheckCircle className="w-4 h-4 text-green-600 dark:text-green-400 mt-0.5" />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-green-900 dark:text-green-100">
                      验证成功
                    </p>
                    <p className="text-sm text-green-700 dark:text-green-300 mt-1">
                      {validateMutation.data.title}
                    </p>
                    {validateMutation.data.description && (
                      <p className="text-xs text-green-600 dark:text-green-400 mt-1">
                        {validateMutation.data.description}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )}

            {validationError && (
              <div className="p-3 bg-red-50 dark:bg-red-950 rounded-lg border border-red-200 dark:border-red-800">
                <div className="flex items-start gap-2">
                  <XCircle className="w-4 h-4 text-red-600 dark:text-red-400 mt-0.5" />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-red-900 dark:text-red-100">
                      验证失败
                    </p>
                    <p className="text-sm text-red-700 dark:text-red-300 mt-1">
                      {validationError}
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Source Name field - shown after validation */}
          {isValidated && (
            <div className="space-y-2">
              <Label htmlFor="sourceName">源名称</Label>
              <Input
                id="sourceName"
                type="text"
                placeholder="输入RSS源的名称"
                value={sourceName}
                onChange={(e) => setSourceName(e.target.value)}
              />
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="category">分类</Label>
            <Input
              id="category"
              type="text"
              placeholder="例如: 技术、新闻、博客"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            />
          </div>

          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={handleClose}>
              取消
            </Button>
            <Button
              type="submit"
              disabled={!isValidated || !sourceName.trim() || createMutation.isPending}
            >
              {createMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  添加中...
                </>
              ) : (
                "添加"
              )}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
