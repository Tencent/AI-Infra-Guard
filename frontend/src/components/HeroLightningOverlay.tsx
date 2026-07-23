type LightningBolt = {
  d: string;
  animation: string;
  animationDelay: string;
  stroke?: string;
  strokeWidth?: number;
};
type HeroLightningOverlayProps = {
  className?: string;
};
const lightningBolts: LightningBolt[] = [
  {
    d: 'M85,30 L95,45 L88,50 L98,65',
    animation: 'heroLightningFlash 4s infinite',
    animationDelay: '0.5s',
  },
  {
    d: 'M220,20 L215,35 L225,40 L218,55',
    animation: 'heroLightningFlash 3s infinite',
    animationDelay: '1.2s',
    stroke: '#7dd3fc',
  },
  {
    d: 'M340,40 L330,55 L335,60 L325,75',
    animation: 'heroLightningFlash 5s infinite',
    animationDelay: '2.5s',
    stroke: '#e0f2fe',
  },
  {
    d: 'M60,130 L70,145 L65,150',
    animation: 'heroLightningFlash 2.5s infinite',
    animationDelay: '0.8s',
  },
  {
    d: 'M390,110 L380,125 L385,130 L375,145',
    animation: 'heroLightningFlash 3.5s infinite',
    animationDelay: '1.8s',
    stroke: '#7dd3fc',
  },
  {
    d: 'M130,210 L140,225 L135,230 L145,245',
    animation: 'heroLightningFlash 4.2s infinite',
    animationDelay: '3s',
    stroke: '#e0f2fe',
  },
  {
    d: 'M290,230 L280,245 L285,250 L275,265',
    animation: 'heroLightningFlash 3.8s infinite',
    animationDelay: '0.2s',
  },
  {
    d: 'M190,160 L200,175 L195,180 L205,195',
    animation: 'heroLightningFlash 2.8s infinite',
    animationDelay: '1.5s',
    strokeWidth: 0.8,
  },
  {
    d: 'M140,90 L130,105 L135,110',
    animation: 'heroLightningFlash 3.2s infinite',
    animationDelay: '2.2s',
    stroke: '#bae6fd',
  },
];
const HeroLightningOverlay = ({ className = '' }: HeroLightningOverlayProps) => {
  return (
    <>
      <style>{`
        @keyframes heroLightningFlash {
          0%, 90%, 100% { opacity: 0; }
          92% { opacity: 1; }
          93% { opacity: 0; }
          94% { opacity: 0.6; }
          96% { opacity: 0; }
        }
        .hero-lightning-bolt {
          stroke: #22d3ee;
          stroke-width: 1;
          fill: none;
          opacity: 0;
          filter: drop-shadow(0 0 2px #22d3ee);
        }
      `}</style>
      <svg
        className={`absolute inset-0 w-full h-full pointer-events-none rounded-2xl ${className}`.trim()}
        viewBox='0 0 448 320'
        preserveAspectRatio='none'
      >
        {lightningBolts.map((bolt, index) => {
          return (
            <path
              key={`${bolt.d}-${index}`}
              className='hero-lightning-bolt'
              d={bolt.d}
              style={{
                animation: bolt.animation,
                animationDelay: bolt.animationDelay,
                stroke: bolt.stroke,
                strokeWidth: bolt.strokeWidth,
              }}
            />
          );
        })}
      </svg>
    </>
  );
};
export default HeroLightningOverlay;
