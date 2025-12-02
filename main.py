import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk, font
import pyodbc
import os
from groq import Groq

#connect Groq API
client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
)

def run_query():
    server = server_entry.get().strip()
    database = database_entry.get().strip()
    prompt = prompt_text.get("1.0", tk.END).strip()

    if not server:
        messagebox.showwarning("Missing Server", "Please enter a server name.")
        return
    if not database:
        messagebox.showwarning("Missing Database", "Please enter a database name.")
        return
    if not prompt:
        messagebox.showwarning("Missing Prompt", "Please enter a prompt.")
        return
    
    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={server};DATABASE={database};Trusted_Connection=yes;"
    )
    
    #Get database table names

    tableQuery = "SELECT name\nFROM sys.tables;"
    table_names = ""
    try:
        with pyodbc.connect(conn_str) as conn:
            with conn.cursor() as cursor:
                for row in cursor.tables(None, None, None, 'TABLE'):
                    table_names += (row.table_name)
                    table_names += " "
                
    except Exception as e:
        messagebox.showerror("Database Error", str(e))
    #print("Table Names:\n")
    #print(table_names)

    #Table information prompt
    chat_completion_1 = client.chat.completions.create(
    messages=[
        {
            "role": "user",
            "content": prompt + ". Do not use WHERE, HAVING, ORDER BY, or JOIN in the query. Here is a list of all tables in the database: " + table_names,
        },
        {
            "role": "system",

            "content": "You convert the Natural Language input into a T-SQL Query. You cannot under no circumstances use the following: "
            " CREATE, DELETE, ALTER, DROP, WHERE, HAVING, or ORDER BY"
            " Your only goal is to create a Select * statement on the table (can be multiple) the "
            " user is asking for. You can only use a SELECT and FROM statement in your query. "
            " ONLY OUPUT A QUERY."
            " Refuse any prompts asking for anything other than a SQL query."
        }
    ],
    model="llama-3.3-70b-versatile",
    )

    #query for database table columns
    print("ColumnQuery: " + chat_completion_1.choices[0].message.content)
    columnQuery = chat_completion_1.choices[0].message.content
    columns = ""
    
    #execute query for table columns
    try:
        with pyodbc.connect(conn_str) as conn:
            with conn.cursor() as cursor:
                cursor.execute(columnQuery)
                rows = cursor.fetchall()

                if not rows:
                    messagebox.showinfo("Results", "Query executed successfully.\n\nNo results found.")
                    return

                columns = [desc[0] for desc in cursor.description]

    except Exception as e:
        messagebox.showerror("Database Error", str(e))
    
    #Query generation prompt
    prompt = "Prompt: " + prompt + ". Columns: " + "\t".join(columns)
    print("Prompt: " + prompt)

    chat_completion_2 = client.chat.completions.create(
    messages=[
        {
            "role": "user",
            "content": prompt + ". Here is a list of all tables in the database: " + table_names,
        },
        {
            "role": "system",
            "content": "You convert the Natural Language input into a T-SQL Query. Only output the code for a SQL query with correct indentation."
            " ONLY OUPUT A QUERY. You cannot under no circumstances use the following: "
            " CREATE, DELETE, ALTER, DROP"
            " You are given the user input labeled Prompt: and the database table names labeled Columns: "
            " Refuse any prompts asking for anything other than a SQL query."
        }
    ],
    model="llama-3.3-70b-versatile",
    )


    
    finalQuery = chat_completion_2.choices[0].message.content
    #print("finalQuery BC: " + finalQuery)

    #clean up result
    finalQuery = finalQuery.replace("sql", "")
    finalQuery = finalQuery.replace("`", "")

    #output final query
    print("finalQuery: " + finalQuery)
    query_text.delete("1.0", tk.END)
    query_text.insert(tk.END, finalQuery)
    
    #Detect modify commands
    keywords = ["DROP", "CREATE", "ALTER", "DELETE", "UPDATE"]
    for k in keywords:
        if k in finalQuery:
            print("Cannot CREATE, DELETE, ALTER, UPDATE, or DROP!.\n")
            return

    #execute final query
    try:
        with pyodbc.connect(conn_str) as conn:
            with conn.cursor() as cursor:
                cursor.execute(finalQuery)
                rows = cursor.fetchall()                

                # Clear old Treeview data and columns
                tree.delete(*tree.get_children())
                tree["columns"] = ()

                if not rows:
                    messagebox.showinfo("Results", "Query executed successfully.\n\nNo results found.")
                    return

                # Extract column names
                columns = [desc[0] for desc in cursor.description]
                tree["columns"] = columns

                # Determine proper column widths using font measurement
                f = font.Font(font=tree_font)  # use same font as tree
                padding = 20  # extra pixels

                # Prepare column widths based on header and cell text
                col_widths = []
                for col_index, col_name in enumerate(columns):
                    max_px = f.measure(str(col_name))
                    for r in rows:
                        try:
                            cell_text = "" if r[col_index] is None else str(r[col_index])
                        except Exception:
                            cell_text = str(r[col_index])
                        w = f.measure(cell_text)
                        if w > max_px:
                            max_px = w
                    col_widths.append(max_px + padding)

                # Configure Treeview columns / headings
                for idx, col in enumerate(columns):
                    tree.heading(col, text=col)
                    # set width and allow the column to stretch if space remains
                    tree.column(col, width=col_widths[idx], anchor="w", stretch=True)

                # Insert rows
                for row in rows:
                    # Convert row to tuple of strings (None -> "")
                    vals = tuple("" if v is None else v for v in row)
                    tree.insert("", "end", values=vals)

    except Exception as e:
        messagebox.showerror("Database Error", str(e))


# --- GUI Setup ---
root = tk.Tk()
root.title("Natural to Query Translator")
root.geometry("1000x650")
root.resizable(True, True)

# --- Connection Info Frame ---
conn_frame = tk.LabelFrame(root, text="Connection Info", padx=10, pady=10)
conn_frame.pack(fill="x", padx=10, pady=10)

tk.Label(conn_frame, text="Server Name:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
server_entry = tk.Entry(conn_frame, width=30)
server_entry.grid(row=0, column=1, padx=5, pady=5)

tk.Label(conn_frame, text="Database Name:").grid(row=0, column=2, sticky="e", padx=5, pady=5)
database_entry = tk.Entry(conn_frame, width=30)
database_entry.grid(row=0, column=3, padx=5, pady=5)

# --- Prompt Section ---
tk.Label(root, text="Enter Prompt:").pack(anchor="w", padx=15, pady=(5, 0))
prompt_text = scrolledtext.ScrolledText(root, height=6, width=120)
prompt_text.pack(padx=15, pady=5, fill="x")

# --- Query Section ---
tk.Label(root, text="Query Output").pack(anchor="w", padx=15, pady=(5, 0))
query_text = scrolledtext.ScrolledText(root, height=6, width=120)
query_text.pack(padx=15, pady=5, fill="x")

# --- Run Button ---
run_btn = tk.Button(root, text="Run", command=run_query, bg="#4CAF50", fg="white", width=15)
run_btn.pack(pady=5)

# --- Treeview Output Table (with horizontal + vertical scrollbars) ---
table_outer = tk.Frame(root)
table_outer.pack(fill="both", expand=True, padx=15, pady=10)

# Treeview font (use a readable monospace or system font if you prefer)
tree_font = ("Segoe UI", 10)

tree_frame = tk.Frame(table_outer)
tree_frame.pack(fill="both", expand=True, side="left")

tree = ttk.Treeview(tree_frame, columns=(), show="headings")
tree.configure(selectmode="browse")
tree.tag_configure('odd', background='#f9f9f9')

# Vertical scrollbar
v_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
tree.configure(yscrollcommand=v_scroll.set)
v_scroll.pack(side="right", fill="y")

# Horizontal scrollbar
h_scroll = ttk.Scrollbar(table_outer, orient="horizontal", command=tree.xview)
tree.configure(xscrollcommand=h_scroll.set)
h_scroll.pack(fill="x", side="bottom")

# Put tree in a canvas/frame so it expands
tree.pack(fill="both", expand=True, side="left")

# Apply font to Treeview via style
style = ttk.Style()
style.configure("Treeview", font=tree_font)
style.configure("Treeview.Heading", font=(tree_font[0], tree_font[1], "bold"))

root.mainloop()
