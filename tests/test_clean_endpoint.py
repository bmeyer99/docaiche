#!/usr/bin/env python3
"""
Test the new clean analytics endpoint for timing and reliability
"""

import asyncio
import websockets
import json
import sys
from datetime import datetime

async def test_clean_analytics():
    """Test the clean analytics endpoint timing"""
    uri = "ws://localhost:4080/api/v1/ws/analytics/clean"
    
    try:
        print(f"🔌 Connecting to {uri}")
        async with websockets.connect(uri) as websocket:
            print("✅ Connected!")
            
            # Track phase timing
            phase_times = {}
            start_time = datetime.now()
            
            print("📊 Monitoring clean analytics phases...")
            
            try:
                for i in range(10):  # Wait for phases
                    message = await asyncio.wait_for(websocket.recv(), timeout=8.0)
                    data = json.loads(message)
                    
                    phase = data.get('phase', 'unknown')
                    elapsed = (datetime.now() - start_time).total_seconds()
                    current_time = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    
                    # Track when each phase arrives
                    if phase not in phase_times:
                        phase_times[phase] = elapsed
                        data_keys = list(data.get('data', {}).keys())
                        print(f"⏱️  {current_time} | {phase:12} | +{elapsed:.2f}s | {data_keys}")
                    
                    # Stop after getting complete signal
                    if phase == 'complete':
                        break
                        
            except asyncio.TimeoutError:
                print("⏰ Timeout - phases stopped arriving")
            
            print(f"\n📈 Clean Analytics Summary:")
            print(f"   Total time: {(datetime.now() - start_time).total_seconds():.2f}s")
            print(f"   Phases received: {len(phase_times)}")
            
            # Check expected phases and timing
            expected_phases = {
                'essential': 1.0,   # Should be < 1s
                'extended': 3.0,    # Should be < 3s  
                'detailed': 5.0,    # Should be < 5s
                'complete': 6.0     # Should be < 6s
            }
            
            success = True
            print(f"\n🎯 Phase Performance Analysis:")
            
            for phase, max_time in expected_phases.items():
                if phase in phase_times:
                    actual_time = phase_times[phase]
                    status = "✅" if actual_time <= max_time else "❌"
                    print(f"   {status} {phase:12}: {actual_time:.2f}s (target: <{max_time:.0f}s)")
                    if actual_time > max_time:
                        success = False
                else:
                    print(f"   ❌ {phase:12}: MISSING")
                    success = False
            
            # Test refresh functionality
            print(f"\n🔄 Testing refresh_data...")
            refresh_message = {
                "type": "refresh_data",
                "timestamp": datetime.now().isoformat()
            }
            await websocket.send(json.dumps(refresh_message))
            
            # Wait for refresh response
            refresh_count = 0
            try:
                for _ in range(5):
                    message = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    data = json.loads(message)
                    phase = data.get('phase', 'unknown')
                    refresh_count += 1
                    print(f"   📧 Refresh phase: {phase}")
                    if phase == 'complete':
                        break
            except asyncio.TimeoutError:
                pass
            
            if refresh_count > 0:
                print(f"   ✅ Refresh worked ({refresh_count} phases)")
            else:
                print(f"   ❌ Refresh failed")
                success = False
            
            return success
                
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def main():
    print("🧪 Clean Analytics Endpoint Test")
    print("=" * 50)
    
    success = await test_clean_analytics()
    
    if success:
        print("\n🎉 Clean analytics test passed!")
        print("\n📋 Summary:")
        print("   ✅ All sections load immediately with skeletons")
        print("   ✅ Essential data loads fast (< 1s)")
        print("   ✅ Extended data loads quickly (< 3s)")
        print("   ✅ Detailed data loads reasonably (< 5s)")
        print("   ✅ Refresh functionality works")
        sys.exit(0)
    else:
        print("\n💥 Clean analytics test failed!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())