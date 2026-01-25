import React from 'react';

const Philosophy: React.FC = () => {
  return (
    <section className="py-24 md:py-40 px-6 md:px-12 bg-white">
      <div className="max-w-7xl mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-16 items-center">
          
          {/* Left Column: Images Placeholder */}
          <div className="lg:col-span-7">
            <div className="grid grid-cols-2 gap-4 md:gap-8 items-start">
              {/* Image 1 Container */}
              <div className="relative group w-full aspect-[3/4] bg-gray-200 overflow-hidden rounded-lg">
                 {/* 
                    USER TODO: Replace the src below with your image URL. 
                    The hover effect (grayscale to color) is already set up.
                 */}
                 <img 
                  src="/images/거리.jpg" 
                  alt="Philosophy Image 1" 
                  className="absolute inset-0 w-full h-full object-cover transition-all duration-700 group-hover:scale-105 grayscale group-hover:grayscale-0"
                />
              </div>

              {/* Image 2 Container - Staggered layout */}
              <div className="relative group w-full aspect-[3/4] bg-gray-200 overflow-hidden rounded-lg mt-12 md:mt-24">
                 {/* 
                    USER TODO: Replace the src below with your image URL. 
                 */}
                 <img 
                  src="/images/한옥.jpg" 
                  alt="Philosophy Image 2" 
                  className="absolute inset-0 w-full h-full object-cover transition-all duration-700 group-hover:scale-105 grayscale group-hover:grayscale-0"
                />
              </div>
            </div>
          </div>

          {/* Right Column: Text Content */}
          <div className="lg:col-span-5 flex flex-col justify-center lg:pl-12">
            {/* Headline */}
            <h2 className="mb-12 text-black leading-snug">
              <span className="block text-3xl md:text-4xl lg:text-5xl font-serif font-bold tracking-tight text-black">
                RoutePick,
              </span>
              <span className="block text-gray-300 italic font-serif font-light text-2xl md:text-3xl lg:text-4xl whitespace-nowrap mt-2">
                하루 설계를 간편하게
              </span>
            </h2>
            
            <div className="space-y-10">
              {/* Sub-headline */}
              <div>
                <h3 className="text-xl md:text-2xl font-bold text-gray-900 leading-snug">
                  하루를 계획하는 일이 <br/>
                  복잡하고 번거로울 필요는 없다는 것.
                </h3>
              </div>

              {/* Body Text */}
              <div className="space-y-6 text-gray-500 leading-relaxed text-sm md:text-base">
                <p>
                  수많은 장소 추천 속에서 우리는 늘 같은 문제를 마주합니다.<br/>
                  장소는 많은데, 하루의 흐름은 보이지 않는다는 것.
                </p>
                
                <p>
                  RoutePick은 장소를 나열하지 않습니다.<br/>
                  테마와 상황을 바탕으로 하루의 구조를 먼저 설계하고, <br className="hidden lg:block"/>
                  그에 맞는 장소들을 하나의 경로로 연결합니다.
                </p>

                <p className="pt-2">
                  무수한 선택지가 아닌, 실제로 가능한 하나의 하루.<br/>
                  <span className="font-bold text-black">RoutePick은 그 흐름을 만들어냅니다.</span>
                </p>
              </div>
            </div>

            {/* Signature / Credits */}
            <div className="mt-20 flex justify-end pr-2">
              <span className="inline-block border-b border-black pb-1 text-sm font-medium text-black">
                김윤진 | 이홍겸 | 정한결
              </span>
            </div>
          </div>
          
        </div>
      </div>
    </section>
  );
};

export default Philosophy;