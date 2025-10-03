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
import io
import base64

# New imports for enhanced features
from docx import Document
import PyPDF2
import fitz  # PyMuPDF - alternative PDF library
from duckduckgo_search import DDGS
import google.generativeai as genai
import os

# Initialize database with enhanced tables
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
    
    # Enhanced Problems table (now tickets)
    c.execute('''
        CREATE TABLE IF NOT EXISTS problems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            priority TEXT NOT NULL,
            status TEXT DEFAULT 'submitted',
            submitted_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deadline TIMESTAMP,
            assigned_to INTEGER,
            resolution TEXT,
            resolved_at TIMESTAMP,
            FOREIGN KEY (submitted_by) REFERENCES users (id),
            FOREIGN KEY (assigned_to) REFERENCES users (id)
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
    
    # File attachments table
    c.execute('''
        CREATE TABLE IF NOT EXISTS file_attachments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            problem_id INTEGER,
            filename TEXT NOT NULL,
            file_data BLOB NOT NULL,
            file_type TEXT NOT NULL,
            uploaded_by INTEGER,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (problem_id) REFERENCES problems (id),
            FOREIGN KEY (uploaded_by) REFERENCES users (id)
        )
    ''')
    
    # Search results table
    c.execute('''
        CREATE TABLE IF NOT EXISTS search_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            problem_id INTEGER,
            search_query TEXT NOT NULL,
            result_title TEXT,
            result_url TEXT,
            result_snippet TEXT,
            search_engine TEXT,
            searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (problem_id) REFERENCES problems (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Generate unique ticket ID
def generate_ticket_id():
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    import random
    random_str = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=4))
    return f"TKT-{timestamp}-{random_str}"

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

# Enhanced problem submission with ticket ID
def submit_problem(title, description, category, priority, submitted_by, deadline_days=30):
    conn = sqlite3.connect('problem_solving.db')
    c = conn.cursor()
    deadline = datetime.now() + timedelta(days=deadline_days)
    ticket_id = generate_ticket_id()
    
    c.execute('''
        INSERT INTO problems (ticket_id, title, description, category, priority, submitted_by, deadline)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (ticket_id, title, description, category, priority, submitted_by, deadline))
    
    problem_id = c.lastrowid
    conn.commit()
    conn.close()
    return problem_id, ticket_id

# Get all problems
def get_all_problems():
    conn = sqlite3.connect('problem_solving.db')
    c = conn.cursor()
    
    c.execute('''
        SELECT p.*, u.name as submitted_by_name, u2.name as assigned_to_name
        FROM problems p 
        LEFT JOIN users u ON p.submitted_by = u.id 
        LEFT JOIN users u2 ON p.assigned_to = u2.id
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
        SELECT p.*, u.name as submitted_by_name, u2.name as assigned_to_name
        FROM problems p 
        LEFT JOIN users u ON p.submitted_by = u.id 
        LEFT JOIN users u2 ON p.assigned_to = u2.id
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
    
    # Update the main problem assignment
    c.execute('UPDATE problems SET assigned_to = ? WHERE id = ?', (user_id, problem_id))
    
    # Check if already assigned in assignments table
    c.execute('SELECT * FROM assignments WHERE problem_id = ? AND user_id = ?', 
              (problem_id, user_id))
    existing = c.fetchone()
    
    if not existing:
        c.execute('INSERT INTO assignments (problem_id, user_id) VALUES (?, ?)', 
                  (problem_id, user_id))
    
    conn.commit()
    conn.close()
    return True

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

# File attachment functions
def save_file_attachment(problem_id, filename, file_data, file_type, uploaded_by):
    conn = sqlite3.connect('problem_solving.db')
    c = conn.cursor()
    
    c.execute('''
        INSERT INTO file_attachments (problem_id, filename, file_data, file_type, uploaded_by)
        VALUES (?, ?, ?, ?, ?)
    ''', (problem_id, filename, file_data, file_type, uploaded_by))
    
    conn.commit()
    conn.close()

def get_file_attachments(problem_id):
    conn = sqlite3.connect('problem_solving.db')
    c = conn.cursor()
    
    c.execute('''
        SELECT fa.*, u.name as uploaded_by_name
        FROM file_attachments fa
        JOIN users u ON fa.uploaded_by = u.id
        WHERE fa.problem_id = ?
        ORDER BY fa.uploaded_at DESC
    ''', (problem_id,))
    
    attachments = c.fetchall()
    conn.close()
    return attachments

def get_file_attachment(file_id):
    conn = sqlite3.connect('problem_solving.db')
    c = conn.cursor()
    
    c.execute('SELECT * FROM file_attachments WHERE id = ?', (file_id,))
    attachment = c.fetchone()
    conn.close()
    return attachment

# Search functions
def save_search_result(problem_id, search_query, result_title, result_url, result_snippet, search_engine):
    conn = sqlite3.connect('problem_solving.db')
    c = conn.cursor()
    
    c.execute('''
        INSERT INTO search_results (problem_id, search_query, result_title, result_url, result_snippet, search_engine)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (problem_id, search_query, result_title, result_url, result_snippet, search_engine))
    
    conn.commit()
    conn.close()

def get_search_results(problem_id):
    conn = sqlite3.connect('problem_solving.db')
    c = conn.cursor()
    
    c.execute('''
        SELECT * FROM search_results 
        WHERE problem_id = ? 
        ORDER BY searched_at DESC
    ''', (problem_id,))
    
    results = c.fetchall()
    conn.close()
    return results

# Web search functionality
def search_web(query, max_results=5):
    """Search using DuckDuckGo"""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            return results
    except Exception as e:
        st.error(f"Search error: {e}")
        return []

def search_with_beautiful_soup(url):
    """Extract content from a URL using BeautifulSoup"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract relevant content
        title = soup.title.string if soup.title else "No title"
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text content
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return {
            'title': title,
            'content': text[:1000] + '...' if len(text) > 1000 else text,  # Limit content length
            'url': url
        }
    except Exception as e:
        return {'error': str(e)}

# Document processing functions
def extract_text_from_pdf(file):
    """Extract text from PDF file"""
    try:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        st.error(f"PDF extraction error: {e}")
        return ""

def extract_text_from_word(file):
    """Extract text from Word document"""
    try:
        doc = Document(file)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text
    except Exception as e:
        st.error(f"Word extraction error: {e}")
        return ""

def process_uploaded_file(file):
    """Process uploaded file and return text content"""
    file_type = file.name.split('.')[-1].lower()
    
    if file_type == 'pdf':
        return extract_text_from_pdf(file)
    elif file_type in ['docx', 'doc']:
        return extract_text_from_word(file)
    elif file_type == 'txt':
        return file.read().decode('utf-8')
    else:
        return "Unsupported file type"

# Update problem status
def update_problem_status(problem_id, new_status, resolution=None):
    conn = sqlite3.connect('problem_solving.db')
    c = conn.cursor()
    
    if new_status == 'solved' and resolution:
        c.execute('''
            UPDATE problems 
            SET status = ?, resolution = ?, resolved_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        ''', (new_status, resolution, problem_id))
    else:
        c.execute('UPDATE problems SET status = ? WHERE id = ?', (new_status, problem_id))
    
    conn.commit()
    conn.close()

# Get all users for assignment
def get_all_users():
    conn = sqlite3.connect('problem_solving.db')
    c = conn.cursor()
    c.execute('SELECT id, name, email, role, created_at FROM users')
    users = c.fetchall()
    conn.close()
    return users

# Priority mapping for sorting
PRIORITY_ORDER = {'Critical': 1, 'High': 2, 'Medium': 3, 'Low': 4}

def main():
    st.set_page_config(page_title="Enhanced Problem Solving Platform", page_icon="🔧", layout="wide")
    
    # Initialize database
    init_db()
    
    # Sidebar for navigation
    st.sidebar.title("🔧 Enhanced Problem Solving Platform")
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
        st.title("🔧 Enhanced Problem Solving Platform")
        st.markdown("""
        ### Welcome to the Enhanced Collaborative Problem Solving Platform!
        
        **New Features:**
        - 🎫 Ticket System with unique IDs
        - 📎 File Attachments (PDF, Word, Text)
        - 🔍 Web Search Integration (DuckDuckGo + BeautifulSoup)
        - 📊 Enhanced Document Processing
        - 👥 Improved Assignment System
        
        **Please login or register to get started!**
        """)
        
        # Show recent problems (read-only for non-logged in users)
        st.subheader("📋 Recently Submitted Problems")
        problems = get_all_problems()
        if problems:
            problem_data = []
            for problem in problems:
                problem_data.append({
                    'Ticket ID': problem[1],
                    'Title': problem[2],
                    'Category': problem[4],
                    'Priority': problem[5],
                    'Status': problem[6],
                    'Submitted By': problem[12],
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
        pages = ["Home", "Submit Ticket", "My Tickets", "All Tickets", "Calendar", "Admin Panel", "Web Search"]
    else:
        pages = ["Home", "Submit Ticket", "My Tickets", "Available Tickets", "Calendar", "Web Search"]
    
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
    elif st.session_state.page == "Submit Ticket":
        show_submit_ticket(user)
    elif st.session_state.page == "My Tickets":
        show_my_tickets(user)
    elif st.session_state.page == "Available Tickets":
        show_available_tickets(user)
    elif st.session_state.page == "All Tickets":
        show_all_tickets(user)
    elif st.session_state.page == "Calendar":
        show_calendar(user)
    elif st.session_state.page == "Admin Panel":
        show_admin_panel(user)
    elif st.session_state.page == "Web Search":
        show_web_search(user)

def show_home_page(user):
    st.title("🏠 Dashboard")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Statistics
    problems = get_all_problems()
    user_problems = get_user_problems(user['id'])
    assignments = len([p for p in problems if p[10] == user['id']])
    
    with col1:
        st.metric("Total Tickets", len(problems))
    with col2:
        st.metric("My Submitted Tickets", len(user_problems))
    with col3:
        st.metric("My Assignments", assignments)
    with col4:
        st.metric("Open Tickets", len([p for p in problems if p[6] in ['submitted', 'in progress']]))
    
    st.markdown("---")
    
    # Recent activity
    st.subheader("📈 Recent Activity")
    
    # Recent problems
    recent_problems = problems[:5]
    if recent_problems:
        st.write("**Recently Submitted Tickets:**")
        for problem in recent_problems:
            with st.expander(f"{problem[1]} - {problem[2]} - {problem[5]} Priority"):
                st.write(f"**Category:** {problem[4]}")
                st.write(f"**Status:** {problem[6]}")
                st.write(f"**Submitted by:** {problem[12]}")
                st.write(f"**Assigned to:** {problem[13] if problem[13] else 'Unassigned'}")
                st.write(f"**Deadline:** {problem[9]}")
    else:
        st.info("No tickets submitted yet.")

def show_submit_ticket(user):
    st.title("🎫 Submit New Ticket")
    
    with st.form("ticket_form"):
        title = st.text_input("Ticket Title*")
        description = st.text_area("Problem Description*", height=150)
        
        col1, col2 = st.columns(2)
        with col1:
            category = st.selectbox("Category*", [
                "Technical", "Research", "Business", 
                "Academic", "Software", "Hardware",
                "Data Analysis", "Algorithm", "Documentation", "Other"
            ])
        with col2:
            priority = st.selectbox("Priority*", ["Low", "Medium", "High", "Critical"])
        
        deadline_days = st.slider("Deadline (days from now)", 1, 90, 30)
        
        # File upload
        uploaded_files = st.file_uploader(
            "Attach Files (PDF, Word, Text)", 
            type=['pdf', 'docx', 'doc', 'txt'],
            accept_multiple_files=True
        )
        
        submitted = st.form_submit_button("Submit Ticket")
        
        if submitted:
            if title and description:
                problem_id, ticket_id = submit_problem(title, description, category, priority, user['id'], deadline_days)
                st.success(f"Ticket submitted successfully! Ticket ID: {ticket_id}")
                
                # Save uploaded files
                if uploaded_files:
                    for uploaded_file in uploaded_files:
                        file_data = uploaded_file.read()
                        save_file_attachment(
                            problem_id, 
                            uploaded_file.name, 
                            file_data, 
                            uploaded_file.type, 
                            user['id']
                        )
                    st.info(f"📎 {len(uploaded_files)} file(s) attached")
                
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

def show_my_tickets(user):
    st.title("📋 My Submitted Tickets")
    
    problems = get_user_problems(user['id'])
    
    if not problems:
        st.info("You haven't submitted any tickets yet.")
        return
    
    for problem in problems:
        with st.expander(f"{problem[1]} - {problem[2]} [{problem[5]}] - {problem[6]}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Ticket ID:** {problem[1]}")
                st.write(f"**Category:** {problem[4]}")
                st.write(f"**Priority:** {problem[5]}")
                st.write(f"**Status:** {problem[6]}")
                st.write(f"**Submitted:** {problem[8]}")
                st.write(f"**Deadline:** {problem[9]}")
                st.write(f"**Assigned to:** {problem[13] if problem[13] else 'Unassigned'}")
            
            with col2:
                st.write("**Description:**")
                st.write(problem[3])
                
                # Show file attachments
                attachments = get_file_attachments(problem[0])
                if attachments:
                    st.write("**Attachments:**")
                    for attachment in attachments:
                        col_a1, col_a2 = st.columns([3, 1])
                        with col_a1:
                            st.write(f"📎 {attachment[2]}")
                        with col_a2:
                            file_data = attachment[3]
                            st.download_button(
                                label="Download",
                                data=file_data,
                                file_name=attachment[2],
                                mime=attachment[4],
                                key=f"dl_{attachment[0]}"
                            )
                
                # Show search results
                search_results = get_search_results(problem[0])
                if search_results:
                    st.write("**Saved Search Results:**")
                    for result in search_results[:3]:  # Show first 3
                        st.write(f"🔍 {result[3]} - {result[5]}")
            
            # Add calendar event for this problem
            st.subheader("Add Calendar Event")
            with st.form(f"event_form_{problem[0]}"):
                event_title = st.text_input("Event Title", value=f"Meeting: {problem[2]}")
                event_desc = st.text_area("Event Description")
                event_date = st.date_input("Event Date", min_value=datetime.now().date())
                event_time = st.time_input("Event Time", datetime.now().time())
                
                if st.form_submit_button("Add to Calendar"):
                    event_datetime = datetime.combine(event_date, event_time)
                    add_calendar_event(problem[0], event_title, event_desc, event_datetime, user['id'])
                    st.success("Event added to calendar!")

def show_available_tickets(user):
    st.title("🔍 Available Tickets for Solving")
    
    problems = get_all_problems()
    
    # Filter problems that are not assigned to current user and are still open
    available_problems = [p for p in problems if p[10] != user['id'] and p[6] in ['submitted', 'in progress']]
    
    if not available_problems:
        st.info("No available tickets at the moment.")
        return
    
    # Sort by priority
    available_problems.sort(key=lambda x: PRIORITY_ORDER.get(x[5], 5))
    
    for problem in available_problems:
        with st.expander(f"{problem[1]} - {problem[2]} [{problem[5]}] - {problem[6]}"):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(f"**Ticket ID:** {problem[1]}")
                st.write(f"**Category:** {problem[4]}")
                st.write(f"**Priority:** {problem[5]}")
                st.write(f"**Status:** {problem[6]}")
                st.write(f"**Submitted by:** {problem[12]}")
                st.write(f"**Deadline:** {problem[9]}")
                st.write("**Description:**")
                st.write(problem[3])
                
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
                        st.error("Assignment failed!")

def show_all_tickets(user):
    if user['role'] != 'admin':
        st.error("Access denied. Admin privileges required.")
        return
    
    st.title("📊 All Tickets (Admin View)")
    
    problems = get_all_problems()
    
    if not problems:
        st.info("No tickets submitted yet.")
        return
    
    # Create DataFrame for better display
    problem_data = []
    for problem in problems:
        assignments = get_problem_assignments(problem[0])
        assigned_to = ", ".join([a[4] for a in assignments]) if assignments else "None"
        
        problem_data.append({
            'Ticket ID': problem[1],
            'Title': problem[2],
            'Category': problem[4],
            'Priority': problem[5],
            'Status': problem[6],
            'Submitted By': problem[12],
            'Assigned To': assigned_to,
            'Deadline': problem[9],
            'Created': problem[8]
        })
    
    df = pd.DataFrame(problem_data)
    st.dataframe(df, use_container_width=True)
    
    # Ticket management
    st.subheader("Ticket Management")
    problem_ids = [p[0] for p in problems]
    selected_problem = st.selectbox("Select Ticket to Manage", problem_ids, 
                                   format_func=lambda x: f"{next(p[1] for p in problems if p[0] == x)} - {next(p[2] for p in problems if p[0] == x)}")
    
    if selected_problem:
        problem = next(p for p in problems if p[0] == selected_problem)
        col1, col2, col3 = st.columns(3)
        
        with col1:
            new_status = st.selectbox("Update Status", 
                                    ["submitted", "in progress", "solved", "closed"],
                                    index=["submitted", "in progress", "solved", "closed"].index(problem[6]))
            
            resolution = st.text_area("Resolution Notes", value=problem[11] or "")
            
            if st.button("Update Status"):
                update_problem_status(selected_problem, new_status, resolution)
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
            
            # Assign to user
            users = get_all_users()
            user_options = {f"{u[1]} ({u[3]})": u[0] for u in users}
            selected_user = st.selectbox("Assign to User", list(user_options.keys()))
            
            if st.button("Assign User"):
                user_id = user_options[selected_user]
                assign_to_problem(selected_problem, user_id)
                st.success("User assigned!")
                st.rerun()
        
        with col3:
            # File attachments
            st.write("**Attachments:**")
            attachments = get_file_attachments(selected_problem)
            if attachments:
                for attachment in attachments:
                    st.write(f"📎 {attachment[2]}")
            else:
                st.write("No attachments")

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
                st.write(f"**Ticket:** {event[6]}")
                st.write(f"**Description:** {event[2]}")
                st.write(f"**Created by:** {event[7]}")

def show_admin_panel(user):
    if user['role'] != 'admin':
        st.error("Access denied. Admin privileges required.")
        return
    
    st.title("⚙️ Admin Panel")
    
    tab1, tab2, tab3, tab4 = st.tabs(["User Management", "System Statistics", "Database Management", "File Management"])
    
    with tab1:
        st.subheader("User Management")
        users = get_all_users()
        
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
        users = get_all_users()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Tickets", len(problems))
        with col2:
            st.metric("Total Users", len(users))
        with col3:
            st.metric("In Progress", len([p for p in problems if p[6] == 'in progress']))
        with col4:
            st.metric("Solved", len([p for p in problems if p[6] == 'solved']))
        
        # Priority distribution
        st.subheader("Priority Distribution")
        priority_counts = {}
        for problem in problems:
            priority = problem[5]
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
        
        if priority_counts:
            priority_df = pd.DataFrame(list(priority_counts.items()), columns=['Priority', 'Count'])
            st.bar_chart(priority_df.set_index('Priority'))
    
    with tab3:
        st.subheader("Database Management")
        
        if st.button("Export Tickets to CSV"):
            problems = get_all_problems()
            if problems:
                problem_data = []
                for problem in problems:
                    problem_data.append({
                        'Ticket_ID': problem[1],
                        'Title': problem[2],
                        'Description': problem[3],
                        'Category': problem[4],
                        'Priority': problem[5],
                        'Status': problem[6],
                        'Submitted_By': problem[12],
                        'Assigned_To': problem[13],
                        'Created_At': problem[8],
                        'Deadline': problem[9],
                        'Resolution': problem[11]
                    })
                
                problems_df = pd.DataFrame(problem_data)
                st.download_button(
                    label="Download Tickets CSV",
                    data=problems_df.to_csv(index=False),
                    file_name="tickets_export.csv",
                    mime="text/csv"
                )
    
    with tab4:
        st.subheader("File Management")
        st.info("File attachments are managed within individual tickets.")

def show_web_search(user):
    st.title("🔍 Web Search & Research")
    
    tab1, tab2, tab3 = st.tabs(["Search Web", "Search Results", "Content Extraction"])
    
    with tab1:
        st.subheader("Web Search")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            search_query = st.text_input("Search Query", placeholder="Enter your search terms...")
        with col2:
            max_results = st.number_input("Max Results", min_value=1, max_value=20, value=5)
        
        problem_id = st.selectbox(
            "Associate with Ticket (Optional)",
            [""] + [f"{p[0]} - {p[1]}" for p in get_user_problems(user['id'])]
        )
        
        if st.button("Search Web") and search_query:
            with st.spinner("Searching..."):
                results = search_web(search_query, max_results)
                
                if results:
                    st.success(f"Found {len(results)} results")
                    
                    for i, result in enumerate(results):
                        with st.expander(f"{i+1}. {result['title']}"):
                            st.write(f"**URL:** {result['href']}")
                            st.write(f"**Snippet:** {result['body']}")
                            
                            col_s1, col_s2 = st.columns(2)
                            with col_s1:
                                if st.button(f"Save Result", key=f"save_{i}"):
                                    if problem_id:
                                        ticket_id = int(problem_id.split(' - ')[0])
                                        save_search_result(
                                            ticket_id,
                                            search_query,
                                            result['title'],
                                            result['href'],
                                            result['body'],
                                            "DuckDuckGo"
                                        )
                                        st.success("Result saved to ticket!")
                                    else:
                                        st.error("Please select a ticket to save the result")
                            
                            with col_s2:
                                if st.button(f"Extract Content", key=f"extract_{i}"):
                                    with st.spinner("Extracting content..."):
                                        content = search_with_beautiful_soup(result['href'])
                                        if 'error' not in content:
                                            st.write("**Extracted Content:**")
                                            st.text_area("Content", content['content'], height=200, key=f"content_{i}")
                                        else:
                                            st.error(f"Extraction failed: {content['error']}")
                else:
                    st.error("No results found or search failed")
    
    with tab2:
        st.subheader("Saved Search Results")
        
        user_problems = get_user_problems(user['id'])
        if user_problems:
            selected_ticket = st.selectbox(
                "Select Ticket to View Saved Results",
                [f"{p[0]} - {p[1]}" for p in user_problems]
            )
            
            if selected_ticket:
                ticket_id = int(selected_ticket.split(' - ')[0])
                saved_results = get_search_results(ticket_id)
                
                if saved_results:
                    for result in saved_results:
                        with st.expander(f"{result[3]} - {result[6]}"):
                            st.write(f"**Query:** {result[2]}")
                            st.write(f"**URL:** {result[4]}")
                            st.write(f"**Snippet:** {result[5]}")
                            st.write(f"**Searched:** {result[7]}")
                else:
                    st.info("No saved search results for this ticket")
        else:
            st.info("No tickets available to show search results")
    
    with tab3:
        st.subheader("Content Extraction Tool")
        
        url = st.text_input("Enter URL to extract content")
        if st.button("Extract Content") and url:
            with st.spinner("Extracting content..."):
                content = search_with_beautiful_soup(url)
                if 'error' not in content:
                    st.success("Content extracted successfully!")
                    st.write(f"**Title:** {content['title']}")
                    st.write("**Content:**")
                    st.text_area("Extracted Content", content['content'], height=300)
                else:
                    st.error(f"Extraction failed: {content['error']}")

# Add credits footer
st.markdown("---")
st.markdown("**Credits:** Enhanced Problem Solving Platform developed by Paulo Monteiro")

if __name__ == "__main__":
    main()
