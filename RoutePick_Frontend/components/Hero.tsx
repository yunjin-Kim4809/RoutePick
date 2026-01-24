import React, { useEffect, useState } from 'react';
import PlaceSearchModal from './PlaceSearchModal';

interface HeroProps {
  onPlanClick: () => void;
}

const Hero: React.FC<HeroProps> = ({ onPlanClick }) => {
  const [isPlaceModalOpen, setIsPlaceModalOpen] = useState(false);

  // Re-init Unicorn Studio if needed when component mounts
  useEffect(() => {
    // @ts-ignore
    if (window.UnicornStudio) {
        // @ts-ignore
      window.UnicornStudio.init();
    }
  }, []);

  return (
    <>
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
          <div className="animate-fade-in-up delay-200 flex flex-col sm:flex-row items-center justify-center gap-4">
            <button 
                onClick={onPlanClick}
                className="inline-flex items-center justify-center px-8 py-4 text-sm font-bold text-white transition-all duration-200 bg-black font-sans uppercase tracking-widest border border-white/20 rounded-full focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-900 bg-opacity-90 backdrop-blur-sm cursor-pointer"
            >
                Discover Your Route
            </button>
            <button 
                onClick={() => setIsPlaceModalOpen(true)}
                className="inline-flex items-center justify-center px-8 py-4 text-sm font-bold text-white transition-all duration-200 bg-black font-sans uppercase tracking-widest border border-white/20 rounded-full focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-900 bg-opacity-90 backdrop-blur-sm cursor-pointer"
            >
                Add Your Place
            </button>
          </div>
        </div>
      </section>
      <PlaceSearchModal isOpen={isPlaceModalOpen} onClose={() => setIsPlaceModalOpen(false)} />
    </>
  );
};

export default Hero;