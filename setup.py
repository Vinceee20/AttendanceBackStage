from cx_Freeze import setup, Executable

setup(
    name="attendance_checker",
    version="1.0",
    description="Attendance Checker Application",
    executables=[Executable("attendance_checker.py", base=None)]
)
