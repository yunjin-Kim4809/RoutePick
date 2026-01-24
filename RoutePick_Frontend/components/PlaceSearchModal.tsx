import React, { useState, useEffect } from 'react';
import { X, Search, MapPin, Star, Plus, Check, CheckCircle, AlertCircle, Trash2 } from 'lucide-react';

interface Place {
  name: string;
  address: string;
  rating?: number;
  category?: string;
  place_id?: string;
  lat?: number;
  lng?: number;
}

interface PlaceSearchModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface Toast {
  id: string;
  message: string;
  type: 'success' | 'error' | 'info';
}

interface ConfirmDialog {
  isOpen: boolean;
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
}

const PlaceSearchModal: React.FC<PlaceSearchModalProps> = ({ isOpen, onClose }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<Place[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [savedPlaces, setSavedPlaces] = useState<Place[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [confirmDialog, setConfirmDialog] = useState<ConfirmDialog>({
    isOpen: false,
    message: '',
    onConfirm: () => {},
    onCancel: () => {}
  });

  // 저장된 장소 목록 불러오기
  useEffect(() => {
    if (isOpen) {
      loadSavedPlaces();
    }
  }, [isOpen]);

  // 애니메이션 CSS 추가
  useEffect(() => {
    const style = document.createElement('style');
    style.textContent = `
      @keyframes slideInRight {
        from {
          transform: translateX(100%);
          opacity: 0;
        }
        to {
          transform: translateX(0);
          opacity: 1;
        }
      }
      @keyframes scaleIn {
        from {
          transform: scale(0.9);
          opacity: 0;
        }
        to {
          transform: scale(1);
          opacity: 1;
        }
      }
    `;
    document.head.appendChild(style);
    return () => {
      document.head.removeChild(style);
    };
  }, []);

  const loadSavedPlaces = async () => {
    try {
      const response = await fetch('http://127.0.0.1:5000/api/saved-places');
      if (response.ok) {
        const data = await response.json();
        setSavedPlaces(data.places || []);
      }
    } catch (error) {
      console.error('저장된 장소 불러오기 실패:', error);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;

    setIsSearching(true);
    try {
      const response = await fetch('http://127.0.0.1:5000/api/search-place', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: searchQuery })
      });

      if (response.ok) {
        const data = await response.json();
        setSearchResults(data.places || []);
      } else {
        showToast('장소 검색에 실패했습니다.', 'error');
      }
    } catch (error) {
      console.error('검색 오류:', error);
      showToast('장소 검색 중 오류가 발생했습니다.', 'error');
    } finally {
      setIsSearching(false);
    }
  };

  const handleSavePlace = async (place: Place) => {
    setIsLoading(true);
    try {
      const response = await fetch('http://127.0.0.1:5000/api/save-place', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(place)
      });

      if (response.ok) {
        await loadSavedPlaces();
        showToast('장소가 저장되었습니다! 코스 생성 시 우선적으로 선정됩니다.', 'success');
      } else {
        const error = await response.json();
        showToast(error.error || '장소 저장에 실패했습니다.', 'error');
      }
    } catch (error) {
      console.error('저장 오류:', error);
      showToast('장소 저장 중 오류가 발생했습니다.', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRemovePlace = async (placeId: string) => {
    const confirmed = await showConfirm('이 장소를 삭제하시겠습니까?');
    if (!confirmed) return;

    setIsLoading(true);
    try {
      const response = await fetch(`http://127.0.0.1:5000/api/saved-places/${placeId}`, {
        method: 'DELETE'
      });

      if (response.ok) {
        await loadSavedPlaces();
        showToast('장소가 삭제되었습니다.', 'success');
      } else {
        showToast('장소 삭제에 실패했습니다.', 'error');
      }
    } catch (error) {
      console.error('삭제 오류:', error);
      showToast('장소 삭제 중 오류가 발생했습니다.', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const isPlaceSaved = (placeId?: string) => {
    if (!placeId) return false;
    return savedPlaces.some(p => p.place_id === placeId);
  };

  const showToast = (message: string, type: 'success' | 'error' | 'info' = 'info') => {
    const id = Date.now().toString();
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(toast => toast.id !== id));
    }, 3000);
  };

  const showConfirm = (message: string): Promise<boolean> => {
    return new Promise((resolve) => {
      setConfirmDialog({
        isOpen: true,
        message,
        onConfirm: () => {
          setConfirmDialog({ isOpen: false, message: '', onConfirm: () => {}, onCancel: () => {} });
          resolve(true);
        },
        onCancel: () => {
          setConfirmDialog({ isOpen: false, message: '', onConfirm: () => {}, onCancel: () => {} });
          resolve(false);
        }
      });
    });
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Toast Notifications */}
      <div className="fixed top-4 right-4 z-[60] space-y-2">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`flex items-center gap-3 px-4 py-3 rounded-xl shadow-2xl backdrop-blur-sm min-w-[300px] transform transition-all duration-300 ease-out ${
              toast.type === 'success'
                ? 'bg-green-500/95 text-white'
                : toast.type === 'error'
                ? 'bg-red-500/95 text-white'
                : 'bg-blue-500/95 text-white'
            }`}
            style={{
              animation: 'slideInRight 0.3s ease-out',
            } as React.CSSProperties}
          >
            {toast.type === 'success' ? (
              <CheckCircle className="w-5 h-5 flex-shrink-0" />
            ) : toast.type === 'error' ? (
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
            ) : (
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
            )}
            <p className="flex-1 text-sm font-medium">{toast.message}</p>
            <button
              onClick={() => setToasts(prev => prev.filter(t => t.id !== toast.id))}
              className="flex-shrink-0 hover:opacity-80 transition-opacity"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        ))}
      </div>

      {/* Confirm Dialog */}
      {confirmDialog.isOpen && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div 
            className="bg-white rounded-2xl shadow-2xl p-6 max-w-md w-full mx-4 transform transition-all duration-200 ease-out"
            style={{
              animation: 'scaleIn 0.2s ease-out',
            } as React.CSSProperties}
          >
            <div className="flex items-start gap-4 mb-6">
              <div className="flex-shrink-0 w-12 h-12 rounded-full bg-red-100 flex items-center justify-center">
                <Trash2 className="w-6 h-6 text-red-600" />
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-gray-900 mb-2">확인 필요</h3>
                <p className="text-gray-600">{confirmDialog.message}</p>
              </div>
            </div>
            <div className="flex gap-3 justify-end">
              <button
                onClick={confirmDialog.onCancel}
                className="px-6 py-2.5 rounded-lg border border-gray-300 text-gray-700 font-medium hover:bg-gray-50 transition-colors"
              >
                취소
              </button>
              <button
                onClick={confirmDialog.onConfirm}
                className="px-6 py-2.5 rounded-lg bg-red-500 text-white font-medium hover:bg-red-600 transition-colors"
              >
                삭제
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="relative w-full max-w-4xl max-h-[90vh] bg-white rounded-2xl shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 bg-gradient-to-r from-white to-gray-50">
          <h2 className="text-2xl font-bold text-gray-900">Add Your Place</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* Search Section */}
          <div className="mb-6">
            <div className="flex gap-3">
              <div className="flex-1 relative">
                <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                  placeholder="장소 이름 또는 주소를 입력하세요..."
                  className="w-full pl-12 pr-4 py-3 border border-gray-300 rounded-full focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent"
                />
              </div>
              <button
                onClick={handleSearch}
                disabled={isSearching || !searchQuery.trim()}
                className="px-6 py-3 bg-black text-white rounded-full font-semibold hover:bg-gray-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSearching ? '검색 중...' : '검색'}
              </button>
            </div>
          </div>

          {/* Search Results */}
          {searchResults.length > 0 && (
            <div className="mb-8">
              <h3 className="text-lg font-semibold mb-4 text-gray-800">검색 결과</h3>
              <div className="space-y-3">
                {searchResults.map((place, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between p-4 border border-gray-200 rounded-xl hover:border-gray-300 hover:shadow-md transition-all"
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <h4 className="font-semibold text-gray-900">{place.name}</h4>
                        {place.rating && (
                          <div className="flex items-center gap-1 text-yellow-500">
                            <Star className="w-4 h-4 fill-current" />
                            <span className="text-sm">{place.rating}</span>
                          </div>
                        )}
                      </div>
                      <div className="flex items-center gap-2 text-sm text-gray-600">
                        <MapPin className="w-4 h-4" />
                        <span>{place.address}</span>
                      </div>
                      {place.category && (
                        <span className="inline-block mt-2 px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded">
                          {place.category}
                        </span>
                      )}
                    </div>
                    <button
                      onClick={() => handleSavePlace(place)}
                      disabled={isLoading || isPlaceSaved(place.place_id)}
                      className="ml-4 p-2 rounded-full bg-black text-white hover:bg-gray-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isPlaceSaved(place.place_id) ? (
                        <Check className="w-5 h-5" />
                      ) : (
                        <Plus className="w-5 h-5" />
                      )}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Saved Places */}
          <div>
            <h3 className="text-lg font-semibold mb-4 text-gray-800">저장된 장소</h3>
            {savedPlaces.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                <MapPin className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>저장된 장소가 없습니다.</p>
                <p className="text-sm mt-2">장소를 검색하여 추가해보세요!</p>
              </div>
            ) : (
              <div className="space-y-3">
                {savedPlaces.map((place, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between p-4 border border-gray-200 rounded-xl hover:border-gray-300 hover:shadow-md transition-all bg-gray-50"
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <h4 className="font-semibold text-gray-900">{place.name}</h4>
                        {place.rating && (
                          <div className="flex items-center gap-1 text-yellow-500">
                            <Star className="w-4 h-4 fill-current" />
                            <span className="text-sm">{place.rating}</span>
                          </div>
                        )}
                      </div>
                      <div className="flex items-center gap-2 text-sm text-gray-600">
                        <MapPin className="w-4 h-4" />
                        <span>{place.address}</span>
                      </div>
                      {place.category && (
                        <span className="inline-block mt-2 px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded">
                          {place.category}
                        </span>
                      )}
                    </div>
                    <button
                      onClick={() => place.place_id && handleRemovePlace(place.place_id)}
                      disabled={isLoading}
                      className="ml-4 p-2 rounded-full bg-red-500 text-white hover:bg-red-600 transition-colors disabled:opacity-50"
                    >
                      <X className="w-5 h-5" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
      </div>
    </>
  );
};

export default PlaceSearchModal;

