#!/usr/bin/env python3
"""
Test script for the social collector.
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.collectors.social_collector import SocialCollector, SocialData, PlatformMetrics


def test_profile_detection():
    """Test social profile detection from content."""
    collector = SocialCollector()
    
    # Test content with social links
    test_content = """
    Check out our social media profiles:
    - Instagram: https://www.instagram.com/stripe
    - Twitter: https://twitter.com/stripe
    - LinkedIn: https://www.linkedin.com/company/stripe
    - TikTok: https://www.tiktok.com/@stripe
    
    Follow us for updates!
    """
    
    profiles = collector._detect_social_profiles_from_content(test_content)
    
    print("=== Profile Detection Test ===")
    for platform, urls in profiles.items():
        print(f"{platform}: {urls}")
    
    return profiles


def test_follower_extraction():
    """Test follower count extraction."""
    collector = SocialCollector()
    
    test_cases = [
        ("1.2M followers", 1200000),
        ("500K followers", 500000),
        ("10,000 followers", 10000),
        ("followers: 2500", 2500),
        ("2.5m people follow this", 2500000),
    ]
    
    print("\n=== Follower Extraction Test ===")
    for content, expected in test_cases:
        result = collector._extract_follower_count(content, "instagram")
        status = "✓" if result == expected else "✗"
        print(f"{status} '{content}' -> {result:,} (expected {expected:,})")


def test_data_classes():
    """Test data class creation."""
    print("\n=== Data Classes Test ===")
    
    # Test PlatformMetrics
    metrics = PlatformMetrics(
        platform="instagram",
        profile_url="https://instagram.com/stripe",
        followers_count=100000,
        posts_count=500,
        verified=True,
    )
    print(f"PlatformMetrics: {metrics.platform}, {metrics.followers_count:,} followers")
    
    # Test SocialData
    data = SocialData(brand_name="Stripe")
    data.platforms["instagram"] = metrics
    data.total_followers = metrics.followers_count
    print(f"SocialData: {data.brand_name}, {len(data.platforms)} platforms")


def test_search_profiles():
    """Test profile URL generation."""
    collector = SocialCollector()
    
    print("\n=== Search Profiles Test ===")
    profiles = collector._search_social_profiles("Stripe")
    
    for platform, urls in profiles.items():
        print(f"{platform}: {urls[:2]}")  # Show first 2 URLs


if __name__ == "__main__":
    print("Testing Social Collector...\n")
    
    test_profile_detection()
    test_follower_extraction()
    test_data_classes()
    test_search_profiles()
    
    print("\n=== Tests Complete ===")
