import asyncio
import aiohttp
import os
import json
import sys
import time
import base64
from datetime import datetime

# Constants
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY")
DEVIN_API_KEY = os.getenv("DEVIN_API_KEY")
DEVIN_API_BASE = "https://api.devin.ai/v1"
SONAR_TOKEN = os.getenv("SONAR_TOKEN")
SONAR_ORG = os.getenv("SONAR_ORG")
SONAR_PROJECT_KEY = os.getenv("SONAR_PROJECT_KEY")

def log(message, level="INFO"):
    """Log a message with the specified level."""
    print(f"{datetime.now().isoformat()} | {level} | {message}")

async def get_sonarcloud_issues():
    """Retrieve issues from SonarCloud."""
    if not SONAR_TOKEN or not SONAR_ORG or not SONAR_PROJECT_KEY:
        log("Missing SonarCloud configuration", "ERROR")
        return []
        
    try:
        async with aiohttp.ClientSession() as session:
            auth = aiohttp.BasicAuth(SONAR_TOKEN, '')
            url = f"https://sonarcloud.io/api/issues/search?projects={SONAR_PROJECT_KEY}&resolved=false&types=VULNERABILITY,BUG"
            
            async with session.get(url, auth=auth) as response:
                if response.status != 200:
                    log(f"Error retrieving SonarCloud issues: {await response.text()}", "ERROR")
                    return []
                    
                result = await response.json()
                issues = result.get("issues", [])
                
                if not issues:
                    log("No issues found in SonarCloud")
                    return []
                    
                # Process and format issues
                formatted_issues = []
                for issue in issues:
                    formatted_issue = {
                        "key": issue.get("key"),
                        "message": issue.get("message"),
                        "component": issue.get("component"),
                        "severity": issue.get("severity"),
                        "type": issue.get("type")
                    }
                    formatted_issues.append(formatted_issue)
                
                log(f"Found {len(formatted_issues)} issues in SonarCloud")
                return formatted_issues
    except Exception as e:
        log(f"Unexpected error when retrieving SonarCloud issues: {str(e)}", "ERROR")
        return []

async def delegate_tasks_to_devin(issues):
    """Delegate the task of fixing multiple issues to Devin AI in a single session."""
    if not DEVIN_API_KEY:
        log("DEVIN_API_KEY environment variable is not set", "ERROR")
        return None
        
    try:
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {DEVIN_API_KEY}"}
            
            # Add timestamp to make branch name unique
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            branch_name = f"devin/fix-batch-{timestamp}"
            
            # Create a comprehensive prompt with all issues
            prompt = f"""
            Fix the following vulnerabilities in {GITHUB_REPOSITORY}:
            
            """
            
            # Add each issue to the prompt
            for i, issue in enumerate(issues, 1):
                prompt += f"""
                Issue {i}:
                - Key: {issue['key']}
                - Message: {issue['message']}
                - Component: {issue['component']}
                - Severity: {issue['severity']}
                - Type: {issue['type']}
                
                """
            
            prompt += f"""
            For each issue:
            1. Create a separate branch for each fix using the pattern 'devin/fix-{timestamp}-[issue-key]'.
            2. Implement the fix.
            3. Write a detailed commit message explaining the changes:
                - Issue Key: [issue-key]
                - Component: [component]
                - Fixed by Devin AI at {datetime.now().isoformat()}
                - Include 'Co-authored-by: github-actions[bot] <github-actions[bot]@users.noreply.github.com>'.
            4. Push the branch to the remote repository.
            5. Open a pull request with a description of the fix.
            
            Process each issue independently, creating a separate PR for each fix.
            """
            
            log(f"Creating Devin session to handle {len(issues)} issues")
            data = {
                "prompt": prompt, 
                "idempotent": True,
                # Uncomment and set these optional parameters as needed
                # "snapshot_id": None,  # ID of a machine snapshot to use
                # "playbook_id": None,  # ID of a playbook to follow
                # "unlisted": True,     # Whether the session should be unlisted
                # "max_acu_limit": 100  # Maximum ACU limit for the session
            }
            
            async with session.post(f"{DEVIN_API_BASE}/sessions", json=data, headers=headers) as response:
                if response.status != 200:
                    log(f"Error delegating tasks to Devin: {await response.text()}", "ERROR")
                    return None
                    
                result = await response.json()
                log(f"Devin session created: {json.dumps(result, indent=2)}")
                return result
    except aiohttp.ClientError as e:
        log(f"Network error when connecting to Devin API: {str(e)}", "ERROR")
        return None
    except Exception as e:
        log(f"Unexpected error when creating Devin session: {str(e)}", "ERROR")
        return None
        
async def monitor_devin_session(session_id):
    """Monitor Devin's progress until it completes the task."""
    if not DEVIN_API_KEY:
        log("DEVIN_API_KEY environment variable is not set", "ERROR")
        return None
        
    try:
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {DEVIN_API_KEY}"}
            max_retries = 3
            retry_count = 0
            
            while True:
                try:
                    async with session.get(f"{DEVIN_API_BASE}/sessions/{session_id}", headers=headers) as response:
                        if response.status != 200:
                            retry_count += 1
                            if retry_count > max_retries:
                                log(f"Error monitoring Devin session after {max_retries} retries: {await response.text()}", "ERROR")
                                return None
                            log(f"Error monitoring Devin session (retry {retry_count}/{max_retries}): {await response.text()}", "WARNING")
                            await asyncio.sleep(5)
                            continue
                            
                        result = await response.json()
                        status = result.get("status")
                        log(f"Devin session status: {status}")
                        
                        if status in ["completed", "stopped"]:
                            log(f"Devin completed the task: {json.dumps(result, indent=2)}")
                            return result
                        elif status == "blocked":
                            log("Devin encountered an issue. Please check manually.", "WARNING")
                            return None
                        
                        # Wait longer between checks to avoid rate limiting
                        await asyncio.sleep(10)
                except aiohttp.ClientError as e:
                    retry_count += 1
                    if retry_count > max_retries:
                        log(f"Network error when monitoring Devin session after {max_retries} retries: {str(e)}", "ERROR")
                        return None
                    log(f"Network error when monitoring Devin session (retry {retry_count}/{max_retries}): {str(e)}", "WARNING")
                    await asyncio.sleep(5)
    except Exception as e:
        log(f"Unexpected error when monitoring Devin session: {str(e)}", "ERROR")
        return None

async def create_pr_directly(issue, branch_name):
    """Create PR using GitHub API directly if Devin PR creation fails."""
    if not GITHUB_TOKEN:
        log("No GitHub token available for direct PR creation", "ERROR")
        return False
        
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"token {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            # PR details
            body = f"""Fixed vulnerability in {issue['component']} identified by SonarCloud.

Issue Key: {issue['key']}
Component: {issue['component']}
Fixed by Devin AI Remediation

Co-authored-by: github-actions[bot] <github-actions[bot]@users.noreply.github.com>"""
            
            data = {
                "title": f"Fix: {issue['message']}",
                "body": body,
                "head": branch_name,
                "base": "master"
            }
            
            api_url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/pulls"
            
            async with session.post(api_url, headers=headers, json=data) as response:
                result = await response.json()
                
                if response.status == 201:
                    log(f"Successfully created PR #{result['number']}: {result['html_url']}")
                    return True
                else:
                    log(f"Failed to create PR using GitHub API: {json.dumps(result, indent=2)}", "ERROR")
                    
                    # Try with full repo name in head if needed
                    if "head" in str(result.get("errors", [])):
                        log("Trying with full repo name in head...")
                        owner = GITHUB_REPOSITORY.split('/')[0]
                        data["head"] = f"{owner}:{branch_name}"
                        
                        async with session.post(api_url, headers=headers, json=data) as retry_response:
                            retry_result = await retry_response.json()
                            
                            if retry_response.status == 201:
                                log(f"Successfully created PR #{retry_result['number']}: {retry_result['html_url']}")
                                return True
                            else:
                                log(f"Failed to create PR with full repo name: {json.dumps(retry_result, indent=2)}", "ERROR")
                    
                    return False
    except Exception as e:
        log(f"Unexpected error when creating PR directly: {str(e)}", "ERROR")
        return False

async def create_fallback_pr(issues):
    """Create a fallback PR if all other methods fail."""
    if not issues or not GITHUB_TOKEN:
        log("No issues found or no GitHub token available for fallback PR", "ERROR")
        return False
        
    try:
        # Use GitHub API to create a fallback PR
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"token {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            # Create a unique branch name
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            branch_name = f"devin/fallback-fix-{timestamp}"
            
            # Get the latest commit SHA on master
            api_url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/git/refs/heads/master"
            async with session.get(api_url, headers=headers) as response:
                if response.status != 200:
                    log(f"Error getting master branch reference: {await response.text()}", "ERROR")
                    return False
                    
                master_data = await response.json()
                master_sha = master_data["object"]["sha"]
                
            # Create a new branch reference
            branch_ref_url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/git/refs"
            branch_data = {
                "ref": f"refs/heads/{branch_name}",
                "sha": master_sha
            }
            
            async with session.post(branch_ref_url, headers=headers, json=branch_data) as response:
                if response.status != 201:
                    log(f"Error creating branch: {await response.text()}", "ERROR")
                    return False
                    
            # Create a new file with the report
            report_content = f"# Devin Remediation Report\n\n"
            report_content += f"Generated: {datetime.now().isoformat()}\n\n"
            report_content += "## Issues Found\n\n"
            
            for issue in issues:
                report_content += f"- {issue['message']} in {issue['component']}\n"
                
            # Encode content to base64
            encoded_content = base64.b64encode(report_content.encode()).decode()
            
            # Create the file
            file_path = ".github/devin-remediation-report.md"
            file_url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/contents/{file_path}"
            file_data = {
                "message": "Add Devin remediation report",
                "content": encoded_content,
                "branch": branch_name
            }
            
            async with session.put(file_url, headers=headers, json=file_data) as response:
                if response.status not in [200, 201]:
                    log(f"Error creating file: {await response.text()}", "ERROR")
                    return False
                    
            # Create PR
            pr_url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/pulls"
            pr_data = {
                "title": "Fallback: Devin Remediation Report",
                "body": f"""# Fallback PR for Devin Remediation

This is a fallback PR created because the Devin-managed PR creation failed.
This PR contains a report of security issues identified by SonarCloud.

Generated at {datetime.now().isoformat()}""",
                "head": branch_name,
                "base": "master"
            }
            
            async with session.post(pr_url, headers=headers, json=pr_data) as response:
                if response.status == 201:
                    result = await response.json()
                    log(f"Successfully created fallback PR #{result['number']}: {result['html_url']}")
                    return True
                else:
                    log(f"Failed to create fallback PR: {await response.text()}", "ERROR")
                    return False
    except Exception as e:
        log(f"Unexpected error when creating fallback PR: {str(e)}", "ERROR")
        return False

async def main():
    start_time = time.time()
    log("Starting Devin remediation process...")
    
    try:
        # Validate required environment variables
        required_vars = ["GITHUB_REPOSITORY", "SONAR_TOKEN", "DEVIN_API_KEY", "SONAR_ORG", "SONAR_PROJECT_KEY"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            log(f"Error: Missing required environment variables: {', '.join(missing_vars)}", "ERROR")
            sys.exit(1)
        
        # Get SonarCloud issues
        issues = await get_sonarcloud_issues()
        
        if not issues:
            log("No issues found. Exiting.")
            return
        
        # Delegate all tasks to Devin in a single session
        session_data = await delegate_tasks_to_devin(issues)
        
        if session_data:
            session_id = session_data.get("session_id")
            if session_id:
                log(f"Monitoring session: {session_id}")
                
                # Monitor Devin's progress
                result = await monitor_devin_session(session_id)
                
                if result and result.get("status") == "completed":
                    log("Devin successfully completed the batch remediation task")
                else:
                    log("Devin session did not complete successfully. Creating fallback PR...", "WARNING")
                    await create_fallback_pr(issues)
            else:
                log("No session ID returned from Devin API", "ERROR")
                await create_fallback_pr(issues)
        else:
            log("Failed to create Devin session", "ERROR")
            await create_fallback_pr(issues)
                
    except Exception as e:
        log(f"Error occurred: {str(e)}", "ERROR")
        # Create fallback PR on exception
        try:
            issues = await get_sonarcloud_issues()
            await create_fallback_pr(issues)
        except Exception as fallback_error:
            log(f"Failed to create fallback PR after exception: {str(fallback_error)}", "ERROR")
        raise
    finally:
        end_time = time.time()
        duration = end_time - start_time
        log(f"Devin remediation process completed in {duration:.2f} seconds")

if __name__ == "__main__":
    asyncio.run(main())
