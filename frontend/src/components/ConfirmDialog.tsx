import { useState } from "react";
import { AlertTriangle, Loader2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "./ui/dialog";
import { Button } from "./ui/button";
import { Checkbox } from "./ui/checkbox";
import { Label } from "./ui/label";

export interface ConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  confirmText?: string;
  cancelText?: string;
  variant?: "danger" | "warning" | "info";
  requireCheck?: boolean;
  checkLabel?: string;
  onConfirm: () => Promise<void> | void;
  loading?: boolean;
}

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmText = "确认",
  cancelText = "取消",
  variant = "info",
  requireCheck = false,
  checkLabel = "我了解这个操作的后果",
  onConfirm,
  loading = false,
}: ConfirmDialogProps) {
  const [isChecked, setIsChecked] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  const handleConfirm = async () => {
    if (requireCheck && !isChecked) return;

    setIsProcessing(true);
    try {
      await onConfirm();
      // Reset state on success
      setIsChecked(false);
      onOpenChange(false);
    } catch (error) {
      console.error("Confirm action failed:", error);
      // Don't close dialog on error, let user retry
    } finally {
      setIsProcessing(false);
    }
  };

  const handleCancel = () => {
    setIsChecked(false);
    onOpenChange(false);
  };

  const canConfirm = !requireCheck || isChecked;
  const isButtonLoading = loading || isProcessing;

  // Variant styles
  const variantStyles = {
    danger: {
      icon: "text-red-600 dark:text-red-400",
      button: "destructive",
    },
    warning: {
      icon: "text-yellow-600 dark:text-yellow-400",
      button: "default",
    },
    info: {
      icon: "text-blue-600 dark:text-blue-400",
      button: "default",
    },
  };

  const currentVariant = variantStyles[variant];

  return (
    <Dialog open={open} onOpenChange={handleCancel}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <div className="flex items-start gap-4">
            {variant !== "info" && (
              <div className="flex-shrink-0">
                <AlertTriangle className={`w-6 h-6 ${currentVariant.icon}`} />
              </div>
            )}
            <div className="flex-1">
              <DialogTitle>{title}</DialogTitle>
              <DialogDescription className="mt-2">
                {description}
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        {requireCheck && (
          <div className="flex items-center space-x-2 py-4">
            <Checkbox
              id="confirm-check"
              checked={isChecked}
              onCheckedChange={(checked) => setIsChecked(checked === true)}
              disabled={isButtonLoading}
            />
            <Label
              htmlFor="confirm-check"
              className="text-sm font-normal cursor-pointer"
            >
              {checkLabel}
            </Label>
          </div>
        )}

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={handleCancel}
            disabled={isButtonLoading}
          >
            {cancelText}
          </Button>
          <Button
            type="button"
            variant={currentVariant.button as "default" | "destructive"}
            onClick={handleConfirm}
            disabled={!canConfirm || isButtonLoading}
          >
            {isButtonLoading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                处理中...
              </>
            ) : (
              confirmText
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
