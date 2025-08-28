from login_app import create_app, db
import os

# Create the Flask application
app = create_app()

if __name__ == '__main__':
    # Run the application
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_DEBUG', '0').lower() in ['1', 'true', 'yes'])
