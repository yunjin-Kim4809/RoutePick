import React, { useState } from 'react';
import { Menu, X } from 'lucide-react';
import PlaceSearchModal from './PlaceSearchModal'; // 모달 임포트

interface NavbarProps {
  onPlanClick: () => void;
}

const Navbar: React.FC<NavbarProps> = ({ onPlanClick }) => {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  
  // 모달 상태를 Navbar에서 관리합니다.
  const [isPlaceModalOpen, setIsPlaceModalOpen] = useState(false);

  return (
    <>
      <nav 
        className="fixed top-0 left-0 right-0 z-50 transition-all duration-500 ease-in-out px-6 md:px-12 py-4 bg-white/90 backdrop-blur-md border-b border-gray-200"
      >
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="text-2xl font-serif font-bold tracking-tight text-route-black cursor-pointer">
            RoutePick
          </div>

          {/* Desktop Menu */}
          <div className="hidden md:flex items-center space-x-4 text-sm font-medium uppercase tracking-widest text-route-black">
            {/* Add Your Place 버튼 (스타일 통일) */}
            <button 
              onClick={() => setIsPlaceModalOpen(true)}
              className="px-5 py-2 rounded-full border border-black transition-all hover:bg-black hover:text-white cursor-pointer"
            >
              Add Place
            </button>

            <button 
              onClick={onPlanClick}
              className="px-5 py-2 rounded-full border border-black transition-all hover:bg-black hover:text-white cursor-pointer"
            >
              Plan Trip
            </button>
          </div>

          {/* Mobile Toggle */}
          <button 
            className="md:hidden" 
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          >
            {isMobileMenuOpen ? <X className="text-black" /> : <Menu className="text-black" />}
          </button>
        </div>

        {/* Mobile Menu */}
        {isMobileMenuOpen && (
          <div className="absolute top-full left-0 w-full bg-white text-black py-8 px-6 shadow-xl flex flex-col space-y-4 md:hidden">
             <button 
              onClick={() => {
                setIsMobileMenuOpen(false);
                setIsPlaceModalOpen(true);
              }}
              className="w-full py-3 border border-gray-300 rounded-full text-black font-medium uppercase tracking-widest"
            >
              Add Place
            </button>
            <button 
              onClick={() => {
                setIsMobileMenuOpen(false);
                onPlanClick();
              }}
              className="w-full py-3 bg-black text-white rounded-full font-medium uppercase tracking-widest"
            >
              Plan Trip
            </button>
          </div>
        )}
      </nav>

      {/* Navbar 레벨에서 모달 렌더링 */}
      <PlaceSearchModal isOpen={isPlaceModalOpen} onClose={() => setIsPlaceModalOpen(false)} />
    </>
  );
};

export default Navbar;