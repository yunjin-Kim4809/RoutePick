import React, { useEffect, useState } from 'react';

interface HeroProps {
  onPlanClick: () => void;
}

const Hero: React.FC<HeroProps> = ({ onPlanClick }) => {

  // Re-init Unicorn Studio if needed when component mounts
  useEffect(() => {
    // @ts-ignore
    if (window.UnicornStudio) {
        // @ts-ignore
      window.UnicornStudio.init();
    }
  }, []);

  return (
    <section className="relative w-full h-screen flex flex-col items-center justify-end pb-8 overflow-hidden bg-black">
      {/* Unicorn Studio Canvas Layer - Full Opacity */}
      <div className="absolute inset-0 w-full h-full opacity-100">
        <div 
          data-us-project="Z3dNYdB7qGp7TyW943FZ" 
          style={{ width: '100%', height: '100%' }}
        ></div>
      </div>

      {/* Overlay Content */}
      <div className="relative z-20 text-center px-4 max-w-5xl mx-auto">
        <div className="animate-fade-in-up delay-200">
             <div className="relative inline-flex group">
                <div className="absolute transition-all duration-1000 opacity-70 -inset-px bg-gradient-to-r from-[#44BCFF] via-[#FF44EC] to-[#FF675E] rounded-full blur-lg group-hover:opacity-100 group-hover:-inset-1 group-hover:duration-200 animate-tilt"></div>
                <button 
                    onClick={onPlanClick}
                    className="relative inline-flex items-center justify-center px-8 py-4 text-sm font-bold text-white transition-all duration-200 bg-black font-sans uppercase tracking-widest border border-white/20 rounded-full focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-900 bg-opacity-90 backdrop-blur-sm cursor-pointer"
                >
                    Discover Your Route
                </button>
            </div>
        </div>
      </div>
    </section>
  );
};


export default Hero;