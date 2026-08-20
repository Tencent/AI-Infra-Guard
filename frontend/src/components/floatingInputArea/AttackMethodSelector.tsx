import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../ui/button';
import { Tooltip, TooltipContent, TooltipTrigger } from '../ui/tooltip';
import { Swords, Check, ChevronRight, HelpCircle } from 'lucide-react';
import { EvaluationItem } from '../../types';

interface AttackMethod {
  id: string;
  type: string;
  typeCn: string;
  description: string;
  descriptionCn: string;
  methods: {
    id: string;
    type: string;
    typeCn: string;
  }[];
}

interface AttackMethodSelectorProps {
  selectedMethods: string[];
  onMethodsSelect: (methods: string[]) => void;
  taskType?: string;
  selectedEvaluations?: EvaluationItem[];
}

const AttackMethodSelector: React.FC<AttackMethodSelectorProps> = ({
  selectedMethods,
  onMethodsSelect,
  taskType,
  selectedEvaluations = [],
}) => {
  const { t, i18n } = useTranslation();
  const [showMenu, setShowMenu] = useState(false);
  const [menuPosition, setMenuPosition] = useState<'top' | 'bottom'>('top');
  const [loading, setLoading] = useState(false);
  const [strategies, setStrategies] = useState<AttackMethod[]>([]);
  const [hoveredStrategy, setHoveredStrategy] = useState<string | null>(null);
  const hasSetDefaultRef = useRef(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const hideTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Decide whether the attack-method selection button should be shown
  const shouldShow = taskType === 'Model-Redteam-Report';
  
  // Check whether any evaluation set has official=false
  const hasNonOfficialEvaluation = selectedEvaluations.some(evaluation => evaluation.official === false);

  // Automatically load attack-method data when taskType is Model-Redteam-Report
  useEffect(() => {
    if (shouldShow && strategies.length === 0 && !loading) {
      const loadAttackMethods = async () => {
        setLoading(true);
        try {
          const response = await fetch('/api/v1/knowledge/jailbreak');
          
          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
          }
          
          const data = await response.json();
          
          if (data.status === 0 && data.data?.configSchema?.strategies) {
            setStrategies(data.data.configSchema.strategies);
            
            // Select strategies from globalParameters.defaultStrategies by default (only on first load)
            if (!hasSetDefaultRef.current && 
                data.data?.globalParameters?.defaultStrategies && 
                data.data.globalParameters.defaultStrategies.length > 0 && 
                onMethodsSelect) {
              onMethodsSelect(data.data.globalParameters.defaultStrategies);
              hasSetDefaultRef.current = true;
              
              // Find the strategy category containing the default methods and auto-hover it
              const defaultMethod = data.data.globalParameters.defaultStrategies[0];
              const strategyWithDefault = data.data.configSchema.strategies.find(strategy => 
                strategy.methods.some(method => method.id === defaultMethod)
              );
              if (strategyWithDefault) {
                setHoveredStrategy(strategyWithDefault.id);
              }
            }
          } else {
            console.error('获取攻击方法失败:', data.msg || data.message || '未知错误');
          }
        } catch (error) {
          console.error('加载攻击方法列表失败:', error);
        } finally {
          setLoading(false);
        }
      };
      
      loadAttackMethods();
    }
  }, [shouldShow, strategies.length, loading, onMethodsSelect]);

  // When the evaluation-set list changes and there are no unofficial sets, reset the default attack methods
  useEffect(() => {
    if (shouldShow && 
        strategies.length > 0 && 
        !hasNonOfficialEvaluation && 
        selectedMethods.length === 0 && 
        !hasSetDefaultRef.current && 
        onMethodsSelect) {
      
      // Find the default strategy among the already loaded strategies
      const defaultStrategies = strategies
        .flatMap(strategy => strategy.methods)
        .filter(method => method.id.includes('default') || method.type.includes('Default'))
        .map(method => method.id);
      
      if (defaultStrategies.length > 0) {
        onMethodsSelect(defaultStrategies);
        hasSetDefaultRef.current = true;
      }
    }
  }, [shouldShow, strategies, hasNonOfficialEvaluation, selectedMethods.length, onMethodsSelect]);

  // Handle attack-method selection
  const handleMethodSelect = (methodId: string) => {
    const isSelected = selectedMethods.includes(methodId);
    if (isSelected) {
      onMethodsSelect(selectedMethods.filter(id => id !== methodId));
    } else {
      onMethodsSelect([...selectedMethods, methodId]);
    }
  };

  // Handle selecting/deselecting all subcategories
  const handleSelectAllMethods = (strategyId: string) => {
    const strategy = strategies.find(s => s.id === strategyId);
    if (!strategy) return;
    
    const strategyMethodIds = strategy.methods.map(method => method.id);
    const allSelected = strategyMethodIds.every(id => selectedMethods.includes(id));
    
    if (allSelected) {
      // Unselect all methods under this strategy
      onMethodsSelect(selectedMethods.filter(id => !strategyMethodIds.includes(id)));
    } else {
      // Select all methods under this strategy
      const newSelectedMethods = [...selectedMethods];
      strategyMethodIds.forEach(id => {
        if (!newSelectedMethods.includes(id)) {
          newSelectedMethods.push(id);
        }
      });
      onMethodsSelect(newSelectedMethods);
    }
  };

  // Handle strategy hover
  const handleStrategyHover = (strategyId: string) => {
    if (hideTimerRef.current) {
      clearTimeout(hideTimerRef.current);
      hideTimerRef.current = null;
    }
    setHoveredStrategy(strategyId);
  };

  // Handle strategy leave
  const handleStrategyLeave = (event: React.MouseEvent) => {
    // Check whether the mouse moved into the second-level menu area
    const relatedTarget = event.relatedTarget as HTMLElement;
    if (relatedTarget && menuRef.current && menuRef.current.contains(relatedTarget)) {
      return; // Do not hide the second-level menu if the mouse moved to another area inside the menu
    }
    
    hideTimerRef.current = setTimeout(() => {
      setHoveredStrategy(null);
    }, 150);
  };

  // Handle entering the second-level menu area
  const handleSubmenuEnter = () => {
    if (hideTimerRef.current) {
      clearTimeout(hideTimerRef.current);
      hideTimerRef.current = null;
    }
  };

  // Toggle the menu
  const toggleMenu = () => {
    if (!showMenu) {
      // Compute the menu position
      const buttonElement = document.querySelector('.attack-method-menu-container button');
      if (buttonElement) {
        const buttonRect = buttonElement.getBoundingClientRect();
        const menuHeight = 300; // Reduce the menu height
        const viewportHeight = window.innerHeight;
        
        // Check whether there is enough space above
        const spaceAbove = buttonRect.top;
        // Check whether there is enough space below
        const spaceBelow = viewportHeight - buttonRect.bottom;
        
        // If the space above is sufficient and larger than the space below, place it above
        if (spaceAbove >= menuHeight && spaceAbove > spaceBelow) {
          setMenuPosition('top');
        } else {
          setMenuPosition('bottom');
        }
      }
    }
    setShowMenu(!showMenu);
  };

  // Close the menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (showMenu && menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setShowMenu(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showMenu]);

  // Clear the timer
  useEffect(() => {
    return () => {
      if (hideTimerRef.current) {
        clearTimeout(hideTimerRef.current);
      }
    };
  }, []);

  if (!shouldShow) {
    return null;
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <div className='relative group attack-method-menu-container' ref={menuRef}>
          <Button
            size='sm'
            variant='ghost'
            className='p-1 h-8 w-auto border rounded-[10px] gap-1'
            onClick={toggleMenu}
            disabled={loading || hasNonOfficialEvaluation}
          >
            <Swords className='w-4 h-4' />
            {(() => {
              if (loading) {
                return (
                  <span className='text-xs text-gray-500'>
                    {t('floatingInputArea.buttons.loading')}
                  </span>
                );
              } else if (hasNonOfficialEvaluation) {
                return (
                  <span className='text-xs text-gray-400'>
                    {t('floatingInputArea.buttons.attackMethodDisabled')}
                  </span>
                );
              } else if (selectedMethods.length === 0) {
                return (
                  <span className='text-xs text-gray-600'>
                    {t('floatingInputArea.buttons.noAttackMethod')}
                  </span>
                );
              } else {
                return (
                  <span className='text-xs text-gray-600'>
                    {`${t('floatingInputArea.buttons.attackMethod')} ${selectedMethods.length}`}
                  </span>
                );
              }
            })()}
          </Button>
          
          {/* Attack-method selection menu */}
          <div className={`absolute left-0 bg-white border border-gray-200 rounded-lg shadow-lg w-auto transition-all duration-200 ${showMenu ? 'opacity-100 visible' : 'opacity-0 invisible'} ${menuPosition === 'top' ? 'bottom-full mb-2' : 'top-full mt-2'}`} style={{zIndex: 30, maxHeight: '300px', minWidth: '300px'}} onMouseEnter={handleSubmenuEnter}>
            <div className='flex' style={{maxHeight: '300px'}}>
              {/* Strategy list */}
              <div className='flex-1 border-r border-gray-200' style={{minWidth: '150px'}} onMouseEnter={handleSubmenuEnter}>
                <div className='p-2'>
                  <div 
                    className='space-y-1 overflow-y-auto' 
                    style={{
                      maxHeight: 'calc(300px - 32px)',
                      scrollbarWidth: 'thin',
                      scrollbarColor: 'transparent transparent'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.scrollbarColor = 'rgba(209, 213, 219, 0.8) transparent';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.scrollbarColor = 'transparent transparent';
                    }}
                  >
                    {strategies.map((strategy) => {
                      const isBehavioralControl = strategy.typeCn === '行为控制攻击' || strategy.type === 'Behavioral Control Attack';
                      const strategyElement = (
                        <div
                          key={strategy.id}
                          className={`flex items-center justify-between p-2 hover:bg-gray-100 rounded cursor-pointer text-gray-600 ${hoveredStrategy === strategy.id ? 'bg-blue-50' : ''}`}
                          onMouseEnter={() => handleStrategyHover(strategy.id)}
                          onMouseLeave={(e) => handleStrategyLeave(e)}
                        >
                          <div className='flex items-center gap-1'>
                            <span className='text-sm font-medium text-gray-600 truncate'>
                              {i18n.language.startsWith('zh') ? strategy.typeCn : strategy.type}
                            </span>
                            {isBehavioralControl && (
                              <HelpCircle className='w-3 h-3 text-gray-400' />
                            )}
                          </div>
                          <ChevronRight className='w-4 h-4 text-gray-400' />
                        </div>
                      );
                      
                      if (isBehavioralControl) {
                        return (
                          <Tooltip key={strategy.id}>
                            <TooltipTrigger asChild>
                              {strategyElement}
                            </TooltipTrigger>
                            <TooltipContent>
                              <p>{t('floatingInputArea.tooltips.behavioralControlAttackDescription')}</p>
                            </TooltipContent>
                          </Tooltip>
                        );
                      }
                      
                      return strategyElement;
                    })}
                  </div>
                </div>
              </div>
              
              {/* Method list */}
              {hoveredStrategy && (
                <div className='flex-1' style={{minWidth: '150px'}} onMouseEnter={handleSubmenuEnter}>
                  <div className='p-2'>
                    <div 
                      className='space-y-1 overflow-y-auto' 
                      style={{
                        maxHeight: 'calc(300px - 64px)',
                        scrollbarWidth: 'thin',
                        scrollbarColor: 'transparent transparent'
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.scrollbarColor = 'rgba(209, 213, 219, 0.8) transparent';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.scrollbarColor = 'transparent transparent';
                      }}
                    >
                      {(() => {
                        const strategy = strategies.find(s => s.id === hoveredStrategy);
                        return strategy?.methods.map((method) => {
                          const isSelected = selectedMethods.includes(method.id);
                          return (
                            <div
                              key={method.id}
                              className={`flex items-center space-x-2 p-2 hover:bg-gray-100 rounded cursor-pointer text-gray-600 ${isSelected ? 'bg-blue-50 border border-blue-200' : ''}`}
                              onClick={() => handleMethodSelect(method.id)}
                            >
                              <div className={`w-4 h-4 border rounded flex items-center justify-center ${isSelected ? 'bg-blue-600 border-blue-600' : 'border-gray-300'}`}>
                                {isSelected && <Check className='w-3 h-3 text-white' />}
                              </div>
                              <span className='text-sm font-medium text-gray-600 truncate'>
                                {i18n.language.startsWith('zh') ? method.typeCn : method.type}
                              </span>
                            </div>
                          );
                        });
                      })()}
                    </div>
                    
                    {/* Select-all / unselect-all checkbox - placed at the bottom */}
                    {(() => {
                      const strategy = strategies.find(s => s.id === hoveredStrategy);
                      if (!strategy) return null;
                      
                      const strategyMethodIds = strategy.methods.map(method => method.id);
                      const allSelected = strategyMethodIds.every(id => selectedMethods.includes(id));
                      const someSelected = strategyMethodIds.some(id => selectedMethods.includes(id));
                      
                      return (
                        <div className='mt-2 pt-2 border-t border-gray-200'>
                          <div 
                            className='flex items-center space-x-2 p-2 hover:bg-gray-100 rounded cursor-pointer text-gray-600'
                            onClick={() => handleSelectAllMethods(hoveredStrategy)}
                          >
                            <div className={`w-4 h-4 border rounded flex items-center justify-center ${allSelected ? 'bg-blue-600 border-blue-600' : someSelected ? 'bg-blue-300 border-blue-300' : 'border-gray-300'}`}>
                              {allSelected && <Check className='w-3 h-3 text-white' />}
                              {someSelected && !allSelected && <div className='w-2 h-2 bg-white rounded-sm' />}
                            </div>
                            <span className='text-sm font-medium text-gray-600'>
                              {allSelected ? t('floatingInputArea.pluginSelection.deselectAll') : t('floatingInputArea.pluginSelection.selectAll')}
                            </span>
                          </div>
                        </div>
                      );
                    })()}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </TooltipTrigger>
      <TooltipContent>
        <p>{t('floatingInputArea.buttons.selectAttackMethod')}</p>
      </TooltipContent>
    </Tooltip>
  );
};

export default AttackMethodSelector;
