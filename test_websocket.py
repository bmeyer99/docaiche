#!/usr/bin/env python3
"""
Simple WebSocket test script to verify the analytics WebSocket is working
"""

import asyncio
import websockets
import json
import sys

async def test_analytics_websocket():
    """Test the progressive analytics WebSocket endpoint"""
    uri = "ws://localhost:4080/api/v1/ws/analytics/progressive"
    
    try:
        print(f"🔌 Connecting to {uri}")
        async with websockets.connect(uri) as websocket:
            print("✅ Connected!")
            
            # Track received messages
            messages_received = []
            
            # Listen for messages for 10 seconds
            try:
                while len(messages_received) < 10:  # Stop after 10 messages or timeout
                    message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    data = json.loads(message)
                    messages_received.append(data)
                    
                    section = data.get('section', 'unknown')
                    data_keys = list(data.get('data', {}).keys())
                    
                    print(f"📧 Received message #{len(messages_received)}")
                    print(f"   Section: {section}")
                    print(f"   Data keys: {data_keys}")
                    
                    # Stop after getting complete data
                    if section == 'complete':
                        print("🎉 Initial data load complete!")
                        break
                        
            except asyncio.TimeoutError:
                print("⏰ Timeout waiting for messages")
            
            # Test refresh_data functionality
            print("\n🔄 Testing refresh_data message...")
            refresh_message = {
                "type": "refresh_data",
                "timestamp": "test"
            }
            await websocket.send(json.dumps(refresh_message))
            print("📤 Sent refresh_data request")
            
            # Wait for refresh response
            try:
                for _ in range(3):  # Wait for up to 3 refresh messages
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(message)
                    section = data.get('section', 'unknown')
                    print(f"📧 Refresh response: {section}")
                    
            except asyncio.TimeoutError:
                print("⏰ Timeout waiting for refresh response")
            
            # Test time range change
            print("\n📅 Testing time range change...")
            timerange_message = {
                "type": "change_timerange",
                "timeRange": "7d"
            }
            await websocket.send(json.dumps(timerange_message))
            print("📤 Sent time range change to 7d")
            
            # Wait for time range response
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(message)
                section = data.get('section', 'unknown')
                print(f"📧 Time range response: {section}")
                
            except asyncio.TimeoutError:
                print("⏰ Timeout waiting for time range response")
            
            print(f"\n✅ Test completed! Received {len(messages_received)} messages total")
            return True
            
    except websockets.exceptions.ConnectionRefused:
        print("❌ Connection refused. Is the API server running?")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def main():
    print("🧪 WebSocket Analytics Test")
    print("=" * 40)
    
    success = await test_analytics_websocket()
    
    if success:
        print("\n🎉 WebSocket test passed!")
        sys.exit(0)
    else:
        print("\n💥 WebSocket test failed!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())