from flask import Flask, request, jsonify, send_file, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import json
from datetime import datetime
import re
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = 'uploads'

db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    original_filename = db.Column(db.String(300))
    google_doc_link = db.Column(db.String(500))
    file_path = db.Column(db.String(500))
    file_type = db.Column(db.String(50))
    file_size = db.Column(db.Integer)
    category = db.Column(db.String(100), default='General')
    tags = db.Column(db.String(300))
    description = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Helper functions
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Please log in first'}), 401
        return f(*args, **kwargs)
    return decorated_function

def allowed_file(filename):
    allowed_extensions = {'pdf', 'doc', 'docx', 'txt', 'xls', 'xlsx', 'ppt', 'pptx', 'jpg', 'jpeg', 'png', 'zip'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def get_user_folder(user_id):
    user_folder = os.path.join(app.config['UPLOAD_FOLDER'], f'user_{user_id}')
    if not os.path.exists(user_folder):
        os.makedirs(user_folder)
    return user_folder

def create_user_folder(user_id):
    """Create user folder immediately when user signs up"""
    user_folder = os.path.join(app.config['UPLOAD_FOLDER'], f'user_{user_id}')
    if not os.path.exists(user_folder):
        os.makedirs(user_folder)
        print(f"✅ Created user folder: {user_folder}")
    return user_folder

def format_file_size(size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"

# Main HTML Page - Enhanced with Charts
@app.route('/')
def index():
    return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DocManager Pro - Enhanced Document Management</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/gsap.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {
            --primary: #6366f1;
            --primary-dark: #4f46e5;
            --secondary: #10b981;
            --danger: #ef4444;
            --warning: #f59e0b;
            --info: #3b82f6;
            
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --bg-card: #334155;
            --text-primary: #f8fafc;
            --text-secondary: #cbd5e1;
            --border: #475569;
            
            --gradient-primary: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            --gradient-secondary: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            --gradient-success: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            
            --shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3), 0 4px 6px -2px rgba(0, 0, 0, 0.2);
            --shadow-lg: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
            
            --border-radius: 12px;
            --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .light-theme {
            --bg-primary: #f8fafc;
            --bg-secondary: #e2e8f0;
            --bg-card: #ffffff;
            --text-primary: #1e293b;
            --text-secondary: #475569;
            --border: #cbd5e1;
            
            --shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
            --shadow-lg: 0 25px 50px -12px rgba(0, 0, 0, 0.15);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            overflow-x: hidden;
            transition: var(--transition);
        }

        /* Particles Background */
        #particles-js {
            position: fixed;
            width: 100%;
            height: 100%;
            z-index: -1;
        }

        /* Header Styles */
        .header {
            background: rgba(15, 23, 42, 0.8);
            backdrop-filter: blur(10px);
            padding: 1rem 0;
            box-shadow: var(--shadow);
            position: sticky;
            top: 0;
            z-index: 100;
            border-bottom: 1px solid var(--border);
            transition: var(--transition);
        }

        .light-theme .header {
            background: rgba(248, 250, 252, 0.8);
        }

        .header-content {
            max-width: 1400px;
            margin: 0 auto;
            padding: 0 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .logo {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .logo-icon {
            font-size: 2rem;
            background: var(--gradient-primary);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            filter: drop-shadow(0 0 10px rgba(99, 102, 241, 0.5));
            animation: pulse 2s infinite;
        }

        .logo h1 {
            font-size: 1.8rem;
            background: var(--gradient-primary);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            font-weight: 700;
        }

        /* Navigation */
        .nav {
            display: flex;
            gap: 10px;
            margin-bottom: 2rem;
            background: var(--bg-secondary);
            padding: 0.5rem;
            border-radius: var(--border-radius);
            box-shadow: var(--shadow);
        }

        .nav-btn {
            padding: 12px 24px;
            background: transparent;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            color: var(--text-secondary);
            transition: var(--transition);
            position: relative;
            overflow: hidden;
        }

        .nav-btn::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: var(--gradient-primary);
            transition: var(--transition);
            z-index: -1;
        }

        .nav-btn:hover::before,
        .nav-btn.active::before {
            left: 0;
        }

        .nav-btn:hover,
        .nav-btn.active {
            color: white;
            box-shadow: 0 0 15px rgba(99, 102, 241, 0.5);
        }

        /* Auth Container */
        .auth-container {
            max-width: 450px;
            margin: 80px auto;
            padding: 2.5rem;
            background: var(--bg-card);
            border-radius: var(--border-radius);
            box-shadow: var(--shadow-lg);
            backdrop-filter: blur(10px);
            border: 1px solid var(--border);
            position: relative;
            overflow: hidden;
        }

        .auth-container::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: var(--gradient-primary);
        }

        .auth-form {
            display: none;
        }

        .auth-form.active {
            display: block;
            animation: fadeIn 0.5s ease-out;
        }

        /* Form Elements */
        .form-group {
            margin-bottom: 1.5rem;
            position: relative;
        }

        .form-group label {
            display: block;
            margin-bottom: 0.5rem;
            font-weight: 600;
            color: var(--text-primary);
        }

        .form-input {
            width: 100%;
            padding: 14px 16px;
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 8px;
            font-size: 16px;
            color: var(--text-primary);
            transition: var(--transition);
        }

        .form-input:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2);
        }

        /* Buttons */
        .btn {
            padding: 14px 24px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            transition: var(--transition);
            position: relative;
            overflow: hidden;
        }

        .btn::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
            transition: var(--transition);
        }

        .btn:hover::before {
            left: 100%;
        }

        .btn-primary {
            background: var(--gradient-primary);
            color: white;
            box-shadow: 0 4px 6px rgba(99, 102, 241, 0.3);
        }

        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(99, 102, 241, 0.4);
        }

        .btn-secondary {
            background: var(--bg-secondary);
            color: var(--text-primary);
            border: 1px solid var(--border);
        }

        .btn-secondary:hover {
            background: var(--bg-card);
        }

        .btn-success {
            background: var(--gradient-success);
            color: white;
        }

        .btn-danger {
            background: var(--danger);
            color: white;
        }

        .btn-block {
            width: 100%;
        }

        /* Stats Cards */
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }

        .stat-card {
            background: var(--bg-card);
            padding: 1.5rem;
            border-radius: var(--border-radius);
            box-shadow: var(--shadow);
            border: 1px solid var(--border);
            transition: var(--transition);
            position: relative;
            overflow: hidden;
        }

        .stat-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: var(--gradient-primary);
        }

        .stat-card:hover {
            transform: translateY(-5px);
            box-shadow: var(--shadow-lg);
        }

        .stat-card h3 {
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
            background: var(--gradient-primary);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
        }

        /* Chart Containers */
        .charts-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }

        .chart-card {
            background: var(--bg-card);
            padding: 1.5rem;
            border-radius: var(--border-radius);
            box-shadow: var(--shadow);
            border: 1px solid var(--border);
            position: relative;
            overflow: hidden;
        }

        .chart-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: var(--gradient-primary);
        }

        .chart-title {
            font-size: 1.2rem;
            font-weight: 600;
            margin-bottom: 1rem;
            text-align: center;
            color: var(--text-primary);
        }

        .chart-wrapper {
            position: relative;
            height: 300px;
            display: flex;
            justify-content: center;
            align-items: center;
        }

        /* Document Cards - UPDATED LAYOUT */
        .documents-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 1.5rem;
        }

        .document-card {
            background: var(--bg-card);
            padding: 1.5rem;
            border-radius: var(--border-radius);
            box-shadow: var(--shadow);
            border: 1px solid var(--border);
            transition: var(--transition);
            position: relative;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            height: 100%;
        }

        .document-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: var(--gradient-primary);
        }

        .document-card:hover {
            transform: translateY(-5px);
            box-shadow: var(--shadow-lg);
        }

        .document-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 1rem;
        }

        .document-title {
            font-weight: 700;
            font-size: 1.2rem;
            margin-bottom: 0.5rem;
            color: var(--text-primary);
            line-height: 1.3;
        }

        .document-category {
            background: var(--gradient-primary);
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            display: inline-block;
        }

        .file-icon-container {
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 1rem;
        }

        .file-icon {
            font-size: 3rem;
        }

        .document-content {
            flex: 1;
            margin-bottom: 1rem;
        }

        .document-description {
            color: var(--text-secondary);
            margin-bottom: 1rem;
            line-height: 1.4;
            font-size: 0.9rem;
        }

        .document-meta {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.8rem;
            color: var(--text-secondary);
            margin-bottom: 1rem;
        }

        .document-actions {
            display: flex;
            gap: 8px;
            justify-content: center;
            padding-top: 1rem;
            border-top: 1px solid var(--border);
        }

        .action-btn {
            padding: 10px 16px;
            border: none;
            background: var(--bg-secondary);
            border-radius: 8px;
            cursor: pointer;
            color: var(--text-secondary);
            transition: var(--transition);
            font-size: 0.9rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 6px;
            flex: 1;
            justify-content: center;
        }

        .action-btn:hover {
            background: var(--primary);
            color: white;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(99, 102, 241, 0.3);
        }

        .action-btn.delete:hover {
            background: var(--danger);
            box-shadow: 0 4px 8px rgba(239, 68, 68, 0.3);
        }

        .action-btn.download:hover {
            background: var(--secondary);
            box-shadow: 0 4px 8px rgba(16, 185, 129, 0.3);
        }

        .action-btn.copy:hover {
            background: var(--info);
            box-shadow: 0 4px 8px rgba(59, 130, 246, 0.3);
        }

        /* File Type Icons */
        .pdf-icon {
            color: #ff4b4b;
        }

        .doc-icon {
            color: #2b579a;
        }

        .xls-icon {
            color: #217346;
        }

        .img-icon {
            color: #ff6b6b;
        }

        .code-icon {
            color: #6f42c1;
        }

        .drive-icon {
            color: #4285f4;
        }

        /* Search and Filter */
        .search-box {
            margin-bottom: 1.5rem;
            display: flex;
            gap: 10px;
            align-items: center;
        }

        .search-box input {
            flex: 1;
            padding: 14px 16px;
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 8px;
            font-size: 16px;
            color: var(--text-primary);
            transition: var(--transition);
        }

        .search-box input:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2);
        }

        /* Modals */
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.7);
            z-index: 1000;
            backdrop-filter: blur(5px);
        }

        .modal-content {
            background: var(--bg-card);
            margin: 50px auto;
            padding: 2rem;
            border-radius: var(--border-radius);
            max-width: 500px;
            position: relative;
            box-shadow: var(--shadow-lg);
            border: 1px solid var(--border);
            animation: modalAppear 0.3s ease-out;
        }

        .close-btn {
            position: absolute;
            top: 15px;
            right: 15px;
            background: none;
            border: none;
            font-size: 1.5rem;
            cursor: pointer;
            color: var(--text-secondary);
            transition: var(--transition);
        }

        .close-btn:hover {
            color: var(--danger);
            transform: rotate(90deg);
        }

        /* Toast */
        .toast {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 1rem 1.5rem;
            background: var(--bg-card);
            border-radius: var(--border-radius);
            box-shadow: var(--shadow-lg);
            display: none;
            z-index: 2000;
            border-left: 4px solid var(--primary);
            animation: slideInRight 0.3s ease-out;
        }

        .toast.success {
            border-left-color: var(--secondary);
        }

        .toast.error {
            border-left-color: var(--danger);
        }

        /* Theme Toggle */
        .theme-toggle {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 50px;
            padding: 8px;
            cursor: pointer;
            display: flex;
            align-items: center;
            transition: var(--transition);
        }

        .theme-toggle:hover {
            background: var(--bg-card);
        }

        .theme-icon {
            font-size: 1.2rem;
            transition: var(--transition);
        }

        /* Animations */
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }

        @keyframes modalAppear {
            from { opacity: 0; transform: scale(0.8) translateY(-20px); }
            to { opacity: 1; transform: scale(1) translateY(0); }
        }

        @keyframes slideInRight {
            from { opacity: 0; transform: translateX(100%); }
            to { opacity: 1; transform: translateX(0); }
        }

        /* Utility Classes */
        .hidden { display: none; }
        .text-center { text-align: center; }
        .mt-2 { margin-top: 1rem; }
        .mb-2 { margin-bottom: 1rem; }

        /* Responsive */
        @media (max-width: 768px) {
            .header-content {
                padding: 0 1rem;
            }
            
            .documents-grid {
                grid-template-columns: 1fr;
            }
            
            .stats {
                grid-template-columns: 1fr;
            }
            
            .charts-container {
                grid-template-columns: 1fr;
            }
            
            .search-box {
                flex-direction: column;
            }
            
            .document-actions {
                flex-direction: column;
            }
            
            .action-btn {
                width: 100%;
            }
        }
    </style>
</head>
<body>
    <!-- Particles Background -->
    <div id="particles-js"></div>

    <!-- Header -->
    <div class="header">
        <div class="header-content">
            <div class="logo">
                <i class="fas fa-folder-open logo-icon"></i>
                <h1>DocManager Pro</h1>
            </div>
            <div id="userInfo" class="hidden">
                <span id="usernameDisplay"></span>
                <button class="btn btn-secondary" onclick="logout()">
                    <i class="fas fa-sign-out-alt"></i> Logout
                </button>
                <div class="theme-toggle" onclick="toggleTheme()">
                    <i class="fas fa-moon theme-icon"></i>
                </div>
            </div>
        </div>
    </div>

    <div class="container">
        <!-- Auth Section -->
        <div id="authSection">
            <div class="auth-container">
                <div class="text-center mb-2">
                    <h2>Welcome to DocManager Pro</h2>
                    <p>Enhanced document management with stunning visuals</p>
                </div>
                
                <div class="nav">
                    <button class="nav-btn active" onclick="showAuthForm('login')">
                        <i class="fas fa-sign-in-alt"></i> Login
                    </button>
                    <button class="nav-btn" onclick="showAuthForm('signup')">
                        <i class="fas fa-user-plus"></i> Sign Up
                    </button>
                </div>

                <form id="loginForm" class="auth-form active" onsubmit="handleLogin(event)">
                    <div class="form-group">
                        <label><i class="fas fa-user"></i> Username</label>
                        <input type="text" class="form-input" required>
                    </div>
                    <div class="form-group">
                        <label><i class="fas fa-lock"></i> Password</label>
                        <input type="password" class="form-input" required>
                    </div>
                    <button type="submit" class="btn btn-primary btn-block">
                        <i class="fas fa-sign-in-alt"></i> Login
                    </button>
                </form>

                <form id="signupForm" class="auth-form" onsubmit="handleSignup(event)">
                    <div class="form-group">
                        <label><i class="fas fa-user"></i> Username</label>
                        <input type="text" class="form-input" required>
                    </div>
                    <div class="form-group">
                        <label><i class="fas fa-envelope"></i> Email</label>
                        <input type="email" class="form-input" required>
                    </div>
                    <div class="form-group">
                        <label><i class="fas fa-lock"></i> Password</label>
                        <input type="password" class="form-input" required>
                    </div>
                    <div class="form-group">
                        <label><i class="fas fa-lock"></i> Confirm Password</label>
                        <input type="password" class="form-input" required>
                    </div>
                    <div class="form-group">
                        <label><i class="fas fa-briefcase"></i> Primary Use</label>
                        <select class="form-input" required>
                            <option value="">Select your primary use</option>
                            <option value="education">Education</option>
                            <option value="professional">Professional Work</option>
                            <option value="personal">Personal</option>
                            <option value="business">Business</option>
                            <option value="research">Research</option>
                            <option value="other">Other</option>
                        </select>
                    </div>
                    <button type="submit" class="btn btn-primary btn-block">
                        <i class="fas fa-user-plus"></i> Create Account
                    </button>
                </form>
            </div>
        </div>

        <!-- Main App Section -->
        <div id="appSection" class="hidden">
            <div class="nav">
                <button class="nav-btn active" onclick="showSection('dashboard')">
                    <i class="fas fa-tachometer-alt"></i> Dashboard
                </button>
                <button class="nav-btn" onclick="showSection('documents')">
                    <i class="fas fa-file"></i> Documents
                </button>
                <div class="theme-toggle" onclick="toggleTheme()">
                    <i class="fas fa-moon theme-icon"></i>
                </div>
            </div>

            <!-- Dashboard -->
            <div id="dashboardSection">
                <h2>Dashboard</h2>
                <div class="stats">
                    <div class="stat-card">
                        <i class="fas fa-file-pdf pdf-icon file-icon"></i>
                        <h3 id="totalDocs">0</h3>
                        <p>Total Documents</p>
                    </div>
                    <div class="stat-card">
                        <i class="fas fa-hdd file-icon"></i>
                        <h3 id="totalStorage">0 B</h3>
                        <p>Storage Used</p>
                    </div>
                    <div class="stat-card">
                        <i class="fas fa-file-code code-icon file-icon"></i>
                        <h3 id="fileTypes">0</h3>
                        <p>File Types</p>
                    </div>
                </div>

                <!-- Charts Section -->
                <div class="charts-container">
                    <div class="chart-card">
                        <div class="chart-title">File Types Distribution</div>
                        <div class="chart-wrapper">
                            <canvas id="fileTypeChart"></canvas>
                        </div>
                    </div>
                    <div class="chart-card">
                        <div class="chart-title">Document Categories</div>
                        <div class="chart-wrapper">
                            <canvas id="categoryChart"></canvas>
                        </div>
                    </div>
                </div>
                
                <div class="stats">
                    <div class="stat-card">
                        <h3>Quick Actions</h3>
                        <button class="btn btn-primary mt-2" onclick="openAddModal()">
                            <i class="fab fa-google-drive"></i> Add Google Doc
                        </button>
                        <button class="btn btn-success mt-2" onclick="openUploadModal()">
                            <i class="fas fa-upload"></i> Upload File
                        </button>
                    </div>
                    <div class="stat-card">
                        <h3>Recent Activity</h3>
                        <div id="recentActivity"></div>
                    </div>
                </div>
            </div>

            <!-- Documents -->
            <div id="documentsSection" class="hidden">
                <h2>My Documents</h2>
                
                <div class="search-box">
                    <input type="text" id="searchInput" placeholder="Search documents..." onkeyup="filterDocuments()">
                    <select id="typeFilter" onchange="filterDocuments()">
                        <option value="">All Types</option>
                        <option value="google_doc">Google Docs</option>
                        <option value="file">Files</option>
                    </select>
                    <select id="categoryFilter" onchange="filterDocuments()">
                        <option value="">All Categories</option>
                        <option value="Education">Education</option>
                        <option value="Professional">Professional</option>
                        <option value="Personal">Personal</option>
                        <option value="Business">Business</option>
                        <option value="Research">Research</option>
                        <option value="General">General</option>
                    </select>
                    <button class="btn btn-primary" onclick="loadDocuments()">
                        <i class="fas fa-sync-alt"></i> Refresh
                    </button>
                </div>

                <div id="documentsContainer" class="documents-grid">
                    <!-- Documents will appear here -->
                </div>
            </div>
        </div>
    </div>

    <!-- Modals -->
    <div id="addModal" class="modal">
        <div class="modal-content">
            <button class="close-btn" onclick="closeAddModal()">×</button>
            <h3>Add Google Document</h3>
            <form onsubmit="handleAddDocument(event)">
                <div class="form-group">
                    <label>Document Name</label>
                    <input type="text" class="form-input" required>
                </div>
                <div class="form-group">
                    <label>Google Doc Link</label>
                    <input type="url" class="form-input" placeholder="https://docs.google.com/..." required>
                </div>
                <div class="form-group">
                    <label>Category</label>
                    <select class="form-input" required>
                        <option value="General">General</option>
                        <option value="Education">Education</option>
                        <option value="Professional">Professional</option>
                        <option value="Personal">Personal</option>
                        <option value="Business">Business</option>
                        <option value="Research">Research</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Description</label>
                    <textarea class="form-input" rows="3"></textarea>
                </div>
                <button type="submit" class="btn btn-primary">
                    <i class="fas fa-save"></i> Save Document
                </button>
            </form>
        </div>
    </div>

    <div id="uploadModal" class="modal">
        <div class="modal-content">
            <button class="close-btn" onclick="closeUploadModal()">×</button>
            <h3>Upload File</h3>
            <form onsubmit="handleUploadFile(event)">
                <div class="form-group">
                    <label>Select File</label>
                    <input type="file" class="form-input" required>
                </div>
                <div class="form-group">
                    <label>Category</label>
                    <select class="form-input" required>
                        <option value="General">General</option>
                        <option value="Education">Education</option>
                        <option value="Professional">Professional</option>
                        <option value="Personal">Personal</option>
                        <option value="Business">Business</option>
                        <option value="Research">Research</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Description</label>
                    <textarea class="form-input" rows="3"></textarea>
                </div>
                <button type="submit" class="btn btn-primary">
                    <i class="fas fa-upload"></i> Upload File
                </button>
            </form>
        </div>
    </div>

    <!-- Toast -->
    <div id="toast" class="toast"></div>

    <script src="https://cdn.jsdelivr.net/particles.js/2.0.0/particles.min.js"></script>
    <script>
        // Initialize particles background
        document.addEventListener('DOMContentLoaded', function() {
            particlesJS('particles-js', {
                particles: {
                    number: { value: 80, density: { enable: true, value_area: 800 } },
                    color: { value: "#6366f1" },
                    shape: { type: "circle" },
                    opacity: { value: 0.5, random: true },
                    size: { value: 3, random: true },
                    line_linked: {
                        enable: true,
                        distance: 150,
                        color: "#6366f1",
                        opacity: 0.4,
                        width: 1
                    },
                    move: {
                        enable: true,
                        speed: 2,
                        direction: "none",
                        random: true,
                        straight: false,
                        out_mode: "out",
                        bounce: false
                    }
                },
                interactivity: {
                    detect_on: "canvas",
                    events: {
                        onhover: { enable: true, mode: "repulse" },
                        onclick: { enable: true, mode: "push" },
                        resize: true
                    }
                },
                retina_detect: true
            });
        });

        let documents = [];
        let currentUser = null;
        let isDarkTheme = true;
        let fileTypeChart = null;
        let categoryChart = null;

        // Theme Toggle
        function toggleTheme() {
            isDarkTheme = !isDarkTheme;
            document.body.classList.toggle('light-theme');
            
            const themeIcon = document.querySelector('.theme-icon');
            if (isDarkTheme) {
                themeIcon.className = 'fas fa-moon theme-icon';
            } else {
                themeIcon.className = 'fas fa-sun theme-icon';
            }
            
            // Save theme preference
            localStorage.setItem('docmanager-theme', isDarkTheme ? 'dark' : 'light');
            
            // Update charts if they exist
            updateChartThemes();
        }

        function updateChartThemes() {
            const isDark = document.body.classList.contains('light-theme') ? false : true;
            const textColor = isDark ? '#f8fafc' : '#1e293b';
            const gridColor = isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)';
            
            if (fileTypeChart) {
                fileTypeChart.options.plugins.legend.labels.color = textColor;
                fileTypeChart.update();
            }
            if (categoryChart) {
                categoryChart.options.plugins.legend.labels.color = textColor;
                categoryChart.update();
            }
        }

        // Load saved theme
        const savedTheme = localStorage.getItem('docmanager-theme');
        if (savedTheme === 'light') {
            toggleTheme(); // Switch to light theme if saved
        }

        // Auth Functions
        function showAuthForm(formType) {
            document.querySelectorAll('.auth-form').forEach(form => form.classList.remove('active'));
            document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
            
            document.getElementById(formType + 'Form').classList.add('active');
            event.target.classList.add('active');
        }

        async function handleLogin(e) {
            e.preventDefault();
            const form = e.target;
            const formData = {
                username: form[0].value,
                password: form[1].value
            };

            try {
                const response = await fetch('/api/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(formData)
                });
                const data = await response.json();
                
                if (data.success) {
                    showToast('Login successful!', 'success');
                    currentUser = data.user;
                    showApp();
                    
                    // Celebration effect
                    createConfetti();
                } else {
                    showToast(data.message, 'error');
                }
            } catch (error) {
                showToast('Login failed', 'error');
            }
        }

        async function handleSignup(e) {
            e.preventDefault();
            const form = e.target;
            const formData = {
                username: form[0].value,
                email: form[1].value,
                password: form[2].value,
                confirm_password: form[3].value,
                primary_use: form[4].value
            };

            try {
                const response = await fetch('/api/signup', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(formData)
                });
                const data = await response.json();
                
                if (data.success) {
                    showToast('Account created successfully!', 'success');
                    currentUser = data.user;
                    showApp();
                    
                    // Celebration effect
                    createConfetti();
                } else {
                    showToast(data.message, 'error');
                }
            } catch (error) {
                showToast('Signup failed', 'error');
            }
        }

        function showApp() {
            document.getElementById('authSection').classList.add('hidden');
            document.getElementById('appSection').classList.remove('hidden');
            document.getElementById('userInfo').classList.remove('hidden');
            document.getElementById('usernameDisplay').textContent = currentUser.username;
            
            loadDashboard();
            loadDocuments();
        }

        async function logout() {
            try {
                await fetch('/api/logout');
                currentUser = null;
                document.getElementById('appSection').classList.add('hidden');
                document.getElementById('authSection').classList.remove('hidden');
                document.getElementById('userInfo').classList.add('hidden');
                showToast('Logged out', 'success');
            } catch (error) {
                showToast('Logout failed', 'error');
            }
        }

        // Chart Functions
        function createCharts(stats) {
            const isDark = !document.body.classList.contains('light-theme');
            const textColor = isDark ? '#f8fafc' : '#1e293b';
            const gridColor = isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)';

            // File Type Chart
            const fileTypeCtx = document.getElementById('fileTypeChart').getContext('2d');
            if (fileTypeChart) {
                fileTypeChart.destroy();
            }
            
            fileTypeChart = new Chart(fileTypeCtx, {
                type: 'doughnut',
                data: {
                    labels: Object.keys(stats.file_types),
                    datasets: [{
                        data: Object.values(stats.file_types),
                        backgroundColor: [
                            '#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4',
                            '#84cc16', '#f97316', '#ec4899', '#14b8a6'
                        ],
                        borderWidth: 2,
                        borderColor: isDark ? '#1e293b' : '#ffffff'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                color: textColor,
                                font: {
                                    size: 12
                                }
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const label = context.label || '';
                                    const value = context.raw || 0;
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = Math.round((value / total) * 100);
                                    return `${label}: ${value} (${percentage}%)`;
                                }
                            }
                        }
                    }
                }
            });

            // Category Chart
            const categoryCtx = document.getElementById('categoryChart').getContext('2d');
            if (categoryChart) {
                categoryChart.destroy();
            }
            
            categoryChart = new Chart(categoryCtx, {
                type: 'pie',
                data: {
                    labels: Object.keys(stats.categories),
                    datasets: [{
                        data: Object.values(stats.categories),
                        backgroundColor: [
                            '#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4',
                            '#84cc16', '#f97316', '#ec4899', '#14b8a6'
                        ],
                        borderWidth: 2,
                        borderColor: isDark ? '#1e293b' : '#ffffff'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                color: textColor,
                                font: {
                                    size: 12
                                }
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const label = context.label || '';
                                    const value = context.raw || 0;
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = Math.round((value / total) * 100);
                                    return `${label}: ${value} (${percentage}%)`;
                                }
                            }
                        }
                    }
                }
            });
        }

        // Document Functions
        async function loadDashboard() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();
                
                if (data.success) {
                    document.getElementById('totalDocs').textContent = data.stats.total_documents;
                    document.getElementById('totalStorage').textContent = data.stats.storage_formatted;
                    document.getElementById('fileTypes').textContent = Object.keys(data.stats.file_types).length;
                    
                    let recentHtml = '';
                    data.stats.recent_documents.forEach(doc => {
                        recentHtml += `<div style="padding: 5px 0; border-bottom: 1px solid var(--border);">
                            <strong>${doc.name}</strong> - ${doc.category}
                        </div>`;
                    });
                    document.getElementById('recentActivity').innerHTML = recentHtml || 'No recent activity';
                    
                    // Create charts
                    createCharts(data.stats);
                }
            } catch (error) {
                console.error('Failed to load dashboard:', error);
            }
        }

        async function loadDocuments() {
            try {
                const response = await fetch('/api/documents');
                const data = await response.json();
                
                if (data.success) {
                    documents = data.documents;
                    displayDocuments(documents);
                }
            } catch (error) {
                showToast('Failed to load documents', 'error');
            }
        }

        function displayDocuments(docs) {
            const container = document.getElementById('documentsContainer');
            
            if (docs.length === 0) {
                container.innerHTML = '<div class="text-center">No documents found</div>';
                return;
            }

            container.innerHTML = docs.map(doc => {
                let fileIcon = 'fas fa-file';
                let iconClass = '';
                
                if (doc.google_doc_link) {
                    fileIcon = 'fab fa-google-drive';
                    iconClass = 'drive-icon';
                } else if (doc.file_path) {
                    const ext = doc.file_path.split('.').pop().toLowerCase();
                    if (['pdf'].includes(ext)) {
                        fileIcon = 'fas fa-file-pdf';
                        iconClass = 'pdf-icon';
                    } else if (['doc', 'docx'].includes(ext)) {
                        fileIcon = 'fas fa-file-word';
                        iconClass = 'doc-icon';
                    } else if (['xls', 'xlsx'].includes(ext)) {
                        fileIcon = 'fas fa-file-excel';
                        iconClass = 'xls-icon';
                    } else if (['jpg', 'jpeg', 'png', 'gif'].includes(ext)) {
                        fileIcon = 'fas fa-file-image';
                        iconClass = 'img-icon';
                    } else if (['js', 'html', 'css', 'py', 'java', 'cpp'].includes(ext)) {
                        fileIcon = 'fas fa-file-code';
                        iconClass = 'code-icon';
                    }
                }
                
                return `
                    <div class="document-card">
                        <div class="document-header">
                            <div>
                                <div class="document-title">${escapeHtml(doc.name)}</div>
                                <span class="document-category">${doc.category}</span>
                            </div>
                        </div>
                        
                        <div class="file-icon-container">
                            <i class="${fileIcon} ${iconClass} file-icon"></i>
                        </div>
                        
                        <div class="document-content">
                            ${doc.description ? `<div class="document-description">${escapeHtml(doc.description)}</div>` : ''}
                            
                            <div class="document-meta">
                                ${doc.file_size ? `<span><i class="fas fa-weight-hanging"></i> ${doc.file_size_formatted}</span>` : ''}
                                <span><i class="fas fa-calendar"></i> ${new Date(doc.created_at).toLocaleDateString()}</span>
                            </div>
                        </div>
                        
                        <div class="document-actions">
                            ${doc.google_doc_link ? `
                                <button class="action-btn copy" onclick="copyLink('${doc.google_doc_link}')">
                                    <i class="fas fa-copy"></i> Copy
                                </button>
                                <button class="action-btn" onclick="openLink('${doc.google_doc_link}')">
                                    <i class="fas fa-external-link-alt"></i> Open
                                </button>
                            ` : ''}
                            ${doc.file_path ? `
                                <button class="action-btn download" onclick="downloadFile(${doc.id})">
                                    <i class="fas fa-download"></i> Download
                                </button>
                            ` : ''}
                            <button class="action-btn delete" onclick="deleteDocument(${doc.id})">
                                <i class="fas fa-trash"></i> Delete
                            </button>
                        </div>
                    </div>
                `;
            }).join('');
        }

        function filterDocuments() {
            const searchTerm = document.getElementById('searchInput').value.toLowerCase();
            const typeFilter = document.getElementById('typeFilter').value;
            const categoryFilter = document.getElementById('categoryFilter').value;
            
            let filtered = documents;
            
            if (searchTerm) {
                filtered = filtered.filter(doc => 
                    doc.name.toLowerCase().includes(searchTerm) ||
                    (doc.description && doc.description.toLowerCase().includes(searchTerm))
                );
            }
            
            if (typeFilter) {
                if (typeFilter === 'google_doc') {
                    filtered = filtered.filter(doc => doc.google_doc_link);
                } else if (typeFilter === 'file') {
                    filtered = filtered.filter(doc => doc.file_path);
                }
            }
            
            if (categoryFilter) {
                filtered = filtered.filter(doc => doc.category === categoryFilter);
            }
            
            displayDocuments(filtered);
        }

        // Modal Functions
        function openAddModal() {
            document.getElementById('addModal').style.display = 'block';
        }

        function closeAddModal() {
            document.getElementById('addModal').style.display = 'none';
        }

        function openUploadModal() {
            document.getElementById('uploadModal').style.display = 'block';
        }

        function closeUploadModal() {
            document.getElementById('uploadModal').style.display = 'none';
        }

        async function handleAddDocument(e) {
            e.preventDefault();
            const form = e.target;
            const formData = {
                name: form[0].value,
                link: form[1].value,
                category: form[2].value,
                description: form[3].value
            };

            try {
                const response = await fetch('/api/documents', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(formData)
                });
                const data = await response.json();
                
                if (data.success) {
                    showToast('Document added!', 'success');
                    closeAddModal();
                    form.reset();
                    loadDocuments();
                    loadDashboard();
                    
                    // Celebration effect for 100th document
                    if (documents.length + 1 === 100) {
                        createFireworks();
                        showToast('🎉 100th Document! You\\'re a Storage Champion!', 'success');
                    }
                } else {
                    showToast(data.message, 'error');
                }
            } catch (error) {
                showToast('Failed to add document', 'error');
            }
        }

        async function handleUploadFile(e) {
            e.preventDefault();
            const form = e.target;
            const fileInput = form[0];
            const file = fileInput.files[0];
            
            if (!file) {
                showToast('Please select a file', 'error');
                return;
            }

            const formData = new FormData();
            formData.append('file', file);
            formData.append('category', form[1].value);
            formData.append('description', form[2].value);

            try {
                const response = await fetch('/api/upload', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();
                
                if (data.success) {
                    showToast('File uploaded!', 'success');
                    closeUploadModal();
                    form.reset();
                    loadDocuments();
                    loadDashboard();
                    
                    // Celebration effect for large files
                    if (file.size > 10 * 1024 * 1024) { // 10MB
                        createRocketAnimation();
                    }
                } else {
                    showToast(data.message, 'error');
                }
            } catch (error) {
                showToast('Upload failed', 'error');
            }
        }

        async function deleteDocument(id) {
            if (!confirm('Are you sure you want to delete this document?')) return;
            
            try {
                const response = await fetch(`/api/documents/${id}`, {
                    method: 'DELETE'
                });
                const data = await response.json();
                
                if (data.success) {
                    showToast('Document deleted', 'success');
                    loadDocuments();
                    loadDashboard();
                } else {
                    showToast(data.message, 'error');
                }
            } catch (error) {
                showToast('Delete failed', 'error');
            }
        }

        async function downloadFile(id) {
            try {
                window.open(`/api/documents/${id}/download`, '_blank');
            } catch (error) {
                showToast('Download failed', 'error');
            }
        }

        function openLink(url) {
            window.open(url, '_blank');
        }

        async function copyLink(url) {
            try {
                await navigator.clipboard.writeText(url);
                showToast('Link copied to clipboard!', 'success');
            } catch (error) {
                showToast('Failed to copy link', 'error');
            }
        }

        function showSection(section) {
            document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');
            
            document.getElementById('dashboardSection').classList.add('hidden');
            document.getElementById('documentsSection').classList.add('hidden');
            document.getElementById(section + 'Section').classList.remove('hidden');
        }

        // Animation Functions
        function createConfetti() {
            const confettiCount = 200;
            const confettiContainer = document.createElement('div');
            confettiContainer.style.position = 'fixed';
            confettiContainer.style.top = '0';
            confettiContainer.style.left = '0';
            confettiContainer.style.width = '100%';
            confettiContainer.style.height = '100%';
            confettiContainer.style.pointerEvents = 'none';
            confettiContainer.style.zIndex = '9999';
            document.body.appendChild(confettiContainer);
            
            for (let i = 0; i < confettiCount; i++) {
                const confetti = document.createElement('div');
                confetti.style.position = 'absolute';
                confetti.style.width = '10px';
                confetti.style.height = '10px';
                confetti.style.backgroundColor = getRandomColor();
                confetti.style.borderRadius = '50%';
                confetti.style.left = Math.random() * 100 + 'vw';
                confetti.style.top = '-10px';
                confetti.style.opacity = '0.8';
                confettiContainer.appendChild(confetti);
                
                // Animate confetti
                const animation = confetti.animate([
                    { transform: 'translateY(0) rotate(0deg)', opacity: 1 },
                    { transform: `translateY(${window.innerHeight}px) rotate(${360 + Math.random() * 360}deg)`, opacity: 0 }
                ], {
                    duration: 2000 + Math.random() * 3000,
                    easing: 'cubic-bezier(0.1, 0.8, 0.2, 1)'
                });
                
                animation.onfinish = () => {
                    confetti.remove();
                    if (confettiContainer.children.length === 0) {
                        confettiContainer.remove();
                    }
                };
            }
        }
        
        function createFireworks() {
            const fireworkCount = 5;
            for (let i = 0; i < fireworkCount; i++) {
                setTimeout(() => {
                    createFirework();
                }, i * 300);
            }
        }
        
        function createFirework() {
            const firework = document.createElement('div');
            firework.style.position = 'fixed';
            firework.style.left = Math.random() * 80 + 10 + 'vw';
            firework.style.top = Math.random() * 80 + 10 + 'vh';
            firework.style.width = '6px';
            firework.style.height = '6px';
            firework.style.backgroundColor = getRandomColor();
            firework.style.borderRadius = '50%';
            firework.style.boxShadow = '0 0 10px ' + getRandomColor();
            firework.style.zIndex = '9999';
            document.body.appendChild(firework);
            
            // Explode firework
            const particles = 30;
            for (let i = 0; i < particles; i++) {
                setTimeout(() => {
                    const particle = document.createElement('div');
                    particle.style.position = 'fixed';
                    particle.style.left = firework.style.left;
                    particle.style.top = firework.style.top;
                    particle.style.width = '4px';
                    particle.style.height = '4px';
                    particle.style.backgroundColor = getRandomColor();
                    particle.style.borderRadius = '50%';
                    particle.style.zIndex = '9999';
                    document.body.appendChild(particle);
                    
                    const angle = (i / particles) * Math.PI * 2;
                    const distance = 50 + Math.random() * 100;
                    const x = Math.cos(angle) * distance;
                    const y = Math.sin(angle) * distance;
                    
                    particle.animate([
                        { transform: 'translate(0, 0) scale(1)', opacity: 1 },
                        { transform: `translate(${x}px, ${y}px) scale(0)`, opacity: 0 }
                    ], {
                        duration: 1000 + Math.random() * 500,
                        easing: 'cubic-bezier(0.1, 0.8, 0.2, 1)'
                    }).onfinish = () => particle.remove();
                }, i * 30);
            }
            
            firework.animate([
                { transform: 'scale(1)', opacity: 1 },
                { transform: 'scale(0)', opacity: 0 }
            ], {
                duration: 500,
                easing: 'ease-out'
            }).onfinish = () => firework.remove();
        }
        
        function createRocketAnimation() {
            const rocket = document.createElement('div');
            rocket.innerHTML = '🚀';
            rocket.style.position = 'fixed';
            rocket.style.left = '50%';
            rocket.style.bottom = '20px';
            rocket.style.fontSize = '40px';
            rocket.style.zIndex = '9999';
            rocket.style.transform = 'translateX(-50%)';
            document.body.appendChild(rocket);
            
            rocket.animate([
                { transform: 'translateX(-50%) translateY(0)', opacity: 1 },
                { transform: 'translateX(-50%) translateY(-100vh)', opacity: 0 }
            ], {
                duration: 2000,
                easing: 'cubic-bezier(0.1, 0.8, 0.2, 1)'
            }).onfinish = () => rocket.remove();
        }
        
        function getRandomColor() {
            const colors = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'];
            return colors[Math.floor(Math.random() * colors.length)];
        }

        // Utility Functions
        function showToast(message, type) {
            const toast = document.getElementById('toast');
            toast.textContent = message;
            toast.className = `toast ${type}`;
            toast.style.display = 'block';
            
            setTimeout(() => {
                toast.style.display = 'none';
            }, 3000);
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Check if user is already logged in
        async function checkAuth() {
            try {
                const response = await fetch('/api/me');
                const data = await response.json();
                if (data.success) {
                    currentUser = data.user;
                    showApp();
                }
            } catch (error) {
                // Not logged in
            }
        }

        // Initialize
        checkAuth();
    </script>
</body>
</html>
    '''

# API Routes (same as before)
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    user = User.query.filter_by(username=data['username']).first()
    
    if user and check_password_hash(user.password_hash, data['password']):
        session['user_id'] = user.id
        return jsonify({
            'success': True, 
            'message': 'Login successful!',
            'user': {'id': user.id, 'username': user.username}
        })
    return jsonify({'success': False, 'message': 'Invalid credentials!'})

@app.route('/api/signup', methods=['POST'])
def api_signup():
    data = request.get_json()
    
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'success': False, 'message': 'Username already exists!'})
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'success': False, 'message': 'Email already registered!'})
    
    user = User(
        username=data['username'],
        email=data['email'],
        password_hash=generate_password_hash(data['password'])
    )
    db.session.add(user)
    db.session.commit()
    
    # ✅ CREATE USER FOLDER IMMEDIATELY AFTER SIGNUP
    create_user_folder(user.id)
    
    # ✅ AUTO-LOGIN AFTER SIGNUP
    session['user_id'] = user.id
    
    return jsonify({
        'success': True, 
        'message': 'Account created successfully!',
        'user': {'id': user.id, 'username': user.username}
    })

@app.route('/api/logout')
def api_logout():
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out!'})

@app.route('/api/me')
def api_me():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        return jsonify({
            'success': True,
            'user': {'id': user.id, 'username': user.username}
        })
    return jsonify({'success': False})

@app.route('/api/stats')
@login_required
def api_stats():
    user_id = session['user_id']
    total_docs = Document.query.filter_by(user_id=user_id).count()
    
    # File types statistics
    file_types = db.session.query(
        Document.file_type, 
        db.func.count(Document.id)
    ).filter_by(user_id=user_id).group_by(Document.file_type).all()
    
    # Categories statistics
    categories = db.session.query(
        Document.category, 
        db.func.count(Document.id)
    ).filter_by(user_id=user_id).group_by(Document.category).all()
    
    total_storage = db.session.query(db.func.sum(Document.file_size)).filter_by(user_id=user_id).scalar() or 0
    
    recent_docs = Document.query.filter_by(user_id=user_id).order_by(Document.created_at.desc()).limit(5).all()
    
    return jsonify({
        'success': True,
        'stats': {
            'total_documents': total_docs,
            'file_types': dict(file_types),
            'categories': dict(categories),
            'total_storage': total_storage,
            'storage_formatted': format_file_size(total_storage),
            'recent_documents': [{'name': doc.name, 'category': doc.category} for doc in recent_docs]
        }
    })

@app.route('/api/documents')
@login_required
def api_documents():
    user_id = session['user_id']
    documents = Document.query.filter_by(user_id=user_id).order_by(Document.created_at.desc()).all()
    
    docs_list = []
    for doc in documents:
        docs_list.append({
            'id': doc.id,
            'name': doc.name,
            'google_doc_link': doc.google_doc_link,
            'file_path': doc.file_path,
            'file_type': doc.file_type,
            'file_size': doc.file_size,
            'file_size_formatted': format_file_size(doc.file_size) if doc.file_size else '',
            'category': doc.category,
            'description': doc.description,
            'created_at': doc.created_at.isoformat()
        })
    
    return jsonify({'success': True, 'documents': docs_list})

@app.route('/api/documents', methods=['POST'])
@login_required
def api_add_document():
    data = request.get_json()
    
    document = Document(
        name=data['name'],
        google_doc_link=data['link'],
        file_type='google_doc',
        category=data.get('category', 'General'),
        description=data.get('description', ''),
        user_id=session['user_id']
    )
    db.session.add(document)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Document added!'})

@app.route('/api/upload', methods=['POST'])
@login_required
def api_upload():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file selected!'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected!'})
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        user_folder = get_user_folder(session['user_id'])
        file_path = os.path.join(user_folder, filename)
        file.save(file_path)
        
        # Get file extension for file type
        file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'unknown'
        
        document = Document(
            name=os.path.splitext(filename)[0],
            original_filename=filename,
            file_path=file_path,
            file_type=file_ext,
            file_size=os.path.getsize(file_path),
            category=request.form.get('category', 'General'),
            description=request.form.get('description', ''),
            user_id=session['user_id']
        )
        db.session.add(document)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'File uploaded!'})
    
    return jsonify({'success': False, 'message': 'Invalid file type!'})

@app.route('/api/documents/<int:doc_id>', methods=['DELETE'])
@login_required
def api_delete_document(doc_id):
    document = Document.query.filter_by(id=doc_id, user_id=session['user_id']).first()
    
    if not document:
        return jsonify({'success': False, 'message': 'Document not found!'})
    
    if document.file_path and os.path.exists(document.file_path):
        os.remove(document.file_path)
    
    db.session.delete(document)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Document deleted!'})

@app.route('/api/documents/<int:doc_id>/download')
@login_required
def api_download_document(doc_id):
    document = Document.query.filter_by(id=doc_id, user_id=session['user_id']).first()
    
    if not document or not document.file_path:
        return jsonify({'success': False, 'message': 'File not found!'})
    
    return send_file(document.file_path, as_attachment=True, download_name=document.original_filename)

# Initialize database and create folders for existing users
def initialize_user_folders():
    """Create folders for all existing users on startup"""
    users = User.query.all()
    for user in users:
        create_user_folder(user.id)
    print(f"✅ Initialized folders for {len(users)} users")

# Initialize database
with app.app_context():
    db.create_all()
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    # Create folders for all existing users
    initialize_user_folders()

if __name__ == '__main__':
    app.run(debug=True)