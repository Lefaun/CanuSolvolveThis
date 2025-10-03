import streamlit as st
import pandas as pd
import datetime
import json
from datetime import datetime, timedelta
import hashlib
import sqlite3
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import re
import time
from datetime import datetime
import json

# Initialize database
def init_db():
    conn = sqlite3.connect('problem_solving.db')
    c = conn.cursor()
    
    # Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Problems table
    c.execute('''
        CREATE TABLE IF NOT EXISTS problems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            priority TEXT NOT NULL,
            status TEXT DEFAULT 'submitted',
            submitted_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deadline TIMESTAMP,
            FOREIGN KEY (submitted_by) REFERENCES users (id)
        )
    ''')
    
    # Assignments table
    c.execute('''
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            problem_id INTEGER,
            user_id INTEGER,
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'assigned',
            FOREIGN KEY (problem_id) REFERENCES problems (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Calendar events table
    c.execute('''
        CREATE TABLE IF NOT EXISTS calendar_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            problem_id INTEGER,
            title TEXT NOT NULL,
            description TEXT,
            event_date TIMESTAMP NOT NULL,
            created_by INTEGER,
            FOREIGN KEY (problem_id) REFERENCES problems (id),
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Hash password
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# User authentication
def authenticate_user(email, password):
    conn = sqlite3.connect('problem_solving.db')
    c = conn.cursor()
    hashed_password = hash_password(password)
    
    c.execute('SELECT * FROM users WHERE email = ? AND password = ?', 
              (email, hashed_password))
    user = c.fetchone()
    conn.close()
    
    if user:
        return {
            'id': user[0],
            'email': user[1],
            'name': user[3],
            'role': user[4]
        }
    return None

# Register new user
def register_user(email, password, name, role='user'):
    conn = sqlite3.connect('problem_solving.db')
    c = conn.cursor()
    hashed_password = hash_password(password)
    
    try:
        c.execute('INSERT INTO users (email, password, name, role) VALUES (?, ?, ?, ?)',
                  (email, hashed_password, name, role))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

# Problem submission
def submit_problem(title, description, category, priority, submitted_by, deadline_days=30):
    conn = sqlite3.connect('problem_solving.db')
    c = conn.cursor()
    deadline = datetime.now() + timedelta(days=deadline_days)
    
    c.execute('''
        INSERT INTO problems (title, description, category, priority, submitted_by, deadline)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (title, description, category, priority, submitted_by, deadline))
    
    problem_id = c.lastrowid
    conn.commit()
    conn.close()
    return problem_id

# Get all problems
def get_all_problems():
    conn = sqlite3.connect('problem_solving.db')
    c = conn.cursor()
    
    c.execute('''
        SELECT p.*, u.name as submitted_by_name 
        FROM problems p 
        LEFT JOIN users u ON p.submitted_by = u.id 
        ORDER BY p.created_at DESC
    ''')
    problems = c.fetchall()
    conn.close()
    
    return problems

# Get user's submitted problems
def get_user_problems(user_id):
    conn = sqlite3.connect('problem_solving.db')
    c = conn.cursor()
    
    c.execute('''
        SELECT p.*, u.name as submitted_by_name 
        FROM problems p 
        LEFT JOIN users u ON p.submitted_by = u.id 
        WHERE p.submitted_by = ?
        ORDER BY p.created_at DESC
    ''', (user_id,))
    problems = c.fetchall()
    conn.close()
    
    return problems

# Assign user to problem
def assign_to_problem(problem_id, user_id):
    conn = sqlite3.connect('problem_solving.db')
    c = conn.cursor()
    
    # Check if already assigned
    c.execute('SELECT * FROM assignments WHERE problem_id = ? AND user_id = ?', 
              (problem_id, user_id))
    existing = c.fetchone()
    
    if not existing:
        c.execute('INSERT INTO assignments (problem_id, user_id) VALUES (?, ?)', 
                  (problem_id, user_id))
        conn.commit()
    
    conn.close()
    return not existing

# Get assignments for problem
def get_problem_assignments(problem_id):
    conn = sqlite3.connect('problem_solving.db')
    c = conn.cursor()
    
    c.execute('''
        SELECT a.*, u.name as user_name 
        FROM assignments a 
        JOIN users u ON a.user_id = u.id 
        WHERE a.problem_id = ?
    ''', (problem_id,))
    assignments = c.fetchall()
    conn.close()
    
    return assignments

# Add calendar event
def add_calendar_event(problem_id, title, description, event_date, created_by):
    conn = sqlite3.connect('problem_solving.db')
    c = conn.cursor()
    
    c.execute('''
        INSERT INTO calendar_events (problem_id, title, description, event_date, created_by)
        VALUES (?, ?, ?, ?, ?)
    ''', (problem_id, title, description, event_date, created_by))
    
    conn.commit()
    conn.close()

# Get calendar events
def get_calendar_events(user_id=None):
    conn = sqlite3.connect('problem_solving.db')
    c = conn.cursor()
    
    if user_id:
        c.execute('''
            SELECT ce.*, p.title as problem_title, u.name as created_by_name
            FROM calendar_events ce
            JOIN problems p ON ce.problem_id = p.id
            JOIN users u ON ce.created_by = u.id
            WHERE ce.created_by = ? OR ce.problem_id IN (
                SELECT problem_id FROM assignments WHERE user_id = ?
            )
            ORDER BY ce.event_date
        ''', (user_id, user_id))
    else:
        c.execute('''
            SELECT ce.*, p.title as problem_title, u.name as created_by_name
            FROM calendar_events ce
            JOIN problems p ON ce.problem_id = p.id
            JOIN users u ON ce.created_by = u.id
            ORDER BY ce.event_date
        ''')
    
    events = c.fetchall()
    conn.close()
    return events

# Priority mapping for sorting
PRIORITY_ORDER = {'Critical': 1, 'High': 2, 'Medium': 3, 'Low': 4}

def main():
    st.set_page_config(page_title="Problem Solving Platform", page_icon="🔧", layout="wide")
    
    # Initialize database
    init_db()
    
    # Sidebar for navigation
    st.sidebar.title("🔧 Problem Solving Platform")
    st.sidebar.markdown("---")
    
    # Session state for authentication
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'page' not in st.session_state:
        st.session_state.page = "Home"
    
    # Authentication section
    if st.session_state.user is None:
        auth_option = st.sidebar.selectbox("Select Option", ["Login", "Register"])
        
        if auth_option == "Login":
            st.sidebar.subheader("Login")
            login_email = st.sidebar.text_input("Email")
            login_password = st.sidebar.text_input("Password", type="password")
            
            if st.sidebar.button("Login"):
                user = authenticate_user(login_email, login_password)
                if user:
                    st.session_state.user = user
                    st.sidebar.success(f"Welcome {user['name']}!")
                    st.rerun()
                else:
                    st.sidebar.error("Invalid credentials")
        
        else:  # Register
            st.sidebar.subheader("Register")
            reg_name = st.sidebar.text_input("Full Name")
            reg_email = st.sidebar.text_input("Email")
            reg_password = st.sidebar.text_input("Password", type="password")
            
            if st.sidebar.button("Register"):
                if register_user(reg_email, reg_password, reg_name):
                    st.sidebar.success("Registration successful! Please login.")
                else:
                    st.sidebar.error("Email already exists!")
        
        # Show main content for non-authenticated users
        st.title("🔧 Problem Solving Platform")
        st.markdown("""
        ### Welcome to the Collaborative Problem Solving Platform!
        
        This platform allows users to:
        - 📝 Submit problem-solving questions with priority levels
        - 🏷️ Categorize problems using tags
        - 👥 Assign problems to solvers
        - 📅 Track deadlines and progress
        - 🔔 Get notifications for assignments
        
        **Please login or register to get started!**
        """)
        
        # Show recent problems (read-only for non-logged in users)
        st.subheader("📋 Recently Submitted Problems")
        problems = get_all_problems()
        if problems:
            problem_data = []
            for problem in problems:
                problem_data.append({
                    'ID': problem[0],
                    'Title': problem[1],
                    'Category': problem[3],
                    'Priority': problem[4],
                    'Status': problem[5],
                    'Submitted By': problem[8],
                    'Deadline': problem[9]
                })
            
            df = pd.DataFrame(problem_data)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No problems submitted yet.")
            
        st.markdown("---")
        st.markdown("**Credits:** Developed by Paulo Monteiro")
        return
    
    # User is authenticated - show full application
    user = st.session_state.user
    
    # Navigation for authenticated users
    if user['role'] == 'admin':
        pages = ["Home", "Submit Problem", "My Problems", "All Problems", "Calendar", "Admin Panel"]
    else:
        pages = ["Home", "Submit Problem", "My Problems", "Available Problems", "Calendar"]
    
    st.session_state.page = st.sidebar.selectbox("Navigation", pages, index=pages.index(st.session_state.page))
    
    st.sidebar.markdown("---")
    st.sidebar.write(f"👤 Welcome, {user['name']} ({user['role']})")
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.session_state.page = "Home"
        st.rerun()
    
    # Page routing
    if st.session_state.page == "Home":
        show_home_page(user)
    elif st.session_state.page == "Submit Problem":
        show_submit_problem(user)
    elif st.session_state.page == "My Problems":
        show_my_problems(user)
    elif st.session_state.page == "Available Problems":
        show_available_problems(user)
    elif st.session_state.page == "All Problems":
        show_all_problems(user)
    elif st.session_state.page == "Calendar":
        show_calendar(user)
    elif st.session_state.page == "Admin Panel":
        show_admin_panel(user)

def show_home_page(user):
    st.title("🏠 Dashboard")
    
    col1, col2, col3 = st.columns(3)
    
    # Statistics
    problems = get_all_problems()
    user_problems = get_user_problems(user['id'])
    assignments = len([p for p in problems if any(a[2] == user['id'] for a in get_problem_assignments(p[0]))])
    
    with col1:
        st.metric("Total Problems", len(problems))
    with col2:
        st.metric("My Submitted Problems", len(user_problems))
    with col3:
        st.metric("My Assignments", assignments)
    
    st.markdown("---")
    
    # Recent activity
    st.subheader("📈 Recent Activity")
    
    # Recent problems
    recent_problems = problems[:5]  # Show last 5 problems
    if recent_problems:
        st.write("**Recently Submitted Problems:**")
        for problem in recent_problems:
            with st.expander(f"{problem[1]} - {problem[4]} Priority"):
                st.write(f"**Category:** {problem[3]}")
                st.write(f"**Status:** {problem[5]}")
                st.write(f"**Submitted by:** {problem[8]}")
                st.write(f"**Deadline:** {problem[9]}")
                st.write(f"**Description:** {problem[2]}")
    else:
        st.info("No problems submitted yet.")

def show_submit_problem(user):
    st.title("📝 Submit New Problem")
    
    with st.form("problem_form"):
        title = st.text_input("Problem Title*")
        description = st.text_area("Problem Description*", height=150)
        
        col1, col2 = st.columns(2)
        with col1:
            category = st.selectbox("Category*", [
                "Technical", "Research", "Business", 
                "Academic", "Software", "Hardware",
                "Data Analysis", "Algorithm", "Other"
            ])
        with col2:
            priority = st.selectbox("Priority*", ["Low", "Medium", "High", "Critical"])
        
        deadline_days = st.slider("Deadline (days from now)", 1, 90, 30)
        
        submitted = st.form_submit_button("Submit Problem")
        
        if submitted:
            if title and description:
                problem_id = submit_problem(title, description, category, priority, user['id'], deadline_days)
                st.success(f"Problem submitted successfully! ID: {problem_id}")
                
                # Add initial calendar event for deadline
                deadline_date = datetime.now() + timedelta(days=deadline_days)
                add_calendar_event(
                    problem_id, 
                    f"Deadline: {title}", 
                    f"Final deadline for solving: {description}",
                    deadline_date,
                    user['id']
                )
            else:
                st.error("Please fill in all required fields!")

def show_my_problems(user):
    st.title("📋 My Submitted Problems")
    
    problems = get_user_problems(user['id'])
    
    if not problems:
        st.info("You haven't submitted any problems yet.")
        return
    
    for problem in problems:
        with st.expander(f"#{problem[0]} - {problem[1]} [{problem[4]}] - {problem[5]}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Category:** {problem[3]}")
                st.write(f"**Priority:** {problem[4]}")
                st.write(f"**Status:** {problem[5]}")
                st.write(f"**Submitted:** {problem[7]}")
                st.write(f"**Deadline:** {problem[9]}")
            
            with col2:
                st.write("**Description:**")
                st.write(problem[2])
                
                # Show assignments for this problem
                assignments = get_problem_assignments(problem[0])
                if assignments:
                    st.write("**Assigned Solvers:**")
                    for assignment in assignments:
                        st.write(f"- {assignment[4]} (Assigned: {assignment[3]})")
                else:
                    st.write("**No assignments yet**")
            
            # Add calendar event for this problem
            st.subheader("Add Calendar Event")
            with st.form(f"event_form_{problem[0]}"):
                event_title = st.text_input("Event Title", value=f"Meeting: {problem[1]}")
                event_desc = st.text_area("Event Description")
                event_date = st.date_input("Event Date", min_value=datetime.now().date())
                event_time = st.time_input("Event Time", datetime.now().time())
                
                if st.form_submit_button("Add to Calendar"):
                    event_datetime = datetime.combine(event_date, event_time)
                    add_calendar_event(problem[0], event_title, event_desc, event_datetime, user['id'])
                    st.success("Event added to calendar!")

def show_available_problems(user):
    st.title("🔍 Available Problems for Solving")
    
    problems = get_all_problems()
    user_assignments = set()
    all_assignments = []
    for problem in problems:
        assignments = get_problem_assignments(problem[0])
        all_assignments.extend(assignments)
        for assignment in assignments:
            if assignment[2] == user['id']:
                user_assignments.add(problem[0])
    
    # Filter problems that are not assigned to current user and are still open
    available_problems = [p for p in problems if p[0] not in user_assignments and p[5] in ['submitted', 'in progress']]
    
    if not available_problems:
        st.info("No available problems at the moment.")
        return
    
    # Sort by priority
    available_problems.sort(key=lambda x: PRIORITY_ORDER.get(x[4], 5))
    
    for problem in available_problems:
        with st.expander(f"#{problem[0]} - {problem[1]} [{problem[4]}] - {problem[5]}"):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(f"**Category:** {problem[3]}")
                st.write(f"**Priority:** {problem[4]}")
                st.write(f"**Status:** {problem[5]}")
                st.write(f"**Submitted by:** {problem[8]}")
                st.write(f"**Deadline:** {problem[9]}")
                st.write("**Description:**")
                st.write(problem[2])
                
                # Show current assignments
                assignments = get_problem_assignments(problem[0])
                if assignments:
                    st.write("**Currently assigned to:**")
                    for assignment in assignments:
                        st.write(f"- {assignment[4]}")
            
            with col2:
                if st.button(f"Assign to Me", key=f"assign_{problem[0]}"):
                    if assign_to_problem(problem[0], user['id']):
                        st.success("Successfully assigned to you!")
                        st.rerun()
                    else:
                        st.error("Already assigned to you!")

def show_all_problems(user):
    if user['role'] != 'admin':
        st.error("Access denied. Admin privileges required.")
        return
    
    st.title("📊 All Problems (Admin View)")
    
    problems = get_all_problems()
    
    if not problems:
        st.info("No problems submitted yet.")
        return
    
    # Create DataFrame for better display
    problem_data = []
    for problem in problems:
        assignments = get_problem_assignments(problem[0])
        assigned_to = ", ".join([a[4] for a in assignments]) if assignments else "None"
        
        problem_data.append({
            'ID': problem[0],
            'Title': problem[1],
            'Category': problem[3],
            'Priority': problem[4],
            'Status': problem[5],
            'Submitted By': problem[8],
            'Assigned To': assigned_to,
            'Deadline': problem[9],
            'Created': problem[7]
        })
    
    df = pd.DataFrame(problem_data)
    st.dataframe(df, use_container_width=True)
    
    # Problem management
    st.subheader("Problem Management")
    problem_ids = [p[0] for p in problems]
    selected_problem = st.selectbox("Select Problem to Manage", problem_ids, 
                                   format_func=lambda x: f"#{x} - {next(p[1] for p in problems if p[0] == x)}")
    
    if selected_problem:
        problem = next(p for p in problems if p[0] == selected_problem)
        col1, col2 = st.columns(2)
        
        with col1:
            new_status = st.selectbox("Update Status", 
                                    ["submitted", "in progress", "solved", "closed"],
                                    index=["submitted", "in progress", "solved", "closed"].index(problem[5]))
            
            if st.button("Update Status"):
                conn = sqlite3.connect('problem_solving.db')
                c = conn.cursor()
                c.execute('UPDATE problems SET status = ? WHERE id = ?', (new_status, selected_problem))
                conn.commit()
                conn.close()
                st.success("Status updated!")
                st.rerun()
        
        with col2:
            st.write("**Current Assignments:**")
            assignments = get_problem_assignments(selected_problem)
            if assignments:
                for assignment in assignments:
                    st.write(f"- {assignment[4]}")
            else:
                st.write("No assignments")

def show_calendar(user):
    st.title("📅 Calendar")
    
    # Get events based on user role
    if user['role'] == 'admin':
        events = get_calendar_events()
    else:
        events = get_calendar_events(user['id'])
    
    if not events:
        st.info("No calendar events found.")
        return
    
    # Group events by date
    events_by_date = {}
    for event in events:
        event_date = datetime.strptime(event[4], '%Y-%m-%d %H:%M:%S').date()
        if event_date not in events_by_date:
            events_by_date[event_date] = []
        events_by_date[event_date].append(event)
    
    # Display events chronologically
    for date in sorted(events_by_date.keys()):
        st.subheader(f"📅 {date.strftime('%A, %B %d, %Y')}")
        
        for event in events_by_date[date]:
            with st.expander(f"⏰ {event[1]} - {event[4][11:16]}"):
                st.write(f"**Problem:** {event[6]}")
                st.write(f"**Description:** {event[2]}")
                st.write(f"**Created by:** {event[7]}")

def show_admin_panel(user):
    if user['role'] != 'admin':
        st.error("Access denied. Admin privileges required.")
        return
    
    st.title("⚙️ Admin Panel")
    
    tab1, tab2, tab3 = st.tabs(["User Management", "System Statistics", "Database Management"])
    
    with tab1:
        st.subheader("User Management")
        conn = sqlite3.connect('problem_solving.db')
        c = conn.cursor()
        c.execute('SELECT id, name, email, role, created_at FROM users')
        users = c.fetchall()
        conn.close()
        
        if users:
            user_data = []
            for user in users:
                user_data.append({
                    'ID': user[0],
                    'Name': user[1],
                    'Email': user[2],
                    'Role': user[3],
                    'Created': user[4]
                })
            
            df = pd.DataFrame(user_data)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No users found.")
    
    with tab2:
        st.subheader("System Statistics")
        
        problems = get_all_problems()
        users = len([u for u in get_all_problems()])  # This needs proper user count
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Problems", len(problems))
        with col2:
            st.metric("Submitted Status", len([p for p in problems if p[5] == 'submitted']))
        with col3:
            st.metric("In Progress", len([p for p in problems if p[5] == 'in progress']))
        with col4:
            st.metric("Solved", len([p for p in problems if p[5] == 'solved']))
        
        # Priority distribution
        st.subheader("Priority Distribution")
        priority_counts = {}
        for problem in problems:
            priority = problem[4]
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
        
        if priority_counts:
            priority_df = pd.DataFrame(list(priority_counts.items()), columns=['Priority', 'Count'])
            st.bar_chart(priority_df.set_index('Priority'))
    
    with tab3:
        st.subheader("Database Management")
        
        if st.button("Export Data to CSV"):
            # Export problems
            problems = get_all_problems()
            if problems:
                problem_data = []
                for problem in problems:
                    problem_data.append({
                        'ID': problem[0],
                        'Title': problem[1],
                        'Description': problem[2],
                        'Category': problem[3],
                        'Priority': problem[4],
                        'Status': problem[5],
                        'Submitted_By': problem[8],
                        'Created_At': problem[7],
                        'Deadline': problem[9]
                    })
                
                problems_df = pd.DataFrame(problem_data)
                st.download_button(
                    label="Download Problems CSV",
                    data=problems_df.to_csv(index=False),
                    file_name="problems_export.csv",
                    mime="text/csv"
                )

# Add credits footer
st.markdown("---")
st.markdown("**Credits:** Problem Solving Platform developed by Paulo Monteiro")

if __name__ == "__main__":
    main()
