# JARVIS Tools Reference

> 263 tools across 90 modules

## Quick Reference

### App Control (apps.py)

| Tool | Description |
|---|---|
| `focus_window` | Bring an already-open window to the foreground |
| `get_window_list` | List the titles of all visible top-level windows currently open on the desktop |
| `open_app` | Launch a Windows application by friendly name |

### Archives (archive.py)

| Tool | Description |
|---|---|
| `compress_folder` | Compress a folder into a  |
| `extract_zip` | Extract a  |

### Audio (TTS/Sounds) (audio.py)

| Tool | Description |
|---|---|
| `beep` | Play a beep sound at a specific frequency and duration |
| `list_system_voices` | List available text-to-speech voices on the system |
| `play_system_sound` | Play a Windows system sound |
| `windows_voice_speak` | Speak text using Windows built-in SAPI voice (no Piper needed) |

### Audio Devices (audio_devices.py)

| Tool | Description |
|---|---|
| `audio_devices` | List all audio input and output devices |
| `open_sound_settings` | Open Windows Sound Settings |
| `open_volume_mixer` | Open the Windows Volume Mixer |
| `set_default_audio` | Switch the default audio output device |

### Bluetooth (bluetooth.py)

| Tool | Description |
|---|---|
| `bluetooth_devices` | List paired Bluetooth devices and their connection status |
| `toggle_bluetooth` | Turn Bluetooth on or off |

### Browser Extra (browser_extra.py)

| Tool | Description |
|---|---|
| `browser_search` | Open a web browser and search for the given query using Google |
| `open_browser_devtools` | Open browser developer tools |
| `open_url_in_browser` | Open a URL in the user's default web browser |
| `refresh_page` | Refresh the current browser page (sends F5) |

### Calculator (calculator.py)

| Tool | Description |
|---|---|
| `calculate` | Evaluate a mathematical expression precisely |
| `convert_units` | Convert between common units: temperature, length, weight, volume |

### Calendar (calendar.py)

| Tool | Description |
|---|---|
| `add_days` | Add or subtract days from a date |
| `date_difference` | Calculate the difference between two dates in days, weeks, and months |
| `day_of_week` | Find out what day of the week a date falls on |
| `get_calendar` | Show a calendar for the current month or a specific month |
| `get_timezone_info` | Get the current time in different timezones |

### Cleanup (system_cleanup.py)

| Tool | Description |
|---|---|
| `clean_temp_files` | Clean temporary files from Windows temp folders to free disk space |
| `clear_dns_cache` | Clear the DNS resolver cache |
| `get_event_log` | Get recent Windows event log entries (errors, warnings) |

### Clipboard History (clipboard.py)

| Tool | Description |
|---|---|
| `clipboard_clear_history` | Clear all clipboard history |
| `clipboard_history` | Show recent clipboard history |

### Clipboard Images (clipboard_image.py)

| Tool | Description |
|---|---|
| `clipboard_image_save` | Save the current clipboard image to a file |
| `full_screenshot` | Take a full desktop screenshot and save it |

### Clipboard Monitor (clipboard_monitor.py)

| Tool | Description |
|---|---|
| `clipboard_compare` | Compare current clipboard with a given text and report similarity |
| `clipboard_monitor` | Check if the clipboard has changed since last check |

### Clipboard Transform (clipboard_transform.py)

| Tool | Description |
|---|---|
| `extract_emails` | Extract email addresses from clipboard text |
| `extract_urls` | Extract URLs from clipboard text |
| `transform_clipboard` | Transform clipboard text: uppercase, lowercase, title case, camelCase, snake_case, kebab-case, reverse, trim, deduplicate lines |

### Code Analysis (code_analysis.py)

| Tool | Description |
|---|---|
| `code_stats` | Analyze code in a directory: line counts, comment ratios, file counts by language |
| `file_types` | List all file types in a directory with their counts and total sizes |

### Code Execution (python_exec.py)

| Tool | Description |
|---|---|
| `run_python` | Execute arbitrary Python 3 code on the user's PC and return the output |

### Colors (colors.py)

| Tool | Description |
|---|---|
| `color_contrast` | Check if two colors have sufficient contrast for accessibility (WCAG AA) |
| `color_convert` | Convert between color formats: hex, rgb, hsl |
| `generate_palette` | Generate a color palette (set of harmonious colors) for design work |

### Conversation Mgmt (conv_manage.py)

| Tool | Description |
|---|---|
| `cleanup_conversations` | Clean up old conversation logs |
| `conversation_summary` | Get a summary of recent conversation activity: turns per day, most active times, average response length, etc |

### Conversation Search (conversations.py)

| Tool | Description |
|---|---|
| `conversation_stats` | Get statistics about past JARVIS conversations: total turns, average response length, tools used most frequently, etc |
| `search_conversations` | Search past JARVIS conversations |

### DNS (dns.py)

| Tool | Description |
|---|---|
| `dns_lookup` | Look up the IP address(es) for a domain name |
| `dns_records` | Query DNS records (A, MX, NS, TXT) using nslookup |
| `reverse_dns` | Perform reverse DNS lookup (IP to hostname) |
| `traceroute` | Trace the network route to a host |

### Data Conversion (data_convert.py)

| Tool | Description |
|---|---|
| `csv_to_json` | Convert CSV text to JSON format |
| `json_format` | Format, validate, or minify JSON text |
| `json_to_csv` | Convert a JSON array of objects to CSV format |
| `yaml_to_json` | Convert YAML text to JSON format |

### Database (database.py)

| Tool | Description |
|---|---|
| `sqlite_count` | Get row counts for all tables in a SQLite database |
| `sqlite_query` | Execute a SQL query on a SQLite database file |
| `sqlite_tables` | List all tables in a SQLite database with their column names |

### Diagnostics (self_test.py)

| Tool | Description |
|---|---|
| `self_test` | Run a quick self-diagnostic to check if JARVIS's core components are working |

### Diff (diff.py)

| Tool | Description |
|---|---|
| `diff_files` | Compare two text files and show the differences |
| `similarity` | Check how similar two texts are (0% to 100%) |

### Display (display.py)

| Tool | Description |
|---|---|
| `screen_resolution` | Get or set the screen resolution |
| `screenshot_region` | Take a screenshot of a specific region of the screen |
| `toggle_dark_mode` | Toggle between Windows dark mode and light mode |

### Email (email.py)

| Tool | Description |
|---|---|
| `configure_email` | Configure SMTP email settings |
| `send_email` | Send an email via SMTP |

### Environment (env.py)

| Tool | Description |
|---|---|
| `get_env` | Get the value of an environment variable |
| `get_path` | Show the system PATH with one directory per line |
| `list_env` | List all environment variables or filter by a keyword |

### Event Log (eventlog.py)

| Tool | Description |
|---|---|
| `event_log_app_errors` | Get recent application crash events from Windows Event Log |
| `event_log_errors` | Get recent error events from the Windows Event Log |
| `get_last_shutdown_time` | Find when the system was last shut down or rebooted |

### Export (export_html.py)

| Tool | Description |
|---|---|
| `export_conversations_html` | Export recent conversations to an HTML file you can open in a browser |

### File Integrity (file_hash.py)

| Tool | Description |
|---|---|
| `file_hash` | Compute file hash (MD5, SHA1, SHA256) |
| `file_hash_all` | Compute all three hashes (MD5, SHA1, SHA256) for a file |
| `verify_hash` | Verify a file's hash matches an expected value |

### File Metadata (file_metadata.py)

| Tool | Description |
|---|---|
| `file_metadata` | Get detailed file metadata: size, created, modified, accessed, extension info |
| `rename_batch` | Batch rename files in a folder with a prefix, suffix, or find-replace pattern |

### File Organization (file_organizer.py)

| Tool | Description |
|---|---|
| `find_duplicates` | Find duplicate files in a folder based on file size and content hash |
| `organize_folder` | Organize files in a folder by sorting them into subfolders by type (Images, Documents, Videos, etc |

### File Search (file_search.py)

| Tool | Description |
|---|---|
| `search_files` | Search for files on the PC by name or extension |

### Files (files.py)

| Tool | Description |
|---|---|
| `list_dir` | List the contents of a directory (files + subdirs, one per line) |
| `read_file` | Read a text file and return its contents (truncated to ~64 KB) |
| `write_file` | Create or overwrite a text file |

### Fonts (fonts.py)

| Tool | Description |
|---|---|
| `font_info` | Get info about a font file |
| `list_fonts` | List all installed system fonts |

### Git (git.py)

| Tool | Description |
|---|---|
| `git_branch` | List git branches and show current branch |
| `git_diff` | Show git diff of unstaged changes |
| `git_log` | View recent git commits |
| `git_status` | Get git status of the current repository |

### GitHub (github.py)

| Tool | Description |
|---|---|
| `github_clone` | Clone a GitHub repository to the local machine |
| `github_repo_info` | Get information about a GitHub repository (stars, forks, issues, description) |
| `github_search` | Search GitHub repositories by query |

### Image Comparison (image_compare.py)

| Tool | Description |
|---|---|
| `compare_images` | Compare two images pixel-by-pixel and report differences |
| `image_to_ascii` | Convert an image to ASCII art text |

### Image Editing (image.py)

| Tool | Description |
|---|---|
| `add_watermark` | Add a text watermark to an image |
| `create_thumbnail` | Create a thumbnail from an image with smart cropping |
| `image_info` | Get image metadata: dimensions, format, file size, color mode |
| `resize_image` | Resize an image to specific dimensions or by percentage |

### JSON Database (json_db.py)

| Tool | Description |
|---|---|
| `db_count` | Count records in a JSON database collection |
| `db_delete` | Delete a JSON database collection or specific records |
| `db_insert` | Insert a record into a named JSON database collection |
| `db_query` | Query records from a JSON database collection |

### Locale (locale.py)

| Tool | Description |
|---|---|
| `get_locale_info` | Get system locale and regional settings: language, date format, currency, timezone |
| `get_system_language` | Get the system's current display and input language |

### Markdown/HTML (markdown.py)

| Tool | Description |
|---|---|
| `html_to_text` | Convert HTML to plain text (strip all tags) |
| `json_to_markdown` | Convert a JSON object to a readable markdown table or list |
| `markdown_to_html` | Convert markdown text to HTML |

### Media & Keyboard (media_control.py)

| Tool | Description |
|---|---|
| `keyboard_press` | Press a keyboard shortcut or hotkey |
| `keyboard_type` | Type text as if from the keyboard |
| `media_next` | Skip to the next track in the currently active media player |
| `media_play_pause` | Toggle play/pause for the currently active media player |
| `media_previous` | Go back to the previous track in the currently active media player |
| `mute` | Mute or unmute the system audio |
| `set_brightness` | Set the screen brightness level (Windows 10/11) |
| `volume_down` | Decrease the system volume by a small amount (about 5%) |
| `volume_up` | Increase the system volume by a small amount (about 5%) |

### Media Recording (media.py)

| Tool | Description |
|---|---|
| `convert_media` | Convert audio/video files to different formats using ffmpeg |
| `record_audio` | Record audio from the microphone |
| `record_screen` | Start recording the screen |

### Memory (memory.py)

| Tool | Description |
|---|---|
| `forget` | Remove a stored memory by its number |
| `list_memories` | List all stored memories with their categories and timestamps |
| `recall` | Search JARVIS's persistent memory for stored facts and preferences |
| `remember` | Store a fact or preference so JARVIS remembers it in future conversations |

### Meta (capabilities.py)

| Tool | Description |
|---|---|
| `list_capabilities` | List everything JARVIS can do |

### Monitoring (monitoring.py)

| Tool | Description |
|---|---|
| `get_disk_info` | Get disk usage information for all drives |
| `get_io_stats` | Get disk I/O and network I/O statistics since boot |
| `get_network_interfaces` | List all network interfaces with their IP addresses and status |
| `get_temperature` | Get hardware temperature readings (CPU, GPU) if available |
| `get_uptime` | Get how long the computer has been running since last boot |

### Mouse (mouse.py)

| Tool | Description |
|---|---|
| `get_mouse_position` | Get the current mouse cursor position |
| `mouse_click` | Click the mouse at the current position or at specific coordinates |
| `mouse_move` | Move the mouse cursor to specific coordinates |
| `scroll` | Scroll the mouse wheel up or down |

### Network (network.py)

| Tool | Description |
|---|---|
| `get_network_info` | Get network information: local IP, public IP, DNS servers, WiFi name, connection type |
| `internet_speed_test` | Run a quick internet speed test |
| `ping` | Ping a host and return the result |

### Notes (notes.py)

| Tool | Description |
|---|---|
| `add_note` | Add a quick note |
| `delete_note` | Delete a note by its ID or title keyword |
| `list_notes` | List all stored notes |
| `read_note` | Read the full text of a note by its ID or title keyword |

### Passwords (password.py)

| Tool | Description |
|---|---|
| `generate_password` | Generate a secure random password with customizable length and character types |
| `password_strength` | Estimate the strength of a password |

### Power (system_power.py)

| Tool | Description |
|---|---|
| `hibernate_pc` | Hibernate the PC |
| `lock_workstation` | Lock the workstation (same as Win+L) |
| `restart_pc` | Restart Windows |
| `shutdown_pc` | Shut down Windows |
| `sleep_pc` | Put the PC to sleep |

### Power Management (power.py)

| Tool | Description |
|---|---|
| `get_battery_report` | Generate a detailed Windows battery health report |
| `get_power_plan` | Get the current Windows power plan |
| `get_sleep_settings` | Get Windows sleep and hibernate settings |
| `set_power_plan` | Change the Windows power plan |

### Printer (printer.py)

| Tool | Description |
|---|---|
| `clear_print_queue` | Clear all pending print jobs for a printer |
| `list_printers` | List all installed printers and their status |
| `print_queue` | Show the current print queue for a printer |

### Processes (process_mgmt.py)

| Tool | Description |
|---|---|
| `kill_process` | Kill a running process by name or PID |
| `list_processes` | List running processes with their PID and memory usage |

### QR Codes (qr_code.py)

| Tool | Description |
|---|---|
| `generate_qr_code` | Generate a QR code image from text or a URL |

### Random/Decisions (random.py)

| Tool | Description |
|---|---|
| `flip_coin` | Flip a coin |
| `pick_random` | Pick a random item from a list |
| `roll_dice` | Roll dice |
| `shuffle` | Shuffle a list of items randomly |

### Regex (regex.py)

| Tool | Description |
|---|---|
| `regex_extract` | Extract named capture groups from text using a regex pattern |
| `regex_replace` | Replace text using a regex pattern |
| `regex_test` | Test a regex pattern against text and show all matches |

### Registry (registry.py)

| Tool | Description |
|---|---|
| `get_startup_programs` | List programs that run at Windows startup |
| `registry_list` | List all values under a registry key |
| `registry_read` | Read a Windows Registry value |

### Screen Control (screen_dim.py)

| Tool | Description |
|---|---|
| `cascade_windows` | Cascade all open windows on the desktop |
| `dim_screen` | Dim the screen brightness below minimum (useful for night work) |
| `focus_mode` | Enable or disable Windows Focus Assist (Do Not Disturb) |
| `show_desktop` | Minimize all windows to show the desktop (Win+D) |

### Screenshots (screen.py)

| Tool | Description |
|---|---|
| `get_screen_text` | Capture the screen (or a region) and run OCR to extract all visible text |
| `take_screenshot` | Capture the current desktop screen (or a rectangular region) as a PNG, save it under logs/screenshots/, and return the full path |

### Search/Replace (search_replace.py)

| Tool | Description |
|---|---|
| `replace_in_files` | Find and replace text across multiple files |
| `search_in_files` | Search for text in files within a directory (grep-like) |

### Security (security.py)

| Tool | Description |
|---|---|
| `active_connections` | Show active network connections with remote addresses and ports |
| `firewall_rules` | List Windows Firewall rules, optionally filtered by enabled status or direction |
| `open_ports` | List all currently open/listening network ports |
| `windows_security_audit` | Quick Windows security audit: UAC status, defender status, firewall status |

### Services (services.py)

| Tool | Description |
|---|---|
| `list_services` | List Windows services, optionally filtered by status or name |
| `restart_service` | Restart a Windows service by name |
| `start_service` | Start a Windows service by name |
| `stop_service` | Stop a Windows service by name |

### Shell (shell.py)

| Tool | Description |
|---|---|
| `run_command` | Run a shell command on the user's Windows PC and return its output |

### Shortcuts (shortcuts.py)

| Tool | Description |
|---|---|
| `create_shortcut` | Create a Windows desktop shortcut ( |
| `open_startup_folder` | Open the Windows Startup folder to manage programs that run at login |

### Storage Analysis (storage.py)

| Tool | Description |
|---|---|
| `disk_hogs` | Find which folders are using the most disk space |
| `find_large_files` | Find the largest files in a folder tree |
| `storage_summary` | Get a storage usage summary for all drives |

### Summarization (summarize.py)

| Tool | Description |
|---|---|
| `extract_keywords` | Extract the most important keywords/phrases from text |
| `summarize_text` | Summarize text by extracting key sentences (extractive summarization) |

### System (system.py)

| Tool | Description |
|---|---|
| `clipboard_read` | Read the current contents of the Windows clipboard as text |
| `clipboard_write` | Replace the Windows clipboard contents with the given text |
| `get_active_window` | Return the title of the currently focused window on the user's desktop |
| `send_notification` | Show a Windows toast notification in the bottom-right corner |
| `set_volume` | Set the system master volume |

### System Info (system_info.py)

| Tool | Description |
|---|---|
| `get_battery` | Get the current battery percentage and charging status |
| `get_cpu_usage` | Get the current CPU usage percentage across all cores |
| `get_processes` | List the top processes by CPU or memory usage |
| `get_system_info` | Get a summary of the PC's system information: OS version, CPU, RAM, GPU, disk space, uptime |

### System Report (system_report.py)

| Tool | Description |
|---|---|
| `system_report` | Generate a comprehensive system report: OS, CPU, RAM, GPU, disk, network, installed software |

### Task Manager (taskmgr.py)

| Tool | Description |
|---|---|
| `get_process_details` | Get detailed info about a specific process by name or PID |
| `task_manager_summary` | Get a Task Manager-style summary: process count, CPU, memory, disk, network usage |

### Task Scheduler (scheduler.py)

| Tool | Description |
|---|---|
| `create_scheduled_task` | Create a Windows scheduled task to run a program or script at a specific time or on a schedule |
| `delete_scheduled_task` | Delete a scheduled task by name |
| `list_scheduled_tasks` | List all Windows scheduled tasks |

### Tasks (tasks.py)

| Tool | Description |
|---|---|
| `add_task` | Add a task or todo item |
| `complete_task` | Mark a task as completed by its ID or keyword |
| `delete_task` | Delete a task by its ID or keyword |
| `list_tasks` | List all tasks, optionally filtered by status |

### Terminal (terminal.py)

| Tool | Description |
|---|---|
| `get_env_var` | Get the value of any system or user environment variable |
| `get_terminal_history` | Get recent PowerShell command history |
| `run_as_admin` | Run a command with elevated (admin) privileges |
| `set_env_var` | Set a user environment variable (requires restart of apps to take effect) |

### Text Tools (text_tools.py)

| Tool | Description |
|---|---|
| `count_words` | Count words, characters, and sentences in the user's clipboard or provided text |
| `hash_text` | Compute hash values of text (MD5, SHA1, SHA256) |
| `text_analyze` | Analyze text: character count, word count, sentence count, reading time |
| `text_transform` | Transform text: uppercase, lowercase, title case, reverse, or truncate |
| `wrap_text` | Wrap text to a specific width |

### Time Tracking (timetrack.py)

| Tool | Description |
|---|---|
| `time_clear` | Clear all time tracking entries |
| `time_report` | Show a report of logged time for today or the last N days |
| `timer_start` | Start tracking time for a task or activity |
| `timer_stop` | Stop the currently running timer |

### Timers (timer.py)

| Tool | Description |
|---|---|
| `cancel_timer` | Cancel a previously set timer by its ID |
| `list_timers` | List all active timers with their remaining time |
| `set_timer` | Set a countdown timer |

### URL Tools (url_tools.py)

| Tool | Description |
|---|---|
| `check_url` | Check if a URL is accessible and get its HTTP status code and response time |
| `expand_url` | Expand a shortened URL to get the full destination URL |
| `shorten_url` | Shorten a long URL using a free URL shortening service |

### USB (usb.py)

| Tool | Description |
|---|---|
| `eject_drive` | Safely eject a USB drive by its drive letter |
| `list_drives` | List all drives and volumes including USB drives with their letters, labels, and free space |
| `list_usb_devices` | List all connected USB devices |

### User Account (user.py)

| Tool | Description |
|---|---|
| `get_recent_files` | List recently modified files in a user folder |
| `open_user_folder` | Open a user folder: Desktop, Documents, Downloads, Pictures, Music, Videos, or AppData |
| `user_groups` | Show which groups the current user belongs to |
| `whoami` | Show current user information: username, domain, groups |

### Voice (speak.py)

| Tool | Description |
|---|---|
| `speak` | Speak a text out loud through the system speakers using JARVIS's TTS engine |

### Weather (weather.py)

| Tool | Description |
|---|---|
| `get_time` | Get the current date and time in various formats |
| `get_weather` | Get current weather for a location |

### Web (browser.py)

| Tool | Description |
|---|---|
| `open_url` | Open a URL in the user's default web browser |
| `web_search` | Search the web (DuckDuckGo) and return the top results |

### Web Scraping (web_scraper.py)

| Tool | Description |
|---|---|
| `fetch_page` | Fetch a web page and extract its text content (strips HTML) |
| `fetch_page_images` | Extract all image URLs from a web page |
| `fetch_page_links` | Extract all links from a web page |

### Windows Settings (windows_settings.py)

| Tool | Description |
|---|---|
| `change_display_brightness` | Change screen brightness on Windows 10/11 laptops |
| `change_wallpaper` | Change the desktop wallpaper to an image file |
| `get_installed_apps` | List installed applications on the system |
| `get_wifi_password` | Show saved WiFi password for a known network |
| `open_settings` | Open Windows Settings to a specific page |

### Zip Archives (zip.py)

| Tool | Description |
|---|---|
| `zip_create` | Create a zip archive from a file or folder |
| `zip_extract` | Extract files from a zip archive |
| `zip_list` | List the contents of a zip file without extracting |

### Accessibility (accessibility.py)

| Tool | Description |
|---|---|
| `text_size` | Change Windows text size |
| `toggle_magnifier` | Open or close Windows Magnifier |
| `toggle_narrator` | Turn Windows Narrator (screen reader) on or off |

### Api (api.py)

| Tool | Description |
|---|---|
| `http_get` | Make an HTTP GET request to a URL and return the response |
| `http_head` | Make an HTTP HEAD request to check if a URL is accessible |
| `http_post` | Make an HTTP POST request with JSON body |

### Briefing (briefing.py)

| Tool | Description |
|---|---|
| `daily_briefing` | Get a daily briefing: current time, weather, system status, recent tasks, and any notes |

### Disk (disk.py)

| Tool | Description |
|---|---|
| `get_disk_usage` | Return total, used, and free disk space for a drive or path in bytes and human-readable form |
| `get_gpu_stats` | Read current GPU usage via nvidia-smi — temperature, utilization, VRAM used/total, power draw |

---
**Total: 263 tools**

## Adding Your Own Tools

Create a new file in `tools/` with a decorated function:

```python
from tools import tool

@tool(name="my_tool", description="What it does.",
    parameters={"type": "object", "properties": {}, "required": []})
def my_tool() -> str:
    return "Hello!"
```