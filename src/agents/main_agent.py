from src.graph.workflow import create_hybrid_workflow

def create_schedule_advisor():
    """
    Tạo Schedule Advisor.
    Toàn bộ logic Workflow đã được tách sang module DeepAgents.graph
    """
    return create_hybrid_workflow()

