import threading
from flask import Flask
from time import sleep
import asyncio

app = Flask(__name__)

# Global dictionary variable
response = {}

@app.route('/')
def get_response():
    return str(response)

def update_response():
    global response
    response['message'] = 'Updated by main thread'

if __name__ == '__main__':
    # Start Flask thread
    flask_thread = threading.Thread(target=app.run)
    flask_thread.start()
    # start flash on main thread
    # app.run()

    # Update the response dictionary from the main thread
    response['message'] = 'Updated by main thread'

    # simulate blocked thread for 5 seconds
    sleep(5)

    # Update the response dictionary from the main thread
    response['message'] = 'Updated by main thread again'

    # Perform additional tasks in the main thread
    # update_response()

    # Wait for Flask thread to complete (optional)
    flask_thread.join()