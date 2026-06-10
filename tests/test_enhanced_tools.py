import sys
import os

# Set UTF-8 encoding for stdout on Windows console
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add workspace to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.web_scraper import scrape_structured_data, monitor_webpage_changes, archive_webpage, download_media, social_media_search, rss_feed_reader
from tools.network import ping_host, port_scan, ssl_certificate_check, api_tester, webhook_manager
from tools.dns import dns_lookup

def test_web_scraper():
    print("Testing Web Scraper & Research tools...")
    # 1. scrape_structured_data
    print("  Testing scrape_structured_data...")
    res = scrape_structured_data("https://news.ycombinator.com", target_type="metadata")
    print(f"    Result contains Hacker News metadata: {'Hacker News' in res or 'title' in res.lower()}")

    # 2. monitor_webpage_changes
    print("  Testing monitor_webpage_changes (initial baseline)...")
    res = monitor_webpage_changes("https://news.ycombinator.com", reset=True)
    print(f"    Result: {res}")
    print("  Testing monitor_webpage_changes (subsequent check)...")
    res = monitor_webpage_changes("https://news.ycombinator.com")
    print(f"    Result: {res}")

    # 3. archive_webpage
    print("  Testing archive_webpage (local only for speed)...")
    res = archive_webpage("https://news.ycombinator.com", mode="local")
    print(f"    Result: {res}")

    # 4. download_media
    print("  Testing download_media (download Hacker News logo/image)...")
    res = download_media("https://news.ycombinator.com", media_type="image", max_files=1)
    print(f"    Result: {res}")

    # 5. social_media_search
    print("  Testing social_media_search (HN)...")
    res = social_media_search("lumi", network="hn", max_results=2)
    print(f"    Result:\n{res}")

    # 6. rss_feed_reader
    print("  Testing rss_feed_reader (subscribe, list, read, sync, unsubscribe)...")
    sub_res = rss_feed_reader("subscribe", url="https://hnrss.org/frontpage", title="HN Frontpage", category="Tech")
    print(f"    Subscribe: {sub_res}")
    list_res = rss_feed_reader("list")
    print(f"    List:\n{list_res}")
    read_res = rss_feed_reader("read", url="https://hnrss.org/frontpage", max_items=2)
    print(f"    Read top 2:\n{read_res}")
    sync_res = rss_feed_reader("sync")
    print(f"    Sync:\n{sync_res}")
    unsub_res = rss_feed_reader("unsubscribe", url="https://hnrss.org/frontpage")
    print(f"    Unsubscribe: {unsub_res}")


def test_network():
    print("Testing Network & Infrastructure tools...")
    # 1. ping_host
    print("  Testing ping_host...")
    res = ping_host("google.com", port=443, method="auto")
    print(f"    Result: {res}")

    # 2. port_scan
    print("  Testing port_scan (scan google.com for 80,443)...")
    res = port_scan("google.com", port_range="80,443")
    print(f"    Result: {res}")

    # 3. ssl_certificate_check
    print("  Testing ssl_certificate_check...")
    res = ssl_certificate_check("google.com")
    print(f"    Result: {res}")

    # 4. api_tester
    print("  Testing api_tester...")
    res = api_tester("https://httpbin.org/get", method="GET")
    print(f"    Result contains response headers/body: {'HTTP Response:' in res}")

    # 5. webhook_manager
    print("  Testing webhook_manager...")
    save_res = webhook_manager("save", name="TestHook", url="https://httpbin.org/post", headers={"X-Test": "Yes"})
    print(f"    Save: {save_res}")
    list_res = webhook_manager("list")
    print(f"    List:\n{list_res}")
    send_res = webhook_manager("send", name="TestHook", payload={"status": "working"})
    print(f"    Send:\n{send_res}")
    del_res = webhook_manager("delete", name="TestHook")
    print(f"    Delete: {del_res}")
    
    # Check HMAC-SHA256 verification
    sig_res = webhook_manager("verify_signature", payload={"a": 1}, signature_header="X-Sig", signature="1731f916fda95877b9a13a23fad534f9e6108a6051a8357360c38298832d3811", secret="mysecret")
    print(f"    Verify Signature: {sig_res}")


def test_dns():
    print("Testing DNS Diagnostics enhancements...")
    # 1. Standard DNS Lookup
    print("  Testing dns_lookup (standard)...")
    res = dns_lookup("google.com")
    print(f"    Result: {res}")

    # 2. Specific DNS Server Lookup
    print("  Testing dns_lookup (specific server)...")
    res = dns_lookup("google.com", dns_server="8.8.8.8")
    print(f"    Result: {res}")

    # 3. DNS Propagation Check
    print("  Testing dns_lookup (propagation check)...")
    res = dns_lookup("google.com", check_propagation=True)
    print(f"    Result:\n{res}")

    # 4. Subdomain check
    print("  Testing dns_lookup (subdomain scan)...")
    res = dns_lookup("google.com", find_subdomains=True)
    print(f"    Result:\n{res}")


if __name__ == "__main__":
    test_web_scraper()
    print("\n" + "="*50 + "\n")
    test_network()
    print("\n" + "="*50 + "\n")
    test_dns()
