import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { env } from '../config/env';

interface WelcomeAnimationProps {
  onComplete: () => void;
}

const WelcomeAnimation: React.FC<WelcomeAnimationProps> = ({ onComplete }) => {
  const { t } = useTranslation();
  const [isVisible, setIsVisible] = useState(true);
  const [animationStarted, setAnimationStarted] = useState(false);

  useEffect(() => {
    const startTimer = setTimeout(() => {
      setAnimationStarted(true);
    }, 100);

    const fadeTimer = setTimeout(() => {
      setIsVisible(false);
    }, 2200);

    const completeTimer = setTimeout(() => {
      onComplete();
    }, 2700);

    return () => {
      clearTimeout(startTimer);
      clearTimeout(fadeTimer);
      clearTimeout(completeTimer);
    };
  }, [onComplete]);

  return (
    <div
      className={`fixed inset-0 z-50 flex items-center justify-center transition-opacity duration-500 ${
        isVisible ? 'opacity-100' : 'opacity-0'
      }`}
      style={{ background: 'linear-gradient(135deg, #f8f9ff 0%, #e1e0ff 50%, #faf7ff 100%)' }}
    >
      {/* Animated Mesh Gradient Background */}
      <div className="absolute inset-0 overflow-hidden" style={{ zIndex: 0 }}>
        <div
          className="absolute"
          style={{
            width: '150vmax',
            height: '150vmax',
            top: '-25vmax',
            left: '-25vmax',
            backgroundImage: 'radial-gradient(circle closest-side, rgba(93, 95, 239, 0.18), transparent)',
            animation: 'welcomeMeshMove 20s infinite linear',
            opacity: 0.8,
          }}
        />
        <div
          className="absolute"
          style={{
            width: '150vmax',
            height: '150vmax',
            top: '-25vmax',
            left: '-25vmax',
            backgroundImage: 'radial-gradient(circle closest-side, rgba(67, 67, 213, 0.15), transparent)',
            animation: 'welcomeMeshMove 30s infinite linear reverse',
            opacity: 0.8,
          }}
        />
        {/* Background Pulsing Depth */}
        <div
          className="w-full h-full"
          style={{
            background: 'radial-gradient(ellipse at center, rgba(93, 95, 239, 0.2), transparent, transparent)',
            animation: 'welcomePulseBg 8s ease-in-out infinite alternate',
            opacity: 0.5,
          }}
        />
      </div>

      {/* Central Content */}
      <main className="relative z-10 flex items-center justify-center w-full px-8 select-none">
        <div
          className="text-center"
          style={{
            animation: animationStarted ? 'welcomePremiumReveal 1.8s cubic-bezier(0.19, 1, 0.22, 1) forwards' : 'none',
            opacity: 0,
            filter: 'blur(15px)',
            transform: 'translateY(10px) scale(0.98)',
          }}
        >
          {/* Background Glow */}
          <div
            className="absolute inset-0 rounded-full"
            style={{
              background: 'rgba(93, 95, 239, 0.05)',
              filter: 'blur(100px)',
              transform: 'scale(1.5)',
              zIndex: -1,
            }}
          />
          {/* Text Layout: flex row on md+, column on mobile */}
          <h1
            className="welcome-text-layout"
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              textShadow: '0 10px 30px rgba(93, 95, 239, 0.15)',
              letterSpacing: '-0.02em',
            }}
          >
            <span
              style={{
                fontSize: 'clamp(24px, 4vw, 56px)',
                fontWeight: 500,
                color: '#5a5e68',
                opacity: 0.8,
              }}
            >
              {t('floatingInputArea.welcome.animation.welcomeText')}
            </span>
            <span
              className="welcome-brand-text"
              style={{
                fontFamily: 'tencentSans',
                fontSize: 'clamp(36px, 7vw, 80px)',
                fontWeight: 800,
                background: 'linear-gradient(135deg, #4343d5 0%, #5d5fef 50%, #4345d1 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text',
                letterSpacing: '-0.04em',
                position: 'relative',
              }}
            >
              {t(`floatingInputArea.welcome.animation.appName-${env.VITE_APP_ENV}`)}
            </span>
          </h1>
        </div>
      </main>

      {/* Inline keyframes */}
      <style>{`
        @keyframes welcomeMeshMove {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        @keyframes welcomePremiumReveal {
          0% {
            opacity: 0;
            filter: blur(15px);
            transform: translateY(10px) scale(0.98);
          }
          100% {
            opacity: 1;
            filter: blur(0);
            transform: translateY(0) scale(1);
          }
        }
        @keyframes welcomePulseBg {
          0% { opacity: 0.4; transform: scale(1); }
          100% { opacity: 0.7; transform: scale(1.08); }
        }
        @keyframes welcomeUnderlineGrow {
          to { width: 40%; }
        }
        .welcome-brand-text::after {
          content: '';
          position: absolute;
          bottom: -8px;
          left: 50%;
          width: 0;
          height: 2px;
          background: linear-gradient(90deg, transparent, #5d5fef, transparent);
          transform: translateX(-50%);
          animation: welcomeUnderlineGrow 2.5s cubic-bezier(0.19, 1, 0.22, 1) 0.5s forwards;
        }
        @media (min-width: 768px) {
          .welcome-text-layout {
            flex-direction: row !important;
            gap: 24px !important;
            align-items: baseline !important;
          }
        }
      `}</style>
    </div>
  );
};

export default WelcomeAnimation;
