import tkinter as tk

root = tk.Tk()
root.title("Jarvis UIA Fixture")
root.geometry("360x160")

entry = tk.Entry(root, name="jarvis_input")
entry.pack(padx=20, pady=10)

result = tk.Label(root, text="idle", name="jarvis_result")
result.pack(padx=20, pady=10)

def save():
    result.config(text="saved:" + entry.get())

button = tk.Button(root, text="Save", command=save, name="jarvis_save")
button.pack(padx=20, pady=10)

root.mainloop()
