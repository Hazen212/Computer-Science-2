import tkinter as tk
from tkinter import messagebox
import serial, serial.tools.list_ports
import threading, time
from datetime import datetime

#screen serial
def find_arduino_port():
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if "Arduino" in port.description or "CH340" in port.description:
            return port.device
    return "COM3"

port_name = find_arduino_port()
baud_rate = 9600

try:
    ser = serial.Serial(port_name, baud_rate, timeout=1)
except:
    ser = None

# login screen
def login_screen():
    login = tk.Tk()
    login.title("Đăng nhập ca trực bảo vệ")
    login.geometry("400x300")
    login.config(bg="#1c1c1c")

    tk.Label(login, text="🔒 ĐĂNG NHẬP", font=("Arial", 20, "bold"), fg="white", bg="#1c1c1c").pack(pady=20)

    tk.Label(login, text="Tên bảo vệ:", font=("Arial", 12), fg="white", bg="#1c1c1c").pack()
    entry_user = tk.Entry(login, font=("Arial", 12))
    entry_user.pack(pady=5)

    tk.Label(login, text="Mật khẩu:", font=("Arial", 12), fg="white", bg="#1c1c1c").pack()
    entry_pass = tk.Entry(login, font=("Arial", 12), show="*")
    entry_pass.pack(pady=5)

    def check_login():
        user = entry_user.get().strip()
        pw = entry_pass.get().strip()
        if user == "" or pw == "":
            messagebox.showwarning("Lỗi", "Vui lòng nhập đầy đủ thông tin!")
            return

        # Tài khoản mẫu
        accounts = {"baove1": "1234", "baove2": "5678"}
        if user in accounts and accounts[user] == pw:
            login.destroy()
            open_main_gui(user)
        else:
            messagebox.showerror("Sai thông tin", "Tên đăng nhập hoặc mật khẩu không đúng!")

    tk.Button(login, text="Đăng nhập", command=check_login, font=("Arial", 12, "bold"),
              bg="#00cc66", fg="white", width=15).pack(pady=15)

    login.mainloop()

# gui chinh
def open_main_gui(guard_name):
    global slot_states, time_in, time_out

    root = tk.Tk()
    root.title("🚗 HỆ THỐNG GIỮ XE Ô TÔ")
    root.geometry("650x550")
    root.configure(bg="#1b1b1b")

    start_time = datetime.now().strftime("%H:%M:%S  %d/%m/%Y")

    # bai giu xe
    tk.Label(root, text="BÃI GIỮ XE Ô TÔ", font=("Arial", 22, "bold"),
             fg="white", bg="#1b1b1b").pack(pady=10)

    lbl_guard = tk.Label(root, text=f"Bảo vệ: {guard_name}  |  Giờ vào ca: {start_time}",
                         font=("Arial", 12), fg="yellow", bg="#1b1b1b")
    lbl_guard.pack()

    lbl_time = tk.Label(root, text="", font=("Arial", 12), fg="cyan", bg="#1b1b1b")
    lbl_time.pack()

    def update_clock():
        lbl_time.config(text="⏰ " + datetime.now().strftime("%H:%M:%S  %d/%m/%Y"))
        root.after(1000, update_clock)
    update_clock()

    # bai giu xe
    frame_slots = tk.Frame(root, bg="#1b1b1b")
    frame_slots.pack(pady=20)

    slot_labels = []
    lbl_times = []
    slot_states = [0, 0, 0]
    time_in = ["--", "--", "--"]
    time_out = ["--", "--", "--"]

    for i in range(3):
        frame = tk.Frame(frame_slots, bg="#1b1b1b")
        frame.grid(row=0, column=i, padx=15)

        lbl_slot = tk.Label(frame, text=f"Ô {i+1}\n(Trống)",
                            font=("Arial", 14, "bold"),
                            bg="green", fg="white", width=12, height=4,
                            relief="groove", bd=3)
        lbl_slot.pack()

        lbl_time_slot = tk.Label(frame, text="Giờ vào: --\nGiờ ra: --",
                                 font=("Arial", 10), fg="cyan", bg="#1b1b1b")
        lbl_time_slot.pack(pady=5)

        slot_labels.append(lbl_slot)
        lbl_times.append(lbl_time_slot)

    # nhan du lieu tu arduino
    def update_parking_status(parts):
        global slot_states, time_in, time_out
        for i in range(3):
            new_state = int(parts[i])
            if new_state == 1 and slot_states[i] == 0:
                slot_labels[i].config(bg="red", text=f"Ô {i+1}\n(Có xe)")
                time_in[i] = datetime.now().strftime("%H:%M:%S")
                lbl_times[i].config(text=f"Giờ vào: {time_in[i]}\nGiờ ra: --")
            elif new_state == 0 and slot_states[i] == 1:
                slot_labels[i].config(bg="green", text=f"Ô {i+1}\n(Trống)")
                time_out[i] = datetime.now().strftime("%H:%M:%S")
                lbl_times[i].config(text=f"Giờ vào: {time_in[i]}\nGiờ ra: {time_out[i]}")
            slot_states[i] = new_state

    def read_serial():
        while True:
            try:
                if ser and ser.in_waiting > 0:
                    line = ser.readline().decode("utf-8", errors="ignore").strip()
                    parts = line.split()
                    if len(parts) == 3 and all(p in ["0", "1"] for p in parts):
                        update_parking_status(parts)
            except:
                pass
            time.sleep(0.2)

    threading.Thread(target=read_serial, daemon=True).start()

    # ket thuc ca truc
    def end_shift():
        end_time = datetime.now().strftime("%H:%M:%S  %d/%m/%Y")
        messagebox.showinfo("Kết thúc ca", f"Bảo vệ: {guard_name}\nGiờ ra ca: {end_time}")
        root.destroy()

    tk.Button(root, text="Kết thúc ca trực", command=end_shift,
              font=("Arial", 12, "bold"), bg="#cc0000", fg="white").pack(pady=15)

    root.mainloop()

# chay chuong trinh
if __name__ == "__main__":
    login_screen()
