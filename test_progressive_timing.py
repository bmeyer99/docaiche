#!/usr/bin/env python3
"""
Test to verify the timing of progressive section loading
"""

import asyncio
import websockets
import json
import sys
from datetime import datetime

async def test_progressive_timing():
    """Test the timing of progressive section delivery"""
    uri = "ws://localhost:4080/api/v1/ws/analytics/progressive"
    
    try:
        print(f"🔌 Connecting to {uri}")
        async with websockets.connect(uri) as websocket:
            print("✅ Connected!")
            
            # Track timing of each section
            section_times = {}
            start_time = datetime.now()
            
            print("📊 Monitoring progressive section delivery timing...")
            
            try:
                for i in range(15):  # Wait for up to 15 messages
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(message)
                    
                    section = data.get('section', 'unknown')
                    elapsed = (datetime.now() - start_time).total_seconds()
                    current_time = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    
                    # Track when each section arrives
                    if section not in section_times:
                        section_times[section] = elapsed
                        print(f"⏱️  {current_time} | {section:20} | +{elapsed:.2f}s")
                    
                    # Stop after getting complete signal
                    if section == 'complete':
                        break
                        
            except asyncio.TimeoutError:
                print("⏰ Timeout - no more messages")
            
            print(f"\n📈 Progressive Loading Summary:")
            print(f"   Total time: {(datetime.now() - start_time).total_seconds():.2f}s")
            print(f"   Sections received: {len(section_times)}")
            
            # Sort sections by arrival time
            sorted_sections = sorted(section_times.items(), key=lambda x: x[1])
            
            print(f"\n🚀 Section Loading Order:")
            for i, (section, time_elapsed) in enumerate(sorted_sections, 1):
                if i == 1:
                    print(f"   {i}. {section:20} | {time_elapsed:.2f}s (first)")
                else:
                    prev_time = sorted_sections[i-2][1]
                    delta = time_elapsed - prev_time
                    print(f"   {i}. {section:20} | {time_elapsed:.2f}s (+{delta:.2f}s)")
            
            # Check if all expected sections arrived quickly
            expected_quick_sections = ['init', 'health', 'search_ai_health', 'monitoring_health']
            missing_sections = []
            slow_sections = []
            
            for expected in expected_quick_sections:
                if expected not in section_times:
                    missing_sections.append(expected)
                elif section_times[expected] > 2.0:  # Should arrive within 2 seconds
                    slow_sections.append((expected, section_times[expected]))
            
            if missing_sections:
                print(f"\n❌ Missing sections: {missing_sections}")
                return False
            
            if slow_sections:
                print(f"\n⚠️  Slow sections (>2s):")
                for section, time_taken in slow_sections:
                    print(f"     {section}: {time_taken:.2f}s")
            
            # Check if Search & AI and Monitoring sections arrived quickly
            search_ai_time = section_times.get('search_ai_health', 999)
            monitoring_time = section_times.get('monitoring_health', 999)
            
            if search_ai_time < 2.0 and monitoring_time < 2.0:
                print(f"\n🎉 SUCCESS! Search & AI ({search_ai_time:.2f}s) and Monitoring ({monitoring_time:.2f}s) sections load quickly!")
                return True
            else:
                print(f"\n❌ SLOW! Search & AI ({search_ai_time:.2f}s) or Monitoring ({monitoring_time:.2f}s) sections are too slow")
                return False
                
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def main():
    print("🧪 Progressive Section Timing Test")
    print("=" * 50)
    
    success = await test_progressive_timing()
    
    if success:
        print("\n🎉 Progressive timing test passed!")
        sys.exit(0)
    else:
        print("\n💥 Progressive timing test failed!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())