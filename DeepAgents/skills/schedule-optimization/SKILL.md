---
name: schedule-optimization
description: >
  Kỹ năng tối ưu hóa lịch trình cá nhân; hướng dẫn chuẩn hóa thời gian,
  phát hiện xung đột, và đề xuất lịch ngắn gọn.
metadata:
  author: DeepAgents Team
  version: "1.0"
  language: vi
---

# Schedule Optimization Skill

## Tổng quan

Skill này cung cấp hướng dẫn chi tiết để agent tối ưu hóa lịch trình cá nhân
dựa trên preferences của người dùng (từ `/memories/user_preferences.txt`)
và lịch hiện có (từ Google Calendar).

## Hướng dẫn

### 1. Phát hiện xung đột thời gian

- Kiểm tra sự kiện mới có overlap với lịch hiện có không (dùng calendar-agent)
- Kiểm tra sự kiện mới có vi phạm giới hạn thời gian trong preferences không
- Kiểm tra buffer time: có đủ khoảng trống giữa các sự kiện liên tiếp không

### 2. Nguyên tắc Time-Blocking

- **Deep Work blocks**: Xếp công việc cần tập trung cao vào khung giờ "study_peak" trong preferences
- **Shallow Work**: Email, họp ngắn → xếp vào khung giờ rảnh ngoài peak
- **Nghỉ ngơi**: Tuân theo giới hạn "study_session_max" trong preferences
- **Buffer**: Giữ khoảng trống giữa các sự kiện liên tiếp

### 3. Thứ tự ưu tiên (Eisenhower Matrix)

1. **Khẩn cấp + Quan trọng**: Thi cử, deadline → ưu tiên tuyệt đối
2. **Quan trọng + Không khẩn cấp**: Học bài, đồ án → lên lịch cố định
3. **Khẩn cấp + Không quan trọng**: Họp nhóm → ủy quyền hoặc rút ngắn
4. **Không khẩn cấp + Không quan trọng**: Giải trí → xếp cuối ngày

### 4. Xử lý xung đột lịch

Khi phát hiện xung đột, PHẢI đưa ra ít nhất 2 phương án KHÁC BIỆT:

**Cách 1 — Dời sự kiện mới:**

- Tìm slot trống phù hợp dựa trên lịch hiện có + thời gian rảnh trong preferences
- Ưu tiên khung giờ gần nhất với thời gian người dùng yêu cầu
- Giải thích lý do chọn khung giờ đó

**Cách 2 — Thay đổi sự kiện gây xung đột:**

- Đề xuất rút ngắn, dời, hoặc hủy sự kiện đang gây xung đột
- Hỏi người dùng muốn ưu tiên sự kiện nào hơn
- Hoặc ghép 2 sự kiện nếu có thể

⚠️ KHÔNG đề xuất 2 khung giờ khác nhau cho cùng một cách tiếp cận.
Mỗi phương án phải là một HƯỚNG GIẢI QUYẾT KHÁC NHAU.

### 5. Quy tắc quan trọng

- Luôn tham khảo preferences từ `/memories/user_preferences.txt` trước khi đề xuất
- Tôn trọng giới hạn "avoid" trong preferences (ví dụ: không xếp lịch ngoài giờ cho phép)
- Giữ nguyên giờ ăn và tập thể dục theo thói quen trong preferences
- Ưu tiên sự kiện có lịch cố định (học trên lớp, thi cử) không thể thay đổi

### 6. Định dạng đề xuất

Khi đề xuất lịch trình, trình bày theo format:

```
📅 [Ngày]
  ⏰ [Giờ bắt đầu] - [Giờ kết thúc] | [Tên sự kiện] | 📍 [Địa điểm]
  💡 Lý do: [Giải thích ngắn gọn tại sao chọn khung giờ này]
```
