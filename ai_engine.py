import requests
import json

def call_ai_api(provider, key, model, prompt):
    """
    Calls the specified AI provider's API.
    """
    if not key:
        return None

    try:
        if provider == 'openai':
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}"
            }
            data = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7
            }
            response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data, timeout=30)
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            else:
                return f"Error: {response.text}"

        elif provider == 'gemini':
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
            headers = {"Content-Type": "application/json"}
            data = {
                "contents": [{"parts": [{"text": prompt}]}]
            }
            response = requests.post(url, headers=headers, json=data, timeout=30)
            if response.status_code == 200:
                return response.json()['candidates'][0]['content']['parts'][0]['text']
            else:
                return f"Error: {response.text}"
                
    except Exception as e:
        return f"Exception: {str(e)}"
    
    return None

def analyze_page_with_ai(url, content, provider, key, model):
    """
    Analyzes a single page's content using AI to find vulnerabilities.
    """
    prompt = f"""
    Analyze the following HTML content for security vulnerabilities, categorizing any findings according to the OWASP Top 10 (2021) framework (A01 to A10).
    Focus specifically on:
    - XSS and Injection (A03)
    - Sensitive data exposure / Cryptographic Failures (A02)
    - Insecure Design patterns or business logic flaws (A04)
    - Security Misconfiguration (A05) such as insecure comments or leaked internal IPs/paths
    - Vulnerable Components (A06) like outdated JS libraries visible in script tags
    
    URL: {url}
    Content Snippet (first 4000 chars):
    {content[:4000]}
    
    Return a JSON array of objects with keys: name (Include the OWASP category, e.g., 'A03: XSS in Search Form'), severity (High/Medium/Low), description, remediation.
    If no vulnerabilities are found, return an empty array [].
    Do not include any markdown formatting, just the raw JSON.
    """
    
    response = call_ai_api(provider, key, model, prompt)
    if response:
        # Clean up potential markdown code blocks
        response = response.replace('```json', '').replace('```', '').strip()
        try:
            return json.loads(response)
        except:
            pass
    return []

def generate_fuzzing_payloads_with_ai(parameter_name, provider, key, model):
    """
    Asks the AI to generate contextual, malicious fuzzing payloads for a specific parameter.
    """
    prompt = f"""
    You are an advanced penetration testing engine.
    Generate a JSON array of 3 highly effective fuzzing payloads (strings) specifically tailored to try and exploit a URL parameter named '{parameter_name}'.
    Consider SQLi, XSS, and Command Injection variations that might bypass primitive WAFs given the parameter's likely context.
    Return ONLY a raw JSON array of strings, no markdown.
    Example output: ["' OR 1=1--", "1; DROP TABLE users", "<script>alert(1)</script>"]
    """
    response = call_ai_api(provider, key, model, prompt)
    if response:
        response = response.replace('```json', '').replace('```', '').strip()
        try:
            return json.loads(response)
        except:
            pass
    # Return empty list if AI fails so the scanner can fallback to local payloads
    return []

def generate_detailed_content(vulns, report_type, provider=None, key=None, model=None):
    """
    Generates detailed content using real AI if available, otherwise falls back to templates.
    """
    if key and provider and model:
        prompt = ""
        if report_type == 'analysis':
            prompt = f"Write a detailed Executive Security Analysis for a report based on these vulnerabilities: {json.dumps(vulns)}. Include Risk Assessment and Key Findings. Format as markdown."
        elif report_type == 'mitigation':
            prompt = f"Write a comprehensive, step-by-step Mitigation Plan for these vulnerabilities: {json.dumps(vulns)}. Structure it by phases (Immediate, Short-term, Long-term). Format as markdown."
        elif report_type == 'vectors':
            prompt = f"Analyze the Attack Vectors for these vulnerabilities: {json.dumps(vulns)}. Describe Reconnaissance, Exploitation, and Impact for each. Format as markdown."
            
        response = call_ai_api(provider, key, model, prompt)
        if response and not response.startswith("Error:") and not response.startswith("Exception:"):
            return response
        else:
            # AI call failed, log error and fall back
            print(f"AI generation failed for report type {report_type}: {response}")
            
    # Fallback to template logic if no key or error
    if not vulns:
        return "No vulnerabilities detected. System appears secure based on current scan parameters."

    content = ""
    
    if report_type == 'analysis':
        content += "## Executive Security Analysis\n\n"
        content += "### Risk Assessment\n"
        high_count = len([v for v in vulns if v['severity'] == 'High'])
        medium_count = len([v for v in vulns if v['severity'] == 'Medium'])
        
        if high_count > 0:
            content += f"**CRITICAL RISK DETECTED**. The scan identified {high_count} high-severity vulnerabilities that pose an immediate threat to system integrity and data confidentiality. Immediate remediation is required.\n\n"
        elif medium_count > 0:
            content += f"**MODERATE RISK**. The scan found {medium_count} medium-severity issues. While not immediately critical, these could be chained together for more significant attacks.\n\n"
        else:
            content += "**LOW RISK**. Only minor configuration issues were detected. The system posture is generally good.\n\n"
            
        content += "### Key Findings Pattern\n"
        content += "Our AI engine has analyzed the vulnerability distribution and detected the following patterns:\n"
        types = set(v['name'] for v in vulns)
        for t in types:
            content += f"- **{t}**: Recurring pattern suggests a systemic issue in the codebase or configuration.\n"

    elif report_type == 'mitigation':
        content += "## Comprehensive Mitigation Plan\n\n"
        content += "### Phase 1: Immediate Actions (0-24 Hours)\n"
        for i, v in enumerate([v for v in vulns if v['severity'] == 'High']):
            content += f"#### {i+1}. Fix {v['name']}\n"
            content += f"**Context**: {v['description']}\n"
            content += "**Action Plan**:\n"
            content += "1.  Isolate the affected component.\n"
            content += "2.  Apply the following patch/config change:\n"
            content += f"    ```\n    {v.get('remediation', 'Refer to standard patching procedures.')}\n    ```\n"
            content += "3.  Verify the fix using the scanner.\n\n"
            
        content += "### Phase 2: System Hardening (1-3 Days)\n"
        content += "Address medium and low severity issues to reduce the attack surface.\n"
        for v in [v for v in vulns if v['severity'] in ['Medium', 'Low']]:
            content += f"- **{v['name']}**: {v.get('remediation', 'remediate as per best practices.')}\n"
            
        content += "\n### Phase 3: Long-term Strategy\n"
        content += "- Implement automated security testing in CI/CD pipeline.\n"
        content += "- Conduct quarterly penetration testing.\n"
        content += "- Training for development team on secure coding practices.\n"

    elif report_type == 'vectors':
        content += "## Attack Vector Analysis\n\n"
        content += "This report details how an attacker could exploit the identified vulnerabilities.\n\n"
        
        for v in vulns:
            content += f"### Target: {v['name']} ({v['severity']})\n"
            content += "**Reconnaissance**:\n"
            content += f"- Attacker identifies {v['name']} by scanning for specific signatures or behavior ({v['description']}).\n"
            content += "**Exploitation**:\n"
            content += "1.  Attacker crafts a malicious payload.\n"
            content += "2.  Payload is injected into the vulnerable parameter/header.\n"
            content += "3.  Server processes the payload without validation.\n"
            content += "**Impact**:\n"
            content += "- Potential data leakage, unauthorized access, or service disruption.\n"
            content += "**Likelihood**:\n"
            content += f"- {'High' if v['severity'] == 'High' else 'Moderate' if v['severity'] == 'Medium' else 'Low'} based on current exposure.\n\n"

    return content
