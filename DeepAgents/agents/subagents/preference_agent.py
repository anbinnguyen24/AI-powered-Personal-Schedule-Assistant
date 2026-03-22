from DeepAgents.prompts.preference_agent import PREFERENCE_AGENT_PROMPT

preference_subagent = {
    "name": "preference-agent",
    "description": (
        "Quản lý hồ sơ cá nhân, sở thích, thói quen và thời gian rảnh của người dùng. "
        "Dùng agent này khi cần đọc, tạo mới hoặc cập nhật preferences. "
        "Dữ liệu được lưu persistent xuyên suốt các cuộc hội thoại."
    ),
    "system_prompt": PREFERENCE_AGENT_PROMPT,
    "tools": [],  # Sử dụng built-in filesystem tools (read_file, write_file, edit_file)
}
