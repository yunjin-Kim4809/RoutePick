import React, { useState, useEffect } from 'react';
import { X, ArrowRight, ArrowLeft, Calendar as CalendarIcon, MapPin, Users, Footprints, Sparkles, Train, Bus, Car, Plus, ChevronLeft, ChevronRight, MoreHorizontal } from 'lucide-react';

interface TripPlannerProps {
  isOpen: boolean;
  onClose: () => void;
}

interface FormData {
  theme: string;
  location: string;
  groupSize: string;
  startDate: string;
  endDate: string;
  visitTime: string;
  transportation: string[];
  customTransport: string; // Store custom transport input separately
}

const steps = [
  { id: 'theme', title: '여행 테마', question: '어떤 여행을 계획하고 계신가요?' },
  { id: 'location', title: '지역', question: '어디로 떠나시나요?' },
  { id: 'groupSize', title: '여행 인원', question: '함께하는 인원은 몇 명인가요?' },
  { id: 'date', title: '방문 일자', question: '일정이 어떻게 되시나요?' },
  { id: 'visitTime', title: '방문 시간', question: '선호하는 시간대가 있으신가요?' },
  { id: 'transportation', title: '이동 수단', question: '주로 어떻게 이동하시나요?' },
  { id: 'review', title: '입력 확인', question: '이대로 일정을 생성할까요?' },
];

const TripPlanner: React.FC<TripPlannerProps> = ({ isOpen, onClose }) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [isCompleted, setIsCompleted] = useState(false);
  
  // Custom states for UI logic
  const [isGroupSizeOther, setIsGroupSizeOther] = useState(false);
  const [isTransportOther, setIsTransportOther] = useState(false);
  
  // Calendar State
  const [currentMonth, setCurrentMonth] = useState(new Date());

  const [formData, setFormData] = useState<FormData>({
    theme: '',
    location: '',
    groupSize: '',
    startDate: '',
    endDate: '',
    visitTime: '',
    transportation: [],
    customTransport: '',
  });

  // Reset state when opened
  useEffect(() => {
    if (isOpen) {
      setCurrentStep(0);
      setIsLoading(false);
      setIsCompleted(false);
      setIsGroupSizeOther(false);
      setIsTransportOther(false);
      setFormData({
        theme: '',
        location: '',
        groupSize: '',
        startDate: '',
        endDate: '',
        visitTime: '',
        transportation: [],
        customTransport: '',
      });
      setCurrentMonth(new Date());
    }
  }, [isOpen]);

  // Enter 키로 다음 단계 이동 (review 단계에서만)
  useEffect(() => {
    if (!isOpen) return;
    
    const handleKeyDown = (e: KeyboardEvent) => {
      // review 단계에서만 Enter 키로 제출
      if (currentStep === steps.length - 1 && e.key === 'Enter') {
        handleNext();
      }
    };

    if (currentStep === steps.length - 1) {
      window.addEventListener('keydown', handleKeyDown);
      return () => {
        window.removeEventListener('keydown', handleKeyDown);
      };
    }
  }, [isOpen, currentStep]);

  const handleNext = async () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(prev => prev + 1);
    } else {
        setIsLoading(true);
      try {
        // 1. Flask 서버에 데이터 전송
        const response = await fetch('http://127.0.0.1:5000/api/create-trip', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(formData),
        });

        if (!response.ok) {
          throw new Error('서버에서 오류가 발생했습니다.');
        }

        const data = await response.json();
        const { taskId } = data;

        // 2. 작업이 완료될 때까지 2초마다 상태 확인 (Polling)
        const pollStatus = setInterval(async () => {
          try {
            const statusResponse = await fetch(`http://127.0.0.1:5000/status/${taskId}`);
            const statusData = await statusResponse.json();

            if (statusData.done) {
              clearInterval(pollStatus); // 상태 확인 중단
              setIsLoading(false);

              if (statusData.success) {
                // 3. 성공 시, chat-map 페이지로 이동
                window.location.href = `http://127.0.0.1:5000/chat-map/${taskId}`;
              } else {
                // 4. 실패 시, 에러 처리 (여기서는 간단히 alert)
                alert(`여행 생성 실패: ${statusData.error || '알 수 없는 오류'}`);
                onClose(); // 모달 닫기
              }
            }
          } catch (error) {
            clearInterval(pollStatus);
            setIsLoading(false);
            alert('상태 확인 중 오류가 발생했습니다.');
            onClose();
          }
        }, 2000); // 2초 간격으로 확인

      } catch (error) {
        setIsLoading(false);
        alert('여행 계획 생성 요청에 실패했습니다.');
        console.error("API Error:", error);
      }
    }
  };

  const handleBack = () => {
    if (currentStep > 0) {
      setCurrentStep(prev => prev - 1);
    }
  };

  // Transportation Toggle Logic
  const toggleTransport = (mode: string) => {
    if (mode === '기타') {
        setIsTransportOther(!isTransportOther);
        // Clear custom transport text if unchecking
        if (isTransportOther) {
             setFormData(prev => ({...prev, customTransport: ''}));
        }
        return;
    }

    setFormData(prev => {
      const exists = prev.transportation.includes(mode);
      return {
        ...prev,
        transportation: exists 
          ? prev.transportation.filter(t => t !== mode)
          : [...prev.transportation, mode]
      };
    });
  };

  // Group Size Logic
  const handleGroupSizeSelect = (value: string) => {
      if (value === '4명+') {
          setIsGroupSizeOther(true);
          setFormData(prev => ({ ...prev, groupSize: '' })); // Clear specific number to force input
      } else {
          setIsGroupSizeOther(false);
          setFormData(prev => ({ ...prev, groupSize: value }));
      }
  };

  // --- Calendar Logic ---
  const getDaysInMonth = (date: Date) => {
    return new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate();
  };
  
  const getFirstDayOfMonth = (date: Date) => {
    return new Date(date.getFullYear(), date.getMonth(), 1).getDay();
  };

  const handleDateClick = (day: number) => {
    const clickedDate = new Date(currentMonth.getFullYear(), currentMonth.getMonth(), day);
    // Format to YYYY-MM-DD (local time)
    const offset = clickedDate.getTimezoneOffset() * 60000;
    const dateStr = new Date(clickedDate.getTime() - offset).toISOString().split('T')[0];

    if (!formData.startDate || (formData.startDate && formData.endDate)) {
        // Start new selection
        setFormData(prev => ({ ...prev, startDate: dateStr, endDate: '' }));
    } else {
        // Select end date
        if (new Date(dateStr) < new Date(formData.startDate)) {
            // If clicked before start date, make it new start date
             setFormData(prev => ({ ...prev, startDate: dateStr, endDate: '' }));
        } else {
             setFormData(prev => ({ ...prev, endDate: dateStr }));
        }
    }
  };

  const changeMonth = (delta: number) => {
      const newDate = new Date(currentMonth);
      newDate.setMonth(newDate.getMonth() + delta);
      setCurrentMonth(newDate);
  };

  const renderCalendar = () => {
    const daysInMonth = getDaysInMonth(currentMonth);
    const firstDay = getFirstDayOfMonth(currentMonth);
    const days = [];

    // Empty cells for previous month
    for (let i = 0; i < firstDay; i++) {
        days.push(<div key={`empty-${i}`} className="h-10 w-10"></div>);
    }

    // Days
    for (let day = 1; day <= daysInMonth; day++) {
        const date = new Date(currentMonth.getFullYear(), currentMonth.getMonth(), day);
        const offset = date.getTimezoneOffset() * 60000;
        const dateStr = new Date(date.getTime() - offset).toISOString().split('T')[0];
        
        let isSelected = false;
        let isRange = false;
        let isStart = false;
        let isEnd = false;

        if (formData.startDate === dateStr) {
            isSelected = true;
            isStart = true;
        }
        if (formData.endDate === dateStr) {
            isSelected = true;
            isEnd = true;
        }
        if (formData.startDate && formData.endDate) {
            if (dateStr > formData.startDate && dateStr < formData.endDate) {
                isRange = true;
            }
        }

        days.push(
            <button
                key={day}
                onClick={() => handleDateClick(day)}
                className={`h-10 w-10 flex items-center justify-center rounded-full text-sm transition-all
                    ${isSelected ? 'bg-black text-white font-bold' : 'hover:bg-gray-100'}
                    ${isRange ? 'bg-gray-100 text-black rounded-none w-full' : ''}
                    ${isStart && formData.endDate ? 'rounded-r-none' : ''}
                    ${isEnd && formData.startDate ? 'rounded-l-none' : ''}
                `}
            >
                {day}
            </button>
        );
    }
    return days;
  };

  if (!isOpen) return null;

  // --------------------------------------------------------------------------
  // LOADING
  // --------------------------------------------------------------------------
  if (isLoading) {
    return (
      <div className="fixed inset-0 z-[60] bg-white flex flex-col items-center justify-center">
        <div className="relative">
          <div className="absolute inset-0 bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400 blur-xl opacity-20 animate-pulse rounded-full"></div>
          <Sparkles className="w-16 h-16 text-black animate-spin-slow relative z-10" />
        </div>
        <h2 className="mt-8 text-3xl font-serif font-bold text-black animate-pulse">여행 경로를 설계하는 중입니다...</h2>
        <p className="mt-4 text-gray-500 font-sans text-sm tracking-widest uppercase">AI가 최적의 루트를 분석하고 있습니다</p>
      </div>
    );
  }

  // --------------------------------------------------------------------------
  // COMPLETED
  // --------------------------------------------------------------------------
  if (isCompleted) {
    return (
      <div className="fixed inset-0 z-[60] bg-black text-white flex flex-col items-center justify-center text-center px-6">
        <h2 className="text-4xl md:text-6xl font-serif font-bold mb-6">여행 준비 완료.</h2>
        <p className="text-gray-400 mb-8 max-w-md">나만의 맞춤형 경로가 생성되었습니다. 이제 떠나볼까요?</p>
        <button onClick={onClose} className="px-8 py-3 bg-white text-black font-bold rounded-full hover:bg-gray-200 transition-colors">
            지도 보기
        </button>
      </div>
    );
  }

  // --------------------------------------------------------------------------
  // WIZARD FORM
  // --------------------------------------------------------------------------
  const stepData = steps[currentStep];

  return (
    <div className="fixed inset-0 z-[60] bg-white flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-6 md:px-12 py-6 border-b border-gray-100">
        <div className="text-sm font-bold tracking-widest uppercase text-gray-400">
          Step {currentStep + 1} / {steps.length}
        </div>
        <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-full transition-colors">
          <X className="w-6 h-6 text-black" />
        </button>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col justify-center px-6 md:px-12 max-w-4xl mx-auto w-full overflow-y-auto">
        <div className="mb-8 animate-fade-in-up">
            <span className="text-route-accent font-serif italic text-xl mb-2 block">{stepData.title}</span>
            <h2 className="text-3xl md:text-5xl font-bold text-black leading-tight word-keep-all">
            {stepData.question}
            </h2>
            
            {stepData.id === 'theme' && (
              <p className="mt-4 text-gray-400 text-sm md:text-base font-medium">
                Tip: 지역, 날씨, 여행 목적 등을 자세하게 입력하면 좋아요!
              </p>
            )}
        </div>

        <div className="min-h-[200px] animate-fade-in-up delay-100 pb-10">
            {/* STEP 1: THEME */}
            {stepData.id === 'theme' && (
                <div className="w-full">
                    <input 
                        type="text" 
                        autoFocus
                        placeholder="" 
                        value={formData.theme}
                        onChange={(e) => setFormData({...formData, theme: e.target.value})}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' && formData.theme.trim()) {
                                handleNext();
                            }
                        }}
                        className="w-full text-2xl md:text-4xl border-b-2 border-gray-200 py-4 focus:border-black focus:outline-none bg-transparent transition-colors"
                    />
                    <div className="mt-6 text-gray-400 text-sm font-medium">
                        ex) 여자친구와 비 오는 날 강남 실내 데이트, 가족과의 잔잔한 전주 여행
                    </div>
                </div>
            )}

            {/* STEP 2: LOCATION */}
            {stepData.id === 'location' && (
                <div className="w-full">
                    <input 
                        type="text" 
                        autoFocus
                        placeholder="" 
                        value={formData.location}
                        onChange={(e) => setFormData({...formData, location: e.target.value})}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' && formData.location.trim()) {
                                handleNext();
                            }
                        }}
                        className="w-full text-2xl md:text-4xl border-b-2 border-gray-200 py-4 focus:border-black focus:outline-none bg-transparent transition-colors"
                    />
                    <div className="mt-6 text-gray-400 text-sm font-medium">
                        ex) 서울 종로, 경기도 고양시
                    </div>
                </div>
            )}

            {/* STEP 3: GROUP SIZE */}
            {stepData.id === 'groupSize' && (
                <div className="space-y-6">
                    <div className="flex flex-wrap gap-4">
                        {['1명', '2명', '3명', '4명+'].map((num) => {
                            const isSelected = !isGroupSizeOther ? formData.groupSize === num : (num === '4명+' && isGroupSizeOther);
                            
                            return (
                                <button
                                    key={num}
                                    onClick={() => handleGroupSizeSelect(num)}
                                    className={`w-24 h-24 md:w-32 md:h-32 rounded-full text-lg md:text-xl font-bold border transition-all duration-300 flex items-center justify-center ${
                                        isSelected
                                        ? 'bg-black text-white border-black scale-110' 
                                        : 'bg-white text-black border-gray-200 hover:border-black'
                                    }`}
                                >
                                    {num}
                                </button>
                            );
                        })}
                    </div>
                    {isGroupSizeOther && (
                         <div className="animate-fade-in-up mt-6 w-full max-w-lg">
                            <label className="block text-xs text-gray-400 mb-2 font-bold uppercase tracking-widest">상세 인원 입력</label>
                            <input 
                                type="text"
                                autoFocus
                                placeholder="예: 6명"
                                value={formData.groupSize === '4명+' ? '' : formData.groupSize}
                                onChange={(e) => setFormData({...formData, groupSize: e.target.value})}
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter' && formData.groupSize.trim()) {
                                        handleNext();
                                    }
                                }}
                                className="w-full text-xl md:text-2xl border-b-2 border-gray-200 py-3 focus:border-black focus:outline-none bg-transparent transition-colors"
                            />
                        </div>
                    )}
                </div>
            )}

            {/* STEP 4: DATE (Custom Calendar) */}
            {stepData.id === 'date' && (
                <div className="flex flex-col items-center">
                    {/* Date Display */}
                    <div className="flex w-full max-w-lg justify-between mb-8 gap-4">
                         <div className="w-1/2 p-4 border rounded-xl bg-gray-50 flex flex-col">
                            <span className="text-xs text-gray-400 font-bold uppercase mb-1">시작일</span>
                            <span className="text-lg font-bold">{formData.startDate || '-'}</span>
                         </div>
                         <div className="w-1/2 p-4 border rounded-xl bg-gray-50 flex flex-col">
                            <span className="text-xs text-gray-400 font-bold uppercase mb-1">종료일</span>
                            <span className="text-lg font-bold">{formData.endDate || '-'}</span>
                         </div>
                    </div>

                    {/* Calendar UI */}
                    <div className="w-full max-w-sm border border-gray-200 rounded-2xl p-6 bg-white shadow-sm">
                        <div className="flex items-center justify-between mb-6">
                            <button onClick={() => changeMonth(-1)} className="p-2 hover:bg-gray-100 rounded-full"><ChevronLeft className="w-5 h-5" /></button>
                            <span className="text-lg font-bold">
                                {currentMonth.getFullYear()}년 {String(currentMonth.getMonth() + 1).padStart(2, '0')}월
                            </span>
                            <button onClick={() => changeMonth(1)} className="p-2 hover:bg-gray-100 rounded-full"><ChevronRight className="w-5 h-5" /></button>
                        </div>
                        
                        <div className="grid grid-cols-7 gap-1 text-center mb-2">
                            {['일', '월', '화', '수', '목', '금', '토'].map(d => (
                                <div key={d} className="text-xs text-gray-400 font-bold py-2">{d}</div>
                            ))}
                        </div>
                        
                        <div className="grid grid-cols-7 gap-y-1 gap-x-0 justify-items-center">
                            {renderCalendar()}
                        </div>
                    </div>
                </div>
            )}

            {/* STEP 5: TIME */}
            {stepData.id === 'visitTime' && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    {[
                        { label: '오전', time: '08:00 - 12:00' },
                        { label: '오후', time: '12:00 - 18:00' },
                        { label: '저녁', time: '18:00 - 24:00' },
                        { label: '하루종일', time: '00:00 - 24:00' }
                    ].map((item) => (
                        <button
                            key={item.label}
                            onClick={() => setFormData({...formData, visitTime: item.label})}
                            className={`py-6 px-6 rounded-xl border text-left transition-all duration-300 ${
                                formData.visitTime === item.label 
                                ? 'bg-black text-white border-black' 
                                : 'bg-white text-black border-gray-200 hover:border-black'
                            }`}
                        >
                            <span className="block text-2xl font-bold mb-1">{item.label}</span>
                            <span className={`text-xs ${formData.visitTime === item.label ? 'opacity-80' : 'opacity-50'}`}>
                                {item.time}
                            </span>
                        </button>
                    ))}
                </div>
            )}

            {/* STEP 6: TRANSPORTATION */}
            {stepData.id === 'transportation' && (
                <div className="space-y-6">
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                        {[
                            { id: 'Walk', label: '도보', icon: Footprints },
                            { id: 'Subway', label: '지하철', icon: Train },
                            { id: 'Bus', label: '버스', icon: Bus },
                            { id: 'Car', label: '자동차', icon: Car },
                            { id: 'Other', label: '기타', icon: MoreHorizontal },
                        ].map((mode) => {
                            const isSelected = mode.label === '기타' 
                                ? isTransportOther 
                                : formData.transportation.includes(mode.label);

                            return (
                                <button
                                    key={mode.id}
                                    onClick={() => toggleTransport(mode.label)}
                                    className={`aspect-square rounded-xl border flex flex-col items-center justify-center gap-4 transition-all duration-300 ${
                                        isSelected
                                        ? 'bg-black text-white border-black' 
                                        : 'bg-white text-black border-gray-200 hover:border-black'
                                    }`}
                                >
                                    <mode.icon className="w-8 h-8" />
                                    <span className="font-medium text-lg">{mode.label}</span>
                                </button>
                            )
                        })}
                    </div>
                    {isTransportOther && (
                        <div className="animate-fade-in-up mt-6 w-full">
                            <label className="block text-xs text-gray-400 mb-2 font-bold uppercase tracking-widest">기타 이동 수단 입력</label>
                            <input 
                                type="text" 
                                autoFocus
                                placeholder="예: 자전거, 킥보드"
                                value={formData.customTransport}
                                onChange={(e) => setFormData({...formData, customTransport: e.target.value})}
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter' && formData.customTransport.trim()) {
                                        handleNext();
                                    }
                                }}
                                className="w-full text-xl md:text-2xl border-b-2 border-gray-200 py-3 focus:border-black focus:outline-none bg-transparent transition-colors"
                            />
                        </div>
                    )}
                </div>
            )}

            {/* STEP 7: REVIEW */}
            {stepData.id === 'review' && (
                <div className="bg-gray-50 p-8 rounded-2xl border border-gray-100">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-y-8 gap-x-12">
                        <div>
                            <span className="text-xs text-gray-400 uppercase tracking-widest block mb-1">여행 테마 (Theme)</span>
                            <p className="text-xl font-medium break-keep">{formData.theme || '입력되지 않음'}</p>
                        </div>
                        <div>
                            <span className="text-xs text-gray-400 uppercase tracking-widest block mb-1">지역 (Location)</span>
                            <p className="text-xl font-medium break-keep">{formData.location || '입력되지 않음'}</p>
                        </div>
                        <div>
                            <span className="text-xs text-gray-400 uppercase tracking-widest block mb-1">여행 인원 (Travelers)</span>
                            <p className="text-xl font-medium">{formData.groupSize || '입력되지 않음'}</p>
                        </div>
                         <div>
                            <span className="text-xs text-gray-400 uppercase tracking-widest block mb-1">일정 (Schedule)</span>
                            <p className="text-xl font-medium">
                                {formData.startDate} {formData.endDate ? `~ ${formData.endDate}` : ''}
                                <span className="text-gray-400 text-base ml-2">({formData.visitTime})</span>
                            </p>
                        </div>
                         <div className="md:col-span-2">
                            <span className="text-xs text-gray-400 uppercase tracking-widest block mb-1">이동 수단 (Transport)</span>
                            <div className="flex gap-2 mt-1 flex-wrap">
                                {formData.transportation.map(t => (
                                    <span key={t} className="px-4 py-1.5 bg-white border border-gray-200 rounded-full text-sm font-medium">{t}</span>
                                ))}
                                {isTransportOther && formData.customTransport && (
                                     <span className="px-4 py-1.5 bg-white border border-gray-200 rounded-full text-sm font-medium">{formData.customTransport}</span>
                                )}
                                {formData.transportation.length === 0 && (!isTransportOther || !formData.customTransport) && (
                                    <span className="text-gray-400 italic">선택안함</span>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
      </div>

      {/* Footer / Navigation */}
      <div className="px-6 md:px-12 py-8 border-t border-gray-100 flex justify-between items-center bg-white/80 backdrop-blur-sm">
        <button 
            onClick={handleBack} 
            disabled={currentStep === 0}
            className={`flex items-center gap-2 text-sm font-bold uppercase tracking-widest transition-opacity hover:opacity-100 ${currentStep === 0 ? 'opacity-0 pointer-events-none' : 'opacity-40'}`}
        >
            <ArrowLeft className="w-4 h-4" /> 이전 (Back)
        </button>

        <button 
            onClick={handleNext}
            className="group flex items-center gap-3 bg-black text-white px-8 py-4 rounded-full font-bold uppercase tracking-widest text-sm hover:bg-gray-800 transition-all shadow-lg hover:shadow-xl"
        >
            {currentStep === steps.length - 1 ? '여행 생성하기' : '다음 단계'}
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
        </button>
      </div>
    </div>
  );
};

export default TripPlanner;