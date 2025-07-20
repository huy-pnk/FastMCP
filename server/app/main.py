import asyncio
import aiohttp
import json
import os
import time
import sys
from typing import Dict, Any, Optional
from fastmcp import FastMCP

mcp = FastMCP("helpdesk-file-jwt")

# Configuration
HELPDESK_API_URL = "http://localhost:8081"
KEYCLOAK_BASE_URL = "http://localhost:9000"
KEYCLOAK_REALM = "oauth-demo"
JWT_FILE_PATH = r"C:\Project\GitHub\Ubuntu\MCP\oauth\saved_jwt.json"

def read_jwt_file() -> Optional[Dict[str, Any]]:
    """
    Read JWT data from saved file
    
    Returns:
        Dict with JWT data or None if file doesn't exist/invalid
    """
    try:
        if not os.path.exists(JWT_FILE_PATH):
            return None
            
        with open(JWT_FILE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Validate required fields
        required_fields = ['access_token', 'expires_at']
        if not all(field in data for field in required_fields):
            return None
            
        return data
        
    except (json.JSONDecodeError, FileNotFoundError, PermissionError) as e:
        print(f"Error reading JWT file: {e}", file=sys.stderr)
        return None

def is_token_valid(jwt_data: Dict[str, Any]) -> tuple[bool, str]:
    """
    Check if JWT token is still valid
    
    Args:
        jwt_data: JWT data from file
        
    Returns:
        Tuple of (is_valid, reason)
    """
    if not jwt_data:
        return False, "No JWT data provided"
    
    access_token = jwt_data.get('access_token')
    if not access_token:
        return False, "No access token found"
    
    expires_at = jwt_data.get('expires_at')
    if not expires_at:
        return False, "No expiry information found"
    
    current_time = int(time.time())
    if current_time >= expires_at:
        expires_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(expires_at))
        return False, f"Token expired at {expires_str}"
    
    return True, "Token is valid"

def get_valid_token() -> tuple[Optional[str], str]:
    """
    Get valid JWT token from file
    
    Returns:
        Tuple of (token, status_message)
    """
    jwt_data = read_jwt_file()
    
    if not jwt_data:
        return None, f"❌ JWT file not found or invalid.\n📂 Expected location: {JWT_FILE_PATH}\n💡 Please open oauth_test_page.html and complete login."
    
    is_valid, reason = is_token_valid(jwt_data)
    
    if not is_valid:
        return None, f"❌ JWT token invalid: {reason}\n💡 Please login again using oauth_test_page.html"
    
    user_info = jwt_data.get('user_info', {})
    username = user_info.get('preferred_username', 'Unknown')
    
    return jwt_data['access_token'], f"✅ Valid JWT found for user: {username}"

@mcp.tool()
async def helpdesk_check_auth_status() -> Dict[str, Any]:
    """
    Check authentication status by reading JWT file
    
    Returns:
        Dict with detailed authentication status
    """
    jwt_data = read_jwt_file()
    
    if not jwt_data:
        return {
            "success": False,
            "authenticated": False,
            "error": "JWT file not found",
            "file_path": JWT_FILE_PATH,
            "instructions": [
                "1. Open oauth_test_page.html in your browser",
                "2. Complete OAuth2 login with Keycloak", 
                "3. Save JWT to file",
                "4. Try again"
            ]
        }
    
    is_valid, reason = is_token_valid(jwt_data)
    user_info = jwt_data.get('user_info', {})
    
    status = {
        "success": True,
        "authenticated": is_valid,
        "file_exists": True,
        "file_path": JWT_FILE_PATH,
        "token_valid": is_valid,
        "validation_reason": reason,
        "user_info": {
            "username": user_info.get('preferred_username'),
            "email": user_info.get('email'),
            "name": user_info.get('name')
        },
        "token_info": {
            "expires_at": jwt_data.get('expires_at'),
            "expires_at_readable": time.strftime('%Y-%m-%d %H:%M:%S', 
                                                time.localtime(jwt_data.get('expires_at', 0))),
            "issued_at": jwt_data.get('issued_at'),
            "time_until_expiry": max(0, jwt_data.get('expires_at', 0) - int(time.time())),
        },
        "keycloak_config": jwt_data.get('keycloak_config', {})
    }
    
    if not is_valid:
        status["instructions"] = [
            "Token is invalid or expired",
            "Please login again:",
            "1. Open oauth_test_page.html", 
            "2. Complete OAuth2 flow",
            "3. Save new JWT to file"
        ]
    
    return status

@mcp.tool()
async def helpdesk_create_ticket(title: str, description: str, priority: str = "medium") -> Dict[str, Any]:
    """
    Create a new support ticket
    
    Args:
        title: Ticket title
        description: Detailed description of the issue
        priority: Priority level (low, medium, high, urgent)
    
    Returns:
        Dict containing ticket information
    """
    # Check authentication
    token, auth_message = get_valid_token()
    
    if not token:
        return {
            "success": False,
            "error": "Authentication required",
            "message": auth_message,
            "suggestion": "Use helpdesk_check_auth_status() for more details"
        }
    
    # Create ticket
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            ticket_data = {
                "title": title,
                "description": description,
                "priority": priority
            }
            
            async with session.post(f"{HELPDESK_API_URL}/tickets", 
                                  headers=headers, 
                                  json=ticket_data) as response:
                
                if response.status in [200, 201]:
                    result = await response.json()
                    return {
                        "success": True,
                        "message": "🎫 Ticket created successfully!",
                        "ticket": result,
                        "auth_status": auth_message
                    }
                elif response.status == 401:
                    return {
                        "success": False,
                        "error": "Authentication failed",
                        "message": "JWT token was rejected by the API. Please login again.",
                        "suggestion": "Open oauth_test_page.html and complete login"
                    }
                else:
                    error_data = await response.text()
                    return {
                        "success": False,
                        "error": f"API error: HTTP {response.status}",
                        "details": error_data
                    }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Connection error: {str(e)}",
            "suggestion": "Check if FastAPI helpdesk server is running on port 8081"
        }

@mcp.tool()
async def helpdesk_get_tickets() -> Dict[str, Any]:
    """
    Get all tickets accessible to current user
    
    Returns:
        Dict containing list of tickets
    """
    # Check authentication
    token, auth_message = get_valid_token()
    
    if not token:
        return {
            "success": False,
            "error": "Authentication required",
            "message": auth_message,
            "suggestion": "Use helpdesk_check_auth_status() for more details"
        }
    
    # Get tickets
    try:
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {token}"}
            
            async with session.get(f"{HELPDESK_API_URL}/tickets", headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        "success": True,
                        "message": f"📋 Found {len(result) if isinstance(result, list) else 0} tickets",
                        "tickets": result,
                        "count": len(result) if isinstance(result, list) else 0,
                        "auth_status": auth_message
                    }
                elif response.status == 401:
                    return {
                        "success": False,
                        "error": "Authentication failed",
                        "message": "JWT token was rejected by the API. Please login again.",
                        "suggestion": "Open oauth_test_page.html and complete login"
                    }
                else:
                    error_data = await response.text()
                    return {
                        "success": False,
                        "error": f"API error: HTTP {response.status}",
                        "details": error_data
                    }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Connection error: {str(e)}",
            "suggestion": "Check if FastAPI helpdesk server is running on port 8081"
        }

@mcp.tool()
async def helpdesk_get_user_info() -> Dict[str, Any]:
    """
    Get current user information
    
    Returns:
        Dict with user information
    """
    # Check authentication
    token, auth_message = get_valid_token()
    
    if not token:
        return {
            "success": False,
            "error": "Authentication required",
            "message": auth_message
        }
    
    jwt_data = read_jwt_file()
    
    try:
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {token}"}
            
            # Get user info from API
            api_user_info = {}
            async with session.get(f"{HELPDESK_API_URL}/users/me", headers=headers) as response:
                if response.status == 200:
                    api_user_info = await response.json()
            
            # Get user info from Keycloak
            keycloak_user_info = {}
            userinfo_url = f"{KEYCLOAK_BASE_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/userinfo"
            async with session.get(userinfo_url, headers=headers) as response:
                if response.status == 200:
                    keycloak_user_info = await response.json()
            
            return {
                "success": True,
                "jwt_file_info": jwt_data.get('user_info', {}),
                "api_user_info": api_user_info,
                "keycloak_user_info": keycloak_user_info,
                "auth_status": auth_message
            }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Connection error: {str(e)}"
        }

@mcp.tool()
async def helpdesk_refresh_instructions() -> Dict[str, Any]:
    """
    Get instructions for refreshing authentication
    
    Returns:
        Dict with step-by-step instructions
    """
    return {
        "success": True,
        "title": "🔄 How to Refresh Authentication",
        "instructions": [
            "1. 🌐 Open your browser",
            f"2. 📁 Navigate to: C:\\Project\\GitHub\\Ubuntu\\MCP\\oauth\\oauth_test_page.html",
            "3. 🔐 Click 'Login with Keycloak'",
            "4. 👤 Enter your credentials (testuser/password123)",
            "5. 🔄 Click 'Exchange Code for Token'",
            "6. 💾 Click 'Save JWT to File'",
            "7. 📂 Move downloaded file to:",
            f"   {JWT_FILE_PATH}",
            "8. ✅ Use helpdesk_check_auth_status() to verify"
        ],
        "file_locations": {
            "oauth_page": "C:\\Project\\GitHub\\Ubuntu\\MCP\\oauth\\oauth_test_page.html",
            "jwt_file": JWT_FILE_PATH
        },
        "test_credentials": {
            "username": "testuser",
            "password": "password123"
        },
        "troubleshooting": [
            "• If Keycloak is not running: docker run -p 9000:8080 keycloak...",
            "• If FastAPI is not running: python main.py",
            "• If file permissions: Run as administrator",
            "• If browser issues: Try incognito/private mode"
        ]
    }

if __name__ == "__main__":
    print(f"🚀 Starting Helpdesk MCP Server with stdio transport...", file=sys.stderr)
    print(f"📁 JWT File Path: {JWT_FILE_PATH}", file=sys.stderr)
    print(f"🌐 FastAPI URL: {HELPDESK_API_URL}", file=sys.stderr)
    print(f"🔐 Keycloak URL: {KEYCLOAK_BASE_URL}", file=sys.stderr)
    
    # Use stdio transport instead of HTTP
    mcp.run()  # This defaults to stdio transport