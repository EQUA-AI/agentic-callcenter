"""
Test Script for Multi-Agent Configuration
Tests the multi-agent routing and configuration management
"""
import asyncio
import aiohttp
import json
from typing import Dict, Any

class MultiAgentTester:
    """Test suite for multi-agent configuration"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_health(self) -> Dict[str, Any]:
        """Test system health"""
        print("🏥 Testing system health...")
        
        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                data = await response.json()
                
                if response.status == 200:
                    print("✅ System is healthy")
                    print(f"   Multi-agent routing: {data.get('multi_agent_routing', {}).get('total_routes', 0)} routes")
                    return {"success": True, "data": data}
                else:
                    print(f"❌ Health check failed: {response.status}")
                    return {"success": False, "error": f"HTTP {response.status}"}
                    
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return {"success": False, "error": str(e)}
    
    async def test_config_api(self) -> Dict[str, Any]:
        """Test configuration API endpoints"""
        print("\n⚙️ Testing configuration API...")
        
        results = {}
        
        # Test agents endpoint
        try:
            async with self.session.get(f"{self.base_url}/config/api/agents") as response:
                if response.status == 200:
                    data = await response.json()
                    agent_count = len(data.get('agents', []))
                    print(f"✅ Agents API working - {agent_count} agents found")
                    results['agents'] = {"success": True, "count": agent_count}
                else:
                    print(f"❌ Agents API failed: {response.status}")
                    results['agents'] = {"success": False, "error": f"HTTP {response.status}"}
        except Exception as e:
            print(f"❌ Agents API error: {e}")
            results['agents'] = {"success": False, "error": str(e)}
        
        # Test channels endpoint
        try:
            async with self.session.get(f"{self.base_url}/config/api/channels") as response:
                if response.status == 200:
                    data = await response.json()
                    channel_count = len(data.get('channels', []))
                    print(f"✅ Channels API working - {channel_count} channels found")
                    results['channels'] = {"success": True, "count": channel_count}
                else:
                    print(f"❌ Channels API failed: {response.status}")
                    results['channels'] = {"success": False, "error": f"HTTP {response.status}"}
        except Exception as e:
            print(f"❌ Channels API error: {e}")
            results['channels'] = {"success": False, "error": str(e)}
        
        # Test validation endpoint
        try:
            async with self.session.get(f"{self.base_url}/config/api/validation") as response:
                if response.status == 200:
                    data = await response.json()
                    is_valid = data.get('valid', False)
                    issues = len(data.get('issues', []))
                    if is_valid:
                        print("✅ Configuration validation passed")
                    else:
                        print(f"⚠️ Configuration has {issues} validation issues")
                    results['validation'] = {"success": True, "valid": is_valid, "issues": issues}
                else:
                    print(f"❌ Validation API failed: {response.status}")
                    results['validation'] = {"success": False, "error": f"HTTP {response.status}"}
        except Exception as e:
            print(f"❌ Validation API error: {e}")
            results['validation'] = {"success": False, "error": str(e)}
        
        return results
    
    async def test_routing(self, test_cases: list = None) -> Dict[str, Any]:
        """Test message routing"""
        print("\n🚦 Testing message routing...")
        
        if not test_cases:
            test_cases = [
                {
                    "name": "Wedding Business Test",
                    "from": "+1999888777",
                    "to": "+1234567890",
                    "message": "Hello, I need help planning my wedding venue"
                },
                {
                    "name": "Telco Support Test", 
                    "from": "+1999888778",
                    "to": "+1234567891",
                    "message": "I'm having issues with my phone bill"
                },
                {
                    "name": "General SMS Test",
                    "from": "+1999888779", 
                    "to": "+1234567892",
                    "message": "General inquiry about your services"
                }
            ]
        
        results = {}
        
        for test_case in test_cases:
            print(f"\n   Testing: {test_case['name']}")
            
            try:
                payload = {
                    "from": test_case["from"],
                    "to": test_case["to"], 
                    "message": test_case["message"],
                    "conversation_id": f"test_{test_case['name'].lower().replace(' ', '_')}"
                }
                
                async with self.session.post(
                    f"{self.base_url}/route/message",
                    json=payload
                ) as response:
                    data = await response.json()
                    
                    if response.status == 200 and data.get('success'):
                        routing_info = data.get('routing_info', {})
                        agent_name = routing_info.get('agent_name', 'Unknown')
                        channel_name = routing_info.get('channel_name', 'Unknown')
                        print(f"   ✅ Routed to: {agent_name} via {channel_name}")
                        results[test_case['name']] = {
                            "success": True,
                            "agent": agent_name,
                            "channel": channel_name
                        }
                    else:
                        error = data.get('error', f'HTTP {response.status}')
                        print(f"   ❌ Routing failed: {error}")
                        results[test_case['name']] = {
                            "success": False,
                            "error": error
                        }
                        
            except Exception as e:
                print(f"   ❌ Routing error: {e}")
                results[test_case['name']] = {
                    "success": False,
                    "error": str(e)
                }
        
        return results
    
    async def test_agent_lookup(self, phone_numbers: list = None) -> Dict[str, Any]:
        """Test agent lookup by phone number"""
        print("\n🔍 Testing agent lookup...")
        
        if not phone_numbers:
            phone_numbers = ["+1234567890", "+1234567891", "+1234567892"]
        
        results = {}
        
        for phone in phone_numbers:
            print(f"   Testing lookup for: {phone}")
            
            try:
                async with self.session.get(f"{self.base_url}/route/agent/{phone}") as response:
                    data = await response.json()
                    
                    if response.status == 200 and data.get('success'):
                        routing_info = data.get('routing_info', {})
                        agent_name = routing_info.get('agent_name', 'Unknown')
                        print(f"   ✅ Found agent: {agent_name}")
                        results[phone] = {"success": True, "agent": agent_name}
                    else:
                        error = data.get('error', f'HTTP {response.status}')
                        print(f"   ❌ Lookup failed: {error}")
                        results[phone] = {"success": False, "error": error}
                        
            except Exception as e:
                print(f"   ❌ Lookup error: {e}")
                results[phone] = {"success": False, "error": str(e)}
        
        return results
    
    async def run_full_test_suite(self) -> Dict[str, Any]:
        """Run complete test suite"""
        print("🧪 Starting Multi-Agent Configuration Test Suite")
        print("=" * 60)
        
        results = {
            "health": await self.test_health(),
            "config_api": await self.test_config_api(),
            "routing": await self.test_routing(),
            "agent_lookup": await self.test_agent_lookup()
        }
        
        print("\n" + "=" * 60)
        print("📋 Test Results Summary:")
        
        total_tests = 0
        passed_tests = 0
        
        for category, test_results in results.items():
            if isinstance(test_results, dict):
                if 'success' in test_results:
                    # Single test result
                    total_tests += 1
                    if test_results['success']:
                        passed_tests += 1
                        print(f"✅ {category.title()}: PASSED")
                    else:
                        print(f"❌ {category.title()}: FAILED - {test_results.get('error', 'Unknown error')}")
                else:
                    # Multiple test results
                    category_total = len(test_results)
                    category_passed = sum(1 for r in test_results.values() if r.get('success', False))
                    total_tests += category_total
                    passed_tests += category_passed
                    
                    if category_passed == category_total:
                        print(f"✅ {category.title()}: PASSED ({category_passed}/{category_total})")
                    else:
                        print(f"⚠️ {category.title()}: PARTIAL ({category_passed}/{category_total})")
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        print(f"\n🎯 Overall Success Rate: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        
        if success_rate == 100:
            print("🎉 All tests passed! Your multi-agent configuration is working correctly.")
        elif success_rate >= 80:
            print("⚠️ Most tests passed, but there are some issues to address.")
        else:
            print("❌ Multiple test failures detected. Please check your configuration.")
        
        return results

async def main():
    """Main test function"""
    print("🚀 Multi-Agent Configuration Tester")
    print("This script tests your multi-agent WhatsApp Business setup")
    print("")
    
    # Ask for base URL
    base_url = input("Enter base URL (default: http://localhost:8000): ").strip()
    if not base_url:
        base_url = "http://localhost:8000"
    
    async with MultiAgentTester(base_url) as tester:
        results = await tester.run_full_test_suite()
        
        # Option to save results
        save_results = input("\nSave test results to file? (y/n): ").lower().strip()
        if save_results == 'y':
            filename = f"test_results_{int(asyncio.get_event_loop().time())}.json"
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"✅ Test results saved to {filename}")

if __name__ == "__main__":
    asyncio.run(main())
