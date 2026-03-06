# ProxyCall

A tool for testing rate limiting mechanisms across different IP addresses using proxy servers.

## ⚠️ Important Disclaimer

**This tool is intended for LEGITIMATE TESTING PURPOSES ONLY**

- This tool is designed to help developers test and validate their rate limiting implementations across different IP addresses in a controlled, ethical manner
- DO NOT use this tool to:
  - Perform denial of service (DDoS) attacks
  - Stress test production websites without explicit permission
  - Circumvent rate limiting for malicious purposes
  - Conduct any form of cyber attacks

Misuse of this tool may be illegal and could result in civil or criminal penalties. Always obtain proper authorization before testing any systems you don't own.

## Intended Use Cases

✅ Valid uses include:
- Testing your own rate limiting implementations
- Validating rate limiting behavior in development/staging environments
- Security research with explicit permission
- Load testing your own applications

❌ Invalid uses include:
- Attacking websites or services
- Circumventing security measures
- Testing without authorization
- Any malicious or harmful activities

## Legal Notice

Users of this tool bear full responsibility for ensuring their usage complies with:
- Applicable laws and regulations
- Terms of service of target systems
- Security and ethical guidelines
- Data protection requirements

By using this tool, you agree to use it responsibly and accept all liability for any misuse or damage caused.

## Remember

Rate limiting exists for good reasons - to protect services from abuse and ensure fair resource allocation. Always respect these mechanisms and use this tool responsibly.

## Features

- Downloads proxy lists from multiple free sources
- Validates working proxies before use
- Makes requests in parallel with configurable rate limiting (default: 2 requests per 20 seconds)
- Prevents caching by using appropriate headers
- Rotates user agents to avoid detection
- Provides detailed logging and statistics

## Requirements

- Python 3.6+
- Required packages (see requirements.txt)

## Installation

1. Clone this repository or download the files
```bash
git clone https://github.com/tn3w/proxycall.git
cd proxycall
```

2. Create an virtual environment:

```bash
python -m venv venv
source venv/bin/activate
```

Install pip (if you don't have it):

```bash
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
python get-pip.py
```

3. Install the required packages:

```bash
pip install -r requirements.txt
```

## Usage

Basic usage:

```bash
python proxycall.py https://example.com
```

This will:
1. Download and validate HTTPS proxies
2. Make calls to https://example.com using available proxies

Advanced options:
```
usage: proxycall.py [-h] [--wait WAIT] [--timeout TIMEOUT] [--workers WORKERS] [--verbose] url

Make requests through multiple proxies

positional arguments:
  url                Target URL to send requests to

options:
  -h, --help         show this help message and exit
  --wait WAIT        Wait time between requests in milliseconds (for rate-limited mode)
  --timeout TIMEOUT  Timeout for requests in seconds
  --workers WORKERS  Maximum number of concurrent workers
  --verbose          Enable verbose debug logging
```

## Notes

- The script will automatically remove proxies that fail to connect
- If no valid proxies are found, the script will exit
- A summary of successful calls will be displayed at the end

## License
Copyright 2025 TN3W

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
