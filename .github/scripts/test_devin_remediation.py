#!/usr/bin/env python3
import asyncio
import os
import sys
from unittest.mock import patch, MagicMock, AsyncMock

# Set environment variables before importing the module
os.environ["GITHUB_REPOSITORY"] = "JonMarkGo-AI-Testing/juice-shop"
os.environ["SONAR_TOKEN"] = "mock_token"
os.environ["DEVIN_API_KEY"] = "mock_key"
os.environ["SONAR_ORG"] = "mock_org"
os.environ["SONAR_PROJECT_KEY"] = "mock_project"
os.environ["GITHUB_TOKEN"] = "mock_github_token"

# Add the current directory to the path so we can import the module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from devin_remediation import get_sonarcloud_issues, delegate_task_to_devin, monitor_devin_session, create_pr_directly, create_fallback_pr

# Mock response for SonarCloud issues
MOCK_SONAR_ISSUES = {
    "issues": [
        {
            "key": "issue1",
            "message": "Fix NoSQL injection vulnerability",
            "component": "JonMarkGo-AI-Testing/juice-shop:routes/likeProductReviews.ts"
        }
    ]
}

# Mock response for Devin session creation
MOCK_DEVIN_SESSION = {
    "session_id": "mock_session_id",
    "status": "running"
}

# Mock response for Devin session monitoring
MOCK_DEVIN_COMPLETED = {
    "session_id": "mock_session_id",
    "status": "completed"
}

# Mock response for GitHub PR creation
MOCK_PR_RESPONSE = {
    "number": 123,
    "html_url": "https://github.com/JonMarkGo-AI-Testing/juice-shop/pull/123"
}

# Create async mock for response.text
async def mock_text():
    return "Mock response text"

async def test_get_sonarcloud_issues():
    """Test fetching SonarCloud issues."""
    print("\n=== Testing get_sonarcloud_issues ===")
    
    # Create a proper AsyncMock for the response
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = MOCK_SONAR_ISSUES
    mock_response.text = mock_text
    
    with patch('aiohttp.ClientSession.get', return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=mock_response)
    )):
        issues = await get_sonarcloud_issues()
        
        assert len(issues) == 1, f"Expected 1 issue, got {len(issues)}"
        assert issues[0]["key"] == "issue1", f"Expected issue key 'issue1', got {issues[0]['key']}"
        
        print("✅ get_sonarcloud_issues test passed")
        return issues[0]

async def test_delegate_task_to_devin(issue):
    """Test delegating task to Devin."""
    print("\n=== Testing delegate_task_to_devin ===")
    
    # Create a proper AsyncMock for the response
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = MOCK_DEVIN_SESSION
    mock_response.text = mock_text
    
    with patch('aiohttp.ClientSession.post', return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=mock_response)
    )):
        session_data = await delegate_task_to_devin(issue)
        
        assert session_data is not None, "Expected session data, got None"
        assert session_data["session_id"] == "mock_session_id", f"Expected session_id 'mock_session_id', got {session_data.get('session_id')}"
        
        print("✅ delegate_task_to_devin test passed")
        return session_data

async def test_monitor_devin_session(session_id):
    """Test monitoring Devin session."""
    print("\n=== Testing monitor_devin_session ===")
    
    # Create a proper AsyncMock for the response
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = MOCK_DEVIN_COMPLETED
    mock_response.text = mock_text
    
    with patch('aiohttp.ClientSession.get', return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=mock_response)
    )):
        # Mock asyncio.sleep to avoid waiting
        with patch('asyncio.sleep', return_value=None):
            result = await monitor_devin_session(session_id)
            
            assert result is not None, "Expected result, got None"
            assert result["status"] == "completed", f"Expected status 'completed', got {result.get('status')}"
            
            print("✅ monitor_devin_session test passed")
            return result

async def test_create_pr_directly(issue):
    """Test creating PR directly."""
    print("\n=== Testing create_pr_directly ===")
    
    # Create a proper AsyncMock for the response
    mock_response = AsyncMock()
    mock_response.status = 201
    mock_response.json.return_value = MOCK_PR_RESPONSE
    mock_response.text = mock_text
    
    with patch('aiohttp.ClientSession.post', return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=mock_response)
    )):
        branch_name = f"devin/fix-test-{issue['key']}"
        success = await create_pr_directly(issue, branch_name)
        
        assert success is True, "Expected success True, got False"
        
        print("✅ create_pr_directly test passed")

async def test_create_fallback_pr(issues):
    """Test creating fallback PR."""
    print("\n=== Testing create_fallback_pr ===")
    
    # Create proper AsyncMocks for the responses
    mock_get_response = AsyncMock()
    mock_get_response.status = 200
    mock_get_response.json.return_value = {"object": {"sha": "mock_sha"}}
    mock_get_response.text = mock_text
    
    mock_post_response = AsyncMock()
    mock_post_response.status = 201
    mock_post_response.json.return_value = MOCK_PR_RESPONSE
    mock_post_response.text = mock_text
    
    mock_put_response = AsyncMock()
    mock_put_response.status = 201
    mock_put_response.text = mock_text
    
    # Patch all HTTP methods
    with patch('aiohttp.ClientSession.get', return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=mock_get_response)
        )), \
        patch('aiohttp.ClientSession.post', return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=mock_post_response)
        )), \
        patch('aiohttp.ClientSession.put', return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=mock_put_response)
        )):
        
        success = await create_fallback_pr(issues)
        
        assert success is True, "Expected success True, got False"
        
        print("✅ create_fallback_pr test passed")

async def test_error_handling():
    """Test error handling in the script."""
    print("\n=== Testing error handling ===")
    
    # Test SonarCloud error handling
    print("Testing SonarCloud error handling...")
    mock_error_response = AsyncMock()
    mock_error_response.status = 401
    mock_error_response.text = mock_text
    
    with patch('aiohttp.ClientSession.get', return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=mock_error_response)
    )):
        issues = await get_sonarcloud_issues()
        
        assert issues == [], "Expected empty list on error, got non-empty list"
    
    # Test Devin API error handling
    print("Testing Devin API error handling...")
    mock_error_response = AsyncMock()
    mock_error_response.status = 401
    mock_error_response.text = mock_text
    
    with patch('aiohttp.ClientSession.post', return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=mock_error_response)
    )):
        issue = {"key": "issue1", "message": "Test", "component": "test.ts"}
        session_data = await delegate_task_to_devin(issue)
        
        assert session_data is None, "Expected None on error, got session data"
    
    print("✅ Error handling tests passed")

async def main():
    """Run all tests."""
    try:
        print("Starting tests for devin_remediation.py...")
        
        # Run tests in sequence
        issue = await test_get_sonarcloud_issues()
        session_data = await test_delegate_task_to_devin(issue)
        await test_monitor_devin_session(session_data["session_id"])
        await test_create_pr_directly(issue)
        await test_create_fallback_pr([issue])
        await test_error_handling()
        
        print("\n✅ All tests passed!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {str(e)}")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
