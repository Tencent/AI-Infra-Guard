import React from 'react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip } from 'recharts';
import { useTranslation } from 'react-i18next';

interface RadarChartData {
  subject: string;
  score: number;
  fullMark: number;
}

interface RadarChartProps {
  data: RadarChartData[];
  title: string;
  height?: number;
}

// Custom Tooltip component
const CustomTooltip = ({ active, payload }: any) => {
  const { t } = useTranslation();
  
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-white p-3 rounded-lg shadow-lg border border-gray-200">
        <p className="font-semibold text-gray-800">{data.subject}</p>
        <p className="text-sm text-gray-600">
          {t('redteam.jailbreakSuccessRate')}: <span className="font-medium text-blue-600">{Math.round(data.score * 100)}%</span>
        </p>
      </div>
    );
  }
  return null;
};

const RadarChartComponent: React.FC<RadarChartProps> = ({
  data,
  title,
  height = 300,
}) => {
  const { t } = useTranslation();

  if (!data || data.length === 0) {
    return (
      <div className="bg-white rounded-2xl overflow-hidden shadow-lg border border-gray-100">
        <div className="p-4">
          <h3 className="text-lg font-bold text-center mb-4">{title}</h3>
          <div className="text-center text-gray-400 py-8">{t('redteam.noData')}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl overflow-hidden shadow-lg border border-gray-100">
      <div className="p-4">
        <h3 className="text-lg font-bold text-center mb-4">{title}</h3>
        <div className="w-full flex items-center justify-center" style={{ height: `${height}px` }}>
          <div className="w-full h-full max-w-sm">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={data} margin={{ top: 50, right: 50, bottom: 60, left: 50 }}>
                <PolarGrid />
                <PolarAngleAxis 
                  dataKey="subject" 
                  tick={{ fontSize: 12, fill: '#666' }}
                  className="text-xs"
                  tickLine={false}
                />
                <PolarRadiusAxis 
                  angle={90} 
                  domain={[0, 1]} 
                  tick={{ fontSize: 10, fill: '#999' }}
                  className="text-xs"
                  tickLine={false}
                />
                <Tooltip content={<CustomTooltip />} />
                <Radar
                  name={t('redteam.score')}
                  dataKey="score"
                  stroke="#667eea"
                  fill="#667eea"
                  fillOpacity={0.3}
                  strokeWidth={2}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RadarChartComponent;
