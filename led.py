import tkinter as tk
from tkinter import messagebox
from tkinter import font as tkFont
import serial
import serial.tools.list_ports
import time
from PIL import Image, ImageTk

# --- THIẾT LẬP CỔNG SERIAL ---
BAUD_RATE = 9600
ser = None
detected_port = None # Biến toàn cục lưu cổng tìm thấy

# --- QUẢN LÝ HẸN GIỜ ---
# Dictionary để lưu trạng thái hẹn giờ cho từng relay (1, 2, 3)
seat_timers = {
    1: {'end_time': None, 'timer_id': None},
    2: {'end_time': None, 'timer_id': None},
    3: {'end_time': None, 'timer_id': None}
}

# Hằng số thời gian (4 tiếng)
#SESSION_DURATION_SECONDS = 4 * 60 * 60
SESSION_DURATION_SECONDS = 10 # DEBUG: 10 giây để test

# ===================================================================
# CÁC HÀM XỬ LÝ SERIAL (Giữ nguyên logic, chỉ cập nhật nhãn)
# ===================================================================

def update_port_status():
    """Tìm Arduino và cập nhật nhãn trạng thái trên màn hình đăng nhập."""
    global detected_port
    global port_status_label 
    
    port = find_arduino_port()
    if port:
        detected_port = port
        if 'port_status_label' in globals():
            port_status_label.config(text=f"Đã tìm thấy: {port}", fg=COLOR_STATUS_SUCCESS)
    else:
        detected_port = None
        if 'port_status_label' in globals():
            port_status_label.config(text="Không tìm thấy Arduino. Kiểm tra cáp!", fg=COLOR_RED_ERROR)
    return port

def find_arduino_port():
    """Tìm cổng COM của Arduino/chip CH340 một cách tự động."""
    ports = list(serial.tools.list_ports.comports())
    for p in ports:
        desc_lower = p.description.lower()
        if 'arduino' in desc_lower or 'ch340' in desc_lower or 'usb serial' in desc_lower:
            return p.device
    return None

def connect_to_arduino():
    """Thiết lập kết nối Serial (SỬ DỤNG CỔNG ĐÃ TÌM THẤY)."""
    global ser
    global detected_port
    global main_status_label # Nhãn trên màn hình chính
    
    if not detected_port:
        update_port_status()

    if not detected_port:
        messagebox.showerror("Lỗi Kết Nối", "Không tìm thấy cổng Arduino. Vui lòng nhấn 'Quét lại cổng' và thử lại.")
        if 'main_status_label' in globals():
            main_status_label.config(text="LỖI: Không tìm thấy cổng", fg=COLOR_RED_ERROR)
        return False
        
    port_to_use = detected_port
    
    try:
        if ser and ser.isOpen():
            ser.close()
            
        ser = serial.Serial(port_to_use, BAUD_RATE, timeout=1)
        if 'main_status_label' in globals():
            main_status_label.config(text=f"Đã kết nối: {port_to_use}", fg=COLOR_STATUS_SUCCESS)
        
        time.sleep(2) 
        return True
    
    except serial.SerialException as e:
        messagebox.showerror("Lỗi Kết Nối", f"Không thể kết nối với cổng {port_to_use}: {e}")
        if 'main_status_label' in globals():
            main_status_label.config(text=f"LỖI: {port_to_use} không khả dụng", fg=COLOR_RED_ERROR)
        return False

def send_command(command):
    """Gửi lệnh ('ON1' đến 'OFF3' hoặc 'ON_FAN'/'OFF_FAN') qua Serial."""
    global ser
    global main_status_label
    if ser and ser.isOpen():
        try:
            ser.write(command.encode() + b'\n')
            
            # Cập nhật nhãn trạng thái (không cập nhật cho quạt vì đã làm ở hàm riêng)
            if command.startswith("ON") and "FAN" not in command:
                relay_id = command[-1]
                main_status_label.config(text=f"Đã gửi lệnh 'BẬT Vị trí {relay_id}'!", fg=COLOR_TEXT_LIGHT)
            elif command.startswith("OFF") and "FAN" not in command:
                relay_id = command[-1]
                main_status_label.config(text=f"Đã gửi lệnh 'TẮT Vị trí {relay_id}'!", fg=COLOR_TEXT_LIGHT)
                
        except Exception as e:
            messagebox.showerror("Lỗi Gửi Dữ Liệu", f"Lỗi khi gửi lệnh: {e}")
            main_status_label.config(text="LỖI: Mất kết nối. Vui lòng thử kết nối lại.", fg=COLOR_RED_ERROR)
            if ser:
                ser.close()
    else:
        # Không hiển thị messagebox nếu đó là lệnh quạt (đã xử lý ở hàm handle_fan_toggle)
        if "FAN" not in command:
             messagebox.showwarning("Chưa Kết Nối", "Vui lòng kiểm tra cáp và nhấn 'Kết Nối Lại'.")

# ===================================================================
# HÀM XỬ LÝ HẸN GIỜ (LOGIC MỚI)
# ===================================================================

def start_timer(relay_id):
    """Bắt đầu hẹn giờ 4 tiếng cho một vị trí (relay)."""
    
    # Kiểm tra xem có đang chạy timer không
    if seat_timers[relay_id]['end_time']:
        messagebox.showwarning("Đang sử dụng", f"Vị trí {relay_id} hiện đang được sử dụng.")
        return

    # Gửi lệnh BẬT
    send_command(f"ON{relay_id}")
    
    # Tính toán thời gian kết thúc
    start_time = time.time()
    end_time = start_time + SESSION_DURATION_SECONDS
    seat_timers[relay_id]['end_time'] = end_time
    
    # Cập nhật giao diện
    update_ui_for_seat(relay_id, 'active')
    
    # Bắt đầu vòng lặp cập nhật đếm ngược
    update_countdown(relay_id)

def update_countdown(relay_id):
    """Cập nhật đồng hồ đếm ngược mỗi giây."""
    
    end_time = seat_timers[relay_id].get('end_time')
    if not end_time:
        # Timer đã bị hủy
        return

    remaining = end_time - time.time()
    
    if remaining > 0:
        # Tính giờ, phút, giây
        hours = int(remaining // 3600)
        minutes = int((remaining % 3600) // 60)
        seconds = int(remaining % 60)
        
        # Cập nhật nhãn timer
        timer_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        ui_elements[relay_id]['timer_label'].config(text=timer_str)
        
        # Hẹn giờ để chạy lại sau 1 giây
        timer_id = root.after(1000, lambda: update_countdown(relay_id))
        seat_timers[relay_id]['timer_id'] = timer_id
    else:
        # Hết giờ
        stop_timer(relay_id, send_off_command=True)

def stop_timer(relay_id, send_off_command=True):
    """Dừng timer, reset UI và (tùy chọn) gửi lệnh TẮT."""
    
    # Dừng vòng lặp 'after' nếu đang chạy
    timer_id = seat_timers[relay_id].get('timer_id')
    if timer_id:
        root.after_cancel(timer_id)
        
    # Gửi lệnh TẮT (nếu được yêu cầu)
    if send_off_command:
        send_command(f"OFF{relay_id}")
        
    # Reset trạng thái
    seat_timers[relay_id]['end_time'] = None
    seat_timers[relay_id]['timer_id'] = None
    
    # Cập nhật UI về trạng thái "Sẵn sàng"
    update_ui_for_seat(relay_id, 'available')

def update_ui_for_seat(relay_id, state):
    """Cập nhật giao diện cho một thẻ vị trí."""
    elements = ui_elements[relay_id]
    if state == 'active':
        elements['status_label'].config(text="Trạng thái: Đang sử dụng", fg=COLOR_PRIMARY)
        elements['start_button'].config(state=tk.DISABLED, bg=COLOR_GRAY_LIGHT)
        elements['stop_button'].config(state=tk.NORMAL, bg=COLOR_ACCENT)
        elements['card_frame'].config(bg="#F7F3EE") # SỬA: Nền Be/Kem nhạt
    
    elif state == 'available':
        elements['status_label'].config(text="Trạng thái: Sẵn sàng", fg=COLOR_TEXT_LIGHT)
        elements['timer_label'].config(text="04:00:00")
        elements['start_button'].config(state=tk.NORMAL, bg=COLOR_PRIMARY)
        elements['stop_button'].config(state=tk.DISABLED, bg=COLOR_GRAY_LIGHT)
        elements['card_frame'].config(bg=COLOR_CARD) # Nền thẻ trắng

# ===================================================================
# HÀM XỬ LÝ ĐĂNG NHẬP
# ===================================================================

def handle_login():
    """Xử lý logic khi nhấn nút Đăng Nhập."""
    username = username_entry.get()
    password = password_entry.get()
    
    if username == "admin" and password == "12345":
        login_frame.pack_forget()
        main_app_frame.pack(fill="both", expand=True)
        # BẮT ĐẦU KẾT NỐI ARDUINO (CHỈ SAU KHI ĐĂNG NHẬP)
        root.after(100, connect_to_arduino)
        
        # <<< SỬA: Tải ảnh nền SAU KHI đăng nhập >>>
        root.after(110, load_and_set_background)
        
        # --- (MỚI) BẮT ĐẦU VÒNG LẶP ĐỌC SERIAL ---
        root.after(1000, check_serial_data) # Bắt đầu lắng nghe sau 1 giây
        
    else:
        login_status_label.config(text="Sai tên đăng nhập hoặc mật khẩu.", fg=COLOR_RED_ERROR)

# ===================================================================
# THIẾT LẬP GIAO DIỆN TKINTER
# ===================================================================

root = tk.Tk()
root.title("Study Cafe Manager")
root.attributes('-fullscreen', True) # Chạy full màn hình
root.config(bg="#FBF9F3") 

# <<< SỬA: Thêm biến toàn cục và hàm tải ảnh nền >>>
bg_image_tk = None

# --- (MỚI) Biến toàn cục cho nút quạt ---
fan_toggle_button = None 
is_fan_on = False
temp_label = None # <-- (MỚI) Biến toàn cục cho nhãn nhiệt độ

def load_and_set_background():
    """Tải và resize ảnh nền cho vừa màn hình."""
    global bg_image_tk
    global main_control_canvas # Cần canvas để đặt ảnh
    try:
        # Lấy kích thước màn hình hiện tại
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
    
        bg_path = "C:\\UEH\\2nd Year\\HK3 2025\\ComputerSience2\\a1.png"

        
        # Mở và resize ảnh
        bg_image_pil = Image.open(bg_path)
        bg_image_pil = bg_image_pil.resize((screen_width, screen_height), Image.Resampling.LANCZOS)
        bg_image_tk = ImageTk.PhotoImage(bg_image_pil)
        
        # Đặt ảnh vào canvas (nếu canvas đã tồn tại)
        if 'main_control_canvas' in globals():
            main_control_canvas.create_image(0, 0, image=bg_image_tk, anchor="nw", tags="bg_image")
            main_control_canvas.tag_lower('bg_image') # Đẩy ảnh xuống dưới cùng
    except Exception as e:
        print(f"Lỗi tải ảnh nền: {e}. Đảm bảo đường dẫn ảnh đúng.")
        # Nếu lỗi, giữ nguyên màu nền
        if 'main_control_canvas' in globals():
            main_control_canvas.config(bg=COLOR_BACKGROUND)
# --- KẾT THÚC HÀM ẢNH NỀN ---

# --- (MỚI) HÀM BẬT/TẮT QUẠT ---
def handle_fan_toggle():
    """Xử lý bật/tắt quạt và cập nhật nút bấm."""
    global is_fan_on
    global fan_toggle_button
    
    if not ser or not ser.isOpen():
        messagebox.showwarning("Chưa Kết Nối", "Vui lòng kiểm tra cáp và nhấn 'Kết Nối Lại'.")
        return

    try:
        if is_fan_on:
            # Nếu đang BẬT -> Gửi lệnh TẮT
            send_command("OFF_FAN")
            is_fan_on = False
            fan_toggle_button.config(text="Bật Quạt 💨", bg=COLOR_STATUS_SUCCESS, fg="white")
            main_status_label.config(text="Đã gửi lệnh 'TẮT Quạt'!", fg=COLOR_TEXT_LIGHT)
        else:
            # Nếu đang TẮT -> Gửi lệnh BẬT
            send_command("ON_FAN")
            is_fan_on = True
            fan_toggle_button.config(text="Tắt Quạt 🚫", bg=COLOR_RED_ERROR, fg="white")
            main_status_label.config(text="Đã gửi lệnh 'BẬT Quạt'!", fg=COLOR_TEXT_LIGHT)
    except Exception as e:
        messagebox.showerror("Lỗi Gửi Lệnh", f"Lỗi khi điều khiển quạt: {e}")
# --- KẾT THÚC HÀM QUẠT ---

# --- (MỚI) HÀM ĐỌC DỮ LIỆU SERIAL TỪ ARDUINO ---
def check_serial_data():
    """Đọc dữ liệu đến từ Arduino và cập nhật GUI."""
    global temp_label, main_status_label
    try:
        if ser and ser.isOpen() and ser.in_waiting > 0:
            # Đọc từng dòng dữ liệu
            while ser.in_waiting > 0:
                line = ser.readline().decode('utf-8').strip()
                
                if not line: # Bỏ qua dòng trống
                    continue

                # 1. Xử lý dữ liệu nhiệt độ (có tiền tố "TEMP:")
                if line.startswith("TEMP:"):
                    try:
                        temp_value = float(line.split(":")[1])
                        if 'temp_label' in globals() and temp_label:
                            # Cập nhật nhãn nhiệt độ trên Header
                            temp_label.config(text=f"Nhiệt độ: {temp_value:.1f} °C")
                    except (ValueError, IndexError):
                        print(f"Lỗi phân tích dữ liệu nhiệt độ: {line}")
                
                # 2. Xử lý các thông báo trạng thái (Relay, Quạt)
                elif line.startswith("Relay") or line.startswith("Quạt"):
                    if 'main_status_label' in globals() and main_status_label:
                        # Cập nhật nhãn trạng thái ở Footer
                        main_status_label.config(text=f"Trạng thái: {line}", fg=COLOR_TEXT_LIGHT)
                
                # (Có thể bỏ qua các dòng khác như "Invalid command"...)
                elif "Invalid" in line:
                    print(f"Arduino Báo Lỗi: {line}")

    except Exception as e:
        # Lỗi này có thể xảy ra khi ngắt kết nối
        # print(f"Lỗi khi đọc serial: {e}")
        pass
    
    # Hẹn giờ chạy lại hàm này sau 100ms
    root.after(100, check_serial_data)
# --- KẾT THÚC HÀM ĐỌC SERIAL ---


# --- (MỚI) ĐÃ DI CHUYỂN HÀM NÀY LÊN ĐÂY ---
# Đóng kết nối Serial khi cửa sổ GUI đóng
def on_closing():
    global ser
    global is_fan_on 
    
    # Tắt tất cả các relay đang bật trước khi thoát
    for i in range(1, 4):
        if seat_timers[i]['end_time']: # Nếu relay đang bật
            stop_timer(i, send_off_command=True)
            print(f"Đã tắt Vị trí {i} trước khi thoát.")
            
    # Tắt quạt nếu đang bật
    if is_fan_on:
        send_command("OFF_FAN")
        print("Đã tắt Quạt trước khi thoát.")
            
    time.sleep(0.5) # Chờ lệnh gửi đi
            
    if ser and ser.isOpen():
        print("Đang đóng cổng Serial...")
        ser.close()
    root.destroy()
# --- KẾT THÚC HÀM ON_CLOSING ---


# --- HÀM BẬT/TẮT FULL MÀN HÌNH (F11) ---
def toggle_fullscreen(event=None):
    is_fullscreen = root.attributes('-fullscreen')
    if is_fullscreen:
        root.attributes('-fullscreen', False)
        root.geometry("800x600") # Khôi phục kích thước cửa sổ
        root.resizable(True, True)
    else:
        root.attributes('-fullscreen', True)

root.bind('<F11>', toggle_fullscreen)
root.bind('<Escape>', toggle_fullscreen) # Thêm phím ESC để thoát


# --- BẢNG MÀU MỚI (PHONG CÁCH CAFE/CHIDORI) ---
COLOR_BACKGROUND = "#FBF9F3"  # Nền be rất nhạt
COLOR_CARD = "#FFFFFF"        # Nền thẻ (Trắng)
COLOR_PRIMARY = "#A1887F"     # SỬA: MÀU NÂU ẤM (Thay cho xanh lá)
COLOR_ACCENT = "#E8D8C9"      # Màu be/gỗ nhạt (cho nút phụ)
COLOR_TEXT_DARK = "#5B4C40"   # Nâu đậm (Màu chữ chính)
COLOR_TEXT_LIGHT = "#9C8F86"  # Nâu/Xám nhạt (Màu chữ phụ)
COLOR_BORDER = "#F0EBE5"      # Viền thẻ
COLOR_RED_ERROR = "#D9534F"   # Đỏ (Lỗi)
COLOR_GRAY_LIGHT = "#E0E0E0"  # Xám nhạt (cho nút bị vô hiệu hóa)
COLOR_BLUE_RESCAN = "#5B9BD5"  # Xanh dương (Nút quét cổng)
COLOR_STATUS_SUCCESS = "#668d6a" # SỬA: Xanh lá mạ (Trạng thái thành công)


# --- TẠO 2 KHUNG CHÍNH: ĐĂNG NHẬP VÀ ỨNG DỤNG ---
login_frame = tk.Frame(root, bg=COLOR_BACKGROUND)
main_app_frame = tk.Frame(root, bg=COLOR_BACKGROUND)

# ===================================================================
# KHUNG ĐĂNG NHẬP (THIẾT KẾ LẠI)
# ===================================================================

login_frame.pack(fill="both", expand=True, padx=0, pady=0)

# Khung chứa nội dung đăng nhập, có border
login_content_frame = tk.Frame(login_frame, bg=COLOR_CARD, bd=1, relief=tk.SOLID, highlightbackground=COLOR_BORDER, highlightthickness=1)
login_content_frame.place(relx=0.5, rely=0.45, anchor="center", width=320) # Đẩy lên 1 chút

# Font chữ
title_font = tkFont.Font(family="Helvetica", size=20, weight="bold") 
label_font = tkFont.Font(family="Helvetica", size=10, weight="bold") # SỬA: Thêm weight="bold"
button_font = tkFont.Font(family="Helvetica", size=10, weight="bold")
small_font = tkFont.Font(family="Helvetica", size=9, weight="bold") # SỬA: Thêm weight="bold"

# --- LOGO PLACEHOLDER ---
try:
    # --- THAY ĐỔI LOGO TẠI ĐÂY ---
    # Bạn cần thay đổi đường dẫn này thành đường dẫn logo của bạn
    logo_path = "C:\\Users\\DELL\\Downloads\\Gemini_Generated_Image_4puudk4puudk4puu.png" 
    logo_image = Image.open(logo_path)
    logo_image = logo_image.resize((250, 200), Image.Resampling.LANCZOS) # Resize logo nếu cần
    logo_tk = ImageTk.PhotoImage(logo_image)
    
    logo_label = tk.Label(login_content_frame, image=logo_tk, bg=COLOR_CARD)
    logo_label.image = logo_tk # Lưu tham chiếu
    logo_label.pack(pady=(30, 0), padx=30)
except Exception as e:
    print(f"Lỗi tải logo: {e}")
    # Nếu lỗi, hiển thị lại text cũ
    logo_placeholder = tk.Label(login_content_frame, text="[Lỗi tải Logo]", 
                                font=tkFont.Font(family="Helvetica", size=14, weight="bold"), 
                                bg=COLOR_BACKGROUND, fg=COLOR_RED_ERROR, 
                                pady=20)
    logo_placeholder.pack(pady=(30, 0), padx=30, fill=tk.X)

tk.Label(login_content_frame, text="Study Coffee House", font=title_font, bg=COLOR_CARD, fg=COLOR_TEXT_DARK).pack(pady=(5, 20))


# Tên đăng nhập
username_entry = tk.Entry(login_content_frame, font=label_font, 
                          bg=COLOR_BACKGROUND, fg=COLOR_TEXT_DARK, 
                          bd=1, relief=tk.SOLID, 
                          highlightbackground=COLOR_BORDER, highlightthickness=1)
username_entry.pack(pady=(5, 5), padx=25, ipady=8, fill=tk.X)
username_entry.insert(0, "Tên đăng nhập (admin)")
username_entry.config(fg=COLOR_TEXT_LIGHT)

# Mật khẩu
password_entry = tk.Entry(login_content_frame, font=label_font, 
                          bg=COLOR_BACKGROUND, fg=COLOR_TEXT_DARK, 
                          bd=1, relief=tk.SOLID, 
                          highlightbackground=COLOR_BORDER, highlightthickness=1,
                          show="*")
password_entry.pack(pady=5, padx=25, ipady=8, fill=tk.X)
password_entry.insert(0, "Mật khẩu (12345)")
password_entry.config(fg=COLOR_TEXT_LIGHT, show="") 

# Hàm xử lý placeholder (Giữ nguyên)
def on_username_click(event):
    if username_entry.get() == "Tên đăng nhập (admin)":
        username_entry.delete(0, "end")
        username_entry.config(fg=COLOR_TEXT_DARK)

def on_username_focusout(event):
    if username_entry.get() == '':
        username_entry.insert(0, "Tên đăng nhập (admin)")
        username_entry.config(fg=COLOR_TEXT_LIGHT)

def on_password_click(event):
    if password_entry.get() == "Mật khẩu (12345)":
        password_entry.delete(0, "end")
        password_entry.config(fg=COLOR_TEXT_DARK, show='*')

def on_password_focusout(event):
    if password_entry.get() == '':
        password_entry.insert(0, "Mật khẩu (12345)")
        password_entry.config(fg=COLOR_TEXT_LIGHT, show='')

username_entry.bind('<FocusIn>', on_username_click)
username_entry.bind('<FocusOut>', on_username_focusout)
password_entry.bind('<FocusIn>', on_password_click)
password_entry.bind('<FocusOut>', on_password_focusout)


# Nút Đăng Nhập (Đổi màu)
login_button = tk.Button(login_content_frame, text="Đăng nhập", command=handle_login, 
                         font=button_font, bg=COLOR_PRIMARY, fg=COLOR_CARD, 
                         activebackground=COLOR_PRIMARY, activeforeground=COLOR_CARD,
                         relief=tk.FLAT, bd=0, padx=20, pady=10)
login_button.pack(pady=15, padx=25, fill=tk.X, ipady=4)

# Nhãn trạng thái đăng nhập (để báo lỗi)
login_status_label = tk.Label(login_content_frame, text="", font=small_font, bg=COLOR_CARD, fg=COLOR_RED_ERROR, wraplength=250)
login_status_label.pack(pady=(0, 20))


# --- KHUNG TRẠNG THÁI KẾT NỐI (MỚI) ---
connect_status_frame = tk.Frame(login_frame, bg=COLOR_BACKGROUND)
connect_status_frame.place(relx=0.5, rely=0.85, anchor="center", width=300)

tk.Label(connect_status_frame, text="--- TRẠNG THÁI KẾT NỐI ---", font=small_font, bg=COLOR_BACKGROUND, fg=COLOR_TEXT_LIGHT).pack(pady=5)

port_status_label = tk.Label(connect_status_frame, text="Đang tìm cổng...", 
                             font=label_font, bg=COLOR_BACKGROUND, fg=COLOR_TEXT_DARK)
port_status_label.pack(pady=5)

rescan_button = tk.Button(connect_status_frame, text="🔄 Quét lại cổng", command=update_port_status,
                          font=button_font, bg=COLOR_BLUE_RESCAN, fg="white",
                          relief=tk.FLAT, bd=0, padx=10, pady=5)
rescan_button.pack(pady=10, ipady=2)


# ===================================================================
# KHUNG ỨNG DỤNG CHÍNH (ĐÃ SỬA BỐ CỤC)
# ===================================================================

# --- Header ---
header_frame = tk.Frame(main_app_frame, bg=COLOR_CARD, highlightbackground=COLOR_BORDER, highlightthickness=1)
header_frame.pack(fill=tk.X, side=tk.TOP)

# Tiêu đề (Bên trái)
tk.Label(header_frame, text="Study Coffee House",
         font=("Helvetica", 16, "bold"), 
         bg=COLOR_CARD, fg=COLOR_TEXT_DARK, 
         pady=15, padx=20, anchor="w").pack(side=tk.LEFT)

# --- (MỚI) Khung bên phải Header (chứa Nhiệt độ và Nút Quạt) ---
right_header_frame = tk.Frame(header_frame, bg=COLOR_CARD)
right_header_frame.pack(side=tk.RIGHT, padx=20, pady=10, fill=tk.Y)

# (MỚI) Nhãn nhiệt độ
temp_label = tk.Label(right_header_frame, 
                      text="Nhiệt độ: --.- °C", 
                      font=("Helvetica", 10, "bold"),
                      bg=COLOR_CARD, 
                      fg=COLOR_TEXT_DARK) # Dùng màu chữ đậm
temp_label.pack(side=tk.LEFT, padx=(0, 15), anchor="center") # Đặt bên trái khung bên phải

# NÚT BẬT/TẮT QUẠT
fan_toggle_button = tk.Button(right_header_frame, 
                              text="Bật Quạt 💨", 
                              command=handle_fan_toggle,
                              font=("Helvetica", 10, "bold"),
                              bg=COLOR_STATUS_SUCCESS, # Màu xanh lá ban đầu
                              fg="white",
                              relief=tk.FLAT, 
                              bd=0, 
                              padx=15, 
                              pady=5)
fan_toggle_button.pack(side=tk.LEFT, anchor="center", padx=(0, 10)) # Thêm khoảng cách

# --- (MỚI) NÚT KẾT THÚC CA ---
end_shift_button = tk.Button(right_header_frame,
                             text="Kết thúc ca 🔚",
                             command=on_closing, # <-- Giờ đã hoạt động
                             font=("Helvetica", 10, "bold"),
                             bg=COLOR_ACCENT, # <-- Màu be (giống nút "Kết thúc sớm")
                             fg=COLOR_TEXT_DARK, # <-- Màu chữ nâu đậm
                             relief=tk.FLAT,
                             bd=0,
                             padx=15,
                             pady=5)
end_shift_button.pack(side=tk.LEFT, anchor="center")
# --- KẾT THÚC PHẦN HEADER MỚI ---


# <<< SỬA: Đổi main_control_frame thành main_control_canvas >>>
global main_control_canvas
main_control_canvas = tk.Canvas(main_app_frame, bg=COLOR_BACKGROUND, bd=0, highlightthickness=0)
main_control_canvas.pack(fill=tk.BOTH, expand=True, side=tk.TOP)

# <<< SỬA: Khung đệm này giờ nằm trên Canvas >>>
centered_frame = tk.Frame(main_control_canvas, bg=COLOR_BACKGROUND, bd=0, highlightthickness=0)

# <<< SỬA: Dùng create_window để đặt centered_frame LÊN TRÊN Canvas >>>
global centered_frame_window_id
centered_frame_window_id = main_control_canvas.create_window(0, 0, anchor="nw", window=centered_frame)

# <<< SỬA: Hàm tự động căn giữa khi resize cửa sổ >>>
def center_frame_on_resize(event):
    try:
        canvas_width = event.width
        canvas_height = event.height
        # Di chuyển cụm thẻ vào giữa
        main_control_canvas.coords(centered_frame_window_id, canvas_width // 2, canvas_height // 2)
        main_control_canvas.itemconfig(centered_frame_window_id, anchor="center")
    except Exception as e:
        pass # Bỏ qua lỗi khi cửa sổ đóng

# Bind hàm này
main_control_canvas.bind("<Configure>", center_frame_on_resize)


# --- Footer (chứa trạng thái và nút kết nối lại) ---
footer_frame = tk.Frame(main_app_frame, bg=COLOR_CARD, height=50, highlightbackground=COLOR_BORDER, highlightthickness=1)
footer_frame.pack(fill=tk.X, side=tk.BOTTOM)
footer_frame.pack_propagate(False) # Ngăn footer co lại

main_status_label = tk.Label(footer_frame, text="Đang cố gắng kết nối...", 
                             font=("Helvetica", 10, "bold"), bg=COLOR_CARD, fg=COLOR_TEXT_LIGHT)
main_status_label.pack(side=tk.LEFT, padx=20)

reconnect_button = tk.Button(footer_frame, text="🔄 KẾT NỐI LẠI", command=connect_to_arduino, 
                             bg=COLOR_BLUE_RESCAN, fg="white", 
                             font=("Helvetica", 9, "bold"), 
                             padx=10, pady=5, relief=tk.FLAT, bd=0)
reconnect_button.pack(side=tk.RIGHT, padx=20)


# --- PIN MAP ---
PIN_MAP = {
    1: "Khu V vực A", 2: "Khu Vực B", 3: "Khu Vực C",
}

# --- THÊM CÁC ĐƯỜNG DẪN ẢNH CỦA BẠN VÀO ĐÂY ---
IMAGE_PATHS = {
    1: "C:\\UEH\\2nd Year\\HK3 2025\\ComputerSience2\\giaodien6.png", # <-- THAY ĐƯỜNG DẪN ẢNH VỊ TRÍ 1
    2: "C:\\UEH\\2nd Year\\HK3 2025\\ComputerSience2\\giaodien7.png", # <-- THAY ĐƯỜNG DẪN ẢNH VỊ TRÍ 2
    3: "C:\\UEH\\2nd Year\\HK3 2025\\ComputerSience2\\giaodien8.png"  # <-- THAY ĐƯỜN G DẪN ẢNH VỊ TRÍ 3
}

# --- Lưu trữ các widget
ui_elements = {}

# --- Vòng lặp tạo 3 thẻ điều khiển (Card) ---
for i in range(1, 4):
    
    # <<< SỬA: Thay parent thành centered_frame >>>
    card_frame = tk.Frame(centered_frame, bg=COLOR_CARD, padx=20, pady=20,
                          highlightbackground=COLOR_BORDER, highlightthickness=1)
    
    # SỬA BỐ CỤC: Chia layout
    card_frame.pack(side=tk.LEFT, fill=tk.Y, expand=False, padx=10, pady=10)

    # --- 1. Khung Ảnh (Bên trái) ---
    image_frame = tk.Frame(card_frame, bg=COLOR_BACKGROUND, 
                           highlightbackground=COLOR_BORDER, highlightthickness=1)
    
    image_frame.pack(side=tk.LEFT, fill=tk.Y, expand=False, padx=(0, 20))
    image_frame.pack_propagate(False) # Ngăn co lại
    
    # --- CODE CHÈN HÌNH ẢNH MỚI ---
    try:
        # Lấy đường dẫn ảnh
        img_path = IMAGE_PATHS[i]
        
        # Mở ảnh
        pil_image = Image.open(img_path)
        
        # Sửa lại kích thước ảnh
        pil_image = pil_image.resize((130, 450), Image.Resampling.LANCZOS) 
        
        # Chuyển sang ảnh Tkinter
        photo = ImageTk.PhotoImage(pil_image)
        
        # Tạo label để chứa ảnh
        image_label = tk.Label(image_frame, image=photo, bg=COLOR_BACKGROUND)
        image_label.image = photo # QUAN TRỌNG: Lưu tham chiếu
        image_label.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    except Exception as e:
        print(f"Lỗi tải ảnh cho Vị trí {i}: {e}")
        # Nếu lỗi, hiển thị lại placeholder
        tk.Label(image_frame, text=f"[Lỗi tải ảnh {i}]", 
                 font=("Helvetica", 12, "italic"), 
                 bg=COLOR_BACKGROUND, fg=COLOR_RED_ERROR,
                 wraplength=180).place(relx=0.5, rely=0.5, anchor="center")
    # --- KẾT THÚC CODE CHÈN HÌNH ẢNH ---


    # --- 2. Khung Nội dung (Bên phải) ---
    content_frame = tk.Frame(card_frame, bg=COLOR_CARD)
    
    content_frame.pack(side=tk.LEFT, fill=tk.Y, expand=False, padx=(10, 0))
    
    # Tiêu đề Vị trí
    tk.Label(content_frame, text=f"Vị trí {i}", 
             font=("Helvetica", 18, "bold"), 
             fg=COLOR_TEXT_DARK, bg=COLOR_CARD, anchor="w").pack(fill=tk.X, pady=(10, 0))
    
    tk.Label(content_frame, text=PIN_MAP[i], 
             font=("Helvetica", 11, "bold"), 
             fg=COLOR_TEXT_LIGHT, bg=COLOR_CARD, anchor="w").pack(fill=tk.X, pady=(0, 20))

    # Nhãn Trạng thái
    status_label = tk.Label(content_frame, text="Trạng thái: Sẵn sàng", 
                            font=("Helvetica", 12, "bold"), 
                            fg=COLOR_TEXT_LIGHT, bg=COLOR_CARD, anchor="w")
    status_label.pack(fill=tk.X, pady=10)

    # Nhãn Đồng hồ
    tk.Label(content_frame, text="Thời gian còn lại:", 
             font=("Helvetica", 10, "bold"), 
             fg=COLOR_TEXT_LIGHT, bg=COLOR_CARD, anchor="w").pack(fill=tk.X, pady=(10, 0))
    
    timer_label = tk.Label(content_frame, text="04:00:00", 
                           font=("Helvetica", 36, "bold"), 
                           fg=COLOR_PRIMARY, bg=COLOR_CARD, anchor="w")
    timer_label.pack(fill=tk.X, pady=5)

    # --- Khung nút bấm ---
    button_frame = tk.Frame(content_frame, bg=COLOR_CARD)
    button_frame.pack(fill=tk.X, pady=20, side=tk.BOTTOM, expand=True) # Đẩy xuống dưới

    # Nút Bắt đầu
    start_button = tk.Button(button_frame, text="Bắt đầu (4h)", 
                             font=("Helvetica", 11, "bold"),
                             command=lambda id=i: start_timer(id),
                             bg=COLOR_PRIMARY, fg=COLOR_CARD, 
                             relief=tk.FLAT, bd=0, activebackground=COLOR_PRIMARY,
                             width=15, height=2)
    start_button.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5, padx=(0, 5))
    
    # Nút Kết thúc sớm
    stop_button = tk.Button(button_frame, text="Kết thúc sớm", 
                            font=("Helvetica", 11, "bold"),
                            command=lambda id=i: stop_timer(id, send_off_command=True),
                            bg=COLOR_GRAY_LIGHT, fg=COLOR_TEXT_DARK, 
                            relief=tk.FLAT, bd=0, activebackground=COLOR_ACCENT,
                            width=15, height=2, state=tk.DISABLED)
    stop_button.pack(side=tk.RIGHT, fill=tk.X, expand=True, ipady=5, padx=(5, 0))

    # Lưu các widget vào dictionary để dễ truy cập
    ui_elements[i] = {
        'card_frame': card_frame,
        'status_label': status_label,
        'timer_label': timer_label,
        'start_button': start_button,
        'stop_button': stop_button
    }

# ===================================================================
# CHẠY ỨNG DỤNG
# ===================================================================

# Tự động quét cổng khi khởi chạy
root.after(100, update_port_status)

# (MỚI) Đã di chuyển hàm on_closing lên trên, chỉ để lại dòng này
root.protocol("WM_DELETE_WINDOW", on_closing)
root.mainloop()