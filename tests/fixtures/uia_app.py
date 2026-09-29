import win32api
import win32con
import win32gui

CLASS_NAME = "JarvisUIAFixture"
EDIT_ID = 101
BUTTON_ID = 102
RESULT_ID = 103


def wndproc(hwnd, msg, wparam, lparam):
    if msg == win32con.WM_COMMAND and win32api.LOWORD(wparam) == BUTTON_ID:
        edit = win32gui.GetDlgItem(hwnd, EDIT_ID)
        result = win32gui.GetDlgItem(hwnd, RESULT_ID)
        value = win32gui.GetWindowText(edit)
        win32gui.SetWindowText(result, "saved:" + value)
        return 0
    if msg == win32con.WM_DESTROY:
        win32gui.PostQuitMessage(0)
        return 0
    return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)


instance = win32api.GetModuleHandle(None)
wc = win32gui.WNDCLASS()
wc.hInstance = instance
wc.lpszClassName = CLASS_NAME
wc.lpfnWndProc = wndproc
atom = win32gui.RegisterClass(wc)

hwnd = win32gui.CreateWindow(
    atom,
    "Jarvis UIA Fixture",
    win32con.WS_OVERLAPPEDWINDOW | win32con.WS_VISIBLE,
    100, 100, 420, 220,
    0, 0, instance, None,
)

win32gui.CreateWindow(
    "Edit", "",
    win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.WS_BORDER | win32con.WS_TABSTOP,
    20, 20, 360, 28,
    hwnd, EDIT_ID, instance, None,
)
win32gui.CreateWindow(
    "Button", "Save",
    win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.WS_TABSTOP,
    20, 65, 100, 32,
    hwnd, BUTTON_ID, instance, None,
)
win32gui.CreateWindow(
    "Static", "idle",
    win32con.WS_CHILD | win32con.WS_VISIBLE,
    20, 115, 360, 28,
    hwnd, RESULT_ID, instance, None,
)

win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
win32gui.UpdateWindow(hwnd)
win32gui.PumpMessages()
