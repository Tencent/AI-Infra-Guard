import React from 'react';
import { Avatar, AvatarFallback, AvatarImage } from './ui/avatar';
import { User, Bot, Shield } from 'lucide-react';

interface MessageAvatarProps {
  type: 'user' | 'assistant' | 'system';
  className?: string;
}

const MessageAvatar: React.FC<MessageAvatarProps> = ({ type, className = "w-8 h-8" }) => {
  if (type === 'user') {
    return (
      <Avatar className={className}>
        <AvatarFallback className="bg-blue-600 text-white text-sm">
          <User className="w-4 h-4" />
        </AvatarFallback>
      </Avatar>
    );
  }

  if (type === 'assistant') {
    return (
      <Avatar className={className}>
        <AvatarFallback className="bg-green-600 text-white text-sm">
          <Bot className="w-4 h-4" />
        </AvatarFallback>
      </Avatar>
    );
  }

  return (
    <Avatar className={className}>
      <AvatarFallback className="bg-orange-600 text-white text-sm">
        <Shield className="w-4 h-4" />
      </AvatarFallback>
    </Avatar>
  );
};

export default MessageAvatar;
