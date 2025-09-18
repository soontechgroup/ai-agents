#!/usr/bin/env python3
"""
Test script for the new flexible web search wrapper
"""
import sys
import os

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from tools.web_search import WebSearchTool

def test_search_wrapper():
    """Test the new web search wrapper"""
    
    print("=" * 60)
    print("Testing Flexible Web Search Wrapper")
    print("=" * 60)
    
    # Initialize the search tool
    search_tool = WebSearchTool()
    
    # Test provider availability
    print("\n1. Testing Provider Availability:")
    print("-" * 40)
    
    test_results = search_tool.test_providers()
    for provider, status in test_results.items():
        print(f"{provider:12}: {'✓ Available' if status else '✗ Not working'}")
    
    # Show provider stats
    print("\n2. Provider Statistics:")
    print("-" * 40)
    
    stats = search_tool.get_search_stats()
    print(f"Primary provider: {stats['provider']}")
    print(f"Available providers: {', '.join(stats['available_providers'])}")
    print(f"Has API key: {stats['has_api_key']}")
    
    # Show detailed provider info
    print("\n3. Detailed Provider Information:")
    print("-" * 40)
    
    for provider_name, info in stats['provider_stats'].items():
        print(f"\n{provider_name.upper()}:")
        print(f"  Cost: {info['cost']}")
        print(f"  API Key Required: {info['api_key_required']}")
        if 'api_key_configured' in info:
            print(f"  API Key Configured: {info['api_key_configured']}")
        if 'rate_limits' in info:
            print(f"  Rate Limits: {info['rate_limits']}")
        print(f"  Capabilities: {', '.join(info['capabilities'])}")
    
    # Test actual searches
    test_queries = [
        "latest artificial intelligence news",
        "Python programming tutorial",
        "what is machine learning"
    ]
    
    print("\n4. Testing Search Functionality:")
    print("-" * 40)
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        
        try:
            results = search_tool.search(query, max_results=3)
            
            if results:
                print(f"Found {len(results)} results:")
                for i, result in enumerate(results, 1):
                    print(f"  {i}. {result['title'][:50]}...")
                    print(f"     Source: {result['source']}")
            else:
                print("  No results found")
        
        except Exception as e:
            print(f"  Error: {e}")
    
    # Test provider switching
    print("\n5. Testing Provider Switching:")
    print("-" * 40)
    
    # Test specific providers
    for provider in ['duckduckgo', 'serper', 'mock']:
        print(f"\nTesting {provider} provider:")
        try:
            results = search_tool.search("test query", max_results=1, provider=provider)
            if results:
                print(f"  ✓ {provider} returned {len(results)} result(s)")
                print(f"    Title: {results[0]['title'][:40]}...")
            else:
                print(f"  ✗ {provider} returned no results")
        except Exception as e:
            print(f"  ✗ {provider} failed: {e}")
    
    # Test environment variable override
    print("\n6. Environment Variable Support:")
    print("-" * 40)
    
    print("Set SEARCH_PROVIDER environment variable to prefer a specific provider")
    print("Set SERPER_API_KEY environment variable to enable Serper provider")
    
    current_serper_key = os.getenv('SERPER_API_KEY')
    print(f"Current SERPER_API_KEY: {'Set' if current_serper_key else 'Not set'}")
    
    current_search_provider = os.getenv('SEARCH_PROVIDER', 'auto')
    print(f"Current SEARCH_PROVIDER: {current_search_provider}")
    
    print("\n" + "=" * 60)
    print("Web Search Wrapper Test Complete!")
    print("=" * 60)

if __name__ == "__main__":
    test_search_wrapper()