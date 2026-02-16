import React from 'react';
import { Badge } from '../../ui/badge'; // Assuming shadcn/ui Badge is here
import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem } from '../../ui/dropdown-menu'; // Assuming shadcn/ui DropdownMenu components

interface Playground {
  id: string;
  name: string;
  review_ready: boolean;
}

interface PlaygroundBadgeProps {
  playgrounds: Playground[];
  onSelectPlayground: (id: string) => void;
}

const PlaygroundBadge: React.FC<PlaygroundBadgeProps> = ({ playgrounds, onSelectPlayground }) => {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Badge 
          variant="secondary" 
          className={`cursor-pointer font-mono text-xs ${playgrounds.some(p => p.review_ready) ? 'shadow-[0_0_10px_rgba(34,197,94,0.7)]' : ''}`}
          style={{ 
            backgroundColor: '#f1f1f1', 
            color: '#333333',
            border: '1px solid #d1d1d1'
          }}
        >
          PG:N
        </Badge>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        {playgrounds.map((playground) => (
          <DropdownMenuItem 
            key={playground.id} 
            onSelect={() => onSelectPlayground(playground.id)}
            className="cursor-pointer"
          >
            <div className="flex items-center justify-between w-full">
              <span>{playground.name}</span>
              {playground.review_ready && (
                <span className="w-2 h-2 bg-green-500 rounded-full"></span>
              )}
            </div>
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
};

export default PlaygroundBadge;