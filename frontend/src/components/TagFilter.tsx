import { useState, useMemo, useCallback } from 'react';
import { Badge } from './ui/badge';
import { ScrollArea } from './ui/scroll-area';
import { Input } from './ui/input';
import { X, Search } from 'lucide-react';
import { useAvailableTags } from '../hooks/useQueries';
import { useAppStore } from '../store/useAppStore';
import { getTagStyle } from './AILabels';
import { cn } from '../lib/utils';
import { useDebounce } from '../hooks/useDebounce';

export function TagFilter() {
  const { selectedSourceId, selectedCategory, selectedTags, toggleTag, clearTags } = useAppStore();
  const { data: availableTags, isLoading } = useAvailableTags(
    selectedSourceId || undefined,
    selectedCategory || undefined
  );

  const [searchQuery, setSearchQuery] = useState('');

  // Debounce search query to reduce re-renders while typing
  const debouncedSearchQuery = useDebounce(searchQuery, 300);

  // Memoize filtered tags to avoid recalculating on every render
  const filteredTags = useMemo(
    () => (availableTags || []).filter(tag =>
      tag.toLowerCase().includes(debouncedSearchQuery.toLowerCase())
    ),
    [availableTags, debouncedSearchQuery]
  );

  // Group tags by category (memoized)
  const groupedTags = useMemo(() => {
    const identityTags = ['#独立开发必备', '#博主素材', '#双重价值', '#可忽略'];
    const themeTags = ['#模型动态', '#技术教程', '#深度洞察', '#经验分享', '#AI应用', '#趣味探索'];

    return {
      special: filteredTags.filter(t => t === '#VibeCoding'),
      identities: filteredTags.filter(t => identityTags.includes(t)),
      themes: filteredTags.filter(t => themeTags.includes(t)),
      extra: filteredTags.filter(t => !identityTags.includes(t) && !themeTags.includes(t) && t !== '#VibeCoding'),
    };
  }, [filteredTags]);

  // Memoize callbacks
  const handleClearTags = useCallback(() => clearTags(), [clearTags]);
  const handleToggleTag = useCallback((tag: string) => toggleTag(tag), [toggleTag]);

  return (
    <div className="w-64 border-r border-border bg-background flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-border flex-shrink-0">
        <div className="flex items-center justify-between mb-2">
          <h3 className="font-semibold text-sm">标签过滤</h3>
          {selectedTags.length > 0 && (
            <button
              onClick={handleClearTags}
              className="text-xs text-muted-foreground hover:text-foreground"
            >
              清除 ({selectedTags.length})
            </button>
          )}
        </div>

        {/* Search Input */}
        <div className="relative">
          <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="搜索标签..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-8 h-9 text-sm"
          />
        </div>
      </div>

      {/* Selected Tags */}
      {selectedTags.length > 0 && (
        <div className="p-3 border-b border-border bg-muted/30">
          <div className="flex flex-wrap gap-1.5">
            {selectedTags.map(tag => (
              <Badge
                key={tag}
                className={cn(
                  "text-xs cursor-pointer",
                  getTagStyle(tag)
                )}
                onClick={() => handleToggleTag(tag)}
              >
                {tag}
                <X className="ml-1 h-3 w-3" />
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* Available Tags */}
      <ScrollArea className="flex-1">
        <div className="p-3 space-y-4">
          {isLoading ? (
            <p className="text-xs text-muted-foreground">加载中...</p>
          ) : filteredTags.length === 0 ? (
            <p className="text-xs text-muted-foreground">暂无标签</p>
          ) : (
            <>
              {groupedTags.special.length > 0 && (
                <TagGroup
                  title="特殊"
                  tags={groupedTags.special}
                  selectedTags={selectedTags}
                  onToggle={handleToggleTag}
                />
              )}

              {groupedTags.identities.length > 0 && (
                <TagGroup
                  title="身份标签"
                  tags={groupedTags.identities}
                  selectedTags={selectedTags}
                  onToggle={handleToggleTag}
                />
              )}

              {groupedTags.themes.length > 0 && (
                <TagGroup
                  title="主题标签"
                  tags={groupedTags.themes}
                  selectedTags={selectedTags}
                  onToggle={handleToggleTag}
                />
              )}

              {groupedTags.extra.length > 0 && (
                <TagGroup
                  title="其他"
                  tags={groupedTags.extra}
                  selectedTags={selectedTags}
                  onToggle={handleToggleTag}
                />
              )}
            </>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}

// Helper component for tag groups
function TagGroup({
  title,
  tags,
  selectedTags,
  onToggle
}: {
  title: string;
  tags: string[];
  selectedTags: string[];
  onToggle: (tag: string) => void;
}) {
  return (
    <div>
      <h4 className="text-xs font-medium text-muted-foreground mb-2">{title}</h4>
      <div className="flex flex-wrap gap-1.5">
        {tags.map(tag => {
          const isSelected = selectedTags.includes(tag);
          return (
            <Badge
              key={tag}
              className={cn(
                "text-xs cursor-pointer transition-opacity",
                getTagStyle(tag),
                !isSelected && "opacity-60 hover:opacity-100"
              )}
              onClick={() => onToggle(tag)}
            >
              {tag}
            </Badge>
          );
        })}
      </div>
    </div>
  );
}
