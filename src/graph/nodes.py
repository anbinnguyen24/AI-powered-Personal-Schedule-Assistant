
import re
from datetime import datetime, timedelta, timezone
from typing import Any
from agents import calendar_agent, research_agent, scheduling_agent
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from src.graph.state import AgentState


# ============================================================================
# NODE 1: SUPERVISOR NODE
# ============================================================================
def call_supervisor_node(state: AgentState) -> AgentState:
    """ 
    Nút giám sát chính: Phân tích yêu cầu và xác định nên gửi tới agent nào.
    
    Input:
        - state["messages"]: Lịch sử hội thoại
        
    Output:
        - state["next_worker"]: Xác định agent tiếp theo (calendar_agent, research_agent, execute_booking, hoặc None)
        - state["messages"]: Thêm response từ supervisor
    """
    # TODO: Implement supervisor logic
    # 1. Get latest user message
    # 2. Analyze the request to determine which agent should handle it
    # 3. Set state["next_worker"] = "calendar_agent" | "research_agent" | "execute_booking" | None
    # 4. Return updated state
    
    latest_message = state["messages"][-1]
    
    # Placeholder response
    supervisor_response = AIMessage(content="[Supervisor processing...]")
    
    return {
        "messages": state["messages"] + [supervisor_response],
        "next_worker": "calendar_agent"  # TODO: Replace with actual logic
    }


# ============================================================================
# NODE 2: CALENDAR EXPERT NODE
# ============================================================================
def call_calendar_node(state: AgentState) -> AgentState:
    """
    Nút chuyên gia lịch: Xử lý các công việc liên quan đến quản lý calendar.
    
    Input:
        - state["messages"]: Lịch sử hội thoại
        
    Output:
        - state["messages"]: Thêm response từ calendar agent
        - state["next_worker"]: Trả về "supervisor" để tiếp tục quy trình
    """
    # TODO: Implement calendar agent logic
    # 1. Parse the user request
    # 2. Check current calendar events
    # 3. Extract tasks/events to handle
    # 4. Call calendar_agent to process
    # 5. Return result to supervisor
    
    latest_message = state["messages"][-1]
    
    # Placeholder response
    calendar_response = AIMessage(content="[Calendar expert processing...]")
    
    return {
        "messages": state["messages"] + [calendar_response],
        "next_worker": "supervisor"
    }


# ============================================================================
# NODE 3: RESEARCHER NODE  
# ============================================================================
def call_research_node(state: AgentState) -> AgentState:
    """
    Nút nhà nghiên cứu: Tìm kiếm thông tin hoặc phân tích dữ liệu.
    
    Input:
        - state["messages"]: Lịch sử hội thoại
        
    Output:
        - state["messages"]: Thêm response từ research agent
        - state["next_worker"]: Trả về "supervisor" để tiếp tục quy trình
    """
    # TODO: Implement research agent logic
    # 1. Parse the research request
    # 2. Perform web search if needed
    # 3. Analyze retrieved information
    # 4. Call research_agent to process
    # 5. Return findings to supervisor
    
    latest_message = state["messages"][-1]
    
    # Placeholder response
    research_response = AIMessage(content="[Researcher processing...]")
    
    return {
        "messages": state["messages"] + [research_response],
        "next_worker": "supervisor"
    }


# ============================================================================
# NODE 4: BOOKING/EXECUTION NODE
# ============================================================================
def execute_booking_node(state: AgentState) -> AgentState:
    """
    Nút thực thi: Chốt lịch và thực hiện hành động cuối cùng.
    
    Input:
        - state["messages"]: Lịch sử hội thoại
        
    Output:
        - state["messages"]: Thêm response xác nhận booking
    """
    # TODO: Implement booking execution logic
    # 1. Get the confirmed schedule choice
    # 2. Check for conflicts one final time
    # 3. Create calendar event
    # 4. Save to database if needed
    # 5. Return confirmation message
    
    latest_message = state["messages"][-1]
    
    # Placeholder response
    booking_response = AIMessage(content="[Booking confirmed and executed...]")
    
    return {
        "messages": state["messages"] + [booking_response]
    }


