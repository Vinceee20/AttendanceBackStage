import sqlite3
import os
import cv2
import csv
import qrcode
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from pyzbar import pyzbar
import threading
from PIL import Image, ImageTk
import numpy as np
import datetime

def create_database():
    with sqlite3.connect('attendance.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                firstname TEXT NOT NULL,
                lastname TEXT NOT NULL,
                contact_number TEXT NOT NULL,
                email TEXT NOT NULL,
                name TEXT NOT NULL,
                date_registered TEXT NOT NULL,
                membership_type TEXT NOT NULL
            )
        ''')
        conn.commit()

def add_member(firstname, lastname, contact_number, email, name, date_registered, membership_type):
    with sqlite3.connect('attendance.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO members (firstname, lastname, contact_number, email, name, date_registered, membership_type)
            VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (firstname, lastname, contact_number, email, name, date_registered, membership_type))
        conn.commit()

def delete_member(name):
    with sqlite3.connect('attendance.db') as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM members WHERE name = ?', (name,))
        conn.commit()
        
    qr_code_file = f"{name}.png"
    if os.path.exists(qr_code_file):
        try:
            os.remove(qr_code_file)
        except OSError as e:
            print(f"Error deleting file {qr_code_file}: {e}")

def generate_qr_code(data, filename):
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')
    img.save(filename)

def scan_qr_code(scanned_listbox, scanned_members):
    scanned_qr_codes = set()

    def scan():
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            messagebox.showerror("Error", "Failed to open the camera.")
            return

        while True:
            ret, frame = cap.read()
            if not ret:
                print("Failed to grab frame")
                break

            decoded_objects = pyzbar.decode(frame)
            for obj in decoded_objects:
                points = obj.polygon
                if len(points) == 4:
                    pts = [(point.x, point.y) for point in points]
                    pts = np.array(pts, dtype=np.int32)
                    pts = pts.reshape((-1, 1, 2))
                    cv2.polylines(frame, [pts], True, (0, 255, 0), 2)

                qr_data = obj.data.decode("utf-8")

                if qr_data in scanned_qr_codes:
                    messagebox.showerror("Error", "User has already been scanned.")
                else:
                    with sqlite3.connect('attendance.db') as conn:
                        cursor = conn.cursor()
                        cursor.execute('SELECT firstname, lastname, membership_type FROM members WHERE name = ?', (qr_data,))
                        member_info = cursor.fetchone()

                    if member_info:
                        firstname, lastname, membership_type = member_info
                        messagebox.showinfo("Attendance", f"Member Info:\nFirst Name: {firstname}\nLast Name: {lastname}\nMembership Type: {membership_type}")
                        scanned_qr_codes.add(qr_data)
                        scanned_members.append(qr_data)
                        scanned_listbox.insert(tk.END, qr_data)
                    else:
                        messagebox.showwarning("Attendance", "User not found.")

            cv2.imshow('QR Code Scanner', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()  # Ensure all OpenCV windows are closed when exiting the loop

    threading.Thread(target=scan).start()

def create_member():
    member_window = tk.Toplevel()
    member_window.title("Create Member")
    center_window(member_window, 300, 300)

    frame = tk.Frame(member_window)
    frame.pack(fill=tk.BOTH, expand=True)

    scrollbar = tk.Scrollbar(frame, orient=tk.VERTICAL)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    canvas = tk.Canvas(frame, yscrollcommand=scrollbar.set)
    scrollbar.config(command=canvas.yview)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    input_frame = tk.Frame(canvas)
    canvas.create_window((0, 0), window=input_frame, anchor=tk.NW)

    fields = ["Firstname", "Lastname", "Contact Number", "Email Address"]
    entries = {}

    for i, field in enumerate(fields):
        tk.Label(input_frame, text=f"{field}:").grid(row=i, column=0, padx=5, pady=5, sticky=tk.W)
        entry = tk.Entry(input_frame)
        entry.grid(row=i, column=1, padx=5, pady=5, sticky=tk.W)
        entries[field.lower().replace(" ", "_")] = entry

    tk.Label(input_frame, text="Membership Type:").grid(row=4, column=0, padx=5, pady=5, sticky=tk.W)
    membership_type_var = tk.StringVar(value="Member")
    tk.Radiobutton(input_frame, text="Member", variable=membership_type_var, value="Member").grid(row=4, column=1, padx=5, pady=5, sticky=tk.W)
    tk.Radiobutton(input_frame, text="Pre-Reg", variable=membership_type_var, value="Pre-Reg").grid(row=5, column=1, padx=5, pady=5, sticky=tk.W)

    def save_member():
        firstname = entries["firstname"].get()
        lastname = entries["lastname"].get()
        contact_number = entries["contact_number"].get()
        email_address = entries["email_address"].get()
        membership_type = membership_type_var.get()

        if not firstname or not lastname or not contact_number or not email_address or not membership_type:
            messagebox.showerror("Error", "All fields are required.")
            return

        name = f"{firstname} {lastname}"
        date_registered = datetime.datetime.now().strftime("%Y-%m-%d")
        add_member(firstname, lastname, contact_number, email_address, name, date_registered, membership_type)
        generate_qr_code(name, f"{name}.png")
        messagebox.showinfo("Member Created", f"Member {name} ({membership_type}) created and QR code saved as {name}.png.")
        member_window.destroy()

    tk.Button(input_frame, text="Save", command=save_member).grid(row=6, columnspan=2, padx=5, pady=10)
    input_frame.update_idletasks()
    canvas.config(scrollregion=canvas.bbox(tk.ALL))

def delete_pre_reg_members():
    def confirm_delete():
        entered_pin = pin_entry.get()
        if entered_pin == "2024":
            with sqlite3.connect('attendance.db') as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT name FROM members WHERE membership_type = ?', ("Pre-Reg",))
                pre_reg_members = cursor.fetchall()
                for member in pre_reg_members:
                    name = member[0]
                    cursor.execute('DELETE FROM members WHERE name = ?', (name,))
                    conn.commit()

                    qr_code_file = f"{name}.png"
                    if os.path.exists(qr_code_file):
                        os.remove(qr_code_file)

            messagebox.showinfo("Members Deleted", "All Pre-Reg members and their associated QR codes have been deleted.")
            pin_window.destroy()
            view_members()
        else:
            messagebox.showerror("Incorrect PIN", "The entered PIN is incorrect. Please try again.")

    pin_window = tk.Toplevel()
    pin_window.title("PIN Verification")
    center_window(pin_window, 300, 150)

    tk.Label(pin_window, text="Enter PIN to delete all Pre-Reg members:").pack(pady=5)
    pin_entry = tk.Entry(pin_window, show="*")
    pin_entry.pack(pady=5)

    tk.Button(pin_window, text="Confirm", command=confirm_delete).pack(pady=10)

def view_members():
    view_window = tk.Toplevel()
    view_window.title("View Members")
    center_window(view_window, 700, 400)

    frame = tk.Frame(view_window)
    frame.pack(fill=tk.BOTH, expand=True)

    scrollbar = tk.Scrollbar(frame, orient=tk.VERTICAL)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    tree = ttk.Treeview(frame, columns=("firstname", "lastname", "date_registered", "membership_type", "qr_code"), show='headings', yscrollcommand=scrollbar.set)
    tree.heading("firstname", text="First Name", command=lambda: sort_treeview(tree, "firstname", False))
    tree.heading("lastname", text="Last Name", command=lambda: sort_treeview(tree, "lastname", False))
    tree.heading("date_registered", text="Registered Date")
    tree.heading("membership_type", text="Membership Type")
    tree.heading("qr_code", text="QR Code")

    tree.column("firstname", width=100)
    tree.column("lastname", width=100)
    tree.column("date_registered", width=100)
    tree.column("membership_type", width=100)
    tree.column("qr_code", width=200)

    scrollbar.config(command=tree.yview)
    tree.pack(fill=tk.BOTH, expand=True)

    with sqlite3.connect('attendance.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT firstname, lastname, date_registered, membership_type, name FROM members')
        for row in cursor.fetchall():
            tree.insert("", tk.END, values=row)

    def delete_selected_member():
        selected_item = tree.selection()[0]
        member_name = tree.item(selected_item)["values"][4]
        tree.delete(selected_item)
        delete_member(member_name)

    delete_button = tk.Button(view_window, text="Delete Member", command=delete_selected_member)
    delete_button.pack(pady=10)
    delete_pre_reg_button = tk.Button(view_window, text="Delete All Pre-Reg Members", command=delete_pre_reg_members)
    delete_pre_reg_button.pack(pady=10)

def sort_treeview(tree, col, reverse):
    data = [(tree.set(child, col), child) for child in tree.get_children("")]
    data.sort(reverse=reverse)
    for index, (val, child) in enumerate(data):
        tree.move(child, "", index)
    tree.heading(col, command=lambda: sort_treeview(tree, col, not reverse))

def export_members_to_csv():
    filename = simpledialog.askstring("Save As", "Enter the filename (without extension):")
    if filename:
        filepath = f"{filename}.csv"
        with open(filepath, "w", newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["First Name", "Last Name", "Contact Number", "Email", "Membership Type", "QR Code Image"])
            with sqlite3.connect('attendance.db') as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT firstname, lastname, contact_number, email, membership_type, name FROM members')
                for row in cursor.fetchall():
                    firstname, lastname, contact_number, email, membership_type, name = row
                    qr_code_image = f"{name}.png"
                    writer.writerow([firstname, lastname, contact_number, email, membership_type, qr_code_image])
        messagebox.showinfo("Exported", f"Member list exported to {filepath}")

def save_scanned_members(scanned_members):
    filename = simpledialog.askstring("Save As", "Enter the filename (without extension):")
    if filename:
        filepath = f"{filename}.csv"
        with open(filepath, "w", newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["QR Code/Name", "Date", "Time"])  # Write the header
            for member in scanned_members:
                # Split the timestamp from the member data if available
                qr_data = member.split(",")[0] if "," in member else member
                date_time = datetime.datetime.now().strftime("%Y-%m-%d, %H:%M:%S")
                date, time = date_time.split(", ")
                writer.writerow([qr_data, date, time])  # Write the member data
        messagebox.showinfo("Saved", f"Scanned members saved to {filepath}")

def reset_scanned_members(scanned_members, scanned_listbox):
    scanned_members.clear()
    scanned_listbox.delete(0, tk.END)
    messagebox.showinfo("Reset", "Scanned member list has been reset.")

def center_window(window, width, height):
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    position_top = int(screen_height / 2 - height / 2)
    position_right = int(screen_width / 2 - width / 2)
    window.geometry(f'{width}x{height}+{position_right}+{position_top}')

def login():
    login_window = tk.Tk()
    login_window.title("Admin Login")
    center_window(login_window, 300, 190)  # Centering the window

    def check_login():
        username = username_entry.get()
        password = password_entry.get()

        if username == "admin" and password == "bsq123":
            login_window.destroy()
            main()
        else:
            messagebox.showerror("Login Failed", "Invalid username or password")

    tk.Label(login_window, text="Username:").pack(pady=5)
    username_entry = tk.Entry(login_window)
    username_entry.pack(pady=5)

    tk.Label(login_window, text="Password:").pack(pady=5)
    password_entry = tk.Entry(login_window, show="*")
    password_entry.pack(pady=5)

    tk.Button(login_window, text="Login", command=check_login).pack(pady=10)

    login_window.mainloop()

def main():
    create_database()

    root = tk.Tk()
    root.title("Attendance Checker")
    root.configure(background='gray15')  # Set the main window background color

    # Increase the size of the window
    window_width = 670
    window_height = 670
    center_window(root, window_width, window_height)

    scanned_members = []

    # Buttons with customized styles
    scan_button = tk.Button(text="Scan", command=lambda: scan_qr_code(scanned_listbox, scanned_members), bg="gray50", fg="white", padx=15, pady=8, font=("Arial", 14, "bold"))
    scan_button.pack(pady=10)

    create_button = tk.Button(text="Create Member/QR Code", command=create_member, bg="gray50", fg="white", padx=15, pady=8, font=("Arial", 14, "bold"))
    create_button.pack(pady=10)

    view_button = tk.Button(text="View Members", command=view_members, bg="gray50", fg="white", padx=15, pady=8, font=("Arial", 14, "bold"))
    view_button.pack(pady=10)

    export_button = tk.Button(text="Export List Member", command=export_members_to_csv, bg="gray50", fg="white", padx=15, pady=8, font=("Arial", 14, "bold"))
    export_button.pack(pady=10)

    # Label for scanned members
    tk.Label(root, text="Scanned Members:", bg="gray15", fg="white", font=("Arial", 16)).pack(pady=10)

    # Listbox for scanned members
    scanned_listbox = tk.Listbox(root, bg="gray30", fg="white", font=("Arial", 12), selectbackground="gray50", selectforeground="white")
    scanned_listbox.pack(pady=10, fill=tk.BOTH, expand=True)

    # Frame for Save and Reset buttons
    button_frame2 = tk.Frame(root, bg="gray15")
    button_frame2.pack(pady=20)

    save_button = tk.Button(button_frame2, text="Save Scanned Members", command=lambda: save_scanned_members(scanned_members), bg="gray50", fg="white", padx=15, pady=8, font=("Arial", 14, "bold"))
    save_button.pack(side=tk.LEFT, padx=20)

    reset_button = tk.Button(button_frame2, text="Reset Scanned Members", command=lambda: reset_scanned_members(scanned_members, scanned_listbox), bg="gray50", fg="white", padx=15, pady=8, font=("Arial", 14, "bold"))
    reset_button.pack(side=tk.LEFT, padx=20)

    root.bind("<Control-d>", lambda event: delete_pre_reg_members())
    root.mainloop()

if __name__ == "__main__":
    login()