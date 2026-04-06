from datetime import datetime

def get_current_date_vn():
    now = datetime.now()
    days_vn = {
        'Monday': 'Thứ 2', 'Tuesday': 'Thứ 3', 'Wednesday': 'Thứ 4',
        'Thursday': 'Thứ 5', 'Friday': 'Thứ 6', 'Saturday': 'Thứ 7', 'Sunday': 'Chủ nhật'
    }
    en_day = now.strftime('%A')
    return f"{days_vn.get(en_day, en_day)}, ngày {now.strftime('%d/%m/%Y')}"