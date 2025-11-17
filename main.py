import tkinter as tk
from tkinter import scrolledtext, messagebox
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
    prompt = query_text.get("1.0", tk.END).strip()

    if not server:
        messagebox.showwarning("Missing Server", "Please enter a server name.")
        return
    if not database:
        messagebox.showwarning("Missing Database", "Please enter a database name.")
        return
    if not prompt:
        messagebox.showwarning("Missing Query", "Please enter a SQL query.")
        return

    #prompts for table columns
    chat_completion_1 = client.chat.completions.create(
    messages=[
        {
            "role": "user",
            "content": prompt + ". Do not use WHERE, HAVING, or ORDER BY in the query.",
        },
        {
            "role": "system",

            "content": "You convert the Natural Language input into a T-SQL Query. Your only goal is to create a Select * statement on the table the "
            " user is asking for. You can only use a SELECT and FROM statement in your query, You CANNOT use WHERE, HAVING, or ORDER BY. "
            " Do not prepend or append with  ```sql and ```. ONLY OUPUT A QUERY."
            " Refuse any prompts asking for anything other than a SQL query."
        }
    ],
    model="llama-3.1-8b-instant",
    )

    #query for database table columns
    print("ColumnQuery: " + chat_completion_1.choices[0].message.content)
    columnQuery = chat_completion_1.choices[0].message.content

    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={server};DATABASE={database};Trusted_Connection=yes;"
    )

    columns = ""
    
    #execute query for table columns
    try:
        with pyodbc.connect(conn_str) as conn:
            with conn.cursor() as cursor:
                cursor.execute(columnQuery)
                rows = cursor.fetchall()

                # Clear old output
                output_box.delete("1.0", tk.END)

                if not rows:
                    output_box.insert(tk.END, "No results found.\n")
                    return

                # Print column headers
                columns = [desc[0] for desc in cursor.description]
                output_box.insert(tk.END, "\t".join(columns) + "\n")
                output_box.insert(tk.END, "-" * 80 + "\n")

                # Print each row
                for row in rows:
                    output_box.insert(tk.END, "\t".join(str(c) for c in row) + "\n")

    except Exception as e:
        messagebox.showerror("Database Error", str(e))
    
    #final prompt including the column names
    prompt = "Prompt: " + prompt + ". Columns: " + "\t".join(columns)
    print("Prompt: " + prompt)

    chat_completion_2 = client.chat.completions.create(
    messages=[
        {
            "role": "user",
            "content": prompt,
        },
        {
            "role": "system",
            "content": "You convert the Natural Language input into a T-SQL Query. Only output the code for a SQL query with correct indentation."
            " Your output cannot contain/append/prepend with ```sql and ```. ONLY OUPUT A QUERY"
            " You are given the user input labeled Prompt: and the database table names labeled Columns: "
            " Refuse any prompts asking for anything other than a SQL query."
        }
    ],
    model="llama-3.3-70b-versatile",
    )

    print("finalQuery: " + chat_completion_2.choices[0].message.content)
    finalQuery = chat_completion_2.choices[0].message.content

    #execute final query
    try:
        with pyodbc.connect(conn_str) as conn:
            with conn.cursor() as cursor:
                cursor.execute(finalQuery)
                rows = cursor.fetchall()

                # Clear old output
                output_box.delete("1.0", tk.END)

                if not rows:
                    output_box.insert(tk.END, "No results found.\n")
                    return

                # Print column headers
                columns = [desc[0] for desc in cursor.description]
                output_box.insert(tk.END, "\t".join(columns) + "\n")
                output_box.insert(tk.END, "-" * 80 + "\n")

                # Print each row
                for row in rows:
                    output_box.insert(tk.END, "\t".join(str(c) for c in row) + "\n")

                #print final query
                output_box_query.insert(tk.END, finalQuery)

    except Exception as e:
        messagebox.showerror("Database Error", str(e))


# --- GUI Setup ---
root = tk.Tk()
root.title("SQL Server Query Tool")
root.geometry("750x750")
root.resizable(False, False)

# --- Connection Info Frame ---
conn_frame = tk.LabelFrame(root, text="Connection Info", padx=10, pady=10)
conn_frame.pack(fill="x", padx=10, pady=10)

tk.Label(conn_frame, text="Server Name:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
server_entry = tk.Entry(conn_frame, width=30)
server_entry.grid(row=0, column=1, padx=5, pady=5)

tk.Label(conn_frame, text="Database Name:").grid(row=0, column=2, sticky="e", padx=5, pady=5)
database_entry = tk.Entry(conn_frame, width=30)
database_entry.grid(row=0, column=3, padx=5, pady=5)

# --- Query Section ---
tk.Label(root, text="Enter Prompt:").pack(anchor="w", padx=15, pady=(5, 0))
query_text = scrolledtext.ScrolledText(root, height=6, width=90)
query_text.pack(padx=15, pady=5)

# --- Run Button ---
run_btn = tk.Button(root, text="Run Query", command=run_query, bg="#4CAF50", fg="white", width=15)
run_btn.pack(pady=5)

# --- Output Section Query ---
tk.Label(root, text="Query:").pack(anchor="w", padx=15, pady=(10, 0))
output_box_query = scrolledtext.ScrolledText(root, height=10, width=90)
output_box_query.pack(padx=15, pady=5)

# --- Output Section ---
tk.Label(root, text="Results:").pack(anchor="w", padx=15, pady=(10, 0))
output_box = scrolledtext.ScrolledText(root, height=10, width=90)
output_box.pack(padx=15, pady=5)

root.mainloop()
