#!/usr/bin/env python3
"""
Example usage of the Social Collector for brand scoring.
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.collectors.social_collector import SocialCollector, collect_social_data
from src.config import FIRECRAWL_API_KEY


def example_basic_usage():
    """Basic usage example."""
    print("=== Basic Usage Example ===\n")
    
    # Create collector with API key
    collector = SocialCollector(api_key=FIRECRAWL_API_KEY)
    
    # Collect social data for a brand
    # Note: This will attempt to detect and scrape social profiles
    social_data = collector.collect("Stripe")
    
    print(f"Brand: {social_data.brand_name}")
    print(f"Total Followers: {social_data.total_followers:,}")
    print(f"Avg Post Frequency: {social_data.avg_post_frequency:.1f} posts/week")
    print(f"Most Active Platform: {social_data.most_active_platform}")
    
    print("\nPlatforms:")
    for platform, metrics in social_data.platforms.items():
        print(f"\n[{platform.upper()}]")
        print(f"  URL: {metrics.profile_url}")
        print(f"  Followers: {metrics.followers_count:,}")
        print(f"  Posts: {metrics.posts_count:,}")
        print(f"  Last Post: {metrics.last_post_date}")
        print(f"  Verified: {metrics.verified}")
        if metrics.error:
            print(f"  Error: {metrics.error}")


def example_with_web_content():
    """Example with web content for profile detection."""
    print("\n=== With Web Content Example ===\n")
    
    # Simulated web content with social links
    web_content = """
    Visit our website at https://stripe.com
    
    Follow us on social media:
    - Instagram: https://www.instagram.com/stripe
    - Twitter: https://twitter.com/stripe  
    - LinkedIn: https://www.linkedin.com/company/stripe
    - TikTok: https://www.tiktok.com/@stripe
    
    For support, email support@stripe.com
    """
    
    collector = SocialCollector(api_key=FIRECRAWL_API_KEY)
    social_data = collector.collect("Stripe", web_content=web_content)
    
    print(f"Profiles found: {social_data.profiles_found}")
    print(f"Platforms detected: {list(social_data.platforms.keys())}")


def example_convenience_function():
    """Example using the convenience function."""
    print("\n=== Convenience Function Example ===\n")
    
    # Simple one-liner to collect social data
    social_data = collect_social_data(
        brand_name="Stripe",
        api_key=FIRECRAWL_API_KEY
    )
    
    print(f"Collected data for {len(social_data.platforms)} platforms")


def example_known_urls():
    """Example with known profile URLs."""
    print("\n=== Known URLs Example ===\n")
    
    collector = SocialCollector(api_key=FIRECRAWL_API_KEY)
    
    # If you already know the profile URLs
    known_urls = {
        "instagram": "https://www.instagram.com/stripe",
        "twitter": "https://x.com/stripe",
        "linkedin": "https://www.linkedin.com/company/stripe",
    }
    
    social_data = collector.collect_from_urls("Stripe", known_urls)
    
    print(f"Collected data from {len(social_data.platforms)} known URLs")


if __name__ == "__main__":
    print("Social Collector Examples\n")
    print("Note: These examples use the Firecrawl API to scrape social profiles.")
    print("Some platforms (like Twitter/X) may not be supported by Firecrawl.\n")
    
    # Run examples
    # example_basic_usage()
    # example_with_web_content()
    # example_convenience_function()
    # example_known_urls()
    
    print("\nUncomment the examples above to run them.")
    print("Warning: Running these examples will make API calls to Firecrawl.")
