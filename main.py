
import sqlite3
from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

DB_NAME = "tasks.db"

st.set_page_config(
    page_title="Task & Productivity Manager",
    page_icon="✅",
    layout="wide"
)


# ---------- DATABASE ----------

def get_connection():
    return sqlite3.connect(DB_NAME)


def initialize_database():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                priority TEXT NOT NULL,
                due_date TEXT NOT NULL,
                status TEXT NOT NULL
            )
        """)


def load_tasks():
    with get_connection() as conn:
        return pd.read_sql_query(
            "SELECT * FROM tasks ORDER BY id DESC",
            conn
        )


def add_task(title, category, priority, due_date):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO tasks
            (title, category, priority, due_date, status)
            VALUES (?, ?, ?, ?, 'Pending')
        """, (title, category, priority, str(due_date)))


def update_task(task_id, status):
    with get_connection() as conn:
        conn.execute(
            "UPDATE tasks SET status = ? WHERE id = ?",
            (status, task_id)
        )


def delete_task(task_id):
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM tasks WHERE id = ?",
            (task_id,)
        )


def edit_task(task_id, title, category, priority, due_date):
    with get_connection() as conn:
        conn.execute("""
            UPDATE tasks
            SET title = ?, category = ?,
                priority = ?, due_date = ?
            WHERE id = ?
        """, (title, category, priority, str(due_date), task_id))


initialize_database()


# ---------- DASHBOARD HEADER ----------

st.title("✅ Task & Productivity Manager")
st.caption("Plan your work. Track your progress. Achieve your goals.")

tasks = load_tasks()

if not tasks.empty:
    tasks["due_date"] = pd.to_datetime(tasks["due_date"]).dt.date
    today = date.today()

    total = len(tasks)
    completed = int((tasks["status"] == "Completed").sum())
    pending = int((tasks["status"] == "Pending").sum())
    overdue = int((
        (tasks["due_date"] < today) &
        (tasks["status"] != "Completed")
    ).sum())
else:
    total = completed = pending = overdue = 0


# ---------- STATISTICS ----------

c1, c2, c3, c4 = st.columns(4)

c1.metric("Total Tasks", total)
c2.metric("Completed", completed)
c3.metric("Pending", pending)
c4.metric("Overdue", overdue)

progress = completed / total if total else 0
st.progress(progress, text=f"Overall completion: {progress:.0%}")


# ---------- ADD TASK ----------

st.subheader("➕ Add a New Task")

with st.form("add_task_form", clear_on_submit=True):
    title = st.text_input("Task title")
    category = st.selectbox(
        "Category",
        ["Study", "Work", "Personal", "Project", "Other"]
    )
    priority = st.selectbox(
        "Priority",
        ["High", "Medium", "Low"]
    )
    due_date = st.date_input("Due date", value=date.today())

    submitted = st.form_submit_button("Add Task")

    if submitted:
        if title.strip():
            add_task(title.strip(), category, priority, due_date)
            st.success("Task added successfully!")
            st.rerun()
        else:
            st.error("Please enter a task title.")


# ---------- FILTERS ----------

st.subheader("📋 Manage Your Tasks")

f1, f2, f3 = st.columns(3)

search = f1.text_input("Search tasks")
status_filter = f2.selectbox(
    "Filter by status",
    ["All", "Pending", "In Progress", "Completed"]
)
priority_filter = f3.selectbox(
    "Filter by priority",
    ["All", "High", "Medium", "Low"]
)

tasks = load_tasks()

if not tasks.empty:
    if search:
        tasks = tasks[
            tasks["title"].str.contains(
                search, case=False, na=False
            )
        ]

    if status_filter != "All":
        tasks = tasks[tasks["status"] == status_filter]

    if priority_filter != "All":
        tasks = tasks[tasks["priority"] == priority_filter]

    for _, task in tasks.iterrows():
        with st.expander(
            f"#{task['id']} | {task['title']} "
            f"| {task['priority']} priority"
        ):
            st.write(f"Category: {task['category']}")
            st.write(f"Due date: {task['due_date']}")
            st.write(f"Current status: {task['status']}")

            new_status = st.selectbox(
                "Update status",
                ["Pending", "In Progress", "Completed"],
                index=[
                    "Pending", "In Progress", "Completed"
                ].index(task["status"]),
                key=f"status_{task['id']}"
            )

            if st.button("Save Status", key=f"save_{task['id']}"):
                update_task(int(task["id"]), new_status)
                st.rerun()

            with st.form(f"edit_{task['id']}"):
                new_title = st.text_input(
                    "Edit title",
                    value=task["title"]
                )
                new_category = st.selectbox(
                    "Edit category",
                    ["Study", "Work", "Personal", "Project", "Other"],
                    index=[
                        "Study", "Work", "Personal", "Project", "Other"
                    ].index(task["category"])
                )
                new_priority = st.selectbox(
                    "Edit priority",
                    ["High", "Medium", "Low"],
                    index=["High", "Medium", "Low"].index(
                        task["priority"]
                    )
                )
                new_due_date = st.date_input(
                    "Edit due date",
                    value=date.fromisoformat(str(task["due_date"]))
                )

                if st.form_submit_button("Save Task Changes"):
                    if new_title.strip():
                        edit_task(
                            int(task["id"]),
                            new_title.strip(),
                            new_category,
                            new_priority,
                            new_due_date
                        )
                        st.rerun()
                    else:
                        st.error("Task title cannot be empty.")

            if st.button("🗑️ Delete Task", key=f"delete_{task['id']}"):
                delete_task(int(task["id"]))
                st.rerun()
else:
    st.info("No tasks found. Add your first task above.")


# ---------- PRODUCTIVITY CHARTS ----------

st.subheader("📊 Productivity Analytics")

all_tasks = load_tasks()

if not all_tasks.empty:
    left, right = st.columns(2)

    with left:
        status_counts = (
            all_tasks["status"]
            .value_counts()
            .rename_axis("Status")
            .reset_index(name="Tasks")
        )

        fig = px.pie(
            status_counts,
            names="Status",
            values="Tasks",
            title="Tasks by Status",
            hole=0.4
        )
        st.plotly_chart(fig, width="stretch")

    with right:
        priority_counts = (
            all_tasks["priority"]
            .value_counts()
            .rename_axis("Priority")
            .reset_index(name="Tasks")
        )

        fig = px.bar(
            priority_counts,
            x="Priority",
            y="Tasks",
            title="Tasks by Priority"
        )
        st.plotly_chart(fig, width="stretch")
else:
    st.info("Add some tasks to see your productivity charts.")

st.divider()
st.caption("Task & Productivity Manager | Built with Python and Streamlit")
