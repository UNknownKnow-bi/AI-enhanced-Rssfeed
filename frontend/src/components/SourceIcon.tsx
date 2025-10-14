import { useState } from "react";

interface SourceIconProps {
  icon: string;
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function SourceIcon({ icon, size = "md", className = "" }: SourceIconProps) {
  const [imageError, setImageError] = useState(false);

  // Determine if icon is a URL or emoji/text
  const isUrl = icon?.startsWith("http://") || icon?.startsWith("https://");

  // Size mappings
  const sizeClasses = {
    sm: "w-4 h-4 text-sm",
    md: "w-6 h-6 text-base",
    lg: "w-8 h-8 text-xl",
  };

  const containerSizeClasses = {
    sm: "w-8 h-8",
    md: "w-10 h-10",
    lg: "w-12 h-12",
  };

  // If it's a URL and no error, render as image
  if (isUrl && !imageError) {
    return (
      <div
        className={`${containerSizeClasses[size]} rounded-lg bg-muted flex items-center justify-center overflow-hidden ${className}`}
      >
        <img
          src={icon}
          alt="Source icon"
          className={`${sizeClasses[size]} object-contain`}
          onError={() => setImageError(true)}
        />
      </div>
    );
  }

  // Otherwise render as text/emoji
  return (
    <div
      className={`${containerSizeClasses[size]} rounded-lg bg-muted flex items-center justify-center ${className}`}
    >
      <span className={sizeClasses[size]}>{icon || "📰"}</span>
    </div>
  );
}
