import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
import aiohttp
from fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP
mcp = FastMCP("helpdesk-tool")

# Configuration
HELPDESK_BASE_URL = "http://localhost:8081"
CURRENT_TOKEN = None
CURRENT_USER = None

class HelpdeskAPI:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.token = None
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def set_token(self, token: str):
        self.token = token
    
    def get_headers(self):
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    async def make_request(self, method: str, endpoint: str, data: Optional[Dict] = None):
        url = f"{self.base_url}{endpoint}"
        headers = self.get_headers()
        
        try:
            async with self.session.request(method, url, headers=headers, json=data) as response:
                response_data = await response.json()
                if response.status >= 400:
                    raise Exception(f"API Error {response.status}: {response_data.get('detail', 'Unknown error')}")
                return response_data
        except aiohttp.ClientError as e:
            raise Exception(f"Connection error: {str(e)}")

# Initialize API client
api = HelpdeskAPI(HELPDESK_BASE_URL)

@mcp.tool()
async def helpdesk_register(username: str, email: str, password: str, role: str = "user") -> Dict[str, Any]:
    """
    Register a new user in the helpdesk system
    
    Args:
        username: Unique username
        email: User's email address
        password: User's password
        role: User role (user, agent, admin) - default: user
    
    Returns:
        Dict containing user information
    """
    async with HelpdeskAPI(HELPDESK_BASE_URL) as client:
        try:
            user_data = {
                "username": username,
                "email": email,
                "password": password,
                "role": role
            }
            
            result = await client.make_request("POST", "/register", user_data)
            return {
                "success": True,
                "message": "User registered successfully",
                "user": result
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

@mcp.tool()
async def helpdesk_login(username: str, password: str) -> Dict[str, Any]:
    """
    Login to the helpdesk system and get access token
    
    Args:
        username: Username
        password: Password
    
    Returns:
        Dict containing login status and token
    """
    global CURRENT_TOKEN, CURRENT_USER
    
    async with HelpdeskAPI(HELPDESK_BASE_URL) as client:
        try:
            login_data = {
                "username": username,
                "password": password
            }
            
            result = await client.make_request("POST", "/login", login_data)
            
            # Store token for future requests
            CURRENT_TOKEN = result["access_token"]
            CURRENT_USER = username
            
            return {
                "success": True,
                "message": "Login successful",
                "token": result["access_token"],
                "user": username
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

@mcp.tool()
async def helpdesk_create_ticket(title: str, description: str, priority: str = "medium") -> Dict[str, Any]:
    """
    Create a new support ticket
    
    Args:
        title: Ticket title
        description: Detailed description of the issue
        priority: Priority level (low, medium, high, urgent) - default: medium
    
    Returns:
        Dict containing ticket information
    """
    if not CURRENT_TOKEN:
        return {
            "success": False,
            "error": "Not logged in. Please login first using helpdesk_login."
        }
    
    async with HelpdeskAPI(HELPDESK_BASE_URL) as client:
        try:
            client.set_token(CURRENT_TOKEN)
            
            ticket_data = {
                "title": title,
                "description": description,
                "priority": priority
            }
            
            result = await client.make_request("POST", "/tickets", ticket_data)
            return {
                "success": True,
                "message": "Ticket created successfully",
                "ticket": result
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

@mcp.tool()
async def helpdesk_get_tickets() -> Dict[str, Any]:
    """
    Get all tickets accessible to the current user
    
    Returns:
        Dict containing list of tickets
    """
    if not CURRENT_TOKEN:
        return {
            "success": False,
            "error": "Not logged in. Please login first using helpdesk_login."
        }
    
    async with HelpdeskAPI(HELPDESK_BASE_URL) as client:
        try:
            client.set_token(CURRENT_TOKEN)
            
            result = await client.make_request("GET", "/tickets")
            return {
                "success": True,
                "tickets": result,
                "count": len(result)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

@mcp.tool()
async def helpdesk_get_ticket(ticket_id: str) -> Dict[str, Any]:
    """
    Get details of a specific ticket
    
    Args:
        ticket_id: ID of the ticket to retrieve
    
    Returns:
        Dict containing ticket details
    """
    if not CURRENT_TOKEN:
        return {
            "success": False,
            "error": "Not logged in. Please login first using helpdesk_login."
        }
    
    async with HelpdeskAPI(HELPDESK_BASE_URL) as client:
        try:
            client.set_token(CURRENT_TOKEN)
            
            result = await client.make_request("GET", f"/tickets/{ticket_id}")
            return {
                "success": True,
                "ticket": result
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

@mcp.tool()
async def helpdesk_update_ticket(ticket_id: str, title: str = None, description: str = None, 
                                status: str = None, priority: str = None, assigned_to: str = None) -> Dict[str, Any]:
    """
    Update an existing ticket
    
    Args:
        ticket_id: ID of the ticket to update
        title: New title (optional)
        description: New description (optional)
        status: New status (open, in_progress, resolved, closed) (optional)
        priority: New priority (low, medium, high, urgent) (optional)
        assigned_to: Assign to user (optional)
    
    Returns:
        Dict containing updated ticket information
    """
    if not CURRENT_TOKEN:
        return {
            "success": False,
            "error": "Not logged in. Please login first using helpdesk_login."
        }
    
    async with HelpdeskAPI(HELPDESK_BASE_URL) as client:
        try:
            client.set_token(CURRENT_TOKEN)
            
            update_data = {}
            if title is not None:
                update_data["title"] = title
            if description is not None:
                update_data["description"] = description
            if status is not None:
                update_data["status"] = status
            if priority is not None:
                update_data["priority"] = priority
            if assigned_to is not None:
                update_data["assigned_to"] = assigned_to
            
            if not update_data:
                return {
                    "success": False,
                    "error": "No update data provided"
                }
            
            result = await client.make_request("PUT", f"/tickets/{ticket_id}", update_data)
            return {
                "success": True,
                "message": "Ticket updated successfully",
                "ticket": result
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

@mcp.tool()
async def helpdesk_get_stats() -> Dict[str, Any]:
    """
    Get helpdesk statistics (requires agent or admin role)
    
    Returns:
        Dict containing system statistics
    """
    if not CURRENT_TOKEN:
        return {
            "success": False,
            "error": "Not logged in. Please login first using helpdesk_login."
        }
    
    async with HelpdeskAPI(HELPDESK_BASE_URL) as client:
        try:
            client.set_token(CURRENT_TOKEN)
            
            result = await client.make_request("GET", "/stats")
            return {
                "success": True,
                "stats": result
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

@mcp.tool()
async def helpdesk_get_current_user() -> Dict[str, Any]:
    """
    Get current logged-in user information
    
    Returns:
        Dict containing user information
    """
    if not CURRENT_TOKEN:
        return {
            "success": False,
            "error": "Not logged in. Please login first using helpdesk_login."
        }
    
    async with HelpdeskAPI(HELPDESK_BASE_URL) as client:
        try:
            client.set_token(CURRENT_TOKEN)
            
            result = await client.make_request("GET", "/users/me")
            return {
                "success": True,
                "user": result
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

@mcp.tool()
async def helpdesk_logout() -> Dict[str, Any]:
    """
    Logout from the helpdesk system
    
    Returns:
        Dict containing logout status
    """
    global CURRENT_TOKEN, CURRENT_USER
    
    CURRENT_TOKEN = None
    CURRENT_USER = None
    
    return {
        "success": True,
        "message": "Logged out successfully"
    }

@mcp.tool()
async def helpdesk_status() -> Dict[str, Any]:
    """
    Check connection status and current user
    
    Returns:
        Dict containing connection and user status
    """
    try:
        async with HelpdeskAPI(HELPDESK_BASE_URL) as client:
            # Test connection
            await client.make_request("GET", "/")
            
            return {
                "success": True,
                "connection": "Connected",
                "base_url": HELPDESK_BASE_URL,
                "logged_in": CURRENT_TOKEN is not None,
                "current_user": CURRENT_USER
            }
    except Exception as e:
        return {
            "success": False,
            "connection": "Failed",
            "error": str(e)
        }

if __name__ == "__main__":
    import sys
    
    # Run the MCP server
    print("Starting IT Helpdesk MCP Tool...", file=sys.stderr)
    mcp.run()
    # mcp.run(
    #     #transport="std",
    #     host="127.0.0.1",
    #     port=8081,
    #     path="/",
    #     log_level="debug",
    # )