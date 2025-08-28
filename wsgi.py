from login_app import create_app

# Create the Flask application
app = create_app()

# This file is used by Gunicorn in production
# The application factory pattern is used to create the app instance

# This file is used by Gunicorn in production
# The application factory pattern is used to create the app instance

if __name__ == "__main__":
    # This block is only executed when running the script directly
    debug = os.environ.get('FLASK_DEBUG', '0').lower() in ['1', 'true', 'yes']
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)), debug=debug)
