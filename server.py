from flask import Flask, request, Response, stream_with_context, send_from_directory
import requests
import json
import re
import time
from urllib.parse import urljoin, urlparse
from collections import deque
import threading
import concurrent.futures
import html as html_lib
import ipaddress
import socket
import urllib3
import random
import os

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__, static_folder='.', static_url_path='')

@app.after_request
def add_security_headers(response):
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' https://api.openai.com https://generativelanguage.googleapis.com"
    return response

# Simple in-memory cache to avoid re-scanning same URLs in short time
scan_cache = {}

# OOB vulnerability tracking
oob_findings = {}


class Crawler:
    def __init__(self, start_url, max_depth=2, user_agent=None, proxy_url=None, follow_redirects=True, auth=None, deep_js_scan=False, stealth_mode=True):
        self.start_url = start_url
        self.max_depth = max_depth
        self.user_agent = user_agent
        self.proxy_url = proxy_url
        self.follow_redirects = follow_redirects
        self.auth = auth
        self.deep_js_scan = deep_js_scan
        self.stealth_mode = stealth_mode
        self.visited = set()
        self.pages = [] # List of (url, content)
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/111.0"
        ]

    def is_safe_url(self, url):
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname
            if not hostname:
                return False
            
            # Resolve hostname to IP
            ip = socket.gethostbyname(hostname)
            ip_obj = ipaddress.ip_address(ip)
            
            # Check if private or loopback
            if ip_obj.is_private or ip_obj.is_loopback:
                return False
                
            return True
        except:
            return False

    def crawl(self):
        if not self.is_safe_url(self.start_url):
             yield {"type": "log", "message": f"Blocked restricted URL: {self.start_url}", "level": "error"}
             return

        queue = deque([(self.start_url, 0)])
        self.visited.add(self.start_url)
        
        domain = urlparse(self.start_url).netloc

        while queue:
            url, depth = queue.popleft()
            
            if depth > self.max_depth:
                continue

            if not self.is_safe_url(url):
                yield {"type": "log", "message": f"Blocked restricted URL: {url}", "level": "error"}
                continue

            try:
                yield {"type": "log", "message": f"Crawling {url} (Depth: {depth})..."}
                
                current_ua = random.choice(self.user_agents) if self.stealth_mode else self.user_agent
                req_headers = {'User-Agent': current_ua} if current_ua else {}
                proxies = {'http': self.proxy_url, 'https': self.proxy_url} if self.proxy_url else None
                
                if self.stealth_mode:
                    time.sleep(random.uniform(0.5, 1.2))
                    
                response = requests.get(url, timeout=10, headers=req_headers, proxies=proxies, allow_redirects=self.follow_redirects, auth=self.auth, verify=False)
                
                self.pages.append((url, response.text))
                
                if response.status_code != 200:
                    yield {"type": "log", "message": f"Warning: {url} returned status {response.status_code}", "level": "warning"}
                    
                if depth < self.max_depth:
                    links = self.extract_links(response.text, url)
                    for link in links:
                        # Only crawl same domain (relax www. check)
                        link_domain = urlparse(link).netloc.replace('www.', '')
                        base_domain = domain.replace('www.', '')
                        if link_domain == base_domain and link not in self.visited:
                            self.visited.add(link)
                            queue.append((link, depth + 1))
            except Exception as e:
                yield {"type": "log", "message": f"Failed to crawl {url}: {str(e)}", "level": "error"}

    def extract_links(self, html, base_url):
        # Simple regex for link extraction to avoid heavy dependencies like bs4 if not present
        # Matches href="..." or href='...'
        pattern = r'href=["\'](.*?)["\']'
        links = re.findall(pattern, html)
        absolute_links = []
        for link in links:
            # Skip anchors, javascript, mailto
            if link.startswith(('#', 'javascript:', 'mailto:')):
                continue
            absolute_links.append(urljoin(base_url, link))
            
        if self.deep_js_scan:
            script_srcs = re.findall(r'<script\s+[^>]*src=["\'](.*?)["\']', html, re.IGNORECASE)
            for src in script_srcs:
               js_url = urljoin(base_url, src)
               if js_url not in self.visited:
                   self.visited.add(js_url)
                   try:
                       current_ua = random.choice(self.user_agents) if self.stealth_mode else self.user_agent
                       req_headers = {'User-Agent': current_ua} if current_ua else {}
                       if self.stealth_mode:
                           time.sleep(random.uniform(0.1, 0.5))
                       js_res = requests.get(js_url, timeout=5, headers=req_headers, verify=False)
                       if js_res.status_code == 200:
                           self.pages.append((js_url, js_res.text))
                           # Extremely naive API endpoint fetch from minified JS
                           endpoints = re.findall(r'["\']((?:/api/|/v1/|/users/)[a-zA-Z0-9_\-\/]+)["\']', js_res.text)
                           for ep in endpoints:
                               absolute_links.append(urljoin(base_url, ep))
                   except:
                       pass
                       
        return absolute_links

class HeuristicScanner:
    def __init__(self, user_agent=None, proxy_url=None, follow_redirects=True, auth=None):
        self.vulnerabilities = []
        self.user_agent = user_agent
        self.proxy_url = proxy_url
        self.follow_redirects = follow_redirects
        self.auth = auth

    def scan_page(self, url, content):
        vulns = []
        
        # Check 1: Missing Security Headers
        try:
            req_headers = {'User-Agent': self.user_agent} if self.user_agent else {}
            proxies = {'http': self.proxy_url, 'https': self.proxy_url} if self.proxy_url else None
            r = requests.head(url, timeout=5, headers=req_headers, proxies=proxies, allow_redirects=self.follow_redirects, auth=self.auth, verify=False)
            headers = r.headers
            if 'X-Frame-Options' not in headers:
                vulns.append({
                    "name": "Missing X-Frame-Options Header",
                    "severity": "Low",
                    "description": "The page is missing the X-Frame-Options header, which could allow clickjacking attacks.",
                    "remediation": "Configure your web server to send the 'X-Frame-Options' header with the value 'DENY' or 'SAMEORIGIN'.\n\nExample (Nginx):\nadd_header X-Frame-Options SAMEORIGIN;"
                })
            if 'Content-Security-Policy' not in headers:
                vulns.append({
                    "name": "Missing Content-Security-Policy",
                    "severity": "Medium",
                    "description": "Content Security Policy (CSP) is an added layer of security that helps to detect and mitigate certain types of attacks, including Cross-Site Scripting (XSS).",
                    "remediation": "Implement a Content Security Policy (CSP) by adding the 'Content-Security-Policy' HTTP header.\n\nStart with a restrictive policy and loosen it as needed:\nContent-Security-Policy: default-src 'self';"
                })
            if 'Strict-Transport-Security' not in headers and url.startswith('https://'):
                vulns.append({
                    "name": "A02: Missing Strict-Transport-Security (HSTS)",
                    "severity": "Medium",
                    "description": "The page is loaded over HTTPS but lacks the HSTS header, leaving it vulnerable to downgrade attacks.",
                    "remediation": "Add the 'Strict-Transport-Security' header to enforce HTTPS."
                })
            if 'Server' in headers or 'X-Powered-By' in headers:
                vulns.append({
                    "name": "A05: Security Misconfiguration - Target IP/Framework Leakage",
                    "severity": "Low",
                    "description": "Server or X-Powered-By headers are exposed, revealing backend technology versions.",
                    "remediation": "Configure the web server to hide the Server signature and remove X-Powered-By headers."
                })
        except:
            pass

        # Check 2: Password fields over HTTP
        if url.startswith('http://'):
            if '<input type="password"' in content or "<input type='password'" in content:
                vulns.append({
                    "name": "Password Field over Insecure HTTP",
                    "severity": "High",
                    "description": "Login forms should always be served over HTTPS to protect credentials.",
                    "remediation": "Ensure that the login page and all pages handling sensitive information are served over HTTPS. Obtain an SSL/TLS certificate and configure your server to redirect HTTP traffic to HTTPS."
                })

        # Check 3: Potential SQL Injection in URL parameters
        if '?' in url and '=' in url:
            vulns.append({
                "name": "Potential SQL Injection Point",
                "severity": "Low",
                "description": f"URL parameters found in {url}. Ensure these are properly sanitized.",
                "remediation": "Use parameterized queries or prepared statements for all database access. Avoid constructing SQL queries by concatenating strings with user input."
            })

        # Check 4: Forms without CSRF tokens (Naive check)
        if '<form' in content and 'csrf' not in content.lower():
             vulns.append({
                "name": "Potential CSRF Vulnerability",
                "severity": "Medium",
                "description": "Form detected without apparent CSRF token field.",
                "remediation": "Include a unique, unpredictable CSRF token in all state-changing forms. Verify this token on the server side before processing the request."
            })

        # Check 5: A08 Software and Data Integrity Failures
        script_tags = re.findall(r'<script\s+[^>]*src=[\'"]([^\'"]+)[\'"][^>]*>', content, re.IGNORECASE)
        for script in script_tags:
            # Check if it's an external script and if the tag has integrity attribute
            if (script.startswith('http') or script.startswith('//')) and 'integrity=' not in content:
                 vulns.append({
                    "name": "A08: Software and Data Integrity Failures",
                    "severity": "Medium",
                    "description": f"External script {script} is loaded without Subresource Integrity (SRI).",
                    "remediation": "Add 'integrity' and 'crossorigin' attributes to external script tags to ensure they haven't been tampered with."
                })
                 break # Only flag once per page to avoid spam

        # Check 6: A06 Vulnerable and Outdated Components (Naive)
        if 'jquery-1.' in content or 'jquery-2.' in content:
            vulns.append({
                "name": "A06: Vulnerable Components (Outdated jQuery)",
                "severity": "Medium",
                "description": "Potential inclusion of an outdated, vulnerable version of jQuery (1.x or 2.x).",
                "remediation": "Update jQuery to the latest secure version (3.x)."
            })

        # Check 7: Deep Secrets Extraction (Tokens, Keys)
        secrets = {
            "AWS Access Key": r"(AKIA[0-9A-Z]{16})",
            "JWT Token": r"(eyJ[a-zA-Z0-9-_]+\.eyJ[a-zA-Z0-9-_]+\.[a-zA-Z0-9-_]+)",
            "Stripe Key": r"(sk_live_[0-9a-zA-Z]{24})",
            "Generic Bearer Token": r"(Bearer\s+[a-zA-Z0-9\-_]+)"
        }
        for secret_name, pattern in secrets.items():
            matches = re.finditer(pattern, content)
            for match in matches:
                vulns.append({
                    "name": f"A02/A06: Sensitive Data Exposure - {secret_name}",
                    "severity": "High",
                    "description": f"Potential {secret_name} found in the page content/source. Fragment: {match.group(0)[:15]}...",
                    "remediation": "Revoke the exposed key immediately and remove it from frontend code or repositories."
                })

        # Check 8: Custom Template Rules
        rules_dir = os.path.join(os.path.dirname(__file__), 'rules')
        if os.path.exists(rules_dir):
            for rule_file in os.listdir(rules_dir):
                if rule_file.endswith('.json'):
                    try:
                        with open(os.path.join(rules_dir, rule_file), 'r') as fp:
                            rule = json.load(fp)
                            if rule.get('match_type') == 'regex':
                                for pattern in rule.get('patterns', []):
                                    if re.search(pattern, content):
                                        vulns.append({
                                            "name": rule.get('name', 'Custom Template Match'),
                                            "severity": rule.get('severity', 'Medium'),
                                            "description": rule.get('description', f'Matched custom rule: {rule.get("id")}'),
                                            "remediation": rule.get('remediation', 'Review custom template guidelines.')
                                        })
                                        break # flag once per rule
                    except Exception as e:
                        pass
                        
        return vulns

from ai_engine import call_ai_api, analyze_page_with_ai, generate_detailed_content, generate_fuzzing_payloads_with_ai

class ActiveScanner:
    def __init__(self, user_agent=None, proxy_url=None, follow_redirects=True, auth=None, ai_provider=None, api_key=None, ai_model=None):
        self.user_agent = user_agent
        self.proxy_url = proxy_url
        self.follow_redirects = follow_redirects
        self.auth = auth
        self.ai_provider = ai_provider
        self.api_key = api_key
        self.ai_model = ai_model
        
    @staticmethod
    def get_static_payloads():
        payloads = []
        payload_dir = os.path.join(os.path.dirname(__file__), 'payloads')
        if os.path.exists(payload_dir):
            for file_name in ['sqli.txt', 'xss.txt', 'cmdi.txt']:
                file_path = os.path.join(payload_dir, file_name)
                if os.path.exists(file_path):
                    try:
                        with open(file_path, 'r') as fp:
                            content = fp.read()
                            payloads.extend([line.strip() for line in content.splitlines() if line.strip()])
                    except:
                        pass
        if not payloads:
            payloads = ["<script>alert('XSS')</script>", "' OR '1'='1"]
        return payloads

    def scan_url(self, url):
        vulns = []
        if '?' not in url:
             return vulns
             
        parsed = urlparse(url)
        params = parsed.query.split('&')
        param_names = [p.split('=')[0] for p in params if '=' in p]
             
        try:
             req_headers = {'User-Agent': self.user_agent} if self.user_agent else {}
             proxies = {'http': self.proxy_url, 'https': self.proxy_url} if self.proxy_url else None

             for param in param_names:
                 # Generate AI contextual payloads for this parameter
                 payloads = []
                 if self.api_key:
                     payloads = generate_fuzzing_payloads_with_ai(param, self.ai_provider, self.api_key, self.ai_model)
                 if not payloads:
                     payloads = self.get_static_payloads()
                     
                 for payload in payloads:
                     test_url = url.replace(f"{param}=", f"{param}={payload}")
                     r = requests.get(test_url, timeout=5, headers=req_headers, proxies=proxies, allow_redirects=self.follow_redirects, auth=self.auth, verify=False)
                     
                     if payload in r.text and "<script" in payload.lower():
                          vulns.append({
                              "name": f"A03: Injection (AI Reflected XSS on '{param}')",
                              "severity": "High",
                              "description": f"URL parameter '{param}' reflected unsanitized AI payload: {payload}",
                              "remediation": "Sanitize and HTML-encode all user input before reflecting it."
                          })
                          
                     if "syntax error" in r.text.lower() or "mysql" in r.text.lower() or r.status_code == 500:
                          if "script" not in payload.lower():
                              vulns.append({
                                  "name": f"A03: Injection (AI Potential SQLi on '{param}')",
                                  "severity": "High",
                                  "description": f"Error detected when injecting AI payload into '{param}': {payload}",
                                  "remediation": "Use parameterized queries to prevent SQL injection."
                              })
                  
                 # A10 / OOB Blind Injection check
                 oob_id = f"oob_{int(time.time())}_{param}"
                 oob_payload = f"http://127.0.0.1:5000/callback/{oob_id}"
                 test_url_oob = url.replace(f"{param}=", f"{param}={oob_payload}")
                 requests.get(test_url_oob, timeout=2, headers=req_headers, proxies=proxies, allow_redirects=self.follow_redirects, auth=self.auth, verify=False)
                 
                 # Brief sleep to allow async webhook ping
                 time.sleep(0.5)
                 if oob_findings.get(oob_id):
                     vulns.append({
                         "name": f"A10: Server-Side Request Forgery (Confirmed on '{param}')",
                         "severity": "High",
                         "description": f"Parameter '{param}' triggered a verified out-of-band request back to the scanner.",
                         "remediation": "Validate all user-supplied URLs against an allowlist of permitted domains."
                     })
                 
        except:
             pass
        return vulns

@app.route('/callback/<vuln_id>')
def oob_callback(vuln_id):
    oob_findings[vuln_id] = True
    return Response("OK", status=200)

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/scan', methods=['POST'])
def scan():
    data = request.get_json()
    target_url = data.get('target_url')
    crawl_depth = data.get('crawl_depth', 2)
    ai_provider = data.get('ai_provider')
    api_key = data.get('api_key')
    ai_model = data.get('ai_model')
    
    user_agent = data.get('user_agent', 'Mozilla/5.0 (AI Security Scanner)')
    proxy_url = data.get('proxy_url')
    follow_redirects = data.get('follow_redirects', True)
    
    auth_tuple = None
    if data.get('basic_auth') and data.get('username') and data.get('password'):
        auth_tuple = (data.get('username'), data.get('password'))
    
    if not target_url:
        return Response("Missing target_url", status=400)
        
    active_scan = data.get('active_scan', False)
    deep_js_scan = data.get('deep_js_scan', False)
    stealth_mode = data.get('stealth_mode', True)

    def generate():
        yield json.dumps({"type": "log", "message": "Initializing scan...", "step": "Initializing..."}) + "\n"
        
        crawler = Crawler(target_url, max_depth=crawl_depth, user_agent=user_agent, proxy_url=proxy_url, follow_redirects=follow_redirects, auth=auth_tuple, deep_js_scan=deep_js_scan, stealth_mode=stealth_mode)
        heuristic_scanner = HeuristicScanner(user_agent=user_agent, proxy_url=proxy_url, follow_redirects=follow_redirects, auth=auth_tuple)
        
        total_vulns = []
        pages_scanned = 0
        
        # Phase 1: Crawling & Parallel Scanning
        yield json.dumps({"type": "log", "message": "Starting crawl and parallel analysis...", "step": "Crawling & Analyzing..."}) + "\n"
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_url = {}
            
            for event in crawler.crawl():
                if isinstance(event, dict) and event.get("type") == "log":
                    yield json.dumps(event) + "\n"
                else:
                    # It's a page content tuple (url, content) - logic inside crawler needs adjustment or we access crawler.pages
                    pass # pragma: no cover
            
            # After crawl (or during, if we refactor crawler to yield pages), we process pages.
            # For simplicity, we iterate over crawler.pages which is populated by crawl()
            
            pages_scanned = len(crawler.pages)
            yield json.dumps({"type": "progress", "percent": 30, "stats": {"total": 0, "pages": pages_scanned, "requests": pages_scanned, "risk": "Calculating...", "high": 0, "medium": 0, "low": 0}}) + "\n"

            # Heuristic Scan
            for url, content in crawler.pages:
                h_vulns = heuristic_scanner.scan_page(url, content)
                for v in h_vulns:
                    # Deduplicate
                    if v not in total_vulns:
                        total_vulns.append(v)
                        yield json.dumps({"type": "vulnerability", **v}) + "\n"

            # Active Scan
            if active_scan:
                yield json.dumps({"type": "log", "message": "Starting active AI-driven fuzzing and OOB testing...", "step": "Active Scanning..."}) + "\n"
                active_scanner = ActiveScanner(user_agent=user_agent, proxy_url=proxy_url, follow_redirects=follow_redirects, auth=auth_tuple, ai_provider=ai_provider, api_key=api_key, ai_model=ai_model)
                for url, content in crawler.pages:
                    a_vulns = active_scanner.scan_url(url)
                    for v in a_vulns:
                        if v not in total_vulns:
                            total_vulns.append(v)
                            yield json.dumps({"type": "vulnerability", **v}) + "\n"

            # AI Parallel Scan
            if api_key:
                yield json.dumps({"type": "log", "message": f"Starting AI analysis on {len(crawler.pages)} pages using {ai_provider}...", "step": "AI Analysis..."}) + "\n"
                
                futures = []
                for url, content in crawler.pages:
                    futures.append(executor.submit(analyze_page_with_ai, url, content, ai_provider, api_key, ai_model))
                
                completed = 0
                for future in concurrent.futures.as_completed(futures):
                    ai_vulns = future.result()
                    completed += 1
                    if ai_vulns:
                        for v in ai_vulns:
                            v['name'] = f"{v['name']} (AI)" # Tag as AI
                            # Deduplicate
                            if v not in total_vulns:
                                total_vulns.append(v)
                                yield json.dumps({"type": "vulnerability", **v}) + "\n"
                    
                    percent = 30 + int((completed / len(crawler.pages)) * 60)
                    yield json.dumps({"type": "progress", "percent": percent, "stats": {"total": len(total_vulns), "pages": pages_scanned, "requests": pages_scanned + completed, "risk": "Calculating...", "high": 0, "medium": 0, "low": 0}}) + "\n"
            else:
                 yield json.dumps({"type": "log", "message": "Skipping AI analysis (No API Key provided).", "step": "Skipping AI..."}) + "\n"

        # Calculate Stats
        high = len([v for v in total_vulns if v['severity'] == 'High'])
        medium = len([v for v in total_vulns if v['severity'] == 'Medium'])
        low = len([v for v in total_vulns if v['severity'] == 'Low'])
        
        risk_score = min(100, (high * 20) + (medium * 10) + (low * 2))
        risk_label = f"{risk_score}%"

        # Generate Recommendations (AI or Static)
        recommendations = []
        if api_key:
             rec_prompt = f"Given these vulnerabilities: {[v['name'] for v in total_vulns]}, provide 3 concise security recommendations."
             ai_recs = call_ai_api(ai_provider, api_key, ai_model, rec_prompt)
             if ai_recs:
                 recommendations = [r.strip('- ').strip() for r in ai_recs.split('\n') if r.strip()]
        
        if not recommendations:
            recommendations = ["Enable HTTPS everywhere.", "Implement Content Security Policy.", "Sanitize all user inputs."]

        heatmap_data = {
            "high": high,
            "medium": medium,
            "low": low,
            "recommendations": recommendations[:5]
        }
        
        yield json.dumps({"type": "heatmap", "data": heatmap_data}) + "\n"
        yield json.dumps({"type": "progress", "percent": 100, "stats": {"total": len(total_vulns), "pages": pages_scanned, "requests": pages_scanned * 2, "risk": risk_label, "high": high, "medium": medium, "low": low}}) + "\n"
        yield json.dumps({"type": "log", "message": "Scan complete.", "step": "Finished"}) + "\n"

    return Response(stream_with_context(generate()), content_type='application/x-ndjson')



@app.route('/generate_report', methods=['POST'])
def generate_report():
    data = request.get_json()
    vulns = data.get('vulnerabilities', [])
    report_type = data.get('type')
    ai_provider = data.get('ai_provider')
    api_key = data.get('api_key')
    ai_model = data.get('ai_model')
    
    content = generate_detailed_content(vulns, report_type, ai_provider, api_key, ai_model)
    
    # Convert markdown to HTML for display
    # Simple conversion for bold, headers, code blocks
    html_content = content.replace('\n', '<br>')
    html_content = re.sub(r'### (.*?)<br>', r'<h3>\1</h3>', html_content)
    html_content = re.sub(r'## (.*?)<br>', r'<h2>\1</h2>', html_content)
    html_content = re.sub(r'#### (.*?)<br>', r'<h4>\1</h4>', html_content)
    html_content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html_content)
    html_content = re.sub(r'```(.*?)```', r'<pre><code>\1</code></pre>', html_content, flags=re.DOTALL)
    
    return json.dumps({"content": html_content})

@app.route('/download_report', methods=['POST'])
def download_report():
    data = request.get_json()
    vulns = data.get('vulnerabilities', [])
    fmt = data.get('format', 'html')
    report_content = generate_detailed_content(vulns, 'analysis') + "\n\n" + \
                     generate_detailed_content(vulns, 'mitigation') + "\n\n" + \
                     generate_detailed_content(vulns, 'vectors')
    
    if fmt == 'json':
        return Response(
            json.dumps({"vulnerabilities": vulns, "detailed_report": report_content}, indent=2),
            mimetype='application/json',
            headers={'Content-Disposition': 'attachment;filename=security_report.json'}
        )
    elif fmt == 'md':
        return Response(
            report_content,
            mimetype='text/markdown',
            headers={'Content-Disposition': 'attachment;filename=security_report.md'}
        )
    else: # HTML
        # So the plan is:
        # 1. Escape `report_content`.
        # 2. Apply formatting replacements.
        
        safe_content = html_lib.escape(report_content)
        
        # Re-apply formatting logic on the ESCAPED content
        html_content = safe_content.replace(chr(10), '<br>')
        html_content = re.sub(r'### (.*?)<br>', r'<h3>\1</h3>', html_content)
        html_content = re.sub(r'## (.*?)<br>', r'<h2>\1</h2>', html_content)
        html_content = re.sub(r'#### (.*?)<br>', r'<h4>\1</h4>', html_content)
        html_content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html_content)
        html_content = re.sub(r'```(.*?)```', r'<pre><code>\1</code></pre>', html_content, flags=re.DOTALL)

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Security Scan Report</title>
            <style>
                body {{ font-family: sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; }}
                h2 {{ color: #2c3e50; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
                h3 {{ color: #34495e; }}
                pre {{ background: #f8f9fa; padding: 15px; border-radius: 5px; overflow-x: auto; }}
                strong {{ color: #e74c3c; }}
            </style>
        </head>
        <body>
            <h1>Security Scan Comprehensive Report</h1>
            <p>Generated on {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
            <hr>
            {html_content}
        </body>
        </html>
        """
        
        return Response(
            html,
            mimetype='text/html',
            headers={'Content-Disposition': 'attachment;filename=security_report.html'}
        )

if __name__ == '__main__': # pragma: no cover
    # CRITICAL: Debug mode disabled for production security
    app.run(debug=False, port=5000)
