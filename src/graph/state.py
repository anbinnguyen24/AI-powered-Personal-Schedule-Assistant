from typing import Annotated, Literal, NotRequired, Sequence, TypedDict
import operator
from langchain_core.messages import BaseMessage
class ParsedTask(TypedDict):
	# Tên công việc đã tách ra từ yêu cầu của người dùng.
	title: str
	# Thời lượng ước tính của công việc, tính bằng phút.
	duration_min: int
	# Hạn chót của công việc, nếu người dùng có cung cấp.
	deadline: NotRequired[str]
	# Mức độ ưu tiên của công việc, dùng để sắp lịch trước/sau.
	priority: NotRequired[int]


class CalendarEvent(TypedDict):
	# Mã định danh của event trên calendar.
	id: str
	# Tiêu đề của event.
	title: str
	# Thời điểm bắt đầu của event.
	start: str
	# Thời điểm kết thúc của event.
	end: str


class ScheduleCandidate(TypedDict):
	# Tên task mà phương án này đang sắp lịch cho.
	task_title: str
	# Giờ bắt đầu được AI đề xuất.
	proposed_start: str
	# Giờ kết thúc được AI đề xuất.
	proposed_end: str
	# Lý do AI chọn khung giờ này.
	reason: NotRequired[str]
	# Điểm đánh giá để so sánh giữa các phương án.
	score: NotRequired[float]


class ConflictItem(TypedDict):
	# Task đang bị trùng lịch.
	task_title: str
	# Event calendar gây xung đột với task.
	conflict_with_event_id: str
	# Số phút bị chồng lấn giữa hai event.
	overlap_minutes: int


class AgentState(TypedDict):
	# Toàn bộ lịch sử hội thoại giữa người dùng và agent.
	messages: Annotated[Sequence[BaseMessage], operator.add]
	# Tên node hoặc agent tiếp theo trong workflow.
	next: str
	# Mã người dùng để gắn với lịch cá nhân.
	user_id: NotRequired[str]

	# 1) Input: dữ liệu đầu vào lấy từ người dùng hoặc hệ thống.
	# Nội dung yêu cầu gốc của người dùng.
	user_request: NotRequired[str]
	# Múi giờ người dùng đang dùng để tính thời gian chính xác.
	user_timezone: NotRequired[str]
	# Thời điểm hiện tại tại lúc xử lý yêu cầu.
	now: NotRequired[str]

	# 2) Analyze: kết quả sau khi AI đọc và bóc tách yêu cầu.
	# Ý định chính của người dùng, ví dụ tạo lịch, dời lịch, tối ưu ngày làm việc.
	intent: NotRequired[str]
	# Danh sách task đã được trích xuất từ câu người dùng.
	extracted_tasks: NotRequired[list[ParsedTask]]

	# 3) Calendar data: dữ liệu lịch hiện có để kiểm tra trùng và xếp slot.
	# Danh sách event đang tồn tại trên calendar trong khoảng cần xét.
	existing_events: NotRequired[list[CalendarEvent]]

	# 4) Suggest schedule: các phương án AI đề xuất.
	# Danh sách slot mà AI nghĩ là phù hợp để xếp task.
	schedule_candidates: NotRequired[list[ScheduleCandidate]]

	# 5) Conflict check: kết quả kiểm tra trùng lịch.
	# Các xung đột được phát hiện giữa task và event khác.
	conflicts: NotRequired[list[ConflictItem]]
	# Cờ cho biết lịch đề xuất có sạch xung đột hay không.
	is_conflict_free: NotRequired[bool]

	# 6) Final output: dữ liệu cuối cùng để trả cho người dùng.
	# Phương án đã được chọn làm kết quả khuyến nghị cuối.
	final_recommendation: NotRequired[list[ScheduleCandidate]]
	# Nội dung trả lời đã được soạn sẵn cho UI hoặc chat.
	response_text: NotRequired[str]

	# 7) Runtime status: trạng thái đang chạy của workflow.
	# Bước hiện tại của pipeline xử lý.
	step: NotRequired[Literal["parsed", "suggested", "validated", "done", "error"]]
	# Danh sách lỗi phát sinh trong quá trình parse, suggest, hoặc validate.
	errors: NotRequired[list[str]]


