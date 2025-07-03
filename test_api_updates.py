#!/usr/bin/env python3
"""
Test to verify API endpoint response times are updating every 5 seconds
"""

import asyncio
import websockets
import json
import sys
from datetime import datetime

async def test_api_endpoint_updates():
    """Test that API endpoint response times update every 5 seconds"""
    uri = "ws://localhost:4080/api/v1/ws/analytics/progressive"
    
    try:
        print(f"🔌 Connecting to {uri}")
        async with websockets.connect(uri) as websocket:
            print("✅ Connected!")
            
            # Track API endpoint response times over multiple updates
            endpoint_times = {}
            update_count = 0
            
            print("📊 Monitoring API endpoint response times for 20 seconds...")
            start_time = datetime.now()
            
            try:
                while (datetime.now() - start_time).seconds < 20:
                    message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(message)
                    
                    # Look for API endpoint updates
                    if data.get('section') in ['api_endpoint', 'health_update']:
                        system_health = data.get('data', {}).get('systemHealth', {})
                        
                        current_time = datetime.now().strftime("%H:%M:%S")
                        
                        for endpoint_key, endpoint_data in system_health.items():
                            if endpoint_key.startswith('api_endpoint_'):
                                endpoint_name = endpoint_data.get('name', endpoint_key)
                                response_time = endpoint_data.get('response_time', 0)
                                
                                # Track this endpoint's response times
                                if endpoint_name not in endpoint_times:
                                    endpoint_times[endpoint_name] = []
                                
                                endpoint_times[endpoint_name].append({
                                    'time': current_time,
                                    'response_time': response_time,
                                    'section': data.get('section')
                                })
                                
                                print(f"⏱️  {current_time} | {endpoint_name}: {response_time}ms ({data.get('section')})")
                        
                        if system_health:
                            update_count += 1
                            
            except asyncio.TimeoutError:
                pass  # Continue monitoring
            
            print(f"\n📈 Update Summary:")
            print(f"   Total updates received: {update_count}")
            print(f"   Monitored endpoints: {len(endpoint_times)}")
            
            # Check if we got multiple updates for endpoints
            for endpoint_name, times in endpoint_times.items():
                if len(times) > 1:
                    print(f"✅ {endpoint_name}: {len(times)} updates")
                    # Show first and last response times
                    first = times[0]
                    last = times[-1]
                    print(f"   First: {first['response_time']}ms at {first['time']}")
                    print(f"   Last:  {last['response_time']}ms at {last['time']}")
                else:
                    print(f"⚠️  {endpoint_name}: Only {len(times)} update(s)")
            
            # Test if we got periodic updates (every 5 seconds)
            if update_count >= 3:  # Should get at least 3 updates in 20 seconds
                print("\n🎉 API endpoints appear to be updating periodically!")
                return True
            else:
                print(f"\n❌ Not enough updates received ({update_count} < 3)")
                return False
                
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def main():
    print("🧪 API Endpoint Updates Test")
    print("=" * 50)
    
    success = await test_api_endpoint_updates()
    
    if success:
        print("\n🎉 API endpoint updates test passed!")
        sys.exit(0)
    else:
        print("\n💥 API endpoint updates test failed!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())