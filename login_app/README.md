# Simple Web App with Login and Posting

A minimal web application with user authentication and posting functionality built with Python Flask.

## Features

- User registration and login
- Create and view posts
- Simple and clean user interface
- SQLite database for data storage

## Setup

1. **Install Python** (3.7 or higher)

2. **Install dependencies**:
   ```
   pip install -r requirements.txt
   ```

3. **Run the application**:
   ```
   python app.py
   ```

4. **Access the application**:
   Open your web browser and go to `http://localhost:5000`

## Usage

1. Register a new account
2. Log in with your credentials
3. Create new posts using the form
4. View posts from all users
5. Log out when done

## Project Structure

- `app.py` - Main application file
- `templates/` - HTML templates
  - `login.html` - Login page
  - `register.html` - Registration page
  - `dashboard.html` - Main page with posts
- `site.db` - SQLite database (created automatically)
